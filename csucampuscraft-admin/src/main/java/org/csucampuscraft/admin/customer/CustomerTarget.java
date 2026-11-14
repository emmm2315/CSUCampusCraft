package org.csucampuscraft.admin.customer;

import java.time.LocalDateTime;

/** Locked write-only safe projection; never placed in a page model. */
public record CustomerTarget(long id, String role, String status, LocalDateTime updatedAt) {
    @Override public String toString() { return "CustomerTarget[id=" + id + ", details=REDACTED]"; }
}
