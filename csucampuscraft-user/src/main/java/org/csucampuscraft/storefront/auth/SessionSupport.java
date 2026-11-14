package org.csucampuscraft.storefront.auth;

import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpSession;
import org.springframework.stereotype.Component;

@Component
public final class SessionSupport {
    public static final String IDENTITY_ATTRIBUTE = "CSUCAMPUSCRAFT_AUTH_IDENTITY";
    public static final String CHECKOUT_CONFIRMATION_ATTRIBUTE = "CSUCAMPUSCRAFT_CHECKOUT_CONFIRMATION";
    public static final String CURRENT_USER_ATTRIBUTE = "csucampuscraft.currentUser";
    public static final String AUTH_EXPIRED_ATTRIBUTE = "csucampuscraft.authExpired";

    public SessionIdentity identity(HttpServletRequest request) {
        HttpSession session = request.getSession(false);
        if (session == null) return null;
        try {
            Object value = session.getAttribute(IDENTITY_ATTRIBUTE);
            if (value instanceof SessionIdentity identity) return identity;
            if (value != null) clear(request);
            return null;
        } catch (IllegalStateException expired) {
            request.removeAttribute(CURRENT_USER_ATTRIBUTE);
            return null;
        }
    }

    public void establish(HttpServletRequest request, StoreUser user) {
        HttpSession session = request.getSession(true);
        synchronized (session) {
            request.changeSessionId();
            session.removeAttribute(CHECKOUT_CONFIRMATION_ATTRIBUTE);
            session.setAttribute(IDENTITY_ATTRIBUTE,
                    new SessionIdentity(user.getId(), user.getUpdatedAt()));
        }
        publishCurrentUser(request, user);
    }

    /** Clears only identity/confirmation; the existing CSRF token remains valid. */
    public void clear(HttpServletRequest request) {
        request.removeAttribute(CURRENT_USER_ATTRIBUTE);
        request.setAttribute(AUTH_EXPIRED_ATTRIBUTE, Boolean.TRUE);
        HttpSession session = request.getSession(false);
        if (session != null) {
            try {
                synchronized (session) {
                    session.removeAttribute(IDENTITY_ATTRIBUTE);
                    session.removeAttribute(CHECKOUT_CONFIRMATION_ATTRIBUTE);
                }
            } catch (IllegalStateException expired) {
                // An already-ended local session has no identity left to clear.
            }
        }
    }

    public void invalidate(HttpServletRequest request) {
        request.removeAttribute(CURRENT_USER_ATTRIBUTE);
        HttpSession session = request.getSession(false);
        if (session != null) {
            try { session.invalidate(); }
            catch (IllegalStateException expired) { /* Already ended. */ }
        }
    }

    public AuthUser currentUser(HttpServletRequest request) {
        Object value = request.getAttribute(CURRENT_USER_ATTRIBUTE);
        return value instanceof AuthUser user ? user : null;
    }

    public void publishCurrentUser(HttpServletRequest request, StoreUser user) {
        request.setAttribute(CURRENT_USER_ATTRIBUTE,
                new AuthUser(user.getId(), user.getUsername(), user.getDisplayName(), user.getRole()));
    }
}

