import json
from datetime import date
from flask import Blueprint, request, jsonify, g
from flask_restful import Api, Resource

from __init__ import db
from api.fopl_auth_api import fopl_token_required
from model.fopl_puzzle import FoplPuzzleStat

fopl_puzzle_api = Blueprint('fopl_puzzle_api', __name__, url_prefix='/api/fopl/puzzle')
api = Api(fopl_puzzle_api)

EMPTY_DIST = {"1": 0, "2": 0, "3": 0, "4": 0, "5": 0, "6": 0}


class _Stats(Resource):
    @fopl_token_required
    def get(self):
        game = request.args.get('game', 'wordle')
        stat = FoplPuzzleStat.query.filter_by(fopl_user_id=g.fopl_user.id, _game=game).first()
        if not stat:
            return jsonify({'game': game, 'streak': 0, 'max_streak': 0,
                            'games_played': 0, 'games_won': 0, 'win_rate': 0,
                            'last_played': None, 'guess_dist': EMPTY_DIST})
        return jsonify(stat.read())

    @fopl_token_required
    def post(self):
        body    = request.get_json() or {}
        game    = body.get('game', 'wordle')
        won     = bool(body.get('won', False))
        guesses = body.get('guesses')   # int 1-6, or None if lost

        stat = FoplPuzzleStat.query.filter_by(fopl_user_id=g.fopl_user.id, _game=game).first()
        if not stat:
            stat = FoplPuzzleStat(fopl_user_id=g.fopl_user.id, _game=game)
            db.session.add(stat)

        today = date.today()
        # Don't record the same game twice in one day
        if stat._last_played == today:
            return jsonify(stat.read())

        stat._games_played += 1
        if won:
            # Extend streak if played consecutively
            if stat._last_played and (today - stat._last_played).days == 1:
                stat._streak += 1
            else:
                stat._streak = 1
            stat._max_streak = max(stat._max_streak, stat._streak)
            stat._games_won += 1
            if guesses:
                dist = stat.guess_dist
                dist[str(guesses)] = dist.get(str(guesses), 0) + 1
                stat._guess_dist = json.dumps(dist)
        else:
            stat._streak = 0

        stat._last_played = today
        db.session.commit()
        return jsonify(stat.read())


api.add_resource(_Stats, '/stats')
