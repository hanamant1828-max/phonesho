import sqlite3
from datetime import datetime

DATABASE = 'inventory.db'

def seed_permissions_and_roles():
    """Add comprehensive permissions and new roles"""
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    print("Seeding comprehensive permissions and roles...")
    
    try:
        # Define comprehensive permissions organized by module
        permissions = [
            # POS / Sales Module
            ('pos.create_sale', 'Create Sale', 'POS'),
            ('pos.edit_sale', 'Edit Sale', 'POS'),
            ('pos.cancel_sale', 'Cancel Sale', 'POS'),
            ('pos.process_returns', 'Process Returns', 'POS'),
            ('pos.apply_discounts', 'Apply Discounts', 'POS'),
            ('pos.view_customer_info', 'View Customer Info in POS', 'POS'),
            ('pos.print_invoice', 'Print Invoice', 'POS'),
            
            # Inventory Module
            ('inventory.view', 'View Inventory', 'Inventory'),
            ('inventory.add_product', 'Add Product', 'Inventory'),
            ('inventory.edit_product', 'Edit Product', 'Inventory'),
            ('inventory.delete_product', 'Delete Product', 'Inventory'),
            ('inventory.view_cost_price', 'View Cost Price', 'Inventory'),
            ('inventory.stock_adjustment', 'Manage Stock Adjustments', 'Inventory'),
            ('inventory.transfer_stock', 'Transfer Stock', 'Inventory'),
            ('inventory.view_imei', 'View IMEI Tracking', 'Inventory'),
            
            # Purchase Orders Module
            ('purchase.view', 'View Purchase Orders', 'Purchase Orders'),
            ('purchase.create', 'Create Purchase Order', 'Purchase Orders'),
            ('purchase.edit', 'Edit Purchase Order', 'Purchase Orders'),
            ('purchase.delete', 'Delete Purchase Order', 'Purchase Orders'),
            ('purchase.receive', 'Receive Purchase Order', 'Purchase Orders'),
            
            # Reports Module
            ('reports.view_sales', 'View Sales Reports', 'Reports'),
            ('reports.view_profit', 'View Profit & Margin Reports', 'Reports'),
            ('reports.view_inventory', 'View Inventory Reports', 'Reports'),
            ('reports.export', 'Export Reports', 'Reports'),
            ('reports.view_dashboard', 'View Dashboard', 'Reports'),
            
            # Customers Module
            ('customers.view', 'View Customers', 'Customers'),
            ('customers.add', 'Add Customer', 'Customers'),
            ('customers.edit', 'Edit Customer', 'Customers'),
            ('customers.delete', 'Delete Customer', 'Customers'),
            ('customers.view_history', 'View Customer History', 'Customers'),
            
            # Service Module
            ('service.view_jobs', 'View Service Jobs', 'Service'),
            ('service.create_job', 'Create Service Job', 'Service'),
            ('service.edit_job', 'Edit Service Job', 'Service'),
            ('service.close_job', 'Close Service Job', 'Service'),
            
            # Settings Module
            ('settings.view', 'View Settings', 'Settings'),
            ('settings.manage_business', 'Manage Business Settings', 'Settings'),
            ('settings.manage_users', 'Manage Users', 'Settings'),
            ('settings.manage_roles', 'Manage Roles & Permissions', 'Settings'),
            ('settings.configure_taxes', 'Configure Taxes', 'Settings'),
            ('settings.backup_restore', 'Backup & Restore', 'Settings'),
            ('settings.view_audit_logs', 'View Audit Logs', 'Settings'),
        ]
        
        # Insert permissions
        print("\nInserting permissions...")
        for perm_key, perm_name, module in permissions:
            try:
                cursor.execute('''
                    INSERT OR IGNORE INTO permissions (permission_key, permission_name, module)
                    VALUES (?, ?, ?)
                ''', (perm_key, perm_name, module))
                print(f"✓ {module}: {perm_name}")
            except Exception as e:
                print(f"⚠ Error inserting {perm_key}: {e}")
        
        # Update existing roles with is_default and role_name
        cursor.execute("UPDATE roles SET is_default = 1, role_name = name WHERE name IN ('Admin', 'Manager', 'Staff')")
        
        # Add new roles (Cashier and Sales Staff)
        new_roles = [
            ('Cashier', 'POS-only user for sales operations', 1),
            ('Sales Staff', 'Limited product access for sales operations', 1),
        ]
        
        print("\nAdding new roles...")
        for role_name, description, is_default in new_roles:
            cursor.execute('SELECT id FROM roles WHERE role_name = ?', (role_name,))
            if not cursor.fetchone():
                cursor.execute('''
                    INSERT INTO roles (role_name, description, is_default, name)
                    VALUES (?, ?, ?, ?)
                ''', (role_name, description, is_default, role_name))
                print(f"✓ Added role: {role_name}")
            else:
                print(f"⚠ Role already exists: {role_name}")
        
        # Set up role-permission mappings
        print("\nSetting up role-permission mappings...")
        
        # Get role IDs
        cursor.execute('SELECT id, role_name FROM roles')
        roles = {row['role_name']: row['id'] for row in cursor.fetchall()}
        
        # Get all permission IDs
        cursor.execute('SELECT id, permission_key FROM permissions')
        permissions_map = {row['permission_key']: row['id'] for row in cursor.fetchall()}
        
        # Define permissions for each role
        role_permissions_config = {
            'Admin': list(permissions_map.keys()),  # Admin gets all permissions
            
            'Manager': [
                'pos.create_sale', 'pos.edit_sale', 'pos.process_returns', 'pos.apply_discounts',
                'inventory.view', 'inventory.add_product', 'inventory.edit_product', 'inventory.view_cost_price',
                'inventory.stock_adjustment', 'inventory.view_imei',
                'purchase.view', 'purchase.create', 'purchase.edit', 'purchase.receive',
                'reports.view_sales', 'reports.view_profit', 'reports.view_inventory', 'reports.export', 'reports.view_dashboard',
                'customers.view', 'customers.add', 'customers.edit', 'customers.view_history',
                'service.view_jobs', 'service.create_job', 'service.edit_job', 'service.close_job',
                'settings.view',
            ],
            
            'Cashier': [
                'pos.create_sale', 'pos.process_returns', 'pos.view_customer_info', 'pos.print_invoice',
                'inventory.view',
                'customers.view', 'customers.add',
                'reports.view_dashboard',
            ],
            
            'Sales Staff': [
                'pos.create_sale', 'pos.view_customer_info', 'pos.print_invoice',
                'inventory.view',
                'customers.view', 'customers.add', 'customers.view_history',
            ],
            
            'Staff': [  # Keep existing Staff role permissions
                'pos.create_sale', 'pos.view_customer_info',
                'inventory.view',
                'customers.view',
            ],
        }
        
        # Clear existing role_permissions for default roles (except Admin to be safe)
        for role_name, role_id in roles.items():
            if role_name != 'Admin':
                cursor.execute('DELETE FROM role_permissions WHERE role_id = ?', (role_id,))
        
        # Insert new role-permission mappings
        for role_name, perm_keys in role_permissions_config.items():
            if role_name not in roles:
                continue
            
            role_id = roles[role_name]
            print(f"\nAssigning permissions to {role_name}:")
            
            for perm_key in perm_keys:
                if perm_key not in permissions_map:
                    print(f"  ⚠ Permission not found: {perm_key}")
                    continue
                
                perm_id = permissions_map[perm_key]
                try:
                    cursor.execute('''
                        INSERT OR IGNORE INTO role_permissions (role_id, permission_id)
                        VALUES (?, ?)
                    ''', (role_id, perm_id))
                except Exception as e:
                    print(f"  ⚠ Error: {e}")
            
            # Count assigned permissions
            cursor.execute('SELECT COUNT(*) as count FROM role_permissions WHERE role_id = ?', (role_id,))
            count = cursor.fetchone()['count']
            print(f"  ✓ {count} permissions assigned to {role_name}")
        
        conn.commit()
        print("\n✅ Permissions and roles seeded successfully!")
        
        # Summary
        cursor.execute('SELECT COUNT(*) as count FROM permissions')
        perm_count = cursor.fetchone()['count']
        cursor.execute('SELECT COUNT(*) as count FROM roles')
        role_count = cursor.fetchone()['count']
        
        print(f"\n📊 Summary:")
        print(f"   Total Permissions: {perm_count}")
        print(f"   Total Roles: {role_count}")
        
    except Exception as e:
        print(f"\n❌ Seeding failed: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()

if __name__ == '__main__':
    seed_permissions_and_roles()
