package org.csucampuscraft.storefront.catalog;

public record HomeCatalog(java.util.List<Category> themes, java.util.List<ThemeNavigation> themeNavigation, Category graduationTheme, java.util.List<Product> newProducts, java.util.List<Product> featuredProducts) {
    public java.util.List<Category> getThemes() { return themes; }
    public java.util.List<ThemeNavigation> getThemeNavigation() { return themeNavigation; }
    public Category getGraduationTheme() { return graduationTheme; }
    public java.util.List<Product> getNewProducts() { return newProducts; }
    public java.util.List<Product> getFeaturedProducts() { return featuredProducts; }
}
