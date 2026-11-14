package org.csucampuscraft.admin.auth;

import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpSession;
import org.springframework.stereotype.Component;

/** This application only touches its own cookie-backed HttpSession. */
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
            return value instanceof SessionIdentity identity ? identity : null;
        } catch (IllegalStateException expired) {
            return null;
        }
    }

    public void establish(HttpServletRequest request, StoreUser user) {
        HttpSession session = request.getSession(true);
        request.changeSessionId();
        session.removeAttribute(CHECKOUT_CONFIRMATION_ATTRIBUTE);
        session.setAttribute(IDENTITY_ATTRIBUTE, new SessionIdentity(user.getId(), user.getUpdatedAt()));
        publishCurrentUser(request, user);
    }

    /** Clear identity/confirmation while retaining the existing CSRF token for the next login. */
    public void clear(HttpServletRequest request) {
        request.removeAttribute(CURRENT_USER_ATTRIBUTE);
        HttpSession session = request.getSession(false);
        if (session == null) return;
        try {
            boolean hadIdentity = session.getAttribute(IDENTITY_ATTRIBUTE) != null;
            session.removeAttribute(IDENTITY_ATTRIBUTE);
            session.removeAttribute(CHECKOUT_CONFIRMATION_ATTRIBUTE);
            if (hadIdentity) request.setAttribute(AUTH_EXPIRED_ATTRIBUTE, true);
        } catch (IllegalStateException expired) {
            // A concurrently expired session contains no usable identity.
        }
    }

    public void invalidate(HttpServletRequest request) {
        request.removeAttribute(CURRENT_USER_ATTRIBUTE);
        HttpSession session = request.getSession(false);
        if (session == null) return;
        try {
            session.invalidate();
        } catch (IllegalStateException expired) {
            // Logout remains successful if this application session has already expired.
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
