const API_BASE = '/api';
let currentPage = 'dashboard';
let inventoryTable = null;
let poItemCounter = 0;
let isAuthenticated = false;

$(document).ready(function() {
    checkAuth();

    $('#productCostPrice, #productSellingPrice').on('input', calculateProfitMargin);
    $('#productBrand').on('change', loadModelsForBrand);

    $('#saveCategoryBtn').on('click', saveCategory);
    $('#saveBrandBtn').on('click', saveBrand);
    $('#saveModelBtn').on('click', saveModel);
    $('#saveProductBtn').on('click', saveProduct);
    $('#savePOBtn').on('click', savePurchaseOrder);
    $('#confirmReceivePOBtn').on('click', confirmReceivePO);
    $('#addPOItemBtn').on('click', addPOItem);
    $('#loginBtn').on('click', performLogin);
    $('#logoutBtn').on('click', performLogout);

    $('#loginPassword').on('keypress', function(e) {
        if (e.which === 13) {
            performLogin();
        }
    });
});

function checkAuth() {
    $.get(`${API_BASE}/check-auth`, function(data) {
        if (data.logged_in) {
            isAuthenticated = true;
            $('#username-display').text(data.username);
            $('#loginModal').modal('hide');
            $('#navbar-menu').show();
            $('#logoutBtn').show();
            initNavigation();
            loadPage('dashboard');
        } else {
            showLoginModal();
        }
    }).fail(function() {
        showLoginModal();
    });
}

function showLoginModal() {
    isAuthenticated = false;
    $('#navbar-menu').hide();
    $('#logoutBtn').hide();
    $('#content-area').html('<div class="empty-state"><i class="bi bi-lock"></i><p>Please login to continue</p></div>');
    const modal = new bootstrap.Modal($('#loginModal'), { backdrop: 'static', keyboard: false });
    modal.show();
}

function performLogin() {
    const username = $('#loginUsername').val();
    const password = $('#loginPassword').val();

    if (!username || !password) {
        $('#loginError').text('Please enter username and password').show();
        return;
    }

    $.ajax({
        url: `${API_BASE}/login`,
        method: 'POST',
        contentType: 'application/json',
        data: JSON.stringify({ username, password }),
        success: function(data) {
            if (data.success) {
                isAuthenticated = true;
                $('#username-display').text(data.username);
                $('#loginModal').modal('hide');
                $('#navbar-menu').show();
                $('#logoutBtn').show();
                $('#loginForm')[0].reset();
                $('#loginError').hide();
                initNavigation();
                loadPage('dashboard');
            }
        },
        error: function(xhr) {
            $('#loginError').text(xhr.responseJSON?.error || 'Login failed').show();
        }
    });
}

function performLogout() {
    if (!confirm('Are you sure you want to logout?')) return;

    $.ajax({
        url: `${API_BASE}/logout`,
        method: 'POST',
        success: function() {
            isAuthenticated = false;
            showLoginModal();
        }
    });
}

function initNavigation() {
    $('a[data-page]').on('click', function(e) {
        e.preventDefault();
        const page = $(this).data('page');
        loadPage(page);

        $('a[data-page]').removeClass('active');
        $(this).addClass('active');
    });
}

function loadPage(page) {
    currentPage = page;
    const contentArea = $('#content-area');

    switch(page) {
        case 'dashboard':
            loadDashboard();
            break;
        case 'inventory':
            loadInventory();
            break;
        case 'categories':
            loadCategories();
            break;
        case 'brands':
            loadBrands();
            break;
        case 'models':
            loadModels();
            break;
        case 'purchase-orders':
            loadPurchaseOrders();
            break;
        case 'grns':
            loadGRNs();
            break;
    }
}

function loadDashboard() {
    $('#content-area').html(`
        <div class="page-header">
            <h2><i class="bi bi-speedometer2"></i> Dashboard</h2>
        </div>
        <div class="row" id="statsCards">
            <div class="col-md-3">
                <div class="card stats-card">
                    <div class="stats-icon text-primary"><i class="bi bi-box-seam"></i></div>
                    <div class="stats-value" id="totalProducts">0</div>
                    <div class="stats-label">Total Products</div>
                </div>
            </div>
            <div class="col-md-3">
                <div class="card stats-card">
                    <div class="stats-icon text-warning"><i class="bi bi-exclamation-triangle"></i></div>
                    <div class="stats-value" id="lowStock">0</div>
                    <div class="stats-label">Low Stock</div>
                </div>
            </div>
            <div class="col-md-3">
                <div class="card stats-card">
                    <div class="stats-icon text-danger"><i class="bi bi-x-circle"></i></div>
                    <div class="stats-value" id="outOfStock">0</div>
                    <div class="stats-label">Out of Stock</div>
                </div>
            </div>
            <div class="col-md-3">
                <div class="card stats-card">
                    <div class="stats-icon text-success"><i class="bi bi-currency-dollar"></i></div>
                    <div class="stats-value" id="stockValue">$0</div>
                    <div class="stats-label">Stock Value</div>
                </div>
            </div>
        </div>

        <div class="row">
            <div class="col-md-6">
                <div class="card">
                    <div class="card-header">
                        <i class="bi bi-exclamation-triangle text-warning"></i> Low Stock Alerts
                    </div>
                    <div class="card-body">
                        <div class="table-responsive">
                            <table class="table table-sm" id="lowStockTable">
                                <thead>
                                    <tr>
                                        <th>Product</th>
                                        <th>Brand</th>
                                        <th>Current Stock</th>
                                        <th>Min Level</th>
                                    </tr>
                                </thead>
                                <tbody></tbody>
                            </table>
                        </div>
                    </div>
                </div>
            </div>
            <div class="col-md-6">
                <div class="card">
                    <div class="card-header">
                        <i class="bi bi-clock-history"></i> Recent Stock Movements
                    </div>
                    <div class="card-body">
                        <div class="table-responsive">
                            <table class="table table-sm" id="recentMovementsTable">
                                <thead>
                                    <tr>
                                        <th>Product</th>
                                        <th>Type</th>
                                        <th>Quantity</th>
                                        <th>Date</th>
                                    </tr>
                                </thead>
                                <tbody></tbody>
                            </table>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    `);

    $.get(`${API_BASE}/dashboard/stats`, function(data) {
        $('#totalProducts').text(data.total_products);
        $('#lowStock').text(data.low_stock);
        $('#outOfStock').text(data.out_of_stock);
        $('#stockValue').text('$' + data.stock_value.toFixed(2));

        const lowStockBody = $('#lowStockTable tbody');
        lowStockBody.empty();
        if (data.low_stock_items.length === 0) {
            lowStockBody.append('<tr><td colspan="4" class="text-center text-muted">No low stock items</td></tr>');
        } else {
            data.low_stock_items.forEach(item => {
                lowStockBody.append(`
                    <tr>
                        <td>${item.name}</td>
                        <td>${item.brand_name || '-'}</td>
                        <td class="stock-low">${item.current_stock}</td>
                        <td>${item.min_stock_level}</td>
                    </tr>
                `);
            });
        }

        const movementsBody = $('#recentMovementsTable tbody');
        movementsBody.empty();
        if (data.recent_movements.length === 0) {
            movementsBody.append('<tr><td colspan="4" class="text-center text-muted">No recent movements</td></tr>');
        } else {
            data.recent_movements.slice(0, 10).forEach(movement => {
                const date = new Date(movement.created_at);
                movementsBody.append(`
                    <tr>
                        <td>${movement.product_name || 'N/A'}</td>
                        <td><span class="badge bg-${movement.type === 'purchase' ? 'success' : 'info'}">${movement.type}</span></td>
                        <td>${movement.quantity}</td>
                        <td>${date.toLocaleDateString()}</td>
                    </tr>
                `);
            });
        }
    });
}

function loadInventory() {
    $('#content-area').html(`
        <div class="page-header d-flex justify-content-between align-items-center">
            <h2><i class="bi bi-box-seam"></i> Inventory Management</h2>
            <div class="btn-action-group">
                <button class="btn btn-success" onclick="showAddProduct()"><i class="bi bi-plus-circle"></i> Add Product</button>
                <button class="btn btn-primary" onclick="exportProducts()"><i class="bi bi-download"></i> Export</button>
                <button class="btn btn-secondary" onclick="showImportModal()"><i class="bi bi-upload"></i> Import</button>
            </div>
        </div>

        <div class="filter-section">
            <div class="row">
                <div class="col-md-3">
                    <label class="form-label">Search</label>
                    <input type="text" class="form-control" id="searchProduct" placeholder="Search products...">
                </div>
                <div class="col-md-2">
                    <label class="form-label">Category</label>
                    <select class="form-select" id="filterCategory">
                        <option value="">All Categories</option>
                    </select>
                </div>
                <div class="col-md-2">
                    <label class="form-label">Brand</label>
                    <select class="form-select" id="filterBrand">
                        <option value="">All Brands</option>
                    </select>
                </div>
                <div class="col-md-2">
                    <label class="form-label">Stock Status</label>
                    <select class="form-select" id="filterStockStatus">
                        <option value="">All</option>
                        <option value="low">Low Stock</option>
                        <option value="out">Out of Stock</option>
                    </select>
                </div>
                <div class="col-md-2">
                    <label class="form-label">Status</label>
                    <select class="form-select" id="filterStatus">
                        <option value="">All</option>
                        <option value="active">Active</option>
                        <option value="inactive">Inactive</option>
                    </select>
                </div>
                <div class="col-md-1 d-flex align-items-end">
                    <button class="btn btn-primary w-100" onclick="applyFilters()">Filter</button>
                </div>
            </div>
        </div>

        <div class="bulk-actions" id="bulkActions">
            <strong>Selected: <span id="selectedCount">0</span> items</strong>
            <div class="mt-2">
                <button class="btn btn-sm btn-danger" onclick="bulkDelete()"><i class="bi bi-trash"></i> Delete</button>
                <button class="btn btn-sm btn-warning" onclick="showBulkUpdate()"><i class="bi bi-pencil"></i> Bulk Update</button>
            </div>
        </div>

        <div class="card">
            <div class="card-body">
                <table class="table table-hover" id="inventoryTable">
                    <thead>
                        <tr>
                            <th><input type="checkbox" id="selectAll"></th>
                            <th>SKU</th>
                            <th>Product Name</th>
                            <th>Category</th>
                            <th>Brand</th>
                            <th>Model</th>
                            <th>Cost Price</th>
                            <th>Selling Price</th>
                            <th>Current Stock</th>
                            <th>Status</th>
                            <th>Actions</th>
                        </tr>
                    </thead>
                    <tbody></tbody>
                </table>
            </div>
        </div>
    `);

    loadFilterDropdowns();
    loadInventoryData();

    $('#selectAll').on('change', function() {
        $('input[name="productCheck"]').prop('checked', this.checked);
        updateBulkActions();
    });
}

function loadFilterDropdowns() {
    $.get(`${API_BASE}/categories`, function(data) {
        const select = $('#filterCategory, #productCategory');
        data.forEach(cat => {
            select.append(`<option value="${cat.id}">${cat.name}</option>`);
        });
    });

    $.get(`${API_BASE}/brands`, function(data) {
        const select = $('#filterBrand, #productBrand');
        data.forEach(brand => {
            select.append(`<option value="${brand.id}">${brand.name}</option>`);
        });
    });
}

function loadInventoryData() {
    const params = new URLSearchParams();
    const search = $('#searchProduct').val();
    const category = $('#filterCategory').val();
    const brand = $('#filterBrand').val();
    const stockStatus = $('#filterStockStatus').val();
    const status = $('#filterStatus').val();

    if (search) params.append('search', search);
    if (category) params.append('category_id', category);
    if (brand) params.append('brand_id', brand);
    if (stockStatus) params.append('stock_status', stockStatus);
    if (status) params.append('status', status);

    $.get(`${API_BASE}/products?${params.toString()}`, function(data) {
        if (inventoryTable) {
            inventoryTable.destroy();
        }

        const tbody = $('#inventoryTable tbody');
        tbody.empty();

        data.forEach(product => {
            const stockClass = product.current_stock === 0 ? 'stock-out' : 
                             (product.current_stock <= product.min_stock_level ? 'stock-low' : 'stock-ok');

            tbody.append(`
                <tr>
                    <td><input type="checkbox" name="productCheck" value="${product.id}"></td>
                    <td>${product.sku || '-'}</td>
                    <td>${product.name}</td>
                    <td>${product.category_name || '-'}</td>
                    <td>${product.brand_name || '-'}</td>
                    <td>${product.model_name || '-'}</td>
                    <td>$${parseFloat(product.cost_price || 0).toFixed(2)}</td>
                    <td>$${parseFloat(product.selling_price || 0).toFixed(2)}</td>
                    <td class="${stockClass}">${product.current_stock}</td>
                    <td><span class="badge bg-${product.status === 'active' ? 'success' : 'secondary'}">${product.status}</span></td>
                    <td>
                        <button class="btn btn-sm btn-info action-btn" onclick="viewStockHistory(${product.id})" title="Stock History">
                            <i class="bi bi-clock-history"></i>
                        </button>
                        <button class="btn btn-sm btn-primary action-btn" onclick="editProduct(${product.id})">
                            <i class="bi bi-pencil"></i>
                        </button>
                        <button class="btn btn-sm btn-danger action-btn" onclick="deleteProduct(${product.id})">
                            <i class="bi bi-trash"></i>
                        </button>
                    </td>
                </tr>
            `);
        });

        inventoryTable = $('#inventoryTable').DataTable({
            order: [[2, 'asc']],
            pageLength: 25,
            columnDefs: [
                { orderable: false, targets: [0, 10] }
            ]
        });

        $('input[name="productCheck"]').on('change', updateBulkActions);
    });
}

function applyFilters() {
    loadInventoryData();
}

function updateBulkActions() {
    const checked = $('input[name="productCheck"]:checked').length;
    $('#selectedCount').text(checked);
    if (checked > 0) {
        $('#bulkActions').addClass('show');
    } else {
        $('#bulkActions').removeClass('show');
    }
}

function bulkDelete() {
    const ids = $('input[name="productCheck"]:checked').map(function() {
        return parseInt($(this).val());
    }).get();

    if (!confirm(`Delete ${ids.length} products?`)) return;

    $.ajax({
        url: `${API_BASE}/products/bulk-delete`,
        method: 'POST',
        contentType: 'application/json',
        data: JSON.stringify({ ids: ids }),
        success: function() {
            alert('Products deleted successfully');
            loadInventoryData();
        }
    });
}

function showBulkUpdate() {
    const ids = $('input[name="productCheck"]:checked').map(function() {
        return parseInt($(this).val());
    }).get();

    const updateType = prompt('Update type:\n1. Category\n2. Status\n3. Selling Price\n4. Cost Price');

    if (!updateType) return;

    const updates = {};

    switch(updateType) {
        case '1':
            const categoryId = prompt('Enter category ID:');
            if (categoryId) updates.category_id = parseInt(categoryId);
            break;
        case '2':
            const status = prompt('Enter status (active/inactive):');
            if (status) updates.status = status;
            break;
        case '3':
            const sellingPrice = prompt('Enter new selling price:');
            if (sellingPrice) updates.selling_price = parseFloat(sellingPrice);
            break;
        case '4':
            const costPrice = prompt('Enter new cost price:');
            if (costPrice) updates.cost_price = parseFloat(costPrice);
            break;
    }

    if (Object.keys(updates).length === 0) return;

    $.ajax({
        url: `${API_BASE}/products/bulk-update`,
        method: 'POST',
        contentType: 'application/json',
        data: JSON.stringify({ ids: ids, updates: updates }),
        success: function() {
            alert('Products updated successfully');
            loadInventoryData();
        }
    });
}

function showAddProduct() {
    $('#productId').val('');
    $('#productForm')[0].reset();
    $('#productModalLabel').text('Add Product');

    loadFilterDropdowns();

    const modal = new bootstrap.Modal($('#productModal'));
    modal.show();
}

function editProduct(id) {
    $.get(`${API_BASE}/products/${id}`, function(product) {
        $('#productId').val(id);
        $('#productSKU').val(product.sku);
        $('#productName').val(product.name);
        $('#productCategory').val(product.category_id);
        $('#productBrand').val(product.brand_id);
        $('#productDescription').val(product.description);
        $('#productCostPrice').val(product.cost_price);
        $('#productSellingPrice').val(product.selling_price);
        $('#productMRP').val(product.mrp);
        $('#productCurrentStock').val(product.current_stock);
        $('#productMinStock').val(product.min_stock_level);
        $('#productLocation').val(product.storage_location);
        $('#productIMEI').val(product.imei);
        $('#productColor').val(product.color);
        $('#productStorage').val(product.storage_capacity);
        $('#productRAM').val(product.ram);
        $('#productWarranty').val(product.warranty_period);
        $('#productSupplierName').val(product.supplier_name);
        $('#productSupplierContact').val(product.supplier_contact);
        $('#productImage').val(product.image_url);
        $('#productStatus').val(product.status);

        loadModelsForBrand();
        $('#productModel').val(product.model_id);

        $('#productModalLabel').text('Edit Product');

        const modal = new bootstrap.Modal($('#productModal'));
        modal.show();
    });
}

function deleteProduct(id) {
    if (!confirm('Are you sure you want to delete this product?')) return;

    $.ajax({
        url: `${API_BASE}/products/${id}`,
        method: 'DELETE',
        success: function() {
            alert('Product deleted successfully');
            loadInventoryData();
        }
    });
}

function saveProduct() {
    const id = $('#productId').val();
    const data = {
        sku: $('#productSKU').val(),
        name: $('#productName').val(),
        category_id: $('#productCategory').val() || null,
        brand_id: $('#productBrand').val() || null,
        model_id: $('#productModel').val() || null,
        description: $('#productDescription').val(),
        cost_price: parseFloat($('#productCostPrice').val()) || 0,
        selling_price: parseFloat($('#productSellingPrice').val()) || 0,
        mrp: parseFloat($('#productMRP').val()) || 0,
        opening_stock: parseInt($('#productOpeningStock').val()) || 0,
        current_stock: parseInt($('#productCurrentStock').val()) || 0,
        min_stock_level: parseInt($('#productMinStock').val()) || 10,
        storage_location: $('#productLocation').val(),
        imei: $('#productIMEI').val(),
        color: $('#productColor').val(),
        storage_capacity: $('#productStorage').val(),
        ram: $('#productRAM').val(),
        warranty_period: $('#productWarranty').val(),
        supplier_name: $('#productSupplierName').val(),
        supplier_contact: $('#productSupplierContact').val(),
        image_url: $('#productImage').val(),
        status: $('#productStatus').val()
    };

    const url = id ? `${API_BASE}/products/${id}` : `${API_BASE}/products`;
    const method = id ? 'PUT' : 'POST';

    $.ajax({
        url: url,
        method: method,
        contentType: 'application/json',
        data: JSON.stringify(data),
        success: function() {
            alert('Product saved successfully');
            bootstrap.Modal.getInstance($('#productModal')).hide();
            loadInventoryData();
        },
        error: function(xhr) {
            alert('Error: ' + (xhr.responseJSON?.error || 'Failed to save product'));
        }
    });
}

function calculateProfitMargin() {
    const cost = parseFloat($('#productCostPrice').val()) || 0;
    const selling = parseFloat($('#productSellingPrice').val()) || 0;

    if (cost > 0) {
        const margin = ((selling - cost) / cost * 100).toFixed(2);
        $('#profitMargin').text(margin + '%');
    } else {
        $('#profitMargin').text('0%');
    }
}

function loadModelsForBrand() {
    const brandId = $('#productBrand').val();
    const modelSelect = $('#productModel');

    modelSelect.empty().append('<option value="">Select Model</option>');

    if (!brandId) return;

    $.get(`${API_BASE}/models`, function(data) {
        data.filter(m => m.brand_id == brandId).forEach(model => {
            modelSelect.append(`<option value="${model.id}">${model.name}</option>`);
        });
    });
}

function exportProducts() {
    window.location.href = `${API_BASE}/export/products`;
}

function showImportModal() {
    const fileInput = $('<input type="file" accept=".csv,.xlsx,.xls">');
    fileInput.on('change', function() {
        const file = this.files[0];
        if (!file) return;

        const formData = new FormData();
        formData.append('file', file);

        $.ajax({
            url: `${API_BASE}/import/products`,
            method: 'POST',
            data: formData,
            processData: false,
            contentType: false,
            success: function(response) {
                alert(`Imported ${response.imported} products successfully`);
                if (response.errors.length > 0) {
                    console.error('Import errors:', response.errors);
                }
                loadInventoryData();
            },
            error: function(xhr) {
                alert('Import failed: ' + (xhr.responseJSON?.error || 'Unknown error'));
            }
        });
    });
    fileInput.click();
}

function loadCategories() {
    $('#content-area').html(`
        <div class="page-header d-flex justify-content-between align-items-center">
            <h2><i class="bi bi-tag"></i> Categories</h2>
            <button class="btn btn-success" onclick="showAddCategory()"><i class="bi bi-plus-circle"></i> Add Category</button>
        </div>
        <div class="card">
            <div class="card-body">
                <table class="table table-hover" id="categoriesTable">
                    <thead>
                        <tr>
                            <th>Name</th>
                            <th>Description</th>
                            <th>Created</th>
                            <th>Actions</th>
                        </tr>
                    </thead>
                    <tbody></tbody>
                </table>
            </div>
        </div>
    `);

    $.get(`${API_BASE}/categories`, function(data) {
        const tbody = $('#categoriesTable tbody');
        tbody.empty();

        data.forEach(cat => {
            const date = new Date(cat.created_at);
            tbody.append(`
                <tr>
                    <td>${cat.name}</td>
                    <td>${cat.description || '-'}</td>
                    <td>${date.toLocaleDateString()}</td>
                    <td>
                        <button class="btn btn-sm btn-primary action-btn" onclick="editCategory(${cat.id}, '${cat.name}', '${cat.description || ''}')">
                            <i class="bi bi-pencil"></i>
                        </button>
                        <button class="btn btn-sm btn-danger action-btn" onclick="deleteCategory(${cat.id})">
                            <i class="bi bi-trash"></i>
                        </button>
                    </td>
                </tr>
            `);
        });

        $('#categoriesTable').DataTable();
    });
}

function showAddCategory() {
    $('#categoryId').val('');
    $('#categoryForm')[0].reset();
    $('#categoryModalLabel').text('Add Category');
    const modal = new bootstrap.Modal($('#categoryModal'));
    modal.show();
}

function editCategory(id, name, description) {
    $('#categoryId').val(id);
    $('#categoryName').val(name);
    $('#categoryDescription').val(description);
    $('#categoryModalLabel').text('Edit Category');
    const modal = new bootstrap.Modal($('#categoryModal'));
    modal.show();
}

function deleteCategory(id) {
    if (!confirm('Are you sure?')) return;

    $.ajax({
        url: `${API_BASE}/categories/${id}`,
        method: 'DELETE',
        success: function() {
            alert('Category deleted');
            loadCategories();
        },
        error: function(xhr) {
            alert('Error: ' + (xhr.responseJSON?.error || 'Cannot delete'));
        }
    });
}

function saveCategory() {
    const id = $('#categoryId').val();
    const data = {
        name: $('#categoryName').val(),
        description: $('#categoryDescription').val()
    };

    const url = id ? `${API_BASE}/categories/${id}` : `${API_BASE}/categories`;
    const method = id ? 'PUT' : 'POST';

    $.ajax({
        url: url,
        method: method,
        contentType: 'application/json',
        data: JSON.stringify(data),
        success: function() {
            alert('Category saved');
            bootstrap.Modal.getInstance($('#categoryModal')).hide();
            loadCategories();
        },
        error: function(xhr) {
            alert('Error: ' + (xhr.responseJSON?.error || 'Failed to save'));
        }
    });
}

function loadBrands() {
    $('#content-area').html(`
        <div class="page-header d-flex justify-content-between align-items-center">
            <h2><i class="bi bi-award"></i> Brands</h2>
            <button class="btn btn-success" onclick="showAddBrand()"><i class="bi bi-plus-circle"></i> Add Brand</button>
        </div>
        <div class="card">
            <div class="card-body">
                <table class="table table-hover" id="brandsTable">
                    <thead>
                        <tr>
                            <th>Name</th>
                            <th>Description</th>
                            <th>Created</th>
                            <th>Actions</th>
                        </tr>
                    </thead>
                    <tbody></tbody>
                </table>
            </div>
        </div>
    `);

    $.get(`${API_BASE}/brands`, function(data) {
        const tbody = $('#brandsTable tbody');
        tbody.empty();

        data.forEach(brand => {
            const date = new Date(brand.created_at);
            tbody.append(`
                <tr>
                    <td>${brand.name}</td>
                    <td>${brand.description || '-'}</td>
                    <td>${date.toLocaleDateString()}</td>
                    <td>
                        <button class="btn btn-sm btn-primary action-btn" onclick="editBrand(${brand.id}, '${brand.name}', '${brand.description || ''}')">
                            <i class="bi bi-pencil"></i>
                        </button>
                        <button class="btn btn-sm btn-danger action-btn" onclick="deleteBrand(${brand.id})">
                            <i class="bi bi-trash"></i>
                        </button>
                    </td>
                </tr>
            `);
        });

        $('#brandsTable').DataTable();
    });
}

function showAddBrand() {
    $('#brandId').val('');
    $('#brandForm')[0].reset();
    $('#brandModalLabel').text('Add Brand');
    const modal = new bootstrap.Modal($('#brandModal'));
    modal.show();
}

function editBrand(id, name, description) {
    $('#brandId').val(id);
    $('#brandName').val(name);
    $('#brandDescription').val(description);
    $('#brandModalLabel').text('Edit Brand');
    const modal = new bootstrap.Modal($('#brandModal'));
    modal.show();
}

function deleteBrand(id) {
    if (!confirm('Are you sure?')) return;

    $.ajax({
        url: `${API_BASE}/brands/${id}`,
        method: 'DELETE',
        success: function() {
            alert('Brand deleted');
            loadBrands();
        },
        error: function(xhr) {
            alert('Error: ' + (xhr.responseJSON?.error || 'Cannot delete'));
        }
    });
}

function saveBrand() {
    const id = $('#brandId').val();
    const data = {
        name: $('#brandName').val(),
        description: $('#brandDescription').val()
    };

    const url = id ? `${API_BASE}/brands/${id}` : `${API_BASE}/brands`;
    const method = id ? 'PUT' : 'POST';

    $.ajax({
        url: url,
        method: method,
        contentType: 'application/json',
        data: JSON.stringify(data),
        success: function() {
            alert('Brand saved');
            bootstrap.Modal.getInstance($('#brandModal')).hide();
            loadBrands();
        },
        error: function(xhr) {
            alert('Error: ' + (xhr.responseJSON?.error || 'Failed to save'));
        }
    });
}

function loadModels() {
    $('#content-area').html(`
        <div class="page-header d-flex justify-content-between align-items-center">
            <h2><i class="bi bi-phone"></i> Models</h2>
            <button class="btn btn-success" onclick="showAddModel()"><i class="bi bi-plus-circle"></i> Add Model</button>
        </div>
        <div class="card">
            <div class="card-body">
                <table class="table table-hover" id="modelsTable">
                    <thead>
                        <tr>
                            <th>Name</th>
                            <th>Brand</th>
                            <th>Description</th>
                            <th>Created</th>
                            <th>Actions</th>
                        </tr>
                    </thead>
                    <tbody></tbody>
                </table>
            </div>
        </div>
    `);

    Promise.all([
        $.get(`${API_BASE}/models`),
        $.get(`${API_BASE}/brands`)
    ]).then(([models, brands]) => {
        const tbody = $('#modelsTable tbody');
        tbody.empty();

        models.forEach(model => {
            const date = new Date(model.created_at);
            tbody.append(`
                <tr>
                    <td>${model.name}</td>
                    <td>${model.brand_name || '-'}</td>
                    <td>${model.description || '-'}</td>
                    <td>${date.toLocaleDateString()}</td>
                    <td>
                        <button class="btn btn-sm btn-primary action-btn" onclick="editModel(${model.id}, '${model.name}', ${model.brand_id}, '${model.description || ''}')">
                            <i class="bi bi-pencil"></i>
                        </button>
                        <button class="btn btn-sm btn-danger action-btn" onclick="deleteModel(${model.id})">
                            <i class="bi bi-trash"></i>
                        </button>
                    </td>
                </tr>
            `);
        });

        $('#modelsTable').DataTable();
    });
}

function showAddModel() {
    $('#modelId').val('');
    $('#modelForm')[0].reset();
    $('#modelModalLabel').text('Add Model');

    $.get(`${API_BASE}/brands`, function(brands) {
        const select = $('#modelBrand');
        select.empty().append('<option value="">Select Brand</option>');
        brands.forEach(brand => {
            select.append(`<option value="${brand.id}">${brand.name}</option>`);
        });
    });

    const modal = new bootstrap.Modal($('#modelModal'));
    modal.show();
}

function editModel(id, name, brandId, description) {
    $('#modelId').val(id);
    $('#modelName').val(name);
    $('#modelDescription').val(description);
    $('#modelModalLabel').text('Edit Model');

    $.get(`${API_BASE}/brands`, function(brands) {
        const select = $('#modelBrand');
        select.empty().append('<option value="">Select Brand</option>');
        brands.forEach(brand => {
            select.append(`<option value="${brand.id}" ${brand.id === brandId ? 'selected' : ''}>${brand.name}</option>`);
        });
    });

    const modal = new bootstrap.Modal($('#modelModal'));
    modal.show();
}

function deleteModel(id) {
    if (!confirm('Are you sure?')) return;

    $.ajax({
        url: `${API_BASE}/models/${id}`,
        method: 'DELETE',
        success: function() {
            alert('Model deleted');
            loadModels();
        },
        error: function(xhr) {
            alert('Error: ' + (xhr.responseJSON?.error || 'Cannot delete'));
        }
    });
}

function saveModel() {
    const id = $('#modelId').val();
    const data = {
        name: $('#modelName').val(),
        brand_id: $('#modelBrand').val(),
        description: $('#modelDescription').val()
    };

    const url = id ? `${API_BASE}/models/${id}` : `${API_BASE}/models`;
    const method = id ? 'PUT' : 'POST';

    $.ajax({
        url: url,
        method: method,
        contentType: 'application/json',
        data: JSON.stringify(data),
        success: function() {
            alert('Model saved');
            bootstrap.Modal.getInstance($('#modelModal')).hide();
            loadModels();
        },
        error: function(xhr) {
            alert('Error: ' + (xhr.responseJSON?.error || 'Failed to save'));
        }
    });
}

function loadPurchaseOrders() {
    $('#content-area').html(`
        <div class="page-header d-flex justify-content-between align-items-center">
            <h2><i class="bi bi-cart-plus"></i> Purchase Orders</h2>
            <button class="btn btn-success" onclick="showAddPO()"><i class="bi bi-plus-circle"></i> Create PO</button>
        </div>
        <div class="card">
            <div class="card-body">
                <table class="table table-hover" id="poTable">
                    <thead>
                        <tr>
                            <th>PO Number</th>
                            <th>Supplier</th>
                            <th>Order Date</th>
                            <th>Expected Delivery</th>
                            <th>Total Amount</th>
                            <th>Status</th>
                            <th>Actions</th>
                        </tr>
                    </thead>
                    <tbody></tbody>
                </table>
            </div>
        </div>
    `);

    $.get(`${API_BASE}/purchase-orders`, function(data) {
        const tbody = $('#poTable tbody');
        tbody.empty();

        data.forEach(po => {
            const orderDate = new Date(po.order_date);
            const expectedDate = po.expected_delivery ? new Date(po.expected_delivery).toLocaleDateString() : '-';

            let statusBadge = 'secondary';
            if (po.status === 'completed') statusBadge = 'success';
            else if (po.status === 'partial') statusBadge = 'warning';
            else if (po.status === 'pending') statusBadge = 'info';

            let paymentBadge = 'danger';
            if (po.payment_status === 'paid') paymentBadge = 'success';
            else if (po.payment_status === 'partial') paymentBadge = 'warning';

            tbody.append(`
                <tr>
                    <td>${po.po_number}</td>
                    <td>${po.supplier_name}</td>
                    <td>${orderDate.toLocaleDateString()}</td>
                    <td>${expectedDate}</td>
                    <td>$${parseFloat(po.total_amount || 0).toFixed(2)}</td>
                    <td><span class="badge bg-${statusBadge}">${po.status}</span></td>
                    <td>
                        <button class="btn btn-sm btn-info action-btn" onclick="viewPO(${po.id})">
                            <i class="bi bi-eye"></i>
                        </button>
                        <button class="btn btn-sm btn-success action-btn" onclick="receivePO(${po.id})" ${po.status === 'completed' ? 'disabled' : ''}>
                            <i class="bi bi-check-circle"></i> Receive
                        </button>
                    </td>
                </tr>
            `);
        });

        $('#poTable').DataTable({
            order: [[0, 'desc']]
        });
    });
}

function showAddPO() {
    $('#poForm')[0].reset();
    $('#poItemsBody').empty();
    poItemCounter = 0;

    const today = new Date().toISOString().split('T')[0];
    $('#poDate').val(today);
    $('#poNumber').val('PO-' + Date.now());

    const modal = new bootstrap.Modal($('#poModal'));
    modal.show();
}

function addPOItem() {
    poItemCounter++;

    Promise.all([
        $.get(`${API_BASE}/categories`),
        $.get(`${API_BASE}/brands`),
        $.get(`${API_BASE}/models`)
    ]).then(([categories, brands, models]) => {
        const row = $(`
            <tr id="poItem${poItemCounter}">
                <td><input type="text" class="form-control form-control-sm po-product-name" placeholder="Product Name" required></td>
                <td>
                    <select class="form-select form-select-sm po-category">
                        <option value="">Select</option>
                        ${categories.map(c => `<option value="${c.id}">${c.name}</option>`).join('')}
                    </select>
                </td>
                <td>
                    <select class="form-select form-select-sm po-brand">
                        <option value="">Select</option>
                        ${brands.map(b => `<option value="${b.id}">${b.name}</option>`).join('')}
                    </select>
                </td>
                <td>
                    <select class="form-select form-select-sm po-model">
                        <option value="">Select</option>
                        ${models.map(m => `<option value="${m.id}">${m.name}</option>`).join('')}
                    </select>
                </td>
                <td><input type="number" class="form-control form-control-sm po-quantity" value="1" min="1" required></td>
                <td><input type="number" class="form-control form-control-sm po-cost" value="0" step="0.01" min="0" required></td>
                <td class="po-line-total">0.00</td>
                <td><button type="button" class="btn btn-sm btn-danger" onclick="removePOItem(${poItemCounter})"><i class="bi bi-x"></i></button></td>
            </tr>
        `);

        $('#poItemsBody').append(row);

        row.find('.po-quantity, .po-cost').on('input', calculatePOTotal);
    });
}

function removePOItem(id) {
    $(`#poItem${id}`).remove();
    calculatePOTotal();
}

function calculatePOTotal() {
    let total = 0;

    $('#poItemsBody tr').each(function() {
        const qty = parseFloat($(this).find('.po-quantity').val()) || 0;
        const cost = parseFloat($(this).find('.po-cost').val()) || 0;
        const lineTotal = qty * cost;

        $(this).find('.po-line-total').text(lineTotal.toFixed(2));
        total += lineTotal;
    });

    $('#poTotalAmount').text(total.toFixed(2));
}

function savePurchaseOrder() {
    const items = [];

    $('#poItemsBody tr').each(function() {
        items.push({
            product_name: $(this).find('.po-product-name').val(),
            category_id: $(this).find('.po-category').val() || null,
            brand_id: $(this).find('.po-brand').val() || null,
            model_id: $(this).find('.po-model').val() || null,
            quantity: parseInt($(this).find('.po-quantity').val()),
            cost_price: parseFloat($(this).find('.po-cost').val())
        });
    });

    if (items.length === 0) {
        alert('Please add at least one item');
        return;
    }

    const data = {
        po_number: $('#poNumber').val(),
        supplier_name: $('#poSupplier').val(),
        supplier_contact: $('#poSupplierContact').val(),
        order_date: $('#poDate').val(),
        expected_delivery: $('#poExpectedDelivery').val() || null,
        total_amount: parseFloat($('#poTotalAmount').text()),
        notes: $('#poNotes').val(),
        items: items
    };

    $.ajax({
        url: `${API_BASE}/purchase-orders`,
        method: 'POST',
        contentType: 'application/json',
        data: JSON.stringify(data),
        success: function() {
            alert('Purchase Order created successfully');
            bootstrap.Modal.getInstance($('#poModal')).hide();
            loadPurchaseOrders();
        },
        error: function(xhr) {
            alert('Error: ' + (xhr.responseJSON?.error || 'Failed to create PO'));
        }
    });
}

function viewPO(id) {
    $.get(`${API_BASE}/purchase-orders/${id}`, function(po) {
        const orderDate = new Date(po.order_date).toLocaleDateString();
        const expectedDate = po.expected_delivery ? new Date(po.expected_delivery).toLocaleDateString() : '-';

        let paymentBadge = 'danger';
        if (po.payment_status === 'paid') paymentBadge = 'success';
        else if (po.payment_status === 'partial') paymentBadge = 'warning';

        let content = `
            <div class="mb-3">
                <h6>PO Details</h6>
                <p><strong>PO Number:</strong> ${po.po_number}</p>
                <p><strong>Supplier:</strong> ${po.supplier_name} (${po.supplier_contact || 'No contact'})</p>
                <p><strong>Order Date:</strong> ${orderDate}</p>
                <p><strong>Expected Delivery:</strong> ${expectedDate}</p>
                <p><strong>Status:</strong> <span class="badge bg-info">${po.status}</span></p>
                <p><strong>Payment Status:</strong> <span class="badge bg-${paymentBadge}">${po.payment_status || 'unpaid'}</span></p>
                <p><strong>Storage Location:</strong> ${po.storage_location || '-'}</p>
                <p><strong>Notes:</strong> ${po.notes || '-'}</p>
            </div>
            <h6>Items</h6>
            <table class="table table-sm">
                <thead>
                    <tr>
                        <th>Product</th>
                        <th>Quantity</th>
                        <th>Cost Price</th>
                        <th>Received</th>
                        <th>Total</th>
                    </tr>
                </thead>
                <tbody>
        `;

        po.items.forEach(item => {
            content += `
                <tr>
                    <td>${item.product_name}</td>
                    <td>${item.quantity}</td>
                    <td>$${parseFloat(item.cost_price).toFixed(2)}</td>
                    <td>${item.received_quantity}</td>
                    <td>$${(item.quantity * item.cost_price).toFixed(2)}</td>
                </tr>
            `;
        });

        content += `
                </tbody>
                <tfoot>
                    <tr>
                        <td colspan="4" class="text-end"><strong>Total:</strong></td>
                        <td><strong>$${parseFloat(po.total_amount).toFixed(2)}</strong></td>
                    </tr>
                </tfoot>
            </table>
        `;

        alert(content);
    });
}

function receivePO(id) {
    $.get(`${API_BASE}/purchase-orders/${id}`, function(po) {
        let content = `
            <p><strong>PO Number:</strong> ${po.po_number}</p>
            <p><strong>Supplier:</strong> ${po.supplier_name}</p>
            <div class="table-responsive">
                <table class="table table-sm">
                    <thead>
                        <tr>
                            <th>Product</th>
                            <th>Ordered</th>
                            <th>Already Received</th>
                            <th>Receive Now</th>
                            <th>Damaged</th>
                            <th>Damage Reason</th>
                        </tr>
                    </thead>
                    <tbody id="receiveItemsBody">
        `;

        po.items.forEach(item => {
            const remaining = item.quantity - item.received_quantity;
            content += `
                <tr>
                    <td>${item.product_name}</td>
                    <td>${item.quantity}</td>
                    <td>${item.received_quantity}</td>
                    <td>
                        <input type="number" class="form-control form-control-sm receive-qty" 
                               data-item-id="${item.id}" value="${remaining}" min="0" max="${remaining}">
                    </td>
                    <td>
                        <input type="number" class="form-control form-control-sm receive-damaged" 
                               data-item-id="${item.id}" value="0" min="0" max="${remaining}">
                    </td>
                    <td>
                        <input type="text" class="form-control form-control-sm receive-damage-reason" 
                               data-item-id="${item.id}" placeholder="Enter reason if damaged">
                    </td>
                </tr>
            `;
        });

        content += '</tbody></table></div>';

        $('#receivePOContent').html(content);
        $('#confirmReceivePOBtn').data('po-id', id);

        const modal = new bootstrap.Modal($('#receivePOModal'));
        modal.show();
    });
}

function confirmReceivePO() {
    const poId = $('#confirmReceivePOBtn').data('po-id');
    const items = [];

    $('.receive-qty').each(function() {
        const itemId = $(this).data('item-id');
        const receivedQty = parseInt($(this).val()) || 0;
        const damagedQty = parseInt($(`.receive-damaged[data-item-id="${itemId}"]`).val()) || 0;
        const damageReason = $(`.receive-damage-reason[data-item-id="${itemId}"]`).val();

        if (receivedQty > 0 || damagedQty > 0) {
            items.push({
                id: itemId,
                received_quantity: receivedQty,
                damaged_quantity: damagedQty,
                damage_reason: damageReason
            });
        }
    });

    if (items.length === 0) {
        alert('Please enter quantities to receive or mark as damaged');
        return;
    }

    const paymentStatus = $('#receivePaymentStatus').val();
    const storageLocation = $('#receiveStorageLocation').val();

    $.ajax({
        url: `${API_BASE}/purchase-orders/${poId}/receive`,
        method: 'POST',
        contentType: 'application/json',
        data: JSON.stringify({ 
            items: items,
            payment_status: paymentStatus,
            storage_location: storageLocation
        }),
        success: function(response) {
            if (response.success) {
                let message = '✓ Items received successfully!\n\n';
                message += 'GRN Number: ' + response.grn_number + '\n';
                message += 'Stock has been updated in inventory.\n';
                message += 'Payment status: ' + paymentStatus + '\n';
                if (storageLocation) {
                    message += 'Storage location: ' + storageLocation + '\n';
                }

                if (response.damaged_count > 0) {
                    message += '\n⚠ ' + response.damaged_count + ' damaged item(s) recorded';
                }

                message += '\n\nWould you like to view the GRN now?';

                if (confirm(message)) {
                    bootstrap.Modal.getInstance($('#receivePOModal')).hide();
                    loadPage('grns');
                } else {
                    bootstrap.Modal.getInstance($('#receivePOModal')).hide();
                    loadPurchaseOrders();
                }

                // Reload inventory if on that page
                if (currentPage === 'inventory') {
                    loadInventoryData();
                }
            } else {
                alert('Error: ' + (response.error || 'Failed to receive items'));
            }
        },
        error: function(xhr) {
            alert('Error: ' + (xhr.responseJSON?.error || 'Failed to receive items'));
        }
    });
}

function loadGRNs() {
    $('#content-area').html(`
        <div class="page-header d-flex justify-content-between align-items-center">
            <h2><i class="bi bi-receipt"></i> Goods Receipt Notes (GRNs)</h2>
            <button class="btn btn-primary" onclick="generateGRNReport()"><i class="bi bi-download"></i> Generate Report</button>
        </div>
        <div class="card">
            <div class="card-body">
                <table class="table table-hover" id="grnTable">
                    <thead>
                        <tr>
                            <th>GRN Number</th>
                            <th>PO Number</th>
                            <th>Supplier</th>
                            <th>Received Date</th>
                            <th>Total Amount</th>
                            <th>Actions</th>
                        </tr>
                    </thead>
                    <tbody></tbody>
                </table>
            </div>
        </div>
    `);

    $.get(`${API_BASE}/grns`, function(data) {
        const tbody = $('#grnTable tbody');
        tbody.empty();

        data.forEach(grn => {
            const receivedDate = new Date(grn.received_date).toLocaleDateString();
            tbody.append(`
                <tr>
                    <td>${grn.grn_number}</td>
                    <td>${grn.po_number || '-'}</td>
                    <td>${grn.supplier_name || '-'}</td>
                    <td>${receivedDate}</td>
                    <td>$${parseFloat(grn.total_amount || 0).toFixed(2)}</td>
                    <td>
                        <button class="btn btn-sm btn-info action-btn" onclick="viewGRN(${grn.id})">
                            <i class="bi bi-eye"></i> View
                        </button>
                    </td>
                </tr>
            `);
        });

        $('#grnTable').DataTable({
            order: [[0, 'desc']]
        });
    });
}

function viewGRN(id) {
    $.get(`${API_BASE}/grns/${id}`, function(grn) {
        const receivedDate = new Date(grn.received_date).toLocaleDateString();

        let content = `
            <div class="mb-3">
                <h6>GRN Details</h6>
                <p><strong>GRN Number:</strong> ${grn.grn_number}</p>
                <p><strong>PO Number:</strong> ${grn.po_number || '-'}</p>
                <p><strong>Supplier:</strong> ${grn.supplier_name || '-'}</p>
                <p><strong>Received Date:</strong> ${receivedDate}</p>
                <p><strong>Payment Status:</strong> <span class="badge bg-${grn.payment_status === 'paid' ? 'success' : grn.payment_status === 'partial' ? 'warning' : 'danger'}">${grn.payment_status || 'unpaid'}</span></p>
                <p><strong>Storage Location:</strong> ${grn.storage_location || '-'}</p>
                <p><strong>Notes:</strong> ${grn.notes || '-'}</p>
            </div>
            <h6>Items Received</h6>
            <table class="table table-sm">
                <thead>
                    <tr>
                        <th>Product</th>
                        <th>Ordered</th>
                        <th>Received</th>
                        <th>Damaged</th>
                        <th>Unit Cost</th>
                        <th>Line Total</th>
                    </tr>
                </thead>
                <tbody>
        `;

        let totalAmount = 0;
        grn.items.forEach(item => {
            const lineTotal = item.quantity_received * item.cost_price;
            totalAmount += lineTotal;
            content += `
                <tr>
                    <td>${item.product_name}</td>
                    <td>${item.ordered_quantity || '-'}</td>
                    <td>${item.quantity_received}</td>
                    <td>${item.quantity_damaged || 0} ${item.damage_reason ? `<br><small class="text-muted">(${item.damage_reason})</small>` : ''}</td>
                    <td>$${parseFloat(item.cost_price).toFixed(2)}</td>
                    <td>$${lineTotal.toFixed(2)}</td>
                </tr>
            `;
        });

        content += `
                </tbody>
                <tfoot>
                    <tr>
                        <td colspan="5" class="text-end"><strong>Total Amount:</strong></td>
                        <td><strong>$${totalAmount.toFixed(2)}</strong></td>
                    </tr>
                </tfoot>
            </table>
        `;

        $('#grnViewContent').html(content);
        const modal = new bootstrap.Modal($('#grnViewModal'));
        modal.show();
    });
}

function generateGRNReport() {
    window.location.href = `${API_BASE}/export/grns`;
}

function printGRN() {
    const content = document.getElementById('grnViewContent').innerHTML;
    const printWindow = window.open('', '', 'height=600,width=800');
    printWindow.document.write('<html><head><title>GRN</title>');
    printWindow.document.write('<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">');
    printWindow.document.write('</head><body>');
    printWindow.document.write(content);
    printWindow.document.write('</body></html>');
    printWindow.document.close();
    printWindow.print();
}

function viewStockHistory(productId) {
    $.get(`${API_BASE}/products/${productId}/stock-history`, function(data) {
        let content = `
            <div class="mb-3">
                <h6>Stock History for: ${data.product_name}</h6>
            </div>
            <div class="table-responsive">
                <table class="table table-sm table-striped">
                    <thead>
                        <tr>
                            <th>Date & Time</th>
                            <th>Stock Added</th>
                            <th>Reference</th>
                            <th>User</th>
                            <th>Running Balance</th>
                        </tr>
                    </thead>
                    <tbody>
        `;

        if (data.history.length === 0) {
            content += '<tr><td colspan="5" class="text-center text-muted">No stock movements found</td></tr>';
        } else {
            data.history.forEach(item => {
                const date = new Date(item.date_time);
                const formattedDate = date.toLocaleDateString() + ' ' + date.toLocaleTimeString();
                
                let stockChange = '';
                if (item.stock_added > 0) {
                    stockChange = `<span class="text-success">+${item.stock_added}</span>`;
                } else if (item.stock_removed > 0) {
                    stockChange = `<span class="text-danger">-${item.stock_removed}</span>`;
                }

                content += `
                    <tr>
                        <td>${formattedDate}</td>
                        <td>${stockChange}</td>
                        <td>${item.reference}</td>
                        <td>${item.received_by}</td>
                        <td><strong>${item.running_balance}</strong></td>
                    </tr>
                `;
            });
        }

        content += `
                    </tbody>
                </table>
            </div>
        `;

        $('#stockHistoryContent').html(content);
        const modal = new bootstrap.Modal($('#stockHistoryModal'));
        modal.show();
    }).fail(function(xhr) {
        alert('Error loading stock history: ' + (xhr.responseJSON?.error || 'Unknown error'));
    });
}