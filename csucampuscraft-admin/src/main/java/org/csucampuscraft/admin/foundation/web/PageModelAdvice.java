package org.csucampuscraft.admin.foundation.web;

import org.csucampuscraft.admin.foundation.security.CsrfTokenService;
import org.csucampuscraft.admin.auth.AuthUser;
import org.csucampuscraft.admin.auth.SessionSupport;
import org.csucampuscraft.admin.foundation.view.ImagePaths;
import jakarta.servlet.RequestDispatcher;
import jakarta.servlet.http.HttpServletRequest;
import java.util.LinkedHashMap;
import java.util.Map;
import org.springframework.ui.Model;
import org.springframework.web.bind.annotation.ControllerAdvice;
import org.springframework.web.bind.annotation.ModelAttribute;

/** Safe presentation values from the identity already verified by AuthFilter. */
@ControllerAdvice
public final class PageModelAdvice {
    private final CsrfTokenService csrfTokens;
    private final SessionSupport sessions;

    public PageModelAdvice(CsrfTokenService csrfTokens, SessionSupport sessions) {
        this.csrfTokens = csrfTokens;
        this.sessions = sessions;
    }

    @ModelAttribute
    public void contribute(Model model, HttpServletRequest request) {
        model.addAllAttributes(commonModel(request));
    }

    /** Also used when MVC resolves a resource error without invoking a controller. */
    public Map<String, Object> commonModel(HttpServletRequest request) {
        Map<String, Object> values = new LinkedHashMap<>();
        values.put("appId", "admin");
        values.put("siteName", "CSUCampusCraft 管理端");
        values.put("cartQuantity", 0);
        AuthUser currentUser = sessions.currentUser(request);
        values.put("currentUser", currentUser);
        values.put("authenticated", currentUser != null);
        if (Boolean.TRUE.equals(request.getAttribute(SessionSupport.AUTH_EXPIRED_ATTRIBUTE))) {
            values.put("globalMessage", "登录状态已失效，请重新登录。");
        }
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
