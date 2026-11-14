package org.csucampuscraft.admin.auth;

/** The only account projection permitted in a request model. */
public record AuthUser(Long userId, String username, String displayName, String role) {
    public Long getUserId() { return userId; }
    public String getUsername() { return username; }
    public String getDisplayName() { return displayName; }
    public String getRole() { return role; }
}
