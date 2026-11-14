package org.csucampuscraft.storefront.checkout;

import java.io.Serializable;
import java.math.BigDecimal;

/** Immutable confirmation values, detached from mutable MyBatis cart projections. */
public record CheckoutLine(long itemId, long productId, int quantity, long itemVersion,
                           BigDecimal unitPrice, BigDecimal subtotal, String sku,
                           String name, String coverImage) implements Serializable {
    private static final long serialVersionUID = 1L;
    public long getItemId() { return itemId; }
    public long getProductId() { return productId; }
    public int getQuantity() { return quantity; }
    public long getItemVersion() { return itemVersion; }
    public BigDecimal getUnitPrice() { return unitPrice; }
    public BigDecimal getSubtotal() { return subtotal; }
    public String getSku() { return sku; }
    public String getName() { return name; }
    public String getCoverImage() { return coverImage; }
}
