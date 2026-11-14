package org.csucampuscraft.storefront.cart;

import java.math.BigDecimal;

/** Private cart persistence projection; product columns always contain current database values. */
public final class CartItem {
    private Long id;
    private Long userId;
    private Long productId;
    private Integer quantity;
    private Long version;
    private String sku;
    private String name;
    private String coverImage;
    private BigDecimal price;
    private Integer stock;
    private String status;

    public Long getId() { return id; }
    public Long getUserId() { return userId; }
    public Long getProductId() { return productId; }
    public Integer getQuantity() { return quantity; }
    public Long getVersion() { return version; }
    public String getSku() { return sku; }
    public String getName() { return name; }
    public String getCoverImage() { return coverImage; }
    public BigDecimal getPrice() { return price; }
    public Integer getStock() { return stock; }
    public String getStatus() { return status; }
}
