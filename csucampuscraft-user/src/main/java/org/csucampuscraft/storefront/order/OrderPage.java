package org.csucampuscraft.storefront.order;

import java.util.List;

public record OrderPage(List<SalesOrder> items, long totalCount, OrderQuery query) {
    public OrderPage { items = List.copyOf(items); }
    public List<SalesOrder> getItems() { return items; }
    public long getTotalCount() { return totalCount; }
    public OrderQuery getQuery() { return query; }
    public long getPage() { return query.page(); }
    public int getSize() { return query.size(); }
    public long getTotalPages() { return totalCount / query.size() + (totalCount % query.size() == 0 ? 0 : 1); }
    public long getFirstValidPage() { return Math.max(1, Math.min(query.page(), getTotalPages())); }
    public long getPreviousPage() { return Math.max(1, query.page() - 1); }
    public long getNextPage() { return query.page() == Long.MAX_VALUE ? Long.MAX_VALUE : query.page() + 1; }
    public boolean isEmpty() { return items.isEmpty(); }
    public boolean isHasPrevious() { return query.page() > 1; }
    public boolean isHasNext() { return query.page() < getTotalPages(); }
}
