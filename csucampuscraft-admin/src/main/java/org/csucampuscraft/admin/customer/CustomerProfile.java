package org.csucampuscraft.admin.customer;

import java.time.LocalDateTime;
import java.time.ZoneOffset;
import java.time.ZoneId;
import java.time.format.DateTimeFormatter;

/** Safe page projection: never contains a password, hash, or editable account fields. */
public record CustomerProfile(long id, String username, String displayName, String status,
                              String email, String phone, LocalDateTime createdAt, LocalDateTime updatedAt) {
    private static final DateTimeFormatter DISPLAY = DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss");
    private static final ZoneId DISPLAY_ZONE = ZoneId.of("Asia/Shanghai");
    public long getId() { return id; }
    public String getUsername() { return username; }
    public String getDisplayName() { return displayName; }
    public String getStatus() { return status; }
    public String getStatusLabel() { return CustomerStatus.valueOf(status).getLabel(); }
    public String getEmail() { return email; }
    public String getPhone() { return phone; }
    public LocalDateTime getCreatedAt() { return createdAt; }
    public LocalDateTime getUpdatedAt() { return updatedAt; }
    public String getCreatedAtDisplay() { return display(createdAt); }
    public String getUpdatedAtDisplay() { return display(updatedAt); }
    public boolean isEnabled() { return "ENABLED".equals(status); }
    private static String display(LocalDateTime value) {
        return value == null ? null : value.atOffset(ZoneOffset.UTC).atZoneSameInstant(DISPLAY_ZONE).format(DISPLAY);
    }
    @Override public String toString() { return "CustomerProfile[id=" + id + ", details=REDACTED]"; }
}
