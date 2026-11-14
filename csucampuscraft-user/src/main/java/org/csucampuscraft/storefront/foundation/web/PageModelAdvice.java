package org.csucampuscraft.storefront.foundation.web;

import org.csucampuscraft.storefront.auth.AuthUser;
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

    public PageModelAdvice(CsrfTokenService csrfTokens) { this.csrfTokens = csrfTokens; }

    @ModelAttribute
    public void contribute(Model model, HttpServletRequest request) {
        model.addAllAttributes(commonModel(request));
    }

    /** Also used when MVC resolves a resource error without invoking a controller. */
    public Map<String, Object> commonModel(HttpServletRequest request) {
        Map<String, Object> values = new LinkedHashMap<>();
        values.put("appId", "user");
        values.put("siteName", "CSUCampusCraft 用户端");
        values.put("cartQuantity", 0);
        Object identity = request.getAttribute(SessionSupport.CURRENT_USER_ATTRIBUTE);
        AuthUser current = identity instanceof AuthUser user ? user : null;
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

    private String publicAttribute(HttpServletRequest request, String name) {
        Object value = request.getAttribute(name);
        return value instanceof String text ? text : "";
    }
}
