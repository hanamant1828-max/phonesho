
from flask import Blueprint, request, jsonify
import sqlite3
from auth import (
    hash_password, verify_password, generate_token, log_audit,
    require_auth, require_permission, require_role, get_user_permissions
)

user_bp = Blueprint('users', __name__)

def get_db_connection():
    conn = sqlite3.connect('mobile_shop.db')
    conn.row_factory = sqlite3.Row
    return conn

# Authentication routes
@user_bp.route('/login', methods=['POST'])
def login():
    """User login endpoint"""
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    
    if not username or not password:
        return jsonify({'error': 'Username and password required'}), 400
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT u.*, r.role_name 
        FROM users u 
        JOIN roles r ON u.role_id = r.id 
        WHERE u.username = ?
    ''', (username,))
    
    user = cursor.fetchone()
    
    if not user:
        conn.close()
        return jsonify({'error': 'Invalid credentials'}), 401
    
    # Check account status
    if user['status'] == 'locked':
        conn.close()
        return jsonify({'error': 'Account is locked. Contact administrator'}), 403
    
    if user['status'] == 'inactive':
        conn.close()
        return jsonify({'error': 'Account is inactive'}), 403
    
    # Verify password
    if not verify_password(password, user['password_hash']):
        # Increment failed login attempts
        failed_attempts = user['failed_login_attempts'] + 1
        
        if failed_attempts >= 5:
            cursor.execute('UPDATE users SET status = ?, failed_login_attempts = ? WHERE id = ?',
                         ('locked', failed_attempts, user['id']))
            conn.commit()
            conn.close()
            
            log_audit(user['id'], 'account_locked', 'Account locked due to multiple failed login attempts',
                     request.remote_addr, request.headers.get('User-Agent'))
            
            return jsonify({'error': 'Account locked due to multiple failed login attempts'}), 403
        
        cursor.execute('UPDATE users SET failed_login_attempts = ? WHERE id = ?',
                     (failed_attempts, user['id']))
        conn.commit()
        conn.close()
        
        return jsonify({'error': 'Invalid credentials'}), 401
    
    # Successful login - reset failed attempts and update last login
    cursor.execute('''
        UPDATE users 
        SET failed_login_attempts = 0, last_login_at = CURRENT_TIMESTAMP 
        WHERE id = ?
    ''', (user['id'],))
    
    conn.commit()
    conn.close()
    
    # Generate token
    token = generate_token(user['id'], user['username'], user['role_id'])
    
    # Get user permissions
    permissions = get_user_permissions(user['id'])
    
    # Log successful login
    log_audit(user['id'], 'login', 'User logged in successfully',
             request.remote_addr, request.headers.get('User-Agent'))
    
    return jsonify({
        'token': token,
        'user': {
            'id': user['id'],
            'name': user['name'],
            'username': user['username'],
            'email': user['email'],
            'role': user['role_name'],
            'is_password_reset_required': bool(user['is_password_reset_required'])
        },
        'permissions': permissions
    })

@user_bp.route('/logout', methods=['POST'])
@require_auth
def logout():
    """User logout endpoint"""
    log_audit(request.current_user['user_id'], 'logout', 'User logged out',
             request.remote_addr, request.headers.get('User-Agent'))
    
    return jsonify({'message': 'Logged out successfully'})

# User management routes
@user_bp.route('/users', methods=['GET'])
@require_auth
@require_permission('settings.users')
def get_users():
    """Get all users"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT u.id, u.name, u.username, u.email, u.phone, u.status, 
               u.last_login_at, u.created_at, r.role_name
        FROM users u
        JOIN roles r ON u.role_id = r.id
        ORDER BY u.created_at DESC
    ''')
    
    users = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    return jsonify(users)

@user_bp.route('/users', methods=['POST'])
@require_auth
@require_permission('settings.users')
def create_user():
    """Create new user"""
    data = request.get_json()
    
    required_fields = ['name', 'username', 'password', 'role_id']
    if not all(field in data for field in required_fields):
        return jsonify({'error': 'Missing required fields'}), 400
    
    # Hash password
    password_hash = hash_password(data['password'])
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            INSERT INTO users (name, username, email, phone, password_hash, role_id, status)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (data['name'], data['username'], data.get('email'), data.get('phone'),
              password_hash, data['role_id'], data.get('status', 'active')))
        
        user_id = cursor.lastrowid
        conn.commit()
        
        log_audit(request.current_user['user_id'], 'user_created',
                 f"Created user: {data['username']}", request.remote_addr,
                 request.headers.get('User-Agent'), {'new_user_id': user_id})
        
        return jsonify({'id': user_id, 'message': 'User created successfully'}), 201
    
    except sqlite3.IntegrityError as e:
        conn.rollback()
        return jsonify({'error': 'Username or email already exists'}), 400
    finally:
        conn.close()

@user_bp.route('/users/<int:user_id>', methods=['GET'])
@require_auth
@require_permission('settings.users')
def get_user(user_id):
    """Get user details"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT u.id, u.name, u.username, u.email, u.phone, u.status,
               u.role_id, u.last_login_at, u.created_at, r.role_name
        FROM users u
        JOIN roles r ON u.role_id = r.id
        WHERE u.id = ?
    ''', (user_id,))
    
    user = cursor.fetchone()
    conn.close()
    
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    return jsonify(dict(user))

@user_bp.route('/users/<int:user_id>', methods=['PUT'])
@require_auth
@require_permission('settings.users')
def update_user(user_id):
    """Update user details"""
    data = request.get_json()
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Build update query dynamically
    fields = []
    values = []
    
    if 'name' in data:
        fields.append('name = ?')
        values.append(data['name'])
    
    if 'email' in data:
        fields.append('email = ?')
        values.append(data['email'])
    
    if 'phone' in data:
        fields.append('phone = ?')
        values.append(data['phone'])
    
    if 'role_id' in data:
        fields.append('role_id = ?')
        values.append(data['role_id'])
    
    if not fields:
        return jsonify({'error': 'No fields to update'}), 400
    
    fields.append('updated_at = CURRENT_TIMESTAMP')
    values.append(user_id)
    
    query = f"UPDATE users SET {', '.join(fields)} WHERE id = ?"
    
    try:
        cursor.execute(query, values)
        conn.commit()
        
        log_audit(request.current_user['user_id'], 'user_updated',
                 f"Updated user ID: {user_id}", request.remote_addr,
                 request.headers.get('User-Agent'), {'updated_user_id': user_id})
        
        return jsonify({'message': 'User updated successfully'})
    
    except sqlite3.IntegrityError:
        conn.rollback()
        return jsonify({'error': 'Email already exists'}), 400
    finally:
        conn.close()

@user_bp.route('/users/<int:user_id>/status', methods=['PATCH'])
@require_auth
@require_permission('settings.users')
def update_user_status(user_id):
    """Activate/deactivate user"""
    data = request.get_json()
    status = data.get('status')
    
    if status not in ['active', 'inactive', 'locked']:
        return jsonify({'error': 'Invalid status'}), 400
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('UPDATE users SET status = ? WHERE id = ?', (status, user_id))
    conn.commit()
    conn.close()
    
    log_audit(request.current_user['user_id'], 'user_status_changed',
             f"Changed user {user_id} status to {status}", request.remote_addr,
             request.headers.get('User-Agent'))
    
    return jsonify({'message': f'User status updated to {status}'})

@user_bp.route('/users/<int:user_id>/reset-password', methods=['POST'])
@require_auth
@require_permission('settings.users')
def reset_user_password(user_id):
    """Reset user password (admin function)"""
    data = request.get_json()
    new_password = data.get('password')
    
    if not new_password or len(new_password) < 6:
        return jsonify({'error': 'Password must be at least 6 characters'}), 400
    
    password_hash = hash_password(new_password)
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        UPDATE users 
        SET password_hash = ?, is_password_reset_required = 1, failed_login_attempts = 0, status = 'active'
        WHERE id = ?
    ''', (password_hash, user_id))
    
    conn.commit()
    conn.close()
    
    log_audit(request.current_user['user_id'], 'password_reset',
             f"Reset password for user ID: {user_id}", request.remote_addr,
             request.headers.get('User-Agent'))
    
    return jsonify({'message': 'Password reset successfully'})

# Role management routes
@user_bp.route('/roles', methods=['GET'])
@require_auth
def get_roles():
    """Get all roles"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM roles ORDER BY role_name')
    roles = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    return jsonify(roles)

@user_bp.route('/roles', methods=['POST'])
@require_auth
@require_permission('settings.roles')
def create_role():
    """Create new role"""
    data = request.get_json()
    
    if not data.get('role_name'):
        return jsonify({'error': 'Role name is required'}), 400
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute('INSERT INTO roles (role_name, description) VALUES (?, ?)',
                     (data['role_name'], data.get('description')))
        role_id = cursor.lastrowid
        conn.commit()
        
        log_audit(request.current_user['user_id'], 'role_created',
                 f"Created role: {data['role_name']}", request.remote_addr,
                 request.headers.get('User-Agent'))
        
        return jsonify({'id': role_id, 'message': 'Role created successfully'}), 201
    
    except sqlite3.IntegrityError:
        conn.rollback()
        return jsonify({'error': 'Role name already exists'}), 400
    finally:
        conn.close()

@user_bp.route('/roles/<int:role_id>', methods=['PUT'])
@require_auth
@require_permission('settings.roles')
def update_role(role_id):
    """Update role details"""
    data = request.get_json()
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('UPDATE roles SET role_name = ?, description = ? WHERE id = ?',
                 (data['role_name'], data.get('description'), role_id))
    conn.commit()
    conn.close()
    
    log_audit(request.current_user['user_id'], 'role_updated',
             f"Updated role ID: {role_id}", request.remote_addr,
             request.headers.get('User-Agent'))
    
    return jsonify({'message': 'Role updated successfully'})

# Permission management routes
@user_bp.route('/permissions', methods=['GET'])
@require_auth
def get_permissions():
    """Get all permissions"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM permissions ORDER BY module, permission_name')
    permissions = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    return jsonify(permissions)

@user_bp.route('/roles/<int:role_id>/permissions', methods=['GET'])
@require_auth
@require_permission('settings.roles')
def get_role_permissions(role_id):
    """Get permissions for a specific role"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT p.*
        FROM permissions p
        JOIN role_permissions rp ON p.id = rp.permission_id
        WHERE rp.role_id = ?
    ''', (role_id,))
    
    permissions = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    return jsonify(permissions)

@user_bp.route('/roles/<int:role_id>/permissions', methods=['PUT'])
@require_auth
@require_permission('settings.roles')
def update_role_permissions(role_id):
    """Update permissions for a role"""
    data = request.get_json()
    permission_ids = data.get('permission_ids', [])
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Delete existing permissions
    cursor.execute('DELETE FROM role_permissions WHERE role_id = ?', (role_id,))
    
    # Insert new permissions
    for perm_id in permission_ids:
        cursor.execute('INSERT INTO role_permissions (role_id, permission_id) VALUES (?, ?)',
                     (role_id, perm_id))
    
    conn.commit()
    conn.close()
    
    log_audit(request.current_user['user_id'], 'permissions_updated',
             f"Updated permissions for role ID: {role_id}", request.remote_addr,
             request.headers.get('User-Agent'))
    
    return jsonify({'message': 'Role permissions updated successfully'})

# Audit log routes
@user_bp.route('/audit-logs', methods=['GET'])
@require_auth
@require_role('Admin')
def get_audit_logs():
    """Get audit logs with filtering"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 50, type=int)
    user_id = request.args.get('user_id', type=int)
    action_type = request.args.get('action_type')
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Build query with filters
    query = '''
        SELECT al.*, u.username, u.name
        FROM audit_logs al
        LEFT JOIN users u ON al.user_id = u.id
        WHERE 1=1
    '''
    params = []
    
    if user_id:
        query += ' AND al.user_id = ?'
        params.append(user_id)
    
    if action_type:
        query += ' AND al.action_type = ?'
        params.append(action_type)
    
    if start_date:
        query += ' AND al.created_at >= ?'
        params.append(start_date)
    
    if end_date:
        query += ' AND al.created_at <= ?'
        params.append(end_date)
    
    query += ' ORDER BY al.created_at DESC LIMIT ? OFFSET ?'
    params.extend([per_page, (page - 1) * per_page])
    
    cursor.execute(query, params)
    logs = [dict(row) for row in cursor.fetchall()]
    
    # Get total count
    count_query = query.split('ORDER BY')[0].replace('SELECT al.*, u.username, u.name', 'SELECT COUNT(*)')
    cursor.execute(count_query, params[:-2])
    total = cursor.fetchone()[0]
    
    conn.close()
    
    return jsonify({
        'logs': logs,
        'total': total,
        'page': page,
        'per_page': per_page,
        'pages': (total + per_page - 1) // per_page
    })
