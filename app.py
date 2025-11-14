from flask import Flask, render_template, request, jsonify, send_file, session, redirect, url_for, send_from_directory
from functools import wraps
from werkzeug.utils import secure_filename
import sqlite3
import json
from datetime import datetime
import pandas as pd
import io
import os
import hashlib
import time
import bcrypt # Import bcrypt

# Import authentication and user route modules
from auth import login_required, authenticate_user, log_audit
from user_routes import user_bp

app = Flask(__name__, static_folder='static', static_url_path='/static')
app.config['SECRET_KEY'] = os.environ.get('SESSION_SECRET', 'dev-secret-key-change-in-production')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['SESSION_COOKIE_SECURE'] = os.environ.get('FLASK_ENV') == 'production'
app.config['UPLOAD_FOLDER'] = 'static/uploads/models'
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0  # Disable caching during development

# Add proper CSP headers
@app.after_request
def add_security_headers(response):
    response.headers['Content-Security-Policy'] = "default-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdn.jsdelivr.net https://code.jquery.com https://cdn.datatables.net https://via.placeholder.com; img-src 'self' data: https: blob:; script-src 'self' 'unsafe-inline' 'unsafe-eval' https://code.jquery.com https://cdn.jsdelivr.net https://cdn.datatables.net; style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://cdn.datatables.net;"
    # Disable cache during development
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, post-check=0, pre-check=0, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '-1'
    return response

@app.route('/static/<path:filename>')
def serve_static(filename):
    return send_from_directory('static', filename)

# Create upload folder if it doesn't exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs('static/css', exist_ok=True)
os.makedirs('static/js', exist_ok=True)

DATABASE = 'inventory.db'
ADMIN_USERNAME = 'admin'
ADMIN_PASSWORD_HASH = hashlib.sha256('admin123'.encode()).hexdigest()

# Register user management blueprint
app.register_blueprint(user_bp)

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
    """Initialize the database and create tables if they don't exist"""
    conn = get_db()
    cursor = conn.cursor()

    # Check and add sold_date column to product_imei if it doesn't exist
    cursor.execute("PRAGMA table_info(product_imei)")
    columns = [column[1] for column in cursor.fetchall()]
    if 'sold_date' not in columns and columns:  # Only if table exists
        try:
            cursor.execute('ALTER TABLE product_imei ADD COLUMN sold_date TIMESTAMP')
            conn.commit()
        except sqlite3.OperationalError:
            pass

    # Check and add sale_id column to product_imei if it doesn't exist
    if columns and 'sale_id' not in columns:
        try:
            cursor.execute('ALTER TABLE product_imei ADD COLUMN sale_id INTEGER')
            conn.commit()
        except sqlite3.OperationalError:
            pass

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

    # Add image_data column if it doesn't exist (migration)
    cursor.execute("PRAGMA table_info(models)")
    columns = [column[1] for column in cursor.fetchall()]
    if 'image_data' not in columns:
        try:
            cursor.execute('ALTER TABLE models ADD COLUMN image_data TEXT')
            conn.commit()
        except sqlite3.OperationalError as e:
            print(f"Migration warning: {e}")
            pass

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

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS quick_orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_number TEXT UNIQUE NOT NULL,
            order_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            total_items INTEGER DEFAULT 0,
            total_amount REAL DEFAULT 0,
            notes TEXT,
            created_by TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS quick_order_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            product_name TEXT NOT NULL,
            quantity INTEGER NOT NULL,
            unit_price REAL NOT NULL,
            total_price REAL NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (order_id) REFERENCES quick_orders (id),
            FOREIGN KEY (product_id) REFERENCES products (id)
        )
    ''')

    # POS Sales Tables
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS pos_sales (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sale_number TEXT UNIQUE NOT NULL,
            customer_name TEXT,
            customer_phone TEXT,
            customer_email TEXT,
            sale_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            subtotal REAL DEFAULT 0,
            discount_amount REAL DEFAULT 0,
            discount_percentage REAL DEFAULT 0,
            tax_amount REAL DEFAULT 0,
            tax_percentage REAL DEFAULT 0,
            total_amount REAL DEFAULT 0,
            payment_method TEXT,
            payment_status TEXT DEFAULT 'paid',
            transaction_type TEXT DEFAULT 'sale',
            original_sale_id INTEGER,
            notes TEXT,
            cashier_name TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (original_sale_id) REFERENCES pos_sales (id)
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS pos_sale_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sale_id INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            product_name TEXT NOT NULL,
            sku TEXT,
            quantity INTEGER NOT NULL,
            unit_price REAL NOT NULL,
            discount REAL DEFAULT 0,
            tax REAL DEFAULT 0,
            total_price REAL NOT NULL,
            imei TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (sale_id) REFERENCES pos_sales (id),
            FOREIGN KEY (product_id) REFERENCES products (id)
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS pos_payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sale_id INTEGER NOT NULL,
            payment_method TEXT NOT NULL,
            amount REAL NOT NULL,
            reference_number TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (sale_id) REFERENCES pos_sales (id)
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS product_imei (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER NOT NULL,
            imei TEXT UNIQUE NOT NULL,
            status TEXT DEFAULT 'available',
            grn_id INTEGER,
            stock_movement_id INTEGER,
            received_date TIMESTAMP,
            sale_id INTEGER,
            sold_date TIMESTAMP,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (product_id) REFERENCES products (id),
            FOREIGN KEY (grn_id) REFERENCES grns (id),
            FOREIGN KEY (stock_movement_id) REFERENCES stock_movements (id),
            FOREIGN KEY (sale_id) REFERENCES pos_sales (id)
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS customers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            phone TEXT UNIQUE,
            email TEXT,
            address TEXT,
            city TEXT,
            state TEXT,
            pincode TEXT,
            gstin TEXT,
            notes TEXT,
            status TEXT DEFAULT 'active',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS business_settings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            business_name TEXT,
            gstin TEXT,
            address TEXT,
            city TEXT,
            state TEXT,
            pincode TEXT,
            country TEXT,
            phone TEXT,
            email TEXT,
            website TEXT,
            logo_url TEXT,
            currency TEXT DEFAULT 'INR',
            tax_label TEXT DEFAULT 'GST',
            invoice_prefix TEXT DEFAULT 'INV',
            receipt_prefix TEXT DEFAULT 'RCP',
            terms_conditions TEXT,
            bank_name TEXT,
            bank_account_number TEXT,
            bank_ifsc TEXT,
            bank_branch TEXT,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Insert default business settings if not exists
    cursor.execute('SELECT COUNT(*) as count FROM business_settings')
    if cursor.fetchone()['count'] == 0:
        cursor.execute('''
            INSERT INTO business_settings (business_name, currency, tax_label)
            VALUES (?, ?, ?)
        ''', ('My Business', 'INR', 'GST'))

    # Service Management Tables
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS technicians (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            phone TEXT,
            email TEXT,
            specialization TEXT,
            status TEXT DEFAULT 'active',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS service_jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_number TEXT UNIQUE NOT NULL,
            customer_name TEXT NOT NULL,
            customer_phone TEXT NOT NULL,
            customer_email TEXT,
            device_brand TEXT,
            device_model TEXT,
            imei_number TEXT,
            problem_description TEXT NOT NULL,
            estimated_cost REAL DEFAULT 0,
            actual_cost REAL DEFAULT 0,
            advance_payment REAL DEFAULT 0,
            estimated_delivery DATE,
            actual_delivery DATE,
            status TEXT DEFAULT 'received',
            technician_id INTEGER,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (technician_id) REFERENCES technicians (id)
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS service_parts_used (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_id INTEGER NOT NULL,
            product_id INTEGER,
            part_name TEXT NOT NULL,
            quantity INTEGER NOT NULL,
            unit_price REAL NOT NULL,
            total_price REAL NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (job_id) REFERENCES service_jobs (id),
            FOREIGN KEY (product_id) REFERENCES products (id)
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS service_labor_charges (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_id INTEGER NOT NULL,
            description TEXT NOT NULL,
            amount REAL NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (job_id) REFERENCES service_jobs (id)
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS service_status_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_id INTEGER NOT NULL,
            old_status TEXT,
            new_status TEXT NOT NULL,
            notes TEXT,
            changed_by TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (job_id) REFERENCES service_jobs (id)
        )
    ''')

    # User Management Tables
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS roles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            description TEXT
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS permissions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            description TEXT
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS role_permissions (
            role_id INTEGER NOT NULL,
            permission_id INTEGER NOT NULL,
            PRIMARY KEY (role_id, permission_id),
            FOREIGN KEY (role_id) REFERENCES roles (id) ON DELETE CASCADE,
            FOREIGN KEY (permission_id) REFERENCES permissions (id) ON DELETE CASCADE
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL,
            full_name TEXT,
            email TEXT UNIQUE,
            role_id INTEGER,
            is_active INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (role_id) REFERENCES roles (id)
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS audit_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            action TEXT NOT NULL,
            target_type TEXT,
            target_id INTEGER,
            details TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')

    # Insert default roles and permissions if they don't exist
    default_roles = [('Admin', 'Administrator role with full access'),
                     ('Manager', 'Manager role with access to reports and inventory management'),
                     ('Staff', 'Staff role with access to POS and basic inventory operations')]
    default_permissions = [('manage_users', 'Ability to create, update, and delete users'),
                           ('view_reports', 'Ability to view all reports'),
                           ('manage_inventory', 'Ability to add, edit, and delete inventory items'),
                           ('process_sales', 'Ability to process sales and returns')]

    for name, description in default_roles:
        cursor.execute('INSERT OR IGNORE INTO roles (name, description) VALUES (?, ?)', (name, description))

    for name, description in default_permissions:
        cursor.execute('INSERT OR IGNORE INTO permissions (name, description) VALUES (?, ?)', (name, description))

    # Link permissions to roles (example: Admin gets all, Manager gets reports and inventory, Staff gets sales)
    # Get IDs
    cursor.execute('SELECT id FROM roles WHERE name = ?', ('Admin',))
    admin_role_id = cursor.fetchone()['id']
    cursor.execute('SELECT id FROM roles WHERE name = ?', ('Manager',))
    manager_role_id = cursor.fetchone()['id']
    cursor.execute('SELECT id FROM roles WHERE name = ?', ('Staff',))
    staff_role_id = cursor.fetchone()['id']

    cursor.execute('SELECT id FROM permissions WHERE name = ?', ('manage_users',))
    perm_manage_users_id = cursor.fetchone()['id']
    cursor.execute('SELECT id FROM permissions WHERE name = ?', ('view_reports',))
    perm_view_reports_id = cursor.fetchone()['id']
    cursor.execute('SELECT id FROM permissions WHERE name = ?', ('manage_inventory',))
    perm_manage_inventory_id = cursor.fetchone()['id']
    cursor.execute('SELECT id FROM permissions WHERE name = ?', ('process_sales',))
    perm_process_sales_id = cursor.fetchone()['id']

    # Admin: All permissions
    cursor.execute('SELECT id FROM permissions')
    all_perm_ids = [p['id'] for p in cursor.fetchall()]
    for perm_id in all_perm_ids:
        cursor.execute('INSERT OR IGNORE INTO role_permissions (role_id, permission_id) VALUES (?, ?)', (admin_role_id, perm_id))

    # Manager: Reports and Inventory
    cursor.execute('INSERT OR IGNORE INTO role_permissions (role_id, permission_id) VALUES (?, ?)', (manager_role_id, perm_view_reports_id))
    cursor.execute('INSERT OR IGNORE INTO role_permissions (role_id, permission_id) VALUES (?, ?)', (manager_role_id, perm_manage_inventory_id))

    # Staff: Sales
    cursor.execute('INSERT OR IGNORE INTO role_permissions (role_id, permission_id) VALUES (?, ?)', (staff_role_id, perm_process_sales_id))

    # Insert default admin user if not exists
    cursor.execute('SELECT COUNT(*) as count FROM users WHERE username = ?', (ADMIN_USERNAME,))
    if cursor.fetchone()['count'] == 0:
        hashed_password = bcrypt.hashpw(b'admin123', bcrypt.gensalt()) # Hash password using bcrypt
        cursor.execute('SELECT id FROM roles WHERE name = ?', ('Admin',))
        admin_role = cursor.fetchone()
        if admin_role:
            cursor.execute('INSERT INTO users (username, password, full_name, email, role_id, is_active) VALUES (?, ?, ?, ?, ?, ?)',
                           (ADMIN_USERNAME, hashed_password.decode('utf-8'), 'Administrator', 'admin@example.com', admin_role['id'], 1))

    conn.commit()
    conn.close()

# Initialize database automatically when app starts
init_db()

@app.route('/')
def index():
    return render_template('index.html', timestamp=int(time.time()))

@app.route('/pos')
def pos_page():
    return render_template('pos.html', timestamp=int(time.time()))


# Update login endpoint to use enhanced authentication
@app.route('/api/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    user, error = authenticate_user(username, password)

    if error:
        log_audit(user_id=None, action='login_failed', details=f"Failed login attempt for username: {username}. Reason: {error}")
        return jsonify({'error': error}), 401

    session['user_id'] = user['id']
    session['username'] = user['username']
    session['role_name'] = user['role_name']
    session['logged_in'] = True # Set logged_in flag

    log_audit(user_id=user['id'], action='login_success', details=f"User {username} logged in successfully.")

    return jsonify({
        'success': True,
        'username': user['username'],
        'role': user['role_name']
    })

@app.route('/api/logout', methods=['POST'])
def logout():
    username = session.get('username', 'Unknown User')
    user_id = session.get('user_id')
    log_audit(user_id=user_id, action='logout', details=f"User {username} logged out.")
    session.clear()
    return jsonify({'success': True})

@app.route('/api/check-auth', methods=['GET'])
def check_auth():
    return jsonify({'logged_in': session.get('logged_in', False), 'username': session.get('username'), 'role': session.get('role_name')})

@app.route('/api/categories', methods=['GET', 'POST'])
@login_required
def categories():
    conn = get_db()
    cursor = conn.cursor()

    if request.method == 'POST':
        data = request.json
        if not data or 'name' not in data or not data['name'].strip():
            conn.close()
            return jsonify({'success': False, 'error': 'Category name is required'}), 400

        try:
            cursor.execute('INSERT INTO categories (name, description) VALUES (?, ?)',
                         (data['name'].strip(), data.get('description', '').strip()))
            conn.commit()
            category_id = cursor.lastrowid
            log_audit(user_id=session.get('user_id'), action='create_category', target_type='category', target_id=category_id, details=f"Created category: {data['name']}")
            conn.close()
            return jsonify({'success': True, 'id': category_id})
        except sqlite3.IntegrityError:
            conn.close()
            return jsonify({'success': False, 'error': 'Category already exists'}), 400
        except Exception as e:
            conn.close()
            return jsonify({'success': False, 'error': str(e)}), 500
    else:
        try:
            cursor.execute('SELECT * FROM categories ORDER BY name')
            categories = [dict(row) for row in cursor.fetchall()]
            conn.close()
            return jsonify(categories)
        except Exception as e:
            conn.close()
            return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/categories/<int:id>', methods=['PUT', 'DELETE'])
@login_required
def category_detail(id):
    conn = get_db()
    cursor = conn.cursor()

    if request.method == 'PUT':
        data = request.json
        if not data:
            conn.close()
            return jsonify({'success': False, 'error': 'Invalid request data'}), 400
        try:
            # Get old name for audit log
            cursor.execute('SELECT name FROM categories WHERE id = ?', (id,))
            old_name = cursor.fetchone()['name']

            cursor.execute('UPDATE categories SET name = ?, description = ? WHERE id = ?',
                         (data['name'], data.get('description', ''), id))
            conn.commit()
            log_audit(user_id=session.get('user_id'), action='update_category', target_type='category', target_id=id, details=f"Updated category from '{old_name}' to '{data['name']}'")
            return jsonify({'success': True})
        except sqlite3.IntegrityError:
            return jsonify({'success': False, 'error': 'Category name already exists'}), 400
        finally:
            conn.close()
    elif request.method == 'DELETE':
        try:
            # Check if category is in use
            cursor.execute('SELECT COUNT(*) as count FROM products WHERE category_id = ?', (id,))
            if cursor.fetchone()['count'] > 0:
                return jsonify({'success': False, 'error': 'Cannot delete category with associated products'}), 400

            cursor.execute('SELECT name FROM categories WHERE id = ?', (id,))
            category_name = cursor.fetchone()['name']

            cursor.execute('DELETE FROM categories WHERE id = ?', (id,))
            conn.commit()
            log_audit(user_id=session.get('user_id'), action='delete_category', target_type='category', target_id=id, details=f"Deleted category: {category_name}")
            return jsonify({'success': True})
        except sqlite3.IntegrityError: # Should not happen due to check above, but good practice
            return jsonify({'success': False, 'error': 'Cannot delete category due to dependencies'}), 400
        finally:
            conn.close()

    conn.close()
    return jsonify({'success': False, 'error': 'Method not allowed'}), 405

@app.route('/api/brands', methods=['GET', 'POST'])
@login_required
def brands():
    conn = get_db()
    cursor = conn.cursor()

    if request.method == 'POST':
        data = request.json
        if not data or 'name' not in data or not data['name'].strip():
            conn.close()
            return jsonify({'success': False, 'error': 'Brand name is required'}), 400

        try:
            cursor.execute('INSERT INTO brands (name, description) VALUES (?, ?)',
                         (data['name'].strip(), data.get('description', '').strip()))
            conn.commit()
            brand_id = cursor.lastrowid
            log_audit(user_id=session.get('user_id'), action='create_brand', target_type='brand', target_id=brand_id, details=f"Created brand: {data['name']}")
            conn.close()
            return jsonify({'success': True, 'id': brand_id})
        except sqlite3.IntegrityError:
            conn.close()
            return jsonify({'success': False, 'error': 'Brand already exists'}), 400
        except Exception as e:
            conn.close()
            return jsonify({'success': False, 'error': str(e)}), 500
    else:
        try:
            cursor.execute('SELECT * FROM brands ORDER BY name')
            brands = [dict(row) for row in cursor.fetchall()]
            conn.close()
            return jsonify(brands)
        except Exception as e:
            conn.close()
            return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/brands/<int:id>', methods=['PUT', 'DELETE'])
@login_required
def brand_detail(id):
    conn = get_db()
    cursor = conn.cursor()

    if request.method == 'PUT':
        data = request.json
        if not data:
            conn.close()
            return jsonify({'success': False, 'error': 'Invalid request data'}), 400
        try:
            # Get old name for audit log
            cursor.execute('SELECT name FROM brands WHERE id = ?', (id,))
            old_name = cursor.fetchone()['name']

            cursor.execute('UPDATE brands SET name = ?, description = ? WHERE id = ?',
                         (data['name'], data.get('description', ''), id))
            conn.commit()
            log_audit(user_id=session.get('user_id'), action='update_brand', target_type='brand', target_id=id, details=f"Updated brand from '{old_name}' to '{data['name']}'")
            return jsonify({'success': True})
        except sqlite3.IntegrityError:
            return jsonify({'success': False, 'error': 'Brand name already exists'}), 400
        finally:
            conn.close()
    elif request.method == 'DELETE':
        try:
            # Check if brand is in use
            cursor.execute('SELECT COUNT(*) as count FROM products WHERE brand_id = ?', (id,))
            if cursor.fetchone()['count'] > 0:
                return jsonify({'success': False, 'error': 'Cannot delete brand with associated products'}), 400

            cursor.execute('SELECT name FROM brands WHERE id = ?', (id,))
            brand_name = cursor.fetchone()['name']

            cursor.execute('DELETE FROM brands WHERE id = ?', (id,))
            conn.commit()
            log_audit(user_id=session.get('user_id'), action='delete_brand', target_type='brand', target_id=id, details=f"Deleted brand: {brand_name}")
            return jsonify({'success': True})
        except sqlite3.IntegrityError: # Should not happen due to check above
            return jsonify({'success': False, 'error': 'Cannot delete brand due to dependencies'}), 400
        finally:
            conn.close()

    conn.close()
    return jsonify({'success': False, 'error': 'Method not allowed'}), 405

@app.route('/api/models', methods=['GET', 'POST'])
@login_required
def models():
    conn = get_db()
    cursor = conn.cursor()

    if request.method == 'POST':
        try:
            data = request.json
            if not data:
                conn.close()
                return jsonify({'success': False, 'error': 'Invalid request data'}), 400

            name = data.get('name')
            brand_id = data.get('brand_id')
            description = data.get('description', '')
            image_data = data.get('image_data', '')

            # Validate that name and brand_id are provided
            if not name or not brand_id:
                return jsonify({'success': False, 'error': 'Name and brand are required'}), 400

            cursor.execute('INSERT INTO models (name, brand_id, description, image_data) VALUES (?, ?, ?, ?)',
                         (name, brand_id, description, image_data))
            conn.commit()
            model_id = cursor.lastrowid
            log_audit(user_id=session.get('user_id'), action='create_model', target_type='model', target_id=model_id, details=f"Created model: {name} for brand ID: {brand_id}")
            return jsonify({'success': True, 'id': model_id})
        except sqlite3.IntegrityError:
            return jsonify({'success': False, 'error': 'Model already exists for this brand'}), 400
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 400
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
            if not data:
                conn.close()
                return jsonify({'success': False, 'error': 'Invalid request data'}), 400

            name = data.get('name')
            brand_id = data.get('brand_id')
            description = data.get('description', '')
            image_data = data.get('image_data', '')

            # Validate that name and brand_id are provided
            if not name or not brand_id:
                return jsonify({'success': False, 'error': 'Name and brand are required'}), 400

            # Get old data for audit log
            cursor.execute('SELECT name, brand_id FROM models WHERE id = ?', (id,))
            old_model = cursor.fetchone()
            if not old_model:
                return jsonify({'success': False, 'error': 'Model not found'}), 404

            cursor.execute('UPDATE models SET name = ?, brand_id = ?, description = ?, image_data = ? WHERE id = ?',
                         (name, brand_id, description, image_data, id))
            conn.commit()
            log_audit(user_id=session.get('user_id'), action='update_model', target_type='model', target_id=id, details=f"Updated model '{old_model['name']}' (Brand ID: {old_model['brand_id']}) to '{name}' (Brand ID: {brand_id})")
            return jsonify({'success': True})
        except sqlite3.IntegrityError:
            return jsonify({'success': False, 'error': 'Model already exists for this brand'}), 400
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 400
        finally:
            conn.close()
    elif request.method == 'DELETE':
        try:
            # Check if model is in use
            cursor.execute('SELECT COUNT(*) as count FROM products WHERE model_id = ?', (id,))
            if cursor.fetchone()['count'] > 0:
                return jsonify({'success': False, 'error': 'Cannot delete model with associated products'}), 400

            cursor.execute('SELECT name, brand_id FROM models WHERE id = ?', (id,))
            model = cursor.fetchone()
            if not model:
                return jsonify({'success': False, 'error': 'Model not found'}), 404

            cursor.execute('DELETE FROM models WHERE id = ?', (id,))
            conn.commit()
            log_audit(user_id=session.get('user_id'), action='delete_model', target_type='model', target_id=id, details=f"Deleted model '{model['name']}' (Brand ID: {model['brand_id']})")
            return jsonify({'success': True})
        except sqlite3.IntegrityError: # Should not happen due to check above
            return jsonify({'success': False, 'error': 'Cannot delete model due to dependencies'}), 400
        finally:
            conn.close()

    conn.close()
    return jsonify({'success': False, 'error': 'Method not allowed'}), 405

@app.route('/api/products', methods=['GET', 'POST'])
@login_required
def products():
    conn = get_db()
    cursor = conn.cursor()

    if request.method == 'POST':
        data = request.json
        if not data:
            conn.close()
            return jsonify({'success': False, 'error': 'Invalid request data'}), 400

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
            product_id = cursor.lastrowid

            if data.get('opening_stock', 0) > 0:
                cursor.execute('''
                    INSERT INTO stock_movements (product_id, type, quantity, reference_type, notes)
                    VALUES (?, ?, ?, ?, ?)
                ''', (product_id, 'opening_stock', data.get('opening_stock', 0), 'manual', 'Opening stock'))

            conn.commit()
            log_audit(user_id=session.get('user_id'), action='create_product', target_type='product', target_id=product_id, details=f"Created product: {data['name']} (SKU: {data.get('sku')})")
            return jsonify({'success': True, 'id': product_id})
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
            SELECT DISTINCT p.*, c.name as category_name, b.name as brand_name, m.name as model_name
            FROM products p
            LEFT JOIN categories c ON p.category_id = c.id
            LEFT JOIN brands b ON p.brand_id = b.id
            LEFT JOIN models m ON p.model_id = m.id
            LEFT JOIN product_imei pi ON p.id = pi.product_id
            WHERE 1=1
        '''
        params = []

        if search:
            query += ' AND (p.name LIKE ? OR p.sku LIKE ? OR p.description LIKE ? OR pi.imei LIKE ?)'
            search_param = f'%{search}%'
            params.extend([search_param, search_param, search_param, search_param])

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
        if not data:
            conn.close()
            return jsonify({'success': False, 'error': 'Invalid request data'}), 400

        try:
            # Get old stock value and other details to track changes for audit log
            cursor.execute('SELECT current_stock, name, sku FROM products WHERE id = ?', (id,))
            old_product_data = cursor.fetchone()
            if not old_product_data:
                return jsonify({'success': False, 'error': 'Product not found'}), 404

            old_stock = old_product_data['current_stock']
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
            log_audit(user_id=session.get('user_id'), action='update_product', target_type='product', target_id=id, details=f"Updated product '{old_product_data['name']}' (SKU: {old_product_data['sku']}). Stock changed from {old_stock} to {new_stock}.")
            return jsonify({'success': True})
        except sqlite3.IntegrityError as e:
            return jsonify({'success': False, 'error': str(e)}), 400
        finally:
            conn.close()

    elif request.method == 'DELETE':
        try:
            # Check for dependencies before deleting
            cursor.execute('SELECT COUNT(*) as count FROM purchase_order_items WHERE product_id = ?', (id,))
            if cursor.fetchone()['count'] > 0:
                return jsonify({'success': False, 'error': 'Cannot delete product associated with purchase orders'}), 400
            cursor.execute('SELECT COUNT(*) as count FROM stock_movements WHERE product_id = ?', (id,))
            if cursor.fetchone()['count'] > 0:
                return jsonify({'success': False, 'error': 'Cannot delete product with stock movement history'}), 400
            cursor.execute('SELECT COUNT(*) as count FROM pos_sale_items WHERE product_id = ?', (id,))
            if cursor.fetchone()['count'] > 0:
                return jsonify({'success': False, 'error': 'Cannot delete product associated with sales'}), 400
            cursor.execute('SELECT COUNT(*) as count FROM product_imei WHERE product_id = ?', (id,))
            if cursor.fetchone()['count'] > 0:
                return jsonify({'success': False, 'error': 'Cannot delete product with associated IMEI numbers'}), 400

            cursor.execute('SELECT name, sku FROM products WHERE id = ?', (id,))
            product = cursor.fetchone()

            cursor.execute('DELETE FROM products WHERE id = ?', (id,))
            conn.commit()
            log_audit(user_id=session.get('user_id'), action='delete_product', target_type='product', target_id=id, details=f"Deleted product '{product['name']}' (SKU: {product['sku']})")
            return jsonify({'success': True})
        except Exception as e:
            conn.rollback()
            return jsonify({'success': False, 'error': str(e)}), 500
        finally:
            conn.close()

@app.route('/api/products/bulk-delete', methods=['POST'])
@login_required
def bulk_delete_products():
    data = request.json
    if not data:
        return jsonify({'success': False, 'error': 'Invalid request data'}), 400

    ids = data.get('ids', [])

    if not ids:
        return jsonify({'success': False, 'error': 'No product IDs provided'}), 400

    conn = get_db()
    cursor = conn.cursor()
    deleted_count = 0
    failed_deletions = []

    for product_id in ids:
        try:
            # Check dependencies before deleting each product
            cursor.execute('SELECT COUNT(*) as count FROM purchase_order_items WHERE product_id = ?', (product_id,))
            if cursor.fetchone()['count'] > 0:
                failed_deletions.append(f"Product ID {product_id}: Associated with purchase orders")
                continue
            cursor.execute('SELECT COUNT(*) as count FROM stock_movements WHERE product_id = ?', (product_id,))
            if cursor.fetchone()['count'] > 0:
                failed_deletions.append(f"Product ID {product_id}: Has stock movement history")
                continue
            cursor.execute('SELECT COUNT(*) as count FROM pos_sale_items WHERE product_id = ?', (product_id,))
            if cursor.fetchone()['count'] > 0:
                failed_deletions.append(f"Product ID {product_id}: Associated with sales")
                continue
            cursor.execute('SELECT COUNT(*) as count FROM product_imei WHERE product_id = ?', (product_id,))
            if cursor.fetchone()['count'] > 0:
                failed_deletions.append(f"Product ID {product_id}: Has associated IMEI numbers")
                continue

            cursor.execute('SELECT name, sku FROM products WHERE id = ?', (product_id,))
            product = cursor.fetchone()

            cursor.execute('DELETE FROM products WHERE id = ?', (product_id,))
            deleted_count += 1
            log_audit(user_id=session.get('user_id'), action='bulk_delete_product', target_type='product', target_id=product_id, details=f"Deleted product '{product['name']}' (SKU: {product['sku']})")

        except Exception as e:
            failed_deletions.append(f"Product ID {product_id}: {str(e)}")

    conn.commit()
    conn.close()

    if failed_deletions:
        return jsonify({
            'success': False,
            'message': f"Some products could not be deleted due to dependencies.",
            'deleted': deleted_count,
            'failed': failed_deletions
        })

    return jsonify({'success': True, 'deleted': deleted_count})

@app.route('/api/products/bulk-update', methods=['POST'])
@login_required
def bulk_update_products():
    data = request.json
    if not data:
        return jsonify({'success': False, 'error': 'Invalid request data'}), 400

    ids = data.get('ids', [])
    updates = data.get('updates', {})

    if not ids:
        return jsonify({'success': False, 'error': 'No product IDs provided'}), 400

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
        log_audit(user_id=session.get('user_id'), action='bulk_update_product', target_type='product', details=f"Bulk updated {len(ids)} products with: {updates}")

    conn.close()
    return jsonify({'success': True, 'updated': len(ids)})

@app.route('/api/products/<int:product_id>/imeis', methods=['GET', 'POST'])
@login_required
def manage_product_imeis(product_id):
    conn = get_db()
    cursor = conn.cursor()

    if request.method == 'POST':
        data = request.json
        if not data:
            conn.close()
            return jsonify({'success': False, 'error': 'Invalid request data'}), 400

        imei_list = data.get('imeis', [])
        grn_id = data.get('grn_id')
        stock_movement_id = data.get('stock_movement_id')

        if not imei_list:
            return jsonify({'success': False, 'error': 'No IMEI numbers provided'}), 400

        try:
            added_imeis = []
            for imei in imei_list:
                imei_clean = imei.strip()
                if not imei_clean:
                    continue

                # Validate IMEI format (15 digits)
                if len(imei_clean) != 15 or not imei_clean.isdigit():
                    raise ValueError(f'Invalid IMEI format: {imei_clean}. IMEI must be exactly 15 digits.')

                cursor.execute('''
                    INSERT INTO product_imei (product_id, imei, status, grn_id, stock_movement_id, received_date)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (product_id, imei_clean, 'available', grn_id, stock_movement_id, datetime.now()))
                added_imeis.append(imei_clean)

            conn.commit()
            log_audit(user_id=session.get('user_id'), action='add_imeis', target_type='product', target_id=product_id, details=f"Added {len(added_imeis)} IMEIs. GRN ID: {grn_id}, Stock Movement ID: {stock_movement_id}")
            return jsonify({'success': True, 'added': len(added_imeis), 'imeis': added_imeis})
        except sqlite3.IntegrityError as e:
            conn.rollback()
            return jsonify({'success': False, 'error': 'One or more IMEI numbers already exist'}), 400
        except ValueError as e: # Catch IMEI validation errors
            conn.rollback()
            return jsonify({'success': False, 'error': str(e)}), 400
        except Exception as e:
            conn.rollback()
            return jsonify({'success': False, 'error': str(e)}), 400
        finally:
            conn.close()
    else: # GET request
        status_filter = request.args.get('status', '')

        query = '''
            SELECT pi.*, ps.sale_number, ps.customer_name, ps.sale_date,
                   sm.reference_type, sm.reference_id
            FROM product_imei pi
            LEFT JOIN pos_sales ps ON pi.sale_id = ps.id
            LEFT JOIN stock_movements sm ON pi.stock_movement_id = sm.id
            WHERE pi.product_id = ?
        '''
        params = [product_id]

        if status_filter:
            # Handle both 'available' and 'in_stock' when status filter is 'available'
            if status_filter == 'available':
                query += " AND pi.status IN ('available', 'in_stock')"
            else:
                query += ' AND pi.status = ?'
                params.append(status_filter)

        query += ' ORDER BY CASE WHEN pi.status IN (\'available\', \'in_stock\') THEN 0 ELSE 1 END, pi.created_at DESC'

        cursor.execute(query, params)
        imeis = [dict(row) for row in cursor.fetchall()]
        conn.close()

        return jsonify(imeis)

@app.route('/api/products/<int:product_id>/imeis/verify', methods=['GET'])
@login_required
def verify_product_imei(product_id):
    imei = request.args.get('imei', '').strip()

    if not imei:
        return jsonify({'error': 'IMEI parameter required'}), 400

    conn = get_db()
    cursor = conn.cursor()

    try:
        cursor.execute('''
            SELECT id, imei, status FROM product_imei
            WHERE product_id = ? AND imei = ?
        ''', (product_id, imei))

        imei_record = cursor.fetchone()

        if imei_record:
            # Accept both 'available' and 'in_stock' as available for sale
            is_available = imei_record['status'] in ('available', 'in_stock')
            return jsonify({
                'exists': True,
                'available': is_available,
                'imei_id': imei_record['id'],
                'status': imei_record['status']
            })
        else:
            return jsonify({
                'exists': False,
                'available': False
            })
    finally:
        conn.close()

@app.route('/api/imeis/<int:imei_id>', methods=['DELETE'])
@login_required
def delete_imei(imei_id):
    conn = get_db()
    cursor = conn.cursor()

    try:
        cursor.execute('SELECT status, imei, product_id FROM product_imei WHERE id = ?', (imei_id,))
        imei_row = cursor.fetchone()

        if not imei_row:
            return jsonify({'success': False, 'error': 'IMEI not found'}), 404

        if imei_row['status'] == 'sold':
            return jsonify({'success': False, 'error': 'Cannot delete sold IMEI'}), 400

        # Also check if it's linked to a GRN or stock movement that might be important to keep
        cursor.execute('SELECT stock_movement_id FROM product_imei WHERE id = ?', (imei_id,))
        sm_id = cursor.fetchone()['stock_movement_id']
        if sm_id:
            # Check if stock movement has other IMEIs associated with it.
            # If so, we might not want to delete it entirely, but just the IMEI link.
            # For now, we'll just delete the IMEI. A more robust solution might involve
            # creating a new stock movement or marking the existing one as incomplete.
            pass

        cursor.execute('DELETE FROM product_imei WHERE id = ?', (imei_id,))
        conn.commit()
        log_audit(user_id=session.get('user_id'), action='delete_imei', target_type='product_imei', target_id=imei_id, details=f"Deleted IMEI {imei_row['imei']} for Product ID {imei_row['product_id']}. Status was: {imei_row['status']}")
        return jsonify({'success': True})
    except Exception as e:
        conn.rollback()
        return jsonify({'success': False, 'error': str(e)}), 400
    finally:
        conn.close()

@app.route('/api/purchase-orders', methods=['GET', 'POST'])
@login_required
def purchase_orders():
    conn = get_db()
    cursor = conn.cursor()

    if request.method == 'POST':
        data = request.json
        if not data:
            conn.close()
            return jsonify({'success': False, 'error': 'Invalid request data'}), 400

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
            log_audit(user_id=session.get('user_id'), action='create_purchase_order', target_type='purchase_order', target_id=po_id, details=f"Created PO: {data['po_number']} for supplier: {data['supplier_name']}")
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

    po_dict = dict(po)

    cursor.execute('''
        SELECT poi.*, c.name as category_name, b.name as brand_name, m.name as model_name
        FROM purchase_order_items poi
        LEFT JOIN categories c ON poi.category_id = c.id
        LEFT JOIN brands b ON poi.brand_id = b.id
        LEFT JOIN models m ON poi.model_id = m.id
        WHERE poi.po_id = ?
    ''', (id,))
    po_dict['items'] = [dict(row) for row in cursor.fetchall()]

    conn.close()
    return jsonify(po_dict)

@app.route('/api/purchase-orders/<int:id>/receive', methods=['POST'])
@login_required
def receive_purchase_order(id):
    data = request.json
    if not data:
        return jsonify({'success': False, 'error': 'Invalid request data'}), 400

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
                    params_update = [received_qty]

                    if storage_location:
                        update_query += ', storage_location = ?'
                        params_update.append(storage_location)

                    update_query += ' WHERE id = ?'
                    params_update.append(po_item['product_id'])

                    cursor.execute(update_query, params_update)

                    # Record stock movement
                    cursor.execute('''
                        INSERT INTO stock_movements (product_id, type, quantity, reference_type, reference_id, notes)
                        VALUES (?, ?, ?, ?, ?, ?)
                    ''', (po_item['product_id'], 'purchase', received_qty, 'purchase_order', id,
                          f"Received from PO #{id}"))

                    stock_movement_id = cursor.lastrowid

                    # Add IMEI numbers if provided
                    imei_list = item.get('imeis', [])
                    if imei_list:
                        for imei in imei_list:
                            if imei and imei.strip():
                                cursor.execute('''
                                    INSERT INTO product_imei (product_id, imei, status, grn_id, stock_movement_id, received_date)
                                    VALUES (?, ?, ?, ?, ?, ?)
                                ''', (po_item['product_id'], imei.strip(), 'available', grn_id, stock_movement_id, datetime.now()))
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

                    stock_movement_id = cursor.lastrowid

                    # Add IMEI numbers if provided
                    imei_list = item.get('imeis', [])
                    if imei_list:
                        for imei in imei_list:
                            if imei and imei.strip():
                                cursor.execute('''
                                    INSERT INTO product_imei (product_id, imei, status, grn_id, stock_movement_id, received_date)
                                    VALUES (?, ?, ?, ?, ?, ?)
                                ''', (new_product_id, imei.strip(), 'available', grn_id, stock_movement_id, datetime.now()))
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

                stock_movement_id = cursor.lastrowid

                # Add IMEI numbers if provided
                imei_list = item.get('imeis', [])
                if imei_list:
                    for imei in imei_list:
                        if imei and imei.strip():
                            cursor.execute('''
                                INSERT INTO product_imei (product_id, imei, status, grn_id, stock_movement_id, received_date)
                                VALUES (?, ?, ?, ?, ?, ?)
                            ''', (new_product_id, imei.strip(), 'available', grn_id, stock_movement_id, datetime.now()))

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
        log_audit(user_id=session.get('user_id'), action='receive_purchase_order', target_type='purchase_order', target_id=id, details=f"Received items for PO #{id}. GRN #{grn_number} created. Status updated to {new_status}.")
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
    grn['items'] = [dict(row) for row in cursor.fetchall()]
    conn.close()

    return jsonify(grn)

@app.route('/api/quick-orders', methods=['GET', 'POST'])
@login_required
def quick_orders():
    conn = get_db()
    cursor = conn.cursor()

    if request.method == 'POST':
        data = request.json
        if not data:
            conn.close()
            return jsonify({'success': False, 'error': 'Invalid request data'}), 400

        try:
            order_number = f"QO-{datetime.now().strftime('%Y%m%d%H%M%S')}"
            items = data.get('items', [])

            if not items:
                return jsonify({'success': False, 'error': 'No items in order'}), 400

            total_items = len(items)
            total_amount = 0

            cursor.execute('''
                INSERT INTO quick_orders (order_number, total_items, notes, created_by)
                VALUES (?, ?, ?, ?)
            ''', (order_number, total_items, data.get('notes', ''), session.get('username')))

            order_id = cursor.lastrowid

            for item in items:
                product_id = item['product_id']
                quantity = item['quantity']

                if not isinstance(quantity, int) or quantity <= 0:
                    raise ValueError(f'Invalid quantity: {quantity}. Quantity must be a positive integer')

                cursor.execute('SELECT name, selling_price, current_stock FROM products WHERE id = ?', (product_id,))
                product_row = cursor.fetchone()

                if not product_row:
                    raise ValueError(f'Product ID {product_id} not found')

                product_name = product_row['name']
                unit_price = product_row['selling_price']
                current_stock = product_row['current_stock']

                if current_stock < quantity:
                    raise ValueError(f'Insufficient stock for {product_name}. Available: {current_stock}, Requested: {quantity}')

                item_total = unit_price * quantity
                total_amount += item_total

                cursor.execute('''
                    INSERT INTO quick_order_items (order_id, product_id, product_name, quantity, unit_price, total_price)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (order_id, product_id, product_name, quantity, unit_price, item_total))

                new_stock = current_stock - quantity
                cursor.execute('UPDATE products SET current_stock = ? WHERE id = ?', (new_stock, product_id))

                cursor.execute('''
                    INSERT INTO stock_movements (product_id, type, quantity, reference_type, reference_id, notes)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (product_id, 'sale', -quantity, 'quick_order', order_id, f'Quick Order {order_number}'))

            cursor.execute('UPDATE quick_orders SET total_amount = ? WHERE id = ?', (total_amount, order_id))

            conn.commit()
            log_audit(user_id=session.get('user_id'), action='create_quick_order', target_type='quick_order', target_id=order_id, details=f"Created Quick Order #{order_number} with {total_items} items.")
            return jsonify({'success': True, 'order_id': order_id, 'order_number': order_number})

        except ValueError as e:
            conn.rollback()
            return jsonify({'success': False, 'error': str(e)}), 400
        except Exception as e:
            conn.rollback()
            return jsonify({'success': False, 'error': str(e)}), 500
        finally:
            conn.close()

    else:
        cursor.execute('''
            SELECT * FROM quick_orders
            ORDER BY created_at DESC
        ''')
        orders = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return jsonify(orders)

@app.route('/api/quick-orders/<int:id>', methods=['GET'])
@login_required
def get_quick_order_detail(id):
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute('SELECT * FROM quick_orders WHERE id = ?', (id,))
    order_row = cursor.fetchone()

    if not order_row:
        conn.close()
        return jsonify({'error': 'Order not found'}), 404

    order = dict(order_row)

    cursor.execute('''
        SELECT qoi.*, p.sku, p.brand_id, p.category_id
        FROM quick_order_items qoi
        LEFT JOIN products p ON qoi.product_id = p.id
        WHERE qoi.order_id = ?
    ''', (id,))
    order['items'] = [dict(row) for row in cursor.fetchall()]
    conn.close()

    return jsonify(order)

@app.route('/api/stock-adjustment', methods=['POST'])
@login_required
def stock_adjustment():
    conn = get_db()
    cursor = conn.cursor()

    try:
        data = request.json
        if not data:
            conn.close()
            return jsonify({'success': False, 'error': 'Invalid request data'}), 400

        product_id = data.get('product_id')
        quantity = data.get('quantity')
        notes = data.get('notes', '')
        imei_numbers = data.get('imei_numbers', [])

        if not product_id:
            return jsonify({'success': False, 'error': 'Product ID is required'}), 400

        if not isinstance(quantity, int) or quantity <= 0:
            return jsonify({'success': False, 'error': 'Quantity must be a positive integer'}), 400

        cursor.execute('SELECT name, current_stock FROM products WHERE id = ?', (product_id,))
        product_row = cursor.fetchone()

        if not product_row:
            return jsonify({'success': False, 'error': 'Product not found'}), 404

        product_name = product_row['name']
        current_stock = product_row['current_stock'] or 0
        new_stock = current_stock + quantity

        cursor.execute('UPDATE products SET current_stock = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?',
                      (new_stock, product_id))

        # Create stock movement record
        movement_notes = notes or 'Stock adjustment'
        if imei_numbers and len(imei_numbers) > 0:
            movement_notes += f' (with {len(imei_numbers)} IMEI numbers)'

        cursor.execute('''
            INSERT INTO stock_movements (product_id, type, quantity, reference_type, notes)
            VALUES (?, ?, ?, ?, ?)
        ''', (product_id, 'adjustment', quantity, 'manual', movement_notes))

        movement_id = cursor.lastrowid

        # Store IMEI numbers if provided
        if imei_numbers and len(imei_numbers) > 0:
            # Insert IMEI numbers
            for imei in imei_numbers:
                imei_clean = imei.strip()
                if not imei_clean:
                    continue
                # Validate IMEI format (15 digits)
                if len(imei_clean) != 15 or not imei_clean.isdigit():
                    raise ValueError(f'Invalid IMEI format: {imei_clean}. IMEI must be exactly 15 digits.')
                try:
                    cursor.execute('''
                        INSERT INTO product_imei (product_id, imei, stock_movement_id, status)
                        VALUES (?, ?, ?, ?)
                    ''', (product_id, imei_clean, movement_id, 'in_stock'))
                except sqlite3.IntegrityError:
                    # IMEI already exists
                    conn.rollback()
                    return jsonify({'success': False, 'error': f'IMEI number {imei_clean} already exists in the system'}), 400

        conn.commit()
        log_audit(user_id=session.get('user_id'), action='stock_adjustment', target_type='product', target_id=product_id, details=f"Adjusted stock for {product_name}. Quantity: {quantity}. IMEI count: {len(imei_numbers) if imei_numbers else 0}.")
        return jsonify({
            'success': True,
            'product_name': product_name,
            'previous_stock': current_stock,
            'added_quantity': quantity,
            'new_stock': new_stock,
            'imei_count': len(imei_numbers) if imei_numbers else 0
        })

    except ValueError as e: # Catch IMEI validation errors
        conn.rollback()
        return jsonify({'success': False, 'error': str(e)}), 400
    except Exception as e:
        conn.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        conn.close()

@app.route('/api/stock-adjustments', methods=['GET'])
@login_required
def get_stock_adjustments():
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute('''
        SELECT
            sm.id,
            sm.product_id,
            p.name as product_name,
            p.sku,
            sm.quantity,
            sm.notes,
            sm.created_at,
            COUNT(pi.id) as imei_count
        FROM stock_movements sm
        LEFT JOIN products p ON sm.product_id = p.id
        LEFT JOIN product_imei pi ON sm.id = pi.stock_movement_id
        WHERE sm.type = 'adjustment'
        GROUP BY sm.id
        ORDER BY sm.created_at DESC
    ''')

    adjustments = [dict(row) for row in cursor.fetchall()]
    conn.close()

    return jsonify(adjustments)

@app.route('/api/stock-adjustments/<int:id>', methods=['GET', 'DELETE'])
@login_required
def stock_adjustment_detail(id):
    conn = get_db()
    cursor = conn.cursor()

    if request.method == 'GET':
        cursor.execute('''
            SELECT
                sm.id,
                sm.product_id,
                p.name as product_name,
                p.sku,
                p.current_stock,
                sm.quantity,
                sm.notes,
                sm.created_at
            FROM stock_movements sm
            LEFT JOIN products p ON sm.product_id = p.id
            WHERE sm.id = ? AND sm.type = 'adjustment'
        ''', (id,))

        adjustment = cursor.fetchone()
        if not adjustment:
            conn.close()
            return jsonify({'error': 'Stock adjustment not found'}), 404

        adjustment_dict = dict(adjustment)

        cursor.execute('''
            SELECT imei, status, created_at
            FROM product_imei
            WHERE stock_movement_id = ?
            ORDER BY created_at
        ''', (id,))

        adjustment_dict['imei_numbers'] = [dict(row) for row in cursor.fetchall()]
        conn.close()

        return jsonify(adjustment_dict)

    elif request.method == 'DELETE':
        try:
            cursor.execute('''
                SELECT product_id, quantity, notes
                FROM stock_movements
                WHERE id = ? AND type = 'adjustment'
            ''', (id,))

            movement = cursor.fetchone()
            if not movement:
                conn.close()
                return jsonify({'success': False, 'error': 'Adjustment not found'}), 404

            product_id = movement['product_id']
            quantity = movement['quantity']

            cursor.execute('SELECT current_stock FROM products WHERE id = ?', (product_id,))
            product = cursor.fetchone()

            if not product:
                conn.close()
                return jsonify({'success': False, 'error': 'Product not found'}), 404

            current_stock = product['current_stock'] or 0

            # Check if current stock is sufficient to reverse the adjustment
            if current_stock < quantity:
                conn.close()
                return jsonify({
                    'success': False,
                    'error': f'Cannot delete adjustment: current stock ({current_stock}) is less than adjustment quantity ({quantity}). Stock may have been sold or further adjusted.'
                }), 409

            cursor.execute('''
                UPDATE products
                SET current_stock = current_stock - ?
                WHERE id = ?
            ''', (quantity, product_id))

            # Delete associated IMEIs
            cursor.execute('DELETE FROM product_imei WHERE stock_movement_id = ?', (id,))
            # Delete the stock movement itself
            cursor.execute('DELETE FROM stock_movements WHERE id = ?', (id,))

            conn.commit()
            log_audit(user_id=session.get('user_id'), action='delete_stock_adjustment', target_type='stock_movement', target_id=id, details=f"Deleted stock adjustment for Product ID {product_id} (Quantity: {quantity}). Notes: {movement['notes']}")
            conn.close()

            return jsonify({'success': True})
        except Exception as e:
            conn.rollback()
            conn.close()
            return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/reports/sales', methods=['GET'])
@login_required
def report_sales():
    conn = get_db()
    cursor = conn.cursor()

    from_date = request.args.get('from_date', '')
    to_date = request.args.get('to_date', '')
    transaction_type = request.args.get('transaction_type', '')

    query = '''
        SELECT
            ps.sale_number,
            ps.sale_date,
            ps.customer_name,
            ps.customer_phone,
            ps.transaction_type,
            ps.subtotal,
            ps.discount_amount,
            ps.tax_amount,
            ps.total_amount,
            ps.payment_method,
            ps.payment_status,
            ps.cashier_name,
            COUNT(psi.id) as item_count,
            SUM(psi.quantity) as total_quantity
        FROM pos_sales ps
        LEFT JOIN pos_sale_items psi ON ps.id = psi.sale_id
        WHERE 1=1
    '''
    params = []

    if from_date:
        query += ' AND DATE(ps.sale_date) >= ?'
        params.append(from_date)

    if to_date:
        query += ' AND DATE(ps.sale_date) <= ?'
        params.append(to_date)

    if transaction_type:
        query += ' AND ps.transaction_type = ?'
        params.append(transaction_type)

    query += ' GROUP BY ps.id ORDER BY ps.sale_date DESC'

    cursor.execute(query, params)
    sales = [dict(row) for row in cursor.fetchall()]
    conn.close()

    df = pd.DataFrame(sales)
    if not df.empty:
        df['sale_date'] = pd.to_datetime(df['sale_date']).dt.strftime('%Y-%m-%d %H:%M:%S')

    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Sales Report')
        workbook = writer.book
        worksheet = writer.sheets['Sales Report']

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
        download_name=f'sales_report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
    )

@app.route('/api/reports/inventory', methods=['GET'])
@login_required
def report_inventory():
    conn = get_db()
    cursor = conn.cursor()

    category_id = request.args.get('category_id', '')
    stock_status = request.args.get('stock_status', '')

    query = '''
        SELECT
            p.sku,
            p.name,
            c.name as category,
            b.name as brand,
            m.name as model,
            p.current_stock,
            p.min_stock_level,
            p.cost_price,
            p.selling_price,
            p.mrp,
            (p.current_stock * p.cost_price) as stock_value,
            CASE
                WHEN p.current_stock = 0 THEN 'Out of Stock'
                WHEN p.current_stock <= p.min_stock_level THEN 'Low Stock'
                ELSE 'Good Stock'
            END as stock_status,
            p.storage_location,
            p.status
        FROM products p
        LEFT JOIN categories c ON p.category_id = c.id
        LEFT JOIN brands b ON p.brand_id = b.id
        LEFT JOIN models m ON p.model_id = m.id
        WHERE 1=1
    '''
    params = []

    if category_id:
        query += ' AND p.category_id = ?'
        params.append(category_id)

    if stock_status == 'low':
        query += ' AND p.current_stock <= p.min_stock_level AND p.current_stock > 0'
    elif stock_status == 'out':
        query += ' AND p.current_stock = 0'
    elif stock_status == 'good':
        query += ' AND p.current_stock > p.min_stock_level'

    query += ' ORDER BY p.name'

    cursor.execute(query, params)
    inventory = [dict(row) for row in cursor.fetchall()]
    conn.close()

    df = pd.DataFrame(inventory)

    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Inventory Report')
        workbook = writer.book
        worksheet = writer.sheets['Inventory Report']

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
        download_name=f'inventory_report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
    )

@app.route('/api/reports/purchase-orders', methods=['GET'])
@login_required
def report_purchase_orders():
    conn = get_db()
    cursor = conn.cursor()

    from_date = request.args.get('from_date', '')
    to_date = request.args.get('to_date', '')
    status = request.args.get('status', '')

    query = '''
        SELECT
            po.po_number,
            po.supplier_name,
            po.supplier_contact,
            po.order_date,
            po.expected_delivery,
            po.status,
            po.payment_status,
            po.total_amount,
            COUNT(poi.id) as total_items,
            SUM(poi.quantity) as total_quantity,
            SUM(poi.received_quantity) as received_quantity,
            po.storage_location,
            po.notes
        FROM purchase_orders po
        LEFT JOIN purchase_order_items poi ON po.id = poi.po_id
        WHERE 1=1
    '''
    params = []

    if from_date:
        query += ' AND DATE(po.order_date) >= ?'
        params.append(from_date)

    if to_date:
        query += ' AND DATE(po.order_date) <= ?'
        params.append(to_date)

    if status:
        query += ' AND po.status = ?'
        params.append(status)

    query += ' GROUP BY po.id ORDER BY po.order_date DESC'

    cursor.execute(query, params)
    pos = [dict(row) for row in cursor.fetchall()]
    conn.close()

    df = pd.DataFrame(pos)
    if not df.empty:
        df['order_date'] = pd.to_datetime(df['order_date']).dt.strftime('%Y-%m-%d')
        df['expected_delivery'] = pd.to_datetime(df['expected_delivery'], errors='coerce').dt.strftime('%Y-%m-%d')

    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Purchase Orders')
        workbook = writer.book
        worksheet = writer.sheets['Purchase Orders']

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
        download_name=f'purchase_orders_report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
    )

@app.route('/api/reports/stock-movements', methods=['GET'])
@login_required
def report_stock_movements():
    conn = get_db()
    cursor = conn.cursor()

    from_date = request.args.get('from_date', '')
    to_date = request.args.get('to_date', '')
    movement_type = request.args.get('type', '')

    query = '''
        SELECT
            sm.created_at,
            p.name as product_name,
            p.sku,
            sm.type as movement_type,
            sm.quantity,
            sm.reference_type,
            sm.reference_id,
            sm.notes,
            c.name as category,
            b.name as brand
        FROM stock_movements sm
        LEFT JOIN products p ON sm.product_id = p.id
        LEFT JOIN categories c ON p.category_id = c.id
        LEFT JOIN brands b ON p.brand_id = b.id
        WHERE 1=1
    '''
    params = []

    if from_date:
        query += ' AND DATE(sm.created_at) >= ?'
        params.append(from_date)

    if to_date:
        query += ' AND DATE(sm.created_at) <= ?'
        params.append(to_date)

    if movement_type:
        query += ' AND sm.type = ?'
        params.append(movement_type)

    query += ' ORDER BY sm.created_at DESC'

    cursor.execute(query, params)
    movements = [dict(row) for row in cursor.fetchall()]
    conn.close()

    df = pd.DataFrame(movements)
    if not df.empty:
        df['created_at'] = pd.to_datetime(df['created_at']).dt.strftime('%Y-%m-%d %H:%M:%S')

    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Stock Movements')
        workbook = writer.book
        worksheet = writer.sheets['Stock Movements']

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
        download_name=f'stock_movements_report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
    )

@app.route('/api/reports/grns', methods=['GET'])
@login_required
def report_grns():
    conn = get_db()
    cursor = conn.cursor()

    from_date = request.args.get('from_date', '')
    to_date = request.args.get('to_date', '')
    payment_status = request.args.get('payment_status', '')

    query = '''
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
        WHERE 1=1
    '''
    params = []

    if from_date:
        query += ' AND DATE(g.received_date) >= ?'
        params.append(from_date)

    if to_date:
        query += ' AND DATE(g.received_date) <= ?'
        params.append(to_date)

    if payment_status:
        query += ' AND g.payment_status = ?'
        params.append(payment_status)

    query += ' ORDER BY g.received_date DESC, g.grn_number'

    cursor.execute(query, params)
    grns = [dict(row) for row in cursor.fetchall()]
    conn.close()

    df = pd.DataFrame(grns)
    if not df.empty:
        df['received_date'] = pd.to_datetime(df['received_date']).dt.strftime('%Y-%m-%d %H:%M:%S')

    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='GRN Report')
        workbook = writer.book
        worksheet = writer.sheets['GRN Report']

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

@app.route('/api/products/<int:id>/imei-tracking', methods=['GET'])
@login_required
def get_imei_tracking(id):
    conn = get_db()
    cursor = conn.cursor()

    # Get product name
    cursor.execute('SELECT name FROM products WHERE id = ?', (id,))
    product_row = cursor.fetchone()
    if not product_row:
        conn.close()
        return jsonify({'error': 'Product not found'}), 404

    product_name = product_row['name']

    # Get IMEI records with sale information
    cursor.execute('''
        SELECT
            pi.id,
            pi.imei,
            pi.status,
            pi.created_at,
            pi.sold_date,
            ps.sale_number,
            ps.customer_name,
            CASE
                WHEN sm.reference_type = 'purchase_order' THEN 'PO #' || sm.reference_id
                WHEN sm.reference_type = 'manual' THEN 'Stock Adjustment'
                WHEN sm.reference_type = 'grn' THEN 'GRN #' || sm.reference_id
                ELSE sm.reference_type
            END as reference
        FROM product_imei pi
        LEFT JOIN stock_movements sm ON pi.stock_movement_id = sm.id
        LEFT JOIN pos_sales ps ON pi.sale_id = ps.id
        WHERE pi.product_id = ?
        ORDER BY pi.status ASC, pi.created_at DESC
    ''', (id,))

    imei_records = [dict(row) for row in cursor.fetchall()]

    # Get total count
    cursor.execute('SELECT COUNT(*) as count FROM product_imei WHERE product_id = ?', (id,))
    total_count = cursor.fetchone()['count']

    conn.close()

    return jsonify({
        'product_name': product_name,
        'total_count': total_count,
        'imei_records': imei_records
    })

@app.route('/api/imei/<int:id>/mark-sold', methods=['POST'])
@login_required
def mark_imei_sold(id):
    conn = get_db()
    cursor = conn.cursor()

    try:
        # Get current IMEI details for audit log
        cursor.execute('SELECT imei, product_id, status FROM product_imei WHERE id = ?', (id,))
        imei_data = cursor.fetchone()
        if not imei_data:
            return jsonify({'success': False, 'error': 'IMEI not found'}), 404

        if imei_data['status'] == 'sold':
            return jsonify({'success': False, 'error': 'IMEI is already marked as sold'}), 400

        cursor.execute('UPDATE product_imei SET status = ?, sold_date = ? WHERE id = ?', ('sold', datetime.now(), id))
        conn.commit()
        log_audit(user_id=session.get('user_id'), action='mark_imei_sold', target_type='product_imei', target_id=id, details=f"Marked IMEI {imei_data['imei']} for Product ID {imei_data['product_id']} as sold. Status changed from {imei_data['status']} to sold.")
        return jsonify({'success': True})
    except Exception as e:
        conn.rollback()
        return jsonify({'success': False, 'error': str(e)}), 400
    finally:
        conn.close()

@app.route('/api/products/search-by-imei', methods=['GET'])
@login_required
def search_by_imei():
    imei_query = request.args.get('imei', '')

    if not imei_query:
        return jsonify({'error': 'IMEI parameter required'}), 400

    conn = get_db()
    cursor = conn.cursor()

    # Search in product_imei table
    cursor.execute('''
        SELECT
            pi.imei,
            pi.status,
            pi.created_at,
            p.id as product_id,
            p.name as product_name,
            p.sku,
            p.current_stock,
            p.selling_price,
            b.name as brand_name,
            m.name as model_name
        FROM product_imei pi
        LEFT JOIN products p ON pi.product_id = p.id
        LEFT JOIN brands b ON p.brand_id = b.id
        LEFT JOIN models m ON p.model_id = m.id
        WHERE pi.imei LIKE ?
        LIMIT 20
    ''', (f'%{imei_query}%',))

    results = [dict(row) for row in cursor.fetchall()]
    conn.close()

    return jsonify(results)

@app.route('/api/reports/profit', methods=['GET'])
@login_required
def report_profit():
    conn = get_db()
    cursor = conn.cursor()

    from_date = request.args.get('from_date', '')
    to_date = request.args.get('to_date', '')
    sort_by = request.args.get('sort_by', 'margin')

    query = '''
        SELECT
            p.name as product_name,
            p.sku,
            c.name as category,
            b.name as brand,
            p.cost_price,
            p.selling_price,
            p.mrp,
            CASE WHEN p.cost_price > 0 THEN ((p.selling_price - p.cost_price) / p.cost_price * 100) ELSE 0 END as profit_margin_percent,
            (p.selling_price - p.cost_price) as profit_per_unit,
            COALESCE(SUM(psi.quantity), 0) as quantity_sold,
            COALESCE(SUM(psi.total_price), 0) as total_revenue,
            COALESCE(SUM(psi.quantity * p.cost_price), 0) as total_cost,
            COALESCE(SUM(psi.total_price) - SUM(psi.quantity * p.cost_price), 0) as total_profit
        FROM products p
        LEFT JOIN categories c ON p.category_id = c.id
        LEFT JOIN brands b ON p.brand_id = b.id
        LEFT JOIN pos_sale_items psi ON p.id = psi.product_id
        LEFT JOIN pos_sales ps ON psi.sale_id = ps.id AND ps.transaction_type = 'sale'
        WHERE 1=1
    '''
    params = []

    if from_date:
        query += ' AND DATE(ps.sale_date) >= ?'
        params.append(from_date)

    if to_date:
        query += ' AND DATE(ps.sale_date) <= ?'
        params.append(to_date)

    query += ' GROUP BY p.id'

    if sort_by == 'margin':
        query += ' ORDER BY profit_margin_percent DESC'
    elif sort_by == 'quantity':
        query += ' ORDER BY quantity_sold DESC'
    elif sort_by == 'revenue':
        query += ' ORDER BY total_revenue DESC'
    elif sort_by == 'profit':
        query += ' ORDER BY total_profit DESC'
    else: # Default sort by name
        query += ' ORDER BY p.name ASC'

    cursor.execute(query, params)
    profit_data = [dict(row) for row in cursor.fetchall()]
    conn.close()

    df = pd.DataFrame(profit_data)

    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Profit Analysis')
        workbook = writer.book
        worksheet = writer.sheets['Profit Analysis']

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
        download_name=f'profit_analysis_report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
    )

@app.route('/api/reports/gst', methods=['GET'])
@login_required
def report_gst():
    conn = get_db()
    cursor = conn.cursor()

    from_date = request.args.get('from_date', '')
    to_date = request.args.get('to_date', '')

    query = '''
        SELECT
            ps.sale_number,
            ps.sale_date,
            ps.customer_name,
            ps.customer_phone,
            ps.transaction_type,
            ps.subtotal,
            ps.discount_amount,
            ps.tax_percentage,
            ps.tax_amount,
            ps.total_amount,
            (ps.tax_amount / 2) as cgst_amount,
            (ps.tax_amount / 2) as sgst_amount,
            (ps.tax_percentage / 2) as cgst_rate,
            (ps.tax_percentage / 2) as sgst_rate,
            ps.payment_method
        FROM pos_sales ps
        WHERE ps.transaction_type = 'sale'
    '''
    params = []

    if from_date:
        query += ' AND DATE(ps.sale_date) >= ?'
        params.append(from_date)

    if to_date:
        query += ' AND DATE(ps.sale_date) <= ?'
        params.append(to_date)

    query += ' ORDER BY ps.sale_date DESC'

    cursor.execute(query, params)
    gst_data = [dict(row) for row in cursor.fetchall()]
    conn.close()

    df = pd.DataFrame(gst_data)
    if not df.empty:
        df['sale_date'] = pd.to_datetime(df['sale_date']).dt.strftime('%Y-%m-%d %H:%M:%S')

    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='GST Report')
        workbook = writer.book
        worksheet = writer.sheets['GST Report']

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
        download_name=f'gst_report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
    )

@app.route('/api/reports/brand-performance', methods=['GET'])
@login_required
def report_brand_performance():
    conn = get_db()
    cursor = conn.cursor()

    from_date = request.args.get('from_date', '')
    to_date = request.args.get('to_date', '')

    query = '''
        SELECT
            b.name as brand_name,
            COUNT(DISTINCT p.id) as total_products,
            COALESCE(SUM(psi.quantity), 0) as total_units_sold,
            COALESCE(SUM(psi.total_price), 0) as total_revenue,
            COALESCE(SUM(psi.quantity * p.cost_price), 0) as total_cost,
            COALESCE(SUM(psi.total_price) - SUM(psi.quantity * p.cost_price), 0) as total_profit,
            COALESCE(AVG((p.selling_price - p.cost_price) / p.cost_price * 100), 0) as avg_margin_percent
        FROM brands b
        LEFT JOIN products p ON b.id = p.brand_id
        LEFT JOIN pos_sale_items psi ON p.id = psi.product_id
        LEFT JOIN pos_sales ps ON psi.sale_id = ps.id AND ps.transaction_type = 'sale'
        WHERE 1=1
    '''
    params = []

    if from_date:
        query += ' AND DATE(ps.sale_date) >= ?'
        params.append(from_date)

    if to_date:
        query += ' AND DATE(ps.sale_date) <= ?'
        params.append(to_date)

    query += ' GROUP BY b.id ORDER BY total_revenue DESC'

    cursor.execute(query, params)
    brand_data = [dict(row) for row in cursor.fetchall()]
    conn.close()

    df = pd.DataFrame(brand_data)

    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Brand Performance')
        workbook = writer.book
        worksheet = writer.sheets['Brand Performance']

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
        download_name=f'brand_performance_report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
    )

@app.route('/api/reports/top-selling', methods=['GET'])
@login_required
def report_top_selling():
    conn = get_db()
    cursor = conn.cursor()

    from_date = request.args.get('from_date', '')
    to_date = request.args.get('to_date', '')
    limit = request.args.get('limit', '20')

    query = '''
        SELECT
            p.name as product_name,
            p.sku,
            c.name as category,
            b.name as brand,
            m.name as model,
            SUM(psi.quantity) as total_quantity_sold,
            SUM(psi.total_price) as total_revenue,
            SUM(psi.quantity * p.cost_price) as total_cost,
            SUM(psi.total_price) - SUM(psi.quantity * p.cost_price) as total_profit,
            AVG(psi.unit_price) as avg_selling_price,
            COUNT(DISTINCT ps.id) as number_of_transactions
        FROM pos_sale_items psi
        LEFT JOIN products p ON psi.product_id = p.id
        LEFT JOIN categories c ON p.category_id = c.id
        LEFT JOIN brands b ON p.brand_id = b.id
        LEFT JOIN models m ON p.model_id = m.id
        LEFT JOIN pos_sales ps ON psi.sale_id = ps.id
        WHERE ps.transaction_type = 'sale'
    '''
    params = []

    if from_date:
        query += ' AND DATE(ps.sale_date) >= ?'
        params.append(from_date)

    if to_date:
        query += ' AND DATE(ps.sale_date) <= ?'
        params.append(to_date)

    query += ' GROUP BY psi.product_id ORDER BY total_quantity_sold DESC LIMIT ?'
    params.append(limit)

    cursor.execute(query, params)
    top_selling = [dict(row) for row in cursor.fetchall()]
    conn.close()

    df = pd.DataFrame(top_selling)

    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Top Selling Products')
        workbook = writer.book
        worksheet = writer.sheets['Top Selling Products']

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
        download_name=f'top_selling_report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
    )

@app.route('/api/reports/staff-performance', methods=['GET'])
@login_required
def report_staff_performance():
    conn = get_db()
    cursor = conn.cursor()

    from_date = request.args.get('from_date', '')
    to_date = request.args.get('to_date', '')

    query = '''
        SELECT
            ps.cashier_name,
            COUNT(DISTINCT ps.id) as total_transactions,
            SUM(CASE WHEN ps.transaction_type = 'sale' THEN 1 ELSE 0 END) as total_sales,
            SUM(CASE WHEN ps.transaction_type = 'return' THEN 1 ELSE 0 END) as total_returns,
            SUM(CASE WHEN ps.transaction_type = 'exchange' THEN 1 ELSE 0 END) as total_exchanges,
            SUM(CASE WHEN ps.transaction_type = 'sale' THEN ps.total_amount ELSE 0 END) as total_sales_amount,
            SUM(CASE WHEN ps.transaction_type = 'return' THEN ABS(ps.total_amount) ELSE 0 END) as total_returns_amount,
            AVG(CASE WHEN ps.transaction_type = 'sale' THEN ps.total_amount ELSE NULL END) as avg_transaction_value,
            SUM(CASE WHEN ps.payment_method = 'cash' THEN 1 ELSE 0 END) as cash_transactions,
            SUM(CASE WHEN ps.payment_method = 'card' THEN 1 ELSE 0 END) as card_transactions,
            SUM(CASE WHEN ps.payment_method = 'upi' THEN 1 ELSE 0 END) as upi_transactions
        FROM pos_sales ps
        WHERE ps.cashier_name IS NOT NULL
    '''
    params = []

    if from_date:
        query += ' AND DATE(ps.sale_date) >= ?'
        params.append(from_date)

    if to_date:
        query += ' AND DATE(ps.sale_date) <= ?'
        params.append(to_date)

    query += ' GROUP BY ps.cashier_name ORDER BY total_sales_amount DESC'

    cursor.execute(query, params)
    staff_data = [dict(row) for row in cursor.fetchall()]
    conn.close()

    df = pd.DataFrame(staff_data)

    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Staff Performance')
        workbook = writer.book
        worksheet = writer.sheets['Staff Performance']

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
        download_name=f'staff_performance_report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
    )

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
            else: # Negative quantity for adjustments means stock reduction
                stock_added = 0
                stock_removed = quantity
                running_balance -= quantity
        elif movement['type'] in ['sale', 'return', 'damage', 'exchange']: # Treat these as stock reduction
            stock_added = 0
            stock_removed = quantity
            running_balance -= quantity
        else:
            # Default handling for unknown types - assume reduction if quantity negative
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

@app.route('/api/dashboard/analytics', methods=['GET'])
@login_required
def dashboard_analytics():
    conn = get_db()
    cursor = conn.cursor()

    # Total products
    cursor.execute('SELECT COUNT(*) as count FROM products WHERE status = "active"')
    total_products = cursor.fetchone()['count']

    # Sales and profit for last 30 days
    cursor.execute('''
        SELECT
            COALESCE(SUM(CASE WHEN transaction_type = 'sale' THEN total_amount ELSE 0 END), 0) as total_sales,
            COALESCE(SUM(CASE WHEN transaction_type = 'return' THEN ABS(total_amount) ELSE 0 END), 0) as total_returns
        FROM pos_sales
        WHERE DATE(sale_date) >= DATE('now', '-30 days')
    ''')
    sales_data = cursor.fetchone()
    total_sales = (sales_data['total_sales'] or 0) - (sales_data['total_returns'] or 0)

    # Calculate profit (revenue - cost)
    cursor.execute('''
        SELECT
            COALESCE(SUM(psi.total_price), 0) as revenue,
            COALESCE(SUM(psi.quantity * p.cost_price), 0) as cost
        FROM pos_sale_items psi
        LEFT JOIN products p ON psi.product_id = p.id
        LEFT JOIN pos_sales ps ON psi.sale_id = ps.id
        WHERE DATE(ps.sale_date) >= DATE('now', '-30 days')
        AND ps.transaction_type = 'sale'
    ''')
    profit_data = cursor.fetchone()
    revenue = profit_data['revenue'] or 0
    cost = profit_data['cost'] or 0
    profit = revenue - cost
    margin_percent = (profit / revenue * 100) if revenue > 0 else 0

    # Low stock count
    cursor.execute('SELECT COUNT(*) as count FROM products WHERE current_stock <= min_stock_level AND status = "active"')
    low_stock_count = cursor.fetchone()['count']

    # Top 5 selling products (last 30 days)
    cursor.execute('''
        SELECT
            psi.product_name,
            p.name as current_product_name,
            b.name as brand_name,
            SUM(psi.quantity) as total_quantity,
            SUM(psi.total_price) as total_revenue
        FROM pos_sale_items psi
        LEFT JOIN pos_sales ps ON psi.sale_id = ps.id
        LEFT JOIN products p ON psi.product_id = p.id
        LEFT JOIN brands b ON p.brand_id = b.id
        WHERE DATE(ps.sale_date) >= DATE('now', '-30 days')
        AND ps.transaction_type = 'sale'
        GROUP BY psi.product_id
        ORDER BY total_quantity DESC
        LIMIT 5
    ''')
    top_products = []
    for row in cursor.fetchall():
        product = dict(row)
        product['product_name'] = product['current_product_name'] or product['product_name']
        top_products.append(product)

    # Recent POS transactions
    cursor.execute('''
        SELECT
            sale_number,
            customer_name,
            total_amount,
            transaction_type,
            sale_date
        FROM pos_sales
        ORDER BY sale_date DESC
        LIMIT 10
    ''')
    recent_transactions = [dict(row) for row in cursor.fetchall()]

    # Low stock items
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

    conn.close()

    return jsonify({
        'total_products': total_products,
        'total_sales': total_sales,
        'total_profit': profit,
        'low_stock_count': low_stock_count,
        'profit_summary': {
            'revenue': revenue,
            'cost': cost,
            'profit': profit,
            'margin_percent': margin_percent
        },
        'top_products': top_products,
        'recent_transactions': recent_transactions,
        'low_stock_items': low_stock_items
    })

@app.route('/api/dashboard/sales-chart', methods=['GET'])
@login_required
def dashboard_sales_chart():
    days = int(request.args.get('days', 7))
    conn = get_db()
    cursor = conn.cursor()

    # Get sales and profit for each day
    cursor.execute('''
        SELECT
            DATE(sale_date) as sale_day,
            COALESCE(SUM(CASE WHEN transaction_type = 'sale' THEN total_amount ELSE -ABS(total_amount) END), 0) as daily_sales
        FROM pos_sales
        WHERE DATE(sale_date) >= DATE('now', '-' || ? || ' days')
        GROUP BY DATE(sale_date)
        ORDER BY sale_day
    ''', (days,))

    sales_by_day = {row['sale_day']: row['daily_sales'] for row in cursor.fetchall()}

    # Get profit for each day
    cursor.execute('''
        SELECT
            DATE(ps.sale_date) as sale_day,
            COALESCE(SUM(psi.total_price - (psi.quantity * p.cost_price)), 0) as daily_profit
        FROM pos_sale_items psi
        LEFT JOIN pos_sales ps ON psi.sale_id = ps.id
        LEFT JOIN products p ON psi.product_id = p.id
        WHERE DATE(ps.sale_date) >= DATE('now', '-' || ? || ' days')
        AND ps.transaction_type = 'sale'
        GROUP BY DATE(ps.sale_date)
        ORDER BY sale_day
    ''', (days,))

    profit_by_day = {row['sale_day']: row['daily_profit'] for row in cursor.fetchall()}

    conn.close()

    # Generate labels and data for last N days
    from datetime import datetime, timedelta
    labels = []
    sales_data = []
    profit_data = []

    for i in range(days - 1, -1, -1):
        day = (datetime.now() - timedelta(days=i)).strftime('%Y-%m-%d')
        label = (datetime.now() - timedelta(days=i)).strftime('%b %d')
        labels.append(label)
        sales_data.append(float(sales_by_day.get(day, 0)))
        profit_data.append(float(profit_by_day.get(day, 0)))

    return jsonify({
        'labels': labels,
        'sales': sales_data,
        'profit': profit_data
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
    # update_existing = request.form.get('update_existing', 'false') == 'true'
    skip_errors = request.form.get('skip_errors', 'true') == 'true'
    # auto_create = request.form.get('auto_create', 'true') == 'true'

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

@app.route('/api/business-settings', methods=['GET', 'PUT'])
@login_required
def business_settings():
    conn = get_db()
    cursor = conn.cursor()

    if request.method == 'GET':
        cursor.execute('SELECT * FROM business_settings ORDER BY id DESC LIMIT 1')
        settings_row = cursor.fetchone()
        conn.close()

        if settings_row:
            return jsonify(dict(settings_row))
        else:
            # Return default settings if none exist
            return jsonify({
                'business_name': 'My Business',
                'gstin': '',
                'address': '',
                'city': '',
                'state': '',
                'pincode': '',
                'country': 'India',
                'phone': '',
                'email': '',
                'website': '',
                'logo_url': '',
                'currency': 'INR',
                'tax_label': 'GST',
                'invoice_prefix': 'INV',
                'receipt_prefix': 'RCP',
                'terms_conditions': '',
                'bank_name': '',
                'bank_account_number': '',
                'bank_ifsc': '',
                'bank_branch': ''
            })

    elif request.method == 'PUT':
        data = request.json
        if not data:
            conn.close()
            return jsonify({'success': False, 'error': 'Invalid request data'}), 400

        try:
            # Check if settings exist
            cursor.execute('SELECT id FROM business_settings ORDER BY id DESC LIMIT 1')
            existing = cursor.fetchone()

            if existing:
                # Update existing settings
                cursor.execute('''
                    UPDATE business_settings SET
                        business_name = ?, gstin = ?, address = ?, city = ?, state = ?,
                        pincode = ?, country = ?, phone = ?, email = ?, website = ?,
                        logo_url = ?, currency = ?, tax_label = ?, invoice_prefix = ?,
                        receipt_prefix = ?, terms_conditions = ?, bank_name = ?,
                        bank_account_number = ?, bank_ifsc = ?, bank_branch = ?,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                ''', (
                    data.get('business_name', ''), data.get('gstin', ''),
                    data.get('address', ''), data.get('city', ''), data.get('state', ''),
                    data.get('pincode', ''), data.get('country', 'India'),
                    data.get('phone', ''), data.get('email', ''), data.get('website', ''),
                    data.get('logo_url', ''), data.get('currency', 'INR'),
                    data.get('tax_label', 'GST'), data.get('invoice_prefix', 'INV'),
                    data.get('receipt_prefix', 'RCP'), data.get('terms_conditions', ''),
                    data.get('bank_name', ''), data.get('bank_account_number', ''),
                    data.get('bank_ifsc', ''), data.get('bank_branch', ''),
                    existing['id']
                ))
            else:
                # Insert new settings
                cursor.execute('''
                    INSERT INTO business_settings (
                        business_name, gstin, address, city, state, pincode, country,
                        phone, email, website, logo_url, currency, tax_label,
                        invoice_prefix, receipt_prefix, terms_conditions, bank_name,
                        bank_account_number, bank_ifsc, bank_branch
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    data.get('business_name', ''), data.get('gstin', ''),
                    data.get('address', ''), data.get('city', ''), data.get('state', ''),
                    data.get('pincode', ''), data.get('country', 'India'),
                    data.get('phone', ''), data.get('email', ''), data.get('website', ''),
                    data.get('logo_url', ''), data.get('currency', 'INR'),
                    data.get('tax_label', 'GST'), data.get('invoice_prefix', 'INV'),
                    data.get('receipt_prefix', 'RCP'), data.get('terms_conditions', ''),
                    data.get('bank_name', ''), data.get('bank_account_number', ''),
                    data.get('bank_ifsc', ''), data.get('bank_branch', '')
                ))

            conn.commit()
            log_audit(user_id=session.get('user_id'), action='update_business_settings', details="Updated business settings.")
            conn.close()
            return jsonify({'success': True})
        except Exception as e:
            conn.rollback()
            conn.close()
            return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/import/products', methods=['POST'])
@login_required
def import_products():
    if 'file' not in request.files:
        return jsonify({'success': False, 'error': 'No file provided'}), 400

    file = request.files['file']
    # first_row_headers = request.form.get('first_row_headers', 'true') == 'true' # Not used
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

        log_audit(user_id=session.get('user_id'), action='import_products', details=f"Imported: {imported}, Updated: {updated}, Created Categories: {created_categories}, Brands: {created_brands}, Models: {created_models}. Errors: {len(errors)}.")

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

@app.route('/api/pos/sales', methods=['GET', 'POST'])
@login_required
def pos_sales():
    conn = get_db()
    cursor = conn.cursor()

    if request.method == 'POST':
        data = request.json
        if not data:
            conn.close()
            return jsonify({'success': False, 'error': 'Invalid request data'}), 400

        try:
            transaction_type = data.get('transaction_type', 'sale')
            sale_number_prefix = 'RET' if transaction_type == 'return' else 'EXC' if transaction_type == 'exchange' else 'POS'
            sale_number = f"{sale_number_prefix}-{datetime.now().strftime('%Y%m%d%H%M%S')}"
            items = data.get('items', [])

            if not items:
                return jsonify({'success': False, 'error': 'No items in sale'}), 400

            # Calculate totals
            subtotal = sum(item['quantity'] * item['unit_price'] for item in items)
            discount_percentage = float(data.get('discount_percentage', 0))
            tax_percentage = float(data.get('tax_percentage', 0))

            discount_amount = subtotal * (discount_percentage / 100)
            taxable_amount = subtotal - discount_amount
            tax_amount = taxable_amount * (tax_percentage / 100)
            total_amount = taxable_amount + tax_amount

            # For returns, make amount negative
            if transaction_type == 'return':
                total_amount = -abs(total_amount)
                subtotal = -abs(subtotal)

            # Auto-save customer to customers table if phone number is provided
            customer_phone = data.get('customer_phone', '').strip()
            customer_name = data.get('customer_name', '').strip()
            customer_email = data.get('customer_email', '').strip()

            if customer_phone and customer_name:
                try:
                    # Check if customer already exists by phone
                    cursor.execute('SELECT id FROM customers WHERE phone = ?', (customer_phone,))
                    existing_customer = cursor.fetchone()

                    if not existing_customer:
                        # Create new customer record
                        cursor.execute('''
                            INSERT INTO customers (name, phone, email, status)
                            VALUES (?, ?, ?, ?)
                        ''', (customer_name, customer_phone, customer_email, 'active'))
                    else:
                        # Update existing customer (in case name or email changed)
                        cursor.execute('''
                            UPDATE customers
                            SET name = ?, email = ?, updated_at = CURRENT_TIMESTAMP
                            WHERE phone = ?
                        ''', (customer_name, customer_email, customer_phone))
                except sqlite3.IntegrityError:
                    # Phone number already exists, skip customer save for this transaction
                    pass

            # Create sale record
            cursor.execute('''
                INSERT INTO pos_sales (
                    sale_number, customer_name, customer_phone, customer_email,
                    sale_date, subtotal, discount_amount, discount_percentage,
                    tax_amount, tax_percentage, total_amount,
                    payment_method, payment_status, transaction_type, original_sale_id,
                    notes, cashier_name
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                sale_number, data.get('customer_name'), data.get('customer_phone'),
                data.get('customer_email'), data.get('sale_date', datetime.now().strftime('%Y-%m-%d %H:%M:%S')),
                subtotal, discount_amount, discount_percentage,
                tax_amount, tax_percentage, total_amount, data.get('payment_method', 'cash'),
                'paid', transaction_type, data.get('original_sale_id'),
                data.get('notes'), session.get('username')
            ))

            sale_id = cursor.lastrowid

            # Add sale items and update stock
            for item in items:
                product_id = item['product_id']
                quantity = item['quantity']
                unit_price = item['unit_price']
                item_total = quantity * unit_price

                # Check stock
                cursor.execute('SELECT current_stock, name FROM products WHERE id = ?', (product_id,))
                product = cursor.fetchone()
                if not product:
                    raise ValueError(f'Product ID {product_id} not found')

                # For regular sales, check stock availability
                if transaction_type == 'sale' and product['current_stock'] < quantity:
                    raise ValueError(f'Insufficient stock for {product["name"]}')

                # Get IMEI IDs and manual IMEIs
                imei_ids = item.get('imei_ids', [])
                manual_imeis = item.get('manual_imeis', [])
                imei_string = None
                created_imei_ids = []

                # Handle selected IMEIs (from inventory)
                if imei_ids:
                    if len(imei_ids) != quantity:
                        raise ValueError(f'Number of selected IMEIs ({len(imei_ids)}) must match quantity ({quantity}) for {product["name"]}')

                    # Validate all IMEIs exist and are available (both 'available' and 'in_stock' statuses)
                    placeholders = ','.join('?' * len(imei_ids))
                    cursor.execute(f'''
                        SELECT id, imei FROM product_imei
                        WHERE id IN ({placeholders}) AND product_id = ? AND status IN ('available', 'in_stock')
                    ''', (*imei_ids, product_id))

                    available_imeis = cursor.fetchall()
                    if len(available_imeis) != len(imei_ids):
                        raise ValueError(f'One or more selected IMEIs are not available for {product["name"]}')

                    # Store comma-separated IMEI numbers for display
                    imei_string = ','.join([row['imei'] for row in available_imeis])

                # Handle manual IMEIs (new entries)
                elif manual_imeis:
                    if len(manual_imeis) != quantity:
                        raise ValueError(f'Number of manual IMEIs ({len(manual_imeis)}) must match quantity ({quantity}) for {product["name"]}')

                    # Validate IMEI format (15 digits)
                    for imei in manual_imeis:
                        imei_clean = imei.strip()
                        if not imei_clean or len(imei_clean) != 15 or not imei_clean.isdigit():
                            raise ValueError(f'Invalid IMEI format: {imei_clean}. IMEI must be exactly 15 digits.')

                    # Check for duplicates within the payload
                    if len(manual_imeis) != len(set(manual_imeis)):
                        raise ValueError(f'Duplicate IMEIs found in the submission for {product["name"]}')

                    # Create new IMEI records and mark as sold immediately
                    for imei in manual_imeis:
                        try:
                            cursor.execute('''
                                INSERT INTO product_imei (
                                    product_id, imei, status, sale_id, sold_date, received_date
                                ) VALUES (?, ?, ?, ?, ?, ?)
                            ''', (product_id, imei.strip(), 'sold', sale_id, datetime.now(), datetime.now()))
                            created_imei_ids.append(cursor.lastrowid)
                        except sqlite3.IntegrityError:
                            raise ValueError(f'IMEI {imei} already exists in the system. Cannot use duplicate IMEI.')

                    # Store comma-separated IMEI numbers for display
                    imei_string = ','.join(manual_imeis)

                # Add sale item
                cursor.execute('''
                    INSERT INTO pos_sale_items (
                        sale_id, product_id, product_name, sku, quantity,
                        unit_price, total_price, imei
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    sale_id, product_id, product['name'], item.get('sku'),
                    quantity, unit_price, item_total, imei_string
                ))

                # Update stock based on transaction type
                if transaction_type == 'sale' or transaction_type == 'exchange':
                    # Deduct stock for sales and exchanges
                    cursor.execute(
                        'UPDATE products SET current_stock = current_stock - ? WHERE id = ?',
                        (quantity, product_id)
                    )
                    movement_type = 'sale' if transaction_type == 'sale' else 'exchange'
                    movement_qty = -quantity

                    # Mark IMEIs as sold if provided
                    if imei_ids:
                        placeholders = ','.join('?' * len(imei_ids))
                        cursor.execute(f'''
                            UPDATE product_imei
                            SET status = 'sold', sale_id = ?, sold_date = ?
                            WHERE id IN ({placeholders}) AND product_id = ? AND status IN ('available', 'in_stock')
                        ''', (sale_id, datetime.now(), *imei_ids, product_id))

                        # Verify all IMEIs were updated (atomic check for race conditions)
                        if cursor.rowcount != len(imei_ids):
                            raise ValueError(f'Failed to mark all IMEIs as sold for {product["name"]}. Some IMEIs may have been sold by another transaction.')
                elif transaction_type == 'return':
                    # Add stock back for returns
                    cursor.execute(
                        'UPDATE products SET current_stock = current_stock + ? WHERE id = ?',
                        (quantity, product_id)
                    )
                    movement_type = 'return'
                    movement_qty = quantity

                    # Mark IMEIs as available again if IMEI IDs provided
                    if imei_ids:
                        # Validate that these IMEIs belong to this product and are sold
                        placeholders = ','.join('?' * len(imei_ids))
                        cursor.execute(f'''
                            SELECT id FROM product_imei
                            WHERE id IN ({placeholders}) AND product_id = ? AND status = 'sold'
                        ''', (*imei_ids, product_id))

                        sold_imeis = cursor.fetchall()
                        if len(sold_imeis) != len(imei_ids):
                            raise ValueError(f'One or more selected IMEIs cannot be returned for {product["name"]}')

                        # Mark as available again
                        cursor.execute(f'''
                            UPDATE product_imei
                            SET status = 'available', sale_id = NULL, sold_date = NULL
                            WHERE id IN ({placeholders}) AND product_id = ? AND status = 'sold'
                        ''', (*imei_ids, product_id))

                        # Verify all IMEIs were updated (atomic check for race conditions)
                        if cursor.rowcount != len(imei_ids):
                            raise ValueError(f'Failed to mark all IMEIs as available for {product["name"]}. Some IMEIs may have been modified by another transaction.')
                else:
                    # Invalid transaction type
                    raise ValueError(f'Invalid transaction type: {transaction_type}. Must be "sale", "exchange", or "return".')

                # Record stock movement
                cursor.execute('''
                    INSERT INTO stock_movements (
                        product_id, type, quantity, reference_type, reference_id, notes
                    ) VALUES (?, ?, ?, ?, ?, ?)
                ''', (product_id, movement_type, movement_qty, 'pos_sale', sale_id, f'POS {transaction_type.title()} {sale_number}'))

            # Record payment
            if data.get('payment_method'):
                cursor.execute('''
                    INSERT INTO pos_payments (sale_id, payment_method, amount, reference_number)
                    VALUES (?, ?, ?, ?)
                ''', (sale_id, data.get('payment_method'), abs(total_amount), data.get('payment_reference')))

            conn.commit()
            log_audit(user_id=session.get('user_id'), action='create_pos_sale', target_type='pos_sale', target_id=sale_id, details=f"Created POS {transaction_type.title()} {sale_number}. Total Amount: {total_amount}.")
            return jsonify({
                'success': True,
                'sale_id': sale_id,
                'sale_number': sale_number,
                'total_amount': total_amount,
                'transaction_type': transaction_type
            })

        except ValueError as e: # Catch specific value errors like insufficient stock or invalid IMEI
            conn.rollback()
            return jsonify({'success': False, 'error': str(e)}), 400
        except Exception as e:
            conn.rollback()
            return jsonify({'success': False, 'error': str(e)}), 500
        finally:
            conn.close()

    else: # GET request - List all sales
        cursor.execute('''
            SELECT * FROM pos_sales
            ORDER BY created_at DESC
            LIMIT 100
        ''')
        sales = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return jsonify(sales)

@app.route('/api/pos/sales/<int:id>', methods=['GET'])
@login_required
def get_pos_sale(id):
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute('SELECT * FROM pos_sales WHERE id = ?', (id,))
    sale = cursor.fetchone()

    if not sale:
        conn.close()
        return jsonify({'error': 'Sale not found'}), 404

    sale_dict = dict(sale)

    cursor.execute('''
        SELECT psi.*, p.sku, p.brand_id, p.category_id
        FROM pos_sale_items psi
        LEFT JOIN products p ON psi.product_id = p.id
        WHERE psi.sale_id = ?
    ''', (id,))

    sale_dict['items'] = [dict(row) for row in cursor.fetchall()]
    conn.close()

    return jsonify(sale_dict)

@app.route('/api/pos/products/search', methods=['GET'])
@login_required
def pos_product_search():
    query = request.args.get('q', '').strip()
    category_id = request.args.get('category_id', '').strip()

    if not query:
        return jsonify([])

    conn = get_db()
    cursor = conn.cursor()

    # Search by name, SKU, or IMEI with optional category filter
    search_pattern = f'%{query}%'

    if category_id and category_id != 'all':
        cursor.execute('''
            SELECT DISTINCT p.id, p.name, p.sku, p.selling_price, p.current_stock,
                   p.brand_id, p.model_id, b.name as brand_name, m.name as model_name
            FROM products p
            LEFT JOIN brands b ON p.brand_id = b.id
            LEFT JOIN models m ON p.model_id = m.id
            LEFT JOIN imei_tracking i ON p.id = i.product_id
            WHERE p.status = 'active' 
            AND p.category_id = ?
            AND (p.name LIKE ? OR p.sku LIKE ? OR i.imei LIKE ?)
            ORDER BY p.name
            LIMIT 20
        ''', (category_id, search_pattern, search_pattern, search_pattern))
    else:
        cursor.execute('''
            SELECT DISTINCT p.id, p.name, p.sku, p.selling_price, p.current_stock,
                   p.brand_id, p.model_id, b.name as brand_name, m.name as model_name
            FROM products p
            LEFT JOIN brands b ON p.brand_id = b.id
            LEFT JOIN models m ON p.model_id = m.id
            LEFT JOIN imei_tracking i ON p.id = i.product_id
            WHERE p.status = 'active' 
            AND (p.name LIKE ? OR p.sku LIKE ? OR i.imei LIKE ?)
            ORDER BY p.name
            LIMIT 20
        ''', (search_pattern, search_pattern, search_pattern))

    products = []
    for row in cursor.fetchall():
        products.append({
            'id': row[0],
            'name': row[1],
            'sku': row[2],
            'selling_price': row[3],
            'current_stock': row[4],
            'brand_id': row[5],
            'model_id': row[6],
            'brand_name': row[7],
            'model_name': row[8]
        })

    return jsonify(products)

@app.route('/api/pos/products/by-category', methods=['GET'])
@login_required
def pos_products_by_category():
    category_id = request.args.get('category_id', '').strip()

    if not category_id:
        return jsonify([])

    conn = get_db()
    cursor = conn.cursor()

    if category_id == 'all':
        cursor.execute('''
            SELECT p.id, p.name, p.sku, p.selling_price, p.current_stock,
                   p.brand_id, p.model_id, b.name as brand_name, m.name as model_name
            FROM products p
            LEFT JOIN brands b ON p.brand_id = b.id
            LEFT JOIN models m ON p.model_id = m.id
            WHERE p.status = 'active' AND p.current_stock > 0
            ORDER BY p.name
            LIMIT 50
        ''')
    else:
        cursor.execute('''
            SELECT p.id, p.name, p.sku, p.selling_price, p.current_stock,
                   p.brand_id, p.model_id, b.name as brand_name, m.name as model_name
            FROM products p
            LEFT JOIN brands b ON p.brand_id = b.id
            LEFT JOIN models m ON p.model_id = m.id
            WHERE p.status = 'active' AND p.current_stock > 0 AND p.category_id = ?
            ORDER BY p.name
            LIMIT 50
        ''', (category_id,))

    products = []
    for row in cursor.fetchall():
        products.append({
            'id': row[0],
            'name': row[1],
            'sku': row[2],
            'selling_price': row[3],
            'current_stock': row[4],
            'brand_id': row[5],
            'model_id': row[6],
            'brand_name': row[7],
            'model_name': row[8]
        })

    return jsonify(products)


@app.route('/api/customers', methods=['GET', 'POST'])
@login_required
def customers():
    conn = get_db()
    cursor = conn.cursor()

    if request.method == 'POST':
        data = request.json
        if not data or 'name' not in data or not data['name'].strip():
            conn.close()
            return jsonify({'success': False, 'error': 'Customer name is required'}), 400

        try:
            cursor.execute('''
                INSERT INTO customers (name, phone, email, address, city, state, pincode, gstin, notes, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                data['name'].strip(),
                data.get('phone', '').strip(),
                data.get('email', '').strip(),
                data.get('address', '').strip(),
                data.get('city', '').strip(),
                data.get('state', '').strip(),
                data.get('pincode', '').strip(),
                data.get('gstin', '').strip(),
                data.get('notes', '').strip(),
                data.get('status', 'active')
            ))
            conn.commit()
            customer_id = cursor.lastrowid
            log_audit(user_id=session.get('user_id'), action='create_customer', target_type='customer', target_id=customer_id, details=f"Created customer: {data['name']} (Phone: {data.get('phone', '')})")
            conn.close()
            return jsonify({'success': True, 'id': customer_id})
        except Exception as e:
            conn.close()
            return jsonify({'success': False, 'error': str(e)}), 500
    else:
        search = request.args.get('search', '')
        status = request.args.get('status', '')

        query = 'SELECT * FROM customers WHERE 1=1'
        params = []

        if search:
            query += ' AND (name LIKE ? OR phone LIKE ? OR email LIKE ?)'
            search_param = f'%{search}%'
            params.extend([search_param, search_param, search_param])

        if status:
            query += ' AND status = ?'
            params.append(status)

        query += ' ORDER BY name'

        cursor.execute(query, params)
        customers = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return jsonify(customers)

@app.route('/api/customers/lookup/<phone>', methods=['GET'])
@login_required
def customer_lookup_by_phone(phone):
    """Lookup customer by phone number"""
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute('SELECT * FROM customers WHERE phone = ? AND status = ?', (phone, 'active'))
    customer = cursor.fetchone()
    conn.close()

    if customer:
        return jsonify(dict(customer))
    return jsonify({'error': 'Customer not found'}), 404

@app.route('/api/customers/<int:id>', methods=['GET', 'PUT', 'DELETE'])
@login_required
def customer_detail(id):
    conn = get_db()
    cursor = conn.cursor()

    if request.method == 'GET':
        cursor.execute('SELECT * FROM customers WHERE id = ?', (id,))
        customer = cursor.fetchone()
        conn.close()

        if customer:
            return jsonify(dict(customer))
        return jsonify({'error': 'Customer not found'}), 404

    elif request.method == 'PUT':
        data = request.json
        if not data:
            conn.close()
            return jsonify({'success': False, 'error': 'Invalid request data'}), 400

        try:
            # Check if phone number is being changed to an existing one
            new_phone = data.get('phone', '').strip()
            if new_phone:
                cursor.execute('SELECT id FROM customers WHERE phone = ? AND id != ?', (new_phone, id))
                if cursor.fetchone():
                    return jsonify({'success': False, 'error': 'Phone number already exists for another customer'}), 400

            cursor.execute('''
                UPDATE customers SET
                    name = ?, phone = ?, email = ?, address = ?, city = ?,
                    state = ?, pincode = ?, gstin = ?, notes = ?, status = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (
                data['name'],
                data.get('phone', ''),
                data.get('email', ''),
                data.get('address', ''),
                data.get('city', ''),
                data.get('state', ''),
                data.get('pincode', ''),
                data.get('gstin', ''),
                data.get('notes', ''),
                data.get('status', 'active'),
                id
            ))
            conn.commit()
            log_audit(user_id=session.get('user_id'), action='update_customer', target_type='customer', target_id=id, details=f"Updated customer ID {id}. New details: {data}")
            return jsonify({'success': True})
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 400
        finally:
            conn.close()

    elif request.method == 'DELETE':
        try:
            # Check if customer has associated sales
            # Assuming phone is the link, this check might be insufficient if only phone is stored.
            # A better approach would be to store customer_id in pos_sales.
            # For now, proceed with caution.
            cursor.execute('SELECT COUNT(*) as count FROM pos_sales WHERE customer_phone = ?', (id,)) # Assuming phone is used as a key for lookup, might need adjustment if ID is truly used.
            # Correcting to check based on ID if phone is not unique identifier for POS sales linkage
            # A better approach would be to store customer_id in pos_sales table
            # For now, let's assume phone is the primary link for historical data, or adjust if customer ID is stored.
            # This check might be insufficient if only phone is stored in POS sales.
            # Let's assume we check based on ID for simplicity, though it implies customer ID is stored in pos_sales.
            cursor.execute('SELECT COUNT(*) as count FROM pos_sales WHERE customer_id = ?', (id,)) # If customer_id column exists in pos_sales
            if cursor.fetchone()['count'] > 0:
                 return jsonify({'success': False, 'error': 'Cannot delete customer with associated sales history'}), 400

            cursor.execute('SELECT name, phone FROM customers WHERE id = ?', (id,))
            customer_info = cursor.fetchone()

            cursor.execute('DELETE FROM customers WHERE id = ?', (id,))
            conn.commit()
            log_audit(user_id=session.get('user_id'), action='delete_customer', target_type='customer', target_id=id, details=f"Deleted customer: {customer_info['name']} (Phone: {customer_info['phone']})")
            return jsonify({'success': True})
        except Exception as e:
            conn.rollback()
            return jsonify({'success': False, 'error': str(e)}), 400
        finally:
            conn.close()

# Service Management APIs

@app.route('/api/technicians', methods=['GET', 'POST'])
@login_required
def technicians():
    conn = get_db()
    cursor = conn.cursor()

    if request.method == 'POST':
        data = request.json
        if not data or 'name' not in data:
            conn.close()
            return jsonify({'success': False, 'error': 'Technician name is required'}), 400

        try:
            cursor.execute('''
                INSERT INTO technicians (name, phone, email, specialization, status)
                VALUES (?, ?, ?, ?, ?)
            ''', (data['name'], data.get('phone'), data.get('email'),
                  data.get('specialization'), data.get('status', 'active')))
            conn.commit()
            tech_id = cursor.lastrowid
            log_audit(user_id=session.get('user_id'), action='create_technician', target_type='technician', target_id=tech_id, details=f"Created technician: {data['name']}")
            conn.close()
            return jsonify({'success': True, 'id': tech_id})
        except Exception as e:
            conn.close()
            return jsonify({'success': False, 'error': str(e)}), 400
    else:
        cursor.execute('SELECT * FROM technicians ORDER BY name')
        techs = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return jsonify(techs)

@app.route('/api/technicians/<int:id>', methods=['PUT', 'DELETE'])
@login_required
def technician_detail(id):
    conn = get_db()
    cursor = conn.cursor()

    if request.method == 'PUT':
        data = request.json
        try:
            # Get old data for audit log
            cursor.execute('SELECT name FROM technicians WHERE id = ?', (id,))
            old_name = cursor.fetchone()['name']

            cursor.execute('''
                UPDATE technicians SET name = ?, phone = ?, email = ?,
                specialization = ?, status = ?
                WHERE id = ?
            ''', (data['name'], data.get('phone'), data.get('email'),
                  data.get('specialization'), data.get('status', 'active'), id))
            conn.commit()
            log_audit(user_id=session.get('user_id'), action='update_technician', target_type='technician', target_id=id, details=f"Updated technician '{old_name}' to '{data['name']}'")
            return jsonify({'success': True})
        except Exception as e:
            conn.rollback()
            return jsonify({'success': False, 'error': str(e)}), 400
        finally:
            conn.close()
    elif request.method == 'DELETE':
        try:
            # Check for dependencies
            cursor.execute('SELECT COUNT(*) as count FROM service_jobs WHERE technician_id = ?', (id,))
            if cursor.fetchone()['count'] > 0:
                return jsonify({'success': False, 'error': 'Cannot delete technician with assigned service jobs'}), 400

            cursor.execute('SELECT name FROM technicians WHERE id = ?', (id,))
            tech_name = cursor.fetchone()['name']

            cursor.execute('DELETE FROM technicians WHERE id = ?', (id,))
            conn.commit()
            log_audit(user_id=session.get('user_id'), action='delete_technician', target_type='technician', target_id=id, details=f"Deleted technician: {tech_name}")
            return jsonify({'success': True})
        except Exception as e:
            conn.rollback()
            return jsonify({'success': False, 'error': str(e)}), 400
        finally:
            conn.close()

@app.route('/api/service-jobs', methods=['GET', 'POST'])
@login_required
def service_jobs():
    conn = get_db()
    cursor = conn.cursor()

    if request.method == 'POST':
        data = request.json
        if not data:
            conn.close()
            return jsonify({'success': False, 'error': 'Invalid request data'}), 400

        try:
            job_number = f"SRV-{datetime.now().strftime('%Y%m%d%H%M%S')}"

            cursor.execute('''
                INSERT INTO service_jobs (
                    job_number, customer_name, customer_phone, customer_email,
                    device_brand, device_model, imei_number, problem_description,
                    estimated_cost, advance_payment, estimated_delivery,
                    technician_id, notes, status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (job_number, data['customer_name'], data['customer_phone'],
                  data.get('customer_email'), data.get('device_brand'),
                  data.get('device_model'), data.get('imei_number'),
                  data['problem_description'], data.get('estimated_cost', 0),
                  data.get('advance_payment', 0), data.get('estimated_delivery'),
                  data.get('technician_id'), data.get('notes'), 'received'))

            job_id = cursor.lastrowid

            # Record status history
            cursor.execute('''
                INSERT INTO service_status_history (job_id, new_status, changed_by)
                VALUES (?, ?, ?)
            ''', (job_id, 'received', session.get('username', 'admin')))

            conn.commit()
            log_audit(user_id=session.get('user_id'), action='create_service_job', target_type='service_job', target_id=job_id, details=f"Created service job {job_number} for {data['customer_name']}")
            return jsonify({'success': True, 'id': job_id, 'job_number': job_number})
        except Exception as e:
            conn.rollback()
            return jsonify({'success': False, 'error': str(e)}), 400
        finally:
            conn.close()
    else:
        status = request.args.get('status', '')
        search = request.args.get('search', '')

        query = '''
            SELECT sj.*, t.name as technician_name
            FROM service_jobs sj
            LEFT JOIN technicians t ON sj.technician_id = t.id
            WHERE 1=1
        '''
        params = []

        if status:
            query += ' AND sj.status = ?'
            params.append(status)

        if search:
            query += ' AND (sj.job_number LIKE ? OR sj.customer_name LIKE ? OR sj.customer_phone LIKE ? OR sj.imei_number LIKE ?)'
            search_param = f'%{search}%'
            params.extend([search_param] * 4)

        query += ' ORDER BY sj.created_at DESC'

        cursor.execute(query, params)
        jobs = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return jsonify(jobs)

@app.route('/api/service-jobs/<int:id>', methods=['GET', 'PUT', 'DELETE'])
@login_required
def service_job_detail(id):
    conn = get_db()
    cursor = conn.cursor()

    if request.method == 'GET':
        cursor.execute('''
            SELECT sj.*, t.name as technician_name
            FROM service_jobs sj
            LEFT JOIN technicians t ON sj.technician_id = t.id
            WHERE sj.id = ?
        ''', (id,))
        job = cursor.fetchone()

        if not job:
            conn.close()
            return jsonify({'error': 'Job not found'}), 404

        job_dict = dict(job)

        # Get parts used
        cursor.execute('''
            SELECT spu.*, p.name as product_name
            FROM service_parts_used spu
            LEFT JOIN products p ON spu.product_id = p.id
            WHERE spu.job_id = ?
        ''', (id,))
        job_dict['parts_used'] = [dict(row) for row in cursor.fetchall()]

        # Get labor charges
        cursor.execute('''
            SELECT * FROM service_labor_charges WHERE job_id = ?
        ''', (id,))
        job_dict['labor_charges'] = [dict(row) for row in cursor.fetchall()]

        # Get status history
        cursor.execute('''
            SELECT * FROM service_status_history WHERE job_id = ?
            ORDER BY created_at DESC
        ''', (id,))
        job_dict['status_history'] = [dict(row) for row in cursor.fetchall()]

        conn.close()
        return jsonify(job_dict)

    elif request.method == 'PUT':
        data = request.json
        try:
            old_status = None
            cursor.execute('SELECT status FROM service_jobs WHERE id = ?', (id,))
            row = cursor.fetchone()
            if row:
                old_status = row['status']

            cursor.execute('''
                UPDATE service_jobs SET
                    customer_name = ?, customer_phone = ?, customer_email = ?,
                    device_brand = ?, device_model = ?, imei_number = ?,
                    problem_description = ?, estimated_cost = ?, actual_cost = ?,
                    advance_payment = ?, estimated_delivery = ?, actual_delivery = ?,
                    status = ?, technician_id = ?, notes = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (data['customer_name'], data['customer_phone'],
                  data.get('customer_email'), data.get('device_brand'),
                  data.get('device_model'), data.get('imei_number'),
                  data['problem_description'], data.get('estimated_cost', 0),
                  data.get('actual_cost', 0), data.get('advance_payment', 0),
                  data.get('estimated_delivery'), data.get('actual_delivery'),
                  data.get('status', 'received'), data.get('technician_id'),
                  data.get('notes'), id))

            # Record status change
            new_status = data.get('status', 'received')
            if old_status != new_status:
                cursor.execute('''
                    INSERT INTO service_status_history (job_id, old_status, new_status, changed_by)
                    VALUES (?, ?, ?, ?)
                ''', (id, old_status, new_status, session.get('username', 'admin')))

            conn.commit()
            log_audit(user_id=session.get('user_id'), action='update_service_job', target_type='service_job', target_id=id, details=f"Updated service job ID {id}. Status changed from '{old_status}' to '{new_status}'.")
            return jsonify({'success': True})
        except Exception as e:
            conn.rollback()
            return jsonify({'success': False, 'error': str(e)}), 400
        finally:
            conn.close()

    elif request.method == 'DELETE':
        try:
            # Check for dependencies (e.g., associated parts, labor, history)
            cursor.execute('DELETE FROM service_parts_used WHERE job_id = ?', (id,))
            cursor.execute('DELETE FROM service_labor_charges WHERE job_id = ?', (id,))
            cursor.execute('DELETE FROM service_status_history WHERE job_id = ?', (id,))

            # Get job details for audit log before deleting
            cursor.execute('SELECT job_number, customer_name FROM service_jobs WHERE id = ?', (id,))
            job_info = cursor.fetchone()

            cursor.execute('DELETE FROM service_jobs WHERE id = ?', (id,))
            conn.commit()
            log_audit(user_id=session.get('user_id'), action='delete_service_job', target_type='service_job', target_id=id, details=f"Deleted service job {job_info['job_number']} for {job_info['customer_name']}")
            return jsonify({'success': True})
        except Exception as e:
            conn.rollback()
            return jsonify({'success': False, 'error': str(e)}), 400
        finally:
            conn.close()

@app.route('/api/service-jobs/<int:id>/parts', methods=['POST'])
@login_required
def add_service_parts(id):
    conn = get_db()
    cursor = conn.cursor()
    data = request.json

    try:
        product_id = data.get('product_id')
        part_name = data.get('part_name')
        quantity = data.get('quantity')
        unit_price = data.get('unit_price')

        if not part_name or not quantity or not unit_price:
            return jsonify({'success': False, 'error': 'Part name, quantity, and unit price are required.'}), 400

        if not isinstance(quantity, int) or quantity <= 0:
            return jsonify({'success': False, 'error': 'Quantity must be a positive integer.'}), 400

        total_price = quantity * unit_price

        cursor.execute('''
            INSERT INTO service_parts_used (job_id, product_id, part_name, quantity, unit_price, total_price)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (id, product_id, part_name, quantity, unit_price, total_price))
        part_id = cursor.lastrowid

        # Update product stock if product_id provided and it's a valid product
        if product_id:
            # Verify product exists and has enough stock before deducting
            cursor.execute('SELECT current_stock, name FROM products WHERE id = ?', (product_id,))
            product = cursor.fetchone()
            if not product:
                raise ValueError(f"Product ID {product_id} not found for part '{part_name}'.")

            if product['current_stock'] < quantity:
                raise ValueError(f"Insufficient stock for product '{product['name']}'. Available: {product['current_stock']}, Requested: {quantity}.")

            cursor.execute('''
                UPDATE products SET current_stock = current_stock - ?
                WHERE id = ?
            ''', (quantity, product_id))

        conn.commit()
        log_audit(user_id=session.get('user_id'), action='add_service_part', target_type='service_job', target_id=id, details=f"Added part '{part_name}' (Qty: {quantity}) to Service Job ID {id}.")
        return jsonify({'success': True, 'id': part_id})
    except ValueError as e: # Catch specific validation errors
        conn.rollback()
        return jsonify({'success': False, 'error': str(e)}), 400
    except Exception as e:
        conn.rollback()
        return jsonify({'success': False, 'error': str(e)}), 400
    finally:
        conn.close()

@app.route('/api/service-jobs/<int:job_id>/parts/<int:part_id>', methods=['DELETE'])
@login_required
def delete_service_part(job_id, part_id):
    conn = get_db()
    cursor = conn.cursor()

    try:
        # Get part details before deleting for stock restoration and audit log
        cursor.execute('SELECT product_id, quantity, part_name FROM service_parts_used WHERE id = ? AND job_id = ?', (part_id, job_id))
        part = cursor.fetchone()

        if not part:
            return jsonify({'success': False, 'error': 'Part not found for this job'}), 404

        # Restore stock if a product_id was associated
        if part['product_id']:
            cursor.execute('''
                UPDATE products SET current_stock = current_stock + ?
                WHERE id = ?
            ''', (part['quantity'], part['product_id']))

        cursor.execute('DELETE FROM service_parts_used WHERE id = ?', (part_id,))
        conn.commit()
        log_audit(user_id=session.get('user_id'), action='delete_service_part', target_type='service_job', target_id=job_id, details=f"Deleted part '{part['part_name']}' (Qty: {part['quantity']}) from Service Job ID {job_id}.")
        return jsonify({'success': True})
    except Exception as e:
        conn.rollback()
        return jsonify({'success': False, 'error': str(e)}), 400
    finally:
        conn.close()

@app.route('/api/service-jobs/<int:id>/labor', methods=['POST'])
@login_required
def add_service_labor(id):
    conn = get_db()
    cursor = conn.cursor()
    data = request.json

    try:
        description = data.get('description')
        amount = data.get('amount')

        if not description or amount is None:
            return jsonify({'success': False, 'error': 'Description and amount are required.'}), 400
        if not isinstance(amount, (int, float)) or amount < 0:
            return jsonify({'success': False, 'error': 'Amount must be a non-negative number.'}), 400

        cursor.execute('''
            INSERT INTO service_labor_charges (job_id, description, amount)
            VALUES (?, ?, ?)
        ''', (id, description, amount))
        conn.commit()
        labor_id = cursor.lastrowid
        log_audit(user_id=session.get('user_id'), action='add_service_labor', target_type='service_job', target_id=id, details=f"Added labor charge '{description}' (Amount: {amount}) to Service Job ID {id}.")
        return jsonify({'success': True, 'id': labor_id})
    except Exception as e:
        conn.rollback()
        return jsonify({'success': False, 'error': str(e)}), 400
    finally:
        conn.close()

@app.route('/api/service-jobs/<int:job_id>/labor/<int:labor_id>', methods=['DELETE'])
@login_required
def delete_service_labor(job_id, labor_id):
    conn = get_db()
    cursor = conn.cursor()

    try:
        # Get labor details for audit log
        cursor.execute('SELECT description, amount FROM service_labor_charges WHERE id = ? AND job_id = ?', (labor_id, job_id))
        labor_info = cursor.fetchone()
        if not labor_info:
            return jsonify({'success': False, 'error': 'Labor charge not found for this job'}), 404

        cursor.execute('DELETE FROM service_labor_charges WHERE id = ?', (labor_id,))
        conn.commit()
        log_audit(user_id=session.get('user_id'), action='delete_service_labor', target_type='service_job', target_id=job_id, details=f"Deleted labor charge '{labor_info['description']}' (Amount: {labor_info['amount']}) from Service Job ID {job_id}.")
        return jsonify({'success': True})
    except Exception as e:
        conn.rollback()
        return jsonify({'success': False, 'error': str(e)}), 400
    finally:
        conn.close()

if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=5000, debug=True)