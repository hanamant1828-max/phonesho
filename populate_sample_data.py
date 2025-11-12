
import sqlite3
from datetime import datetime, timedelta
import random

DATABASE = 'inventory.db'

def populate_sample_data():
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    print("🚀 Starting to populate sample data...")
    
    # 1. Add Categories
    print("\n📁 Adding Categories...")
    categories = [
        ('Smartphones', 'Mobile phones and smartphones'),
        ('Tablets', 'Tablets and iPads'),
        ('Smartwatches', 'Wearable smart devices'),
        ('Accessories', 'Phone accessories and peripherals'),
        ('Audio', 'Headphones, earbuds, and speakers'),
        ('Power Banks', 'Portable charging solutions'),
        ('Cases & Covers', 'Protective cases and covers'),
        ('Screen Protectors', 'Tempered glass and screen guards'),
    ]
    
    category_ids = {}
    for name, desc in categories:
        try:
            cursor.execute('INSERT INTO categories (name, description) VALUES (?, ?)', (name, desc))
            category_ids[name] = cursor.lastrowid
            print(f"  ✓ Added category: {name}")
        except sqlite3.IntegrityError:
            cursor.execute('SELECT id FROM categories WHERE name = ?', (name,))
            category_ids[name] = cursor.fetchone()[0]
            print(f"  ⚠ Category already exists: {name}")
    
    # 2. Add Brands
    print("\n🏷️  Adding Brands...")
    brands = [
        ('Apple', 'Premium smartphones and tablets'),
        ('Samsung', 'Android smartphones and devices'),
        ('OnePlus', 'Flagship killer smartphones'),
        ('Xiaomi', 'Value for money smartphones'),
        ('Realme', 'Budget smartphones'),
        ('Oppo', 'Camera-focused smartphones'),
        ('Vivo', 'Innovative smartphone technology'),
        ('Google', 'Pixel smartphones'),
        ('Sony', 'Audio and electronics'),
        ('JBL', 'Audio equipment'),
        ('Anker', 'Charging accessories'),
        ('Belkin', 'Premium accessories'),
    ]
    
    brand_ids = {}
    for name, desc in brands:
        try:
            cursor.execute('INSERT INTO brands (name, description) VALUES (?, ?)', (name, desc))
            brand_ids[name] = cursor.lastrowid
            print(f"  ✓ Added brand: {name}")
        except sqlite3.IntegrityError:
            cursor.execute('SELECT id FROM brands WHERE name = ?', (name,))
            brand_ids[name] = cursor.fetchone()[0]
            print(f"  ⚠ Brand already exists: {name}")
    
    # 3. Add Models
    print("\n📱 Adding Models...")
    models = [
        ('iPhone 15 Pro', brand_ids['Apple'], '6.1" Super Retina XDR display'),
        ('iPhone 15', brand_ids['Apple'], '6.1" Super Retina XDR display'),
        ('iPhone 14', brand_ids['Apple'], '6.1" Super Retina XDR display'),
        ('Galaxy S24 Ultra', brand_ids['Samsung'], '6.8" Dynamic AMOLED 2X'),
        ('Galaxy S23', brand_ids['Samsung'], '6.1" Dynamic AMOLED 2X'),
        ('Galaxy A54', brand_ids['Samsung'], '6.4" Super AMOLED'),
        ('OnePlus 12', brand_ids['OnePlus'], '6.82" LTPO AMOLED'),
        ('OnePlus 11', brand_ids['OnePlus'], '6.7" LTPO3 AMOLED'),
        ('Redmi Note 13 Pro', brand_ids['Xiaomi'], '6.67" AMOLED'),
        ('Xiaomi 14', brand_ids['Xiaomi'], '6.36" LTPO AMOLED'),
        ('Realme 12 Pro', brand_ids['Realme'], '6.7" AMOLED'),
        ('Pixel 8 Pro', brand_ids['Google'], '6.7" LTPO OLED'),
        ('Pixel 8', brand_ids['Google'], '6.2" OLED'),
    ]
    
    model_ids = {}
    for name, brand_id, desc in models:
        try:
            cursor.execute('INSERT INTO models (name, brand_id, description) VALUES (?, ?, ?)', 
                         (name, brand_id, desc))
            model_ids[name] = cursor.lastrowid
            print(f"  ✓ Added model: {name}")
        except sqlite3.IntegrityError:
            cursor.execute('SELECT id FROM models WHERE name = ? AND brand_id = ?', (name, brand_id))
            model_ids[name] = cursor.fetchone()[0]
            print(f"  ⚠ Model already exists: {name}")
    
    # 4. Add Products
    print("\n📦 Adding Products...")
    products = [
        # Smartphones
        ('IP15P-256-BLK', 'iPhone 15 Pro 256GB Black', category_ids['Smartphones'], brand_ids['Apple'], 
         model_ids['iPhone 15 Pro'], 999.00, 1149.00, 1199.00, 15, 5, 'Shelf A1', 'Black', '256GB', '8GB', '12 months'),
        ('IP15-128-BLU', 'iPhone 15 128GB Blue', category_ids['Smartphones'], brand_ids['Apple'], 
         model_ids['iPhone 15'], 799.00, 899.00, 949.00, 20, 5, 'Shelf A2', 'Blue', '128GB', '6GB', '12 months'),
        ('IP14-128-WHT', 'iPhone 14 128GB White', category_ids['Smartphones'], brand_ids['Apple'], 
         model_ids['iPhone 14'], 699.00, 799.00, 849.00, 12, 3, 'Shelf A3', 'White', '128GB', '6GB', '12 months'),
        ('S24U-512-BLK', 'Galaxy S24 Ultra 512GB Black', category_ids['Smartphones'], brand_ids['Samsung'], 
         model_ids['Galaxy S24 Ultra'], 1199.00, 1349.00, 1399.00, 10, 3, 'Shelf B1', 'Black', '512GB', '12GB', '24 months'),
        ('S23-256-GRN', 'Galaxy S23 256GB Green', category_ids['Smartphones'], brand_ids['Samsung'], 
         model_ids['Galaxy S23'], 749.00, 849.00, 899.00, 18, 5, 'Shelf B2', 'Green', '256GB', '8GB', '24 months'),
        ('GA54-128-BLK', 'Galaxy A54 128GB Black', category_ids['Smartphones'], brand_ids['Samsung'], 
         model_ids['Galaxy A54'], 349.00, 449.00, 499.00, 25, 8, 'Shelf B3', 'Black', '128GB', '8GB', '12 months'),
        ('OP12-256-GRN', 'OnePlus 12 256GB Green', category_ids['Smartphones'], brand_ids['OnePlus'], 
         model_ids['OnePlus 12'], 699.00, 799.00, 849.00, 15, 5, 'Shelf C1', 'Green', '256GB', '12GB', '12 months'),
        ('OP11-128-BLK', 'OnePlus 11 128GB Black', category_ids['Smartphones'], brand_ids['OnePlus'], 
         model_ids['OnePlus 11'], 599.00, 699.00, 749.00, 20, 5, 'Shelf C2', 'Black', '128GB', '8GB', '12 months'),
        ('RN13P-256-BLU', 'Redmi Note 13 Pro 256GB Blue', category_ids['Smartphones'], brand_ids['Xiaomi'], 
         model_ids['Redmi Note 13 Pro'], 299.00, 379.00, 399.00, 30, 10, 'Shelf D1', 'Blue', '256GB', '8GB', '12 months'),
        ('X14-512-WHT', 'Xiaomi 14 512GB White', category_ids['Smartphones'], brand_ids['Xiaomi'], 
         model_ids['Xiaomi 14'], 799.00, 899.00, 949.00, 12, 4, 'Shelf D2', 'White', '512GB', '12GB', '12 months'),
        ('R12P-256-SLV', 'Realme 12 Pro 256GB Silver', category_ids['Smartphones'], brand_ids['Realme'], 
         model_ids['Realme 12 Pro'], 349.00, 429.00, 449.00, 22, 8, 'Shelf E1', 'Silver', '256GB', '8GB', '12 months'),
        ('P8P-256-BLK', 'Pixel 8 Pro 256GB Black', category_ids['Smartphones'], brand_ids['Google'], 
         model_ids['Pixel 8 Pro'], 899.00, 999.00, 1049.00, 10, 3, 'Shelf F1', 'Black', '256GB', '12GB', '24 months'),
        ('P8-128-BLU', 'Pixel 8 128GB Blue', category_ids['Smartphones'], brand_ids['Google'], 
         model_ids['Pixel 8'], 649.00, 749.00, 799.00, 15, 5, 'Shelf F2', 'Blue', '128GB', '8GB', '24 months'),
        
        # Accessories
        ('AP-CASE-IP15', 'Apple Silicone Case iPhone 15', category_ids['Cases & Covers'], brand_ids['Apple'], 
         None, 29.00, 49.00, 59.00, 50, 15, 'Shelf G1', 'Black', None, None, '6 months'),
        ('SM-CASE-S24', 'Samsung Clear Case S24', category_ids['Cases & Covers'], brand_ids['Samsung'], 
         None, 19.00, 35.00, 39.00, 45, 15, 'Shelf G2', 'Clear', None, None, '6 months'),
        ('TG-IP15', 'Tempered Glass iPhone 15', category_ids['Screen Protectors'], None, 
         None, 5.00, 12.00, 15.00, 100, 30, 'Shelf H1', None, None, None, '3 months'),
        ('TG-S24', 'Tempered Glass Galaxy S24', category_ids['Screen Protectors'], None, 
         None, 5.00, 12.00, 15.00, 80, 30, 'Shelf H2', None, None, None, '3 months'),
        
        # Audio
        ('AP-AIRPODS-PRO2', 'AirPods Pro 2nd Gen', category_ids['Audio'], brand_ids['Apple'], 
         None, 199.00, 249.00, 269.00, 25, 8, 'Shelf I1', 'White', None, None, '12 months'),
        ('JBL-TUNE230NC', 'JBL Tune 230NC TWS', category_ids['Audio'], brand_ids['JBL'], 
         None, 79.00, 99.00, 119.00, 30, 10, 'Shelf I2', 'Black', None, None, '12 months'),
        ('SONY-WH1000XM5', 'Sony WH-1000XM5', category_ids['Audio'], brand_ids['Sony'], 
         None, 349.00, 399.00, 429.00, 15, 5, 'Shelf I3', 'Black', None, None, '24 months'),
        
        # Power Banks
        ('ANKER-20K', 'Anker PowerCore 20000mAh', category_ids['Power Banks'], brand_ids['Anker'], 
         None, 39.00, 59.00, 69.00, 40, 12, 'Shelf J1', 'Black', '20000mAh', None, '18 months'),
        ('ANKER-10K', 'Anker PowerCore 10000mAh', category_ids['Power Banks'], brand_ids['Anker'], 
         None, 25.00, 39.00, 49.00, 50, 15, 'Shelf J2', 'White', '10000mAh', None, '18 months'),
    ]
    
    product_ids = {}
    for sku, name, cat_id, brand_id, model_id, cost, selling, mrp, stock, min_stock, location, color, storage, ram, warranty in products:
        try:
            cursor.execute('''
                INSERT INTO products (
                    sku, name, category_id, brand_id, model_id, description,
                    cost_price, selling_price, mrp, opening_stock, current_stock,
                    min_stock_level, storage_location, color, storage_capacity, ram,
                    warranty_period, status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (sku, name, cat_id, brand_id, model_id, f'{name} - Premium quality product',
                  cost, selling, mrp, stock, stock, min_stock, location, color, storage, ram, warranty, 'active'))
            product_ids[sku] = cursor.lastrowid
            print(f"  ✓ Added product: {name} (Stock: {stock})")
            
            # Add opening stock movement
            cursor.execute('''
                INSERT INTO stock_movements (product_id, type, quantity, reference_type, notes)
                VALUES (?, ?, ?, ?, ?)
            ''', (cursor.lastrowid, 'opening_stock', stock, 'manual', 'Initial stock'))
            
        except sqlite3.IntegrityError:
            cursor.execute('SELECT id FROM products WHERE sku = ?', (sku,))
            result = cursor.fetchone()
            if result:
                product_ids[sku] = result[0]
            print(f"  ⚠ Product already exists: {name}")
    
    # 5. Add IMEI numbers for smartphones
    print("\n🔢 Adding IMEI numbers for smartphones...")
    smartphone_products = [
        ('IP15P-256-BLK', 5),
        ('IP15-128-BLU', 5),
        ('S24U-512-BLK', 3),
        ('S23-256-GRN', 5),
        ('OP12-256-GRN', 4),
        ('P8P-256-BLK', 3),
    ]
    
    for sku, count in smartphone_products:
        if sku in product_ids:
            product_id = product_ids[sku]
            for i in range(count):
                timestamp = datetime.now().timestamp()
                imei = f"{int(timestamp * 1000) % 1000000000000000:015d}"
                try:
                    cursor.execute('''
                        INSERT INTO product_imei (product_id, imei, status, received_date)
                        VALUES (?, ?, ?, ?)
                    ''', (product_id, imei, 'in_stock', datetime.now()))
                    print(f"  ✓ Added IMEI for {sku}: {imei}")
                except sqlite3.IntegrityError:
                    print(f"  ⚠ IMEI already exists for {sku}")
    
    # 6. Add Stock Adjustments
    print("\n📊 Adding Stock Adjustments...")
    adjustments = [
        ('IP15-128-BLU', 10, 'Received from supplier - Batch A'),
        ('S23-256-GRN', 8, 'Stock replenishment'),
        ('GA54-128-BLK', 15, 'Bulk purchase discount batch'),
        ('RN13P-256-BLU', 20, 'New stock arrival'),
        ('ANKER-20K', 25, 'Promotional stock'),
    ]
    
    for sku, qty, notes in adjustments:
        if sku in product_ids:
            product_id = product_ids[sku]
            
            # Update product stock
            cursor.execute('UPDATE products SET current_stock = current_stock + ? WHERE id = ?', 
                         (qty, product_id))
            
            # Record stock movement
            cursor.execute('''
                INSERT INTO stock_movements (product_id, type, quantity, reference_type, notes)
                VALUES (?, ?, ?, ?, ?)
            ''', (product_id, 'adjustment', qty, 'manual', notes))
            
            print(f"  ✓ Added stock adjustment: {sku} +{qty} units")
    
    # 7. Add Purchase Orders
    print("\n📝 Adding Purchase Orders...")
    po_date = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
    
    try:
        cursor.execute('''
            INSERT INTO purchase_orders (
                po_number, supplier_name, supplier_contact, order_date,
                expected_delivery, status, total_amount, notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', ('PO-2024-001', 'Apple Authorized Distributor', '+1-800-APPLE', po_date,
              (datetime.now() + timedelta(days=3)).strftime('%Y-%m-%d'), 'pending', 15000.00,
              'Monthly stock replenishment'))
        po_id = cursor.lastrowid
        print(f"  ✓ Added Purchase Order: PO-2024-001")
        
        # Add PO items
        po_items = [
            (product_ids.get('IP15P-256-BLK'), 'iPhone 15 Pro 256GB Black', 5, 999.00),
            (product_ids.get('IP15-128-BLU'), 'iPhone 15 128GB Blue', 10, 799.00),
        ]
        
        for prod_id, name, qty, cost in po_items:
            if prod_id:
                cursor.execute('''
                    INSERT INTO purchase_order_items (
                        po_id, product_id, product_name, quantity, cost_price
                    ) VALUES (?, ?, ?, ?, ?)
                ''', (po_id, prod_id, name, qty, cost))
                print(f"    ✓ Added PO item: {name} x {qty}")
    except Exception as e:
        print(f"  ⚠ Error adding purchase order: {e}")
    
    # Commit all changes
    conn.commit()
    
    # Print summary
    print("\n" + "="*60)
    print("✅ SAMPLE DATA POPULATION COMPLETE!")
    print("="*60)
    
    cursor.execute('SELECT COUNT(*) FROM categories')
    print(f"📁 Categories: {cursor.fetchone()[0]}")
    
    cursor.execute('SELECT COUNT(*) FROM brands')
    print(f"🏷️  Brands: {cursor.fetchone()[0]}")
    
    cursor.execute('SELECT COUNT(*) FROM models')
    print(f"📱 Models: {cursor.fetchone()[0]}")
    
    cursor.execute('SELECT COUNT(*) FROM products')
    print(f"📦 Products: {cursor.fetchone()[0]}")
    
    cursor.execute('SELECT COUNT(*) FROM product_imei')
    print(f"🔢 IMEI Numbers: {cursor.fetchone()[0]}")
    
    cursor.execute('SELECT COUNT(*) FROM stock_movements')
    print(f"📊 Stock Movements: {cursor.fetchone()[0]}")
    
    cursor.execute('SELECT COUNT(*) FROM purchase_orders')
    print(f"📝 Purchase Orders: {cursor.fetchone()[0]}")
    
    cursor.execute('SELECT SUM(current_stock * selling_price) FROM products')
    total_value = cursor.fetchone()[0] or 0
    print(f"💰 Total Inventory Value: ${total_value:,.2f}")
    
    print("="*60)
    print("\n🎉 You can now login and explore the system!")
    print("   Username: admin")
    print("   Password: admin123")
    print("="*60 + "\n")
    
    conn.close()

if __name__ == '__main__':
    populate_sample_data()
