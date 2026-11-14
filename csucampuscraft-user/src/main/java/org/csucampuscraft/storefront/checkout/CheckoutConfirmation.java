package org.csucampuscraft.storefront.checkout;

import java.io.Serializable;
import java.math.BigDecimal;
import java.time.Instant;
import java.util.List;

/** One latest server-side confirmation; contains no receiver details or client amounts. */
public final class CheckoutConfirmation implements Serializable {
    private static final long serialVersionUID = 1L;
    private final String token;
    private final Instant createdAt;
    private final Instant expiresAt;
    private final long userId;
    private final List<CheckoutLine> items;
    private final BigDecimal total;

    CheckoutConfirmation(String token, Instant createdAt, Instant expiresAt, long userId,
                         List<CheckoutLine> items, BigDecimal total) {
        this.token = token;
        this.createdAt = createdAt;
        this.expiresAt = expiresAt;
        this.userId = userId;
        this.items = List.copyOf(items);
        this.total = total;
    }

    String token() { return token; }
    public Instant getCreatedAt() { return createdAt; }
    public Instant getExpiresAt() { return expiresAt; }
    public long getUserId() { return userId; }
    public List<CheckoutLine> getItems() { return items; }
    public BigDecimal getTotal() { return total; }
    public int getItemCount() { return items.size(); }
    public long getQuantity() { return items.stream().mapToLong(CheckoutLine::quantity).sum(); }

    @Override
    public String toString() {
        return "CheckoutConfirmation[items=" + items.size() + ", token=REDACTED]";
    }
}
