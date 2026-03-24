from datetime import datetime
from sqlalchemy.exc import IntegrityError
from werkzeug.security import generate_password_hash, check_password_hash

from __init__ import db


class FoplUser(db.Model):
    """
    FoplUser Model
    Stores registered users for the Friends of the Poway Library site.

    Columns:
        id         — primary key
        _name      — display name
        _email     — unique login identifier
        _password  — hashed password
        _role      — 'Member' or 'Admin' (default 'Member')
        created_at — UTC timestamp of account creation
    """
    __tablename__ = 'fopl_users'

    id         = db.Column(db.Integer,     primary_key=True)
    _name      = db.Column(db.String(255), nullable=False)
    _email     = db.Column(db.String(255), unique=True, nullable=False)
    _password  = db.Column(db.String(255), nullable=False)
    _role      = db.Column(db.String(20),  nullable=False, default='Member')
    created_at = db.Column(db.DateTime,    nullable=False, default=datetime.utcnow)

    def __init__(self, name, email, password, role='Member'):
        self._name  = name
        self._email = email.lower().strip()
        self.set_password(password)
        self._role  = role

    def set_password(self, password):
        if password and password.startswith('pbkdf2:sha256:'):
            self._password = password
        else:
            self._password = generate_password_hash(password, 'pbkdf2:sha256', salt_length=10)

    def is_password(self, password):
        return check_password_hash(self._password, password)

    @property
    def name(self):
        return self._name

    @property
    def email(self):
        return self._email

    @property
    def role(self):
        return self._role

    def is_admin(self):
        return self._role == 'Admin'

    def create(self):
        try:
            db.session.add(self)
            db.session.commit()
            return self
        except IntegrityError:
            db.session.rollback()
            return None

    def read(self):
        return {
            'id':         self.id,
            'name':       self._name,
            'email':      self._email,
            'role':       self._role,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }

    def delete(self):
        db.session.delete(self)
        db.session.commit()
