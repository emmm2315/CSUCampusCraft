package org.csucampuscraft.admin.auth;

import java.io.Serializable;
import java.time.LocalDateTime;
import java.util.Objects;

/** Exact database UTC timestamp; never stringify, format, or truncate it for authorization. */
public record SessionIdentity(Long userId, LocalDateTime authStamp) implements Serializable {
    public SessionIdentity {
        Objects.requireNonNull(userId);
        Objects.requireNonNull(authStamp);
        if (userId <= 0) throw new IllegalArgumentException("Invalid identity");
    }

    @Override
    public String toString() { return "SessionIdentity[redacted]"; }
}
