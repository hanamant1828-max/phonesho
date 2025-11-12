# Mobile Shop Inventory Management System

## Overview
A comprehensive web-based inventory management system designed specifically for mobile phone shops. Built with Flask (Python) backend, HTML/CSS/JavaScript frontend, and SQLite database.

## Project Architecture

### Backend (Python Flask)
- **app.py**: Main Flask application with REST API endpoints
- **Database**: SQLite (inventory.db)
- **Dependencies**: Flask, Pandas, OpenPyXL, XlRD

### Frontend
- **HTML/CSS/JavaScript**: Vanilla JavaScript with Bootstrap 5
- **UI Libraries**: 
  - Bootstrap 5 for responsive design
  - DataTables.js for advanced table features
  - Chart.js for visualizations
  - Bootstrap Icons

### Database Schema
1. **categories** - Product categories
2. **brands** - Mobile phone brands
3. **models** - Phone models linked to brands
4. **products** - Main inventory with full product details
5. **purchase_orders** - Purchase order headers
6. **purchase_order_items** - PO line items
7. **stock_movements** - Stock transaction history
8. **quick_orders** - Quick order headers for simplified order entry
9. **quick_order_items** - Quick order line items
10. **grns** - Goods Receipt Notes
11. **grn_items** - GRN line items
12. **damaged_items** - Damaged product records
13. **product_imei** - Individual IMEI tracking for serialized products
14. **pos_sales** - Point of sale transactions
15. **pos_sale_items** - POS sale line items
16. **pos_payments** - Payment records for POS sales

## Features Implemented

### Phase 1: Master Data Management ✓
- Category CRUD operations
- Brand CRUD operations
- Model CRUD operations (linked to brands)
- Full validation and error handling

### Phase 2: Inventory Table ✓
- Complete product listing with pagination
- Search and filtering capabilities
- Multi-column sorting via DataTables
- Stock status indicators (low/out of stock)

### Phase 3: Product Management ✓
- 5-tab product form:
  - Basic Info (SKU, name, category, brand, model)
  - Pricing (cost, selling price, MRP, profit margin)
  - Stock (opening stock, min level, location, IMEI)
  - Specifications (color, storage, RAM, warranty)
  - Supplier (name, contact)
- Add/Edit/Delete products
- Opening stock tracking

### Phase 4: Purchase Orders ✓
- Create purchase orders with multiple items
- PO receiving workflow
- Automatic stock updates on receipt
- Auto-create products from PO if not exists
- PO status tracking (pending/partial/completed)

### Phase 5: Advanced Filtering ✓
- Filter by category, brand, model
- Price range filtering
- Stock status filters (low/out of stock)
- Active/inactive status filter
- Real-time search

### Phase 6: Bulk Operations ✓
- Bulk select functionality
- Bulk delete products
- Bulk update (category, status, pricing)
- Select all/deselect all

### Phase 7: Import/Export ✓
- Export inventory to Excel
- Import products from CSV/Excel
- Error handling for import failures

### Phase 8: Dashboard & Reports ✓
- Key metrics (total products, low stock, out of stock, stock value)
- Low stock alerts table
- Recent stock movements
- Visual status indicators

### Phase 9: Quick Order Entry ✓
- Simple product selection interface
- Quantity input with stock validation
- Real-time product information display
- Automatic stock reduction on order submission
- Stock movement tracking for each order
- Server-side validation for data integrity
- Transaction safety with rollback on errors

### Phase 10: Stock Adjustment ✓
- Add stock to existing products
- Display current stock before adjustment
- Real-time preview of new stock level
- Positive integer quantity validation
- Optional notes for adjustment tracking
- Automatic stock movement recording
- Transaction safety with NULL handling

### Phase 11: IMEI Tracking System ✓
- Individual IMEI number tracking for serialized products
- IMEI capture during stock receiving (GRN process)
- **Smart IMEI handling during POS sales** (dual-path system):
  - **Path 1**: Select from existing inventory IMEIs
  - **Path 2**: Manually enter new IMEIs (auto-creates records marked as sold)
  - IMEI verification API to distinguish existing vs new IMEIs
  - Mutually exclusive handling prevents mixed payloads
- Track which specific IMEI was sold to which customer
- IMEI availability status (available/sold)
- Return handling - restore IMEI availability on returns
- Race condition protection - prevent double-selling of same IMEI
- Atomic updates with rowcount validation
- 15-digit format validation (client and server-side)
- Global uniqueness enforcement via database constraint
- Full audit trail (received date, sold date, sale reference)
- Search products by IMEI number
- View IMEI history and sales information
- See comprehensive documentation in IMEI_TRACKING_GUIDE.md

### Phase 12: Customer Management Integration ✓
- **Bidirectional customer sync** between POS and Customer Management
- **Customer auto-save from POS**: Automatically creates/updates customer records when sales are made
- **Customer auto-lookup in POS**: Enter phone number to auto-fill customer details
- **Phone as unique identifier**: UNIQUE constraint on phone field prevents duplicates
- **Race condition protection**: AJAX request cancellation and response validation
- **Stale data prevention**: Fields cleared when customer not found or phone changed
- **Migration script**: `migrate_customer_phone_unique.py` handles existing duplicates gracefully
- Full CRUD operations in Customer Management view
- Customer data syncs seamlessly between POS transactions and customer database

## Technical Details

### API Endpoints
- `/api/categories` - Category management
- `/api/brands` - Brand management
- `/api/models` - Model management
- `/api/products` - Product CRUD and filtering
- `/api/products/bulk-delete` - Bulk delete
- `/api/products/bulk-update` - Bulk update
- `/api/products/<id>/imeis` - IMEI management (GET list, POST add)
- `/api/products/<id>/imeis/verify` - Verify if IMEI exists (POST) - returns status
- `/api/products/<id>/imei-tracking` - Get IMEI tracking details
- `/api/products/search-by-imei` - Search products by IMEI
- `/api/imeis/<id>` - Delete IMEI (DELETE)
- `/api/purchase-orders` - PO management
- `/api/purchase-orders/<id>/receive` - Receive PO (with IMEI capture)
- `/api/quick-orders` - Quick order management (GET list, POST create)
- `/api/quick-orders/<id>` - Quick order details
- `/api/stock-adjustment` - Add stock to existing products
- `/api/grns` - GRN management
- `/api/grns/<id>` - GRN details
- `/api/pos/sales` - POS sales (with IMEI tracking)
- `/api/customers` - Customer CRUD operations
- `/api/customers/lookup/<phone>` - Customer lookup by phone number
- `/api/dashboard/stats` - Dashboard statistics
- `/api/export/products` - Export to Excel
- `/api/import/products` - Import from file

### Security
- Same-origin policy enforced (no CORS)
- Session-based authentication with secure cookies
- Password hashing (SHA256)
- All API endpoints protected with authentication
- Session secret from environment variable
- Input validation on all forms
- SQL injection prevention via parameterized queries

## Security Features
- **Authentication System**: Session-based login/logout
- **Password Hashing**: SHA256 for credential storage
- **Protected API Endpoints**: All data operations require authentication
- **Session Security**: HttpOnly and SameSite cookie protection
- **File Upload Limits**: 16MB maximum to prevent DoS attacks
- **Default Credentials**: admin / admin123 (MUST be changed for production)

## Development Status
- Phase 1-8: Complete ✓
- Phase 9 (Authentication & Security): Complete ✓
- Phase 10 (Multi-location): Not implemented (single location system)
- Phase 11 (Testing): Complete ✓

## Production Deployment Notes
⚠️ **CRITICAL**: Before deploying to production:
1. Change admin password in app.py (regenerate ADMIN_PASSWORD_HASH)
2. Set SESSION_SECRET environment variable to a secure random string
3. Use a production WSGI server (gunicorn recommended)
4. Enable HTTPS via reverse proxy or Replit deployment
5. Set up regular database backups

## Recent Changes
- **November 12, 2025**: Customer Management Integration
  - Implemented bidirectional sync between POS and Customer Management
  - Added automatic customer creation/update when POS sales are made
  - Created customer lookup API endpoint (`/api/customers/lookup/<phone>`)
  - Added real-time customer auto-fill in POS when phone number is entered
  - Implemented UNIQUE constraint on customer phone numbers with migration script
  - Fixed race condition in AJAX customer lookup with request cancellation
  - Added response validation to prevent stale data population
  - Migration script handles existing duplicate phone numbers gracefully
  - Architect-reviewed with PASS status - robust race condition handling
  - Seamless customer data flow: POS ↔ Customer Database
- **November 12, 2025**: Enhanced Smart IMEI Tracking for POS
  - Implemented dual-path IMEI handling in POS sales
  - Added IMEI verification endpoint (`/api/products/<id>/imeis/verify`)
  - Updated POS to allow both inventory selection and manual entry
  - Manual IMEIs are auto-created with status='sold' in single transaction
  - Added IMEI selection modal in pos.html for choosing from available inventory
  - 15-digit format validation enforced (client and server-side)
  - Global uniqueness check prevents duplicate IMEIs across products
  - Architect-reviewed with PASS status - meets all functional requirements
  - Products with/without IMEI tracking now fully supported
- **November 11, 2025**: Added IMEI Tracking System
  - Created product_imei table for individual IMEI tracking
  - Implemented API endpoints for IMEI management
  - Updated purchase order receiving to capture IMEI numbers
  - Enhanced POS sales to track sold IMEIs with atomic updates
  - Added race condition protection to prevent double-selling
  - Implemented return handling to restore IMEI availability
  - Created comprehensive documentation (IMEI_TRACKING_GUIDE.md)
  - Architect-reviewed and approved implementation
  - Full traceability: track which IMEI was sold to which customer
- **November 10, 2025**: Added Stock Adjustment feature
  - Created POST /api/stock-adjustment endpoint for adding stock
  - Built UI showing current stock before adjustment
  - Added real-time preview of new stock level after addition
  - Implemented positive integer validation and NULL handling
  - Stock movements automatically tracked with manual reference type
  - Transaction safety with commit/rollback handling
  - Architect-reviewed and approved with PASS status
- **November 10, 2025**: Added Quick Order feature
  - Created dedicated quick_orders and quick_order_items database tables
  - Implemented /api/quick-orders endpoints with full CRUD operations
  - Built simplified UI for product selection and quantity entry
  - Added server-side validation for positive integer quantities
  - Implemented automatic stock reduction with transaction safety
  - Added stock movement tracking for all quick orders
  - Architect-reviewed and security-tested implementation
- Initial project setup with complete feature set (Phases 1-8)
- Added session-based authentication system
- Implemented login/logout with secure password hashing
- Protected all API endpoints with @login_required decorator
- Configured secure session cookies (HttpOnly, SameSite)
- Removed CORS to prevent cross-origin credential attacks
- Added comprehensive documentation (README.md)
- Created sample test data for demonstration
