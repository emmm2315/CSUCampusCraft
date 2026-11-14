package org.csucampuscraft.admin.catalog;

/** Allowlisted raw values kept separately from the database entity for safe form redisplay. */
public record ProductImageInput(String imagePath, String altText, String sortOrder, String productVersion) {
    public String getImagePath() { return imagePath; }
    public String getAltText() { return altText; }
    public String getSortOrder() { return sortOrder; }
    public String getProductVersion() { return productVersion; }
}
