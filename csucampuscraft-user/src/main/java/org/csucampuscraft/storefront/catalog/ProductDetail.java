package org.csucampuscraft.storefront.catalog;

public record ProductDetail(Product product, Category theme, Category category, java.util.List<ProductImage> images) {
    public Product getProduct() { return product; }
    public Category getTheme() { return theme; }
    public Category getCategory() { return category; }
    public java.util.List<ProductImage> getImages() { return images; }
}
