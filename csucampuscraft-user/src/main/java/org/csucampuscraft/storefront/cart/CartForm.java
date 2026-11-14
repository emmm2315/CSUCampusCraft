package org.csucampuscraft.storefront.cart;

/** Allowlisted raw field values for escaped redisplay after a rejected POST. */
public record CartForm(String quantity, String version) {
    public String getQuantity() { return quantity; }
    public String getVersion() { return version; }
}
