package org.csucampuscraft.storefront.auth;

/** Transaction-time identity failure; the MVC handler clears only this application's session identity. */
public final class SessionExpiredException extends RuntimeException {
    public SessionExpiredException() { super("Authentication must be renewed"); }
}
