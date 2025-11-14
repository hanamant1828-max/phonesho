
-- User Management Module - Complete Schema

-- Roles table (predefined roles)
CREATE TABLE IF NOT EXISTS roles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    role_name TEXT NOT NULL UNIQUE,
    description TEXT,
    is_default BOOLEAN DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Permissions table (granular permissions)
CREATE TABLE IF NOT EXISTS permissions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    permission_key TEXT NOT NULL UNIQUE,
    permission_name TEXT NOT NULL,
    module TEXT NOT NULL,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Role-Permission mapping
CREATE TABLE IF NOT EXISTS role_permissions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    role_id INTEGER NOT NULL,
    permission_id INTEGER NOT NULL,
    FOREIGN KEY (role_id) REFERENCES roles(id) ON DELETE CASCADE,
    FOREIGN KEY (permission_id) REFERENCES permissions(id) ON DELETE CASCADE,
    UNIQUE(role_id, permission_id)
);

-- Enhanced users table
CREATE TABLE IF NOT EXISTS users_new (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    username TEXT NOT NULL UNIQUE,
    email TEXT,
    phone TEXT,
    password_hash TEXT NOT NULL,
    role_id INTEGER NOT NULL,
    status TEXT DEFAULT 'active' CHECK(status IN ('active', 'inactive', 'locked')),
    failed_login_attempts INTEGER DEFAULT 0,
    is_password_reset_required BOOLEAN DEFAULT 0,
    store_id INTEGER,
    last_login_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (role_id) REFERENCES roles(id)
);

-- Audit logs table
CREATE TABLE IF NOT EXISTS audit_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    action_type TEXT NOT NULL,
    description TEXT,
    ip_address TEXT,
    device_info TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

-- Insert default roles
INSERT INTO roles (role_name, description, is_default) VALUES
('Admin', 'Full access to all modules and settings', 1),
('Manager', 'Operational control - billing, inventory, reports', 1),
('Cashier', 'POS-only user - sales, billing, returns', 1),
('Sales Staff', 'Limited product access - view stock, create sales', 1);

-- Insert permissions
INSERT INTO permissions (permission_key, permission_name, module, description) VALUES
-- POS/Sales
('pos.create_sale', 'Create Sale', 'POS', 'Create new sales transactions'),
('pos.edit_sale', 'Edit Sale', 'POS', 'Modify existing sales'),
('pos.cancel_sale', 'Cancel Sale', 'POS', 'Cancel sales transactions'),
('pos.process_returns', 'Process Returns', 'POS', 'Handle product returns'),
('pos.apply_discounts', 'Apply Discounts', 'POS', 'Apply discounts to sales'),
('pos.access_customer_info', 'Access Customer Info', 'POS', 'View customer information'),

-- Inventory
('inventory.view', 'View Inventory', 'Inventory', 'View inventory lists'),
('inventory.add_update', 'Add/Update Product', 'Inventory', 'Create and modify products'),
('inventory.delete', 'Delete Product', 'Inventory', 'Remove products'),
('inventory.manage_stock', 'Manage Stock', 'Inventory', 'Stock adjustments and transfers'),
('inventory.view_cost_price', 'View Cost Price', 'Inventory', 'See product cost prices'),
('inventory.transfer_stock', 'Transfer Stock', 'Inventory', 'Move stock between locations'),

-- Reports
('reports.view_sales', 'View Sales Reports', 'Reports', 'Access daily/weekly sales reports'),
('reports.view_profit', 'View Profit/Margin', 'Reports', 'View profit and margin analytics'),
('reports.export', 'Export Reports', 'Reports', 'Download and export reports'),

-- System Settings
('settings.pos_config', 'POS Settings', 'Settings', 'Configure POS settings'),
('settings.manage_users', 'Manage Users', 'Settings', 'Create, edit, delete users'),
('settings.manage_roles', 'Manage Roles', 'Settings', 'Configure roles and permissions'),
('settings.configure_taxes', 'Configure Taxes', 'Settings', 'Set up tax configurations'),
('settings.backup_restore', 'Backup/Restore', 'Settings', 'System backup and restore'),

-- Customers
('customers.add_edit', 'Add/Edit Customer', 'Customers', 'Create and modify customers'),
('customers.delete', 'Delete Customer', 'Customers', 'Remove customers'),
('customers.view_history', 'View Customer History', 'Customers', 'Access customer purchase history');

-- Assign permissions to Admin (all permissions)
INSERT INTO role_permissions (role_id, permission_id)
SELECT 1, id FROM permissions;

-- Assign permissions to Manager (operational permissions)
INSERT INTO role_permissions (role_id, permission_id)
SELECT 2, id FROM permissions WHERE permission_key IN (
    'pos.create_sale', 'pos.edit_sale', 'pos.cancel_sale', 'pos.process_returns', 'pos.apply_discounts', 'pos.access_customer_info',
    'inventory.view', 'inventory.add_update', 'inventory.manage_stock', 'inventory.view_cost_price',
    'reports.view_sales', 'reports.view_profit', 'reports.export',
    'customers.add_edit', 'customers.view_history'
);

-- Assign permissions to Cashier (POS only)
INSERT INTO role_permissions (role_id, permission_id)
SELECT 3, id FROM permissions WHERE permission_key IN (
    'pos.create_sale', 'pos.process_returns', 'pos.access_customer_info',
    'customers.add_edit', 'customers.view_history'
);

-- Assign permissions to Sales Staff (limited access)
INSERT INTO role_permissions (role_id, permission_id)
SELECT 4, id FROM permissions WHERE permission_key IN (
    'pos.create_sale', 'pos.access_customer_info',
    'inventory.view',
    'customers.add_edit'
);

-- Migrate existing users
INSERT INTO users_new (name, username, password_hash, role_id, status, created_at)
SELECT username, username, password, 1, 'active', created_at
FROM users;

-- Drop old users table and rename new one
DROP TABLE users;
ALTER TABLE users_new RENAME TO users;

-- Create indexes for performance
CREATE INDEX idx_audit_logs_user ON audit_logs(user_id);
CREATE INDEX idx_audit_logs_created ON audit_logs(created_at);
CREATE INDEX idx_users_username ON users(username);
CREATE INDEX idx_users_role ON users(role_id);
CREATE INDEX idx_users_status ON users(status);
