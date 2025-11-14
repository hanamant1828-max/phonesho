# This script generates the updated init_db() function with enhanced schema
# Run this manually to update app.py

init_db_code = '''
def init_db():
    """Initialize the database and create tables if they don't exist"""
    conn = get_db()
    cursor = conn.cursor()

    # [Keep all existing table creation code from original - categories, brands, models, products, etc.]
    # ... (existing tables remain the same) ...
    
    # Enhanced User Management Tables with all required fields
    cursor.execute(\'''
        CREATE TABLE IF NOT EXISTS roles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            role_name TEXT,
            description TEXT,
            is_default INTEGER DEFAULT 0
        )
    \''')

    cursor.execute(\'''
        CREATE TABLE IF NOT EXISTS permissions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            permission_key TEXT UNIQUE,
            permission_name TEXT,
            module TEXT,
            description TEXT
        )
    \''')

    cursor.execute(\'''
        CREATE TABLE IF NOT EXISTS role_permissions (
            role_id INTEGER NOT NULL,
            permission_id INTEGER NOT NULL,
            PRIMARY KEY (role_id, permission_id),
            FOREIGN KEY (role_id) REFERENCES roles (id) ON DELETE CASCADE,
            FOREIGN KEY (permission_id) REFERENCES permissions (id) ON DELETE CASCADE
        )
    \''')

    cursor.execute(\'''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password TEXT,
            password_hash TEXT,
            name TEXT,
            full_name TEXT,
            email TEXT UNIQUE,
            phone TEXT,
            role_id INTEGER,
            status TEXT DEFAULT 'active',
            is_active INTEGER DEFAULT 1,
            failed_login_attempts INTEGER DEFAULT 0,
            last_login_at TIMESTAMP,
            is_password_reset_required INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (role_id) REFERENCES roles (id)
        )
    \''')

    cursor.execute(\'''
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
    \''')
    
    # Insert comprehensive permissions (44 total)
    comprehensive_permissions = [
        ('pos.create_sale', 'Create Sale', 'POS'),
        ('pos.edit_sale', 'Edit Sale', 'POS'),
        ('pos.cancel_sale', 'Cancel Sale', 'POS'),
        ('pos.process_returns', 'Process Returns', 'POS'),
        ('pos.apply_discounts', 'Apply Discounts', 'POS'),
        ('pos.view_customer_info', 'View Customer Info in POS', 'POS'),
        ('pos.print_invoice', 'Print Invoice', 'POS'),
        ('inventory.view', 'View Inventory', 'Inventory'),
        ('inventory.add_product', 'Add Product', 'Inventory'),
        ('inventory.edit_product', 'Edit Product', 'Inventory'),
        ('inventory.delete_product', 'Delete Product', 'Inventory'),
        ('inventory.view_cost_price', 'View Cost Price', 'Inventory'),
        ('inventory.stock_adjustment', 'Manage Stock Adjustments', 'Inventory'),
        ('inventory.transfer_stock', 'Transfer Stock', 'Inventory'),
        ('inventory.view_imei', 'View IMEI Tracking', 'Inventory'),
        ('purchase.view', 'View Purchase Orders', 'Purchase Orders'),
        ('purchase.create', 'Create Purchase Order', 'Purchase Orders'),
        ('purchase.edit', 'Edit Purchase Order', 'Purchase Orders'),
        ('purchase.delete', 'Delete Purchase Order', 'Purchase Orders'),
        ('purchase.receive', 'Receive Purchase Order', 'Purchase Orders'),
        ('reports.view_sales', 'View Sales Reports', 'Reports'),
        ('reports.view_profit', 'View Profit & Margin Reports', 'Reports'),
        ('reports.view_inventory', 'View Inventory Reports', 'Reports'),
        ('reports.export', 'Export Reports', 'Reports'),
        ('reports.view_dashboard', 'View Dashboard', 'Reports'),
        ('customers.view', 'View Customers', 'Customers'),
        ('customers.add', 'Add Customer', 'Customers'),
        ('customers.edit', 'Edit Customer', 'Customers'),
        ('customers.delete', 'Delete Customer', 'Customers'),
        ('customers.view_history', 'View Customer History', 'Customers'),
        ('service.view_jobs', 'View Service Jobs', 'Service'),
        ('service.create_job', 'Create Service Job', 'Service'),
        ('service.edit_job', 'Edit Service Job', 'Service'),
        ('service.close_job', 'Close Service Job', 'Service'),
        ('settings.view', 'View Settings', 'Settings'),
        ('settings.manage_business', 'Manage Business Settings', 'Settings'),
        ('settings.manage_users', 'Manage Users', 'Settings'),
        ('settings.manage_roles', 'Manage Roles & Permissions', 'Settings'),
        ('settings.configure_taxes', 'Configure Taxes', 'Settings'),
        ('settings.backup_restore', 'Backup & Restore', 'Settings'),
        ('settings.view_audit_logs', 'View Audit Logs', 'Settings'),
    ]
    
    for perm_key, perm_name, module in comprehensive_permissions:
        cursor.execute(\'''
            INSERT OR IGNORE INTO permissions (name, permission_key, permission_name, module, description)
            VALUES (?, ?, ?, ?, ?)
        \''', (perm_key, perm_key, perm_name, module, perm_name))
    
    # Insert all 5 roles
    all_roles = [
        ('Admin', 'Administrator role with full access', 1),
        ('Manager', 'Manager role with operational control', 1),
        ('Cashier', 'POS-only user for sales operations', 1),
        ('Sales Staff', 'Limited product access for sales', 1),
        ('Staff', 'Staff role with basic POS operations', 1),
    ]
    
    for role_name, description, is_default in all_roles:
        cursor.execute(\'''
            INSERT OR IGNORE INTO roles (name, role_name, description, is_default)
            VALUES (?, ?, ?, ?)
        \''', (role_name, role_name, description, is_default))
    
    conn.commit()
    
    # Assign permissions to roles
    [role permission assignment code continues...]
    
    conn.commit()
    conn.close()
'''

print("Generated init_db function code - manual update required")
