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

## Technical Details

### API Endpoints
- `/api/categories` - Category management
- `/api/brands` - Brand management
- `/api/models` - Model management
- `/api/products` - Product CRUD and filtering
- `/api/products/bulk-delete` - Bulk delete
- `/api/products/bulk-update` - Bulk update
- `/api/purchase-orders` - PO management
- `/api/purchase-orders/<id>/receive` - Receive PO
- `/api/quick-orders` - Quick order management (GET list, POST create)
- `/api/quick-orders/<id>` - Quick order details
- `/api/grns` - GRN management
- `/api/grns/<id>` - GRN details
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
