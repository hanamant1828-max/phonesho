
from functools import wraps
from flask import session, redirect, url_for, request, jsonify
import sqlite3
import bcrypt
from datetime import datetime

def get_db():
    conn = sqlite3.connect('inventory.db')
    conn.row_factory = sqlite3.Row
    return conn

def log_audit(user_id, action_type, description, ip_address=None, device_info=None):
    """Log user activity to audit trail"""
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            INSERT INTO audit_logs (user_id, action_type, description, ip_address, device_info)
            VALUES (?, ?, ?, ?, ?)
        ''', (user_id, action_type, description, ip_address, device_info))
        conn.commit()
    except Exception as e:
        print(f"Audit log error: {e}")
    finally:
        conn.close()

def check_permission(permission_key):
    """Check if current user has specific permission"""
    if 'user_id' not in session:
        return False
    
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            SELECT COUNT(*) as count
            FROM role_permissions rp
            JOIN permissions p ON rp.permission_id = p.id
            JOIN users u ON u.role_id = rp.role_id
            WHERE u.id = ? AND p.permission_key = ?
        ''', (session['user_id'], permission_key))
        result = cursor.fetchone()
        return result['count'] > 0
    finally:
        conn.close()

def get_user_permissions():
    """Get all permissions for current user"""
    if 'user_id' not in session:
        return []
    
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            SELECT DISTINCT p.permission_key, p.permission_name, p.module
            FROM role_permissions rp
            JOIN permissions p ON rp.permission_id = p.id
            JOIN users u ON u.role_id = rp.role_id
            WHERE u.id = ?
            ORDER BY p.module, p.permission_name
        ''', (session['user_id'],))
        return [dict(row) for row in cursor.fetchall()]
    finally:
        conn.close()

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            if request.is_json:
                return jsonify({'error': 'Authentication required'}), 401
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

def permission_required(permission_key):
    """Decorator to check if user has specific permission"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user_id' not in session:
                if request.is_json:
                    return jsonify({'error': 'Authentication required'}), 401
                return redirect(url_for('index'))
            
            if not check_permission(permission_key):
                if request.is_json:
                    return jsonify({'error': 'Permission denied'}), 403
                return jsonify({'error': 'You do not have permission to perform this action'}), 403
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def admin_required(f):
    """Decorator to restrict access to admin users only"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            if request.is_json:
                return jsonify({'error': 'Authentication required'}), 401
            return redirect(url_for('index'))
        
        conn = get_db()
        cursor = conn.cursor()
        try:
            cursor.execute('''
                SELECT r.role_name
                FROM users u
                JOIN roles r ON u.role_id = r.id
                WHERE u.id = ?
            ''', (session['user_id'],))
            result = cursor.fetchone()
            
            if not result or result['role_name'] != 'Admin':
                if request.is_json:
                    return jsonify({'error': 'Admin access required'}), 403
                return jsonify({'error': 'Admin access required'}), 403
        finally:
            conn.close()
        
        return f(*args, **kwargs)
    return decorated_function

def authenticate_user(username, password):
    """Authenticate user and handle login attempts"""
    conn = get_db()
    cursor = conn.cursor()
    
    try:
        # Get user details
        cursor.execute('''
            SELECT u.*, r.role_name
            FROM users u
            JOIN roles r ON u.role_id = r.id
            WHERE u.username = ?
        ''', (username,))
        user = cursor.fetchone()
        
        if not user:
            return None, "Invalid username or password"
        
        # Check if account is locked
        if user['status'] == 'locked':
            return None, "Account is locked. Contact administrator."
        
        if user['status'] == 'inactive':
            return None, "Account is inactive. Contact administrator."
        
        # Check if account has too many failed attempts
        if user['failed_login_attempts'] >= 5:
            cursor.execute('UPDATE users SET status = ? WHERE id = ?', ('locked', user['id']))
            conn.commit()
            log_audit(user['id'], 'account_locked', 'Account locked due to multiple failed login attempts', 
                     request.remote_addr, request.headers.get('User-Agent'))
            return None, "Account locked due to multiple failed login attempts"
        
        # Verify password
        if bcrypt.checkpw(password.encode('utf-8'), user['password_hash'].encode('utf-8')):
            # Reset failed attempts on successful login
            cursor.execute('''
                UPDATE users 
                SET failed_login_attempts = 0, last_login_at = ?
                WHERE id = ?
            ''', (datetime.now(), user['id']))
            conn.commit()
            
            # Log successful login
            log_audit(user['id'], 'login_success', f'User {username} logged in successfully',
                     request.remote_addr, request.headers.get('User-Agent'))
            
            return dict(user), None
        else:
            # Increment failed attempts
            cursor.execute('''
                UPDATE users 
                SET failed_login_attempts = failed_login_attempts + 1
                WHERE id = ?
            ''', (user['id'],))
            conn.commit()
            
            # Log failed login
            log_audit(user['id'], 'login_failed', f'Failed login attempt for user {username}',
                     request.remote_addr, request.headers.get('User-Agent'))
            
            return None, "Invalid username or password"
    
    finally:
        conn.close()
