package org.csucampuscraft.storefront.cart;

import java.math.BigDecimal;

/** Read projection joined to the current product; invalid rows remain visible and removable. */
public class CartLine {
    private Long id;
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
    public Long getProductId() { return productId; }
    public Integer getQuantity() { return quantity; }
    public Long getVersion() { return version; }
    public String getSku() { return sku; }
    public String getName() { return name; }
    public String getCoverImage() { return coverImage; }
    public BigDecimal getPrice() { return price; }
    public Integer getStock() { return stock; }
    public String getStatus() { return status; }

    public boolean isPublicProduct() { return "ON_SALE".equals(status); }
    public String getInvalidCode() {
        if (price == null || stock == null || status == null) return "UNAVAILABLE";
        if (!isPublicProduct()) return "DRAFT";
        if (stock == 0) return "SOLD_OUT";
        if (quantity > stock) return "OVER_STOCK";
        return "VALID";
    }
    public boolean isValid() { return "VALID".equals(getInvalidCode()); }
    public String getInvalidReason() {
        return switch (getInvalidCode()) {
            case "DRAFT" -> "商品已下架，可移除此条目。";
            case "SOLD_OUT" -> "商品已售罄，可移除此条目。";
            case "OVER_STOCK" -> "数量超过当前库存，请减少数量或移除。";
            case "UNAVAILABLE" -> "商品暂不可用，可移除此条目。";
            default -> "";
        };
    }
    public BigDecimal getSubtotal() {
        return isValid() ? price.multiply(BigDecimal.valueOf(quantity)).setScale(2)
                : new BigDecimal("0.00");
    }
}
