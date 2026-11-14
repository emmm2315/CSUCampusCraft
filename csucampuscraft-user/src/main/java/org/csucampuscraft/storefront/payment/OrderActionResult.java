package org.csucampuscraft.storefront.payment;

/** Safe outcome labels only; receipts and receiver details are read from the owned order page. */
public enum OrderActionResult {
    PAYMENT_FAILED,
    PAYMENT_SUCCEEDED,
    PAYMENT_ALREADY_SUCCEEDED,
    ORDER_CANCELLED,
    ORDER_ALREADY_CANCELLED
}
