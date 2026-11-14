package org.csucampuscraft.admin.order;

public enum OrderStatus {
    PENDING_PAYMENT("待支付"), PAID("待发货"), SHIPPED("已发货"),
    COMPLETED("已完成"), CANCELLED("已取消");
    private final String label;
    OrderStatus(String label) { this.label = label; }
    public String getValue() { return name(); }
    public String getLabel() { return label; }
}
