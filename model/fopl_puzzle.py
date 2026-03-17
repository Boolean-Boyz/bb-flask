import json
from datetime import date
from sqlalchemy.exc import IntegrityError
from __init__ import app, db


class FoplPuzzleStat(db.Model):
    __tablename__ = 'fopl_puzzle_stats'

    id           = db.Column(db.Integer, primary_key=True)
    fopl_user_id = db.Column(db.Integer, db.ForeignKey('fopl_users.id'), nullable=False)
    _game        = db.Column(db.String(50), nullable=False)
    _streak      = db.Column(db.Integer, default=0, nullable=False)
    _max_streak  = db.Column(db.Integer, default=0, nullable=False)
    _games_played= db.Column(db.Integer, default=0, nullable=False)
    _games_won   = db.Column(db.Integer, default=0, nullable=False)
    _last_played = db.Column(db.Date, nullable=True)
    _guess_dist  = db.Column(db.Text, nullable=True)   # JSON: {"1":0,...,"6":0}

    __table_args__ = (
        db.UniqueConstraint('fopl_user_id', '_game', name='uq_fopl_user_game'),
    )

    @property
    def guess_dist(self):
        if self._guess_dist:
            return json.loads(self._guess_dist)
        return {"1": 0, "2": 0, "3": 0, "4": 0, "5": 0, "6": 0}

    def read(self):
        return {
            'game':         self._game,
            'streak':       self._streak,
            'max_streak':   self._max_streak,
            'games_played': self._games_played,
            'games_won':    self._games_won,
            'win_rate':     round(self._games_won / self._games_played * 100) if self._games_played else 0,
            'last_played':  self._last_played.isoformat() if self._last_played else None,
            'guess_dist':   self.guess_dist,
        }
