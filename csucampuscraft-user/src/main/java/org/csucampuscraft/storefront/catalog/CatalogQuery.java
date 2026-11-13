package org.csucampuscraft.storefront.catalog;

import java.util.Objects;
import org.csucampuscraft.storefront.foundation.validation.InputChecks;

/** Canonical server-bound public query; raw text is retained for escaped form feedback. */
public record CatalogQuery(Long categoryId, ProductType type, String q, ProductSort sort,
                           long page, int size) {
    public CatalogQuery {
        Objects.requireNonNull(type);
        Objects.requireNonNull(q);
        Objects.requireNonNull(sort);
        if (page < 1 || size < 1 || size > 50) throw new IllegalArgumentException("Noncanonical catalog query");
    }

    public static CatalogQuery bind(String categoryId, String type, String q, String sort,
                                    String page, String size) {
        Long themeId = categoryId == null || categoryId.isBlank() ? null
                : InputChecks.longInteger("categoryId", categoryId, Long.MIN_VALUE, Long.MAX_VALUE);
        ProductType parsedType = type == null ? ProductType.ALL
                : InputChecks.enumeration("type", type, ProductType.class);
        String keyword = InputChecks.text("q", q, 0, 120);
        ProductSort parsedSort = sort == null ? ProductSort.DEFAULT
                : InputChecks.enumeration("sort", sort, ProductSort.class);
        long parsedPage = page == null ? 1
                : InputChecks.longInteger("page", page, Long.MIN_VALUE, Long.MAX_VALUE);
        int parsedSize = size == null ? 6 : InputChecks.integer("size", size, 1, 50);
        return new CatalogQuery(themeId, parsedType, keyword, parsedSort,
                Math.max(1, parsedPage), parsedSize);
    }

    public Long getCategoryId() { return categoryId; }
    public ProductType getType() { return type; }
    public String getQ() { return q; }
    public ProductSort getSort() { return sort; }
    public long getPage() { return page; }
    public int getSize() { return size; }

    /** An explicit ! escape leaves backslash literal under either MySQL SQL mode. */
    public String getLikePattern() {
        return q.isEmpty() ? null : "%" + q.replace("!", "!!").replace("%", "!%").replace("_", "!_") + "%";
    }
}
