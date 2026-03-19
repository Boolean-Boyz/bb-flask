import requests as http
from flask import Blueprint, request, jsonify, current_app, g
from flask_restful import Api, Resource
from sqlalchemy import or_

from __init__ import db
from api.fopl_auth_api import fopl_token_required
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

        api_key = current_app.config.get('GEMINI_API_KEY')
        server  = current_app.config.get('GEMINI_SERVER')
        if not api_key:
            return {'message': 'AI search is not configured yet.'}, 503

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

        payload = {'contents': [{'parts': [{'text': prompt}]}]}
        try:
            resp = http.post(
                f'{server}?key={api_key}',
                headers={'Content-Type': 'application/json'},
                json=payload, timeout=30,
            )
            data = resp.json()
            text = data['candidates'][0]['content']['parts'][0]['text']
            return jsonify({'response': text})
        except Exception as e:
            return {'message': f'AI error: {str(e)}'}, 500


api.add_resource(_Books,   '')
api.add_resource(_Book,    '/<int:book_id>')
api.add_resource(_AISearch, '/ai')
