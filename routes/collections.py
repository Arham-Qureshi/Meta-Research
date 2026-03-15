"""
routes/collections.py — Bookmark collection CRUD routes.

Provides endpoints for creating, listing, updating, and deleting
bookmark collections, plus moving bookmarks between collections.
"""

from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from extensions import db
from models import Collection, Bookmark

bp = Blueprint('collections', __name__)


@bp.route('/api/collections', methods=['GET'])
@login_required
def list_collections():
    """List all collections for the current user, with bookmark counts."""
    collections = Collection.query.filter_by(user_id=current_user.id)\
                                   .order_by(Collection.created_at.desc()).all()
    return jsonify({'collections': [c.to_dict() for c in collections]})


@bp.route('/api/collections', methods=['POST'])
@login_required
def create_collection():
    """Create a new collection."""
    data = request.get_json()
    name = (data.get('name') or '').strip() if data else ''
    if not name:
        return jsonify({'error': 'Collection name is required.'}), 400

    existing = Collection.query.filter_by(user_id=current_user.id, name=name).first()
    if existing:
        return jsonify({'error': 'A collection with this name already exists.'}), 409

    collection = Collection(
        user_id=current_user.id,
        name=name,
        color=data.get('color', '#6366f1'),
    )
    db.session.add(collection)
    db.session.commit()
    return jsonify({'message': 'Collection created.', 'collection': collection.to_dict()}), 201


@bp.route('/api/collections/<int:collection_id>', methods=['PUT'])
@login_required
def update_collection(collection_id):
    """Rename or re-colour a collection."""
    collection = Collection.query.filter_by(
        id=collection_id, user_id=current_user.id
    ).first()
    if not collection:
        return jsonify({'error': 'Collection not found.'}), 404

    data = request.get_json() or {}
    if data.get('name'):
        collection.name = data['name'].strip()
    if data.get('color'):
        collection.color = data['color']
    db.session.commit()
    return jsonify({'message': 'Collection updated.', 'collection': collection.to_dict()})


@bp.route('/api/collections/<int:collection_id>', methods=['DELETE'])
@login_required
def delete_collection(collection_id):
    """Delete a collection. Bookmarks inside become uncollected."""
    collection = Collection.query.filter_by(
        id=collection_id, user_id=current_user.id
    ).first()
    if not collection:
        return jsonify({'error': 'Collection not found.'}), 404

    # Unlink bookmarks from this collection (don't delete them)
    Bookmark.query.filter_by(collection_id=collection_id)\
                   .update({'collection_id': None})
    db.session.delete(collection)
    db.session.commit()
    return jsonify({'message': 'Collection deleted.'})


@bp.route('/api/bookmarks/<int:bookmark_id>/move', methods=['PUT'])
@login_required
def move_bookmark(bookmark_id):
    """Move a bookmark into a collection, or set to null to uncollect."""
    bookmark = Bookmark.query.filter_by(
        id=bookmark_id, user_id=current_user.id
    ).first()
    if not bookmark:
        return jsonify({'error': 'Bookmark not found.'}), 404

    data = request.get_json() or {}
    target_id = data.get('collection_id')

    if target_id is not None:
        collection = Collection.query.filter_by(
            id=target_id, user_id=current_user.id
        ).first()
        if not collection:
            return jsonify({'error': 'Target collection not found.'}), 404

    bookmark.collection_id = target_id
    db.session.commit()
    return jsonify({'message': 'Bookmark moved.', 'bookmark': bookmark.to_dict()})
