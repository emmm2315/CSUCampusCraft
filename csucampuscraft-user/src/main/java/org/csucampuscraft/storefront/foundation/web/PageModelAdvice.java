package org.csucampuscraft.storefront.foundation.web;

import org.csucampuscraft.storefront.auth.AuthUser;
import org.csucampuscraft.storefront.auth.AuthService;
import org.csucampuscraft.storefront.auth.CartRequestNavigation;
import org.csucampuscraft.storefront.auth.SessionIdentity;
import org.csucampuscraft.storefront.auth.StoreUser;
import org.csucampuscraft.storefront.cart.CartService;
import org.springframework.dao.DataAccessException;
import org.csucampuscraft.storefront.auth.SessionSupport;
import org.csucampuscraft.storefront.foundation.security.CsrfTokenService;
import org.csucampuscraft.storefront.foundation.view.ImagePaths;
import jakarta.servlet.RequestDispatcher;
import jakarta.servlet.http.HttpServletRequest;
import java.util.LinkedHashMap;
import java.util.Map;
import org.springframework.ui.Model;
import org.springframework.web.bind.annotation.ControllerAdvice;
import org.springframework.web.bind.annotation.ModelAttribute;

/** Shared presentation values; identity has already been rechecked by AuthFilter. */
@ControllerAdvice
public final class PageModelAdvice {
    private final CsrfTokenService csrfTokens;

    private static final String BADGE_UNAVAILABLE = "csucampuscraft.cartQuantityUnavailable";
    private final SessionSupport sessions;
    private final AuthService auth;
    private final CartService carts;

    public PageModelAdvice(CsrfTokenService csrfTokens, SessionSupport sessions, AuthService auth, CartService carts) {
        this.csrfTokens = csrfTokens;
        this.sessions = sessions;
        this.auth = auth;
        this.carts = carts;
    }

    @ModelAttribute
    public void contribute(Model model, HttpServletRequest request) {
        model.addAllAttributes(commonModel(request));
    }

    /** Also used when MVC resolves a resource error without invoking a controller. */
    public Map<String, Object> commonModel(HttpServletRequest request) {
        Map<String, Object> values = new LinkedHashMap<>();
        values.put("appId", "user");
        values.put("siteName", "CSUCampusCraft 用户端");
        AuthUser current = currentCustomer(request);
        boolean unavailable = Boolean.TRUE.equals(request.getAttribute(BADGE_UNAVAILABLE));
        long quantity = 0;
        if (current != null && !unavailable) {
            try {
                quantity = carts.quantityFor(current.userId());
            } catch (DataAccessException failedRead) {
                // The generic 500 can render without repeating the failed SUM or inventing zero.
                request.setAttribute(BADGE_UNAVAILABLE, Boolean.TRUE);
                throw failedRead;
            }
        }
        values.put("cartQuantity", unavailable ? null : quantity);
        values.put("cartQuantityUnavailable", unavailable);
        values.put("currentUser", current);
        values.put("authenticated", current != null);
        values.put("defaultCoverImage", ImagePaths.DEFAULT_COVER);
        // An invalid write must not create a new session while rendering the rejection.
        values.put("csrfToken", "GET".equals(request.getMethod())
                ? csrfTokens.getOrCreate(request) : csrfTokens.getExisting(request));
        values.put("fieldErrors", Map.of());
        Object status = request.getAttribute(RequestDispatcher.ERROR_STATUS_CODE);
        values.put("errorStatus", status instanceof Integer code ? code : 0);
        values.put("errorCode", publicAttribute(request, "foundation.errorCode"));
        values.put("errorMessage", publicAttribute(request, "foundation.errorMessage"));
        return values;
    }

    private AuthUser currentCustomer(HttpServletRequest request) {
        AuthUser current = sessions.currentUser(request);
        if (current != null) return "CUSTOMER".equals(current.role()) ? current : null;
        if (Boolean.TRUE.equals(request.getAttribute(BADGE_UNAVAILABLE))
                || Boolean.TRUE.equals(request.getAttribute(CartRequestNavigation.ROLE_REJECTED))) return null;
        SessionIdentity identity = sessions.identity(request);
        if (identity == null) return null;
        try {
            // Direct Boot /error renders also use the current account, never a previous browser value.
            StoreUser user = auth.findCurrent(identity);
            if (user == null) {
                sessions.clear(request);
                return null;
            }
            if (!"CUSTOMER".equals(user.getRole())) return null;
            sessions.publishCurrentUser(request, user);
            return sessions.currentUser(request);
        } catch (DataAccessException failedRead) {
            request.setAttribute(BADGE_UNAVAILABLE, Boolean.TRUE);
            throw failedRead;
        }
    }

    private String publicAttribute(HttpServletRequest request, String name) {
        Object value = request.getAttribute(name);
        return value instanceof String text ? text : "";
    }
}
