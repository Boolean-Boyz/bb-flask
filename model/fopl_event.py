"""FOPL Event Model — Single responsibility: calendar event schema and CRUD."""
from datetime import datetime
from __init__ import db


class FoplEvent(db.Model):
    __tablename__ = 'fopl_events'

    id           = db.Column(db.Integer,     primary_key=True)
    _title       = db.Column(db.String(255), nullable=False)
    _date        = db.Column(db.String(10),  nullable=False)   # YYYY-MM-DD
    _description = db.Column(db.Text,        nullable=True)
    _color       = db.Column(db.String(20),  nullable=False, default='#023b0f')
    created_at   = db.Column(db.DateTime,    nullable=False, default=datetime.utcnow)

    def __init__(self, title, date, description='', color='#023b0f'):
        self._title       = title.strip()
        self._date        = date          # expects 'YYYY-MM-DD'
        self._description = (description or '').strip()
        self._color       = color or '#023b0f'

    def read(self):
        return {
            'id':          self.id,
            'title':       self._title,
            'date':        self._date,
            'description': self._description,
            'color':       self._color,
        }

    def create(self):
        db.session.add(self)
        db.session.commit()
        return self

    def update(self, data):
        if 'title'       in data: self._title       = data['title'].strip()
        if 'date'        in data: self._date         = data['date']
        if 'description' in data: self._description  = (data['description'] or '').strip()
        if 'color'       in data: self._color        = data['color'] or '#023b0f'
        db.session.commit()

    def delete(self):
        db.session.delete(self)
        db.session.commit()
