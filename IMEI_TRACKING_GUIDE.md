# IMEI Tracking System - Implementation Guide

## Overview
Your inventory system now has complete IMEI tracking functionality. When you receive stock with IMEI numbers, the system tracks each individual unit, and when products are sold, you can see exactly which IMEI number was sold.

## Database Changes

### New Table: `product_imei`
Tracks individual IMEI numbers for each product with the following fields:
- `id`: Unique identifier for the IMEI record
- `product_id`: Links to the product
- `imei`: The actual IMEI number (unique across all products)
- `status`: Either `available` or `sold`
- `grn_id`: Links to the Goods Receipt Note when received
- `stock_movement_id`: Links to the stock movement record
- `received_date`: When the IMEI was received
- `sale_id`: Links to the POS sale when sold
- `sold_date`: When the IMEI was sold

## API Endpoints

### 1. Add IMEI Numbers to a Product
**POST** `/api/products/<product_id>/imeis`

**Request Body:**
```json
{
  "imeis": ["123456789012345", "987654321098765"],
  "grn_id": 1,
  "stock_movement_id": 5
}
```

**Response:**
```json
{
  "success": true,
  "added": 2,
  "imeis": ["123456789012345", "987654321098765"]
}
```

### 2. Get All IMEIs for a Product
**GET** `/api/products/<product_id>/imeis?status=available`

Query Parameters:
- `status` (optional): Filter by status (`available` or `sold`)

**Response:**
```json
[
  {
    "id": 1,
    "product_id": 10,
    "imei": "123456789012345",
    "status": "available",
    "grn_id": 1,
    "received_date": "2025-11-11 07:00:00",
    "sale_id": null,
    "sold_date": null,
    "sale_number": null,
    "customer_name": null
  },
  {
    "id": 2,
    "product_id": 10,
    "imei": "987654321098765",
    "status": "sold",
    "grn_id": 1,
    "received_date": "2025-11-11 07:00:00",
    "sale_id": 25,
    "sold_date": "2025-11-11 08:30:00",
    "sale_number": "POS-20251111083000",
    "customer_name": "John Doe"
  }
]
```

### 3. Delete an IMEI
**DELETE** `/api/imeis/<imei_id>`

Note: Can only delete IMEIs with status `available` (not sold)

### 4. Search Products by IMEI
**GET** `/api/products/search-by-imei?imei=123456789`

Find products by IMEI number (partial matching supported)

## How It Works

### When Receiving Stock (Purchase Orders/GRN)

When you receive items through **POST** `/api/purchase-orders/<id>/receive`, you can now include IMEI numbers in each item:

**Request Example:**
```json
{
  "payment_status": "paid",
  "storage_location": "Warehouse A",
  "items": [
    {
      "id": 1,
      "received_quantity": 2,
      "damaged_quantity": 0,
      "imeis": ["123456789012345", "987654321098765"]
    }
  ]
}
```

**What happens:**
1. Stock quantity is updated
2. Each IMEI number is stored in the `product_imei` table
3. IMEIs are linked to the GRN and stock movement
4. All IMEIs are marked as `available`

### When Selling Products (POS)

When creating a sale through **POST** `/api/pos/sales`, you now provide IMEI IDs (not IMEI strings):

**Request Example:**
```json
{
  "customer_name": "John Doe",
  "payment_method": "cash",
  "items": [
    {
      "product_id": 10,
      "quantity": 1,
      "unit_price": 599.00,
      "imei_ids": [1]
    }
  ]
}
```

**What happens:**
1. System validates that all IMEI IDs belong to the product
2. System checks that all IMEIs have status `available`
3. System validates that the number of IMEI IDs matches the quantity
4. Stock is deducted
5. IMEIs are marked as `sold` with the sale ID and sold date
6. Sale is recorded with IMEI numbers for display

**Important Features:**
- **Race Condition Protection**: If two cashiers try to sell the same IMEI simultaneously, one will fail with an error message
- **Atomic Updates**: All IMEIs must be successfully marked as sold, or the entire sale is rolled back
- **Validation**: You cannot sell an item with IMEI tracking without providing the correct number of IMEI IDs

### When Processing Returns

For returns, provide the same IMEI IDs that were sold:

**Request Example:**
```json
{
  "transaction_type": "return",
  "items": [
    {
      "product_id": 10,
      "quantity": 1,
      "unit_price": 599.00,
      "imei_ids": [1]
    }
  ]
}
```

**What happens:**
1. System validates that the IMEIs are currently `sold`
2. Stock is added back
3. IMEIs are marked as `available` again
4. Sale and sold date are cleared

## Viewing IMEI Tracking

### Get IMEI Tracking for a Product
**GET** `/api/products/<product_id>/imei-tracking`

This endpoint shows all IMEI records for a product with purchase information.

### In Sales Reports

When you query sales, the IMEI numbers are stored in the `pos_sale_items.imei` field as a comma-separated string. You can see exactly which IMEI numbers were sold in each transaction.

## Frontend Integration Notes

To fully integrate IMEI tracking in the frontend:

1. **Stock Receiving Screen**: Add input fields for IMEI numbers when receiving items
2. **POS Screen**: When selecting a product, show available IMEIs and let the cashier select which ones to sell
3. **Inventory View**: Add a column or detail view showing IMEI count (available/sold)
4. **Product Detail Page**: Show all IMEIs for a product with their status and sale history

## Example Workflow

1. **Receive 5 phones**:
   ```
   POST /api/purchase-orders/1/receive
   {
     "items": [{
       "id": 1,
       "received_quantity": 5,
       "imeis": ["111111", "222222", "333333", "444444", "555555"]
     }]
   }
   ```

2. **Check available IMEIs**:
   ```
   GET /api/products/10/imeis?status=available
   Returns: 5 available IMEIs
   ```

3. **Sell 2 phones**:
   ```
   POST /api/pos/sales
   {
     "items": [{
       "product_id": 10,
       "quantity": 2,
       "unit_price": 599,
       "imei_ids": [1, 2]  // IDs of IMEI records
     }]
   }
   ```

4. **Check inventory**:
   ```
   GET /api/products/10/imeis
   Shows: 2 sold (with sale details), 3 available
   ```

## Benefits

✅ **Complete Traceability**: Know exactly which IMEI was sold to which customer
✅ **Prevent Double-Selling**: Race condition protection ensures each IMEI is sold only once
✅ **Accurate Inventory**: Track individual units, not just quantities
✅ **Return Management**: Properly handle returns by restoring IMEI availability
✅ **Audit Trail**: Full history of when each IMEI was received and sold

## Next Steps

The backend is fully implemented and tested. To complete the frontend:
1. Add IMEI input fields to the stock receiving modal
2. Add IMEI selection to the POS interface
3. Display IMEI information in inventory and sales views
4. Add IMEI search functionality to quickly find products by IMEI

The API is ready to use and all endpoints are working correctly!
