package org.csucampuscraft.storefront.catalog;

/** Read-only catalog projection mapped from the existing product_image table. */
public final class ProductImage {
    private Long id;
    private Long productId;
    private String imagePath;
    private String altText;
    private Integer sortOrder;

    public Long getId() { return id; }
    public Long getProductId() { return productId; }
    public String getImagePath() { return imagePath; }
    public String getAltText() { return altText; }
    public Integer getSortOrder() { return sortOrder; }
}
