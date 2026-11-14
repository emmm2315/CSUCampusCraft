package org.csucampuscraft.storefront.auth;

/** Explicitly safe presentation projection; no password or authentication stamp. */
public record AuthUser(Long userId, String username, String displayName, String role) {
    public Long getUserId() { return userId; }
    public String getUsername() { return username; }
    public String getDisplayName() { return displayName; }
    public String getRole() { return role; }
}

