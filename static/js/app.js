const API_BASE = '/api';
let currentPage = 'dashboard';
let inventoryTable = null;
let poItemCounter = 0;
let isAuthenticated = false;

let currentPOSProductForIMEI = null;
let currentPOSCartIndex = null;

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
        case 'stock-adjustment':
            loadStockAdjustment();
            break;
        case 'quick-order':
            loadQuickOrder();
            break;
        case 'grns':
            loadGRNs();
            break;
        case 'pos':
            loadPOS();
            break;
        case 'reports':
            loadReports();
            break;
    }
}

let salesChart = null;

function loadDashboard() {
    $('#content-area').html(`
        <div class="page-header">
            <h2><i class="bi bi-speedometer2"></i> Dashboard</h2>
        </div>

        <!-- Stats Cards -->
        <div class="row mb-4" id="statsCards">
            <div class="col-md-3">
                <div class="card stats-card">
                    <div class="stats-icon text-primary"><i class="bi bi-box-seam"></i></div>
                    <div class="stats-value" id="totalProducts">0</div>
                    <div class="stats-label">Total Products</div>
                </div>
            </div>
            <div class="col-md-3">
                <div class="card stats-card">
                    <div class="stats-icon text-success"><i class="bi bi-cart-check"></i></div>
                    <div class="stats-value" id="totalSales">$0</div>
                    <div class="stats-label">Total Sales (30d)</div>
                </div>
            </div>
            <div class="col-md-3">
                <div class="card stats-card">
                    <div class="stats-icon text-info"><i class="bi bi-graph-up"></i></div>
                    <div class="stats-value" id="totalProfit">$0</div>
                    <div class="stats-label">Total Profit (30d)</div>
                </div>
            </div>
            <div class="col-md-3">
                <div class="card stats-card">
                    <div class="stats-icon text-warning"><i class="bi bi-exclamation-triangle"></i></div>
                    <div class="stats-value" id="lowStock">0</div>
                    <div class="stats-label">Low Stock Items</div>
                </div>
            </div>
        </div>

        <!-- Charts Row -->
        <div class="row mb-4">
            <div class="col-md-8">
                <div class="card">
                    <div class="card-header d-flex justify-content-between align-items-center">
                        <span><i class="bi bi-graph-up"></i> Sales Trend</span>
                        <div class="btn-group btn-group-sm" role="group">
                            <input type="radio" class="btn-check" name="salesPeriod" id="period7d" value="7" checked>
                            <label class="btn btn-outline-primary" for="period7d">7 Days</label>

                            <input type="radio" class="btn-check" name="salesPeriod" id="period30d" value="30">
                            <label class="btn btn-outline-primary" for="period30d">30 Days</label>
                        </div>
                    </div>
                    <div class="card-body">
                        <canvas id="salesChart" height="80"></canvas>
                    </div>
                </div>
            </div>

            <div class="col-md-4">
                <div class="card">
                    <div class="card-header">
                        <i class="bi bi-trophy"></i> Top Selling Products
                    </div>
                    <div class="card-body">
                        <div id="topProductsList"></div>
                    </div>
                </div>
            </div>
        </div>

        <!-- Profit Summary & Recent Transactions -->
        <div class="row mb-4">
            <div class="col-md-6">
                <div class="card">
                    <div class="card-header">
                        <i class="bi bi-cash-stack"></i> Profit Margin Summary (30 Days)
                    </div>
                    <div class="card-body">
                        <div class="row text-center">
                            <div class="col-4">
                                <h5 class="text-primary" id="totalRevenue">$0</h5>
                                <small class="text-muted">Revenue</small>
                            </div>
                            <div class="col-4">
                                <h5 class="text-danger" id="totalCost">$0</h5>
                                <small class="text-muted">Cost</small>
                            </div>
                            <div class="col-4">
                                <h5 class="text-success" id="netProfit">$0</h5>
                                <small class="text-muted">Profit</small>
                            </div>
                        </div>
                        <hr>
                        <div class="text-center">
                            <h3 class="mb-0" id="profitMarginPercent">0%</h3>
                            <small class="text-muted">Profit Margin</small>
                        </div>
                        <div class="progress mt-3" style="height: 25px;">
                            <div class="progress-bar bg-success" id="profitProgressBar" role="progressbar" style="width: 0%">
                                <span id="profitProgressText">0%</span>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            <div class="col-md-6">
                <div class="card">
                    <div class="card-header">
                        <i class="bi bi-clock-history"></i> Recent POS Transactions
                    </div>
                    <div class="card-body">
                        <div class="table-responsive">
                            <table class="table table-sm table-hover" id="recentTransactionsTable">
                                <thead>
                                    <tr>
                                        <th>Sale #</th>
                                        <th>Customer</th>
                                        <th>Amount</th>
                                        <th>Time</th>
                                    </tr>
                                </thead>
                                <tbody></tbody>
                            </table>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <!-- Low Stock Alerts -->
        <div class="row">
            <div class="col-md-12">
                <div class="card">
                    <div class="card-header">
                        <i class="bi bi-exclamation-triangle text-warning"></i> Low Stock Alerts
                    </div>
                    <div class="card-body">
                        <div class="table-responsive">
                            <table class="table table-sm table-hover" id="lowStockTable">
                                <thead>
                                    <tr>
                                        <th>Product</th>
                                        <th>Brand</th>
                                        <th>Category</th>
                                        <th>Current Stock</th>
                                        <th>Min Level</th>
                                        <th>Action</th>
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

    // Load dashboard data
    loadDashboardData();

    // Period change handler
    $('input[name="salesPeriod"]').on('change', function() {
        loadSalesChart($(this).val());
    });
}

function loadDashboardData() {
    $.get(`${API_BASE}/dashboard/analytics`, function(data) {
        // Update stats cards
        $('#totalProducts').text(data.total_products);
        $('#totalSales').text('$' + data.total_sales.toFixed(2));
        $('#totalProfit').text('$' + data.total_profit.toFixed(2));
        $('#lowStock').text(data.low_stock_count);

        // Update profit summary
        $('#totalRevenue').text('$' + data.profit_summary.revenue.toFixed(2));
        $('#totalCost').text('$' + data.profit_summary.cost.toFixed(2));
        $('#netProfit').text('$' + data.profit_summary.profit.toFixed(2));

        const marginPercent = data.profit_summary.margin_percent || 0;
        $('#profitMarginPercent').text(marginPercent.toFixed(2) + '%');
        $('#profitProgressBar').css('width', Math.min(marginPercent, 100) + '%');
        $('#profitProgressText').text(marginPercent.toFixed(1) + '%');

        // Update top products
        const topProductsList = $('#topProductsList');
        topProductsList.empty();
        if (data.top_products.length === 0) {
            topProductsList.append('<p class="text-muted text-center">No sales data yet</p>');
        } else {
            data.top_products.forEach((product, index) => {
                const badgeClass = index === 0 ? 'bg-warning' : index === 1 ? 'bg-secondary' : 'bg-info';
                topProductsList.append(`
                    <div class="d-flex justify-content-between align-items-center mb-3 pb-2 border-bottom">
                        <div>
                            <span class="badge ${badgeClass} me-2">#${index + 1}</span>
                            <strong>${product.product_name}</strong>
                            <br>
                            <small class="text-muted">${product.brand_name || 'N/A'}</small>
                        </div>
                        <div class="text-end">
                            <strong class="text-success">${product.total_quantity} sold</strong>
                            <br>
                            <small class="text-muted">$${product.total_revenue.toFixed(2)}</small>
                        </div>
                    </div>
                `);
            });
        }

        // Update recent transactions
        const transactionsBody = $('#recentTransactionsTable tbody');
        transactionsBody.empty();
        if (data.recent_transactions.length === 0) {
            transactionsBody.append('<tr><td colspan="4" class="text-center text-muted">No recent transactions</td></tr>');
        } else {
            data.recent_transactions.forEach(transaction => {
                const date = new Date(transaction.sale_date);
                const timeStr = date.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });
                const amountClass = transaction.transaction_type === 'return' ? 'text-danger' : 'text-success';
                transactionsBody.append(`
                    <tr>
                        <td><small>${transaction.sale_number}</small></td>
                        <td><small>${transaction.customer_name || 'Walk-in'}</small></td>
                        <td class="${amountClass}"><strong>$${Math.abs(transaction.total_amount).toFixed(2)}</strong></td>
                        <td><small>${timeStr}</small></td>
                    </tr>
                `);
            });
        }

        // Update low stock table
        const lowStockBody = $('#lowStockTable tbody');
        lowStockBody.empty();
        if (data.low_stock_items.length === 0) {
            lowStockBody.append('<tr><td colspan="6" class="text-center text-muted">No low stock items</td></tr>');
        } else {
            data.low_stock_items.forEach(item => {
                lowStockBody.append(`
                    <tr>
                        <td>${item.name}</td>
                        <td>${item.brand_name || '-'}</td>
                        <td>${item.category_name || '-'}</td>
                        <td><span class="badge bg-warning">${item.current_stock}</span></td>
                        <td>${item.min_stock_level}</td>
                        <td>
                            <button class="btn btn-sm btn-primary" onclick="viewProductDetails(${item.id})">
                                <i class="bi bi-eye"></i>
                            </button>
                        </td>
                    </tr>
                `);
            });
        }
    });

    // Load sales chart with default 7 days
    loadSalesChart(7);
}

function loadSalesChart(days) {
    $.get(`${API_BASE}/dashboard/sales-chart?days=${days}`, function(data) {
        const ctx = document.getElementById('salesChart');
        if (!ctx) return;

        // Destroy existing chart if it exists
        if (salesChart) {
            salesChart.destroy();
        }

        salesChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: data.labels,
                datasets: [{
                    label: 'Sales',
                    data: data.sales,
                    borderColor: 'rgb(75, 192, 192)',
                    backgroundColor: 'rgba(75, 192, 192, 0.2)',
                    tension: 0.4,
                    fill: true
                }, {
                    label: 'Profit',
                    data: data.profit,
                    borderColor: 'rgb(54, 162, 235)',
                    backgroundColor: 'rgba(54, 162, 235, 0.2)',
                    tension: 0.4,
                    fill: true
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: true,
                plugins: {
                    legend: {
                        position: 'top',
                    },
                    title: {
                        display: true,
                        text: `Sales & Profit Trend (Last ${days} Days)`
                    },
                    tooltip: {
                        mode: 'index',
                        intersect: false,
                        callbacks: {
                            label: function(context) {
                                let label = context.dataset.label || '';
                                if (label) {
                                    label += ': ';
                                }
                                if (context.parsed.y !== null) {
                                    label += '$' + context.parsed.y.toFixed(2);
                                }
                                return label;
                            }
                        }
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: {
                            callback: function(value) {
                                return '$' + value;
                            }
                        }
                    }
                }
            }
        });
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
                    <input type="text" class="form-control" id="searchProduct" placeholder="Search by name, SKU, or IMEI...">
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

    // Add event handlers for filters
    $('#searchProduct').on('keyup', function() {
        applyFilters();
    });

    $('#filterCategory, #filterBrand, #filterStockStatus, #filterStatus').on('change', function() {
        applyFilters();
    });

    $('#selectAll').on('change', function() {
        $('input[name="productCheck"]').prop('checked', this.checked);
        updateBulkActions();
    });
}

function loadFilterDropdowns() {
    // Load categories for filter dropdown
    $.get(`${API_BASE}/categories`, function(data) {
        const filterSelect = $('#filterCategory');
        filterSelect.empty().append('<option value="">All Categories</option>');
        data.forEach(cat => {
            filterSelect.append(`<option value="${cat.id}">${cat.name}</option>`);
        });

        // Also populate product form dropdown
        const productSelect = $('#productCategory');
        productSelect.empty().append('<option value="">Select Category</option>');
        data.forEach(cat => {
            productSelect.append(`<option value="${cat.id}">${cat.name}</option>`);
        });
    });

    // Load brands for filter dropdown
    $.get(`${API_BASE}/brands`, function(data) {
        const filterSelect = $('#filterBrand');
        filterSelect.empty().append('<option value="">All Brands</option>');
        data.forEach(brand => {
            filterSelect.append(`<option value="${brand.id}">${brand.name}</option>`);
        });

        // Also populate product form dropdown
        const productSelect = $('#productBrand');
        productSelect.empty().append('<option value="">Select Brand</option>');
        data.forEach(brand => {
            productSelect.append(`<option value="${brand.id}">${brand.name}</option>`);
        });
    });

    // Load all models for product form
    $.get(`${API_BASE}/models`, function(data) {
        const modelSelect = $('#productModel');
        modelSelect.empty().append('<option value="">Select Model</option>');
        data.forEach(model => {
            modelSelect.append(`<option value="${model.id}" data-brand-id="${model.brand_id}">${model.name}</option>`);
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
            inventoryTable = null;
        }

        const tbody = $('#inventoryTable tbody');
        tbody.empty();

        if (data.length === 0) {
            tbody.append('<tr><td colspan="11" class="text-center text-muted">No products found</td></tr>');
            // Don't initialize DataTable for empty results
        } else {
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
                            <button class="btn btn-sm btn-success action-btn" onclick="viewProductDetails(${product.id})" title="View Details">
                                <i class="bi bi-eye"></i>
                            </button>
                            <button class="btn btn-sm btn-secondary action-btn" onclick="viewIMEITracking(${product.id})" title="IMEI Tracking">
                                <i class="bi bi-list-ul"></i>
                            </button>
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
                    </tr>`)
            });

            // Initialize DataTable only when there's data
            inventoryTable = $('#inventoryTable').DataTable({
                order: [[2, 'asc']],
                pageLength: 25,
                columnDefs: [
                    { orderable: false, targets: [0, 10] }
                ]
            });

            $('input[name="productCheck"]').on('change', updateBulkActions);
        }
    }).fail(function(xhr) {
        console.error('Error loading products:', xhr);
        alert('Error loading products. Please try again.');
    });
}

function applyFilters() {
    // Clear any existing search timeout
    if (window.filterTimeout) {
        clearTimeout(window.filterTimeout);
    }

    // Add small delay to prevent too many rapid requests
    window.filterTimeout = setTimeout(function() {
        loadInventoryData();
    }, 300);
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

    // Ensure model dropdown is fully visible for adding new products
    $('#productModel option').show();

    const modal = new bootstrap.Modal($('#productModal'));
    modal.show();
}

function editProduct(id) {
    loadFilterDropdowns();

    // Add brand change handler
    $('#productBrand').off('change').on('change', function() {
        const brandId = $(this).val();
        const modelSelect = $('#productModel');

        if (brandId) {
            modelSelect.find('option').each(function() {
                const option = $(this);
                if (option.val() === '') {
                    option.show();
                } else if (option.data('brand-id') == brandId) {
                    option.show();
                } else {
                    option.hide();
                }
            });
        } else {
            modelSelect.find('option').show();
        }
        // Reset model selection if brand changes
        modelSelect.val('');
    });

    // Wait for dropdowns to load, then populate form
    setTimeout(function() {
        $.get(`${API_BASE}/products/${id}`, function(product) {
            $('#productId').val(product.id);
            $('#productSKU').val(product.sku);
            $('#productName').val(product.name);
            $('#productCategory').val(product.category_id);
            $('#productBrand').val(product.brand_id);

            // Trigger the change event for brand to filter models correctly
            $('#productBrand').trigger('change');

            // Filter models by brand first
            if (product.brand_id) {
                $('#productModel option').each(function() {
                    const option = $(this);
                    if (option.val() === '') {
                        option.show();
                    } else if (option.data('brand-id') == product.brand_id) {
                        option.show();
                    } else {
                        option.hide();
                    }
                });
            }

            $('#productModel').val(product.model_id);
            $('#productDescription').val(product.description);
            $('#productCostPrice').val(product.cost_price);
            $('#productSellingPrice').val(product.selling_price);
            $('#productMRP').val(product.mrp);
            $('#productOpeningStock').val(product.opening_stock);
            $('#productCurrentStock').val(product.current_stock);
            $('#productMinStockLevel').val(product.min_stock_level);
            $('#productStorageLocation').val(product.storage_location);
            $('#productStatus').val(product.status);
            $('#productModalLabel').text('Edit Product');

            calculateProfitMargin(); // Renamed from updateProfitMargin

            const modal = new bootstrap.Modal($('#productModal'));
            modal.show();
        });
    }, 200); // Short delay to ensure dropdowns are populated
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
        min_stock_level: parseInt($('#productMinStockLevel').val()) || 10,
        storage_location: $('#productStorageLocation').val(),
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

    if (!brandId) {
        // If no brand is selected, show all models
        $.get(`${API_BASE}/models`, function(data) {
            data.forEach(model => {
                modelSelect.append(`<option value="${model.id}" data-brand-id="${model.brand_id}">${model.name}</option>`);
            });
        });
        return;
    }

    // Fetch all models and filter them by the selected brand
    $.get(`${API_BASE}/models`, function(data) {
        data.filter(m => m.brand_id == brandId).forEach(model => {
            modelSelect.append(`<option value="${model.id}" data-brand-id="${model.brand_id}">${model.name}</option>`);
        });
    });
}

function exportProducts() {
    // Show export options modal
    const content = `
        <div class="mb-3">
            <label class="form-label">Export Scope</label>
            <select class="form-select" id="exportScope">
                <option value="all">All Products</option>
                <option value="filtered">Current Filtered View</option>
                <option value="selected">Selected Products Only</option>
            </select>
        </div>
        <div class="mb-3">
            <label class="form-label">Format</label>
            <select class="form-select" id="exportFormat">
                <option value="excel">Excel (.xlsx)</option>
                <option value="csv">CSV</option>
            </select>
        </div>
        <div class="mb-3">
            <label class="form-label">Columns to Include</label>
            <div class="row">
                <div class="col-6">
                    <div class="form-check">
                        <input class="form-check-input export-col" type="checkbox" value="sku" checked id="col_sku">
                        <label class="form-check-label" for="col_sku">SKU</label>
                    </div>
                    <div class="form-check">
                        <input class="form-check-input export-col" type="checkbox" value="name" checked id="col_name">
                        <label class="form-check-label" for="col_name">Product Name</label>
                    </div>
                    <div class="form-check">
                        <input class="form-check-input export-col" type="checkbox" value="category" checked id="col_category">
                        <label class="form-check-label" for="col_category">Category</label>
                    </div>
                    <div class="form-check">
                        <input class="form-check-input export-col" type="checkbox" value="brand" checked id="col_brand">
                        <label class="form-check-label" for="col_brand">Brand</label>
                    </div>
                    <div class="form-check">
                        <input class="form-check-input export-col" type="checkbox" value="model" checked id="col_model">
                        <label class="form-check-label" for="col_model">Model</label>
                    </div>
                </div>
                <div class="col-6">
                    <div class="form-check">
                        <input class="form-check-input export-col" type="checkbox" value="cost_price" checked id="col_cost">
                        <label class="form-check-label" for="col_cost">Cost Price</label>
                    </div>
                    <div class="form-check">
                        <input class="form-check-input export-col" type="checkbox" value="selling_price" checked id="col_selling">
                        <label class="form-check-label" for="col_selling">Selling Price</label>
                    </div>
                    <div class="form-check">
                        <input class="form-check-input export-col" type="checkbox" value="current_stock" checked id="col_stock">
                        <label class="form-check-label" for="col_stock">Current Stock</label>
                    </div>
                    <div class="form-check">
                        <input class="form-check-input export-col" type="checkbox" value="status" checked id="col_status">
                        <label class="form-check-label" for="col_status">Status</label>
                    </div>
                </div>
            </div>
        </div>
    `;

    const modal = $(`
        <div class="modal fade" id="exportModal" tabindex="-1">
            <div class="modal-dialog">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title"><i class="bi bi-download"></i> Export Products</h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                    </div>
                    <div class="modal-body">${content}</div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
                        <button type="button" class="btn btn-primary" onclick="performExport()">Export</button>
                    </div>
                </div>
            </div>
        </div>
    `);

    $('body').append(modal);
    const modalInstance = new bootstrap.Modal($('#exportModal'));
    modalInstance.show();

    $('#exportModal').on('hidden.bs.modal', function() {
        $(this).remove();
    });
}

function performExport() {
    const scope = $('#exportScope').val();
    const format = $('#exportFormat').val();
    const columns = $('.export-col:checked').map(function() {
        return $(this).val();
    }).get();

    let url = `${API_BASE}/export/products?format=${format}&columns=${columns.join(',')}`;

    if (scope === 'filtered') {
        const search = $('#searchProduct').val();
        const category = $('#filterCategory').val();
        const brand = $('#filterBrand').val();
        const stockStatus = $('#filterStockStatus').val();
        const status = $('#filterStatus').val();

        if (search) url += `&search=${encodeURIComponent(search)}`;
        if (category) url += `&category_id=${category}`;
        if (brand) url += `&brand_id=${brand}`;
        if (stockStatus) url += `&stock_status=${stockStatus}`;
        if (status) url += `&status=${status}`;
    } else if (scope === 'selected') {
        const selectedIds = $('input[name="productCheck"]:checked').map(function() {
            return $(this).val();
        }).get();

        if (selectedIds.length === 0) {
            alert('Please select products to export');
            return;
        }
        url += `&ids=${selectedIds.join(',')}`;
    }

    window.location.href = url;
    bootstrap.Modal.getInstance($('#exportModal')).hide();
}

let importFile = null;
let importPreviewData = [];

function showImportModal() {
    const content = `
        <div id="importStep1">
            <h6 class="mb-3"><i class="bi bi-1-circle"></i> Download Template</h6>
            <p>Download the template file to prepare your product data:</p>
            <div class="mb-3">
                <a href="${API_BASE}/export/template?format=excel" class="btn btn-outline-primary me-2">
                    <i class="bi bi-file-earmark-excel"></i> Excel Template
                </a>
                <a href="${API_BASE}/export/template?format=csv" class="btn btn-outline-primary">
                    <i class="bi bi-file-earmark-text"></i> CSV Template
                </a>
            </div>
            <hr>
            <h6 class="mb-3"><i class="bi bi-2-circle"></i> Upload File</h6>
            <div class="mb-3">
                <input type="file" class="form-control" id="importFileInput" accept=".csv,.xlsx,.xls">
                <div class="form-text">Max 10MB, up to 1000 products. Supports .xlsx, .xls, .csv</div>
            </div>
            <div class="mb-3">
                <div class="form-check">
                    <input class="form-check-input" type="checkbox" id="importFirstRowHeaders" checked>
                    <label class="form-check-label" for="importFirstRowHeaders">
                        First row contains headers
                    </label>
                </div>
                <div class="form-check">
                    <input class="form-check-input" type="checkbox" id="importUpdateExisting">
                    <label class="form-check-label" for="importUpdateExisting">
                        Update existing products (match by SKU)
                    </label>
                </div>
                <div class="form-check">
                    <input class="form-check-input" type="checkbox" id="importSkipErrors" checked>
                    <label class="form-check-label" for="importSkipErrors">
                        Skip products with errors
                    </label>
                </div>
                <div class="form-check">
                    <input class="form-check-input" type="checkbox" id="importAutoCreate" checked>
                    <label class="form-check-label" for="importAutoCreate">
                        Auto-create missing categories/brands
                    </label>
                </div>
            </div>
        </div>
        <div id="importStep2" style="display:none;">
            <h6 class="mb-3"><i class="bi bi-check-circle"></i> File Uploaded</h6>
            <p id="importFileInfo"></p>
            <div id="importPreview"></div>
        </div>
        <div id="importProgress" style="display:none;">
            <div class="progress mb-3">
                <div class="progress-bar progress-bar-striped progress-bar-animated" id="importProgressBar"
                     role="progressbar" style="width: 0%"></div>
            </div>
            <p id="importProgressText" class="text-center"></p>
        </div>
        <div id="importResult" style="display:none;"></div>
    `;

    const modal = $(`
        <div class="modal fade" id="importModal" tabindex="-1">
            <div class="modal-dialog modal-lg">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title"><i class="bi bi-upload"></i> Import Products</h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                    </div>
                    <div class="modal-body">${content}</div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
                        <button type="button" class="btn btn-primary" id="importUploadBtn" onclick="uploadImportFile()">
                            <i class="bi bi-cloud-upload"></i> Upload & Preview
                        </button>
                        <button type="button" class="btn btn-success" id="importConfirmBtn" style="display:none;" onclick="confirmImport()">
                            <i class="bi bi-check-circle"></i> Import Products
                        </button>
                    </div>
                </div>
            </div>
        </div>
    `);

    $('body').append(modal);
    const modalInstance = new bootstrap.Modal($('#importModal'));
    modalInstance.show();

    $('#importModal').on('hidden.bs.modal', function() {
        $(this).remove();
        importFile = null;
        importPreviewData = [];
    });

    $('#importFileInput').on('change', function(e) {
        importFile = e.target.files[0];
        if (importFile) {
            $('#importUploadBtn').prop('disabled', false);
        }
    });
}

function uploadImportFile() {
    if (!importFile) {
        alert('Please select a file');
        return;
    }

    const formData = new FormData();
    formData.append('file', importFile);
    formData.append('first_row_headers', $('#importFirstRowHeaders').is(':checked'));
    formData.append('preview_only', 'true');

    $('#importUploadBtn').prop('disabled', true).html('<span class="spinner-border spinner-border-sm"></span> Uploading...');

    $.ajax({
        url: `${API_BASE}/import/products/preview`,
        method: 'POST',
        data: formData,
        processData: false,
        contentType: false,
        success: function(response) {
            importPreviewData = response;
            showImportPreview(response);
            $('#importStep1').hide();
            $('#importStep2').show();
            $('#importUploadBtn').hide();
            $('#importConfirmBtn').show();
        },
        error: function(xhr) {
            alert('Upload failed: ' + (xhr.responseJSON?.error || 'Unknown error'));
            $('#importUploadBtn').prop('disabled', false).html('<i class="bi bi-cloud-upload"></i> Upload & Preview');
        }
    });
}

function showImportPreview(data) {
    const { total_rows, preview_rows, columns, validation } = data;

    let html = `
        <div class="alert alert-info">
            <strong>File contains ${total_rows} products</strong>
        </div>
        <div class="mb-3">
            <h6>Preview (first 3 rows):</h6>
            <div class="table-responsive">
                <table class="table table-sm table-bordered">
                    <thead>
                        <tr>
    `;

    columns.forEach(col => {
        html += `<th>${col}</th>`;
    });
    html += `</tr></thead><tbody>`;

    preview_rows.forEach(row => {
        html += '<tr>';
        columns.forEach(col => {
            html += `<td>${row[col] || ''}</td>`;
        });
        html += '</tr>';
    });

    html += `</tbody></table></div></div>`;

    if (validation.errors.length > 0) {
        html += `
            <div class="alert alert-warning">
                <strong>⚠ ${validation.errors.length} validation error(s) found:</strong>
                <ul class="mb-0 mt-2">
        `;
        validation.errors.slice(0, 10).forEach(err => {
            html += `<li>${err}</li>`;
        });
        if (validation.errors.length > 10) {
            html += `<li><em>... and ${validation.errors.length - 10} more errors</em></li>`;
        }
        html += `</ul></div>`;
    }

    html += `
        <div class="alert alert-success">
            <strong>✓ ${validation.valid_count} valid products ready to import</strong>
        </div>
    `;

    $('#importFileInfo').html(`<strong>${importFile.name}</strong> (${(importFile.size / 1024).toFixed(1)} KB)`);
    $('#importPreview').html(html);
}

function confirmImport() {
    if (!importFile) return;

    const formData = new FormData();
    formData.append('file', importFile);
    formData.append('first_row_headers', $('#importFirstRowHeaders').is(':checked'));
    formData.append('update_existing', $('#importUpdateExisting').is(':checked'));
    formData.append('skip_errors', $('#importSkipErrors').is(':checked'));
    formData.append('auto_create', $('#importAutoCreate').is(':checked'));

    $('#importStep2').hide();
    $('#importConfirmBtn').hide();
    $('#importProgress').show();
    $('#importProgressBar').css('width', '10%');
    $('#importProgressText').text('Starting import...');

    $.ajax({
        url: `${API_BASE}/import/products`,
        method: 'POST',
        data: formData,
        processData: false,
        contentType: false,
        xhr: function() {
            const xhr = new window.XMLHttpRequest();
            xhr.upload.addEventListener("progress", function(evt) {
                if (evt.lengthComputable) {
                    const percentComplete = (evt.loaded / evt.total) * 100;
                    $('#importProgressBar').css('width', percentComplete + '%');
                    $('#importProgressText').text('Uploading file... ' + percentComplete.toFixed(0) + '%');
                }
            }, false);
            return xhr;
        },
        success: function(response) {
            $('#importProgressBar').css('width', '100%').removeClass('progress-bar-animated');
            $('#importProgressText').text('Import completed!');

            let resultHtml = `
                <div class="alert alert-success">
                    <h6>✓ Import Completed Successfully!</h6>
                    <p class="mb-1"><strong>${response.imported}</strong> products imported</p>
                    ${response.updated ? `<p class="mb-1"><strong>${response.updated}</strong> products updated</p>` : ''}
                    ${response.created_categories ? `<p class="mb-1"><strong>${response.created_categories}</strong> new categories created</p>` : ''}
                    ${response.created_brands ? `<p class="mb-1"><strong>${response.created_brands}</strong> new brands created</p>` : ''}
                </div>
            `;

            if (response.errors && response.errors.length > 0) {
                resultHtml += `
                    <div class="alert alert-warning">
                        <h6>⚠ ${response.errors.length} error(s) encountered:</h6>
                        <ul class="mb-0">
                `;
                response.errors.slice(0, 10).forEach(err => {
                    resultHtml += `<li>${err}</li>`;
                });
                if (response.errors.length > 10) {
                    resultHtml += `<li><em>... and ${response.errors.length - 10} more errors</em></li>`;
                }
                resultHtml += `</ul></div>`;
            }

            $('#importProgress').hide();
            $('#importResult').html(resultHtml).show();

            setTimeout(() => {
                bootstrap.Modal.getInstance($('#importModal')).hide();
                loadInventoryData();
            }, 3000);
        },
        error: function(xhr) {
            $('#importProgressBar').removeClass('progress-bar-animated').addClass('bg-danger');
            $('#importProgressText').text('Import failed!');

            const errorMsg = xhr.responseJSON?.error || 'Unknown error';
            $('#importResult').html(`
                <div class="alert alert-danger">
                    <h6>✗ Import Failed</h6>
                    <p>${errorMsg}</p>
                </div>
            `).show();
        }
    });
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
                            <th>Image</th>
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
            const imageUrl = model.image_data || 'https://via.placeholder.com/50x50?text=No+Image';
            const escapedImageData = model.image_data ? model.image_data.replace(/'/g, "\\'") : '';
            tbody.append(`
                <tr>
                    <td>
                        <img src="${imageUrl}"
                             alt="${model.name}"
                             style="width: 50px; height: 50px; object-fit: cover; border-radius: 5px;"
                             onerror="this.src='https://via.placeholder.com/50x50?text=No+Image'; this.title='Image failed to load';">
                    </td>
                    <td>${model.name}</td>
                    <td>${model.brand_name || '-'}</td>
                    <td>${model.description || '-'}</td>
                    <td>${date.toLocaleDateString()}</td>
                    <td>
                        <button class="btn btn-sm btn-primary action-btn" onclick='editModel(${model.id}, "${model.name}", ${model.brand_id}, "${(model.description || '').replace(/"/g, '&quot;')}", "${escapedImageData}")'>
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
    $('#modelImagePreview').hide();
    $('#modelModalLabel').text('Add Model');

    $.get(`${API_BASE}/brands`, function(brands) {
        const select = $('#modelBrand');
        select.empty().append('<option value="">Select Brand</option>');
        brands.forEach(brand => {
            select.append(`<option value="${brand.id}">${brand.name}</option>`);
        });
    });

    // Add image preview handler
    $('#modelImage').off('change').on('change', function(e) {
        const file = e.target.files[0];
        if (file) {
            // Validate file size (max 5MB for base64)
            if (file.size > 5 * 1024 * 1024) {
                alert('Image size must be less than 5MB');
                $(this).val('');
                $('#modelImagePreview').hide();
                return;
            }

            const reader = new FileReader();
            reader.onload = function(e) {
                $('#modelImagePreviewImg').attr('src', e.target.result);
                $('#modelImagePreview').show();
            };
            reader.readAsDataURL(file);
        } else {
            $('#modelImagePreview').hide();
        }
    });

    const modal = new bootstrap.Modal($('#modelModal'));
    modal.show();
}

function editModel(id, name, brandId, description, imageData) {
    $('#modelId').val(id);
    $('#modelName').val(name);
    $('#modelDescription').val(description);
    $('#modelModalLabel').text('Edit Model');

    // Show current image if exists
    if (imageData) {
        $('#modelImagePreviewImg').attr('src', imageData);
        $('#modelImagePreview').show();
    } else {
        $('#modelImagePreview').hide();
    }

    $.get(`${API_BASE}/brands`, function(brands) {
        const select = $('#modelBrand');
        select.empty().append('<option value="">Select Brand</option>');
        brands.forEach(brand => {
            select.append(`<option value="${brand.id}" ${brand.id === brandId ? 'selected' : ''}>${brand.name}</option>`);
        });
    });

    // Add image preview handler
    $('#modelImage').off('change').on('change', function(e) {
        const file = e.target.files[0];
        if (file) {
            // Validate file size (max 5MB for base64)
            if (file.size > 5 * 1024 * 1024) {
                alert('Image size must be less than 5MB');
                $(this).val('');
                return;
            }

            const reader = new FileReader();
            reader.onload = function(e) {
                $('#modelImagePreviewImg').attr('src', e.target.result);
                $('#modelImagePreview').show();
            };
            reader.readAsDataURL(file);
        }
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
    const imageFile = $('#modelImage')[0].files[0];
    const modelName = $('#modelName').val();
    const brandId = $('#modelBrand').val();

    // Validate required fields
    if (!modelName || !modelName.trim()) {
        alert('Please enter a model name');
        return;
    }

    if (!brandId) {
        alert('Please select a brand');
        return;
    }

    // Function to send data
    const sendData = (imageData) => {
        const data = {
            name: modelName.trim(),
            brand_id: brandId,
            description: $('#modelDescription').val(),
            image_data: imageData
        };

        const url = id ? `${API_BASE}/models/${id}` : `${API_BASE}/models`;
        const method = id ? 'PUT' : 'POST';

        $.ajax({
            url: url,
            method: method,
            contentType: 'application/json',
            data: JSON.stringify(data),
            success: function() {
                alert('Model saved successfully');
                bootstrap.Modal.getInstance($('#modelModal')).hide();
                loadModels();
            },
            error: function(xhr) {
                const errorMsg = xhr.responseJSON?.error || 'Failed to save model. Please try again.';
                alert('Error: ' + errorMsg);
                console.error('Save model error:', xhr);
            }
        });
    };

    // If new image file is selected, convert to base64
    if (imageFile) {
        // Validate file size (max 5MB)
        if (imageFile.size > 5 * 1024 * 1024) {
            alert('Image size must be less than 5MB');
            return;
        }

        const reader = new FileReader();
        reader.onload = function(e) {
            sendData(e.target.result);
        };
        reader.onerror = function() {
            alert('Error reading image file. Please try again.');
        };
        reader.readAsDataURL(imageFile);
    } else {
        // No new image, use existing preview image or empty
        const existingImage = $('#modelImagePreviewImg').attr('src');
        const imageData = existingImage && !existingImage.includes('placeholder') ? existingImage : '';
        sendData(imageData);
    }
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

        let paymentBadge = 'danger';
        if (grn.payment_status === 'paid') paymentBadge = 'success';
        else if (grn.payment_status === 'partial') paymentBadge = 'warning';

        let content = `
            <div class="mb-3">
                <h6>GRN Details</h6>
                <p><strong>GRN Number:</strong> ${grn.grn_number}</p>
                <p><strong>PO Number:</strong> ${grn.po_number || '-'}</p>
                <p><strong>Supplier:</strong> ${grn.supplier_name || '-'}</p>
                <p><strong>Received Date:</strong> ${receivedDate}</p>
                <p><strong>Payment Status:</strong> <span class="badge bg-${grn.payment_status === 'paid' ? 'success' : grn.payment_status === 'partial' ? 'warning' : 'danger'}">${grn.payment_status || 'unpaid'}</span></p>
                <p><strong>Storage Location:</strong> ${grn.storage_location || '-'}</p>
                <p><strong>Created By:</strong> ${grn.created_by || 'System'}</p>
                <p><strong>Total Items:</strong> ${grn.total_items || 0}</p>
                <p><strong>Total Quantity:</strong> ${grn.total_quantity || 0}</p>
                ${grn.notes ? `<p><strong>Notes:</strong> ${grn.notes}</p>` : ''}
            </div>
            <h6>Items Received</h6>
            <table class="table table-sm table-bordered">
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
                    <td>${item.quantity_damaged || 0}${item.damage_reason ? `<br><small class="text-muted">(${item.damage_reason})</small>` : ''}</td>
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
    }).fail(function(xhr) {
        const errorMsg = xhr.responseJSON?.error || 'Failed to load GRN details.';
        alert('Error: ' + errorMsg);
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

function loadStockAdjustment() {
    $('#content-area').html(`
        <div class="page-header">
            <h2><i class="bi bi-box-arrow-in-down"></i> Stock Adjustment</h2>
            <p class="text-muted">Add stock to existing products with optional IMEI tracking</p>
        </div>

        <ul class="nav nav-tabs mb-4" role="tablist">
            <li class="nav-item" role="presentation">
                <button class="nav-link active" id="adjust-tab" data-bs-toggle="tab" data-bs-target="#adjust-panel" type="button">
                    <i class="bi bi-box-arrow-in-down"></i> Adjust Stock
                </button>
            </li>
            <li class="nav-item" role="presentation">
                <button class="nav-link" id="history-tab" data-bs-toggle="tab" data-bs-target="#history-panel" type="button">
                    <i class="bi bi-clock-history"></i> Adjustment History
                </button>
            </li>
        </ul>

        <div class="tab-content">
            <div class="tab-pane fade show active" id="adjust-panel" role="tabpanel">
                <div class="row justify-content-center">
                    <div class="col-md-10">
                        <div class="card">
                            <div class="card-header bg-primary text-white">
                                <h5 class="mb-0">Adjust Stock</h5>
                            </div>
                            <div class="card-body">
                        <div class="mb-4">
                            <label class="form-label fw-bold">Select Product</label>
                            <select class="form-select form-select-lg" id="adjustmentProduct">
                                <option value="">-- Choose a product --</option>
                            </select>
                        </div>

                        <div id="currentStockInfo" class="alert alert-info d-none mb-4">
                            <h6 class="alert-heading">Current Stock Information</h6>
                            <div class="row">
                                <div class="col-md-4">
                                    <strong>Product:</strong>
                                    <div id="currentProductName" class="fs-5">-</div>
                                </div>
                                <div class="col-md-4">
                                    <strong>Current Stock:</strong>
                                    <div id="currentStockQty" class="fs-3 text-primary">0</div>
                                </div>
                                <div class="col-md-4">
                                    <strong>SKU:</strong>
                                    <div id="currentProductSku" class="fs-5">-</div>
                                </div>
                            </div>
                        </div>

                        <div id="adjustmentForm" class="d-none">
                            <div class="row">
                                <div class="col-md-6 mb-3">
                                    <label class="form-label fw-bold">Quantity to Add</label>
                                    <input type="number" class="form-control form-control-lg" id="adjustmentQuantity" min="1" value="" placeholder="Enter quantity to add">
                                    <small class="text-muted">Enter how many units you want to add to stock</small>
                                </div>
                                <div class="col-md-6 mb-3">
                                    <label class="form-label fw-bold">New Stock (Preview)</label>
                                    <input type="text" class="form-control form-control-lg bg-light" id="newStockPreview" readonly placeholder="0">
                                    <small class="text-muted">This will be the new stock level</small>
                                </div>
                            </div>

                            <div class="mb-3">
                                <div class="form-check form-switch">
                                    <input class="form-check-input" type="checkbox" id="trackIMEI">
                                    <label class="form-check-label fw-bold" for="trackIMEI">
                                        <i class="bi bi-upc-scan"></i> Track IMEI Numbers for Each Item
                                    </label>
                                </div>
                                <small class="text-muted">Enable this to enter individual IMEI numbers for mobile devices</small>
                            </div>

                            <div id="imeiFieldsContainer" class="d-none mb-3">
                                <div class="card">
                                    <div class="card-header bg-light">
                                        <div class="d-flex justify-content-between align-items-center">
                                            <h6 class="mb-0"><i class="bi bi-list-ol"></i> IMEI Numbers (<span id="imeiCount">0</span>/<span id="imeiTotal">0</span>)</h6>
                                            <button type="button" class="btn btn-sm btn-outline-secondary" onclick="autoFillIMEI()">
                                                <i class="bi bi-magic"></i> Auto-generate Test IMEIs
                                            </button>
                                        </div>
                                    </div>
                                    <div class="card-body" style="max-height: 400px; overflow-y: auto;">
                                        <div id="imeiFields" class="row g-2"></div>
                                    </div>
                                </div>
                            </div>

                            <div class="mb-3">
                                <label class="form-label fw-bold">Notes (Optional)</label>
                                <textarea class="form-control" id="adjustmentNotes" rows="3" placeholder="Add any notes about this adjustment (e.g., 'Received from supplier', 'Return from customer')"></textarea>
                            </div>

                            <div class="d-grid gap-2">
                                <button class="btn btn-success btn-lg" onclick="submitStockAdjustment()">
                                    <i class="bi bi-check-circle"></i> Update Stock
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <div class="tab-pane fade" id="history-panel" role="tabpanel">
            <div class="card">
                <div class="card-header bg-secondary text-white d-flex justify-content-between align-items-center">
                    <h5 class="mb-0">Stock Adjustment History</h5>
                    <button class="btn btn-sm btn-light" onclick="loadAdjustmentHistory()">
                        <i class="bi bi-arrow-clockwise"></i> Refresh
                    </button>
                </div>
                <div class="card-body">
                    <div class="table-responsive">
                        <table class="table table-hover" id="adjustmentHistoryTable">
                            <thead>
                                <tr>
                                    <th>#</th>
                                    <th>Date & Time</th>
                                    <th>Product</th>
                                    <th>SKU</th>
                                    <th>Quantity Added</th>
                                    <th>IMEI Count</th>
                                    <th>Notes</th>
                                    <th>Actions</th>
                                </tr>
                            </thead>
                            <tbody id="adjustmentHistoryBody">
                                <tr>
                                    <td colspan="8" class="text-center">
                                        <div class="spinner-border text-primary" role="status">
                                            <span class="visually-hidden">Loading...</span>
                                        </div>
                                    </td>
                                </tr>
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
        </div>
    </div>
    `);

    loadProductsForAdjustment();
    loadAdjustmentHistory();

    $('#adjustmentProduct').on('change', function() {
        const productId = $(this).val();
        if (productId) {
            showCurrentStock(productId);
        } else {
            $('#currentStockInfo').addClass('d-none');
            $('#adjustmentForm').addClass('d-none');
        }
    });

    $('#adjustmentQuantity').on('input', function() {
        updateStockPreview();
        if ($('#trackIMEI').is(':checked')) {
            generateIMEIFields();
        }
    });

    $('#trackIMEI').on('change', function() {
        if ($(this).is(':checked')) {
            const quantity = parseInt($('#adjustmentQuantity').val()) || 0;
            if (quantity > 0) {
                generateIMEIFields();
                $('#imeiFieldsContainer').removeClass('d-none');
            } else {
                alert('Please enter a quantity first');
                $(this).prop('checked', false);
            }
        } else {
            $('#imeiFieldsContainer').addClass('d-none');
        }
    });
}

function loadProductsForAdjustment() {
    $.get(`${API_BASE}/products`, function(products) {
        const select = $('#adjustmentProduct');
        select.empty().append('<option value="">-- Choose a product --</option>');

        products.filter(p => p.status === 'active').forEach(product => {
            select.append(`<option value="${product.id}" data-stock="${product.current_stock}" data-name="${product.name}" data-sku="${product.sku || 'N/A'}">
                ${product.name} - Current Stock: ${product.current_stock}
            </option>`);
        });
    });
}

function showCurrentStock(productId) {
    $.get(`${API_BASE}/products/${productId}`, function(product) {
        $('#currentProductName').text(product.name);
        $('#currentStockQty').text(product.current_stock);
        $('#currentProductSku').text(product.sku || 'N/A');
        $('#currentStockInfo').removeClass('d-none');
        $('#adjustmentForm').removeClass('d-none');
        $('#adjustmentQuantity').val('');
        $('#newStockPreview').val('');
        $('#adjustmentNotes').val('');
    });
}

function updateStockPreview() {
    const select = $('#adjustmentProduct');
    const currentStock = parseInt(select.find('option:selected').data('stock')) || 0;
    const addQuantity = parseInt($('#adjustmentQuantity').val()) || 0;
    const newStock = currentStock + addQuantity;
    $('#newStockPreview').val(newStock);
}

function generateIMEIFields() {
    const quantity = parseInt($('#adjustmentQuantity').val()) || 0;
    const container = $('#imeiFields');
    container.empty();

    if (quantity <= 0) {
        return;
    }

    $('#imeiTotal').text(quantity);

    for (let i = 1; i <= quantity; i++) {
        container.append(`
            <div class="col-md-6 col-lg-4 mb-2">
                <label class="form-label small mb-1">Item #${i}</label>
                <input type="text" class="form-control imei-input" id="imei_${i}"
                       placeholder="Enter IMEI" maxlength="15"
                       data-index="${i}" pattern="[0-9]{15}">
            </div>
        `);
    }

    // Add input event to count filled IMEIs
    $('.imei-input').on('input', function() {
        const filled = $('.imei-input').filter(function() {
            return $(this).val().trim() !== '';
        }).length;
        $('#imeiCount').text(filled);

        // Validate IMEI format (15 digits)
        const value = $(this).val().replace(/\D/g, '');
        if (value.length > 15) {
            $(this).val(value.substring(0, 15));
        } else {
            $(this).val(value);
        }
    });
}

function autoFillIMEI() {
    const quantity = parseInt($('#adjustmentQuantity').val()) || 0;
    if (quantity <= 0) return;

    if (!confirm('This will generate test IMEI numbers. Use this only for testing purposes.\n\nDo you want to continue?')) {
        return;
    }

    // Generate random but valid-looking IMEI numbers for testing
    for (let i = 1; i <= quantity; i++) {
        const timestamp = Date.now().toString().substring(3);
        const random = Math.floor(Math.random() * 10000).toString().padStart(4, '0');
        const testIMEI = (timestamp + random + i.toString().padStart(2, '0')).substring(0, 15);
        $(`#imei_${i}`).val(testIMEI);
    }

    $('#imeiCount').text(quantity);
}

function collectIMEINumbers() {
    const imeiList = [];
    const quantity = parseInt($('#adjustmentQuantity').val()) || 0;

    for (let i = 1; i <= quantity; i++) {
        const imei = $(`#imei_${i}`).val().trim();
        if (imei) {
            if (imei.length !== 15 || !/^\d{15}$/.test(imei)) {
                throw new Error(`Item #${i}: IMEI must be exactly 15 digits`);
            }
            if (imeiList.includes(imei)) {
                throw new Error(`Item #${i}: Duplicate IMEI number detected (${imei})`);
            }
            imeiList.push(imei);
        }
    }

    return imeiList;
}

function submitStockAdjustment() {
    const productId = $('#adjustmentProduct').val();
    const quantity = parseInt($('#adjustmentQuantity').val());
    const notes = $('#adjustmentNotes').val();
    const trackIMEI = $('#trackIMEI').is(':checked');

    if (!productId) {
        alert('Please select a product');
        return;
    }

    if (!quantity || quantity <= 0) {
        alert('Please enter a valid quantity to add');
        return;
    }

    let imeiNumbers = [];
    if (trackIMEI) {
        try {
            imeiNumbers = collectIMEINumbers();

            if (imeiNumbers.length < quantity) {
                if (!confirm(`You've only entered ${imeiNumbers.length} out of ${quantity} IMEI numbers.\n\nDo you want to continue without all IMEI numbers?`)) {
                    return;
                }
            }
        } catch (error) {
            alert('IMEI Validation Error: ' + error.message);
            return;
        }
    }

    const productName = $('#adjustmentProduct option:selected').data('name');
    const currentStock = parseInt($('#adjustmentProduct option:selected').data('stock'));
    const newStock = currentStock + quantity;

    let confirmMessage = `Add ${quantity} units to ${productName}?\n\nCurrent Stock: ${currentStock}\nNew Stock: ${newStock}`;
    if (trackIMEI && imeiNumbers.length > 0) {
        confirmMessage += `\n\nIMEI Numbers: ${imeiNumbers.length} recorded`;
    }

    if (!confirm(confirmMessage)) {
        return;
    }

    const requestData = {
        product_id: productId,
        quantity: quantity,
        notes: notes
    };

    if (trackIMEI && imeiNumbers.length > 0) {
        requestData.imei_numbers = imeiNumbers;
    }

    $.ajax({
        url: `${API_BASE}/stock-adjustment`,
        method: 'POST',
        contentType: 'application/json',
        data: JSON.stringify(requestData),
        success: function(response) {
            if (response.success) {
                let message = `Stock updated successfully!\n\n${response.product_name}\nPrevious: ${response.previous_stock}\nAdded: +${response.added_quantity}\nNew Stock: ${response.new_stock}`;
                if (trackIMEI && imeiNumbers.length > 0) {
                    message += `\n\nIMEI Numbers Recorded: ${imeiNumbers.length}`;
                }
                alert(message);
                loadStockAdjustment();
            } else {
                alert('Error: ' + (response.error || 'Failed to update stock'));
            }
        },
        error: function(xhr) {
            alert('Error: ' + (xhr.responseJSON?.error || 'Failed to update stock'));
        }
    });
}

function loadAdjustmentHistory() {
    $.get(`${API_BASE}/stock-adjustments`, function(adjustments) {
        const tbody = $('#adjustmentHistoryBody');
        tbody.empty();

        if (adjustments.length === 0) {
            tbody.append(`
                <tr>
                    <td colspan="8" class="text-center text-muted">
                        <i class="bi bi-inbox"></i> No stock adjustments found
                    </td>
                </tr>
            `);
            return;
        }

        adjustments.forEach((adj, index) => {
            const date = new Date(adj.created_at);
            const formattedDate = date.toLocaleString();
            const imeiText = adj.imei_count > 0 ? `<span class="badge bg-info">${adj.imei_count} IMEI</span>` : '-';
            const notes = adj.notes || '-';

            tbody.append(`
                <tr>
                    <td>${index + 1}</td>
                    <td>${formattedDate}</td>
                    <td>${adj.product_name || 'N/A'}</td>
                    <td>${adj.sku || 'N/A'}</td>
                    <td><span class="badge bg-success">+${adj.quantity}</span></td>
                    <td>${imeiText}</td>
                    <td>${notes}</td>
                    <td>
                        <button class="btn btn-sm btn-info" onclick="viewAdjustmentDetail(${adj.id})" title="View Details">
                            <i class="bi bi-eye"></i>
                        </button>
                        <button class="btn btn-sm btn-danger" onclick="deleteAdjustment(${adj.id}, '${adj.product_name}')" title="Delete">
                            <i class="bi bi-trash"></i>
                        </button>
                    </td>
                </tr>
            `);
        });
    }).fail(function(xhr) {
        $('#adjustmentHistoryBody').html(`
            <tr>
                <td colspan="8" class="text-center text-danger">
                    <i class="bi bi-exclamation-triangle"></i> Failed to load adjustment history
                </td>
            </tr>
        `);
    });
}

function viewAdjustmentDetail(id) {
    $.get(`${API_BASE}/stock-adjustments/${id}`, function(adj) {
        const date = new Date(adj.created_at);
        const formattedDate = date.toLocaleString();

        let imeiSection = '';
        if (adj.imei_numbers && adj.imei_numbers.length > 0) {
            imeiSection = `
                <div class="mt-4">
                    <h6><i class="bi bi-upc-scan"></i> IMEI Numbers Recorded (${adj.imei_numbers.length})</h6>
                    <div class="table-responsive">
                        <table class="table table-sm table-hover">
                            <thead>
                                <tr>
                                    <th>#</th>
                                    <th>IMEI Number</th>
                                    <th>Status</th>
                                    <th>Added On</th>
                                </tr>
                            </thead>
                            <tbody>
            `;

            adj.imei_numbers.forEach((imei, index) => {
                const statusBadge = imei.status === 'available' || imei.status === 'in_stock'
                    ? '<span class="badge bg-success">Available</span>'
                    : '<span class="badge bg-danger">Sold</span>';
                const imeiDate = imei.created_at ? new Date(imei.created_at).toLocaleDateString() : 'N/A';

                imeiSection += `
                    <tr>
                        <td>${index + 1}</td>
                        <td><code>${imei.imei}</code></td>
                        <td>${statusBadge}</td>
                        <td>${imeiDate}</td>
                    </tr>
                `;
            });

            imeiSection += `
                            </tbody>
                        </table>
                    </div>
                </div>
            `;
        } else {
            imeiSection = `
                <div class="mt-4">
                    <h6><i class="bi bi-upc-scan"></i> IMEI Numbers</h6>
                    <div class="alert alert-info mb-0">
                        <i class="bi bi-info-circle"></i> No IMEI numbers were recorded for this stock adjustment.
                    </div>
                </div>
            `;
        }

        const content = `
            <div class="row">
                <div class="col-md-6">
                    <p><strong><i class="bi bi-box"></i> Product:</strong> ${adj.product_name}</p>
                    <p><strong><i class="bi bi-tag"></i> SKU:</strong> ${adj.sku || 'N/A'}</p>
                    <p><strong><i class="bi bi-stack"></i> Current Stock:</strong> <span class="badge bg-primary">${adj.current_stock}</span></p>
                </div>
                <div class="col-md-6">
                    <p><strong><i class="bi bi-calendar"></i> Date:</strong> ${formattedDate}</p>
                    <p><strong><i class="bi bi-plus-circle"></i> Quantity Added:</strong> <span class="badge bg-success">+${adj.quantity}</span></p>
                    <p><strong><i class="bi bi-pencil"></i> Notes:</strong> ${adj.notes || '<em class="text-muted">None</em>'}</p>
                </div>
            </div>
            <hr>
            ${imeiSection}
        `;

        $('#adjustmentDetailContent').html(content);
        const modal = new bootstrap.Modal($('#adjustmentDetailModal'));
        modal.show();
    }).fail(function(xhr) {
        alert('Error: Failed to load adjustment details');
    });
}

function deleteAdjustment(id, productName) {
    if (!confirm(`Are you sure you want to delete this stock adjustment for ${productName}?\n\nThis will reverse the stock change. This action cannot be undone.`)) {
        return;
    }

    $.ajax({
        url: `${API_BASE}/stock-adjustments/${id}`,
        method: 'DELETE',
        success: function(response) {
            if (response.success) {
                alert('Stock adjustment deleted successfully. Stock has been reversed.');
                loadAdjustmentHistory();
            } else {
                alert('Error: ' + (response.error || 'Failed to delete adjustment'));
            }
        },
        error: function(xhr) {
            const errorMsg = xhr.responseJSON?.error || 'Failed to delete adjustment';
            alert('Error: ' + errorMsg);
        }
    });
}

let quickOrderItems = [];

function loadQuickOrder() {
    quickOrderItems = [];

    $('#content-area').html(`
        <div class="page-header">
            <h2><i class="bi bi-bag-plus"></i> Quick Order</h2>
            <p class="text-muted">Simple order entry - Select products and quantities</p>
        </div>

        <div class="row">
            <div class="col-md-8">
                <div class="card mb-3">
                    <div class="card-header">
                        <h5 class="mb-0">Add Items to Order</h5>
                    </div>
                    <div class="card-body">
                        <div class="row">
                            <div class="col-md-6 mb-3">
                                <label class="form-label">Select Product</label>
                                <select class="form-select" id="quickOrderProduct">
                                    <option value="">-- Choose a product --</option>
                                </select>
                            </div>
                            <div class="col-md-3 mb-3">
                                <label class="form-label">Quantity</label>
                                <input type="number" class="form-control" id="quickOrderQuantity" min="1" value="1">
                            </div>
                            <div class="col-md-3 mb-3">
                                <label class="form-label">&nbsp;</label>
                                <button class="btn btn-primary w-100" onclick="addQuickOrderItem()">
                                    <i class="bi bi-plus-circle"></i> Add Item
                                </button>
                            </div>
                        </div>
                        <div id="productInfo" class="alert alert-info d-none">
                            <strong>Product Info:</strong>
                            <div id="productInfoContent"></div>
                        </div>
                    </div>
                </div>

                <div class="card">
                    <div class="card-header">
                        <h5 class="mb-0">Order Items</h5>
                    </div>
                    <div class="card-body">
                        <div class="table-responsive">
                            <table class="table table-bordered" id="quickOrderItemsTable">
                                <thead>
                                    <tr>
                                        <th>Product</th>
                                        <th>Quantity</th>
                                        <th>Unit Price</th>
                                        <th>Total</th>
                                        <th>Action</th>
                                    </tr>
                                </thead>
                                <tbody></tbody>
                                <tfoot>
                                    <tr class="table-primary">
                                        <td colspan="3" class="text-end"><strong>Total Amount:</strong></td>
                                        <td><strong id="orderTotalAmount">$0.00</strong></td>
                                        <td></td>
                                    </tr>
                                </tfoot>
                            </table>
                        </div>
                        <div id="emptyOrderMessage" class="text-center text-muted py-4">
                            No items added yet. Select products above to start your order.
                        </div>
                    </div>
                </div>
            </div>

            <div class="col-md-4">
                <div class="card">
                    <div class="card-header bg-success text-white">
                        <h5 class="mb-0">Submit Order</h5>
                    </div>
                    <div class="card-body">
                        <div class="mb-3">
                            <label class="form-label">Notes (Optional)</label>
                            <textarea class="form-control" id="quickOrderNotes" rows="3" placeholder="Add any notes about this order..."></textarea>
                        </div>
                        <button class="btn btn-success w-100" onclick="submitQuickOrder()">
                            <i class="bi bi-check-circle"></i> Submit Order
                        </button>
                    </div>
                    <div class="card-footer">
                        <small class="text-muted">
                            <i class="bi bi-info-circle"></i> Stock will be automatically reduced when order is submitted
                        </small>
                    </div>
                </div>
            </div>
        </div>
    `);

    loadProductsForQuickOrder();
    updateQuickOrderTable();

    $('#quickOrderProduct').on('change', function() {
        const productId = $(this).val();
        if (productId) {
            showProductInfo(productId);
        } else {
            $('#productInfo').addClass('d-none');
        }
    });
}

function loadProductsForQuickOrder() {
    $.get(`${API_BASE}/products`, function(products) {
        const select = $('#quickOrderProduct');
        select.empty().append('<option value="">-- Choose a product --</option>');

        products.filter(p => p.status === 'active' && p.current_stock > 0).forEach(product => {
            select.append(`<option value="${product.id}" data-stock="${product.current_stock}" data-price="${product.selling_price}" data-name="${product.name}">
                ${product.name} - Stock: ${product.current_stock} - $${parseFloat(product.selling_price || 0).toFixed(2)}
            </option>`);
        });
    });
}

function showProductInfo(productId) {
    $.get(`${API_BASE}/products/${productId}`, function(product) {
        const content = `
            <div class="row">
                <div class="col-6"><strong>Available Stock:</strong></div>
                <div class="col-6">${product.current_stock} units</div>
            </div>
            <div class="row">
                <div class="col-6"><strong>Price:</strong></div>
                <div class="col-6">$${parseFloat(product.selling_price || 0).toFixed(2)}</div>
            </div>
            <div class="row">
                <div class="col-6"><strong>SKU:</strong></div>
                <div class="col-6">${product.sku || 'N/A'}</div>
            </div>
        `;
        $('#productInfoContent').html(content);
        $('#productInfo').removeClass('d-none');
    });
}

function addQuickOrderItem() {
    const select = $('#quickOrderProduct');
    const productId = select.val();
    const quantity = parseInt($('#quickOrderQuantity').val()) || 1;

    if (!productId) {
        alert('Please select a product');
        return;
    }

    if (quantity <= 0) {
        alert('Please enter a valid quantity');
        return;
    }

    const option = select.find('option:selected');
    const productName = option.data('name');
    const stock = parseInt(option.data('stock'));
    const price = parseFloat(option.data('price'));

    const existingItem = quickOrderItems.find(item => item.product_id === parseInt(productId));
    const currentQty = existingItem ? existingItem.quantity : 0;

    if (currentQty + quantity > stock) {
        alert(`Insufficient stock! Available: ${stock}, Already in order: ${currentQty}, Requested: ${quantity}`);
        return;
    }

    if (existingItem) {
        existingItem.quantity += quantity;
    } else {
        quickOrderItems.push({
            product_id: parseInt(productId),
            product_name: productName,
            quantity: quantity,
            price: price
        });
    }

    $('#quickOrderQuantity').val(1);
    select.val('');
    $('#productInfo').addClass('d-none');
    updateQuickOrderTable();
}

function removeQuickOrderItem(index) {
    quickOrderItems.splice(index, 1);
    updateQuickOrderTable();
}

function updateQuickOrderTable() {
    const tbody = $('#quickOrderItemsTable tbody');
    tbody.empty();

    if (quickOrderItems.length === 0) {
        $('#emptyOrderMessage').show();
        $('#quickOrderItemsTable').hide();
        return;
    }

    $('#emptyOrderMessage').hide();
    $('#quickOrderItemsTable').show();

    let totalAmount = 0;

    quickOrderItems.forEach((item, index) => {
        const itemTotal = item.quantity * item.price;
        totalAmount += itemTotal;

        tbody.append(`
            <tr>
                <td>${item.product_name}</td>
                <td>${item.quantity}</td>
                <td>$${item.price.toFixed(2)}</td>
                <td>$${itemTotal.toFixed(2)}</td>
                <td>
                    <button class="btn btn-sm btn-danger" onclick="removeQuickOrderItem(${index})">
                        <i class="bi bi-trash"></i>
                    </button>
                </td>
            </tr>
        `);
    });

    $('#orderTotalAmount').text('$' + totalAmount.toFixed(2));
}

function submitQuickOrder() {
    if (quickOrderItems.length === 0) {
        alert('Please add at least one item to the order');
        return;
    }

    if (!confirm(`Submit order with ${quickOrderItems.length} item(s)?`)) {
        return;
    }

    const orderData = {
        items: quickOrderItems,
        notes: $('#quickOrderNotes').val()
    };

    $.ajax({
        url: `${API_BASE}/quick-orders`,
        method: 'POST',
        contentType: 'application/json',
        data: JSON.stringify(orderData),
        success: function(response) {
            if (response.success) {
                alert(`Order ${response.order_number} created successfully!`);
                loadQuickOrder();
            } else {
                alert('Error: ' + (response.error || 'Failed to create order'));
            }
        },
        error: function(xhr) {
            alert('Error: ' + (xhr.responseJSON?.error || 'Failed to create order'));
        }
    });
}

function loadPOS() {
    posCart = [];
    
    $('#content-area').html(`
        <div class="page-header">
            <h2><i class="bi bi-calculator"></i> Point of Sale (POS)</h2>
        </div>

        <div class="row">
            <!-- Left Panel - Product Search & Cart -->
            <div class="col-md-8">
                <!-- Transaction Type -->
                <div class="card mb-3">
                    <div class="card-header bg-primary text-white">
                        <i class="bi bi-cart"></i> Transaction Type
                    </div>
                    <div class="card-body">
                        <div class="btn-group w-100" role="group">
                            <input type="radio" class="btn-check" name="transactionType" id="typeSale" value="sale" checked>
                            <label class="btn btn-outline-success" for="typeSale">
                                <i class="bi bi-cart-check"></i> Sale
                            </label>

                            <input type="radio" class="btn-check" name="transactionType" id="typeReturn" value="return">
                            <label class="btn btn-outline-warning" for="typeReturn">
                                <i class="bi bi-arrow-counterclockwise"></i> Return
                            </label>

                            <input type="radio" class="btn-check" name="transactionType" id="typeExchange" value="exchange">
                            <label class="btn btn-outline-info" for="typeExchange">
                                <i class="bi bi-arrow-left-right"></i> Exchange
                            </label>
                        </div>
                    </div>
                </div>

                <!-- Product Search -->
                <div class="card mb-3">
                    <div class="card-header bg-primary text-white">
                        <i class="bi bi-search"></i> Product Search
                    </div>
                    <div class="card-body">
                        <input type="text" class="form-control form-control-lg" id="posProductSearch" placeholder="Search by product name, SKU, or IMEI...">
                        <div id="posSearchResults" class="mt-3"></div>
                    </div>
                </div>

                <!-- Shopping Cart -->
                <div class="card">
                    <div class="card-header bg-success text-white d-flex justify-content-between align-items-center">
                        <span><i class="bi bi-cart"></i> Shopping Cart (<span id="cartItemCount">0</span> items)</span>
                        <button class="btn btn-sm btn-light" onclick="clearPOSCart()">
                            <i class="bi bi-trash"></i> Clear Cart
                        </button>
                    </div>
                    <div class="card-body">
                        <div class="table-responsive">
                            <table class="table table-hover" id="posCartTable">
                                <thead>
                                    <tr>
                                        <th>Product</th>
                                        <th>Price</th>
                                        <th>Qty</th>
                                        <th>IMEI</th>
                                        <th>Total</th>
                                        <th>Action</th>
                                    </tr>
                                </thead>
                                <tbody id="posCartBody">
                                    <tr>
                                        <td colspan="6" class="text-center text-muted">Cart is empty</td>
                                    </tr>
                                </tbody>
                            </table>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Right Panel - Bill Summary -->
            <div class="col-md-4">
                <!-- Customer Information -->
                <div class="card mb-3">
                    <div class="card-header bg-info text-white">
                        <i class="bi bi-person"></i> Customer Information (Optional)
                    </div>
                    <div class="card-body">
                        <div class="mb-2">
                            <label class="form-label">Customer Name</label>
                            <input type="text" class="form-control" id="posCustomerName" placeholder="Customer name">
                        </div>
                        <div class="mb-2">
                            <label class="form-label">Phone Number</label>
                            <input type="text" class="form-control" id="posCustomerPhone" placeholder="Phone number">
                        </div>
                        <div class="mb-2">
                            <label class="form-label">Email</label>
                            <input type="email" class="form-control" id="posCustomerEmail" placeholder="Email">
                        </div>
                    </div>
                </div>

                <!-- Bill Summary -->
                <div class="card mb-3">
                    <div class="card-header bg-dark text-white">
                        <i class="bi bi-receipt"></i> Bill Summary
                    </div>
                    <div class="card-body">
                        <div class="d-flex justify-content-between mb-2">
                            <span>Transaction Date:</span>
                            <strong>${new Date().toLocaleDateString()}</strong>
                        </div>
                        <div class="d-flex justify-content-between mb-2">
                            <span>Transaction Time:</span>
                            <strong id="posTransactionTime">${new Date().toLocaleTimeString()}</strong>
                        </div>
                        <hr>
                        <div class="d-flex justify-content-between mb-2">
                            <span>Subtotal:</span>
                            <strong id="posSubtotal">$0.00</strong>
                        </div>
                        <div class="row mb-2">
                            <div class="col-7">
                                <label class="form-label">Discount (%):</label>
                            </div>
                            <div class="col-5">
                                <input type="number" class="form-control form-control-sm" id="posDiscountPercent" value="0" min="0" max="100" step="0.1">
                            </div>
                        </div>
                        <div class="d-flex justify-content-between mb-2 text-danger">
                            <span>Discount Amount:</span>
                            <strong id="posDiscountAmount">-$0.00</strong>
                        </div>
                        <div class="row mb-2">
                            <div class="col-7">
                                <label class="form-label">Tax (%):</label>
                            </div>
                            <div class="col-5">
                                <input type="number" class="form-control form-control-sm" id="posTaxPercent" value="0" min="0" max="100" step="0.1">
                            </div>
                        </div>
                        <div class="d-flex justify-content-between mb-2">
                            <span>Tax Amount:</span>
                            <strong id="posTaxAmount">+$0.00</strong>
                        </div>
                        <hr>
                        <div class="d-flex justify-content-between mb-3">
                            <h5>Total:</h5>
                            <h5 class="text-success" id="posTotal">$0.00</h5>
                        </div>
                    </div>
                </div>

                <!-- Payment Method -->
                <div class="card mb-3">
                    <div class="card-header bg-warning text-dark">
                        <i class="bi bi-credit-card"></i> Payment Method
                    </div>
                    <div class="card-body">
                        <select class="form-select" id="posPaymentMethod">
                            <option value="cash">Cash</option>
                            <option value="card">Credit/Debit Card</option>
                            <option value="upi">UPI</option>
                            <option value="wallet">Mobile Wallet</option>
                            <option value="bank_transfer">Bank Transfer</option>
                        </select>
                        <div class="mt-2">
                            <label class="form-label">Reference Number (Optional)</label>
                            <input type="text" class="form-control" id="posPaymentReference" placeholder="Transaction reference">
                        </div>
                    </div>
                </div>

                <!-- Complete Sale Button -->
                <button class="btn btn-success btn-lg w-100" onclick="completePOSSale()">
                    <i class="bi bi-check-circle"></i> Complete Sale
                </button>
            </div>
        </div>
    `);

    // Event handlers
    $('#posProductSearch').on('input', debounce(searchPOSProducts, 300));
    $('#posDiscountPercent, #posTaxPercent').on('input', updatePOSCart);
    
    // Update time every second
    setInterval(() => {
        $('#posTransactionTime').text(new Date().toLocaleTimeString());
    }, 1000);
}

function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

function searchPOSProducts() {
    const query = $('#posProductSearch').val();
    
    if (!query || query.length < 2) {
        $('#posSearchResults').empty();
        return;
    }
    
    $.get(`${API_BASE}/pos/products/search?q=${encodeURIComponent(query)}`, function(products) {
        const resultsDiv = $('#posSearchResults');
        resultsDiv.empty();
        
        if (products.length === 0) {
            resultsDiv.html('<div class="alert alert-info">No products found</div>');
            return;
        }
        
        products.forEach(product => {
            const stockBadge = product.current_stock > 0 ? 
                `<span class="badge bg-success">${product.current_stock} in stock</span>` :
                `<span class="badge bg-danger">Out of stock</span>`;
            
            const card = $(`
                <div class="card mb-2 product-search-result">
                    <div class="card-body p-2">
                        <div class="d-flex justify-content-between align-items-center">
                            <div>
                                <strong>${product.name}</strong>
                                <br>
                                <small class="text-muted">${product.brand_name || ''} ${product.model_name || ''}</small>
                                <br>
                                <small class="text-muted">SKU: ${product.sku || 'N/A'}</small>
                            </div>
                            <div class="text-end">
                                <div class="h5 mb-1 text-success">$${parseFloat(product.selling_price).toFixed(2)}</div>
                                ${stockBadge}
                                <br>
                                <button class="btn btn-sm btn-primary mt-1" onclick='addToPOSCart(${JSON.stringify(product)})'>
                                    <i class="bi bi-plus-circle"></i> Add
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            `);
            resultsDiv.append(card);
        });
    });
}

function addToPOSCart(product) {
    if (product.current_stock <= 0) {
        alert('Product is out of stock');
        return;
    }
    
    // Check if product already in cart
    const existingIndex = posCart.findIndex(item => item.product_id === product.id);
    
    if (existingIndex >= 0) {
        if (posCart[existingIndex].quantity < product.current_stock) {
            posCart[existingIndex].quantity++;
        } else {
            alert('Cannot add more than available stock');
            return;
        }
    } else {
        posCart.push({
            product_id: product.id,
            product_name: product.name,
            sku: product.sku,
            unit_price: parseFloat(product.selling_price),
            quantity: 1,
            max_stock: product.current_stock,
            imei_ids: []
        });
    }
    
    updatePOSCart();
    $('#posProductSearch').val('').focus();
    $('#posSearchResults').empty();
}

function updatePOSCart() {
    const tbody = $('#posCartBody');
    tbody.empty();
    
    if (posCart.length === 0) {
        tbody.html('<tr><td colspan="6" class="text-center text-muted">Cart is empty</td></tr>');
        $('#cartItemCount').text(0);
        updatePOSTotals();
        return;
    }
    
    posCart.forEach((item, index) => {
        const total = item.quantity * item.unit_price;
        const imeiInfo = item.imei_ids.length > 0 ? 
            `<span class="badge bg-success">${item.imei_ids.length} selected</span>` :
            '<span class="badge bg-warning">Not selected</span>';
        
        tbody.append(`
            <tr>
                <td>
                    <strong>${item.product_name}</strong>
                    <br><small class="text-muted">${item.sku || ''}</small>
                </td>
                <td>$${item.unit_price.toFixed(2)}</td>
                <td>
                    <div class="input-group input-group-sm" style="width: 120px;">
                        <button class="btn btn-outline-secondary" onclick="updateCartQty(${index}, -1)">-</button>
                        <input type="number" class="form-control text-center" value="${item.quantity}" 
                               onchange="setCartQty(${index}, this.value)" min="1" max="${item.max_stock}">
                        <button class="btn btn-outline-secondary" onclick="updateCartQty(${index}, 1)">+</button>
                    </div>
                </td>
                <td>
                    <button class="btn btn-sm btn-info" onclick="showIMEISelectionModal(${index})">
                        <i class="bi bi-upc-scan"></i> Select
                    </button>
                    <br>${imeiInfo}
                </td>
                <td><strong>$${total.toFixed(2)}</strong></td>
                <td>
                    <button class="btn btn-sm btn-danger" onclick="removeFromPOSCart(${index})">
                        <i class="bi bi-trash"></i>
                    </button>
                </td>
            </tr>
        `);
    });
    
    $('#cartItemCount').text(posCart.length);
    updatePOSTotals();
}

function updateCartQty(index, change) {
    const item = posCart[index];
    const newQty = item.quantity + change;
    
    if (newQty < 1) {
        removeFromPOSCart(index);
        return;
    }
    
    if (newQty > item.max_stock) {
        alert('Cannot exceed available stock');
        return;
    }
    
    item.quantity = newQty;
    
    // Reset IMEI selection if quantity changed
    if (item.imei_ids.length !== newQty) {
        item.imei_ids = [];
    }
    
    updatePOSCart();
}

function setCartQty(index, value) {
    const qty = parseInt(value);
    const item = posCart[index];
    
    if (isNaN(qty) || qty < 1) {
        item.quantity = 1;
    } else if (qty > item.max_stock) {
        item.quantity = item.max_stock;
        alert('Cannot exceed available stock');
    } else {
        item.quantity = qty;
    }
    
    // Reset IMEI selection if quantity changed
    if (item.imei_ids.length !== item.quantity) {
        item.imei_ids = [];
    }
    
    updatePOSCart();
}

function removeFromPOSCart(index) {
    posCart.splice(index, 1);
    updatePOSCart();
}

function clearPOSCart() {
    if (posCart.length === 0) return;
    
    if (confirm('Clear all items from cart?')) {
        posCart = [];
        updatePOSCart();
    }
}

function updatePOSTotals() {
    const subtotal = posCart.reduce((sum, item) => sum + (item.quantity * item.unit_price), 0);
    const discountPercent = parseFloat($('#posDiscountPercent').val()) || 0;
    const taxPercent = parseFloat($('#posTaxPercent').val()) || 0;
    
    const discountAmount = subtotal * (discountPercent / 100);
    const taxableAmount = subtotal - discountAmount;
    const taxAmount = taxableAmount * (taxPercent / 100);
    const total = taxableAmount + taxAmount;
    
    $('#posSubtotal').text('$' + subtotal.toFixed(2));
    $('#posDiscountAmount').text('-$' + discountAmount.toFixed(2));
    $('#posTaxAmount').text('+$' + taxAmount.toFixed(2));
    $('#posTotal').text('$' + total.toFixed(2));
}

function showIMEISelectionModal(cartIndex) {
    const item = posCart[cartIndex];
    currentPOSCartIndex = cartIndex;
    
    // Fetch available IMEIs for this product
    $.get(`${API_BASE}/products/${item.product_id}/imeis?status=available`, function(imeis) {
        $('#imeiProductName').text(item.product_name);
        $('#imeiQuantityRequired').text(item.quantity);
        
        const tbody = $('#imeiSelectionList');
        tbody.empty();
        
        if (imeis.length === 0) {
            tbody.html('<tr><td colspan="3" class="text-center text-muted">No IMEI numbers available for this product</td></tr>');
            $('#confirmImeiSelectionBtn').prop('disabled', true);
        } else {
            $('#confirmImeiSelectionBtn').prop('disabled', false);
            
            imeis.forEach(imei => {
                const checked = item.imei_ids.includes(imei.id) ? 'checked' : '';
                tbody.append(`
                    <tr>
                        <td>
                            <input type="checkbox" class="form-check-input imei-checkbox" 
                                   value="${imei.id}" ${checked}>
                        </td>
                        <td><code>${imei.imei}</code></td>
                        <td><span class="badge bg-success">${imei.status}</span></td>
                    </tr>
                `);
            });
        }
        
        $('#imeiSelectionError').hide();
        const modal = new bootstrap.Modal($('#imeiSelectionModal'));
        modal.show();
    }).fail(function() {
        alert('Failed to load IMEI numbers');
    });
}

function confirmIMEISelection() {
    const item = posCart[currentPOSCartIndex];
    const selectedIMEIs = $('.imei-checkbox:checked').map(function() {
        return parseInt($(this).val());
    }).get();
    
    if (selectedIMEIs.length !== item.quantity) {
        $('#imeiSelectionError').text(`Please select exactly ${item.quantity} IMEI number(s)`).show();
        return;
    }
    
    item.imei_ids = selectedIMEIs;
    bootstrap.Modal.getInstance($('#imeiSelectionModal')).hide();
    updatePOSCart();
}

function completePOSSale() {
    if (posCart.length === 0) {
        alert('Cart is empty');
        return;
    }
    
    const transactionType = $('input[name="transactionType"]:checked').val();
    
    // Validate IMEI selection for all items
    for (let item of posCart) {
        if (item.imei_ids.length > 0 && item.imei_ids.length !== item.quantity) {
            alert(`Please select ${item.quantity} IMEI number(s) for ${item.product_name}`);
            return;
        }
    }
    
    const subtotal = posCart.reduce((sum, item) => sum + (item.quantity * item.unit_price), 0);
    const discountPercent = parseFloat($('#posDiscountPercent').val()) || 0;
    const taxPercent = parseFloat($('#posTaxPercent').val()) || 0;
    
    const saleData = {
        transaction_type: transactionType,
        customer_name: $('#posCustomerName').val(),
        customer_phone: $('#posCustomerPhone').val(),
        customer_email: $('#posCustomerEmail').val(),
        items: posCart,
        discount_percentage: discountPercent,
        tax_percentage: taxPercent,
        payment_method: $('#posPaymentMethod').val(),
        payment_reference: $('#posPaymentReference').val()
    };
    
    if (!confirm(`Complete ${transactionType} transaction for $${$('#posTotal').text().replace('$', '')}?`)) {
        return;
    }
    
    $.ajax({
        url: `${API_BASE}/pos/sales`,
        method: 'POST',
        contentType: 'application/json',
        data: JSON.stringify(saleData),
        success: function(response) {
            alert(`${transactionType.toUpperCase()} completed successfully!\nSale Number: ${response.sale_number}\nTotal: $${Math.abs(response.total_amount).toFixed(2)}`);
            
            // Reset form
            posCart = [];
            updatePOSCart();
            $('#posCustomerName, #posCustomerPhone, #posCustomerEmail, #posPaymentReference').val('');
            $('#posDiscountPercent, #posTaxPercent').val(0);
            $('#posPaymentMethod').val('cash');
            $('input[name="transactionType"][value="sale"]').prop('checked', true);
        },
        error: function(xhr) {
            alert('Error: ' + (xhr.responseJSON?.error || 'Failed to complete sale'));
        }
    });
}

function loadReports() {
    $('#content-area').html(`
        <div class="page-header">
            <h2><i class="bi bi-file-earmark-bar-graph"></i> Business Reports & Analytics</h2>
            <p class="text-muted">Generate comprehensive reports to track your business performance</p>
        </div>

        <!-- Quick Stats Summary -->
        <div class="row mb-4">
            <div class="col-md-3">
                <div class="card bg-primary text-white">
                    <div class="card-body">
                        <h6 class="card-title"><i class="bi bi-calendar-range"></i> Reporting Period</h6>
                        <p class="card-text mb-0">Current Month</p>
                    </div>
                </div>
            </div>
            <div class="col-md-3">
                <div class="card bg-success text-white">
                    <div class="card-body">
                        <h6 class="card-title"><i class="bi bi-file-earmark-check"></i> Available Reports</h6>
                        <p class="card-text mb-0">6 Report Types</p>
                    </div>
                </div>
            </div>
            <div class="col-md-3">
                <div class="card bg-info text-white">
                    <div class="card-body">
                        <h6 class="card-title"><i class="bi bi-download"></i> Export Format</h6>
                        <p class="card-text mb-0">Excel (XLSX)</p>
                    </div>
                </div>
            </div>
            <div class="col-md-3">
                <div class="card bg-warning text-dark">
                    <div class="card-body">
                        <h6 class="card-title"><i class="bi bi-clock-history"></i> Quick Access</h6>
                        <p class="card-text mb-0">Real-time Data</p>
                    </div>
                </div>
            </div>
        </div>

        <!-- Report Categories -->
        <ul class="nav nav-tabs mb-4" id="reportTabs" role="tablist">
            <li class="nav-item" role="presentation">
                <button class="nav-link active" id="sales-reports-tab" data-bs-toggle="tab" data-bs-target="#sales-reports" type="button">
                    <i class="bi bi-cart-check"></i> Sales & Transactions
                </button>
            </li>
            <li class="nav-item" role="presentation">
                <button class="nav-link" id="inventory-reports-tab" data-bs-toggle="tab" data-bs-target="#inventory-reports" type="button">
                    <i class="bi bi-box-seam"></i> Inventory & Stock
                </button>
            </li>
            <li class="nav-item" role="presentation">
                <button class="nav-link" id="procurement-reports-tab" data-bs-toggle="tab" data-bs-target="#procurement-reports" type="button">
                    <i class="bi bi-cart-plus"></i> Procurement
                </button>
            </li>
            <li class="nav-item" role="presentation">
                <button class="nav-link" id="financial-reports-tab" data-bs-toggle="tab" data-bs-target="#financial-reports" type="button">
                    <i class="bi bi-graph-up"></i> Financial Analysis
                </button>
            </li>
        </ul>

        <div class="tab-content" id="reportTabContent">
            <!-- Sales & Transactions Reports -->
            <div class="tab-pane fade show active" id="sales-reports" role="tabpanel">
                <div class="row">
                    <div class="col-md-6 mb-4">
                        <div class="card h-100 shadow-sm">
                            <div class="card-header bg-primary text-white">
                                <h5 class="mb-0"><i class="bi bi-cart-check"></i> POS Sales Report</h5>
                            </div>
                            <div class="card-body">
                                <p class="card-text">Detailed sales transactions with customer information, payment methods, and transaction types.</p>
                                <hr>
                                <div class="mb-3">
                                    <label class="form-label fw-bold">Date Range</label>
                                    <div class="row g-2">
                                        <div class="col-6">
                                            <input type="date" class="form-control" id="salesReportFrom">
                                        </div>
                                        <div class="col-6">
                                            <input type="date" class="form-control" id="salesReportTo">
                                        </div>
                                    </div>
                                </div>
                                <div class="mb-3">
                                    <label class="form-label fw-bold">Transaction Type</label>
                                    <select class="form-select" id="salesReportType">
                                        <option value="">All Types</option>
                                        <option value="sale">Sales</option>
                                        <option value="return">Returns</option>
                                        <option value="exchange">Exchanges</option>
                                    </select>
                                </div>
                                <div class="alert alert-info">
                                    <small><i class="bi bi-info-circle"></i> <strong>Includes:</strong> Sale number, customer details, items sold, payment info, timestamps</small>
                                </div>
                            </div>
                            <div class="card-footer">
                                <button class="btn btn-primary w-100" onclick="generateSalesReport()">
                                    <i class="bi bi-download"></i> Download Sales Report
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Inventory & Stock Reports -->
            <div class="tab-pane fade" id="inventory-reports" role="tabpanel">
                <div class="row">
                    <div class="col-md-6 mb-4">
                        <div class="card h-100 shadow-sm">
                            <div class="card-header bg-success text-white">
                                <h5 class="mb-0"><i class="bi bi-box-seam"></i> Current Inventory Report</h5>
                            </div>
                            <div class="card-body">
                                <p class="card-text">Complete inventory snapshot with stock levels, values, and low stock alerts.</p>
                                <hr>
                                <div class="mb-3">
                                    <label class="form-label fw-bold">Category Filter</label>
                                    <select class="form-select" id="inventoryReportCategory">
                                        <option value="">All Categories</option>
                                    </select>
                                </div>
                                <div class="mb-3">
                                    <label class="form-label fw-bold">Stock Status</label>
                                    <select class="form-select" id="inventoryReportStatus">
                                        <option value="">All</option>
                                        <option value="low">Low Stock</option>
                                        <option value="out">Out of Stock</option>
                                        <option value="good">Good Stock</option>
                                    </select>
                                </div>
                                <div class="alert alert-success">
                                    <small><i class="bi bi-info-circle"></i> <strong>Includes:</strong> SKU, product name, stock levels, pricing, stock value, status</small>
                                </div>
                            </div>
                            <div class="card-footer">
                                <button class="btn btn-success w-100" onclick="generateInventoryReport()">
                                    <i class="bi bi-download"></i> Download Inventory Report
                                </button>
                            </div>
                        </div>
                    </div>

                    <div class="col-md-6 mb-4">
                        <div class="card h-100 shadow-sm">
                            <div class="card-header bg-warning text-dark">
                                <h5 class="mb-0"><i class="bi bi-arrow-left-right"></i> Stock Movement Report</h5>
                            </div>
                            <div class="card-body">
                                <p class="card-text">Track all inventory movements including purchases, sales, adjustments, and returns.</p>
                                <hr>
                                <div class="mb-3">
                                    <label class="form-label fw-bold">Date Range</label>
                                    <div class="row g-2">
                                        <div class="col-6">
                                            <input type="date" class="form-control" id="movementReportFrom">
                                        </div>
                                        <div class="col-6">
                                            <input type="date" class="form-control" id="movementReportTo">
                                        </div>
                                    </div>
                                </div>
                                <div class="mb-3">
                                    <label class="form-label fw-bold">Movement Type</label>
                                    <select class="form-select" id="movementReportType">
                                        <option value="">All Types</option>
                                        <option value="purchase">Purchases</option>
                                        <option value="sale">Sales</option>
                                        <option value="adjustment">Adjustments</option>
                                        <option value="return">Returns</option>
                                    </select>
                                </div>
                                <div class="alert alert-warning">
                                    <small><i class="bi bi-info-circle"></i> <strong>Includes:</strong> Product, movement type, quantity, reference, date/time</small>
                                </div>
                            </div>
                            <div class="card-footer">
                                <button class="btn btn-warning w-100" onclick="generateMovementReport()">
                                    <i class="bi bi-download"></i> Download Movement Report
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Procurement Reports -->
            <div class="tab-pane fade" id="procurement-reports" role="tabpanel">
                <div class="row">
                    <div class="col-md-6 mb-4">
                        <div class="card h-100 shadow-sm">
                            <div class="card-header bg-info text-white">
                                <h5 class="mb-0"><i class="bi bi-cart-plus"></i> Purchase Orders Report</h5>
                            </div>
                            <div class="card-body">
                                <p class="card-text">Complete PO history with supplier details, quantities, and receiving status.</p>
                                <hr>
                                <div class="mb-3">
                                    <label class="form-label fw-bold">Date Range</label>
                                    <div class="row g-2">
                                        <div class="col-6">
                                            <input type="date" class="form-control" id="poReportFrom">
                                        </div>
                                        <div class="col-6">
                                            <input type="date" class="form-control" id="poReportTo">
                                        </div>
                                    </div>
                                </div>
                                <div class="mb-3">
                                    <label class="form-label fw-bold">Status</label>
                                    <select class="form-select" id="poReportStatus">
                                        <option value="">All Status</option>
                                        <option value="pending">Pending</option>
                                        <option value="partial">Partial</option>
                                        <option value="completed">Completed</option>
                                    </select>
                                </div>
                                <div class="alert alert-info">
                                    <small><i class="bi bi-info-circle"></i> <strong>Includes:</strong> PO number, supplier, items, quantities, amounts, status</small>
                                </div>
                            </div>
                            <div class="card-footer">
                                <button class="btn btn-info w-100" onclick="generatePOReport()">
                                    <i class="bi bi-download"></i> Download PO Report
                                </button>
                            </div>
                        </div>
                    </div>

                    <div class="col-md-6 mb-4">
                        <div class="card h-100 shadow-sm">
                            <div class="card-header bg-secondary text-white">
                                <h5 class="mb-0"><i class="bi bi-receipt"></i> GRN Report</h5>
                            </div>
                            <div class="card-body">
                                <p class="card-text">Goods Receipt Notes with received quantities, damaged items, and payment status.</p>
                                <hr>
                                <div class="mb-3">
                                    <label class="form-label fw-bold">Date Range</label>
                                    <div class="row g-2">
                                        <div class="col-6">
                                            <input type="date" class="form-control" id="grnReportFrom">
                                        </div>
                                        <div class="col-6">
                                            <input type="date" class="form-control" id="grnReportTo">
                                        </div>
                                    </div>
                                </div>
                                <div class="mb-3">
                                    <label class="form-label fw-bold">Payment Status</label>
                                    <select class="form-select" id="grnReportPayment">
                                        <option value="">All Status</option>
                                        <option value="paid">Paid</option>
                                        <option value="partial">Partial</option>
                                        <option value="unpaid">Unpaid</option>
                                    </select>
                                </div>
                                <div class="alert alert-secondary">
                                    <small><i class="bi bi-info-circle"></i> <strong>Includes:</strong> GRN number, PO details, received/damaged quantities, payment info</small>
                                </div>
                            </div>
                            <div class="card-footer">
                                <button class="btn btn-secondary w-100" onclick="generateGRNReport()">
                                    <i class="bi bi-download"></i> Download GRN Report
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Financial Analysis Reports -->
            <div class="tab-pane fade" id="financial-reports" role="tabpanel">
                <div class="row">
                    <div class="col-md-6 mb-4">
                        <div class="card h-100 shadow-sm">
                            <div class="card-header bg-danger text-white">
                                <h5 class="mb-0"><i class="bi bi-graph-up"></i> Profit Analysis Report</h5>
                            </div>
                            <div class="card-body">
                                <p class="card-text">Analyze profit margins, identify top-performing products, and track financial performance.</p>
                                <hr>
                                <div class="mb-3">
                                    <label class="form-label fw-bold">Date Range</label>
                                    <div class="row g-2">
                                        <div class="col-6">
                                            <input type="date" class="form-control" id="profitReportFrom">
                                        </div>
                                        <div class="col-6">
                                            <input type="date" class="form-control" id="profitReportTo">
                                        </div>
                                    </div>
                                </div>
                                <div class="mb-3">
                                    <label class="form-label fw-bold">Sort By</label>
                                    <select class="form-select" id="profitReportSort">
                                        <option value="margin">Profit Margin %</option>
                                        <option value="quantity">Quantity Sold</option>
                                        <option value="revenue">Total Revenue</option>
                                    </select>
                                </div>
                                <div class="alert alert-danger">
                                    <small><i class="bi bi-info-circle"></i> <strong>Includes:</strong> Product details, cost/selling price, profit margins, sales data</small>
                                </div>
                            </div>
                            <div class="card-footer">
                                <button class="btn btn-danger w-100" onclick="generateProfitReport()">
                                    <i class="bi bi-download"></i> Download Profit Report
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <!-- Help Section -->
        <div class="card mt-4 bg-light">
            <div class="card-body">
                <h6 class="card-title"><i class="bi bi-question-circle"></i> How to Use Reports</h6>
                <ul class="mb-0">
                    <li>Select the report category tab that matches your needs</li>
                    <li>Configure the date range and filters for each report</li>
                    <li>Click the download button to generate an Excel file</li>
                    <li>All reports are generated in real-time with current data</li>
                    <li>Downloaded files can be opened in Excel, Google Sheets, or any spreadsheet application</li>
                </ul>
            </div>
        </div>
    `);

    // Load categories for inventory report filter
    $.get(`${API_BASE}/categories`, function(categories) {
        const select = $('#inventoryReportCategory');
        categories.forEach(cat => {
            select.append(`<option value="${cat.id}">${cat.name}</option>`);
        });
    });

    // Set default date ranges to current month
    const today = new Date();
    const firstDay = new Date(today.getFullYear(), today.getMonth(), 1);
    const todayStr = today.toISOString().split('T')[0];
    const firstDayStr = firstDay.toISOString().split('T')[0];

    $('#salesReportFrom, #poReportFrom, #movementReportFrom, #grnReportFrom, #profitReportFrom').val(firstDayStr);
    $('#salesReportTo, #poReportTo, #movementReportTo, #grnReportTo, #profitReportTo').val(todayStr);
}

function generateSalesReport() {
    const fromDate = $('#salesReportFrom').val();
    const toDate = $('#salesReportTo').val();
    const transactionType = $('#salesReportType').val();

    let url = `${API_BASE}/reports/sales?format=excel`;
    if (fromDate) url += `&from_date=${fromDate}`;
    if (toDate) url += `&to_date=${toDate}`;
    if (transactionType) url += `&transaction_type=${transactionType}`;

    window.location.href = url;
}

function generateInventoryReport() {
    const category = $('#inventoryReportCategory').val();
    const status = $('#inventoryReportStatus').val();

    let url = `${API_BASE}/reports/inventory?format=excel`;
    if (category) url += `&category_id=${category}`;
    if (status) url += `&stock_status=${status}`;

    window.location.href = url;
}

function generatePOReport() {
    const fromDate = $('#poReportFrom').val();
    const toDate = $('#poReportTo').val();
    const status = $('#poReportStatus').val();

    let url = `${API_BASE}/reports/purchase-orders?format=excel`;
    if (fromDate) url += `&from_date=${fromDate}`;
    if (toDate) url += `&to_date=${toDate}`;
    if (status) url += `&status=${status}`;

    window.location.href = url;
}

function generateMovementReport() {
    const fromDate = $('#movementReportFrom').val();
    const toDate = $('#movementReportTo').val();
    const movementType = $('#movementReportType').val();

    let url = `${API_BASE}/reports/stock-movements?format=excel`;
    if (fromDate) url += `&from_date=${fromDate}`;
    if (toDate) url += `&to_date=${toDate}`;
    if (movementType) url += `&type=${movementType}`;

    window.location.href = url;
}

function generateGRNReport() {
    const fromDate = $('#grnReportFrom').val();
    const toDate = $('#grnReportTo').val();
    const paymentStatus = $('#grnReportPayment').val();

    let url = `${API_BASE}/reports/grns?format=excel`;
    if (fromDate) url += `&from_date=${fromDate}`;
    if (toDate) url += `&to_date=${toDate}`;
    if (paymentStatus) url += `&payment_status=${paymentStatus}`;

    window.location.href = url;
}

function generateProfitReport() {
    const fromDate = $('#profitReportFrom').val();
    const toDate = $('#profitReportTo').val();
    const sortBy = $('#profitReportSort').val();

    let url = `${API_BASE}/reports/profit?format=excel`;
    if (fromDate) url += `&from_date=${fromDate}`;
    if (toDate) url += `&to_date=${toDate}`;
    if (sortBy) url += `&sort_by=${sortBy}`;

    window.location.href = url;
}

function viewIMEITracking(productId) {
    $.get(`${API_BASE}/products/${productId}/imei-tracking`, function(data) {
        let content = `
            <div class="card">
                <div class="card-header bg-primary text-white">
                    <h6 class="mb-0"><i class="bi bi-upc-scan"></i> IMEI Tracking - ${data.product_name}</h6>
                </div>
                <div class="card-body">
                    <div class="alert alert-info">
                        <strong>Total IMEI Records:</strong> ${data.total_count}
                        <span class="ms-3">
                            <i class="bi bi-check-circle text-success"></i> Available: ${data.imei_records.filter(r => r.status === 'available').length}
                        </span>
                        <span class="ms-3">
                            <i class="bi bi-cart-x text-danger"></i> Sold: ${data.imei_records.filter(r => r.status === 'sold').length}
                        </span>
                    </div>
                    <div class="table-responsive">
                        <table class="table table-sm table-hover">
                            <thead>
                                <tr>
                                    <th>IMEI Number</th>
                                    <th>Status</th>
                                    <th>Added Date</th>
                                    <th>Reference</th>
                                    <th>Sale Details</th>
                                    <th>Action</th>
                                </tr>
                            </thead>
                            <tbody>
        `;

        if (data.imei_records.length === 0) {
            content += '<tr><td colspan="6" class="text-center text-muted">No IMEI records found</td></tr>';
        } else {
            data.imei_records.forEach(record => {
                const statusBadge = record.status === 'available' ? 'success' :
                                   record.status === 'sold' ? 'danger' : 'warning';
                const addedDate = new Date(record.created_at).toLocaleString();

                // Sale details for sold items
                let saleDetails = '<span class="text-muted">-</span>';
                if (record.status === 'sold' && record.sale_number) {
                    const soldDate = record.sold_date ? new Date(record.sold_date).toLocaleDateString() : 'N/A';
                    const soldTime = record.sold_date ? new Date(record.sold_date).toLocaleTimeString('en-US', {
                        hour: '2-digit',
                        minute: '2-digit'
                    }) : '';

                    saleDetails = `
                        <div class="small">
                            <div><strong class="text-primary"><i class="bi bi-receipt"></i> ${record.sale_number}</strong></div>
                            ${record.customer_name ? `<div class="text-muted"><i class="bi bi-person-fill"></i> ${record.customer_name}</div>` : '<div class="text-muted"><i class="bi bi-person"></i> Walk-in Customer</div>'}
                            <div class="text-muted"><i class="bi bi-calendar3"></i> ${soldDate} ${soldTime}</div>
                            <div class="mt-1"><span class="badge bg-success bg-opacity-10 text-success"><i class="bi bi-upc-scan"></i> IMEI: ${record.imei}</span></div>
                        </div>
                    `;
                }

                // Action buttons - store record id in a variable to avoid scope issues
                const recordId = record.id;
                const saleId = record.sale_id;

                let actionButtons = '<span class="text-muted">-</span>';
                if (record.status === 'available') {
                    actionButtons = `
                        <button class="btn btn-sm btn-danger" onclick="deleteIMEI(${recordId}, '${record.imei}')">
                            <i class="bi bi-trash"></i>
                        </button>
                    `;
                } else if (record.status === 'sold' && saleId) {
                    actionButtons = `
                        <button class="btn btn-sm btn-info" onclick="viewSaleDetails(${saleId})" title="View Sale">
                            <i class="bi bi-eye"></i>
                        </button>
                    `;
                }

                content += `
                    <tr class="${record.status === 'sold' ? 'table-light' : ''}">
                        <td><strong>${record.imei}</strong></td>
                        <td><span class="badge bg-${statusBadge}">${record.status.toUpperCase()}</span></td>
                        <td><small>${addedDate}</small></td>
                        <td><small>${record.reference || 'Manual Entry'}</small></td>
                        <td>${saleDetails}</td>
                        <td>${actionButtons}</td>
                    </tr>
                `;
            });
        }

        content += `
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
        `;

        $('#imeiTrackingContent').html(content);
        $('#imeiTrackingModal').data('product-id', productId);
        const modal = new bootstrap.Modal($('#imeiTrackingModal'));
        modal.show();
    }).fail(function(xhr) {
        alert('Error loading IMEI tracking: ' + (xhr.responseJSON?.error || 'Unknown error'));
    });
}

function markIMEISold(imeiId, imeiNumber) {
    if (!confirm(`Mark IMEI ${imeiNumber} as sold?`)) return;

    $.ajax({
        url: `${API_BASE}/imei/${imeiId}/mark-sold`,
        method: 'POST',
        success: function() {
            alert('IMEI marked as sold');
            $('#imeiTrackingModal').modal('hide');
        },
        error: function(xhr) {
            alert('Error: ' + (xhr.responseJSON?.error || 'Failed to update IMEI status'));
        }
    });
}

function deleteIMEI(imeiId, imeiNumber) {
    if (!confirm(`Are you sure you want to delete IMEI ${imeiNumber}?\n\nThis action cannot be undone.`)) return;

    $.ajax({
        url: `${API_BASE}/imeis/${imeiId}`,
        method: 'DELETE',
        success: function() {
            alert('IMEI deleted successfully');
            // Refresh the IMEI tracking modal
            const productId = $('#imeiTrackingModal').data('product-id');
            if (productId) {
                viewIMEITracking(productId);
            } else {
                $('#imeiTrackingModal').modal('hide');
            }
        },
        error: function(xhr) {
            alert('Error: ' + (xhr.responseJSON?.error || 'Failed to delete IMEI'));
        }
    });
}

function viewSaleDetails(saleId) {
    if (!saleId) {
        alert('Sale information not available');
        return;
    }

    $.get(`${API_BASE}/pos/sales/${saleId}`, function(sale) {
        const saleDate = new Date(sale.sale_date).toLocaleString();

        let content = `
            <div class="card">
                <div class="card-header bg-primary text-white">
                    <h6 class="mb-0"><i class="bi bi-receipt"></i> Sale Details - ${sale.sale_number}</h6>
                </div>
                <div class="card-body">
                    <div class="row mb-3">
                        <div class="col-md-6">
                            <p><strong>Sale Number:</strong> ${sale.sale_number}</p>
                            <p><strong>Date:</strong> ${saleDate}</p>
                            <p><strong>Transaction Type:</strong> <span class="badge bg-${sale.transaction_type === 'sale' ? 'success' : 'warning'}">${sale.transaction_type.toUpperCase()}</span></p>
                        </div>
                        <div class="col-md-6">
                            <p><strong>Customer:</strong> ${sale.customer_name || 'Walk-in'}</p>
                            ${sale.customer_phone ? `<p><strong>Phone:</strong> ${sale.customer_phone}</p>` : ''}
                            <p><strong>Payment Method:</strong> ${sale.payment_method || 'N/A'}</p>
                        </div>
                    </div>

                    <h6>Items</h6>
                    <table class="table table-sm table-bordered">
                        <thead>
                            <tr>
                                <th>Product</th>
                                <th>Quantity</th>
                                <th>Unit Price</th>
                                <th>Total</th>
                                <th>IMEI</th>
                            </tr>
                        </thead>
                        <tbody>
        `;

        sale.items.forEach(item => {
            content += `
                <tr>
                    <td>${item.product_name}</td>
                    <td>${item.quantity}</td>
                    <td>$${parseFloat(item.unit_price).toFixed(2)}</td>
                    <td>$${parseFloat(item.total_price).toFixed(2)}</td>
                    <td>${item.imei || '-'}</td>
                </tr>
            `;
        });

        content += `
                        </tbody>
                    </table>

                    <div class="row mt-3">
                        <div class="col-md-6 offset-md-6">
                            <table class="table table-sm">
                                <tr>
                                    <td class="text-end"><strong>Subtotal:</strong></td>
                                    <td class="text-end">$${parseFloat(sale.subtotal).toFixed(2)}</td>
                                </tr>
                                ${sale.discount_amount > 0 ? `
                                <tr>
                                    <td class="text-end"><strong>Discount:</strong></td>
                                    <td class="text-end text-danger">-$${parseFloat(sale.discount_amount).toFixed(2)}</td>
                                </tr>
                                ` : ''}
                                ${sale.tax_amount > 0 ? `
                                <tr>
                                    <td class="text-end"><strong>Tax:</strong></td>
                                    <td class="text-end">$${parseFloat(sale.tax_amount).toFixed(2)}</td>
                                </tr>
                                ` : ''}
                                <tr class="fw-bold">
                                    <td class="text-end"><strong>Total:</strong></td>
                                    <td class="text-end">$${parseFloat(sale.total_amount).toFixed(2)}</td>
                                </tr>
                            </table>
                        </div>
                    </div>

                    ${sale.notes ? `<p class="mt-3"><strong>Notes:</strong> ${sale.notes}</p>` : ''}
                </div>
            </div>
        `;

        // Create a new modal for sale details
        const modal = $(`
            <div class="modal fade" id="saleDetailsModal" tabindex="-1">
                <div class="modal-dialog modal-lg">
                    <div class="modal-content">
                        <div class="modal-header">
                            <h5 class="modal-title">Sale Details</h5>
                            <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                        </div>
                        <div class="modal-body">${content}</div>
                        <div class="modal-footer">
                            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Close</button>
                        </div>
                    </div>
                </div>
            </div>
        `);

        $('body').append(modal);
        const modalInstance = new bootstrap.Modal($('#saleDetailsModal'));
        modalInstance.show();

        $('#saleDetailsModal').on('hidden.bs.modal', function() {
            $(this).remove();
        });
    }).fail(function(xhr) {
        alert('Error loading sale details: ' + (xhr.responseJSON?.error || 'Unknown error'));
    });
}

function viewProductDetails(productId) {
    try {
        // Show loading state
        $('#productDetailsContent').html('<div class="text-center py-4"><div class="spinner-border" role="status"><span class="visually-hidden">Loading...</span></div><p class="mt-2">Loading product details...</p></div>');

        const modal = new bootstrap.Modal($('#productDetailsModal'));
        modal.show();
    } catch (error) {
        console.error('Error showing product details modal:', error);
        alert('Error opening product details. Please refresh the page and try again.');
        return;
    }

    // Fetch product and model data
    Promise.all([
        $.get(`${API_BASE}/products/${productId}`),
        $.get(`${API_BASE}/models`)
    ]).then(([product, models]) => {
        // Helper function to safely escape HTML
        function escapeHtml(text) {
            if (!text) return '';
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }

        const costPrice = parseFloat(product.cost_price || 0);
        const sellingPrice = parseFloat(product.selling_price || 0);
        const profitMargin = costPrice > 0 ? ((sellingPrice - costPrice) / costPrice * 100).toFixed(2) : 0;
        const profitColor = profitMargin > 30 ? 'success' : profitMargin > 15 ? 'warning' : 'danger';

        const stockStatus = product.current_stock === 0 ? 'Out of Stock' :
                           product.current_stock <= product.min_stock_level ? 'Low Stock' : 'In Stock';
        const stockBadgeClass = product.current_stock === 0 ? 'danger' :
                               product.current_stock <= product.min_stock_level ? 'warning' : 'success';

        // Find the model image from models array
        let modelImage = 'https://via.placeholder.com/300x300?text=No+Image';
        if (product.model_id) {
            const model = models.find(m => m.id === product.model_id);
            if (model && model.image_data) {
                modelImage = model.image_data;
            }
        }

        // Use model image if available, otherwise fall back to product image_url
        const displayImage = modelImage !== 'https://via.placeholder.com/300x300?text=No+Image' ? modelImage : (product.image_url || 'https://via.placeholder.com/300x300?text=No+Image');

        let content = `
            <div class="row">
                <!-- Left Column: Image Gallery -->
                <div class="col-md-4">
                    <div class="card mb-3">
                        <div class="card-body text-center">
                            <img src="${displayImage}"
                                 class="img-fluid rounded mb-2" style="max-height: 300px;" alt="${escapeHtml(product.name)}"
                                 onerror="this.src='https://via.placeholder.com/300x300?text=No+Image';">
                            <div class="d-flex justify-content-center gap-2">
                                <button class="btn btn-sm btn-outline-primary" onclick="changeProductImage(${product.id})">
                                    <i class="bi bi-image"></i> Change Image
                                </button>
                                <button class="btn btn-sm btn-outline-secondary" onclick="zoomProductImage('${displayImage}')">
                                    <i class="bi bi-zoom-in"></i> Zoom
                                </button>
                            </div>
                        </div>
                    </div>

                    <!-- Quick Actions -->
                    <div class="card">
                        <div class="card-header">
                            <strong><i class="bi bi-lightning-charge"></i> Quick Actions</strong>
                        </div>
                        <div class="card-body">
                            <div class="d-grid gap-2">
                                <button class="btn btn-primary btn-sm" onclick="editProduct(${product.id})">
                                    <i class="bi bi-pencil"></i> Edit Product
                                </button>
                                <button class="btn btn-info btn-sm" onclick="adjustStock(${product.id})">
                                    <i class="bi bi-plus-slash-minus"></i> Adjust Stock
                                </button>
                                <button class="btn btn-secondary btn-sm" onclick="viewIMEITracking(${product.id})">
                                    <i class="bi bi-list-ul"></i> IMEI Tracking
                                </button>
                                <button class="btn btn-warning btn-sm" onclick="generateBarcode(${product.id})">
                                    <i class="bi bi-upc-scan"></i> Print Barcode
                                </button>
                                <button class="btn btn-success btn-sm" onclick="reorderProduct(${product.id})">
                                    <i class="bi bi-cart-plus"></i> Reorder
                                </button>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Right Column: Details -->
                <div class="col-md-8">
                    <!-- Basic Information -->
                    <div class="card mb-3">
                        <div class="card-header">
                            <strong><i class="bi bi-info-circle"></i> Basic Information</strong>
                        </div>
                        <div class="card-body">
                            <div class="row">
                                <div class="col-md-6">
                                    <p><strong>Product Name:</strong> ${escapeHtml(product.name)}</p>
                                    <p><strong>SKU:</strong> ${escapeHtml(product.sku) || 'N/A'}
                                        ${product.sku ? `<button class="btn btn-sm btn-outline-secondary" onclick="copyToClipboard('${escapeHtml(product.sku)}')"><i class="bi bi-clipboard"></i></button>` : ''}
                                    </p>
                                    <p><strong>Category:</strong> ${escapeHtml(product.category_name) || 'N/A'}</p>
                                    <p><strong>Brand:</strong> ${escapeHtml(product.brand_name) || 'N/A'}</p>
                                </div>
                                <div class="col-md-6">
                                    <p><strong>Model:</strong> ${escapeHtml(product.model_name) || 'N/A'}</p>
                                    <p><strong>Status:</strong> <span class="badge bg-${product.status === 'active' ? 'success' : 'secondary'}">${escapeHtml(product.status)}</span></p>
                                    <p><strong>IMEI:</strong> ${escapeHtml(product.imei) || 'N/A'}</p>
                                    <p><strong>Color:</strong> ${escapeHtml(product.color) || 'N/A'}</p>
                                </div>
                            </div>
                            ${product.description ? `<p class="mb-0"><strong>Description:</strong><br>${escapeHtml(product.description)}</p>` : ''}
                        </div>
                    </div>

                    <!-- Pricing Information -->
                    <div class="card mb-3">
                        <div class="card-header">
                            <strong><i class="bi bi-currency-dollar"></i> Pricing Information</strong>
                        </div>
                        <div class="card-body">
                            <div class="row">
                                <div class="col-md-4">
                                    <p><strong>Cost Price:</strong><br><span class="h5 text-primary">$${costPrice.toFixed(2)}</span></p>
                                </div>
                                <div class="col-md-4">
                                    <p><strong>Selling Price:</strong><br><span class="h5 text-success">$${sellingPrice.toFixed(2)}</span></p>
                                </div>
                                <div class="col-md-4">
                                    <p><strong>MRP:</strong><br><span class="h5 text-info">$${parseFloat(product.mrp || 0).toFixed(2)}</span></p>
                                </div>
                            </div>
                            <div class="alert alert-${profitColor} mb-0">
                                <strong>Profit Margin:</strong> ${profitMargin}%
                            </div>
                        </div>
                    </div>

                    <!-- Stock Information -->
                    <div class="card mb-3">
                        <div class="card-header">
                            <strong><i class="bi bi-box"></i> Stock Information</strong>
                        </div>
                        <div class="card-body">
                            <div class="row">
                                <div class="col-md-3">
                                    <p><strong>Current Stock:</strong><br>
                                        <span class="h4 text-${stockBadgeClass}">${product.current_stock}</span>
                                        <button class="btn btn-sm btn-link" onclick="adjustStock(${product.id})">
                                            <i class="bi bi-pencil"></i>
                                        </button>
                                    </p>
                                </div>
                                <div class="col-md-3">
                                    <p><strong>Min Level:</strong><br><span class="h6">${product.min_stock_level}</span></p>
                                </div>
                                <div class="col-md-3">
                                    <p><strong>Opening Stock:</strong><br><span class="h6">${product.opening_stock || 0}</span></p>
                                </div>
                                <div class="col-md-3">
                                    <p><strong>Status:</strong><br><span class="badge bg-${stockBadgeClass}">${stockStatus}</span></p>
                                </div>
                            </div>
                            <div class="mt-2">
                                <p><strong>Storage Location:</strong> ${product.storage_location || 'Not specified'}</p>
                                <button class="btn btn-sm btn-outline-primary" onclick="viewStockHistory(${product.id})">
                                    <i class="bi bi-clock-history"></i> View Stock History
                                </button>
                            </div>
                        </div>
                    </div>

                    <!-- Supplier Information -->
                    <div class="card mb-3">
                        <div class="card-header">
                            <strong><i class="bi bi-truck"></i> Supplier Information</strong>
                        </div>
                        <div class="card-body">
                            <div class="row">
                                <div class="col-md-6">
                                    <p><strong>Supplier Name:</strong> ${product.supplier_name || 'N/A'}</p>
                                </div>
                                <div class="col-md-6">
                                    <p><strong>Contact:</strong> ${product.supplier_contact || 'N/A'}
                                        ${product.supplier_contact ? `
                                            <button class="btn btn-sm btn-outline-primary" onclick="window.location.href='tel:${product.supplier_contact}'">
                                                <i class="bi bi-telephone"></i>
                                            </button>
                                        ` : ''}
                                    </p>
                                </div>
                            </div>
                        </div>
                    </div>

                    <!-- Specifications -->
                    <div class="card mb-3">
                        <div class="card-header">
                            <strong><i class="bi bi-list-ul"></i> Specifications</strong>
                        </div>
                        <div class="card-body">
                            <table class="table table-sm mb-0">
                                <tbody>
                                    ${product.storage_capacity ? `<tr><td><strong>Storage:</strong></td><td>${product.storage_capacity}</td></tr>` : ''}
                                    ${product.ram ? `<tr><td><strong>RAM:</strong></td><td>${product.ram}</td></tr>` : ''}
                                    ${product.warranty_period ? `<tr><td><strong>Warranty:</strong></td><td>${product.warranty_period}</td></tr>` : ''}
                                    ${!product.storage_capacity && !product.ram && !product.warranty_period ? '<tr><td colspan="2" class="text-muted">No specifications available</td></tr>' : ''}
                                </tbody>
                            </table>
                        </div>
                    </div>
                </div>
            </div>
        `;

        $('#productDetailsContent').html(content);
    }).catch(function(error) {
        console.error('Error loading product details:', error);
        const errorMsg = error.responseJSON?.error || 'Failed to load product details.';
        $('#productDetailsContent').html(`
            <div class="alert alert-danger">
                <i class="bi bi-exclamation-triangle"></i> <strong>Error:</strong> ${errorMsg}
            </div>
        `);
    });
}

function copyToClipboard(text) {
    navigator.clipboard.writeText(text).then(() => {
        alert('Copied to clipboard: ' + text);
    });
}

function changeProductImage(productId) {
    const newUrl = prompt('Enter new image URL:');
    if (newUrl) {
        $.ajax({
            url: `${API_BASE}/products/${productId}`,
            method: 'GET',
            success: function(product) {
                product.image_url = newUrl;
                $.ajax({
                    url: `${API_BASE}/products/${productId}`,
                    method: 'PUT',
                    contentType: 'application/json',
                    data: JSON.stringify(product),
                    success: function() {
                        alert('Image updated successfully');
                        viewProductDetails(productId);
                    }
                });
            }
        });
    }
}

function zoomProductImage(imageUrl) {
    if (!imageUrl || imageUrl.includes('placeholder')) {
        alert('No image available to zoom');
        return;
    }
    window.open(imageUrl, '_blank');
}

function adjustStock(productId) {
    $.get(`${API_BASE}/products/${productId}`, function(product) {
        const adjustment = prompt(`Current stock: ${product.current_stock}\n\nEnter adjustment amount (use + or - prefix):`);
        if (adjustment) {
            const newStock = product.current_stock + parseInt(adjustment);
            if (newStock < 0) {
                alert('Stock cannot be negative');
                return;
            }

            $.ajax({
                url: `${API_BASE}/products/${productId}`,
                method: 'PUT',
                contentType: 'application/json',
                data: JSON.stringify({
                    ...product,
                    current_stock: newStock
                }),
                success: function() {
                    alert('Stock adjusted successfully');
                    viewProductDetails(productId);
                    if (currentPage === 'inventory') {
                        loadInventoryData();
                    }
                }
            });
        }
    });
}

function generateBarcode(productId) {
    alert('Barcode generation feature - Coming soon!\n\nThis will allow you to:\n- Generate barcodes in various formats\n- Print labels with product details\n- Customize label templates');
}

function reorderProduct(productId) {
    $.get(`${API_BASE}/products/${productId}`, function(product) {
        const recommended = Math.max(product.min_stock_level * 2, 10);
        const quantity = prompt(`Reorder ${product.name}\n\nCurrent Stock: ${product.current_stock}\nMin Level: ${product.min_stock_level}\nRecommended Quantity: ${recommended}\n\nEnter quantity to order:`, recommended);

        if (quantity && parseInt(quantity) > 0) {
            alert('Creating purchase order...\n\nThis will create a PO for ' + quantity + ' units of ' + product.name);
            // Future: Automatically create PO
        }
    });
}

let posCart = [];
let posCustomer = {};

function loadPOS() {
    posCart = [];
    posCustomer = {};

    // Set current date and time
    const now = new Date();
    const dateStr = now.toISOString().slice(0, 16);

    $('#content-area').html(`
        <div class="page-header">
            <h2><i class="bi bi-calculator"></i> Point of Sale (POS)</h2>
        </div>

        <div class="row">
            <!-- Left Side - Product Search and Cart -->
            <div class="col-md-8">
                <!-- Transaction Type Selector -->
                <div class="card mb-3">
                    <div class="card-header bg-info text-white">
                        <h6 class="mb-0"><i class="bi bi-tag"></i> Transaction Type</h6>
                    </div>
                    <div class="card-body">
                        <div class="btn-group w-100" role="group">
                            <input type="radio" class="btn-check" name="transactionType" id="typeSale" value="sale" checked>
                            <label class="btn btn-outline-success" for="typeSale">
                                <i class="bi bi-cart-check"></i> Sale
                            </label>

                            <input type="radio" class="btn-check" name="transactionType" id="typeReturn" value="return">
                            <label class="btn btn-outline-danger" for="typeReturn">
                                <i class="bi bi-arrow-return-left"></i> Return
                            </label>

                            <input type="radio" class="btn-check" name="transactionType" id="typeExchange" value="exchange">
                            <label class="btn btn-outline-warning" for="typeExchange">
                                <i class="bi bi-arrow-left-right"></i> Exchange
                            </label>
                        </div>
                        <div id="returnExchangeInfo" class="alert alert-info mt-3" style="display:none;">
                            <small>
                                <strong>Note:</strong> <span id="transactionTypeNote"></span>
                            </small>
                        </div>
                    </div>
                </div>

                <!-- Product Search -->
                <div class="card mb-3">
                    <div class="card-header bg-primary text-white">
                        <h5 class="mb-0"><i class="bi bi-search"></i> Product Search</h5>
                    </div>
                    <div class="card-body">
                        <div class="input-group input-group-lg">
                            <span class="input-group-text"><i class="bi bi-upc-scan"></i></span>
                            <input type="text" class="form-control" id="posProductSearch"
                                   placeholder="Search by product name, SKU, or IMEI..." autofocus>
                        </div>
                        <div id="posSearchResults" class="mt-3"></div>
                    </div>
                </div>

                <!-- Shopping Cart -->
                <div class="card">
                    <div class="card-header text-white" id="cartHeader" style="background-color: #198754;">
                        <h5 class="mb-0">
                            <i class="bi bi-cart"></i> <span id="cartTypeLabel">Shopping Cart</span>
                            (<span id="cartItemCount">0</span> items)
                        </h5>
                    </div>
                    <div class="card-body p-0">
                        <div class="table-responsive">
                            <table class="table table-hover mb-0" id="posCartTable">
                                <thead class="table-light">
                                    <tr>
                                        <th>Product</th>
                                        <th>Price</th>
                                        <th style="width: 120px;">Qty</th>
                                        <th>IMEI</th>
                                        <th>Total</th>
                                        <th>Action</th>
                                    </tr>
                                </thead>
                                <tbody id="posCartBody"></tbody>
                            </table>
                        </div>
                        <div id="emptyCart" class="text-center text-muted py-5">
                            <i class="bi bi-cart-x" style="font-size: 3rem;"></i>
                            <p class="mt-2">Cart is empty. Search and add products above.</p>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Right Side - Customer and Payment -->
            <div class="col-md-4">
                <!-- Customer Information -->
                <div class="card mb-3">
                    <div class="card-header bg-info text-white">
                        <h6 class="mb-0"><i class="bi bi-person"></i> Customer Information (Optional)</h6>
                    </div>
                    <div class="card-body">
                        <div class="mb-2">
                            <input type="text" class="form-control form-control-sm" id="customerName" placeholder="Customer Name">
                        </div>
                        <div class="mb-2">
                            <input type="text" class="form-control form-control-sm" id="customerPhone" placeholder="Phone Number">
                        </div>
                        <div class="mb-2">
                            <input type="email" class="form-control form-control-sm" id="customerEmail" placeholder="Email">
                        </div>
                    </div>
                </div>

                <!-- Bill Summary -->
                <div class="card mb-3">
                    <div class="card-header bg-dark text-white">
                        <h6 class="mb-0"><i class="bi bi-receipt"></i> Bill Summary</h6>
                    </div>
                    <div class="card-body">
                        <div class="mb-3 pb-2 border-bottom">
                            <div class="d-flex justify-content-between align-items-center">
                                <span class="text-muted small"><i class="bi bi-calendar3"></i> Transaction Date:</span>
                                <strong class="small" id="posTransactionDate"></strong>
                            </div>
                            <div class="d-flex justify-content-between align-items-center">
                                <span class="text-muted small"><i class="bi bi-clock"></i> Transaction Time:</span>
                                <strong class="small" id="posTransactionTime"></strong>
                            </div>
                        </div>
                        <div class="d-flex justify-content-between mb-2">
                            <span>Subtotal:</span>
                            <strong id="posSubtotal">$0.00</strong>
                        </div>
                        <div class="d-flex justify-content-between align-items-center mb-2">
                            <span>Discount (%):</span>
                            <div class="input-group input-group-sm" style="width: 100px;">
                                <input type="number" class="form-control" id="posDiscountPercent" value="0" min="0" max="100">
                                <span class="input-group-text">%</span>
                            </div>
                        </div>
                        <div class="d-flex justify-content-between mb-2">
                            <span>Discount Amount:</span>
                            <strong id="posDiscountAmount" class="text-danger">-$0.00</strong>
                        </div>
                        <div class="d-flex justify-content-between align-items-center mb-2">
                            <span>Tax (%):</span>
                            <div class="input-group input-group-sm" style="width: 100px;">
                                <input type="number" class="form-control" id="posTaxPercent" value="0" min="0" max="100">
                                <span class="input-group-text">%</span>
                            </div>
                        </div>
                        <div class="d-flex justify-content-between mb-2">
                            <span>Tax Amount:</span>
                            <strong id="posTaxAmount" class="text-info">+$0.00</strong>
                        </div>
                        <hr>
                        <div class="d-flex justify-content-between">
                            <h5>Total:</h5>
                            <h5 class="text-success" id="posTotal">$0.00</h5>
                        </div>
                    </div>
                </div>

                <!-- Payment Method -->
                <div class="card mb-3">
                    <div class="card-header bg-warning">
                        <h6 class="mb-0"><i class="bi bi-credit-card"></i> Payment Method</h6>
                    </div>
                    <div class="card-body">
                        <select class="form-select mb-2" id="posPaymentMethod">
                            <option value="cash">Cash</option>
                            <option value="card">Credit/Debit Card</option>
                            <option value="upi">UPI</option>
                            <option value="wallet">Digital Wallet</option>
                            <option value="bank_transfer">Bank Transfer</option>
                        </select>
                        <input type="text" class="form-control form-control-sm" id="posPaymentReference" placeholder="Reference Number (Optional)">
                    </div>
                </div>

                <!-- Actions -->
                <div class="d-grid gap-2">
                    <button class="btn btn-lg" id="completeTransactionBtn" onclick="completePOSSale()" style="background-color: #198754; color: white;">
                        <i class="bi bi-check-circle"></i> <span id="completeButtonLabel">Complete Sale</span>
                    </button>
                    <button class="btn btn-danger" onclick="clearPOSCart()">
                        <i class="bi bi-x-circle"></i> Clear Cart
                    </button>
                    <button class="btn btn-secondary" onclick="loadPage('pos')">
                        <i class="bi bi-arrow-clockwise"></i> New Transaction
                    </button>
                </div>
            </div>
        </div>
    `);

    updatePOSCart();

    // Transaction type change handler
    $('input[name="transactionType"]').on('change', function() {
        const transactionType = $(this).val();
        let buttonColor, buttonLabel;

        if (transactionType === 'return') {
            $('#returnExchangeInfo').show();
            $('#transactionTypeNote').text('Returns will add stock back and refund the customer. Amount will show as negative.');
            buttonColor = '#dc3545';
            buttonLabel = 'Complete Return';
        } else if (transactionType === 'exchange') {
            $('#returnExchangeInfo').show();
            $('#transactionTypeNote').text('Exchange allows returning items and adding new items in the same transaction.');
            buttonColor = '#ffc107';
            buttonLabel = 'Complete Exchange';
        } else {
            $('#returnExchangeInfo').hide();
            buttonColor = '#198754';
            buttonLabel = 'Complete Sale';
        }

        $('#completeTransactionBtn').css('background-color', buttonColor);
        $('#completeButtonLabel').text(buttonLabel);
        updatePOSCart();
    });

    // Product search with debounce
    let searchTimeout;
    $('#posProductSearch').on('input', function() {
        clearTimeout(searchTimeout);
        const query = $(this).val();

        if (query.length >= 2) {
            searchTimeout = setTimeout(() => searchPOSProducts(query), 300);
        } else {
            $('#posSearchResults').empty();
        }
    });

    // Calculate totals on discount/tax change
    $('#posDiscountPercent, #posTaxPercent').on('input', updatePOSCart);
}

function searchPOSProducts(query) {
    $.get(`${API_BASE}/pos/products/search?q=${encodeURIComponent(query)}`, function(products) {
        const resultsDiv = $('#posSearchResults');
        resultsDiv.empty();

        if (products.length === 0) {
            resultsDiv.html('<div class="alert alert-info">No products found</div>');
            return;
        }

        const html = products.map(p => `
            <div class="product-search-item" onclick='addToCart(${JSON.stringify(p)})' style="cursor: pointer; padding: 10px; border-bottom: 1px solid #eee;">
                <div class="d-flex justify-content-between align-items-center">
                    <div>
                        <strong>${p.name}</strong>
                        <div class="small text-muted">
                            ${p.sku ? `SKU: ${p.sku} | ` : ''}
                            ${p.brand_name || ''} ${p.model_name || ''}
                            <span class="badge bg-${p.current_stock > 10 ? 'success' : p.current_stock > 0 ? 'warning' : 'danger'}">
                                Stock: ${p.current_stock}
                            </span>
                        </div>
                    </div>
                    <div class="text-end">
                        <strong class="text-success">$${parseFloat(p.selling_price).toFixed(2)}</strong>
                    </div>
                </div>
            </div>
        `).join('');

        resultsDiv.html(html);
    });
}

function addToCart(product) {
    const existingItem = posCart.find(item => item.product_id === product.id);

    if (existingItem) {
        existingItem.quantity += 1;
        // Check if product has IMEI tracking
        checkAndPromptIMEI(product, posCart.indexOf(existingItem));
    } else {
        posCart.push({
            product_id: product.id,
            product_name: product.name,
            sku: product.sku,
            unit_price: product.selling_price,
            quantity: 1,
            imei_ids: [],
            imei_available: [], // Initialize for IMEI selection
            imei_numbers: []    // To store selected IMEI strings for display
        });
        // Check if product has IMEI tracking
        checkAndPromptIMEI(product, posCart.length - 1);
    }

    updatePOSCart();
    $('#posProductSearch').val('').focus();
    $('#posSearchResults').empty(); // Clear search results after adding to cart
}

function checkAndPromptIMEI(product, cartIndex) {
    // Check if product has available IMEIs
    $.get(`${API_BASE}/products/${product.id}/imeis?status=available`, function(imeis) {
        // Only prompt if there are available IMEIs and the item is not yet fully selected
        if (imeis.length > 0 && (posCart[cartIndex].imei_ids.length < posCart[cartIndex].quantity)) {
            // Store available IMEIs for this product in the cart item
            posCart[cartIndex].imei_available = imeis;
            // Show selection modal
            currentPOSProductForIMEI = product;
            currentPOSCartIndex = cartIndex;
            showIMEISelectionModal(product, posCart[cartIndex].quantity, posCart[cartIndex].imei_ids);
        } else if (imeis.length === 0 && posCart[cartIndex].imei_ids.length > 0) {
            // If no IMEIs are available but some were previously selected, clear them
            posCart[cartIndex].imei_ids = [];
            posCart[cartIndex].imei_available = [];
            posCart[cartIndex].imei_numbers = [];
            updatePOSCart(); // Update cart to reflect cleared IMEIs
        }
    });
}

function showIMEISelectionModal(product, requiredQty, selectedIds = []) {
    $.get(`${API_BASE}/products/${product.id}/imeis?status=available`, function(imeis) {
        $('#imeiProductName').text(product.name);
        $('#imeiQuantityRequired').text(requiredQty);

        const listBody = $('#imeiSelectionList');
        listBody.empty();

        if (imeis.length === 0) {
            listBody.append(`
                <tr>
                    <td colspan="3" class="text-center text-muted">
                        <i class="bi bi-inbox"></i> No IMEI numbers available for this product
                    </td>
                </tr>
            `);
        } else {
            imeis.forEach(imei => {
                const isChecked = selectedIds.includes(imei.id) ? 'checked' : '';
                listBody.append(`
                    <tr>
                        <td>
                            <div class="form-check">
                                <input class="form-check-input imei-checkbox" type="checkbox" value="${imei.id}" 
                                       id="imei_${imei.id}" ${isChecked}>
                            </div>
                        </td>
                        <td><label for="imei_${imei.id}"><code>${imei.imei}</code></label></td>
                        <td><span class="badge bg-success">Available</span></td>
                    </tr>
                `);
            });
        }

        $('#imeiSelectionError').hide();
        $('#confirmImeiSelectionBtn').data('cart-index', currentPOSCartIndex); // Ensure correct index is stored
        const modal = new bootstrap.Modal($('#imeiSelectionModal'));
        modal.show();
    });
}

function confirmIMEISelection() {
    const cartIndex = $('#confirmImeiSelectionBtn').data('cart-index');
    if (cartIndex === null || cartIndex === undefined) return; // Should not happen, but good practice

    const item = posCart[cartIndex];
    const requiredQty = item.quantity;

    const selectedIMEIs = [];
    $('.imei-checkbox:checked').each(function() {
        selectedIMEIs.push({
            id: parseInt($(this).val()),
            imei: $(this).data('imei') // Store imei string for display
        });
    });

    if (selectedIMEIs.length !== requiredQty) {
        $('#imeiSelectionError').text(`Please select exactly ${requiredQty} IMEI number(s). Currently selected: ${selectedIMEIs.length}`).show();
        return;
    }

    // Update cart item with selected IMEI IDs and their strings
    posCart[cartIndex].imei_ids = selectedIMEIs.map(i => i.id);
    posCart[cartIndex].imei_numbers = selectedIMEIs.map(i => i.imei); // Store strings for display

    // Close modal and update display
    bootstrap.Modal.getInstance($('#imeiSelectionModal')).hide();
    $('#imeiSelectionError').hide();
    updatePOSCart();
}

function updatePOSCart() {
    const tbody = $('#posCartTable tbody');
    tbody.empty();

    // Get transaction type
    const transactionType = $('input[name="transactionType"]:checked').val();

    // Update cart header based on transaction type
    let headerColor, headerIcon, headerLabel;
    if (transactionType === 'return') {
        headerColor = '#dc3545';
        headerIcon = 'arrow-return-left';
        headerLabel = 'Return Cart';
    } else if (transactionType === 'exchange') {
        headerColor = '#ffc107';
        headerIcon = 'arrow-left-right';
        headerLabel = 'Exchange Cart';
    } else {
        headerColor = '#198754';
        headerIcon = 'cart';
        headerLabel = 'Shopping Cart';
    }
    $('#cartHeader').css('background-color', headerColor);
    $('#cartTypeLabel').html(`<i class="bi bi-${headerIcon}"></i> ${headerLabel}`);

    if (posCart.length === 0) {
        $('#emptyCart').show();
        $('#posCartTable').hide();
        // Reset totals if cart is empty
        updatePOSTotals(0);
        return;
    }

    $('#emptyCart').hide();
    $('#posCartTable').show();

    let subtotal = 0;

    posCart.forEach((item, index) => {
        const itemTotal = item.quantity * item.unit_price;
        subtotal += itemTotal;

        // Display IMEI information
        let imeiDisplay = '-';
        let imeiClass = '';
        if (item.imei_ids && item.imei_ids.length > 0) {
            imeiDisplay = `<span class="badge bg-success">${item.imei_ids.length} IMEI</span>`;
            if (item.imei_ids.length < item.quantity) {
                imeiDisplay = `<span class="badge bg-warning">${item.imei_ids.length}/${item.quantity} IMEI</span>`;
                imeiClass = 'text-warning'; // Highlight row if IMEI count is incomplete
            }
        }

        tbody.append(`
            <tr class="${imeiClass}">
                <td>
                    <strong>${item.product_name}</strong>
                    <div class="small text-muted">${item.sku || ''}</div>
                </td>
                <td>$${item.unit_price.toFixed(2)}</td>
                <td>
                    <div class="input-group input-group-sm" style="width: 120px;">
                        <button class="btn btn-outline-secondary" onclick="updateCartQty(${index}, -1)">-</button>
                        <input type="number" class="form-control text-center" value="${item.quantity}"
                               onchange="updateCartQty(${index}, parseInt(this.value))" min="1" max="${item.available_stock || 999}">
                        <button class="btn btn-outline-secondary" onclick="updateCartQty(${index}, 1)">+</button>
                    </div>
                    <small class="text-muted">Stock: ${item.available_stock}</small>
                </td>
                <td>
                    ${imeiDisplay}
                    <button class="btn btn-sm btn-outline-primary mt-1" onclick="selectIMEIForCart(${index})" title="Select IMEI">
                        <i class="bi bi-upc-scan"></i>
                    </button>
                    ${item.imei_numbers && item.imei_numbers.length > 0 ? `<div class="small text-muted mt-1">${item.imei_numbers.join(', ')}</div>` : ''}
                </td>
                <td><strong>$${itemTotal.toFixed(2)}</strong></td>
                <td>
                    <button class="btn btn-sm btn-danger" onclick="removeFromPOSCart(${index})">
                        <i class="bi bi-trash"></i>
                    </button>
                </td>
            </tr>
        `);
    });

    // Update transaction date and time
    const now = new Date();
    const dateOptions = { year: 'numeric', month: 'short', day: 'numeric' };
    const timeOptions = { hour: '2-digit', minute: '2-digit', second: '2-digit' };
    $('#posTransactionDate').text(now.toLocaleDateString('en-US', dateOptions));
    $('#posTransactionTime').text(now.toLocaleTimeString('en-US', timeOptions));

    updatePOSTotals(subtotal);
}

function updatePOSTotals(subtotal) {
    const discountPercent = parseFloat($('#posDiscountPercent').val()) || 0;
    const taxPercent = parseFloat($('#posTaxPercent').val()) || 0;
    const transactionType = $('input[name="transactionType"]:checked').val();

    let effectiveSubtotal = subtotal;
    if (transactionType === 'return') {
        effectiveSubtotal = -Math.abs(subtotal); // Make subtotal negative for returns
    }

    const discountAmount = Math.abs(effectiveSubtotal) * (discountPercent / 100);
    const taxableAmount = effectiveSubtotal - (transactionType === 'return' ? -discountAmount : discountAmount);
    const taxAmount = Math.abs(taxableAmount) * (taxPercent / 100);
    const total = taxableAmount + (transactionType === 'return' ? -taxAmount : taxAmount);

    $('#cartItemCount').text(posCart.length);
    $('#posSubtotal').text((transactionType === 'return' ? '-' : '') + '$' + Math.abs(subtotal).toFixed(2));
    $('#posDiscountAmount').text('-$' + discountAmount.toFixed(2));
    $('#posTaxAmount').text('+$' + taxAmount.toFixed(2));
    $('#posTotal').text((total < 0 ? '-' : '') + '$' + Math.abs(total).toFixed(2));
}

function updateCartQty(index, change) {
    const item = posCart[index];
    let newQuantity = item.quantity + change;

    // Ensure quantity is at least 1 and does not exceed stock (if available)
    if (newQuantity < 1) newQuantity = 1;
    if (item.available_stock && newQuantity > item.available_stock) {
        alert(`Maximum available stock is ${item.available_stock}`);
        newQuantity = item.available_stock;
    }

    item.quantity = newQuantity;

    // If IMEI selection is required and quantity changes, reset IMEI selection
    if (item.imei_available && item.imei_available.length > 0) {
        item.imei_ids = []; // Clear selected IMEIs
        item.imei_numbers = [];
    }

    updatePOSCart();
}

function removeFromPOSCart(index) {
    posCart.splice(index, 1);
    updatePOSCart();
}

function clearPOSCart() {
    if (posCart.length > 0 && !confirm('Clear all items from cart?')) {
        return;
    }
    posCart = [];
    updatePOSCart();
}

function selectIMEIForCart(index) {
    const item = posCart[index];
    // Fetch product details again to ensure we have the latest IMEI list
    $.get(`${API_BASE}/products/${item.product_id}`, function(product) {
        currentPOSProductForIMEI = product;
        currentPOSCartIndex = index;
        showIMEISelectionModal(product, item.quantity, item.imei_ids);
    });
}

function completePOSSale() {
    if (posCart.length === 0) {
        alert('Please add items to cart');
        return;
    }

    // Check if all items with IMEI tracking have the required number of IMEIs selected
    let imeiSelectionIncomplete = false;
    let incompleteItemName = '';
    posCart.forEach(item => {
        // Check only if the item requires IMEIs (indicated by available IMEIs or already selected IMEIs)
        // And if the number of selected IMEIs is less than the required quantity
        if ((item.imei_available && item.imei_available.length > 0 || (item.imei_ids && item.imei_ids.length > 0)) &&
            item.imei_ids.length < item.quantity) {
            imeiSelectionIncomplete = true;
            incompleteItemName = item.product_name; // Store name for alert message
        }
    });

    if (imeiSelectionIncomplete) {
        alert(`IMEI selection is incomplete for "${incompleteItemName}". Please ensure all required IMEI numbers are selected for this item.`);
        return; // Prevent proceeding if IMEI selection is incomplete
    }

    const transactionType = $('input[name="transactionType"]:checked').val();
    const transactionLabel = transactionType === 'return' ? 'Return' :
                            transactionType === 'exchange' ? 'Exchange' : 'Sale';

    // Confirm transaction
    if (!confirm(`Complete this ${transactionLabel}?`)) {
        return;
    }

    const now = new Date();
    const saleDate = now.toISOString().slice(0, 19).replace('T', ' ');

    const saleData = {
        items: posCart,
        customer_name: $('#customerName').val(),
        customer_phone: $('#customerPhone').val(),
        customer_email: $('#customerEmail').val(),
        sale_date: saleDate,
        transaction_type: transactionType,
        discount_percentage: parseFloat($('#posDiscountPercent').val()) || 0,
        tax_percentage: parseFloat($('#posTaxPercent').val()) || 0,
        payment_method: $('#posPaymentMethod').val(),
        payment_reference: $('#posPaymentReference').val()
    };

    $.ajax({
        url: `${API_BASE}/pos/sales`,
        method: 'POST',
        contentType: 'application/json',
        data: JSON.stringify(saleData),
        success: function(response) {
            if (response.success) {
                const amountLabel = transactionType === 'return' ? 'Refund Amount' : 'Total Amount';
                alert(`✓ ${transactionLabel} completed successfully!\n\nTransaction Number: ${response.sale_number}\n${amountLabel}: $${Math.abs(response.total_amount).toFixed(2)}\n\nThank you!`);
                loadPOS(); // Reset for new transaction
            } else {
                alert('Error: ' + (response.error || 'Failed to complete transaction'));
            }
        },
        error: function(xhr) {
            alert('Error: ' + (xhr.responseJSON?.error || 'Failed to complete transaction'));
        }
    });
}

function viewStockHistory(productId) {
    try {
        // Show loading state
        $('#stockHistoryContent').html('<div class="text-center py-4"><div class="spinner-border" role="status"><span class="visually-hidden">Loading...</span></div><p class="mt-2">Loading stock history...</p></div>');

        const modal = new bootstrap.Modal($('#stockHistoryModal'));
        modal.show();
    } catch (error) {
        console.error('Error showing stock history modal:', error);
        alert('Error opening stock history. Please refresh the page and try again.');
        return;
    }

    // Load the stock history data
    $.get(`${API_BASE}/products/${productId}/stock-history`, function(data) {
        const productName = escapeHtml(data.product_name || 'Unknown Product');

        let content = `
            <div class="mb-3">
                <h6><i class="bi bi-box-seam"></i> Complete Audit Trail for: <strong>${productName}</strong></h6>
                <p class="text-muted mb-0"><small>Complete history of all stock movements with running balance</small></p>
            </div>
            <div class="table-responsive">
                <table class="table table-sm table-striped table-hover table-bordered">
                    <thead class="table-dark">
                        <tr>
                            <th style="min-width: 150px;"><i class="bi bi-calendar-event"></i> Date & Time</th>
                            <th style="min-width: 100px;" class="text-center"><i class="bi bi-plus-circle text-success"></i> Stock Added</th>
                            <th style="min-width: 100px;" class="text-center"><i class="bi bi-dash-circle text-danger"></i> Stock Removed</th>
                            <th style="min-width: 150px;"><i class="bi bi-receipt"></i> Reference Number</th>
                            <th style="min-width: 120px;"><i class="bi bi-person"></i> Performed By</th>
                            <th style="min-width: 120px;" class="text-center"><i class="bi bi-bar-chart"></i> Running Balance</th>
                        </tr>
                    </thead>
                    <tbody>
        `;

        if (!data.history || data.history.length === 0) {
            content += '<tr><td colspan="6" class="text-center text-muted py-4"><i class="bi bi-inbox"></i><br>No stock movements found for this product</td></tr>';
        } else {
            let totalAdded = 0;
            let totalRemoved = 0;

            data.history.forEach((item, index) => {
                try {
                    const dateStr = item.date_time || '';
                    const date = new Date(dateStr);
                    const formattedDate = !isNaN(date.getTime()) ? date.toLocaleDateString('en-US', {
                        year: 'numeric',
                        month: 'short',
                        day: 'numeric'
                    }) : 'Invalid Date';
                    const formattedTime = !isNaN(date.getTime()) ? date.toLocaleTimeString('en-US', {
                        hour: '2-digit',
                        minute: '2-digit',
                        second: '2-digit'
                    }) : '';

                    const stockAddedVal = parseInt(item.stock_added) || 0;
                    const stockRemovedVal = parseInt(item.stock_removed) || 0;

                    const stockAdded = stockAddedVal > 0
                        ? `<span class="badge bg-success">+${stockAddedVal}</span>`
                        : '<span class="text-muted">-</span>';

                    const stockRemoved = stockRemovedVal > 0
                        ? `<span class="badge bg-danger">-${stockRemovedVal}</span>`
                        : '<span class="text-muted">-</span>';

                    const reference = escapeHtml(item.reference || 'Manual Entry');
                    const performedBy = escapeHtml(item.received_by || 'System');

                    const runningBalance = parseInt(item.running_balance) || 0;

                    // Determine balance color based on stock level
                    let balanceClass = 'text-primary';
                    if (runningBalance === 0) {
                        balanceClass = 'text-danger';
                    } else if (runningBalance < 10) {
                        balanceClass = 'text-warning';
                    }

                    totalAdded += stockAddedVal;
                    totalRemoved += stockRemovedVal;

                    content += `
                        <tr>
                            <td>
                                <div class="d-flex flex-column">
                                    <span class="fw-bold">${formattedDate}</span>
                                    <small class="text-muted">${formattedTime}</small>
                                </div>
                            </td>
                            <td class="text-center">${stockAdded}</td>
                            <td class="text-center">${stockRemoved}</td>
                            <td>
                                <span class="badge bg-info bg-opacity-10 text-dark">
                                    <i class="bi bi-link-45deg"></i> ${reference}
                                </span>
                            </td>
                            <td>
                                <span class="badge bg-secondary bg-opacity-10 text-dark">
                                    <i class="bi bi-person-circle"></i> ${performedBy}
                                </span>
                            </td>
                            <td class="text-center">
                                <strong class="${balanceClass}" style="font-size: 1.1em;">${runningBalance}</strong>
                            </td>
                        </tr>
                    `;
                } catch (err) {
                    console.error('Error rendering row:', err, item);
                }
            });

            // Add summary row
            const currentBalance = data.history.length > 0 ? (parseInt(data.history[data.history.length - 1].running_balance) || 0) : 0;

            content += `
                    <tr class="table-light fw-bold">
                        <td class="text-end">SUMMARY:</td>
                        <td class="text-center text-success">+${totalAdded}</td>
                        <td class="text-center text-danger">-${totalRemoved}</td>
                        <td colspan="2" class="text-center">Total Transactions: ${data.history.length}</td>
                        <td class="text-center text-primary" style="font-size: 1.2em;">${currentBalance}</td>
                    </tr>
            `;
        }

        content += `
                    </tbody>
                </table>
            </div>
            <div class="mt-3">
                <div class="alert alert-info mb-0">
                    <i class="bi bi-info-circle"></i> <strong>Legend:</strong>
                    <ul class="mb-0 mt-2">
                        <li><strong>Stock Added:</strong> Incoming stock from purchases, returns, or manual adjustments</li>
                        <li><strong>Stock Removed:</strong> Outgoing stock from sales or manual adjustments</li>
                        <li><strong>Reference Number:</strong> Associated PO number, GRN number, or transaction identifier</li>
                        <li><strong>Performed By:</strong> User who performed the transaction</li>
                        <li><strong>Running Balance:</strong> Current stock level after each transaction</li>
                    </ul>
                </div>
            </div>
        `;

        $('#stockHistoryContent').html(content);
    }).fail(function(xhr) {
        console.error('Stock history API error:', xhr);
        const errorMsg = escapeHtml((xhr.responseJSON && xhr.responseJSON.error) ? xhr.responseJSON.error : 'Failed to load stock history. Please try again.');
        $('#stockHistoryContent').html(`
            <div class="alert alert-danger">
                <i class="bi bi-exclamation-triangle"></i> <strong>Error:</strong> ${errorMsg}
                <p class="mb-0 mt-2">Please try again or contact support if the issue persists.</p>
            </div>
        `);
    });
}