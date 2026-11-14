package org.csucampuscraft.admin.customer;

import org.csucampuscraft.admin.foundation.validation.InputChecks;

public record CustomerQuery(String q, String status, long page, int size) {
    public CustomerQuery {
        if (q == null || status == null || page < 1 || size < 1 || size > 50) {
            throw new IllegalArgumentException("Noncanonical customer query");
        }
    }
    public static CustomerQuery bind(String q, String status, String page, String size) {
        String keyword = InputChecks.text("q", q, 0, 50);
        String state = status == null || "ALL".equals(status.strip()) ? "ALL"
                : InputChecks.enumeration("status", status, CustomerStatus.class).name();
        long requested = page == null ? 1 : InputChecks.longInteger("page", page, Long.MIN_VALUE, Long.MAX_VALUE);
        int limit = size == null ? 10 : InputChecks.integer("size", size, 1, 50);
        return new CustomerQuery(keyword, state, Math.max(1, requested), limit);
    }
    public String getQ() { return q; }
    public String getStatus() { return status; }
    public long getPage() { return page; }
    public int getSize() { return size; }
    public boolean isOffsetRepresentable() { return page - 1 <= Long.MAX_VALUE / size; }
    public long offset() {
        if (!isOffsetRepresentable()) throw new IllegalStateException("Customer offset is not representable");
        return (page - 1) * size;
    }
    public long getOffset() { return offset(); }
    /** ! is the explicit SQL escape: backslash itself is an ordinary literal. */
    public String likePattern() {
        return q.isEmpty() ? null : "%" + q.replace("!", "!!").replace("%", "!%").replace("_", "!_") + "%";
    }
    public String getLikePattern() { return likePattern(); }
}
