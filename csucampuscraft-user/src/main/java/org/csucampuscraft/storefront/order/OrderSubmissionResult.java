package org.csucampuscraft.storefront.order;

import org.csucampuscraft.storefront.checkout.CheckoutService;

/** A field-error response or a committed order number, never diagnostic receiver data. */
public record OrderSubmissionResult(String orderNo, CheckoutService.Validation validation) {
    public String getOrderNo() { return orderNo; }
    public CheckoutService.Validation getValidation() { return validation; }
    public boolean isCreated() { return orderNo != null; }
    @Override public String toString() { return "OrderSubmissionResult[receiver=REDACTED]"; }
}
