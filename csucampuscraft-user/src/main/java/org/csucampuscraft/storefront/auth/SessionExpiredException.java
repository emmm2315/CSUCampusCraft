package org.csucampuscraft.storefront.auth;

/** A transaction-time identity failure; renew this application's authentication. */
public final class SessionExpiredException extends RuntimeException {
    public SessionExpiredException() { super("Authentication must be renewed"); }
}
