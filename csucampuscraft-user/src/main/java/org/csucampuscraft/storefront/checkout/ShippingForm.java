package org.csucampuscraft.storefront.checkout;

/** Request-scoped redisplay only: never retained in the session or diagnostic output. */
public record ShippingForm(String receiverName, String receiverPhone, String receiverAddress) {
    public ShippingForm {
        receiverName = receiverName == null ? "" : receiverName;
        receiverPhone = receiverPhone == null ? "" : receiverPhone;
        receiverAddress = receiverAddress == null ? "" : receiverAddress;
    }
    public static ShippingForm empty() { return new ShippingForm("", "", ""); }
    public String getReceiverName() { return receiverName; }
    public String getReceiverPhone() { return receiverPhone; }
    public String getReceiverAddress() { return receiverAddress; }
    @Override public String toString() { return "ShippingForm[REDACTED]"; }
}
