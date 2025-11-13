
import bcrypt
import jwt
import json
from datetime import datetime, timedelta
from functools import wraps
from flask import request, jsonify, session
import sqlite3

SECRET_KEY = "your-secret-key-change-in-production"  # Should be in environment variable
TOKEN_EXPIRATION_HOURS = 24

def get_db_connection():
    conn = sqlite3.connect('mobile_shop.db')
    conn.row_factory = sqlite3.Row
    return conn

def hash_password(password):
    """Hash a password using bcrypt"""
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verify_password(password, password_hash):
    """Verify a password against its hash"""
    return bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8'))

def generate_token(user_id, username, role_id):
    """Generate JWT token for authenticated user"""
    payload = {
        'user_id': user_id,
        'username': username,
        'role_id': role_id,
        'exp': datetime.utcnow() + timedelta(hours=TOKEN_EXPIRATION_HOURS)
    }
    return jwt.encode(payload, SECRET_KEY, algorithm='HS256')

def decode_token(token):
    """Decode and verify JWT token"""
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None

def log_audit(user_id, action_type, description, ip_address=None, device_info=None, metadata=None):
    """Log user activity to audit trail"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    metadata_json = json.dumps(metadata) if metadata else None
    
    cursor.execute('''
        INSERT INTO audit_logs (user_id, action_type, description, ip_address, device_info, metadata)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (user_id, action_type, description, ip_address, device_info, metadata_json))
    
    conn.commit()
    conn.close()

def get_user_permissions(user_id):
    """Get all permissions for a user based on their role"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT p.permission_name
        FROM users u
        JOIN role_permissions rp ON u.role_id = rp.role_id
        JOIN permissions p ON rp.permission_id = p.id
        WHERE u.id = ? AND u.status = 'active'
    ''', (user_id,))
    
    permissions = [row['permission_name'] for row in cursor.fetchall()]
    conn.close()
    return permissions

def require_auth(f):
    """Decorator to require authentication"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = request.headers.get('Authorization')
        
        if not token:
            token = session.get('token')
        
        if token and token.startswith('Bearer '):
            token = token[7:]
        
        if not token:
            return jsonify({'error': 'Authentication required'}), 401
        
        user_data = decode_token(token)
        if not user_data:
            return jsonify({'error': 'Invalid or expired token'}), 401
        
        # Check if user is still active
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT status FROM users WHERE id = ?', (user_data['user_id'],))
        user = cursor.fetchone()
        conn.close()
        
        if not user or user['status'] != 'active':
            return jsonify({'error': 'User account is not active'}), 401
        
        request.current_user = user_data
        return f(*args, **kwargs)
    
    return decorated_function

def require_permission(permission_name):
    """Decorator to require specific permission"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not hasattr(request, 'current_user'):
                return jsonify({'error': 'Authentication required'}), 401
            
            user_permissions = get_user_permissions(request.current_user['user_id'])
            
            if permission_name not in user_permissions:
                log_audit(
                    request.current_user['user_id'],
                    'permission_denied',
                    f"Access denied to {permission_name}",
                    request.remote_addr,
                    request.headers.get('User-Agent')
                )
                return jsonify({'error': 'Permission denied'}), 403
            
            return f(*args, **kwargs)
        
        return decorated_function
    return decorator

def require_role(role_name):
    """Decorator to require specific role"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not hasattr(request, 'current_user'):
                return jsonify({'error': 'Authentication required'}), 401
            
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute('''
                SELECT r.role_name
                FROM users u
                JOIN roles r ON u.role_id = r.id
                WHERE u.id = ?
            ''', (request.current_user['user_id'],))
            
            user = cursor.fetchone()
            conn.close()
            
            if not user or user['role_name'] != role_name:
                return jsonify({'error': 'Insufficient privileges'}), 403
            
            return f(*args, **kwargs)
        
        return decorated_function
    return decorator
