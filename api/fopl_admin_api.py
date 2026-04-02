from flask import Blueprint, jsonify
from flask_restful import Api, Resource
from sqlalchemy import func

from api.fopl_auth_api import fopl_token_required
from flask import g
from model.fopl_user import FoplUser
from model.fopl_book import FoplBook
from model.fopl_event import FoplEvent
from model.fopl_puzzle import FoplPuzzleStat

fopl_admin_api = Blueprint('fopl_admin_api', __name__, url_prefix='/api/fopl/admin')
api = Api(fopl_admin_api)


class _Stats(Resource):
    @fopl_token_required
    def get(self):
        if not g.fopl_user.is_admin():
            return {'message': 'Admin access required'}, 403

        # ── Users ──────────────────────────────────────────────
        users = FoplUser.query.order_by(FoplUser.created_at.desc()).all()
        total_users = len(users)
        total_admins = sum(1 for u in users if u.is_admin())

        # ── Books ───────────────────────────────────────────────
        books = FoplBook.query.all()
        total_books = len(books)
        total_inventory = sum(b._quantity for b in books)
        total_value = round(sum(b._price * b._quantity for b in books), 2)

        by_age = {}
        by_condition = {}
        for b in books:
            by_age[b._age_group] = by_age.get(b._age_group, 0) + b._quantity
            by_condition[b._condition] = by_condition.get(b._condition, 0) + b._quantity

        # ── Games ───────────────────────────────────────────────
        stats = FoplPuzzleStat.query.all()
        total_sessions = sum(s._games_played for s in stats)
        total_wins = sum(s._games_won for s in stats)

        by_game = {}
        for s in stats:
            g_name = s._game
            if g_name not in by_game:
                by_game[g_name] = {'sessions': 0, 'wins': 0}
            by_game[g_name]['sessions'] += s._games_played
            by_game[g_name]['wins'] += s._games_won

        # ── Events ──────────────────────────────────────────────
        total_events = FoplEvent.query.count()

        return jsonify({
            'users': {
                'total': total_users,
                'admins': total_admins,
                'members': total_users - total_admins,
                'list': [u.read() for u in users],
            },
            'books': {
                'total_titles': total_books,
                'total_inventory': total_inventory,
                'total_value': total_value,
                'by_age_group': by_age,
                'by_condition': by_condition,
            },
            'games': {
                'total_sessions': total_sessions,
                'total_wins': total_wins,
                'by_game': by_game,
            },
            'events': {
                'total': total_events,
            },
        })


api.add_resource(_Stats, '/stats')
