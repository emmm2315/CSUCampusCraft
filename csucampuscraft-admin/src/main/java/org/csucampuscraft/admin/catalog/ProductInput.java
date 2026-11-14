package org.csucampuscraft.admin.catalog;

/** Raw allowlisted form strings only; never bind request data directly to the database entity. */
public record ProductInput(String sku, String categoryId, String name, String price,
                           String summary, String description, String coverImage,
                           String stock, String sortOrder, String version) {
    public static ProductInput fromProduct(Product p) {
        return new ProductInput(p.getSku(), p.getCategoryId().toString(), p.getName(),
                p.getPrice().toPlainString(), p.getSummary(), p.getDescription(), p.getCoverImage(),
                p.getStock().toString(), p.getSortOrder().toString(), p.getVersion().toString());
    }
    public String getSku() { return sku; }
    public String getCategoryId() { return categoryId; }
    public String getName() { return name; }
    public String getPrice() { return price; }
    public String getSummary() { return summary; }
    public String getDescription() { return description; }
    public String getCoverImage() { return coverImage; }
    public String getStock() { return stock; }
    public String getSortOrder() { return sortOrder; }
    public String getVersion() { return version; }
}
