package org.csucampuscraft.storefront.cart;

import java.math.BigDecimal;

/** Safe page model: no client-supplied price or ownership participates in cart calculations. */
public record CartLine(long id, long productId, String sku, String name, String coverImage,
                       BigDecimal price, int stock, String status, int quantity, long version,
                       BigDecimal subtotal, boolean valid, String invalidReason) {
    public long getId() { return id; }
    public long getProductId() { return productId; }
    public String getSku() { return sku; }
    public String getName() { return name; }
    public String getCoverImage() { return coverImage; }
    public BigDecimal getPrice() { return price; }
    public int getStock() { return stock; }
    public String getStatus() { return status; }
    public int getQuantity() { return quantity; }
    public long getVersion() { return version; }
    public BigDecimal getSubtotal() { return subtotal; }
    public boolean isValid() { return valid; }
    public String getInvalidReason() { return invalidReason; }
}
