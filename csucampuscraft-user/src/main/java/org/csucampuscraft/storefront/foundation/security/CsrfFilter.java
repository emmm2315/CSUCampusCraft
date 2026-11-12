package org.csucampuscraft.storefront.foundation.security;

import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import java.io.IOException;
import java.net.URLDecoder;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import org.springframework.core.Ordered;
import org.springframework.core.annotation.Order;
import org.springframework.stereotype.Component;
import org.springframework.web.filter.OncePerRequestFilter;

/** Protects every external non-GET request, including login forms added in STEP04. */
@Component
@Order(Ordered.HIGHEST_PRECEDENCE + 20)
public final class CsrfFilter extends OncePerRequestFilter {
    private final CsrfTokenService tokens;

    public CsrfFilter(CsrfTokenService tokens) { this.tokens = tokens; }

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
            request.setAttribute("foundation.errorCode", "CSRF_REJECTED");
            request.setAttribute("foundation.errorMessage", "请求校验失败，请重新打开页面后提交。");
            response.sendError(HttpServletResponse.SC_FORBIDDEN);
            return;
        }
        chain.doFilter(request, response);
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
