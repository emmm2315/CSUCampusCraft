package org.csucampuscraft.storefront.catalog;

public record CatalogPage(CatalogQuery query, Category selectedTheme, java.util.List<Product> products, long total, long totalPages, boolean hasPrevious, boolean hasNext, long previousPage, long nextPage, java.util.List<Category> themes, java.util.List<ThemeNavigation> themeNavigation) {
    public CatalogQuery getQuery() { return query; }
    public Category getSelectedTheme() { return selectedTheme; }
    public java.util.List<Product> getProducts() { return products; }
    public long getTotal() { return total; }
    public long getTotalPages() { return totalPages; }
    public boolean isHasPrevious() { return hasPrevious; }
    public boolean isHasNext() { return hasNext; }
    public long getPreviousPage() { return previousPage; }
    public long getNextPage() { return nextPage; }
    public java.util.List<Category> getThemes() { return themes; }
    public java.util.List<ThemeNavigation> getThemeNavigation() { return themeNavigation; }
}
