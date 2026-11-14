package org.csucampuscraft.admin.customer;

import java.util.List;

public record CustomerPage(List<CustomerProfile> items, long totalCount, CustomerQuery query) {
    public CustomerPage { items = List.copyOf(items); }
    public List<CustomerProfile> getItems() { return items; }
    public long getTotalCount() { return totalCount; }
    public CustomerQuery getQuery() { return query; }
    public long getPage() { return query.page(); }
    public int getSize() { return query.size(); }
    public long getTotalPages() { return totalCount / query.size() + (totalCount % query.size() == 0 ? 0 : 1); }
    public long getFirstValidPage() { return Math.max(1, Math.min(query.page(), getTotalPages())); }
    public boolean isEmpty() { return items.isEmpty(); }
    public boolean isHasPrevious() { return query.page() > 1; }
    public boolean isHasNext() { return query.page() < getTotalPages(); }
    @Override public String toString() { return "CustomerPage[count=" + totalCount + ", customerDetails=REDACTED]"; }
}
