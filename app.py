from flask import Flask, render_template, request, jsonify, send_file, session, redirect, url_for
from functools import wraps
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

def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    cursor = conn.cursor()
    
    # Migration: Add payment_status and storage_location to purchase_orders if they don't exist
    cursor.execute("PRAGMA table_info(purchase_orders)")
    columns = [col[1] for col in cursor.fetchall()]
    if 'payment_status' not in columns:
        cursor.execute('ALTER TABLE purchase_orders ADD COLUMN payment_status TEXT DEFAULT "unpaid"')
    if 'storage_location' not in columns:
        cursor.execute('ALTER TABLE purchase_orders ADD COLUMN storage_location TEXT')
    
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
        data = request.json
        try:
            cursor.execute('INSERT INTO models (name, brand_id, description) VALUES (?, ?, ?)',
                         (data['name'], data['brand_id'], data.get('description', '')))
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
        data = request.json
        try:
            cursor.execute('UPDATE models SET name = ?, brand_id = ?, description = ? WHERE id = ?',
                         (data['name'], data['brand_id'], data.get('description', ''), id))
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
        
        for item in data.get('items', []):
            item_id = item['id']
            received_qty = item['received_quantity']
            
            cursor.execute('SELECT * FROM purchase_order_items WHERE id = ?', (item_id,))
            po_item = dict(cursor.fetchone())
            
            cursor.execute('''
                UPDATE purchase_order_items 
                SET received_quantity = received_quantity + ?
                WHERE id = ?
            ''', (received_qty, item_id))
            
            if po_item['product_id']:
                # Update product stock and optionally set storage location
                if storage_location:
                    cursor.execute('''
                        UPDATE products 
                        SET current_stock = current_stock + ?, storage_location = ?
                        WHERE id = ?
                    ''', (received_qty, storage_location, po_item['product_id']))
                else:
                    cursor.execute('''
                        UPDATE products 
                        SET current_stock = current_stock + ?
                        WHERE id = ?
                    ''', (received_qty, po_item['product_id']))
                
                cursor.execute('''
                    INSERT INTO stock_movements (product_id, type, quantity, reference_type, reference_id, notes)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (po_item['product_id'], 'purchase', received_qty, 'purchase_order', id, f"Received from PO {po_item['po_id']}"))
            else:
                cursor.execute('''
                    INSERT INTO products (
                        name, category_id, brand_id, model_id, cost_price,
                        selling_price, mrp, current_stock, opening_stock, 
                        storage_location, status
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    po_item['product_name'], po_item['category_id'], po_item['brand_id'],
                    po_item['model_id'], po_item['cost_price'], po_item['cost_price'] * 1.2,
                    po_item['cost_price'] * 1.3, received_qty, 0, storage_location, 'active'
                ))
                new_product_id = cursor.lastrowid
                
                cursor.execute('''
                    UPDATE purchase_order_items 
                    SET product_id = ?
                    WHERE id = ?
                ''', (new_product_id, item_id))
                
                cursor.execute('''
                    INSERT INTO stock_movements (product_id, type, quantity, reference_type, reference_id, notes)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (new_product_id, 'purchase', received_qty, 'purchase_order', id, f"Initial stock from PO"))
        
        cursor.execute('''
            SELECT SUM(quantity) as total_qty, SUM(received_quantity) as received_qty
            FROM purchase_order_items WHERE po_id = ?
        ''', (id,))
        totals = dict(cursor.fetchone())
        
        if totals['total_qty'] == totals['received_qty']:
            cursor.execute('''
                UPDATE purchase_orders 
                SET status = ?, payment_status = ?, storage_location = ?
                WHERE id = ?
            ''', ('completed', payment_status, storage_location, id))
        else:
            cursor.execute('''
                UPDATE purchase_orders 
                SET status = ?, payment_status = ?, storage_location = ?
                WHERE id = ?
            ''', ('partial', payment_status, storage_location, id))
        
        conn.commit()
        return jsonify({'success': True})
    except Exception as e:
        conn.rollback()
        return jsonify({'success': False, 'error': str(e)}), 400
    finally:
        conn.close()

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

@app.route('/api/export/products', methods=['GET'])
@login_required
def export_products():
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT p.*, c.name as category_name, b.name as brand_name, m.name as model_name
        FROM products p
        LEFT JOIN categories c ON p.category_id = c.id
        LEFT JOIN brands b ON p.brand_id = b.id
        LEFT JOIN models m ON p.model_id = m.id
        ORDER BY p.name
    ''')
    products = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    df = pd.DataFrame(products)
    
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

@app.route('/api/import/products', methods=['POST'])
@login_required
def import_products():
    if 'file' not in request.files:
        return jsonify({'success': False, 'error': 'No file provided'}), 400
    
    file = request.files['file']
    
    try:
        if file.filename.endswith('.csv'):
            df = pd.read_csv(file)
        else:
            df = pd.read_excel(file)
        
        conn = get_db()
        cursor = conn.cursor()
        
        imported = 0
        errors = []
        
        for index, row in df.iterrows():
            try:
                cursor.execute('''
                    INSERT INTO products (
                        sku, name, category_id, brand_id, model_id, description,
                        cost_price, selling_price, mrp, current_stock, min_stock_level, status
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    row.get('sku'), row.get('name'), row.get('category_id'),
                    row.get('brand_id'), row.get('model_id'), row.get('description'),
                    row.get('cost_price', 0), row.get('selling_price', 0),
                    row.get('mrp', 0), row.get('current_stock', 0),
                    row.get('min_stock_level', 10), row.get('status', 'active')
                ))
                imported += 1
            except Exception as e:
                errors.append(f"Row {index + 1}: {str(e)}")
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'imported': imported,
            'errors': errors
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=5000, debug=True)
