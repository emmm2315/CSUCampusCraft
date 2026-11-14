package org.csucampuscraft.storefront.cart;

import java.math.BigDecimal;
import java.util.List;

/** Server-calculated current cart view; no checkout token or order is produced. */
public record CartPage(List<CartLine> items, long quantity, BigDecimal validSubtotal, int invalidCount) {
    public CartPage { items = List.copyOf(items); }
    public List<CartLine> getItems() { return items; }
    public long getQuantity() { return quantity; }
    public BigDecimal getValidSubtotal() { return validSubtotal; }
    public int getInvalidCount() { return invalidCount; }
    public int getItemCount() { return items.size(); }
    public boolean isEmpty() { return items.isEmpty(); }
    public boolean isHasInvalidItems() { return invalidCount > 0; }
    public boolean isAllValid() { return !items.isEmpty() && invalidCount == 0; }
}
