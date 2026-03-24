from datetime import datetime
from sqlalchemy.exc import IntegrityError
from __init__ import db


class FoplBook(db.Model):
    __tablename__ = 'fopl_books'

    id          = db.Column(db.Integer,     primary_key=True)
    _title      = db.Column(db.String(255), nullable=False)
    _author     = db.Column(db.String(255), nullable=False)
    _series     = db.Column(db.String(255), nullable=True)
    _series_num = db.Column(db.Integer,     nullable=True)
    _genre      = db.Column(db.String(100), nullable=False)
    _age_group  = db.Column(db.String(50),  nullable=False)   # Kids | Middle Grade | YA | Adult
    _price      = db.Column(db.Float,       nullable=False)
    _condition  = db.Column(db.String(20),  nullable=False)   # Good | Very Good | Like New
    _quantity   = db.Column(db.Integer,     default=1, nullable=False)
    _description= db.Column(db.Text,        nullable=True)
    _isbn       = db.Column(db.String(20),  nullable=True)
    added_at    = db.Column(db.DateTime,    default=datetime.utcnow)

    @property
    def title(self):       return self._title
    @property
    def author(self):      return self._author
    @property
    def available(self):   return self._quantity > 0

    def read(self):
        return {
            'id':          self.id,
            'title':       self._title,
            'author':      self._author,
            'series':      self._series,
            'series_num':  self._series_num,
            'genre':       self._genre,
            'age_group':   self._age_group,
            'price':       self._price,
            'condition':   self._condition,
            'quantity':    self._quantity,
            'description': self._description,
            'isbn':        self._isbn,
        }

    def create(self):
        try:
            db.session.add(self)
            db.session.commit()
            return self
        except IntegrityError:
            db.session.rollback()
            return None

    def update(self, data):
        for k, v in data.items():
            setattr(self, f'_{k}' if not k.startswith('_') else k, v)
        db.session.commit()

    def delete(self):
        db.session.delete(self)
        db.session.commit()

