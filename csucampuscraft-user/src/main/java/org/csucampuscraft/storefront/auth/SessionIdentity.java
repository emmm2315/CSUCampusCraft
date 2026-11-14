package org.csucampuscraft.storefront.auth;

import java.io.Serializable;
import java.time.LocalDateTime;
import java.util.Objects;

/** UTC database value retained exactly, including microseconds. */
public record SessionIdentity(Long userId, LocalDateTime authStamp) implements Serializable {
    private static final long serialVersionUID = 1L;
    public SessionIdentity {
        Objects.requireNonNull(userId);
        Objects.requireNonNull(authStamp);
        if (userId < 1) throw new IllegalArgumentException("Invalid identity");
    }
    public Long getUserId() { return userId; }
    public LocalDateTime getAuthStamp() { return authStamp; }
}

