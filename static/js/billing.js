
/**
 * Billing Summary Calculator
 * Calculates per-product totals and grand total for POS transactions
 */

class BillingCalculator {
    /**
     * Calculate billing summary from array of products
     * @param {Array} products - Array of product objects with name, price, qty, discount
     * @returns {Object} Billing summary with items and grand_total
     */
    static calculateBillingSummary(products) {
        if (!Array.isArray(products) || products.length === 0) {
            return {
                items: [],
                grand_total: 0,
                error: 'No products provided'
            };
        }

        const items = [];
        let grandTotal = 0;

        products.forEach((product, index) => {
            // Validate product data
            if (!product.name || typeof product.price !== 'number' || typeof product.qty !== 'number') {
                console.warn(`Invalid product at index ${index}:`, product);
                return;
            }

            const name = product.name;
            const unitPrice = parseFloat(product.price) || 0;
            const qty = parseInt(product.qty) || 0;
            const discount = parseFloat(product.discount) || 0;

            // Calculate total for this product
            const subtotal = unitPrice * qty;
            const total = subtotal - discount;

            // Add to items array
            items.push({
                name: name,
                unit_price: unitPrice,
                qty: qty,
                discount: discount,
                total: parseFloat(total.toFixed(2))
            });

            // Add to grand total
            grandTotal += total;
        });

        return {
            items: items,
            grand_total: parseFloat(grandTotal.toFixed(2))
        };
    }

    /**
     * Calculate billing summary with percentage discount
     * @param {Array} products - Array of product objects with name, price, qty, discount_percent
     * @returns {Object} Billing summary with items and grand_total
     */
    static calculateBillingSummaryWithPercent(products) {
        if (!Array.isArray(products) || products.length === 0) {
            return {
                items: [],
                grand_total: 0,
                error: 'No products provided'
            };
        }

        const items = [];
        let grandTotal = 0;

        products.forEach((product, index) => {
            if (!product.name || typeof product.price !== 'number' || typeof product.qty !== 'number') {
                console.warn(`Invalid product at index ${index}:`, product);
                return;
            }

            const name = product.name;
            const unitPrice = parseFloat(product.price) || 0;
            const qty = parseInt(product.qty) || 0;
            const discountPercent = parseFloat(product.discount_percent) || 0;

            // Calculate total for this product
            const subtotal = unitPrice * qty;
            const discountAmount = subtotal * (discountPercent / 100);
            const total = subtotal - discountAmount;

            items.push({
                name: name,
                unit_price: unitPrice,
                qty: qty,
                discount_percent: discountPercent,
                discount: parseFloat(discountAmount.toFixed(2)),
                total: parseFloat(total.toFixed(2))
            });

            grandTotal += total;
        });

        return {
            items: items,
            grand_total: parseFloat(grandTotal.toFixed(2))
        };
    }

    /**
     * Format billing summary for display
     * @param {Object} billingSummary - Result from calculateBillingSummary
     * @returns {String} HTML formatted summary
     */
    static formatBillingSummaryHTML(billingSummary) {
        if (!billingSummary.items || billingSummary.items.length === 0) {
            return '<p class="text-muted">No items in cart</p>';
        }

        let html = `
            <div class="billing-summary">
                <table class="table table-sm">
                    <thead>
                        <tr>
                            <th>Product</th>
                            <th class="text-center">Qty</th>
                            <th class="text-end">Price</th>
                            <th class="text-end">Discount</th>
                            <th class="text-end">Total</th>
                        </tr>
                    </thead>
                    <tbody>
        `;

        billingSummary.items.forEach(item => {
            html += `
                <tr>
                    <td>${item.name}</td>
                    <td class="text-center">${item.qty}</td>
                    <td class="text-end">₹${item.unit_price.toFixed(2)}</td>
                    <td class="text-end">${item.discount > 0 ? '-₹' + item.discount.toFixed(2) : '-'}</td>
                    <td class="text-end"><strong>₹${item.total.toFixed(2)}</strong></td>
                </tr>
            `;
        });

        html += `
                    </tbody>
                    <tfoot>
                        <tr class="table-primary">
                            <td colspan="4" class="text-end"><strong>Grand Total:</strong></td>
                            <td class="text-end"><strong>₹${billingSummary.grand_total.toFixed(2)}</strong></td>
                        </tr>
                    </tfoot>
                </table>
            </div>
        `;

        return html;
    }

    /**
     * Format billing summary for plain text receipt
     * @param {Object} billingSummary - Result from calculateBillingSummary
     * @returns {String} Plain text formatted summary
     */
    static formatBillingSummaryText(billingSummary) {
        if (!billingSummary.items || billingSummary.items.length === 0) {
            return 'No items in cart';
        }

        let text = '================================\n';
        text += '         BILLING SUMMARY        \n';
        text += '================================\n\n';

        billingSummary.items.forEach((item, index) => {
            text += `${index + 1}. ${item.name}\n`;
            text += `   Price: ₹${item.unit_price.toFixed(2)} x ${item.qty}\n`;
            if (item.discount > 0) {
                text += `   Discount: -₹${item.discount.toFixed(2)}\n`;
            }
            text += `   Total: ₹${item.total.toFixed(2)}\n\n`;
        });

        text += '================================\n';
        text += `GRAND TOTAL: ₹${billingSummary.grand_total.toFixed(2)}\n`;
        text += '================================\n';

        return text;
    }
}

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = BillingCalculator;
}
