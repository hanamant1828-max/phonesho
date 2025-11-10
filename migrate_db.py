
import sqlite3

DATABASE = 'inventory.db'

def migrate_database():
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    # Check if image_data column exists
    cursor.execute("PRAGMA table_info(models)")
    columns = [column[1] for column in cursor.fetchall()]
    
    if 'image_data' not in columns:
        print("Adding image_data column to models table...")
        try:
            cursor.execute('ALTER TABLE models ADD COLUMN image_data TEXT')
            conn.commit()
            print("Successfully added image_data column!")
        except sqlite3.OperationalError as e:
            print(f"Error: {e}")
    else:
        print("image_data column already exists.")
    
    conn.close()

if __name__ == '__main__':
    migrate_database()
