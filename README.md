# Mobile Shop Inventory Management System

A comprehensive web-based inventory management system designed for mobile phone shops, built with Flask (Python) backend and vanilla JavaScript frontend.

## Features

### Core Functionality
- **Dashboard** with real-time metrics (total products, low stock alerts, stock value)
- **Master Data Management** (Categories, Brands, Models) with full CRUD operations
- **Inventory Management** with advanced filtering, search, and pagination
- **Product Management** with 5-tab detailed form (Basic Info, Pricing, Stock, Specifications, Supplier)
- **Purchase Order System** with receiving workflow and automatic stock updates
- **Bulk Operations** (delete, price updates, category assignment)
- **Import/Export** functionality (CSV/Excel)
- **Stock Movement Tracking** with complete audit trail

### Security Features
- Session-based authentication
- Password hashing (SHA256)
- Protected API endpoints
- HttpOnly and SameSite cookie protection
- File upload size limits (16MB)

## Quick Start

### Prerequisites
- Python 3.11+
- pip (Python package manager)

### Installation

1. Install dependencies:
```bash
pip install flask pandas openpyxl xlrd
```

2. Run the application:
```bash
python app.py
```

3. Access the application:
```
http://localhost:5000
```

4. Login with default credentials:
```
Username: admin
Password: admin123
```

## Production Deployment

### CRITICAL: Before deploying to production

1. **Change the admin password**:
   - Edit `app.py` and update `ADMIN_PASSWORD_HASH`
   - Generate new hash: `python3 -c "import hashlib; print(hashlib.sha256(b'YOUR_NEW_PASSWORD').hexdigest())"`

2. **Set a secure session secret**:
   - Set environment variable: `export SESSION_SECRET='your-very-long-random-secret-key-here'`
   - Or use Replit Secrets to store SESSION_SECRET

3. **Use a production WSGI server**:
   ```bash
   pip install gunicorn
   export FLASK_ENV=production
   gunicorn --bind 0.0.0.0:5000 --workers 4 app:app
   ```
   Note: Setting FLASK_ENV=production enables secure cookie flag for HTTPS

4. **Enable HTTPS**:
   - Deploy behind a reverse proxy (nginx, Caddy)
   - Or use Replit's built-in HTTPS

5. **Database backups**:
   - Regularly backup `inventory.db`
   - Consider upgrading to PostgreSQL for production

## Database Schema

- **categories** - Product categories
- **brands** - Mobile phone brands
- **models** - Phone models (linked to brands)
- **products** - Complete product inventory
- **purchase_orders** - PO headers
- **purchase_order_items** - PO line items
- **stock_movements** - Stock transaction history

## API Endpoints

All endpoints require authentication except:
- `POST /api/login` - User login
- `POST /api/logout` - User logout
- `GET /api/check-auth` - Check authentication status

### Protected Endpoints
- `/api/categories` - Category management
- `/api/brands` - Brand management
- `/api/models` - Model management
- `/api/products` - Product CRUD and filtering
- `/api/products/bulk-delete` - Bulk delete products
- `/api/products/bulk-update` - Bulk update products
- `/api/purchase-orders` - Purchase order management
- `/api/purchase-orders/<id>/receive` - Receive PO items
- `/api/dashboard/stats` - Dashboard statistics
- `/api/export/products` - Export to Excel
- `/api/import/products` - Import from CSV/Excel

## Technology Stack

### Backend
- **Flask** - Web framework
- **SQLite** - Database
- **Pandas** - Data import/export
- **OpenPyXL** - Excel file handling

### Frontend
- **HTML5/CSS3** - Structure and styling
- **JavaScript (Vanilla)** - Client-side logic
- **Bootstrap 5** - Responsive UI framework
- **DataTables.js** - Advanced table features
- **jQuery** - DOM manipulation

## Features by Phase

✅ **Phase 1**: Master Data CRUD (Categories, Brands, Models)  
✅ **Phase 2**: Basic Inventory Table with search and pagination  
✅ **Phase 3**: Product Add/Edit Form with 5 tabs  
✅ **Phase 4**: Purchase Order system with stock updates  
✅ **Phase 5**: Advanced filtering and search  
✅ **Phase 6**: Bulk operations  
✅ **Phase 7**: Import/Export functionality  
✅ **Phase 8**: Dashboard with metrics and alerts  
✅ **Phase 9**: Authentication and security  
❌ **Phase 10**: Multi-location support (not implemented - single location system)

## Sample Data

Sample data is included with:
- 5 Categories
- 10 Brands (Apple, Samsung, Xiaomi, etc.)
- 11 Models
- 3 Products with stock

## License

This project is provided as-is for use in mobile shop inventory management.

## Support

For issues or questions, please refer to the project documentation or contact your system administrator.

---

**Note**: This is a single-user system designed for small mobile shops. For multi-user or enterprise deployments, additional features like role-based access control, multi-location support, and advanced reporting should be implemented.
