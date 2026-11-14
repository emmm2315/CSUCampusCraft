package org.csucampuscraft.storefront.auth;

import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.csucampuscraft.storefront.foundation.web.BusinessException;
import org.springframework.context.annotation.Configuration;
import org.springframework.http.HttpStatus;
import org.springframework.web.servlet.HandlerInterceptor;
import org.springframework.web.servlet.config.annotation.InterceptorRegistry;
import org.springframework.web.servlet.config.annotation.WebMvcConfigurer;

/** Cart POST role rejection follows the CSRF filter and precedes MVC argument binding. */
@Configuration
public class CartRoleConfiguration implements WebMvcConfigurer {
    @Override
    public void addInterceptors(InterceptorRegistry registry) {
        registry.addInterceptor(new HandlerInterceptor() {
            @Override
            public boolean preHandle(HttpServletRequest request, HttpServletResponse response,
                                     Object handler) {
                if (CartRequestNavigation.isCartWrite(request)
                        && Boolean.TRUE.equals(request.getAttribute(CartRequestNavigation.ROLE_REJECTED))) {
                    throw new BusinessException(HttpStatus.FORBIDDEN, "AUTH_ROLE_FORBIDDEN",
                            "当前账号无权执行购物车操作。");
                }
                return true;
            }
        }).addPathPatterns("/cart/items", "/cart/items/*/quantity", "/cart/items/*/remove");
    }
}
