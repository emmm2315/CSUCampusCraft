package org.csucampuscraft.storefront.cart;

import java.math.BigDecimal;
import java.util.List;

/** Total is the current subtotal of valid rows; quantity includes every row, including invalid ones. */
public record CartPage(List<CartLine> items, BigDecimal total, boolean checkoutAllowed, long totalQuantity) {
    public CartPage { items = List.copyOf(items); }
    public List<CartLine> getItems() { return items; }
    public BigDecimal getTotal() { return total; }
    public boolean isCheckoutAllowed() { return checkoutAllowed; }
    public long getTotalQuantity() { return totalQuantity; }
    public boolean isEmpty() { return items.isEmpty(); }
}
