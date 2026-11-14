package org.csucampuscraft.admin.order;

import java.util.List;

public record OrderDetail(SalesOrder order, List<SalesOrderItem> items) {
    public OrderDetail { items = List.copyOf(items); }
    public SalesOrder getOrder() { return order; }
    public List<SalesOrderItem> getItems() { return items; }
    @Override public String toString() { return "OrderDetail[receiver=REDACTED]"; }
}
