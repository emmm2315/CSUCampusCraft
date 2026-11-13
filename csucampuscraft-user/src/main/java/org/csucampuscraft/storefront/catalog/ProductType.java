package org.csucampuscraft.storefront.catalog;

import java.util.Locale;

/** Public type choices derive from stable category-code suffixes, never display names. */
public enum ProductType {
    ALL("全部", null), STATIONERY("文具", "_STATIONERY"), SOUVENIR("纪念周边", "_SOUVENIR");

    private final String label;
    private final String suffix;
    ProductType(String label, String suffix) { this.label = label; this.suffix = suffix; }
    public String getLabel() { return label; }
    public String getSuffix() { return suffix; }
    public int getSuffixLength() { return suffix == null ? 0 : suffix.length(); }

    public static ProductType fromCategoryCode(String code) {
        if (code != null) {
            String normalized = code.toUpperCase(Locale.ROOT);
            for (ProductType type : values()) {
                if (type.suffix != null && normalized.endsWith(type.suffix)) return type;
            }
        }
        return null;
    }
}
