package org.csucampuscraft.storefront.foundation.security;

import org.csucampuscraft.storefront.foundation.web.PageModelAdvice;
import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import java.io.IOException;
import java.net.URLDecoder;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.util.LinkedHashMap;
import java.util.Map;
import org.springframework.beans.factory.ObjectProvider;
import org.springframework.core.Ordered;
import org.springframework.core.annotation.Order;
import org.springframework.stereotype.Component;
import org.springframework.web.filter.OncePerRequestFilter;
import org.springframework.web.servlet.View;
import org.thymeleaf.spring6.view.ThymeleafViewResolver;

/** Protects every external non-GET request, including login forms added in STEP04. */
@Component
@Order(Ordered.HIGHEST_PRECEDENCE + 20)
public final class CsrfFilter extends OncePerRequestFilter {
    private final CsrfTokenService tokens;
    private final ObjectProvider<ThymeleafViewResolver> views;
    private final ObjectProvider<PageModelAdvice> pageModels;

    public CsrfFilter(CsrfTokenService tokens, ObjectProvider<ThymeleafViewResolver> views,
                      ObjectProvider<PageModelAdvice> pageModels) {
        this.tokens = tokens;
        this.views = views;
        this.pageModels = pageModels;
    }

    @Override
    protected boolean shouldNotFilter(HttpServletRequest request) {
        return "GET".equals(request.getMethod());
    }

    @Override
    protected boolean shouldNotFilterErrorDispatch() { return true; }

    @Override
    protected void doFilterInternal(HttpServletRequest request, HttpServletResponse response,
                                    FilterChain chain) throws ServletException, IOException {
        if (!valid(request)) {
            renderForbidden(request, response);
            return;
        }
        chain.doFilter(request, response);
    }

    private void renderForbidden(HttpServletRequest request, HttpServletResponse response)
            throws ServletException {
        try {
            Map<String, Object> model = new LinkedHashMap<>(pageModels.getObject().commonModel(request));
            model.put("errorStatus", HttpServletResponse.SC_FORBIDDEN);
            model.put("errorCode", "CSRF_REJECTED");
            model.put("errorMessage", "请求校验失败，请重新打开页面后提交。");
            View view = views.getObject().resolveViewName("error/403", request.getLocale());
            if (view == null) {
                throw new ServletException("Forbidden view is unavailable");
            }
            // Security rejection is always an HTML page, independent of Accept/Content-Type.
            response.setStatus(HttpServletResponse.SC_FORBIDDEN);
            response.setContentType("text/html;charset=UTF-8");
            response.setCharacterEncoding(StandardCharsets.UTF_8.name());
            view.render(model, request, response);
        } catch (Exception renderingFailure) {
            // The normal Boot error dispatch remains the last-resort fallback.
            // Do not propagate model values or request data through a technical message.
            throw new ServletException("Unable to render forbidden response");
        }
    }

    private boolean valid(HttpServletRequest request) {
        String expected = tokens.getExisting(request);
        if (expected == null || queryContainsToken(request.getQueryString())) {
            return false;
        }
        String contentType = request.getContentType();
        // This step supports ordinary HTML forms; no multipart/upload flow is in scope.
        if (contentType == null || !contentType.split(";", 2)[0].trim()
                .equalsIgnoreCase("application/x-www-form-urlencoded")) {
            return false;
        }
        String[] submitted = request.getParameterValues(CsrfTokenService.PARAMETER_NAME);
        if (submitted == null || submitted.length != 1 || submitted[0] == null
                || !submitted[0].matches("[0-9a-f]{64}")) {
            return false;
        }
        return MessageDigest.isEqual(expected.getBytes(StandardCharsets.US_ASCII),
                submitted[0].getBytes(StandardCharsets.US_ASCII));
    }

    private boolean queryContainsToken(String query) {
        if (query == null) {
            return false;
        }
        try {
            for (String part : query.split("&")) {
                String key = part.split("=", 2)[0];
                if (CsrfTokenService.PARAMETER_NAME.equals(URLDecoder.decode(key, StandardCharsets.UTF_8))) {
                    return true;
                }
            }
            return false;
        } catch (IllegalArgumentException malformed) {
            return true;
        }
    }
}
