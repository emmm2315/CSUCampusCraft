package org.csucampuscraft.admin.order;

/** Safe customer filter label; never contains authentication fields. */
public record OrderCustomer(long id, String username, String displayName, String status) {
    public long getId() { return id; }
    public String getUsername() { return username; }
    public String getDisplayName() { return displayName; }
    public String getStatus() { return status; }
    @Override public String toString() { return "OrderCustomer[id=" + id + ", details=REDACTED]"; }
}
