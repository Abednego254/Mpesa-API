# backend/routes/items.py

from backend.routes.auth_middleware import token_required
from flask import Blueprint, request, jsonify
from ..extensions import db
from ..models import Item, InvoiceItem

bp = Blueprint("items", __name__)

# GET all items
@bp.route("/", methods=["GET"])
@token_required()
def get_items():
    items = Item.query.all()
    return jsonify([{
        "id": i.id,
        "name": i.name,
        "description": i.description,
        "price": i.price,
        "stock": i.stock,
        "created_at": i.created_at
    } for i in items])

# GET single item by id
@bp.route("/<int:item_id>", methods=["GET"])
@token_required()
def get_item(item_id):
    item = Item.query.get_or_404(item_id)
    return jsonify({
        "id": item.id,
        "name": item.name,
        "description": item.description,
        "price": item.price,
        "stock": item.stock,
        "created_at": item.created_at
    })

# CREATE new item
@bp.route("/", methods=["POST"])
@token_required()
def create_item():
    data = request.get_json()
    item = Item(
        name=data.get("name"),
        description=data.get("description"),
        price=data.get("price"),
        stock=data.get("stock", 0)
    )
    db.session.add(item)
    db.session.commit()
    return jsonify({"message": "Item created", "id": item.id}), 201

# UPDATE item
@bp.route("/<int:item_id>", methods=["PUT"])
@token_required()
def update_item(item_id):
    item = Item.query.get_or_404(item_id)
    data = request.get_json()
    item.name = data.get("name", item.name)
    item.description = data.get("description", item.description)
    item.price = data.get("price", item.price)
    item.stock = data.get("stock", item.stock)
    db.session.commit()
    return jsonify({"message": "Item updated"})

# DELETE item
@bp.route("/<int:item_id>", methods=["DELETE"])
@token_required()
def delete_item(item_id):
    item = Item.query.get_or_404(item_id)
    # Optional: delete related InvoiceItems first
    InvoiceItem.query.filter_by(item_id=item.id).delete()
    db.session.delete(item)
    db.session.commit()
    return jsonify({"message": "Item deleted"})
