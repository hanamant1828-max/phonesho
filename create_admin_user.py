
#!/usr/bin/env python3
"""
Create default admin user for the system
Run this once after setting up the database
"""

import sqlite3
from auth import hash_password

def create_admin_user():
    conn = sqlite3.connect('mobile_shop.db')
    cursor = conn.cursor()
    
    # Check if admin user already exists
    cursor.execute("SELECT id FROM users WHERE username = 'admin'")
    if cursor.fetchone():
        print("Admin user already exists!")
        conn.close()
        return
    
    # Get Admin role ID
    cursor.execute("SELECT id FROM roles WHERE role_name = 'Admin'")
    admin_role = cursor.fetchone()
    
    if not admin_role:
        print("Admin role not found. Please run migrations first.")
        conn.close()
        return
    
    # Create admin user
    password_hash = hash_password('admin123')  # Change this password!
    
    cursor.execute('''
        INSERT INTO users (name, username, email, password_hash, role_id, status)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', ('System Administrator', 'admin', 'admin@mobileshop.com', password_hash, admin_role[0], 'active'))
    
    conn.commit()
    conn.close()
    
    print("✓ Admin user created successfully!")
    print("  Username: admin")
    print("  Password: admin123")
    print("  ⚠️  IMPORTANT: Change this password immediately after first login!")

if __name__ == '__main__':
    create_admin_user()
