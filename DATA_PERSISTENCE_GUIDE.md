# Data Persistence Guide

## Overview
Your inventory management system uses SQLite database (`inventory.db`) to store all data. Here's how data persistence works in your Replit project.

## 📊 Sample Data Added
I've added sample data to your database including:
- **5 Categories**: Smartphones, Tablets, Laptops, Accessories, Smartwatches
- **8 Brands**: Apple, Samsung, Google, OnePlus, Xiaomi, Realme, Oppo, Vivo
- **10 Models**: Various phone models (iPhone 15 Pro, Galaxy S24, Pixel 8, etc.)
- **9 Products**: Complete product inventory with pricing and stock
- **1 Purchase Order**: Sample pending order
- **1 Sale Transaction**: Completed sale example

## 🔐 Login Credentials
- **Username**: `admin`
- **Password**: `admin123`

## 💾 How Data is Stored

### Current Setup
- **Database Type**: SQLite (file-based database)
- **Database File**: `inventory.db` in the root directory
- **Automatic Saving**: All data is saved automatically when you add/edit/delete records

### Data Persistence in Replit
1. **Development Environment**: Your `inventory.db` file is stored in your Replit workspace and persists across sessions
2. **Automatic Backups**: Replit automatically backs up your workspace files
3. **Version Control**: The database file is tracked in your git repository

## 🚀 Deploying Your Application

When you publish/deploy your app, here's what happens with data:

### Option 1: SQLite (Current Setup)
- ✅ **Pros**: Simple, no configuration needed
- ⚠️ **Cons**: 
  - Development and production databases are separate
  - Data added in development won't automatically appear in production
  - Not ideal for high-traffic applications

### Option 2: PostgreSQL (Recommended for Production)
For a production application, I recommend migrating to PostgreSQL:

1. **Create PostgreSQL Database**:
   - Use Replit's built-in PostgreSQL database
   - Development and production databases are managed separately
   - Better for scaling and concurrent users

2. **Data Migration**:
   - Export data from SQLite
   - Import into PostgreSQL
   - Update database connection in `app.py`

## 🔄 Adding Data to Your System

### Through the Web Interface
1. Log in with admin credentials
2. Navigate to the relevant section (Products, Categories, Brands, etc.)
3. Click "Add New" and fill in the form
4. Data is automatically saved to `inventory.db`

### Through the Seed Script
Run `python seed_data.py` to add sample data (only run once to avoid duplicates)

## 📤 Backing Up Your Data

### Manual Backup
```bash
# Download a copy of your database
cp inventory.db inventory_backup_$(date +%Y%m%d).db
```

### Export to Excel/CSV
Use the built-in export features in the application to export:
- Products
- Sales reports
- Inventory reports

## 🔧 Resetting the Database

If you need to start fresh:
```bash
# Delete the database (this will remove ALL data)
rm inventory.db

# Restart the application to create fresh tables
# Then run the seed script to add sample data again
python seed_data.py
```

## 📝 Important Notes

1. **Development vs Production**: 
   - Changes in development don't automatically sync to production
   - You need to deploy your app to make changes live

2. **Database File**:
   - The `inventory.db` file contains ALL your data
   - Keep backups before making major changes
   - Don't delete this file unless you want to lose all data

3. **Git Tracking**:
   - The database file is tracked in git
   - Each commit includes the current state of your database
   - You can rollback to previous versions if needed

4. **Scaling Considerations**:
   - SQLite works well for small to medium applications
   - For high-traffic production apps, consider PostgreSQL
   - PostgreSQL offers better concurrency and reliability

## 🎯 Next Steps

1. **Test the Application**: Log in and explore the sample data
2. **Add Your Own Data**: Start adding real products and categories
3. **Consider Migration**: If planning for production, plan PostgreSQL migration
4. **Regular Backups**: Set up a backup routine for important data

## 💡 Need Help?

- Run `python seed_data.py` to repopulate sample data
- Check `IMEI_TRACKING_GUIDE.md` for IMEI tracking features
- Review the application logs if you encounter issues
