import sqlite3
from datetime import datetime, timedelta

DATABASE = 'inventory.db'

def seed_database():
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    print("Adding sample data to the database...")
    
    # Add Categories
    categories = [
        ('Smartphones', 'Mobile phones and smartphones'),
        ('Tablets', 'Tablets and iPads'),
        ('Laptops', 'Laptop computers'),
        ('Accessories', 'Phone and computer accessories'),
        ('Smartwatches', 'Wearable smart devices')
    ]
    
    for name, desc in categories:
        try:
            cursor.execute('INSERT INTO categories (name, description) VALUES (?, ?)', (name, desc))
        except sqlite3.IntegrityError:
            print(f"Category '{name}' already exists, skipping...")
    
    conn.commit()
    print(f"✓ Added {len(categories)} categories")
    
    # Add Brands
    brands = [
        ('Apple', 'Apple Inc. products'),
        ('Samsung', 'Samsung Electronics'),
        ('Google', 'Google Pixel devices'),
        ('OnePlus', 'OnePlus smartphones'),
        ('Xiaomi', 'Xiaomi devices'),
        ('Realme', 'Realme smartphones'),
        ('Oppo', 'Oppo mobile devices'),
        ('Vivo', 'Vivo smartphones')
    ]
    
    for name, desc in brands:
        try:
            cursor.execute('INSERT INTO brands (name, description) VALUES (?, ?)', (name, desc))
        except sqlite3.IntegrityError:
            print(f"Brand '{name}' already exists, skipping...")
    
    conn.commit()
    print(f"✓ Added {len(brands)} brands")
    
    # Get category and brand IDs
    cursor.execute('SELECT id, name FROM categories')
    category_map = {name: id for id, name in cursor.fetchall()}
    
    cursor.execute('SELECT id, name FROM brands')
    brand_map = {name: id for id, name in cursor.fetchall()}
    
    # Add Models
    models = [
        ('iPhone 15 Pro', brand_map['Apple'], 'Latest flagship iPhone'),
        ('iPhone 15', brand_map['Apple'], 'Standard iPhone 15'),
        ('iPhone 14', brand_map['Apple'], 'Previous generation iPhone'),
        ('Galaxy S24 Ultra', brand_map['Samsung'], 'Premium Samsung flagship'),
        ('Galaxy S24', brand_map['Samsung'], 'Samsung flagship'),
        ('Galaxy A54', brand_map['Samsung'], 'Mid-range Samsung'),
        ('Pixel 8 Pro', brand_map['Google'], 'Google flagship phone'),
        ('Pixel 8', brand_map['Google'], 'Google Pixel 8'),
        ('OnePlus 12', brand_map['OnePlus'], 'OnePlus flagship'),
        ('Redmi Note 13 Pro', brand_map['Xiaomi'], 'Xiaomi mid-range'),
    ]
    
    for name, brand_id, desc in models:
        try:
            cursor.execute('INSERT INTO models (name, brand_id, description) VALUES (?, ?, ?)', 
                         (name, brand_id, desc))
        except sqlite3.IntegrityError:
            print(f"Model '{name}' already exists, skipping...")
    
    conn.commit()
    print(f"✓ Added {len(models)} models")
    
    # Get model IDs
    cursor.execute('SELECT id, name FROM models')
    model_map = {name: id for id, name in cursor.fetchall()}
    
    # Add Products
    products = [
        ('IP15P-256-BLK', 'iPhone 15 Pro 256GB Black', category_map['Smartphones'], brand_map['Apple'], 
         model_map['iPhone 15 Pro'], 95000, 115000, 119900, 10, 'Black', '256GB', '8GB', '1 Year'),
        
        ('IP15-128-BLU', 'iPhone 15 128GB Blue', category_map['Smartphones'], brand_map['Apple'], 
         model_map['iPhone 15'], 75000, 89000, 89900, 15, 'Blue', '128GB', '6GB', '1 Year'),
        
        ('GS24U-512-GRY', 'Galaxy S24 Ultra 512GB Gray', category_map['Smartphones'], brand_map['Samsung'], 
         model_map['Galaxy S24 Ultra'], 110000, 135000, 139900, 8, 'Gray', '512GB', '12GB', '1 Year'),
        
        ('GS24-256-VIO', 'Galaxy S24 256GB Violet', category_map['Smartphones'], brand_map['Samsung'], 
         model_map['Galaxy S24'], 70000, 85000, 89900, 12, 'Violet', '256GB', '8GB', '1 Year'),
        
        ('GA54-128-WHT', 'Galaxy A54 128GB White', category_map['Smartphones'], brand_map['Samsung'], 
         model_map['Galaxy A54'], 32000, 39000, 42999, 20, 'White', '128GB', '8GB', '1 Year'),
        
        ('P8P-256-BAY', 'Pixel 8 Pro 256GB Bay', category_map['Smartphones'], brand_map['Google'], 
         model_map['Pixel 8 Pro'], 85000, 105000, 109900, 5, 'Bay Blue', '256GB', '12GB', '1 Year'),
        
        ('P8-128-ROS', 'Pixel 8 128GB Rose', category_map['Smartphones'], brand_map['Google'], 
         model_map['Pixel 8'], 65000, 79000, 82999, 10, 'Rose', '128GB', '8GB', '1 Year'),
        
        ('OP12-256-GRN', 'OnePlus 12 256GB Green', category_map['Smartphones'], brand_map['OnePlus'], 
         model_map['OnePlus 12'], 62000, 75000, 79999, 8, 'Green', '256GB', '12GB', '1 Year'),
        
        ('RN13P-256-BLK', 'Redmi Note 13 Pro 256GB Black', category_map['Smartphones'], brand_map['Xiaomi'], 
         model_map['Redmi Note 13 Pro'], 25000, 32000, 34999, 25, 'Black', '256GB', '8GB', '1 Year'),
    ]
    
    product_ids = []
    for sku, name, cat_id, brand_id, model_id, cost, selling, mrp, stock, color, storage, ram, warranty in products:
        try:
            cursor.execute('''
                INSERT INTO products (
                    sku, name, category_id, brand_id, model_id, 
                    cost_price, selling_price, mrp, opening_stock, current_stock,
                    min_stock_level, color, storage_capacity, ram, warranty_period, status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (sku, name, cat_id, brand_id, model_id, cost, selling, mrp, stock, stock, 5, 
                  color, storage, ram, warranty, 'active'))
            
            product_id = cursor.lastrowid
            product_ids.append(product_id)
            
            # Add opening stock movement
            cursor.execute('''
                INSERT INTO stock_movements (product_id, type, quantity, reference_type, notes)
                VALUES (?, ?, ?, ?, ?)
            ''', (product_id, 'opening_stock', stock, 'manual', 'Initial stock'))
            
        except sqlite3.IntegrityError:
            print(f"Product '{sku}' already exists, skipping...")
    
    conn.commit()
    print(f"✓ Added {len(products)} products with opening stock")
    
    # Add a sample Purchase Order
    po_date = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
    try:
        cursor.execute('''
            INSERT INTO purchase_orders (
                po_number, supplier_name, supplier_contact, order_date, 
                expected_delivery, status, payment_status, total_amount, notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', ('PO-2024-001', 'Mobile Hub Distributors', '+91 9876543210', po_date, 
              (datetime.now() + timedelta(days=3)).strftime('%Y-%m-%d'), 
              'pending', 'unpaid', 250000, 'Bulk order for restocking'))
        
        po_id = cursor.lastrowid
        
        # Add PO items
        cursor.execute('''
            INSERT INTO purchase_order_items (
                po_id, product_id, product_name, category_id, brand_id, model_id, 
                quantity, cost_price, received_quantity
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (po_id, product_ids[0], 'iPhone 15 Pro 256GB Black', category_map['Smartphones'], 
              brand_map['Apple'], model_map['iPhone 15 Pro'], 5, 95000, 0))
        
        conn.commit()
        print(f"✓ Added sample purchase order")
    except sqlite3.IntegrityError:
        print("Purchase order already exists, skipping...")
    
    # Add a sample completed sale
    try:
        cursor.execute('''
            INSERT INTO pos_sales (
                sale_number, customer_name, customer_phone, sale_date,
                subtotal, discount_amount, discount_percentage, tax_amount, 
                tax_percentage, total_amount, payment_method, payment_status, cashier_name
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', ('SALE-2024-001', 'Rajesh Kumar', '+91 9988776655', 
              (datetime.now() - timedelta(days=2)).strftime('%Y-%m-%d %H:%M:%S'),
              32000, 1600, 5, 5760, 18, 36160, 'card', 'paid', 'Admin'))
        
        sale_id = cursor.lastrowid
        
        # Add sale item (assuming product_ids[4] is Galaxy A54)
        cursor.execute('''
            INSERT INTO pos_sale_items (
                sale_id, product_id, product_name, sku, quantity, 
                unit_price, discount, tax, total_price
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (sale_id, product_ids[4], 'Galaxy A54 128GB White', 'GA54-128-WHT', 
              1, 39000, 1950, 7020, 36160))
        
        # Update product stock
        cursor.execute('UPDATE products SET current_stock = current_stock - 1 WHERE id = ?', (product_ids[4],))
        
        # Add stock movement
        cursor.execute('''
            INSERT INTO stock_movements (product_id, type, quantity, reference_type, reference_id, notes)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (product_ids[4], 'sale', -1, 'pos_sale', sale_id, 'POS Sale'))
        
        conn.commit()
        print(f"✓ Added sample sale transaction")
    except sqlite3.IntegrityError:
        print("Sale already exists, skipping...")
    
    conn.close()
    print("\n✅ Database seeding completed successfully!")
    print("\nLogin credentials:")
    print("Username: admin")
    print("Password: admin123")

if __name__ == '__main__':
    seed_database()
