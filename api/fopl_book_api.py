import requests as http
from flask import Blueprint, request, jsonify, current_app, g
from flask_restful import Api, Resource
from sqlalchemy import or_
import os

from __init__ import db
from api.fopl_auth_api import fopl_token_required


def _call_ai(prompt_text, system_prompt=None, timeout=30):
    """Try Gemini first, fall back to Groq. Returns the AI text or raises."""
    # ── Try Gemini ───────────────────────────────────────────
    gemini_key = current_app.config.get('GEMINI_API_KEY')
    gemini_server = current_app.config.get('GEMINI_SERVER')
    if gemini_key and gemini_server:
        payload = {'contents': [{'parts': [{'text': prompt_text}]}]}
        if system_prompt:
            payload['system_instruction'] = {'parts': [{'text': system_prompt}]}
        resp = http.post(
            f'{gemini_server}?key={gemini_key}',
            headers={'Content-Type': 'application/json'},
            json=payload, timeout=timeout,
        )
        if resp.status_code == 200:
            data = resp.json()
            return data['candidates'][0]['content']['parts'][0]['text']

    # ── Try Groq ─────────────────────────────────────────────
    groq_key = current_app.config.get('GROQ_API_KEY') or os.getenv('GROQ_API_KEY')
    groq_server = current_app.config.get('GROQ_SERVER') or 'https://api.groq.com/openai/v1/chat/completions'
    if groq_key:
        messages = []
        if system_prompt:
            messages.append({'role': 'system', 'content': system_prompt})
        messages.append({'role': 'user', 'content': prompt_text})
        resp = http.post(
            groq_server,
            headers={'Authorization': f'Bearer {groq_key}', 'Content-Type': 'application/json'},
            json={'model': 'llama-3.3-70b-versatile', 'messages': messages, 'temperature': 0.7, 'max_tokens': 1024},
            timeout=timeout,
        )
        if resp.status_code == 200:
            data = resp.json()
            return data['choices'][0]['message']['content']

    raise RuntimeError('No AI provider configured. Set GEMINI_API_KEY or GROQ_API_KEY in your .env file.')


def _call_ai_chat(system_prompt, history_messages, user_msg, timeout=60):
    """Multi-turn chat: try Gemini then Groq. Returns the AI reply text or raises."""
    # ── Try Gemini ───────────────────────────────────────────
    gemini_key = current_app.config.get('GEMINI_API_KEY')
    gemini_server = current_app.config.get('GEMINI_SERVER')
    if gemini_key and gemini_server:
        gemini_contents = [
            {'role': 'user', 'parts': [{'text': 'You are the FOPL bookstore assistant. Follow the system instructions given to you.'}]},
            {'role': 'model', 'parts': [{'text': "Understood! I'm the FOPL Bookstore Assistant. How can I help you find your next great read today?"}]},
        ]
        for msg in history_messages[-20:]:
            role = 'user' if msg.get('role') == 'user' else 'model'
            text = (msg.get('content') or '').strip()
            if text:
                gemini_contents.append({'role': role, 'parts': [{'text': text}]})
        gemini_contents.append({'role': 'user', 'parts': [{'text': user_msg}]})

        payload = {
            'system_instruction': {'parts': [{'text': system_prompt}]},
            'contents': gemini_contents,
            'generationConfig': {'temperature': 0.7, 'maxOutputTokens': 1024},
        }
        resp = http.post(
            f'{gemini_server}?key={gemini_key}',
            headers={'Content-Type': 'application/json'},
            json=payload, timeout=timeout,
        )
        if resp.status_code == 200:
            data = resp.json()
            return data['candidates'][0]['content']['parts'][0]['text']

    # ── Try Groq ─────────────────────────────────────────────
    groq_key = current_app.config.get('GROQ_API_KEY') or os.getenv('GROQ_API_KEY')
    groq_server = current_app.config.get('GROQ_SERVER') or 'https://api.groq.com/openai/v1/chat/completions'
    if groq_key:
        messages = [{'role': 'system', 'content': system_prompt}]
        for msg in history_messages[-20:]:
            role = msg.get('role', 'user')
            text = (msg.get('content') or '').strip()
            if text:
                messages.append({'role': role, 'content': text})
        messages.append({'role': 'user', 'content': user_msg})

        resp = http.post(
            groq_server,
            headers={'Authorization': f'Bearer {groq_key}', 'Content-Type': 'application/json'},
            json={'model': 'llama-3.3-70b-versatile', 'messages': messages, 'temperature': 0.7, 'max_tokens': 1024},
            timeout=timeout,
        )
        if resp.status_code == 200:
            data = resp.json()
            return data['choices'][0]['message']['content']

    raise RuntimeError('No AI provider configured. Set GEMINI_API_KEY or GROQ_API_KEY in your .env file.')
from model.fopl_book import FoplBook

fopl_book_api = Blueprint('fopl_book_api', __name__, url_prefix='/api/fopl/books')
api = Api(fopl_book_api)


def _admin_required(func):
    from functools import wraps
    @wraps(func)
    @fopl_token_required
    def wrapper(*args, **kwargs):
        if not g.fopl_user.is_admin():
            return {'message': 'Admin access required'}, 403
        return func(*args, **kwargs)
    return wrapper


class _Books(Resource):
    def get(self):
        q         = request.args.get('q', '').strip()
        age       = request.args.get('age', '')
        genre     = request.args.get('genre', '')
        condition = request.args.get('condition', '')

        query = FoplBook.query
        if q:
            like = f'%{q}%'
            query = query.filter(or_(
                FoplBook._title.ilike(like),
                FoplBook._author.ilike(like),
                FoplBook._series.ilike(like),
                FoplBook._genre.ilike(like),
            ))
        if age:
            query = query.filter(FoplBook._age_group == age)
        if genre:
            query = query.filter(FoplBook._genre.ilike(f'%{genre}%'))
        if condition:
            query = query.filter(FoplBook._condition == condition)

        books = query.order_by(FoplBook._age_group, FoplBook._series, FoplBook._series_num, FoplBook._title).all()
        return jsonify([b.read() for b in books])

    @_admin_required
    def post(self):
        body = request.get_json() or {}
        required = ['title', 'author', 'genre', 'age_group', 'price', 'condition']
        if any(not body.get(k) for k in required):
            return {'message': f'Required fields: {", ".join(required)}'}, 400
        book = FoplBook(
            _title=body['title'], _author=body['author'],
            _series=body.get('series'), _series_num=body.get('series_num'),
            _genre=body['genre'], _age_group=body['age_group'],
            _price=float(body['price']), _condition=body['condition'],
            _quantity=int(body.get('quantity', 1)),
            _description=body.get('description'), _isbn=body.get('isbn'),
        ).create()
        if not book:
            return {'message': 'Could not add book'}, 500
        return jsonify(book.read())


class _Book(Resource):
    def get(self, book_id):
        book = FoplBook.query.get(book_id)
        if not book:
            return {'message': 'Book not found'}, 404
        return jsonify(book.read())

    @_admin_required
    def put(self, book_id):
        book = FoplBook.query.get(book_id)
        if not book:
            return {'message': 'Book not found'}, 404
        data = request.get_json() or {}
        allowed = ['title', 'author', 'series', 'series_num', 'genre',
                   'age_group', 'price', 'condition', 'quantity', 'description', 'isbn']
        for field in allowed:
            if field in data:
                setattr(book, f'_{field}', data[field])
        db.session.commit()
        return jsonify(book.read())

    @_admin_required
    def delete(self, book_id):
        book = FoplBook.query.get(book_id)
        if not book:
            return {'message': 'Book not found'}, 404
        book.delete()
        return jsonify({'message': 'Book deleted'})


class _AISearch(Resource):
    def post(self):
        body  = request.get_json() or {}
        query = (body.get('query') or '').strip()
        if not query:
            return {'message': 'Query required'}, 400

        # Build catalog context from DB
        books = FoplBook.query.filter(FoplBook._quantity > 0).all()
        catalog_lines = []
        for b in books:
            series_str = f' (Series: {b._series} #{b._series_num})' if b._series else ''
            catalog_lines.append(
                f'- ID:{b.id} | "{b._title}"{series_str} by {b._author} | '
                f'{b._age_group} | {b._genre} | ${b._price:.2f} | {b._condition} | {b._description or ""}'
            )
        catalog_text = '\n'.join(catalog_lines)

        prompt = f"""You are a helpful librarian at the Friends of the Poway Library used bookstore.
A customer is looking for books. Here is the current catalog of available books:

{catalog_text}

Customer request: "{query}"

Recommend 2–4 books from the catalog above that best match the customer's request.
For each recommendation, include:
- The book title and author
- A brief reason why it matches their request (1 sentence)
- The price

Be warm, friendly, and conversational. If no books closely match, suggest the closest alternatives.
Only recommend books that appear in the catalog above."""

        try:
            text = _call_ai(prompt)
            return jsonify({'response': text})
        except Exception as e:
            return {'message': f'AI error: {str(e)}'}, 500


class _Chat(Resource):
    """
    POST /api/fopl/books/chat
    Full conversational chatbot: budget stacks, vibe recs, store assistant.
    Accepts: { "message": "...", "history": [ {role, content}, ... ] }
    Returns: { "reply": "...", "books_mentioned": [...] }
    """
    def post(self):
        body = request.get_json() or {}
        user_msg = (body.get('message') or '').strip()
        history  = body.get('history') or []
        if not user_msg:
            return {'message': 'message field is required'}, 400

        # ── Build live catalogue snapshot ────────────────────────────
        books = FoplBook.query.filter(FoplBook._quantity > 0).all()
        catalog_lines = []
        for b in books:
            series_str = f' (Series: {b._series} #{b._series_num})' if b._series else ''
            catalog_lines.append(
                f'ID:{b.id} | "{b._title}"{series_str} by {b._author} | '
                f'{b._age_group} | {b._genre} | ${b._price:.2f} | '
                f'Condition: {b._condition} | Qty: {b._quantity} | {b._description or ""}'
            )
        catalog_text = '\n'.join(catalog_lines)

        # ── Events (hardcoded for now — swap for DB later) ───────────
        events_text = (
            "Upcoming FOPL Events:\n"
            "- Saturday Story Time: Every Saturday 10 AM, ages 3-7. Free. Stories, songs, and crafts.\n"
            "- Teen Book Club: 1st & 3rd Wednesday 4 PM, ages 13-17. Currently reading 'The Hunger Games'.\n"
            "- Sci-Fi & Fantasy Night: Friday March 28 at 6 PM. Trivia, cosplay, and featured sci-fi/fantasy books on sale.\n"
            "- Author Visit — Local Authors Fair: Saturday April 5, 11 AM-2 PM. Meet local authors and get signed copies.\n"
            "- Summer Reading Kickoff: June 1. Sign up for the summer reading challenge and earn prizes.\n"
            "- Used Book Sale (Big Spring Sale): April 12-13, 9 AM-4 PM. Extra 25% off all books storewide."
        )

        # ── System prompt ────────────────────────────────────────────
        system_prompt = f"""You are the FOPL Bookstore Assistant — a warm, knowledgeable chatbot for the Friends of the Poway Library used bookstore.

CURRENT INVENTORY (only recommend books from this list):
{catalog_text}

{events_text}

YOUR CAPABILITIES:
1. **Book Stack Builder**: When a customer gives a budget (e.g. "$15"), pick 3-4 books that fit within that budget. Show a running total. Maximize variety and value.
2. **Vibe Matching**: When a customer describes a mood or says "something like X but Y", find the best matches from the catalogue. Explain WHY each book fits the vibe.
3. **Store Assistant**: Answer questions about inventory, prices, book conditions, age groups, and series availability. If we don't have something, say so honestly and suggest the closest alternative.
4. **Event Recommendations**: When relevant, mention upcoming events. If someone asks about sci-fi, mention Sci-Fi Night. If they have young kids, mention Story Time, etc.
5. **Series Completion Helper**: If someone mentions they own or have read books in a series, immediately check the inventory for OTHER books in that same series they might be missing. Proactively list which ones we carry with prices. For example, if someone says "I love Dog Man" or "I have Percy Jackson 1 and 2", list ALL the other books in that series we have in stock. Always mention series_num so they know the reading order.
6. **Age-Appropriate Filtering**: Pay close attention to age cues. If a customer mentions their child's age, grade, or reading level, ONLY recommend books from the appropriate age group:
   - Ages 4-7 or grades K-2 → "Kids" books only
   - Ages 8-12 or grades 3-7 → "Kids" and "Middle Grade" books
   - Ages 13-17 or grades 8-12 → "Middle Grade" and "YA" books
   - Adults or no age mentioned → any age group is fine
   If a parent says "for my 6-year-old", do NOT suggest YA or Adult books. If they say "for my teenager", focus on YA. Always mention the age group so parents can make informed choices.

RULES:
- ONLY recommend books that appear in the inventory above. Never invent books.
- Always include the price when recommending a book.
- If the customer has a budget, never exceed it. Show subtotals.
- Be friendly, enthusiastic about reading, and conversational — like a real bookstore employee.
- Keep responses concise but helpful (aim for 3-8 sentences unless the question needs more).
- If you don't know something or we don't carry a book, be honest about it.
- When recommending series books, always mention the series name and book number so customers know reading order.
- If a customer mentions an age or grade, acknowledge it and explain why your picks are age-appropriate."""

        try:
            reply = _call_ai_chat(system_prompt, history, user_msg, timeout=60)

            # ── Extract mentioned book IDs for frontend highlighting ─
            mentioned = []
            for b in books:
                if b._title.lower() in reply.lower():
                    mentioned.append(b.read())

            return jsonify({'reply': reply, 'books_mentioned': mentioned})

        except http.exceptions.Timeout:
            return {'message': 'AI request timed out. Please try again.'}, 504
        except Exception as e:
            current_app.logger.error(f'FOPL chat error: {e}')
            return {'message': f'Chat error: {str(e)}'}, 500


api.add_resource(_Books,    '')
api.add_resource(_Book,     '/<int:book_id>')
api.add_resource(_AISearch, '/ai')
api.add_resource(_Chat,     '/chat')
