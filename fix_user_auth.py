import sqlite3
import bcrypt

def fix_database():
    conn = sqlite3.connect('inventory.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    try:
        # 1. Add missing columns to users table
        cursor.execute("PRAGMA table_info(users)")
        columns = [col[1] for col in cursor.fetchall()]
        
        if 'password_hash' not in columns:
            print("Adding password_hash column...")
            cursor.execute('ALTER TABLE users ADD COLUMN password_hash TEXT')
        
        if 'status' not in columns:
            print("Adding status column...")
            cursor.execute("ALTER TABLE users ADD COLUMN status TEXT DEFAULT 'active'")
        
        if 'failed_login_attempts' not in columns:
            print("Adding failed_login_attempts column...")
            cursor.execute('ALTER TABLE users ADD COLUMN failed_login_attempts INTEGER DEFAULT 0')
        
        if 'last_login_at' not in columns:
            print("Adding last_login_at column...")
            cursor.execute('ALTER TABLE users ADD COLUMN last_login_at TIMESTAMP')
        
        if 'name' not in columns:
            print("Adding name column...")
            cursor.execute('ALTER TABLE users ADD COLUMN name TEXT')
        
        conn.commit()
        
        # 2. Migrate existing passwords to bcrypt hashes
        print("Migrating passwords to bcrypt...")
        cursor.execute('SELECT id, username, password FROM users')
        users = cursor.fetchall()
        
        for user in users:
            if user['password']:
                # Check if it's already a bcrypt hash (starts with $2b$)
                if not user['password'].startswith('$2b$'):
                    # Hash the password with bcrypt
                    password_hash = bcrypt.hashpw(user['password'].encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
                    cursor.execute('UPDATE users SET password_hash = ? WHERE id = ?', (password_hash, user['id']))
                else:
                    # Already hashed, just copy to password_hash
                    cursor.execute('UPDATE users SET password_hash = ? WHERE id = ?', (user['password'], user['id']))
            
            # Set name if not set (name column was just added, so it will be NULL)
            cursor.execute('UPDATE users SET name = ? WHERE id = ?', (user['username'], user['id']))
        
        # 3. Ensure admin user has correct password
        print("Resetting admin password to admin123...")
        admin_password_hash = bcrypt.hashpw('admin123'.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        cursor.execute('''
            UPDATE users 
            SET password_hash = ?, status = 'active', failed_login_attempts = 0, name = 'Administrator'
            WHERE username = 'admin'
        ''', (admin_password_hash,))
        
        # 4. Create audit_logs table if not exists
        print("Creating audit_logs table...")
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS audit_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                action_type TEXT NOT NULL,
                description TEXT,
                ip_address TEXT,
                device_info TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        ''')
        
        # 5. Update permissions table to have proper columns
        cursor.execute("PRAGMA table_info(permissions)")
        perm_columns = [col[1] for col in cursor.fetchall()]
        
        if 'permission_key' not in perm_columns:
            print("Adding permission_key column...")
            cursor.execute('ALTER TABLE permissions ADD COLUMN permission_key TEXT')
        
        if 'permission_name' not in perm_columns:
            print("Adding permission_name column...")
            cursor.execute('ALTER TABLE permissions ADD COLUMN permission_name TEXT')
        
        if 'module' not in perm_columns:
            print("Adding module column...")
            cursor.execute('ALTER TABLE permissions ADD COLUMN module TEXT')
        
        # Update existing permissions to have permission_key and permission_name
        cursor.execute('SELECT id, name FROM permissions WHERE permission_key IS NULL')
        perms = cursor.fetchall()
        for perm in perms:
            key = perm['name'].lower().replace(' ', '_')
            cursor.execute('''
                UPDATE permissions 
                SET permission_key = ?, permission_name = ?, module = 'General'
                WHERE id = ?
            ''', (key, perm['name'], perm['id']))
        
        # 6. Update roles table
        cursor.execute("PRAGMA table_info(roles)")
        role_columns = [col[1] for col in cursor.fetchall()]
        
        if 'role_name' not in role_columns:
            print("Adding role_name column...")
            cursor.execute('ALTER TABLE roles ADD COLUMN role_name TEXT')
            # Copy name to role_name
            cursor.execute('UPDATE roles SET role_name = name')
        
        conn.commit()
        print("\nDatabase migration completed successfully!")
        
        # Verify admin user
        cursor.execute('SELECT id, username, name, status, role_id FROM users WHERE username = "admin"')
        admin = cursor.fetchone()
        if admin:
            print(f"\nAdmin user verified:")
            print(f"  ID: {admin['id']}")
            print(f"  Username: {admin['username']}")
            print(f"  Name: {admin['name']}")
            print(f"  Status: {admin['status']}")
            print(f"  Role ID: {admin['role_id']}")
        else:
            print("\nWarning: Admin user not found!")
        
    except Exception as e:
        print(f"Error during migration: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()

if __name__ == '__main__':
    fix_database()
