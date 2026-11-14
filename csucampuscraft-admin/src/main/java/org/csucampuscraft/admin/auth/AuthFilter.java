package org.csucampuscraft.admin.auth;

import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import java.io.IOException;
import java.net.URLEncoder;
import java.nio.charset.StandardCharsets;
import org.csucampuscraft.admin.foundation.security.ReturnUrlPolicy;
import org.csucampuscraft.admin.foundation.web.BusinessException;
import org.csucampuscraft.admin.foundation.web.GlobalExceptionHandler;
import org.springframework.beans.factory.ObjectProvider;
import org.springframework.core.Ordered;
import org.springframework.core.annotation.Order;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Component;
import org.springframework.web.filter.OncePerRequestFilter;
import org.springframework.web.servlet.ModelAndView;
import org.springframework.web.servlet.View;
import org.thymeleaf.spring6.view.ThymeleafViewResolver;

/** Identity checks precede the existing +20 CSRF filter for every protected request. */
@Component
@Order(Ordered.HIGHEST_PRECEDENCE + 10)
public final class AuthFilter extends OncePerRequestFilter {
    private final AuthService auth;
    private final SessionSupport sessions;
    private final ReturnUrlPolicy returns;
    private final ObjectProvider<GlobalExceptionHandler> errors;
    private final ObjectProvider<ThymeleafViewResolver> views;

    public AuthFilter(AuthService auth, SessionSupport sessions, ReturnUrlPolicy returns,
                      ObjectProvider<GlobalExceptionHandler> errors,
                      ObjectProvider<ThymeleafViewResolver> views) {
        this.auth = auth;
        this.sessions = sessions;
        this.returns = returns;
        this.errors = errors;
        this.views = views;
    }

    @Override
    protected boolean shouldNotFilterErrorDispatch() { return true; }

    @Override
    protected void doFilterInternal(HttpServletRequest request, HttpServletResponse response,
                                    FilterChain chain) throws ServletException, IOException {
        String path = request.getServletPath();
        boolean protectedRequest = !publicPath(path);
        // Error and static resources must stay available even if the database is unavailable.
        if ("/error".equals(path) || resourcePath(path)) {
            chain.doFilter(request, response);
            return;
        }
        if (protectedRequest || "/login".equals(path)) {
            response.setHeader("Cache-Control", "no-store");
        }
        try {
            SessionIdentity identity = sessions.identity(request);
            StoreUser current = identity == null ? null : auth.findCurrent(identity);
            if (current == null) {
                sessions.clear(request);
                if (protectedRequest) {
                    redirectToLogin(request, response);
                    return;
                }
            } else if (!AuthService.REQUIRED_ROLE.equals(current.getRole())) {
                if (protectedRequest) {
                    throw new BusinessException(HttpStatus.FORBIDDEN, "AUTH_ROLE_FORBIDDEN",
                            "当前账号无权访问本端页面。");
                }
                sessions.clear(request);
            } else {
                response.setHeader("Cache-Control", "no-store");
                sessions.publishCurrentUser(request, current);
            }
        } catch (Exception failure) {
            renderFailure(failure, request, response);
            return;
        }
        // Business Controller errors are handled by MVC; never swallow downstream failures.
        chain.doFilter(request, response);
    }

    private boolean publicPath(String path) {
        return "/login".equals(path) || "/error".equals(path) || resourcePath(path);
    }

    private boolean resourcePath(String path) {
        return "/css".equals(path) || path.startsWith("/css/")
                || "/js".equals(path) || path.startsWith("/js/")
                || "/images".equals(path) || path.startsWith("/images/");
    }

    private void redirectToLogin(HttpServletRequest request, HttpServletResponse response) {
        String candidate = "/";
        if ("GET".equals(request.getMethod())) {
            candidate = request.getRequestURI().substring(request.getContextPath().length());
            String query = request.getQueryString();
            if (query != null) candidate += "?" + query;
        }
        String destination = returns.resolve(candidate, "/");
        response.setStatus(HttpServletResponse.SC_FOUND);
        // Cookie-only tracking intentionally avoids encodeRedirectURL / URL session rewriting.
        response.setHeader("Location", request.getContextPath() + "/login?returnUrl="
                + URLEncoder.encode(destination, StandardCharsets.UTF_8));
    }

    private void renderFailure(Exception failure, HttpServletRequest request,
                               HttpServletResponse response) throws IOException {
        try {
            GlobalExceptionHandler handler = errors.getObject();
            ModelAndView result = failure instanceof BusinessException business
                    ? handler.business(business, request) : handler.unexpected(failure, request, response);
            if (response.isCommitted()) return;
            if (result == null || result.isEmpty() || result.getViewName() == null) {
                response.sendError(HttpServletResponse.SC_INTERNAL_SERVER_ERROR);
                return;
            }
            View view = views.getObject().resolveViewName(result.getViewName(), request.getLocale());
            if (view == null) {
                response.sendError(HttpServletResponse.SC_INTERNAL_SERVER_ERROR);
                return;
            }
            response.setStatus(result.getStatus() == null ? 500 : result.getStatus().value());
            response.setContentType("text/html;charset=UTF-8");
            response.setCharacterEncoding(StandardCharsets.UTF_8.name());
            view.render(result.getModel(), request, response);
        } catch (Exception renderingFailure) {
            if (!response.isCommitted()) response.sendError(HttpServletResponse.SC_INTERNAL_SERVER_ERROR);
        }
    }
}
