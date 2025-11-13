
-- User Management Module Migration

-- Roles table
CREATE TABLE IF NOT EXISTS roles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    role_name TEXT NOT NULL UNIQUE,
    description TEXT,
    is_default BOOLEAN DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Permissions table
CREATE TABLE IF NOT EXISTS permissions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    permission_name TEXT NOT NULL UNIQUE,
    module TEXT NOT NULL,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Role-Permission mapping
CREATE TABLE IF NOT EXISTS role_permissions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    role_id INTEGER NOT NULL,
    permission_id INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (role_id) REFERENCES roles(id) ON DELETE CASCADE,
    FOREIGN KEY (permission_id) REFERENCES permissions(id) ON DELETE CASCADE,
    UNIQUE(role_id, permission_id)
);

-- Users table (enhanced)
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    username TEXT NOT NULL UNIQUE,
    email TEXT UNIQUE,
    phone TEXT,
    password_hash TEXT NOT NULL,
    role_id INTEGER NOT NULL,
    status TEXT DEFAULT 'active' CHECK(status IN ('active', 'inactive', 'locked')),
    failed_login_attempts INTEGER DEFAULT 0,
    is_password_reset_required BOOLEAN DEFAULT 0,
    last_login_at TIMESTAMP,
    store_id INTEGER,
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
    metadata TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
);

-- Insert default roles
INSERT OR IGNORE INTO roles (role_name, description, is_default) VALUES
('Admin', 'Full system access with all permissions', 1),
('Manager', 'Operational control with limited user management', 1),
('Cashier', 'POS-only access for billing operations', 1),
('Sales Staff', 'Limited product and sales access', 1);

-- Insert permissions
INSERT OR IGNORE INTO permissions (permission_name, module, description) VALUES
-- POS/Sales permissions
('pos.create_sale', 'POS', 'Create new sales'),
('pos.edit_sale', 'POS', 'Edit existing sales'),
('pos.cancel_sale', 'POS', 'Cancel sales'),
('pos.process_returns', 'POS', 'Process returns and refunds'),
('pos.apply_discounts', 'POS', 'Apply discounts to sales'),
('pos.access_customer_info', 'POS', 'Access customer information'),

-- Inventory permissions
('inventory.view', 'Inventory', 'View inventory'),
('inventory.add_update', 'Inventory', 'Add or update products'),
('inventory.delete', 'Inventory', 'Delete products'),
('inventory.manage_stock', 'Inventory', 'Manage stock adjustments'),
('inventory.view_cost_price', 'Inventory', 'View product cost prices'),
('inventory.transfer_stock', 'Inventory', 'Transfer stock between locations'),

-- Reports permissions
('reports.view_sales', 'Reports', 'View sales reports'),
('reports.view_profit', 'Reports', 'View profit and margin reports'),
('reports.export', 'Reports', 'Export reports'),

-- System Settings permissions
('settings.pos', 'Settings', 'Modify POS settings'),
('settings.users', 'Settings', 'Manage users'),
('settings.roles', 'Settings', 'Manage roles and permissions'),
('settings.taxes', 'Settings', 'Configure taxes'),
('settings.backup', 'Settings', 'Backup and restore system'),

-- Customer permissions
('customers.add_edit', 'Customers', 'Add or edit customers'),
('customers.delete', 'Customers', 'Delete customers'),
('customers.view_history', 'Customers', 'View customer purchase history');

-- Assign permissions to Admin role (all permissions)
INSERT OR IGNORE INTO role_permissions (role_id, permission_id)
SELECT 1, id FROM permissions;

-- Assign permissions to Manager role
INSERT OR IGNORE INTO role_permissions (role_id, permission_id)
SELECT 2, id FROM permissions WHERE permission_name NOT IN ('settings.backup', 'settings.roles', 'inventory.delete');

-- Assign permissions to Cashier role
INSERT OR IGNORE INTO role_permissions (role_id, permission_id)
SELECT 3, id FROM permissions WHERE module = 'POS' AND permission_name NOT IN ('pos.cancel_sale');

-- Assign permissions to Sales Staff role
INSERT OR IGNORE INTO role_permissions (role_id, permission_id)
SELECT 4, id FROM permissions WHERE permission_name IN ('inventory.view', 'pos.create_sale', 'pos.access_customer_info', 'customers.view_history');

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_audit_logs_user_id ON audit_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_audit_logs_created_at ON audit_logs(created_at);
CREATE INDEX IF NOT EXISTS idx_audit_logs_action_type ON audit_logs(action_type);
CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_role_id ON users(role_id);
CREATE INDEX IF NOT EXISTS idx_role_permissions_role_id ON role_permissions(role_id);
