package org.csucampuscraft.storefront.order;

import org.csucampuscraft.storefront.foundation.validation.InputChecks;

/** Exact order number comparison; database collation supplies case-insensitivity. */
public record OrderQuery(String orderNo, String status, long page, int size) {
    public OrderQuery {
        if (orderNo == null || status == null || page < 1 || size < 1 || size > 50) {
            throw new IllegalArgumentException("Noncanonical order query");
        }
    }
    public static OrderQuery bind(String orderNo, String status, String page, String size) {
        String number = InputChecks.text("orderNo", orderNo, 0, 40);
        String state = status == null || "ALL".equals(status.strip()) ? "ALL"
                : InputChecks.enumeration("status", status, OrderStatus.class).name();
        long requested = page == null ? 1
                : InputChecks.longInteger("page", page, Long.MIN_VALUE, Long.MAX_VALUE);
        int limit = size == null ? 10 : InputChecks.integer("size", size, 1, 50);
        return new OrderQuery(number, state, Math.max(1, requested), limit);
    }
    public String getOrderNo() { return orderNo; }
    public String getStatus() { return status; }
    public long getPage() { return page; }
    public int getSize() { return size; }
    public boolean isOffsetRepresentable() { return page - 1 <= Long.MAX_VALUE / size; }
    public long getOffset() {
        if (!isOffsetRepresentable()) throw new IllegalStateException("Order offset is not representable");
        return (page - 1) * size;
    }
}
