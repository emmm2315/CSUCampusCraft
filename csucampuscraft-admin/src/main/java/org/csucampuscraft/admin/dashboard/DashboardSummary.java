package org.csucampuscraft.admin.dashboard;

public record DashboardSummary(long onSaleProductCount, long draftProductCount, long paidOrderCount,
                               long enabledCustomerCount, long disabledCustomerCount) {
    public DashboardSummary {
        if (onSaleProductCount < 0 || draftProductCount < 0 || paidOrderCount < 0
                || enabledCustomerCount < 0 || disabledCustomerCount < 0) {
            throw new IllegalArgumentException("Invalid dashboard counts");
        }
    }
    public long getOnSaleProductCount() { return onSaleProductCount; }
    public long getDraftProductCount() { return draftProductCount; }
    public long getPaidOrderCount() { return paidOrderCount; }
    public long getEnabledCustomerCount() { return enabledCustomerCount; }
    public long getDisabledCustomerCount() { return disabledCustomerCount; }
}
