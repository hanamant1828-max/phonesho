#!/usr/bin/env python3
"""
Migration script to add UNIQUE constraint to customers.phone field
Handles existing duplicate phone numbers by keeping the most recent record
"""
import sqlite3
import sys
from datetime import datetime

DATABASE = 'inventory.db'

def migrate():
    print("Starting migration: Add UNIQUE constraint to customers.phone")
    print("=" * 60)
    
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    try:
        # Step 1: Find duplicate phone numbers
        print("\n[1/5] Checking for duplicate phone numbers...")
        cursor.execute('''
            SELECT phone, COUNT(*) as count 
            FROM customers 
            WHERE phone IS NOT NULL AND phone != ''
            GROUP BY phone 
            HAVING COUNT(*) > 1
        ''')
        duplicates = cursor.fetchall()
        
        if duplicates:
            print(f"Found {len(duplicates)} duplicate phone number(s)")
            
            # Step 2: Handle duplicates - keep most recent, mark others inactive
            print("\n[2/5] Resolving duplicates (keeping most recent record)...")
            for dup in duplicates:
                phone = dup['phone']
                print(f"  - Processing phone: {phone} ({dup['count']} records)")
                
                # Get all records with this phone, ordered by most recent first
                cursor.execute('''
                    SELECT id, name, created_at 
                    FROM customers 
                    WHERE phone = ? 
                    ORDER BY created_at DESC
                ''', (phone,))
                records = cursor.fetchall()
                
                # Keep the first (most recent), update others
                kept_id = records[0]['id']
                print(f"    Keeping record ID {kept_id} ({records[0]['name']})")
                
                for record in records[1:]:
                    # Clear phone and mark as inactive for older duplicates
                    cursor.execute('''
                        UPDATE customers 
                        SET phone = NULL, 
                            status = 'inactive',
                            notes = CASE 
                                WHEN notes IS NULL OR notes = '' 
                                THEN 'Phone cleared due to duplicate - ' || ?
                                ELSE notes || '; Phone cleared due to duplicate - ' || ?
                            END
                        WHERE id = ?
                    ''', (datetime.now().isoformat(), datetime.now().isoformat(), record['id']))
                    print(f"    Updated record ID {record['id']} ({record['name']}) - phone cleared, marked inactive")
            
            conn.commit()
            print(f"\nResolved {len(duplicates)} duplicate phone number(s)")
        else:
            print("No duplicate phone numbers found")
        
        # Step 3: Create new table with UNIQUE constraint
        print("\n[3/5] Creating new customers table with UNIQUE phone constraint...")
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS customers_new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                phone TEXT UNIQUE,
                email TEXT,
                address TEXT,
                city TEXT,
                state TEXT,
                pincode TEXT,
                gstin TEXT,
                notes TEXT,
                status TEXT DEFAULT 'active',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Step 4: Copy data to new table
        print("\n[4/5] Copying data to new table...")
        cursor.execute('''
            INSERT INTO customers_new 
            SELECT * FROM customers
        ''')
        
        # Step 5: Replace old table with new one
        print("\n[5/5] Replacing old table with new one...")
        cursor.execute('DROP TABLE customers')
        cursor.execute('ALTER TABLE customers_new RENAME TO customers')
        
        conn.commit()
        print("\n" + "=" * 60)
        print("✓ Migration completed successfully!")
        print("  - UNIQUE constraint added to customers.phone field")
        print("  - All duplicate phone numbers resolved")
        print("=" * 60)
        
    except Exception as e:
        conn.rollback()
        print(f"\n✗ Migration failed: {str(e)}")
        print("  Database has been rolled back to previous state")
        sys.exit(1)
    finally:
        conn.close()

if __name__ == '__main__':
    print("\n" + "=" * 60)
    print("CUSTOMER PHONE UNIQUENESS MIGRATION")
    print("=" * 60)
    print("\nThis migration will:")
    print("  1. Find duplicate phone numbers in customers table")
    print("  2. Keep the most recent record for each duplicate")
    print("  3. Clear phone and mark other duplicates as inactive")
    print("  4. Add UNIQUE constraint to phone field")
    print("\nWARNING: This will modify your database!")
    print("=" * 60)
    
    response = input("\nContinue with migration? (yes/no): ")
    if response.lower() in ['yes', 'y']:
        migrate()
    else:
        print("\nMigration cancelled")
        sys.exit(0)
