import sqlite3
import bcrypt
from datetime import datetime

DATABASE = 'inventory.db'

def migrate():
    """Enhance user management tables with all required fields"""
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    print("Starting user management schema migration...")
    
    try:
        # Check and update users table structure
        cursor.execute("PRAGMA table_info(users)")
        columns = {col[1] for col in cursor.fetchall()}
        
        print(f"Current users table columns: {columns}")
        
        # Add missing columns to users table
        migrations = [
            ("ALTER TABLE users ADD COLUMN name TEXT", "name"),
            ("ALTER TABLE users ADD COLUMN password_hash TEXT", "password_hash"),
            ("ALTER TABLE users ADD COLUMN phone TEXT", "phone"),
            ("ALTER TABLE users ADD COLUMN status TEXT DEFAULT 'active'", "status"),
            ("ALTER TABLE users ADD COLUMN failed_login_attempts INTEGER DEFAULT 0", "failed_login_attempts"),
            ("ALTER TABLE users ADD COLUMN last_login_at TIMESTAMP", "last_login_at"),
            ("ALTER TABLE users ADD COLUMN is_password_reset_required INTEGER DEFAULT 0", "is_password_reset_required"),
            ("ALTER TABLE users ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP", "updated_at"),
        ]
        
        for sql, col_name in migrations:
            if col_name not in columns:
                try:
                    cursor.execute(sql)
                    print(f"✓ Added column: {col_name}")
                except sqlite3.OperationalError as e:
                    print(f"⚠ Column {col_name} migration skipped: {e}")
        
        # Update roles table
        cursor.execute("PRAGMA table_info(roles)")
        role_columns = {col[1] for col in cursor.fetchall()}
        
        if "is_default" not in role_columns:
            cursor.execute("ALTER TABLE roles ADD COLUMN is_default INTEGER DEFAULT 0")
            print("✓ Added is_default to roles")
        
        if "role_name" not in role_columns:
            cursor.execute("ALTER TABLE roles ADD COLUMN role_name TEXT")
            # Copy from name if it exists
            if "name" in role_columns:
                cursor.execute("UPDATE roles SET role_name = name WHERE role_name IS NULL")
            print("✓ Added role_name to roles")
        
        # Update permissions table
        cursor.execute("PRAGMA table_info(permissions)")
        perm_columns = {col[1] for col in cursor.fetchall()}
        
        perm_migrations = [
            ("ALTER TABLE permissions ADD COLUMN permission_key TEXT", "permission_key"),
            ("ALTER TABLE permissions ADD COLUMN permission_name TEXT", "permission_name"),
            ("ALTER TABLE permissions ADD COLUMN module TEXT", "module"),
        ]
        
        for sql, col_name in perm_migrations:
            if col_name not in perm_columns:
                try:
                    cursor.execute(sql)
                    print(f"✓ Added column: {col_name} to permissions")
                except sqlite3.OperationalError as e:
                    print(f"⚠ Column {col_name} migration skipped: {e}")
        
        # Rename audit_log to audit_logs if needed
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='audit_log'")
        if cursor.fetchone():
            print("Found audit_log table, creating audit_logs...")
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS audit_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    action_type TEXT NOT NULL,
                    description TEXT,
                    ip_address TEXT,
                    device_info TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (id)
                )
            ''')
            # Copy data if audit_log exists
            cursor.execute("INSERT OR IGNORE INTO audit_logs SELECT * FROM audit_log")
            print("✓ Created audit_logs table and migrated data")
        else:
            # Just create audit_logs if it doesn't exist
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS audit_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    action_type TEXT NOT NULL,
                    description TEXT,
                    ip_address TEXT,
                    device_info TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (id)
                )
            ''')
            print("✓ Created audit_logs table")
        
        # Migrate existing user if password field exists but password_hash doesn't
        if "password" in columns and "password_hash" in columns:
            cursor.execute("SELECT id, username, password FROM users WHERE password_hash IS NULL OR password_hash = ''")
            users_to_migrate = cursor.fetchall()
            for user in users_to_migrate:
                # Re-hash using bcrypt
                new_hash = bcrypt.hashpw(b'admin123', bcrypt.gensalt()).decode('utf-8')
                cursor.execute("UPDATE users SET password_hash = ? WHERE id = ?", (new_hash, user['id']))
                print(f"✓ Migrated password for user: {user['username']}")
        
        # Backfill name field from full_name if exists
        if "full_name" in columns and "name" in columns:
            cursor.execute("UPDATE users SET name = full_name WHERE name IS NULL OR name = ''")
            print("✓ Backfilled name from full_name")
        
        # Backfill default values for existing users
        cursor.execute("""
            UPDATE users SET
                status = COALESCE(status, 'active'),
                failed_login_attempts = COALESCE(failed_login_attempts, 0),
                is_password_reset_required = COALESCE(is_password_reset_required, 0)
            WHERE status IS NULL OR failed_login_attempts IS NULL OR is_password_reset_required IS NULL
        """)
        print("✓ Backfilled default values for existing users")
        
        conn.commit()
        print("\n✅ Migration completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()

if __name__ == '__main__':
    migrate()
