package org.csucampuscraft.storefront.catalog;

public record ThemeNavigation(Category theme, java.util.List<TypeLink> types) {
    public Category getTheme() { return theme; }
    public java.util.List<TypeLink> getTypes() { return types; }
}
