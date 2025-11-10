from flask import Flask, render_template, request, jsonify, send_file, session, redirect, url_for
from functools import wraps
from werkzeug.utils import secure_filename
import sqlite3
import json
from datetime import datetime
import pandas as pd
import io
import os
import hashlib

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SESSION_SECRET', 'dev-secret-key-change-in-production')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['SESSION_COOKIE_SECURE'] = os.environ.get('FLASK_ENV') == 'production'
app.config['UPLOAD_FOLDER'] = 'static/uploads/models'
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

# Create upload folder if it doesn't exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

DATABASE = 'inventory.db'
ADMIN_USERNAME = 'admin'
ADMIN_PASSWORD_HASH = hashlib.sha256('admin123'.encode()).hexdigest()

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in'):
            return jsonify({'error': 'Authentication required'}), 401
        return f(*args, **kwargs)
    return decorated_function

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            description TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS brands (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            description TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS models (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            brand_id INTEGER NOT NULL,
            description TEXT,
            image_data TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (brand_id) REFERENCES brands (id),
            UNIQUE(name, brand_id)
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sku TEXT UNIQUE,
            name TEXT NOT NULL,
            category_id INTEGER,
            brand_id INTEGER,
            model_id INTEGER,
            description TEXT,
            cost_price REAL DEFAULT 0,
            selling_price REAL DEFAULT 0,
            mrp REAL DEFAULT 0,
            opening_stock INTEGER DEFAULT 0,
            current_stock INTEGER DEFAULT 0,
            min_stock_level INTEGER DEFAULT 10,
            storage_location TEXT,
            imei TEXT,
            color TEXT,
            storage_capacity TEXT,
            ram TEXT,
            warranty_period TEXT,
            supplier_name TEXT,
            supplier_contact TEXT,
            image_url TEXT,
            status TEXT DEFAULT 'active',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (category_id) REFERENCES categories (id),
            FOREIGN KEY (brand_id) REFERENCES brands (id),
            FOREIGN KEY (model_id) REFERENCES models (id)
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS purchase_orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            po_number TEXT UNIQUE NOT NULL,
            supplier_name TEXT NOT NULL,
            supplier_contact TEXT,
            order_date DATE NOT NULL,
            expected_delivery DATE,
            status TEXT DEFAULT 'pending',
            payment_status TEXT DEFAULT 'unpaid',
            storage_location TEXT,
            total_amount REAL DEFAULT 0,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS purchase_order_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            po_id INTEGER NOT NULL,
            product_id INTEGER,
            product_name TEXT NOT NULL,
            category_id INTEGER,
            brand_id INTEGER,
            model_id INTEGER,
            quantity INTEGER NOT NULL,
            cost_price REAL NOT NULL,
            received_quantity INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (po_id) REFERENCES purchase_orders (id),
            FOREIGN KEY (product_id) REFERENCES products (id),
            FOREIGN KEY (category_id) REFERENCES categories (id),
            FOREIGN KEY (brand_id) REFERENCES brands (id),
            FOREIGN KEY (model_id) REFERENCES models (id)
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS stock_movements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER NOT NULL,
            type TEXT NOT NULL,
            quantity INTEGER NOT NULL,
            reference_type TEXT,
            reference_id INTEGER,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (product_id) REFERENCES products (id)
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS damaged_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            po_id INTEGER NOT NULL,
            po_item_id INTEGER NOT NULL,
            product_name TEXT NOT NULL,
            quantity INTEGER NOT NULL,
            damage_reason TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (po_id) REFERENCES purchase_orders (id),
            FOREIGN KEY (po_item_id) REFERENCES purchase_order_items (id)
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS grns (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            grn_number TEXT UNIQUE NOT NULL,
            po_id INTEGER NOT NULL,
            po_number TEXT NOT NULL,
            supplier_name TEXT NOT NULL,
            received_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            total_items INTEGER DEFAULT 0,
            total_quantity INTEGER DEFAULT 0,
            payment_status TEXT DEFAULT 'unpaid',
            storage_location TEXT,
            notes TEXT,
            created_by TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (po_id) REFERENCES purchase_orders (id)
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS grn_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            grn_id INTEGER NOT NULL,
            product_id INTEGER,
            product_name TEXT NOT NULL,
            quantity_received INTEGER NOT NULL,
            quantity_damaged INTEGER DEFAULT 0,
            damage_reason TEXT,
            cost_price REAL NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (grn_id) REFERENCES grns (id),
            FOREIGN KEY (product_id) REFERENCES products (id)
        )
    ''')

    conn.commit()
    conn.close()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/login', methods=['POST'])
def login():
    data = request.json
    if not data or 'username' not in data or 'password' not in data:
        return jsonify({'success': False, 'error': 'Username and password required'}), 400

    username = data['username']
    password = data['password']
    password_hash = hashlib.sha256(password.encode()).hexdigest()

    if username == ADMIN_USERNAME and password_hash == ADMIN_PASSWORD_HASH:
        session['logged_in'] = True
        session['username'] = username
        return jsonify({'success': True, 'username': username})

    return jsonify({'success': False, 'error': 'Invalid credentials'}), 401

@app.route('/api/logout', methods=['POST'])
def logout():
    session.clear()
    return jsonify({'success': True})

@app.route('/api/check-auth', methods=['GET'])
def check_auth():
    return jsonify({'logged_in': session.get('logged_in', False), 'username': session.get('username')})

@app.route('/api/categories', methods=['GET', 'POST'])
@login_required
def categories():
    conn = get_db()
    cursor = conn.cursor()

    if request.method == 'POST':
        data = request.json
        try:
            cursor.execute('INSERT INTO categories (name, description) VALUES (?, ?)',
                         (data['name'], data.get('description', '')))
            conn.commit()
            return jsonify({'success': True, 'id': cursor.lastrowid})
        except sqlite3.IntegrityError:
            return jsonify({'success': False, 'error': 'Category already exists'}), 400
        finally:
            conn.close()
    else:
        cursor.execute('SELECT * FROM categories ORDER BY name')
        categories = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return jsonify(categories)

@app.route('/api/categories/<int:id>', methods=['PUT', 'DELETE'])
@login_required
def category_detail(id):
    conn = get_db()
    cursor = conn.cursor()

    if request.method == 'PUT':
        data = request.json
        try:
            cursor.execute('UPDATE categories SET name = ?, description = ? WHERE id = ?',
                         (data['name'], data.get('description', ''), id))
            conn.commit()
            return jsonify({'success': True})
        except sqlite3.IntegrityError:
            return jsonify({'success': False, 'error': 'Category name already exists'}), 400
        finally:
            conn.close()
    elif request.method == 'DELETE':
        try:
            cursor.execute('DELETE FROM categories WHERE id = ?', (id,))
            conn.commit()
            return jsonify({'success': True})
        except sqlite3.IntegrityError:
            return jsonify({'success': False, 'error': 'Cannot delete category with associated products'}), 400
        finally:
            conn.close()

@app.route('/api/brands', methods=['GET', 'POST'])
@login_required
def brands():
    conn = get_db()
    cursor = conn.cursor()

    if request.method == 'POST':
        data = request.json
        try:
            cursor.execute('INSERT INTO brands (name, description) VALUES (?, ?)',
                         (data['name'], data.get('description', '')))
            conn.commit()
            return jsonify({'success': True, 'id': cursor.lastrowid})
        except sqlite3.IntegrityError:
            return jsonify({'success': False, 'error': 'Brand already exists'}), 400
        finally:
            conn.close()
    else:
        cursor.execute('SELECT * FROM brands ORDER BY name')
        brands = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return jsonify(brands)

@app.route('/api/brands/<int:id>', methods=['PUT', 'DELETE'])
@login_required
def brand_detail(id):
    conn = get_db()
    cursor = conn.cursor()

    if request.method == 'PUT':
        data = request.json
        try:
            cursor.execute('UPDATE brands SET name = ?, description = ? WHERE id = ?',
                         (data['name'], data.get('description', ''), id))
            conn.commit()
            return jsonify({'success': True})
        except sqlite3.IntegrityError:
            return jsonify({'success': False, 'error': 'Brand name already exists'}), 400
        finally:
            conn.close()
    elif request.method == 'DELETE':
        try:
            cursor.execute('DELETE FROM brands WHERE id = ?', (id,))
            conn.commit()
            return jsonify({'success': True})
        except sqlite3.IntegrityError:
            return jsonify({'success': False, 'error': 'Cannot delete brand with associated products'}), 400
        finally:
            conn.close()

@app.route('/api/models', methods=['GET', 'POST'])
@login_required
def models():
    conn = get_db()
    cursor = conn.cursor()

    if request.method == 'POST':
        try:
            data = request.json
            name = data.get('name')
            brand_id = data.get('brand_id')
            description = data.get('description', '')
            image_data = data.get('image_data', '')
            
            cursor.execute('INSERT INTO models (name, brand_id, description, image_data) VALUES (?, ?, ?, ?)',
                         (name, brand_id, description, image_data))
            conn.commit()
            return jsonify({'success': True, 'id': cursor.lastrowid})
        except sqlite3.IntegrityError:
            return jsonify({'success': False, 'error': 'Model already exists for this brand'}), 400
        finally:
            conn.close()
    else:
        cursor.execute('''
            SELECT m.*, b.name as brand_name 
            FROM models m 
            LEFT JOIN brands b ON m.brand_id = b.id 
            ORDER BY b.name, m.name
        ''')
        models = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return jsonify(models)

@app.route('/api/models/<int:id>', methods=['PUT', 'DELETE'])
@login_required
def model_detail(id):
    conn = get_db()
    cursor = conn.cursor()

    if request.method == 'PUT':
        try:
            data = request.json
            name = data.get('name')
            brand_id = data.get('brand_id')
            description = data.get('description', '')
            image_data = data.get('image_data', '')
            
            cursor.execute('UPDATE models SET name = ?, brand_id = ?, description = ?, image_data = ? WHERE id = ?',
                         (name, brand_id, description, image_data, id))
            conn.commit()
            return jsonify({'success': True})
        except sqlite3.IntegrityError:
            return jsonify({'success': False, 'error': 'Model already exists for this brand'}), 400
        finally:
            conn.close()
    elif request.method == 'DELETE':
        try:
            cursor.execute('DELETE FROM models WHERE id = ?', (id,))
            conn.commit()
            return jsonify({'success': True})
        except sqlite3.IntegrityError:
            return jsonify({'success': False, 'error': 'Cannot delete model with associated products'}), 400
        finally:
            conn.close()

@app.route('/api/products', methods=['GET', 'POST'])
@login_required
def products():
    conn = get_db()
    cursor = conn.cursor()

    if request.method == 'POST':
        data = request.json
        try:
            cursor.execute('''
                INSERT INTO products (
                    sku, name, category_id, brand_id, model_id, description,
                    cost_price, selling_price, mrp, opening_stock, current_stock,
                    min_stock_level, storage_location, imei, color, storage_capacity,
                    ram, warranty_period, supplier_name, supplier_contact, image_url, status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                data.get('sku'), data['name'], data.get('category_id'), data.get('brand_id'),
                data.get('model_id'), data.get('description'), data.get('cost_price', 0),
                data.get('selling_price', 0), data.get('mrp', 0), data.get('opening_stock', 0),
                data.get('opening_stock', 0), data.get('min_stock_level', 10),
                data.get('storage_location'), data.get('imei'), data.get('color'),
                data.get('storage_capacity'), data.get('ram'), data.get('warranty_period'),
                data.get('supplier_name'), data.get('supplier_contact'), data.get('image_url'), 
                data.get('status', 'active')
            ))
            conn.commit()

            if data.get('opening_stock', 0) > 0:
                cursor.execute('''
                    INSERT INTO stock_movements (product_id, type, quantity, reference_type, notes)
                    VALUES (?, ?, ?, ?, ?)
                ''', (cursor.lastrowid, 'opening_stock', data.get('opening_stock', 0), 'manual', 'Opening stock'))
                conn.commit()

            return jsonify({'success': True, 'id': cursor.lastrowid})
        except sqlite3.IntegrityError as e:
            return jsonify({'success': False, 'error': str(e)}), 400
        finally:
            conn.close()
    else:
        search = request.args.get('search', '')
        category_id = request.args.get('category_id', '')
        brand_id = request.args.get('brand_id', '')
        model_id = request.args.get('model_id', '')
        status = request.args.get('status', '')
        stock_status = request.args.get('stock_status', '')

        query = '''
            SELECT p.*, c.name as category_name, b.name as brand_name, m.name as model_name
            FROM products p
            LEFT JOIN categories c ON p.category_id = c.id
            LEFT JOIN brands b ON p.brand_id = b.id
            LEFT JOIN models m ON p.model_id = m.id
            WHERE 1=1
        '''
        params = []

        if search:
            query += ' AND (p.name LIKE ? OR p.sku LIKE ? OR p.description LIKE ?)'
            search_param = f'%{search}%'
            params.extend([search_param, search_param, search_param])

        if category_id:
            query += ' AND p.category_id = ?'
            params.append(category_id)

        if brand_id:
            query += ' AND p.brand_id = ?'
            params.append(brand_id)

        if model_id:
            query += ' AND p.model_id = ?'
            params.append(model_id)

        if status:
            query += ' AND p.status = ?'
            params.append(status)

        if stock_status == 'low':
            query += ' AND p.current_stock <= p.min_stock_level'
        elif stock_status == 'out':
            query += ' AND p.current_stock = 0'

        query += ' ORDER BY p.created_at DESC'

        cursor.execute(query, params)
        products = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return jsonify(products)

@app.route('/api/products/<int:id>', methods=['GET', 'PUT', 'DELETE'])
@login_required
def product_detail(id):
    conn = get_db()
    cursor = conn.cursor()

    if request.method == 'GET':
        cursor.execute('''
            SELECT p.*, c.name as category_name, b.name as brand_name, m.name as model_name
            FROM products p
            LEFT JOIN categories c ON p.category_id = c.id
            LEFT JOIN brands b ON p.brand_id = b.id
            LEFT JOIN models m ON p.model_id = m.id
            WHERE p.id = ?
        ''', (id,))
        product = cursor.fetchone()
        conn.close()
        if product:
            return jsonify(dict(product))
        return jsonify({'error': 'Product not found'}), 404

    elif request.method == 'PUT':
        data = request.json
        try:
            # Get old stock value to track changes
            cursor.execute('SELECT current_stock FROM products WHERE id = ?', (id,))
            old_stock = cursor.fetchone()['current_stock']
            new_stock = data.get('current_stock', old_stock)

            cursor.execute('''
                UPDATE products SET
                    sku = ?, name = ?, category_id = ?, brand_id = ?, model_id = ?,
                    description = ?, cost_price = ?, selling_price = ?, mrp = ?,
                    current_stock = ?, min_stock_level = ?, storage_location = ?, imei = ?, color = ?,
                    storage_capacity = ?, ram = ?, warranty_period = ?, supplier_name = ?,
                    supplier_contact = ?, image_url = ?, status = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (
                data.get('sku'), data['name'], data.get('category_id'), data.get('brand_id'),
                data.get('model_id'), data.get('description'), data.get('cost_price', 0),
                data.get('selling_price', 0), data.get('mrp', 0), new_stock,
                data.get('min_stock_level', 10), data.get('storage_location'), data.get('imei'), 
                data.get('color'), data.get('storage_capacity'), data.get('ram'), 
                data.get('warranty_period'), data.get('supplier_name'), data.get('supplier_contact'), 
                data.get('image_url'), data.get('status', 'active'), id
            ))

            # Record stock adjustment if stock changed
            if new_stock != old_stock:
                stock_diff = new_stock - old_stock
                cursor.execute('''
                    INSERT INTO stock_movements (product_id, type, quantity, reference_type, notes)
                    VALUES (?, ?, ?, ?, ?)
                ''', (id, 'adjustment', stock_diff, 'manual', 'Stock adjustment via edit'))
            conn.commit()
            return jsonify({'success': True})
        except sqlite3.IntegrityError as e:
            return jsonify({'success': False, 'error': str(e)}), 400
        finally:
            conn.close()

    elif request.method == 'DELETE':
        cursor.execute('DELETE FROM products WHERE id = ?', (id,))
        conn.commit()
        conn.close()
        return jsonify({'success': True})

@app.route('/api/products/bulk-delete', methods=['POST'])
@login_required
def bulk_delete_products():
    data = request.json
    ids = data.get('ids', [])

    conn = get_db()
    cursor = conn.cursor()

    placeholders = ','.join('?' * len(ids))
    cursor.execute(f'DELETE FROM products WHERE id IN ({placeholders})', ids)
    conn.commit()
    conn.close()

    return jsonify({'success': True, 'deleted': len(ids)})

@app.route('/api/products/bulk-update', methods=['POST'])
@login_required
def bulk_update_products():
    data = request.json
    ids = data.get('ids', [])
    updates = data.get('updates', {})

    conn = get_db()
    cursor = conn.cursor()

    set_clauses = []
    params = []

    if 'category_id' in updates:
        set_clauses.append('category_id = ?')
        params.append(updates['category_id'])

    if 'status' in updates:
        set_clauses.append('status = ?')
        params.append(updates['status'])

    if 'selling_price' in updates:
        set_clauses.append('selling_price = ?')
        params.append(updates['selling_price'])

    if 'cost_price' in updates:
        set_clauses.append('cost_price = ?')
        params.append(updates['cost_price'])

    if set_clauses:
        set_clauses.append('updated_at = CURRENT_TIMESTAMP')
        params.extend(ids)
        placeholders = ','.join('?' * len(ids))
        query = f"UPDATE products SET {', '.join(set_clauses)} WHERE id IN ({placeholders})"
        cursor.execute(query, params)
        conn.commit()

    conn.close()
    return jsonify({'success': True, 'updated': len(ids)})

@app.route('/api/purchase-orders', methods=['GET', 'POST'])
@login_required
def purchase_orders():
    conn = get_db()
    cursor = conn.cursor()

    if request.method == 'POST':
        data = request.json
        try:
            cursor.execute('''
                INSERT INTO purchase_orders (
                    po_number, supplier_name, supplier_contact, order_date,
                    expected_delivery, status, total_amount, notes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                data['po_number'], data['supplier_name'], data.get('supplier_contact'),
                data['order_date'], data.get('expected_delivery'), 'pending',
                data.get('total_amount', 0), data.get('notes')
            ))
            po_id = cursor.lastrowid

            for item in data.get('items', []):
                cursor.execute('''
                    INSERT INTO purchase_order_items (
                        po_id, product_id, product_name, category_id, brand_id,
                        model_id, quantity, cost_price
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    po_id, item.get('product_id'), item['product_name'],
                    item.get('category_id'), item.get('brand_id'), item.get('model_id'),
                    item['quantity'], item['cost_price']
                ))

            conn.commit()
            return jsonify({'success': True, 'id': po_id})
        except sqlite3.IntegrityError as e:
            return jsonify({'success': False, 'error': str(e)}), 400
        finally:
            conn.close()
    else:
        cursor.execute('''
            SELECT * FROM purchase_orders ORDER BY created_at DESC
        ''')
        pos = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return jsonify(pos)

@app.route('/api/purchase-orders/<int:id>', methods=['GET'])
@login_required
def purchase_order_detail(id):
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute('SELECT * FROM purchase_orders WHERE id = ?', (id,))
    po = cursor.fetchone()

    if not po:
        conn.close()
        return jsonify({'error': 'Purchase order not found'}), 404

    cursor.execute('''
        SELECT poi.*, c.name as category_name, b.name as brand_name, m.name as model_name
        FROM purchase_order_items poi
        LEFT JOIN categories c ON poi.category_id = c.id
        LEFT JOIN brands b ON poi.brand_id = b.id
        LEFT JOIN models m ON poi.model_id = m.id
        WHERE poi.po_id = ?
    ''', (id,))
    items = [dict(row) for row in cursor.fetchall()]

    result = dict(po)
    result['items'] = items

    conn.close()
    return jsonify(result)

@app.route('/api/purchase-orders/<int:id>/receive', methods=['POST'])
@login_required
def receive_purchase_order(id):
    data = request.json
    conn = get_db()
    cursor = conn.cursor()

    try:
        payment_status = data.get('payment_status', 'unpaid')
        storage_location = data.get('storage_location', '')
        damaged_count = 0

        # Get PO details
        cursor.execute('SELECT po_number, supplier_name FROM purchase_orders WHERE id = ?', (id,))
        po_row = cursor.fetchone()
        if not po_row:
            return jsonify({'success': False, 'error': 'Purchase order not found'}), 404

        po_data = dict(po_row)

        # Generate GRN number
        grn_number = f"GRN-{datetime.now().strftime('%Y%m%d%H%M%S')}"

        # Create GRN record
        cursor.execute('''
            INSERT INTO grns (grn_number, po_id, po_number, supplier_name, payment_status, storage_location, created_by)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (grn_number, id, po_data['po_number'], po_data['supplier_name'], payment_status, storage_location, session.get('username', 'admin')))

        grn_id = cursor.lastrowid
        total_items = 0
        total_quantity = 0

        for item in data.get('items', []):
            item_id = item['id']
            received_qty = item.get('received_quantity', 0)
            damaged_qty = item.get('damaged_quantity', 0)
            damage_reason = item.get('damage_reason', '')

            if received_qty <= 0 and damaged_qty <= 0:
                continue

            cursor.execute('SELECT * FROM purchase_order_items WHERE id = ?', (item_id,))
            po_item_row = cursor.fetchone()
            if not po_item_row:
                continue

            po_item = dict(po_item_row)

            # Update received quantity (good + damaged)
            total_received = received_qty + damaged_qty
            cursor.execute('''
                UPDATE purchase_order_items 
                SET received_quantity = received_quantity + ?
                WHERE id = ?
            ''', (total_received, item_id))

            # Add to GRN items
            cursor.execute('''
                INSERT INTO grn_items (grn_id, product_id, product_name, quantity_received, quantity_damaged, damage_reason, cost_price)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (grn_id, po_item['product_id'], po_item['product_name'], received_qty, damaged_qty, damage_reason, po_item['cost_price']))

            total_items += 1
            total_quantity += received_qty

            # Record damaged items if any
            if damaged_qty > 0:
                cursor.execute('''
                    INSERT INTO damaged_items (po_id, po_item_id, product_name, quantity, damage_reason)
                    VALUES (?, ?, ?, ?, ?)
                ''', (id, item_id, po_item['product_name'], damaged_qty, damage_reason))
                damaged_count += 1

            # Check if product exists or needs to be created
            if po_item['product_id']:
                # Product exists, update stock
                cursor.execute('SELECT * FROM products WHERE id = ?', (po_item['product_id'],))
                existing_product = cursor.fetchone()

                if existing_product:
                    # Update stock and storage location
                    update_query = 'UPDATE products SET current_stock = current_stock + ?, updated_at = CURRENT_TIMESTAMP'
                    params = [received_qty]

                    if storage_location:
                        update_query += ', storage_location = ?'
                        params.append(storage_location)

                    update_query += ' WHERE id = ?'
                    params.append(po_item['product_id'])

                    cursor.execute(update_query, params)

                    # Record stock movement
                    cursor.execute('''
                        INSERT INTO stock_movements (product_id, type, quantity, reference_type, reference_id, notes)
                        VALUES (?, ?, ?, ?, ?, ?)
                    ''', (po_item['product_id'], 'purchase', received_qty, 'purchase_order', id, 
                          f"Received from PO #{id}"))
                else:
                    # Product was deleted, create new one
                    cursor.execute('''
                        INSERT INTO products (
                            name, category_id, brand_id, model_id, cost_price,
                            selling_price, mrp, current_stock, opening_stock, 
                            storage_location, status
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        po_item['product_name'], po_item['category_id'], po_item['brand_id'],
                        po_item['model_id'], po_item['cost_price'], 
                        round(po_item['cost_price'] * 1.2, 2),
                        round(po_item['cost_price'] * 1.3, 2), 
                        received_qty, received_qty, storage_location, 'active'
                    ))
                    new_product_id = cursor.lastrowid

                    # Update PO item with new product ID
                    cursor.execute('''
                        UPDATE purchase_order_items 
                        SET product_id = ?
                        WHERE id = ?
                    ''', (new_product_id, item_id))

                    # Record stock movement
                    cursor.execute('''
                        INSERT INTO stock_movements (product_id, type, quantity, reference_type, reference_id, notes)
                        VALUES (?, ?, ?, ?, ?, ?)
                    ''', (new_product_id, 'purchase', received_qty, 'purchase_order', id, 
                          f"Initial stock from PO #{id}"))
            else:
                # Create new product
                cursor.execute('''
                    INSERT INTO products (
                        name, category_id, brand_id, model_id, cost_price,
                        selling_price, mrp, current_stock, opening_stock, 
                        storage_location, status
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    po_item['product_name'], po_item['category_id'], po_item['brand_id'],
                    po_item['model_id'], po_item['cost_price'], 
                    round(po_item['cost_price'] * 1.2, 2),
                    round(po_item['cost_price'] * 1.3, 2), 
                    received_qty, received_qty, storage_location, 'active'
                ))
                new_product_id = cursor.lastrowid

                # Update PO item with new product ID
                cursor.execute('''
                    UPDATE purchase_order_items 
                    SET product_id = ?
                    WHERE id = ?
                ''', (new_product_id, item_id))

                # Record stock movement
                cursor.execute('''
                    INSERT INTO stock_movements (product_id, type, quantity, reference_type, reference_id, notes)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (new_product_id, 'purchase', received_qty, 'purchase_order', id, 
                      f"Initial stock from PO #{id}"))

        # Check if all items are fully received
        cursor.execute('''
            SELECT SUM(quantity) as total_qty, SUM(received_quantity) as received_qty
            FROM purchase_order_items WHERE po_id = ?
        ''', (id,))
        totals_row = cursor.fetchone()
        totals = dict(totals_row) if totals_row else {'total_qty': 0, 'received_qty': 0}

        # Update PO status
        if totals['total_qty'] <= totals['received_qty']:
            new_status = 'completed'
        elif totals['received_qty'] > 0:
            new_status = 'partial'
        else:
            new_status = 'pending'

        cursor.execute('''
            UPDATE purchase_orders 
            SET status = ?, payment_status = ?, storage_location = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (new_status, payment_status, storage_location, id))

        # Update GRN totals
        cursor.execute('''
            UPDATE grns 
            SET total_items = ?, total_quantity = ?
            WHERE id = ?
        ''', (total_items, total_quantity, grn_id))

        conn.commit()
        return jsonify({
            'success': True, 
            'message': 'Items received successfully',
            'grn_number': grn_number,
            'grn_id': grn_id,
            'status': new_status,
            'total_qty': totals['total_qty'],
            'received_qty': totals['received_qty'],
            'damaged_count': damaged_count
        })
    except Exception as e:
        conn.rollback()
        return jsonify({'success': False, 'error': str(e)}), 400
    finally:
        conn.close()

@app.route('/api/grns', methods=['GET'])
@login_required
def get_grns():
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute('''
        SELECT * FROM grns 
        ORDER BY created_at DESC
    ''')
    grns = [dict(row) for row in cursor.fetchall()]
    conn.close()

    return jsonify(grns)

@app.route('/api/grns/<int:id>', methods=['GET'])
@login_required
def get_grn_detail(id):
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute('SELECT * FROM grns WHERE id = ?', (id,))
    grn_row = cursor.fetchone()

    if not grn_row:
        conn.close()
        return jsonify({'error': 'GRN not found'}), 404

    grn = dict(grn_row)

    cursor.execute('''
        SELECT gi.*, p.sku, p.brand_id, p.category_id, poi.quantity as ordered_quantity
        FROM grn_items gi
        LEFT JOIN products p ON gi.product_id = p.id
        LEFT JOIN purchase_order_items poi ON gi.product_name = poi.product_name AND poi.po_id = ?
        WHERE gi.grn_id = ?
    ''', (grn['po_id'], id))
    items = [dict(row) for row in cursor.fetchall()]

    grn['items'] = items
    conn.close()

    return jsonify(grn)

@app.route('/api/products/<int:id>/stock-history', methods=['GET'])
@login_required
def get_stock_history(id):
    conn = get_db()
    cursor = conn.cursor()

    # Get product name and opening stock
    cursor.execute('SELECT name, opening_stock FROM products WHERE id = ?', (id,))
    product_row = cursor.fetchone()
    if not product_row:
        conn.close()
        return jsonify({'error': 'Product not found'}), 404

    product_name = product_row['name']
    opening_stock = product_row['opening_stock'] or 0
    
    # Get stock movements with running balance
    cursor.execute('''
        SELECT 
            sm.id,
            sm.type,
            sm.quantity,
            sm.reference_type,
            sm.reference_id,
            sm.notes,
            sm.created_at,
            CASE 
                WHEN sm.reference_type = 'purchase_order' THEN 'PO-' || COALESCE(po.po_number, sm.reference_id)
                WHEN sm.reference_type = 'grn' THEN COALESCE(g.grn_number, 'GRN-' || sm.reference_id)
                WHEN sm.reference_type = 'manual' THEN 'Manual Entry'
                ELSE COALESCE(sm.reference_type, 'System')
            END as reference_number,
            COALESCE(g.created_by, 'System') as received_by
        FROM stock_movements sm
        LEFT JOIN purchase_orders po ON sm.reference_type = 'purchase_order' AND sm.reference_id = po.id
        LEFT JOIN grns g ON sm.reference_type = 'grn' AND sm.reference_id = g.id
        WHERE sm.product_id = ?
        ORDER BY sm.created_at ASC
    ''', (id,))
    
    movements = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    # Calculate running balance starting from opening stock
    running_balance = opening_stock
    history = []
    
    for movement in movements:
        quantity = abs(movement['quantity'])
        
        # Determine if stock is added or removed based on movement type
        if movement['type'] in ['purchase', 'opening_stock', 'adjustment']:
            if movement['quantity'] >= 0:
                stock_added = quantity
                stock_removed = 0
                running_balance += quantity
            else:
                stock_added = 0
                stock_removed = quantity
                running_balance -= quantity
        elif movement['type'] in ['sale', 'return', 'damage']:
            stock_added = 0
            stock_removed = quantity
            running_balance -= quantity
        else:
            # Default handling
            if movement['quantity'] >= 0:
                stock_added = quantity
                stock_removed = 0
                running_balance += quantity
            else:
                stock_added = 0
                stock_removed = quantity
                running_balance -= quantity
        
        history.append({
            'date_time': movement['created_at'],
            'stock_added': stock_added,
            'stock_removed': stock_removed,
            'reference': movement['reference_number'],
            'received_by': movement['received_by'],
            'running_balance': max(0, running_balance)  # Ensure balance doesn't go negative
        })
    
    return jsonify({
        'product_name': product_name,
        'history': history
    })

@app.route('/api/dashboard/stats', methods=['GET'])
@login_required
def dashboard_stats():
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute('SELECT COUNT(*) as count FROM products WHERE status = "active"')
    total_products = cursor.fetchone()['count']

    cursor.execute('SELECT COUNT(*) as count FROM products WHERE current_stock <= min_stock_level AND status = "active"')
    low_stock = cursor.fetchone()['count']

    cursor.execute('SELECT COUNT(*) as count FROM products WHERE current_stock = 0 AND status = "active"')
    out_of_stock = cursor.fetchone()['count']

    cursor.execute('SELECT SUM(current_stock * cost_price) as value FROM products WHERE status = "active"')
    stock_value = cursor.fetchone()['value'] or 0

    cursor.execute('''
        SELECT p.*, c.name as category_name, b.name as brand_name
        FROM products p
        LEFT JOIN categories c ON p.category_id = c.id
        LEFT JOIN brands b ON p.brand_id = b.id
        WHERE p.current_stock <= p.min_stock_level AND p.status = "active"
        ORDER BY p.current_stock ASC
        LIMIT 10
    ''')
    low_stock_items = [dict(row) for row in cursor.fetchall()]

    cursor.execute('''
        SELECT sm.*, p.name as product_name
        FROM stock_movements sm
        LEFT JOIN products p ON sm.product_id = p.id
        ORDER BY sm.created_at DESC
        LIMIT 20
    ''')
    recent_movements = [dict(row) for row in cursor.fetchall()]

    conn.close()

    return jsonify({
        'total_products': total_products,
        'low_stock': low_stock,
        'out_of_stock': out_of_stock,
        'stock_value': round(stock_value, 2),
        'low_stock_items': low_stock_items,
        'recent_movements': recent_movements
    })

@app.route('/api/export/template', methods=['GET'])
@login_required
def export_template():
    format_type = request.args.get('format', 'excel')
    
    # Create template with headers and sample data
    template_data = {
        'sku': ['SKU001', 'SKU002'],
        'name': ['Sample Product 1', 'Sample Product 2'],
        'category_name': ['Smartphones', 'Accessories'],
        'brand_name': ['Apple', 'Samsung'],
        'model_name': ['iPhone 14', 'Galaxy S23'],
        'description': ['Sample description', 'Another description'],
        'cost_price': [500.00, 300.00],
        'selling_price': [650.00, 400.00],
        'mrp': [699.00, 449.00],
        'current_stock': [10, 25],
        'min_stock_level': [5, 10],
        'storage_location': ['A1', 'B2'],
        'imei': ['123456789012345', ''],
        'color': ['Black', 'White'],
        'storage_capacity': ['128GB', '64GB'],
        'ram': ['6GB', '8GB'],
        'warranty_period': ['12 months', '24 months'],
        'supplier_name': ['Supplier A', 'Supplier B'],
        'supplier_contact': ['+1234567890', '+0987654321'],
        'status': ['active', 'active']
    }
    
    df = pd.DataFrame(template_data)
    
    if format_type == 'csv':
        output = io.StringIO()
        df.to_csv(output, index=False)
        output.seek(0)
        return send_file(
            io.BytesIO(output.getvalue().encode()),
            mimetype='text/csv',
            as_attachment=True,
            download_name='product_import_template.csv'
        )
    else:
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Products')
            workbook = writer.book
            worksheet = writer.sheets['Products']
            
            # Add instructions sheet
            instructions = workbook.create_sheet('Instructions')
            instructions['A1'] = 'Product Import Instructions'
            instructions['A3'] = 'Required Fields:'
            instructions['A4'] = '- name: Product name (required)'
            instructions['A6'] = 'Optional Fields:'
            instructions['A7'] = '- sku: Unique product code'
            instructions['A8'] = '- category_name: Product category'
            instructions['A9'] = '- brand_name: Brand name'
            instructions['A10'] = '- model_name: Model name'
            instructions['A11'] = '- cost_price, selling_price, mrp: Prices'
            instructions['A12'] = '- current_stock: Stock quantity'
            instructions['A13'] = '- status: active or inactive'
            
        output.seek(0)
        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name='product_import_template.xlsx'
        )

@app.route('/api/export/products', methods=['GET'])
@login_required
def export_products():
    conn = get_db()
    cursor = conn.cursor()

    format_type = request.args.get('format', 'excel')
    columns_param = request.args.get('columns', '')
    selected_columns = columns_param.split(',') if columns_param else []
    
    # Build query based on filters
    query = '''
        SELECT p.*, c.name as category_name, b.name as brand_name, m.name as model_name
        FROM products p
        LEFT JOIN categories c ON p.category_id = c.id
        LEFT JOIN brands b ON p.brand_id = b.id
        LEFT JOIN models m ON p.model_id = m.id
        WHERE 1=1
    '''
    params = []
    
    # Apply filters
    search = request.args.get('search', '')
    category_id = request.args.get('category_id', '')
    brand_id = request.args.get('brand_id', '')
    status = request.args.get('status', '')
    stock_status = request.args.get('stock_status', '')
    ids = request.args.get('ids', '')
    
    if search:
        query += ' AND (p.name LIKE ? OR p.sku LIKE ?)'
        search_param = f'%{search}%'
        params.extend([search_param, search_param])
    
    if category_id:
        query += ' AND p.category_id = ?'
        params.append(category_id)
    
    if brand_id:
        query += ' AND p.brand_id = ?'
        params.append(brand_id)
    
    if status:
        query += ' AND p.status = ?'
        params.append(status)
    
    if stock_status == 'low':
        query += ' AND p.current_stock <= p.min_stock_level'
    elif stock_status == 'out':
        query += ' AND p.current_stock = 0'
    
    if ids:
        id_list = ids.split(',')
        placeholders = ','.join('?' * len(id_list))
        query += f' AND p.id IN ({placeholders})'
        params.extend(id_list)
    
    query += ' ORDER BY p.name'
    
    cursor.execute(query, params)
    products = [dict(row) for row in cursor.fetchall()]
    conn.close()

    # Filter columns if specified
    if selected_columns:
        column_mapping = {
            'sku': 'sku',
            'name': 'name',
            'category': 'category_name',
            'brand': 'brand_name',
            'model': 'model_name',
            'cost_price': 'cost_price',
            'selling_price': 'selling_price',
            'current_stock': 'current_stock',
            'status': 'status'
        }
        
        filtered_products = []
        for product in products:
            filtered_product = {}
            for col in selected_columns:
                if col in column_mapping:
                    filtered_product[col] = product.get(column_mapping[col], '')
            filtered_products.append(filtered_product)
        products = filtered_products

    df = pd.DataFrame(products)
    
    if format_type == 'csv':
        output = io.StringIO()
        df.to_csv(output, index=False)
        output.seek(0)
        return send_file(
            io.BytesIO(output.getvalue().encode()),
            mimetype='text/csv',
            as_attachment=True,
            download_name=f'products_export_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
        )
    else:
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Products')
        output.seek(0)
        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=f'products_export_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
        )

@app.route('/api/import/products/preview', methods=['POST'])
@login_required
def import_products_preview():
    if 'file' not in request.files:
        return jsonify({'success': False, 'error': 'No file provided'}), 400

    file = request.files['file']
    first_row_headers = request.form.get('first_row_headers', 'true') == 'true'

    try:
        if file.filename.endswith('.csv'):
            df = pd.read_csv(file)
        else:
            df = pd.read_excel(file)

        total_rows = len(df)
        preview_rows = df.head(3).fillna('').to_dict('records')
        columns = list(df.columns)
        
        # Basic validation
        errors = []
        valid_count = 0
        
        for index, row in df.iterrows():
            row_errors = []
            
            if pd.isna(row.get('name')) or str(row.get('name')).strip() == '':
                row_errors.append(f"Row {index + 2}: Product name is required")
            else:
                valid_count += 1
            
            if row_errors:
                errors.extend(row_errors)
        
        return jsonify({
            'success': True,
            'total_rows': total_rows,
            'preview_rows': preview_rows,
            'columns': columns,
            'validation': {
                'valid_count': valid_count,
                'error_count': len(errors),
                'errors': errors[:50]  # Return first 50 errors
            }
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/api/export/grns', methods=['GET'])
@login_required
def export_grns():
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute('''
        SELECT 
            g.grn_number,
            g.po_number,
            g.supplier_name,
            g.received_date,
            g.total_items,
            g.total_quantity,
            g.payment_status,
            g.storage_location,
            g.created_by,
            gi.product_name,
            gi.quantity_received,
            gi.quantity_damaged,
            gi.damage_reason,
            gi.cost_price,
            (gi.quantity_received * gi.cost_price) as line_total
        FROM grns g
        LEFT JOIN grn_items gi ON g.id = gi.grn_id
        ORDER BY g.received_date DESC, g.grn_number
    ''')
    
    grn_data = [dict(row) for row in cursor.fetchall()]
    conn.close()

    df = pd.DataFrame(grn_data)
    
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='GRN Report')
        
        workbook = writer.book
        worksheet = writer.sheets['GRN Report']
        
        # Auto-adjust column widths
        for column in worksheet.columns:
            max_length = 0
            column_letter = column[0].column_letter
            for cell in column:
                try:
                    if len(str(cell.value)) > max_length:
                        max_length = len(str(cell.value))
                except:
                    pass
            adjusted_width = min(max_length + 2, 50)
            worksheet.column_dimensions[column_letter].width = adjusted_width
    
    output.seek(0)
    return send_file(
        output,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name=f'grn_report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
    )

@app.route('/api/import/products', methods=['POST'])
@login_required
def import_products():
    if 'file' not in request.files:
        return jsonify({'success': False, 'error': 'No file provided'}), 400

    file = request.files['file']
    first_row_headers = request.form.get('first_row_headers', 'true') == 'true'
    update_existing = request.form.get('update_existing', 'false') == 'true'
    skip_errors = request.form.get('skip_errors', 'true') == 'true'
    auto_create = request.form.get('auto_create', 'true') == 'true'

    try:
        if file.filename.endswith('.csv'):
            df = pd.read_csv(file)
        else:
            df = pd.read_excel(file)

        conn = get_db()
        cursor = conn.cursor()

        imported = 0
        updated = 0
        errors = []
        created_categories = 0
        created_brands = 0
        created_models = 0
        category_cache = {}
        brand_cache = {}
        model_cache = {}

        for index, row in df.iterrows():
            try:
                # Validate required fields
                if pd.isna(row.get('name')) or str(row.get('name')).strip() == '':
                    if skip_errors:
                        errors.append(f"Row {index + 2}: Missing product name - skipped")
                        continue
                    else:
                        raise ValueError("Product name is required")

                # Auto-create category if needed (support both 'category' and 'category_name' columns)
                category_id = None
                category_name = row.get('category') or row.get('category_name')
                if auto_create and not pd.isna(category_name):
                    category_name = str(category_name).strip()
                    if category_name:
                        if category_name in category_cache:
                            category_id = category_cache[category_name]
                        else:
                            cursor.execute('SELECT id FROM categories WHERE name = ?', (category_name,))
                            existing = cursor.fetchone()
                            if existing:
                                category_id = existing['id']
                            else:
                                cursor.execute('INSERT INTO categories (name) VALUES (?)', (category_name,))
                                category_id = cursor.lastrowid
                                created_categories += 1
                            category_cache[category_name] = category_id

                # Auto-create brand if needed (support both 'brand' and 'brand_name' columns)
                brand_id = None
                brand_name = row.get('brand') or row.get('brand_name')
                if auto_create and not pd.isna(brand_name):
                    brand_name = str(brand_name).strip()
                    if brand_name:
                        if brand_name in brand_cache:
                            brand_id = brand_cache[brand_name]
                        else:
                            cursor.execute('SELECT id FROM brands WHERE name = ?', (brand_name,))
                            existing = cursor.fetchone()
                            if existing:
                                brand_id = existing['id']
                            else:
                                cursor.execute('INSERT INTO brands (name) VALUES (?)', (brand_name,))
                                brand_id = cursor.lastrowid
                                created_brands += 1
                            brand_cache[brand_name] = brand_id

                # Auto-create model if needed (support both 'model' and 'model_name' columns)
                model_id = None
                model_name = row.get('model') or row.get('model_name')
                if auto_create and not pd.isna(model_name) and brand_id:
                    model_name = str(model_name).strip()
                    if model_name:
                        cache_key = f"{brand_id}_{model_name}"
                        if cache_key in model_cache:
                            model_id = model_cache[cache_key]
                        else:
                            cursor.execute('SELECT id FROM models WHERE name = ? AND brand_id = ?', (model_name, brand_id))
                            existing = cursor.fetchone()
                            if existing:
                                model_id = existing['id']
                            else:
                                cursor.execute('INSERT INTO models (name, brand_id) VALUES (?, ?)', (model_name, brand_id))
                                model_id = cursor.lastrowid
                                created_models += 1
                            model_cache[cache_key] = model_id

                # Check if product exists by SKU
                existing_product = None
                if update_existing and not pd.isna(row.get('sku')):
                    cursor.execute('SELECT id FROM products WHERE sku = ?', (row.get('sku'),))
                    existing_product = cursor.fetchone()

                if existing_product:
                    # Update existing product
                    cursor.execute('''
                        UPDATE products SET
                            name = ?, category_id = ?, brand_id = ?, model_id = ?, description = ?,
                            cost_price = ?, selling_price = ?, mrp = ?,
                            current_stock = ?, min_stock_level = ?, status = ?,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE id = ?
                    ''', (
                        row.get('name'), category_id, brand_id, model_id,
                        row.get('description', ''),
                        float(row.get('cost_price', 0) or 0),
                        float(row.get('selling_price', 0) or 0),
                        float(row.get('mrp', 0) or 0),
                        int(row.get('current_stock', 0) or 0),
                        int(row.get('min_stock_level', 10) or 10),
                        row.get('status', 'active'),
                        existing_product['id']
                    ))
                    updated += 1
                else:
                    # Insert new product
                    cursor.execute('''
                        INSERT INTO products (
                            sku, name, category_id, brand_id, model_id, description,
                            cost_price, selling_price, mrp, current_stock, opening_stock,
                            min_stock_level, storage_location, imei, color,
                            storage_capacity, ram, warranty_period, supplier_name,
                            supplier_contact, status
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        row.get('sku'), row.get('name'), category_id, brand_id, model_id,
                        row.get('description', ''),
                        float(row.get('cost_price', 0) or 0),
                        float(row.get('selling_price', 0) or 0),
                        float(row.get('mrp', 0) or 0),
                        int(row.get('current_stock', 0) or 0),
                        int(row.get('current_stock', 0) or 0),
                        int(row.get('min_stock_level', 10) or 10),
                        row.get('storage_location', ''),
                        row.get('imei', ''),
                        row.get('color', ''),
                        row.get('storage_capacity', ''),
                        row.get('ram', ''),
                        row.get('warranty_period', ''),
                        row.get('supplier_name', ''),
                        row.get('supplier_contact', ''),
                        row.get('status', 'active')
                    ))
                    imported += 1

            except Exception as e:
                error_msg = f"Row {index + 2}: {str(e)}"
                if skip_errors:
                    errors.append(error_msg)
                else:
                    conn.rollback()
                    conn.close()
                    return jsonify({'success': False, 'error': error_msg}), 400

        conn.commit()
        conn.close()

        return jsonify({
            'success': True,
            'imported': imported,
            'updated': updated,
            'created_categories': created_categories,
            'created_brands': created_brands,
            'created_models': created_models,
            'errors': errors
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=5000, debug=True)