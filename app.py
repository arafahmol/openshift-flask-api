import os
from flask import Flask, request, jsonify
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure
from bson import ObjectId
from datetime import datetime

app = Flask(__name__)

# Get MongoDB URL from environment variable (injected from OpenShift Secret)
MONGO_URL = os.environ.get('MONGO_URL', 'mongodb://localhost:27017/flaskdb')

# Connect to MongoDB
client = MongoClient(MONGO_URL)
db = client.get_database()
products = db['products']

# ── Helper ───────────────────────────────────────────
def serialize(doc):
    """Convert MongoDB document to JSON-serializable dict"""
    doc['_id'] = str(doc['_id'])   # ObjectId is not JSON serializable by default
    return doc

# ── Health check ─────────────────────────────────────
@app.route('/health')
def health():
    try:
        client.admin.command('ping')
        db_status = 'connected'
    except ConnectionFailure:
        db_status = 'disconnected'
    return jsonify({
        'status': 'ok',
        'database': db_status,
        'version': '1.0.0'
    })

# ── Welcome ──────────────────────────────────────────
@app.route('/')
def welcome():
    return jsonify({
        'message': 'Welcome to the Flask Product API!',
        'version': '1.0.0',
        'endpoints': {
            'GET  /products':       'get all products',
            'GET  /products/<id>':  'get one product',
            'POST /products':       'create a product',
            'PUT  /products/<id>':  'update a product',
            'DELETE /products/<id>':'delete a product'
        }
    })

# ── GET all products ──────────────────────────────────
@app.route('/products', methods=['GET'])
def get_products():
    all_products = [serialize(p) for p in products.find()]
    return jsonify({'total': len(all_products), 'products': all_products})

# ── GET one product ───────────────────────────────────
@app.route('/products/<id>', methods=['GET'])
def get_product(id):
    try:
        product = products.find_one({'_id': ObjectId(id)})
        if not product:
            return jsonify({'error': 'Product not found'}), 404
        return jsonify(serialize(product))
    except Exception as e:
        return jsonify({'error': str(e)}), 400

# ── POST create product ───────────────────────────────
@app.route('/products', methods=['POST'])
def create_product():
    data = request.get_json()
    if not data or not data.get('name'):
        return jsonify({'error': 'name is required'}), 400
    product = {
        'name': data['name'],
        'price': data.get('price', 0.0),
        'category': data.get('category', 'general'),
        'createdAt': datetime.utcnow()
    }
    result = products.insert_one(product)
    product['_id'] = str(result.inserted_id)
    product['createdAt'] = product['createdAt'].isoformat()
    return jsonify(product), 201

# ── PUT update product ────────────────────────────────
@app.route('/products/<id>', methods=['PUT'])
def update_product(id):
    try:
        data = request.get_json()
        result = products.find_one_and_update(
            {'_id': ObjectId(id)},
            {'$set': data},
            return_document=True
        )
        if not result:
            return jsonify({'error': 'Product not found'}), 404
        return jsonify(serialize(result))
    except Exception as e:
        return jsonify({'error': str(e)}), 400

# ── DELETE product ────────────────────────────────────
@app.route('/products/<id>', methods=['DELETE'])
def delete_product(id):
    try:
        result = products.find_one_and_delete({'_id': ObjectId(id)})
        if not result:
            return jsonify({'error': 'Product not found'}), 404
        return jsonify({'message': 'Product deleted', 'product': serialize(result)})
    except Exception as e:
        return jsonify({'error': str(e)}), 400

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)
