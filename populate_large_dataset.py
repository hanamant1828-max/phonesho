
import sqlite3
from datetime import datetime, timedelta
import random
import string

DATABASE = 'inventory.db'

def generate_sku(prefix, index):
    """Generate unique SKU"""
    return f"{prefix}-{index:05d}"

def generate_imei():
    """Generate a random 15-digit IMEI"""
    return ''.join([str(random.randint(0, 9)) for _ in range(15)])

def generate_phone():
    """Generate Indian phone number"""
    return f"+91 {random.randint(7000000000, 9999999999)}"

def populate_large_dataset():
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    print("🚀 Starting large dataset population...")
    print("="*70)
    
    # 1. Extended Categories (50 categories)
    print("\n📁 Adding 50 Categories...")
    categories = [
        ('Smartphones', 'Mobile phones and smartphones'),
        ('Feature Phones', 'Basic mobile phones'),
        ('Tablets', 'Tablets and iPads'),
        ('Laptops', 'Laptop computers'),
        ('Desktop PCs', 'Desktop computers'),
        ('Smartwatches', 'Wearable smart devices'),
        ('Fitness Trackers', 'Health and fitness bands'),
        ('Accessories', 'Phone accessories and peripherals'),
        ('Audio', 'Headphones, earbuds, and speakers'),
        ('Power Banks', 'Portable charging solutions'),
        ('Cases & Covers', 'Protective cases and covers'),
        ('Screen Protectors', 'Tempered glass and screen guards'),
        ('Chargers', 'Wall and car chargers'),
        ('Cables', 'USB and charging cables'),
        ('Memory Cards', 'SD and microSD cards'),
        ('USB Drives', 'Flash drives and pen drives'),
        ('External HDDs', 'External hard drives'),
        ('SSDs', 'Solid state drives'),
        ('Keyboards', 'Computer keyboards'),
        ('Mouse', 'Computer mice'),
        ('Webcams', 'Web cameras'),
        ('Monitors', 'Computer monitors'),
        ('Printers', 'Printing devices'),
        ('Scanners', 'Document scanners'),
        ('Routers', 'WiFi routers'),
        ('Modems', 'Internet modems'),
        ('Network Switches', 'Network switches'),
        ('Gaming Consoles', 'Gaming devices'),
        ('Gaming Accessories', 'Gaming peripherals'),
        ('VR Headsets', 'Virtual reality devices'),
        ('Smart Home', 'IoT devices'),
        ('Security Cameras', 'Surveillance cameras'),
        ('Drones', 'Camera drones'),
        ('Action Cameras', 'Sports cameras'),
        ('DSLR Cameras', 'Professional cameras'),
        ('Mirrorless Cameras', 'Compact system cameras'),
        ('Camera Lenses', 'Photography lenses'),
        ('Tripods', 'Camera tripods'),
        ('Photography Lighting', 'Studio lights'),
        ('Microphones', 'Recording microphones'),
        ('Audio Interfaces', 'Sound cards'),
        ('Studio Monitors', 'Professional speakers'),
        ('DJ Equipment', 'DJ gear'),
        ('Smart Speakers', 'Voice assistants'),
        ('Soundbars', 'TV soundbars'),
        ('Projectors', 'Video projectors'),
        ('Streaming Devices', 'Media streaming'),
        ('E-Readers', 'Digital book readers'),
        ('Graphics Tablets', 'Drawing tablets'),
        ('3D Printers', '3D printing devices'),
    ]
    
    category_ids = {}
    for name, desc in categories:
        try:
            cursor.execute('INSERT INTO categories (name, description) VALUES (?, ?)', (name, desc))
            category_ids[name] = cursor.lastrowid
            print(f"  ✓ {name}")
        except sqlite3.IntegrityError:
            cursor.execute('SELECT id FROM categories WHERE name = ?', (name,))
            category_ids[name] = cursor.fetchone()[0]
    
    # 2. Extended Brands (100 brands)
    print("\n🏷️  Adding 100 Brands...")
    brands = [
        ('Apple', 'Premium electronics'), ('Samsung', 'Android devices'),
        ('OnePlus', 'Flagship smartphones'), ('Xiaomi', 'Value devices'),
        ('Realme', 'Budget smartphones'), ('Oppo', 'Camera phones'),
        ('Vivo', 'Innovative phones'), ('Google', 'Pixel devices'),
        ('Sony', 'Electronics'), ('JBL', 'Audio equipment'),
        ('Anker', 'Charging accessories'), ('Belkin', 'Premium accessories'),
        ('Nokia', 'Reliable phones'), ('Motorola', 'Moto series'),
        ('Asus', 'ROG gaming'), ('Acer', 'Computing devices'),
        ('Lenovo', 'ThinkPad series'), ('HP', 'Business laptops'),
        ('Dell', 'Precision workstations'), ('MSI', 'Gaming laptops'),
        ('Razer', 'Gaming peripherals'), ('Logitech', 'Peripherals'),
        ('Corsair', 'Gaming gear'), ('SteelSeries', 'Gaming audio'),
        ('HyperX', 'Gaming headsets'), ('Bose', 'Premium audio'),
        ('Sennheiser', 'Professional audio'), ('Audio-Technica', 'Studio gear'),
        ('Shure', 'Microphones'), ('Blue Microphones', 'USB mics'),
        ('Rode', 'Video microphones'), ('Focusrite', 'Audio interfaces'),
        ('PreSonus', 'Studio equipment'), ('Behringer', 'Audio gear'),
        ('Yamaha', 'Musical instruments'), ('Roland', 'Electronic music'),
        ('Korg', 'Synthesizers'), ('Pioneer', 'DJ equipment'),
        ('Numark', 'DJ controllers'), ('Seagate', 'Hard drives'),
        ('Western Digital', 'Storage devices'), ('SanDisk', 'Memory cards'),
        ('Kingston', 'RAM and storage'), ('Crucial', 'Memory modules'),
        ('Samsung Memory', 'SSDs'), ('Intel', 'Processors'),
        ('AMD', 'CPUs and GPUs'), ('NVIDIA', 'Graphics cards'),
        ('Gigabyte', 'Motherboards'), ('ASUS ROG', 'Gaming hardware'),
        ('TP-Link', 'Networking'), ('Netgear', 'Routers'),
        ('D-Link', 'Network devices'), ('Linksys', 'WiFi systems'),
        ('Ubiquiti', 'Enterprise networking'), ('Cisco', 'Network equipment'),
        ('Canon', 'Cameras and printers'), ('Nikon', 'Photography'),
        ('Fujifilm', 'Cameras'), ('Panasonic', 'Video cameras'),
        ('GoPro', 'Action cameras'), ('DJI', 'Drones'),
        ('Parrot', 'Consumer drones'), ('Manfrotto', 'Tripods'),
        ('Godox', 'Photography lighting'), ('Neewer', 'Studio equipment'),
        ('Elgato', 'Streaming gear'), ('Blue Yeti', 'USB microphones'),
        ('Wacom', 'Graphics tablets'), ('Huion', 'Drawing tablets'),
        ('XP-Pen', 'Digital art'), ('Epson', 'Printers'),
        ('Brother', 'Office printers'), ('Xerox', 'Document solutions'),
        ('Zebra', 'Label printers'), ('Dymo', 'Label makers'),
        ('Amazon', 'Echo devices'), ('Google Nest', 'Smart home'),
        ('Ring', 'Security devices'), ('Arlo', 'Security cameras'),
        ('Wyze', 'Budget smart home'), ('Philips Hue', 'Smart lighting'),
        ('TP-Link Kasa', 'Smart plugs'), ('Sonos', 'Multi-room audio'),
        ('Roku', 'Streaming devices'), ('Apple TV', 'Media players'),
        ('Chromecast', 'Streaming sticks'), ('Fire TV', 'Amazon streaming'),
        ('NVIDIA Shield', 'Gaming streaming'), ('Kindle', 'E-readers'),
        ('Kobo', 'E-book readers'), ('Pocketbook', 'Digital readers'),
        ('LG', 'Electronics'), ('Panasonic Lumix', 'Cameras'),
        ('Olympus', 'Photography'), ('Sigma', 'Camera lenses'),
        ('Tamron', 'Photography lenses'), ('Rode VideoMic', 'Camera mics'),
        ('Zoom', 'Audio recorders'), ('Tascam', 'Recording devices'),
        ('Blackmagic', 'Video equipment'), ('Atomos', 'Video recorders'),
    ]
    
    brand_ids = {}
    for name, desc in brands:
        try:
            cursor.execute('INSERT INTO brands (name, description) VALUES (?, ?)', (name, desc))
            brand_ids[name] = cursor.lastrowid
            print(f"  ✓ {name}")
        except sqlite3.IntegrityError:
            cursor.execute('SELECT id FROM brands WHERE name = ?', (name,))
            brand_ids[name] = cursor.fetchone()[0]
    
    # 3. Extended Models (200 models)
    print("\n📱 Adding 200 Models...")
    models = []
    
    # Smartphones (80 models)
    smartphone_models = [
        ('iPhone 15 Pro Max', 'Apple'), ('iPhone 15 Pro', 'Apple'), ('iPhone 15 Plus', 'Apple'), ('iPhone 15', 'Apple'),
        ('iPhone 14 Pro Max', 'Apple'), ('iPhone 14 Pro', 'Apple'), ('iPhone 14 Plus', 'Apple'), ('iPhone 14', 'Apple'),
        ('iPhone 13 Pro Max', 'Apple'), ('iPhone 13 Pro', 'Apple'), ('iPhone 13', 'Apple'), ('iPhone SE 3rd Gen', 'Apple'),
        ('Galaxy S24 Ultra', 'Samsung'), ('Galaxy S24 Plus', 'Samsung'), ('Galaxy S24', 'Samsung'),
        ('Galaxy S23 Ultra', 'Samsung'), ('Galaxy S23 Plus', 'Samsung'), ('Galaxy S23', 'Samsung'),
        ('Galaxy Z Fold 5', 'Samsung'), ('Galaxy Z Flip 5', 'Samsung'), ('Galaxy A54', 'Samsung'),
        ('Galaxy A34', 'Samsung'), ('Galaxy A24', 'Samsung'), ('Galaxy A14', 'Samsung'),
        ('Galaxy M54', 'Samsung'), ('Galaxy M34', 'Samsung'), ('Galaxy M14', 'Samsung'),
        ('OnePlus 12', 'OnePlus'), ('OnePlus 11', 'OnePlus'), ('OnePlus Nord 3', 'OnePlus'),
        ('OnePlus Nord CE 3', 'OnePlus'), ('OnePlus 11R', 'OnePlus'),
        ('Xiaomi 14', 'Xiaomi'), ('Xiaomi 13T Pro', 'Xiaomi'), ('Redmi Note 13 Pro Max', 'Xiaomi'),
        ('Redmi Note 13 Pro', 'Xiaomi'), ('Redmi Note 13', 'Xiaomi'), ('Redmi 13C', 'Xiaomi'),
        ('Poco X6 Pro', 'Xiaomi'), ('Poco X6', 'Xiaomi'), ('Poco M6 Pro', 'Xiaomi'),
        ('Realme 12 Pro Plus', 'Realme'), ('Realme 12 Pro', 'Realme'), ('Realme 12', 'Realme'),
        ('Realme Narzo 60 Pro', 'Realme'), ('Realme Narzo 60', 'Realme'), ('Realme C67', 'Realme'),
        ('Pixel 8 Pro', 'Google'), ('Pixel 8', 'Google'), ('Pixel 7a', 'Google'),
        ('Pixel Fold', 'Google'), ('Pixel 7 Pro', 'Google'),
        ('Vivo V29 Pro', 'Vivo'), ('Vivo V29', 'Vivo'), ('Vivo Y100', 'Vivo'),
        ('Vivo T2 Pro', 'Vivo'), ('Vivo Y27', 'Vivo'),
        ('Oppo Reno 11 Pro', 'Oppo'), ('Oppo Reno 11', 'Oppo'), ('Oppo Find N3', 'Oppo'),
        ('Oppo F25 Pro', 'Oppo'), ('Oppo A79', 'Oppo'),
        ('Moto Edge 40 Pro', 'Motorola'), ('Moto Edge 40', 'Motorola'), ('Moto G84', 'Motorola'),
        ('Moto G73', 'Motorola'), ('Moto G54', 'Motorola'),
        ('Nokia G42', 'Nokia'), ('Nokia C32', 'Nokia'), ('Nokia 105', 'Nokia'),
        ('Nothing Phone 2', 'OnePlus'), ('Nothing Phone 2a', 'OnePlus'),
        ('Sony Xperia 1 V', 'Sony'), ('Sony Xperia 5 V', 'Sony'), ('Sony Xperia 10 V', 'Sony'),
    ]
    
    for model_name, brand_name in smartphone_models:
        if brand_name in brand_ids:
            models.append((model_name, brand_ids[brand_name], f'{model_name} smartphone'))
    
    # Laptops (40 models)
    laptop_models = [
        ('MacBook Pro 16"', 'Apple'), ('MacBook Pro 14"', 'Apple'), ('MacBook Air M2', 'Apple'),
        ('MacBook Air M1', 'Apple'),
        ('Galaxy Book 3 Pro', 'Samsung'), ('Galaxy Book 3', 'Samsung'),
        ('ThinkPad X1 Carbon', 'Lenovo'), ('ThinkPad T14', 'Lenovo'), ('IdeaPad Gaming 3', 'Lenovo'),
        ('Yoga 9i', 'Lenovo'), ('Legion 5 Pro', 'Lenovo'),
        ('XPS 15', 'Dell'), ('XPS 13', 'Dell'), ('Inspiron 15', 'Dell'),
        ('Alienware M15', 'Dell'), ('G15 Gaming', 'Dell'),
        ('Spectre x360', 'HP'), ('Envy 13', 'HP'), ('Pavilion 15', 'HP'),
        ('Omen 16', 'HP'), ('EliteBook 840', 'HP'),
        ('ZenBook 14', 'Asus'), ('VivoBook 15', 'Asus'), ('ROG Zephyrus G14', 'Asus'),
        ('ROG Strix G15', 'Asus'), ('TUF Gaming A15', 'Asus'),
        ('Swift 3', 'Acer'), ('Aspire 5', 'Acer'), ('Predator Helios 300', 'Acer'),
        ('Nitro 5', 'Acer'),
        ('GS66 Stealth', 'MSI'), ('GP66 Leopard', 'MSI'), ('Katana GF66', 'MSI'),
        ('Blade 15', 'Razer'), ('Blade 14', 'Razer'),
        ('Gram 17', 'LG'), ('Gram 16', 'LG'), ('Gram 14', 'LG'),
        ('Surface Laptop 5', 'Microsoft'), ('Surface Pro 9', 'Microsoft'),
    ]
    
    for model_name, brand_name in laptop_models:
        if brand_name in brand_ids:
            models.append((model_name, brand_ids[brand_name], f'{model_name} laptop'))
    
    # Other devices (80 models)
    other_models = [
        ('AirPods Pro 2nd Gen', 'Apple'), ('AirPods 3rd Gen', 'Apple'), ('AirPods Max', 'Apple'),
        ('Apple Watch Series 9', 'Apple'), ('Apple Watch SE', 'Apple'), ('Apple Watch Ultra 2', 'Apple'),
        ('iPad Pro 12.9"', 'Apple'), ('iPad Air', 'Apple'), ('iPad 10th Gen', 'Apple'), ('iPad Mini', 'Apple'),
        ('Galaxy Buds 2 Pro', 'Samsung'), ('Galaxy Buds FE', 'Samsung'), ('Galaxy Watch 6', 'Samsung'),
        ('Galaxy Tab S9', 'Samsung'), ('Galaxy Tab A9', 'Samsung'),
        ('WH-1000XM5', 'Sony'), ('WH-1000XM4', 'Sony'), ('WF-1000XM5', 'Sony'), ('LinkBuds S', 'Sony'),
        ('Tune 230NC', 'JBL'), ('Live Pro 2', 'JBL'), ('Flip 6', 'JBL'), ('Charge 5', 'JBL'),
        ('QuietComfort 45', 'Bose'), ('QuietComfort Ultra', 'Bose'), ('Sport Earbuds', 'Bose'),
        ('PowerCore 20000', 'Anker'), ('PowerCore 10000', 'Anker'), ('Nano Power Bank', 'Anker'),
        ('G502 Hero', 'Logitech'), ('MX Master 3S', 'Logitech'), ('G Pro X', 'Logitech'),
        ('K380', 'Logitech'), ('MX Keys', 'Logitech'),
        ('DeathAdder V3', 'Razer'), ('BlackWidow V3', 'Razer'), ('Kraken V3', 'Razer'),
        ('Cloud II', 'HyperX'), ('Cloud Alpha', 'HyperX'), ('Alloy Origins', 'HyperX'),
        ('Arctis Nova Pro', 'SteelSeries'), ('Apex Pro', 'SteelSeries'),
        ('BarraCuda 2TB', 'Seagate'), ('IronWolf 4TB', 'Seagate'),
        ('WD Blue 1TB', 'Western Digital'), ('WD Black SN850X', 'Western Digital'),
        ('Extreme Pro 128GB', 'SanDisk'), ('Ultra 256GB', 'SanDisk'),
        ('Fury Beast 16GB', 'Kingston'), ('A400 480GB', 'Kingston'),
        ('Hero 11 Black', 'GoPro'), ('Hero 12 Black', 'GoPro'),
        ('Mini 3 Pro', 'DJI'), ('Air 3', 'DJI'), ('Mavic 3', 'DJI'),
        ('EOS R6 Mark II', 'Canon'), ('EOS R10', 'Canon'),
        ('Z9', 'Nikon'), ('Z6 III', 'Nikon'),
        ('X-T5', 'Fujifilm'), ('X-S20', 'Fujifilm'),
        ('Echo Dot 5th Gen', 'Amazon'), ('Echo Show 8', 'Amazon'),
        ('Nest Hub 2nd Gen', 'Google Nest'), ('Nest Cam', 'Google Nest'),
        ('Video Doorbell Pro', 'Ring'), ('Stick Up Cam', 'Ring'),
        ('Streaming Stick 4K', 'Roku'), ('Ultra', 'Roku'),
        ('4K', 'Chromecast'), ('HD', 'Chromecast'),
        ('Paperwhite', 'Kindle'), ('Oasis', 'Kindle'),
    ]
    
    for model_name, brand_name in other_models:
        if brand_name in brand_ids:
            models.append((model_name, brand_ids[brand_name], f'{model_name} device'))
    
    model_ids = {}
    for name, brand_id, desc in models:
        try:
            cursor.execute('INSERT INTO models (name, brand_id, description) VALUES (?, ?, ?)', 
                         (name, brand_id, desc))
            model_ids[name] = cursor.lastrowid
            print(f"  ✓ {name}")
        except sqlite3.IntegrityError:
            cursor.execute('SELECT id, name FROM models WHERE name = ? AND brand_id = ?', (name, brand_id))
            result = cursor.fetchone()
            if result:
                model_ids[name] = result[0]
    
    # 4. Products (800+ products)
    print("\n📦 Adding 800+ Products...")
    
    colors = ['Black', 'White', 'Blue', 'Green', 'Red', 'Silver', 'Gold', 'Gray', 'Purple', 'Pink', 'Rose Gold', 'Midnight', 'Starlight']
    storage_options = ['64GB', '128GB', '256GB', '512GB', '1TB', '2TB']
    ram_options = ['4GB', '6GB', '8GB', '12GB', '16GB', '32GB']
    
    products_added = 0
    product_ids_list = []
    
    # Generate smartphone products
    for idx, (model_name, brand_name) in enumerate(smartphone_models[:100], 1):
        if model_name not in model_ids:
            continue
            
        brand_id = brand_ids.get(brand_name)
        model_id = model_ids[model_name]
        category_id = category_ids['Smartphones']
        
        color = random.choice(colors)
        storage = random.choice(storage_options)
        ram = random.choice(ram_options)
        
        base_price = random.randint(15000, 150000)
        cost_price = base_price
        selling_price = int(base_price * 1.20)
        mrp = int(base_price * 1.25)
        stock = random.randint(5, 50)
        
        sku = generate_sku(f"SP{idx}", idx)
        name = f"{model_name} {storage} {color}"
        
        try:
            cursor.execute('''
                INSERT INTO products (
                    sku, name, category_id, brand_id, model_id, description,
                    cost_price, selling_price, mrp, opening_stock, current_stock,
                    min_stock_level, storage_location, color, storage_capacity, ram,
                    warranty_period, status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (sku, name, category_id, brand_id, model_id, f'{name} - Premium quality',
                  cost_price, selling_price, mrp, stock, stock, 5, f'Shelf-{chr(65 + (idx % 26))}{idx % 10}',
                  color, storage, ram, '12 months', 'active'))
            
            product_id = cursor.lastrowid
            product_ids_list.append(product_id)
            
            cursor.execute('''
                INSERT INTO stock_movements (product_id, type, quantity, reference_type, notes)
                VALUES (?, ?, ?, ?, ?)
            ''', (product_id, 'opening_stock', stock, 'manual', 'Initial stock'))
            
            products_added += 1
            if products_added % 50 == 0:
                print(f"  ✓ Added {products_added} products...")
        except sqlite3.IntegrityError:
            pass
    
    # Generate laptop products
    for idx, (model_name, brand_name) in enumerate(laptop_models[:80], 201):
        if model_name not in model_ids:
            continue
            
        brand_id = brand_ids.get(brand_name)
        model_id = model_ids[model_name]
        category_id = category_ids['Laptops']
        
        color = random.choice(['Silver', 'Space Gray', 'Black', 'White'])
        storage = random.choice(['256GB', '512GB', '1TB', '2TB'])
        ram = random.choice(['8GB', '16GB', '32GB'])
        
        base_price = random.randint(40000, 250000)
        cost_price = base_price
        selling_price = int(base_price * 1.15)
        mrp = int(base_price * 1.20)
        stock = random.randint(3, 20)
        
        sku = generate_sku(f"LP{idx}", idx)
        name = f"{model_name} {storage} {ram}"
        
        try:
            cursor.execute('''
                INSERT INTO products (
                    sku, name, category_id, brand_id, model_id, description,
                    cost_price, selling_price, mrp, opening_stock, current_stock,
                    min_stock_level, storage_location, color, storage_capacity, ram,
                    warranty_period, status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (sku, name, category_id, brand_id, model_id, f'{name} - Professional grade',
                  cost_price, selling_price, mrp, stock, stock, 3, f'Shelf-L{idx % 10}',
                  color, storage, ram, '24 months', 'active'))
            
            product_id = cursor.lastrowid
            product_ids_list.append(product_id)
            
            cursor.execute('''
                INSERT INTO stock_movements (product_id, type, quantity, reference_type, notes)
                VALUES (?, ?, ?, ?, ?)
            ''', (product_id, 'opening_stock', stock, 'manual', 'Initial stock'))
            
            products_added += 1
            if products_added % 50 == 0:
                print(f"  ✓ Added {products_added} products...")
        except sqlite3.IntegrityError:
            pass
    
    # Generate accessory products
    accessory_categories = ['Audio', 'Power Banks', 'Cases & Covers', 'Screen Protectors', 
                           'Chargers', 'Cables', 'Memory Cards', 'USB Drives']
    
    for idx in range(301, 1001):
        category_name = random.choice(accessory_categories)
        category_id = category_ids.get(category_name)
        
        brand_name = random.choice(list(brand_ids.keys()))
        brand_id = brand_ids[brand_name]
        
        base_price = random.randint(500, 15000)
        cost_price = base_price
        selling_price = int(base_price * 1.30)
        mrp = int(base_price * 1.40)
        stock = random.randint(10, 100)
        
        sku = generate_sku(f"AC{idx}", idx)
        name = f"{brand_name} {category_name} {random.choice(['Pro', 'Elite', 'Basic', 'Premium', 'Standard'])}"
        
        try:
            cursor.execute('''
                INSERT INTO products (
                    sku, name, category_id, brand_id, model_id, description,
                    cost_price, selling_price, mrp, opening_stock, current_stock,
                    min_stock_level, storage_location, color, storage_capacity, ram,
                    warranty_period, status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (sku, name, category_id, brand_id, None, f'{name} - Quality accessory',
                  cost_price, selling_price, mrp, stock, stock, 10, f'Shelf-A{idx % 20}',
                  random.choice(colors), None, None, '6 months', 'active'))
            
            product_id = cursor.lastrowid
            product_ids_list.append(product_id)
            
            cursor.execute('''
                INSERT INTO stock_movements (product_id, type, quantity, reference_type, notes)
                VALUES (?, ?, ?, ?, ?)
            ''', (product_id, 'opening_stock', stock, 'manual', 'Initial stock'))
            
            products_added += 1
            if products_added % 100 == 0:
                print(f"  ✓ Added {products_added} products...")
        except sqlite3.IntegrityError:
            pass
    
    print(f"\n  ✅ Total products added: {products_added}")
    
    # 5. Add IMEI numbers for smartphones (500+ IMEIs)
    print("\n🔢 Adding 500+ IMEI numbers...")
    imei_count = 0
    
    cursor.execute('''
        SELECT p.id, p.sku, p.current_stock 
        FROM products p 
        WHERE p.category_id = ? 
        LIMIT 100
    ''', (category_ids['Smartphones'],))
    
    smartphone_products = cursor.fetchall()
    
    for product_id, sku, stock in smartphone_products:
        imeis_to_add = min(stock, random.randint(3, 8))
        for _ in range(imeis_to_add):
            imei = generate_imei()
            try:
                cursor.execute('''
                    INSERT INTO product_imei (product_id, imei, status, received_date)
                    VALUES (?, ?, ?, ?)
                ''', (product_id, imei, 'in_stock', datetime.now()))
                imei_count += 1
            except sqlite3.IntegrityError:
                pass
    
    print(f"  ✅ Total IMEI numbers added: {imei_count}")
    
    # 6. Add Stock Adjustments (100+ adjustments)
    print("\n📊 Adding 100+ Stock Adjustments...")
    adjustment_count = 0
    
    adjustment_notes = [
        'Received from supplier',
        'Stock replenishment',
        'Bulk purchase discount batch',
        'New stock arrival',
        'Promotional stock',
        'Return to stock',
        'Warehouse transfer',
        'Inventory count correction',
    ]
    
    for _ in range(150):
        if not product_ids_list:
            break
            
        product_id = random.choice(product_ids_list)
        quantity = random.randint(5, 30)
        notes = random.choice(adjustment_notes)
        
        try:
            cursor.execute('UPDATE products SET current_stock = current_stock + ? WHERE id = ?', 
                         (quantity, product_id))
            
            cursor.execute('''
                INSERT INTO stock_movements (product_id, type, quantity, reference_type, notes)
                VALUES (?, ?, ?, ?, ?)
            ''', (product_id, 'adjustment', quantity, 'manual', notes))
            
            adjustment_count += 1
            if adjustment_count % 25 == 0:
                print(f"  ✓ Added {adjustment_count} adjustments...")
        except Exception:
            pass
    
    print(f"  ✅ Total stock adjustments added: {adjustment_count}")
    
    # 7. Add Purchase Orders (20 POs)
    print("\n📝 Adding 20 Purchase Orders...")
    
    suppliers = [
        ('Tech Distributors Ltd', '+91 9876543210'),
        ('Mobile World Suppliers', '+91 9876543211'),
        ('Electronics Hub', '+91 9876543212'),
        ('Gadget Wholesale', '+91 9876543213'),
        ('Premium Tech Imports', '+91 9876543214'),
    ]
    
    for po_idx in range(1, 21):
        supplier_name, supplier_contact = random.choice(suppliers)
        po_date = (datetime.now() - timedelta(days=random.randint(1, 60))).strftime('%Y-%m-%d')
        expected_date = (datetime.now() + timedelta(days=random.randint(1, 14))).strftime('%Y-%m-%d')
        status = random.choice(['pending', 'received', 'partial'])
        
        try:
            cursor.execute('''
                INSERT INTO purchase_orders (
                    po_number, supplier_name, supplier_contact, order_date,
                    expected_delivery, status, total_amount, notes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (f'PO-2024-{po_idx:04d}', supplier_name, supplier_contact, po_date,
                  expected_date, status, random.randint(50000, 500000),
                  f'Bulk order #{po_idx}'))
            
            po_id = cursor.lastrowid
            
            # Add 3-7 items per PO
            num_items = random.randint(3, 7)
            for _ in range(num_items):
                if product_ids_list:
                    product_id = random.choice(product_ids_list)
                    cursor.execute('SELECT name FROM products WHERE id = ?', (product_id,))
                    product_name = cursor.fetchone()[0]
                    
                    cursor.execute('''
                        INSERT INTO purchase_order_items (
                            po_id, product_id, product_name, quantity, cost_price
                        ) VALUES (?, ?, ?, ?, ?)
                    ''', (po_id, product_id, product_name, random.randint(5, 50), 
                          random.randint(10000, 100000)))
        except Exception:
            pass
    
    print("  ✅ Purchase orders added")
    
    conn.commit()
    
    # Print summary
    print("\n" + "="*70)
    print("✅ LARGE DATASET POPULATION COMPLETE!")
    print("="*70)
    
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
    print(f"💰 Total Inventory Value: ₹{total_value:,.2f}")
    
    print("="*70)
    print("\n🎉 Database now has 1000+ records!")
    print("="*70 + "\n")
    
    conn.close()

if __name__ == '__main__':
    populate_large_dataset()
