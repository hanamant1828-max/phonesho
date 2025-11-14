
from flask import Blueprint, request, jsonify, session
from auth import login_required, admin_required, permission_required, log_audit, check_permission
import sqlite3
import bcrypt
from datetime import datetime

user_bp = Blueprint('user_management', __name__)

def get_db():
    conn = sqlite3.connect('inventory.db')
    conn.row_factory = sqlite3.Row
    return conn

# User Management Endpoints

@user_bp.route('/api/users', methods=['GET'])
@login_required
@permission_required('settings.manage_users')
def get_users():
    """Get list of all users"""
    conn = get_db()
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            SELECT u.id, u.name, u.username, u.email, u.phone, u.status,
                   u.last_login_at, u.created_at, r.role_name, r.id as role_id
            FROM users u
            JOIN roles r ON u.role_id = r.id
            ORDER BY u.created_at DESC
        ''')
        users = [dict(row) for row in cursor.fetchall()]
        return jsonify(users)
    finally:
        conn.close()

@user_bp.route('/api/users/<int:user_id>', methods=['GET'])
@login_required
@permission_required('settings.manage_users')
def get_user(user_id):
    """Get single user details"""
    conn = get_db()
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            SELECT u.*, r.role_name
            FROM users u
            JOIN roles r ON u.role_id = r.id
            WHERE u.id = ?
        ''', (user_id,))
        user = cursor.fetchone()
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        return jsonify(dict(user))
    finally:
        conn.close()

@user_bp.route('/api/users', methods=['POST'])
@login_required
@permission_required('settings.manage_users')
def create_user():
    """Create new user"""
    data = request.get_json()
    
    # Validate required fields
    required = ['name', 'username', 'password', 'role_id']
    if not all(k in data for k in required):
        return jsonify({'error': 'Missing required fields'}), 400
    
    # Hash password
    password_hash = bcrypt.hashpw(data['password'].encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    conn = get_db()
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            INSERT INTO users (name, username, email, phone, password_hash, role_id, status)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            data['name'],
            data['username'],
            data.get('email'),
            data.get('phone'),
            password_hash,
            data['role_id'],
            data.get('status', 'active')
        ))
        conn.commit()
        
        user_id = cursor.lastrowid
        
        # Log activity
        log_audit(session['user_id'], 'user_created', 
                 f'Created new user: {data["username"]}',
                 request.remote_addr, request.headers.get('User-Agent'))
        
        return jsonify({'success': True, 'user_id': user_id}), 201
    
    except sqlite3.IntegrityError:
        return jsonify({'error': 'Username already exists'}), 400
    finally:
        conn.close()

@user_bp.route('/api/users/<int:user_id>', methods=['PUT'])
@login_required
@permission_required('settings.manage_users')
def update_user(user_id):
    """Update user details"""
    data = request.get_json()
    
    conn = get_db()
    cursor = conn.cursor()
    
    try:
        # Build update query dynamically
        update_fields = []
        params = []
        
        if 'name' in data:
            update_fields.append('name = ?')
            params.append(data['name'])
        if 'email' in data:
            update_fields.append('email = ?')
            params.append(data['email'])
        if 'phone' in data:
            update_fields.append('phone = ?')
            params.append(data['phone'])
        if 'role_id' in data:
            update_fields.append('role_id = ?')
            params.append(data['role_id'])
        
        if not update_fields:
            return jsonify({'error': 'No fields to update'}), 400
        
        update_fields.append('updated_at = ?')
        params.append(datetime.now())
        params.append(user_id)
        
        query = f"UPDATE users SET {', '.join(update_fields)} WHERE id = ?"
        cursor.execute(query, params)
        conn.commit()
        
        # Log activity
        log_audit(session['user_id'], 'user_updated', 
                 f'Updated user ID: {user_id}',
                 request.remote_addr, request.headers.get('User-Agent'))
        
        return jsonify({'success': True})
    
    except sqlite3.IntegrityError:
        return jsonify({'error': 'Update failed'}), 400
    finally:
        conn.close()

@user_bp.route('/api/users/<int:user_id>/status', methods=['PATCH'])
@login_required
@permission_required('settings.manage_users')
def update_user_status(user_id):
    """Activate/Deactivate user"""
    data = request.get_json()
    status = data.get('status')
    
    if status not in ['active', 'inactive', 'locked']:
        return jsonify({'error': 'Invalid status'}), 400
    
    conn = get_db()
    cursor = conn.cursor()
    
    try:
        cursor.execute('UPDATE users SET status = ? WHERE id = ?', (status, user_id))
        conn.commit()
        
        # Log activity
        log_audit(session['user_id'], 'user_status_changed', 
                 f'Changed user ID {user_id} status to: {status}',
                 request.remote_addr, request.headers.get('User-Agent'))
        
        return jsonify({'success': True})
    finally:
        conn.close()

@user_bp.route('/api/users/<int:user_id>/reset-password', methods=['POST'])
@login_required
@permission_required('settings.manage_users')
def reset_user_password(user_id):
    """Reset user password"""
    data = request.get_json()
    new_password = data.get('new_password')
    
    if not new_password or len(new_password) < 6:
        return jsonify({'error': 'Password must be at least 6 characters'}), 400
    
    password_hash = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    conn = get_db()
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            UPDATE users 
            SET password_hash = ?, is_password_reset_required = 1, failed_login_attempts = 0
            WHERE id = ?
        ''', (password_hash, user_id))
        conn.commit()
        
        # Log activity
        log_audit(session['user_id'], 'password_reset', 
                 f'Reset password for user ID: {user_id}',
                 request.remote_addr, request.headers.get('User-Agent'))
        
        return jsonify({'success': True})
    finally:
        conn.close()

# Role Management Endpoints

@user_bp.route('/api/roles', methods=['GET'])
@login_required
def get_roles():
    """Get all roles"""
    conn = get_db()
    cursor = conn.cursor()
    
    try:
        cursor.execute('SELECT * FROM roles ORDER BY id')
        roles = [dict(row) for row in cursor.fetchall()]
        return jsonify(roles)
    finally:
        conn.close()

@user_bp.route('/api/roles', methods=['POST'])
@login_required
@permission_required('settings.manage_roles')
def create_role():
    """Create new role"""
    data = request.get_json()
    
    if not data.get('role_name'):
        return jsonify({'error': 'Role name required'}), 400
    
    conn = get_db()
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            INSERT INTO roles (role_name, description)
            VALUES (?, ?)
        ''', (data['role_name'], data.get('description')))
        conn.commit()
        
        role_id = cursor.lastrowid
        
        # Log activity
        log_audit(session['user_id'], 'role_created', 
                 f'Created new role: {data["role_name"]}',
                 request.remote_addr, request.headers.get('User-Agent'))
        
        return jsonify({'success': True, 'role_id': role_id}), 201
    
    except sqlite3.IntegrityError:
        return jsonify({'error': 'Role name already exists'}), 400
    finally:
        conn.close()

@user_bp.route('/api/roles/<int:role_id>', methods=['PUT'])
@login_required
@permission_required('settings.manage_roles')
def update_role(role_id):
    """Update role details"""
    data = request.get_json()
    
    conn = get_db()
    cursor = conn.cursor()
    
    try:
        # Check if it's a default role
        cursor.execute('SELECT is_default FROM roles WHERE id = ?', (role_id,))
        role = cursor.fetchone()
        
        if role and role['is_default']:
            return jsonify({'error': 'Cannot modify default roles'}), 400
        
        cursor.execute('''
            UPDATE roles 
            SET role_name = ?, description = ?
            WHERE id = ?
        ''', (data['role_name'], data.get('description'), role_id))
        conn.commit()
        
        # Log activity
        log_audit(session['user_id'], 'role_updated', 
                 f'Updated role ID: {role_id}',
                 request.remote_addr, request.headers.get('User-Agent'))
        
        return jsonify({'success': True})
    finally:
        conn.close()

# Permission Management Endpoints

@user_bp.route('/api/permissions', methods=['GET'])
@login_required
def get_permissions():
    """Get all permissions grouped by module"""
    conn = get_db()
    cursor = conn.cursor()
    
    try:
        cursor.execute('SELECT * FROM permissions ORDER BY module, permission_name')
        permissions = [dict(row) for row in cursor.fetchall()]
        return jsonify(permissions)
    finally:
        conn.close()

@user_bp.route('/api/roles/<int:role_id>/permissions', methods=['GET'])
@login_required
@permission_required('settings.manage_roles')
def get_role_permissions(role_id):
    """Get permissions for a specific role"""
    conn = get_db()
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            SELECT p.*
            FROM permissions p
            JOIN role_permissions rp ON p.id = rp.permission_id
            WHERE rp.role_id = ?
            ORDER BY p.module, p.permission_name
        ''', (role_id,))
        permissions = [dict(row) for row in cursor.fetchall()]
        return jsonify(permissions)
    finally:
        conn.close()

@user_bp.route('/api/roles/<int:role_id>/permissions', methods=['PUT'])
@login_required
@permission_required('settings.manage_roles')
def update_role_permissions(role_id):
    """Update permissions for a role"""
    data = request.get_json()
    permission_ids = data.get('permission_ids', [])
    
    conn = get_db()
    cursor = conn.cursor()
    
    try:
        # Check if it's a default Admin role
        cursor.execute('SELECT role_name, is_default FROM roles WHERE id = ?', (role_id,))
        role = cursor.fetchone()
        
        if role and role['is_default'] and role['role_name'] == 'Admin':
            return jsonify({'error': 'Cannot modify Admin role permissions'}), 400
        
        # Delete existing permissions
        cursor.execute('DELETE FROM role_permissions WHERE role_id = ?', (role_id,))
        
        # Insert new permissions
        for perm_id in permission_ids:
            cursor.execute('''
                INSERT INTO role_permissions (role_id, permission_id)
                VALUES (?, ?)
            ''', (role_id, perm_id))
        
        conn.commit()
        
        # Log activity
        log_audit(session['user_id'], 'permissions_updated', 
                 f'Updated permissions for role ID: {role_id}',
                 request.remote_addr, request.headers.get('User-Agent'))
        
        return jsonify({'success': True})
    finally:
        conn.close()

# Audit Log Endpoints

@user_bp.route('/api/audit-logs', methods=['GET'])
@login_required
@admin_required
def get_audit_logs():
    """Get audit logs with filters"""
    user_id = request.args.get('user_id')
    action_type = request.args.get('action_type')
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    limit = int(request.args.get('limit', 100))
    offset = int(request.args.get('offset', 0))
    
    conn = get_db()
    cursor = conn.cursor()
    
    try:
        query = '''
            SELECT al.*, u.username, u.name as user_name
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
        params.extend([limit, offset])
        
        cursor.execute(query, params)
        logs = [dict(row) for row in cursor.fetchall()]
        
        # Get total count
        count_query = 'SELECT COUNT(*) as total FROM audit_logs WHERE 1=1'
        count_params = []
        
        if user_id:
            count_query += ' AND user_id = ?'
            count_params.append(user_id)
        
        if action_type:
            count_query += ' AND action_type = ?'
            count_params.append(action_type)
        
        cursor.execute(count_query, count_params)
        total = cursor.fetchone()['total']
        
        return jsonify({
            'logs': logs,
            'total': total,
            'limit': limit,
            'offset': offset
        })
    finally:
        conn.close()

@user_bp.route('/api/user/permissions', methods=['GET'])
@login_required
def get_current_user_permissions():
    """Get permissions for current logged-in user"""
    from auth import get_user_permissions
    permissions = get_user_permissions()
    return jsonify(permissions)
