"""FOPL Calendar API — Single responsibility: calendar event CRUD endpoints."""
from functools import wraps
from flask import Blueprint, request, jsonify, g
from flask_restful import Api, Resource

from __init__ import db
from api.fopl_auth_api import fopl_token_required
from model.fopl_event import FoplEvent

fopl_calendar_api = Blueprint('fopl_calendar_api', __name__, url_prefix='/api/fopl/events')
api = Api(fopl_calendar_api)

ADMIN_EMAIL = 'admin@powayfriends.org'


def _admin_required(func):
    @wraps(func)
    @fopl_token_required
    def wrapper(*args, **kwargs):
        if g.fopl_user.email != ADMIN_EMAIL and not g.fopl_user.is_admin():
            return {'message': 'Admin access required'}, 403
        return func(*args, **kwargs)
    return wrapper


class _Events(Resource):
    def get(self):
        """Public — return all events sorted by date."""
        events = FoplEvent.query.order_by(FoplEvent._date).all()
        return jsonify([e.read() for e in events])

    @_admin_required
    def post(self):
        """Admin — create a new event."""
        body = request.get_json() or {}
        title = (body.get('title') or '').strip()
        date  = (body.get('date')  or '').strip()
        if not title:
            return {'message': 'Title is required'}, 400
        if not date:
            return {'message': 'Date is required'}, 400
        event = FoplEvent(
            title=title,
            date=date,
            description=body.get('description', ''),
            color=body.get('color', '#023b0f'),
        ).create()
        return jsonify(event.read())


class _Event(Resource):
    @_admin_required
    def put(self, event_id):
        """Admin — update an existing event."""
        event = FoplEvent.query.get(event_id)
        if not event:
            return {'message': 'Event not found'}, 404
        event.update(request.get_json() or {})
        return jsonify(event.read())

    @_admin_required
    def delete(self, event_id):
        """Admin — delete an event."""
        event = FoplEvent.query.get(event_id)
        if not event:
            return {'message': 'Event not found'}, 404
        event.delete()
        return jsonify({'message': 'Event deleted'})


api.add_resource(_Events, '')
api.add_resource(_Event,  '/<int:event_id>')
