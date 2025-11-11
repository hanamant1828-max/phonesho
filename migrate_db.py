import sqlite3

DATABASE = 'inventory.db'

def migrate_database():
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    # Check if image_data column exists in models table
    cursor.execute("PRAGMA table_info(models)")
    columns = [column[1] for column in cursor.fetchall()]

    if 'image_data' not in columns:
        try:
            cursor.execute('ALTER TABLE models ADD COLUMN image_data TEXT')
            conn.commit()
            print("image_data column added successfully.")
        except sqlite3.OperationalError as e:
            print(f"Migration error: {e}")
    else:
        print("image_data column already exists.")

    # Create product_imei table if it doesn't exist
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS product_imei (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER NOT NULL,
            imei TEXT NOT NULL UNIQUE,
            stock_movement_id INTEGER,
            status TEXT DEFAULT 'in_stock',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (product_id) REFERENCES products (id),
            FOREIGN KEY (stock_movement_id) REFERENCES stock_movements (id)
        )
    ''')
    conn.commit()
    print("product_imei table ready.")
    
    # Check if sold_date column exists in product_imei table
    cursor.execute("PRAGMA table_info(product_imei)")
    columns = [column[1] for column in cursor.fetchall()]
    
    if 'sold_date' not in columns:
        try:
            cursor.execute('ALTER TABLE product_imei ADD COLUMN sold_date TIMESTAMP')
            conn.commit()
            print("sold_date column added successfully to product_imei table.")
        except sqlite3.OperationalError as e:
            print(f"Migration error for sold_date: {e}")
    else:
        print("sold_date column already exists in product_imei table.")

    conn.close()

if __name__ == '__main__':
    migrate_database()