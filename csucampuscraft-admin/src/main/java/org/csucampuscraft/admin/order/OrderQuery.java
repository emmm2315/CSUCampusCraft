package org.csucampuscraft.admin.order;

import org.csucampuscraft.admin.foundation.validation.InputChecks;

/** Values are bound parameters; collation provides exact case-insensitive number matching. */
public record OrderQuery(String orderNo, String status, Long userId, long page, int size) {
    public OrderQuery {
        if (orderNo == null || status == null || (userId != null && userId < 1)
                || page < 1 || size < 1 || size > 50) {
            throw new IllegalArgumentException("Noncanonical administrator order query");
        }
    }
    public static OrderQuery bind(String orderNo, String status, String userId, String page, String size) {
        String number = InputChecks.text("orderNo", orderNo, 0, 40);
        String state = status == null || "ALL".equals(status.strip()) ? "ALL"
                : InputChecks.enumeration("status", status, OrderStatus.class).name();
        Long customer = userId == null || userId.strip().isEmpty() ? null
                : InputChecks.longInteger("userId", userId, 1, Long.MAX_VALUE);
        long requested = page == null ? 1
                : InputChecks.longInteger("page", page, Long.MIN_VALUE, Long.MAX_VALUE);
        int limit = size == null ? 10 : InputChecks.integer("size", size, 1, 50);
        return new OrderQuery(number, state, customer, Math.max(1, requested), limit);
    }
    public String getOrderNo() { return orderNo; }
    public String getStatus() { return status; }
    public Long getUserId() { return userId; }
    public long getPage() { return page; }
    public int getSize() { return size; }
    public boolean isOffsetRepresentable() { return page - 1 <= Long.MAX_VALUE / size; }
    /** MyBatis record properties require the exact accessor, including derived offset. */
    public long offset() {
        if (!isOffsetRepresentable()) throw new IllegalStateException("Order offset is not representable");
        return (page - 1) * size;
    }
    public long getOffset() { return offset(); }
}
