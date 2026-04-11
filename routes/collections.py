from flask import Blueprint, request
from flask_login import login_required, current_user
from extensions import db
from models import Collection, Bookmark
from errors import api_success, NotFoundError, ConflictError, ValidationError
from validators import require_json, validate_string

bp = Blueprint('collections', __name__)

@bp.route('/api/collections', methods=['GET'])
@login_required
def list_collections():
    collections = (
        Collection.query
        .filter_by(user_id=current_user.id)
        .order_by(Collection.created_at.desc())
        .all()
    )
    return api_success([c.to_dict() for c in collections])

@bp.route('/api/collections', methods=['POST'])
@login_required
@require_json('name')
def create_collection():
    data = request.get_json()
    name = validate_string(data['name'], 'Collection name', min_len=1, max_len=128)

    existing = Collection.query.filter_by(user_id=current_user.id, name=name).first()
    if existing:
        raise ConflictError('A collection with this name already exists.')

    collection = Collection(
        user_id=current_user.id,
        name=name,
        color=data.get('color', '#6366f1'),
    )
    db.session.add(collection)
    db.session.commit()

    return api_success(
        collection.to_dict(),
        message='Collection created.',
        status=201,
    )

@bp.route('/api/collections/<int:collection_id>', methods=['PUT'])
@login_required
def update_collection(collection_id):
    collection = Collection.query.filter_by(
        id=collection_id, user_id=current_user.id
    ).first()
    if not collection:
        raise NotFoundError('Collection not found.')

    data = request.get_json() or {}
    if not data.get('name') and not data.get('color'):
        raise ValidationError('Provide at least one field to update (name or color).')

    if data.get('name'):
        collection.name = validate_string(data['name'], 'Collection name', max_len=128)
    if data.get('color'):
        collection.color = data['color']
    db.session.commit()

    return api_success(
        collection.to_dict(),
        message='Collection updated.',
    )


@bp.route('/api/collections/<int:collection_id>', methods=['DELETE'])
@login_required
def delete_collection(collection_id):
    collection = Collection.query.filter_by(
        id=collection_id, user_id=current_user.id
    ).first()
    if not collection:
        raise NotFoundError('Collection not found.')

    Bookmark.query.filter_by(collection_id=collection_id).update({'collection_id': None})
    db.session.delete(collection)
    db.session.commit()

    return api_success(message='Collection deleted.')


@bp.route('/api/bookmarks/<int:bookmark_id>/move', methods=['PUT'])
@login_required
def move_bookmark(bookmark_id):
    bookmark = Bookmark.query.filter_by(
        id=bookmark_id, user_id=current_user.id
    ).first()
    if not bookmark:
        raise NotFoundError('Bookmark not found.')

    data = request.get_json() or {}
    target_id = data.get('collection_id')

    if target_id is not None:
        collection = Collection.query.filter_by(
            id=target_id, user_id=current_user.id
        ).first()
        if not collection:
            raise NotFoundError('Target collection not found.')

    bookmark.collection_id = target_id
    db.session.commit()

    return api_success(
        bookmark.to_dict(),
        message='Bookmark moved.',
    )
