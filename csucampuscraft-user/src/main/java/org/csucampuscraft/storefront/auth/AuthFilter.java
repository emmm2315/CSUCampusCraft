package org.csucampuscraft.storefront.auth;

import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import java.io.IOException;
import java.net.URLEncoder;
import java.nio.charset.StandardCharsets;
import org.csucampuscraft.storefront.foundation.security.ReturnUrlPolicy;
import org.csucampuscraft.storefront.foundation.web.BusinessException;
import org.csucampuscraft.storefront.foundation.web.GlobalExceptionHandler;
import org.springframework.beans.factory.ObjectProvider;
import org.springframework.core.Ordered;
import org.springframework.core.annotation.Order;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Component;
import org.springframework.web.filter.OncePerRequestFilter;
import org.springframework.web.servlet.ModelAndView;
import org.springframework.web.servlet.View;
import org.thymeleaf.spring6.view.ThymeleafViewResolver;

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
        try {
            if (!authorize(request, response)) return;
        } catch (Exception failure) {
            renderFailure(request, response, failure);
            return;
        }
        // Downstream MVC/CSRF failures keep their own existing mapping.
        chain.doFilter(request, response);
    }

    private boolean authorize(HttpServletRequest request, HttpServletResponse response) {
        String path = request.getServletPath();
        if (publicInfrastructure(path)) return true;
        boolean protectedRequest = isProtected(request, path);
        if (protectedRequest || "/login".equals(path)) response.setHeader("Cache-Control", "no-store");
        SessionIdentity identity = sessions.identity(request);
        if (identity == null) {
            if (protectedRequest) {
                sessions.clear(request);
                redirectToLogin(request, response);
                return false;
            }
            return true;
        }
        StoreUser user = auth.findCurrent(identity);
        if (user == null) {
            sessions.clear(request);
            if (protectedRequest) {
                redirectToLogin(request, response);
                return false;
            }
            return true;
        }
        if (!AuthService.REQUIRED_ROLE.equals(user.getRole())) {
            if (protectedRequest) {
                throw new BusinessException(HttpStatus.FORBIDDEN, "AUTH_ROLE_FORBIDDEN",
                        "当前账号无权访问此页面。");
            }
            sessions.clear(request);
            return true;
        }
        sessions.publishCurrentUser(request, user);
        response.setHeader("Cache-Control", "no-store");
        return true;
    }

    private boolean publicInfrastructure(String path) {
        // Static assets and error dispatch need no database identity lookup.
        return "/error".equals(path)
                || within(path, "/css") || within(path, "/js") || within(path, "/images");
    }

    private boolean isProtected(HttpServletRequest request, String path) {
        return within(path, "/cart") || within(path, "/checkout") || within(path, "/orders")
                || ("POST".equals(request.getMethod()) && "/logout".equals(path));
    }

    private boolean within(String path, String prefix) {
        return prefix.equals(path) || path.startsWith(prefix + "/");
    }

    private void redirectToLogin(HttpServletRequest request, HttpServletResponse response) {
        // Only the original GET may become a destination; POST is never replayed.
        String requested = "GET".equals(request.getMethod())
                ? request.getRequestURI().substring(request.getContextPath().length())
                    + (request.getQueryString() == null ? "" : "?" + request.getQueryString())
                : "/";
        String target = returns.resolve(requested, "/");
        response.setStatus(HttpServletResponse.SC_FOUND);
        response.setHeader("Location", request.getContextPath() + "/login?returnUrl="
                + URLEncoder.encode(target, StandardCharsets.UTF_8));
    }

    private void renderFailure(HttpServletRequest request, HttpServletResponse response,
                               Exception failure) throws IOException {
        try {
            ModelAndView result = failure instanceof BusinessException business
                    ? errors.getObject().business(business, request)
                    : errors.getObject().unexpected(failure, request, response);
            if (response.isCommitted()) return;
            if (result == null || result.getViewName() == null) {
                response.sendError(HttpServletResponse.SC_INTERNAL_SERVER_ERROR);
                return;
            }
            View view = views.getObject().resolveViewName(result.getViewName(), request.getLocale());
            if (view == null) {
                response.sendError(HttpServletResponse.SC_INTERNAL_SERVER_ERROR);
                return;
            }
            response.setStatus(result.getStatus() == null
                    ? HttpServletResponse.SC_INTERNAL_SERVER_ERROR : result.getStatus().value());
            response.setContentType("text/html;charset=UTF-8");
            response.setCharacterEncoding(StandardCharsets.UTF_8.name());
            view.render(result.getModel(), request, response);
        } catch (Exception renderingFailure) {
            if (!response.isCommitted()) response.sendError(HttpServletResponse.SC_INTERNAL_SERVER_ERROR);
        }
    }
}

