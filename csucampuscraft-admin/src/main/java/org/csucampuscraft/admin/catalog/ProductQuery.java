package org.csucampuscraft.admin.catalog;

import java.net.URLEncoder;
import java.util.Objects;
import java.nio.charset.StandardCharsets;
import org.csucampuscraft.admin.foundation.validation.InputChecks;

public record ProductQuery(Long categoryId, String q, ProductStatus status, long page, int size) {
    public ProductQuery {
        Objects.requireNonNull(q);
        Objects.requireNonNull(status);
        if (page < 1 || size < 1 || size > 50) throw new IllegalArgumentException("Noncanonical product query");
    }
    public static ProductQuery bind(String categoryId, String q, String status, String page, String size) {
        Long category = categoryId == null || categoryId.isBlank() ? null
                : InputChecks.longInteger("categoryId", categoryId, Long.MIN_VALUE, Long.MAX_VALUE);
        String keyword = InputChecks.text("q", q, 0, 120);
        ProductStatus state = status == null ? ProductStatus.ALL
                : InputChecks.enumeration("status", status, ProductStatus.class);
        long requestedPage = page == null ? 1 : InputChecks.longInteger("page", page, Long.MIN_VALUE, Long.MAX_VALUE);
        int requestedSize = size == null ? 10 : InputChecks.integer("size", size, 1, 50);
        return new ProductQuery(category, keyword, state, Math.max(1, requestedPage), requestedSize);
    }
    public Long getCategoryId() { return categoryId; }
    public String getQ() { return q; }
    public ProductStatus getStatus() { return status; }
    public long getPage() { return page; }
    public int getSize() { return size; }
    public String getLikePattern() {
        return q.isEmpty() ? null : "%" + q.replace("!", "!!").replace("%", "!%").replace("_", "!_") + "%";
    }
    public String path(long targetPage) {
        return "/products?" + (categoryId == null ? "" : "categoryId=" + categoryId + "&")
                + "q=" + URLEncoder.encode(q, StandardCharsets.UTF_8)
                + "&status=" + status.name() + "&page=" + targetPage + "&size=" + size;
    }
}
