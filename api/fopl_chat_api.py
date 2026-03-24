"""
FOPL Chat & AI Search API
Single responsibility: AI-powered book search and chatbot endpoints.
"""
import requests as http
from flask import Blueprint, request, jsonify, current_app
from flask_restful import Api, Resource

from model.fopl_book import FoplBook
from api.fopl_ai_service import call_ai, call_ai_chat

fopl_chat_api = Blueprint('fopl_chat_api', __name__, url_prefix='/api/fopl/books')
api = Api(fopl_chat_api)


def _build_catalog_text(include_qty=False):
    """Build a text snapshot of available books for AI prompts."""
    books = FoplBook.query.filter(FoplBook._quantity > 0).all()
    lines = []
    for b in books:
        series_str = f' (Series: {b._series} #{b._series_num})' if b._series else ''
        line = (
            f'ID:{b.id} | "{b._title}"{series_str} by {b._author} | '
            f'{b._age_group} | {b._genre} | ${b._price:.2f} | '
            f'Condition: {b._condition}'
        )
        if include_qty:
            line += f' | Qty: {b._quantity}'
        line += f' | {b._description or ""}'
        lines.append(line)
    return books, '\n'.join(lines)


class _AISearch(Resource):
    def post(self):
        body  = request.get_json() or {}
        query = (body.get('query') or '').strip()
        if not query:
            return {'message': 'Query required'}, 400

        _books, catalog_text = _build_catalog_text()

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
            text = call_ai(prompt)
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

        books, catalog_text = _build_catalog_text(include_qty=True)

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
            reply = call_ai_chat(system_prompt, history, user_msg, timeout=60)

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


api.add_resource(_AISearch, '/ai')
api.add_resource(_Chat,     '/chat')
