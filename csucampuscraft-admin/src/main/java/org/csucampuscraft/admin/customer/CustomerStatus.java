package org.csucampuscraft.admin.customer;

public enum CustomerStatus {
    ENABLED("启用"), DISABLED("禁用");
    private final String label;
    CustomerStatus(String label) { this.label = label; }
    public String getValue() { return name(); }
    public String getLabel() { return label; }
}
