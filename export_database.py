
import sqlite3
import json
from datetime import datetime

def export_database():
    """Export database schema and data to SQL file"""
    conn = sqlite3.connect('inventory.db')
    
    # Create backup filename with timestamp
    backup_file = f"database_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.sql"
    
    with open(backup_file, 'w') as f:
        for line in conn.iterdump():
            f.write('%s\n' % line)
    
    conn.close()
    print(f"✅ Database exported to {backup_file}")
    print(f"📊 This file contains all schema and data")
    print(f"💡 To restore: sqlite3 inventory.db < {backup_file}")

if __name__ == '__main__':
    export_database()
