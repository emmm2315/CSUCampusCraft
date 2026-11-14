package org.csucampuscraft.storefront.auth;

import jakarta.servlet.http.HttpServletRequest;

/** Fixed read destinations only; a rejected POST is never replayed after login. */
public final class CartRequestNavigation {
    public static final String ROLE_REJECTED = "csucampuscraft.cartRoleRejected";
    private CartRequestNavigation() { }

    public static boolean isCartWrite(HttpServletRequest request) {
        if (!"POST".equals(request.getMethod())) return false;
        String path = request.getServletPath();
        return "/cart/items".equals(path)
                || path.matches("/cart/items/[^/]+/(?:quantity|remove)");
    }

    public static String readDestination(HttpServletRequest request) {
        if ("GET".equals(request.getMethod())) {
            return request.getRequestURI().substring(request.getContextPath().length())
                    + (request.getQueryString() == null ? "" : "?" + request.getQueryString());
        }
        if (isCartWrite(request)) {
            if ("/cart/items".equals(request.getServletPath())) {
                String[] values = request.getParameterValues("productId");
                if (values != null && values.length == 1 && values[0] != null) {
                    String raw = values[0].strip();
                    if (raw.matches("[0-9]+")) {
                        try {
                            long id = Long.parseLong(raw);
                            if (id > 0) return "/products/" + id;
                        } catch (NumberFormatException outsideLongRange) {
                            // Invalid input selects the fixed cart read page, not an arbitrary URL.
                        }
                    }
                }
            }
            return "/cart";
        }
        return "/";
    }
}
