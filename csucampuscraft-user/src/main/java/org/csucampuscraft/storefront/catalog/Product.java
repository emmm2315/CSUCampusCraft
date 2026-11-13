package org.csucampuscraft.storefront.catalog;

/** Read-only catalog projection mapped from the existing product table. */
public final class Product {
    private Long id;
    private String sku;
    private Long categoryId;
    private String name;
    private String summary;
    private String description;
    private String coverImage;
    private java.math.BigDecimal price;
    private Integer stock;
    private String status;
    private Integer sortOrder;
    private Long version;
    private java.time.LocalDateTime createdAt;

    public Long getId() { return id; }
    public String getSku() { return sku; }
    public Long getCategoryId() { return categoryId; }
    public String getName() { return name; }
    public String getSummary() { return summary; }
    public String getDescription() { return description; }
    public String getCoverImage() { return coverImage; }
    public java.math.BigDecimal getPrice() { return price; }
    public Integer getStock() { return stock; }
    public String getStatus() { return status; }
    public Integer getSortOrder() { return sortOrder; }
    public Long getVersion() { return version; }
    public java.time.LocalDateTime getCreatedAt() { return createdAt; }
}
