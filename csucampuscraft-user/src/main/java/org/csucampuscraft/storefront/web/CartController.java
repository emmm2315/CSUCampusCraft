package org.csucampuscraft.storefront.web;

import jakarta.servlet.http.HttpServletRequest;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import org.csucampuscraft.storefront.auth.SessionExpiredException;
import org.csucampuscraft.storefront.auth.SessionIdentity;
import org.csucampuscraft.storefront.auth.SessionSupport;
import org.csucampuscraft.storefront.cart.CartPage;
import org.csucampuscraft.storefront.cart.CartService;
import org.csucampuscraft.storefront.catalog.CatalogService;
import org.csucampuscraft.storefront.catalog.ProductDetail;
import org.csucampuscraft.storefront.foundation.validation.InputChecks;
import org.csucampuscraft.storefront.foundation.web.BusinessException;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Controller;
import org.springframework.util.MultiValueMap;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.servlet.ModelAndView;
import org.springframework.web.servlet.view.RedirectView;

@Controller
public final class CartController {
    private final CartService carts;
    private final SessionSupport sessions;
    private final CatalogService catalog;

    public CartController(CartService carts, SessionSupport sessions, CatalogService catalog) {
        this.carts = carts;
        this.sessions = sessions;
        this.catalog = catalog;
    }

    @GetMapping("/cart")
    public ModelAndView page(HttpServletRequest request) {
        return cartPage(actor(request), null, null, null, null);
    }

    @PostMapping("/cart/items")
    public ModelAndView add(@RequestParam MultiValueMap<String, String> parameters,
                            HttpServletRequest request) {
        SessionIdentity actor = actor(request);
        Long productId = null;
        String quantity = first(parameters, "quantity");
        try {
            productId = positiveId("productId", single(parameters, "productId"));
            int amount = quantity(single(parameters, "quantity"));
            carts.add(actor, productId, amount);
            return redirect();
        } catch (BusinessException failure) {
            if (!formFailure(failure)) throw failure;
            return addFailure(actor, productId, quantity, failure);
        }
    }

    @PostMapping("/cart/items/{itemId}/quantity")
    public ModelAndView quantity(@PathVariable("itemId") String itemId,
                                 @RequestParam MultiValueMap<String, String> parameters,
                                 HttpServletRequest request) {
        SessionIdentity actor = actor(request);
        Long id = null;
        String quantity = first(parameters, "quantity");
        try {
            id = positiveId("itemId", itemId);
            int amount = quantity(single(parameters, "quantity"));
            long version = version(single(parameters, "version"));
            carts.changeQuantity(actor, id, amount, version);
            return redirect();
        } catch (BusinessException failure) {
            if (!formFailure(failure)) throw failure;
            return cartPage(actor, id, "quantity", quantity, failure);
        }
    }

    @PostMapping("/cart/items/{itemId}/remove")
    public ModelAndView remove(@PathVariable("itemId") String itemId,
                               @RequestParam MultiValueMap<String, String> parameters,
                               HttpServletRequest request) {
        SessionIdentity actor = actor(request);
        Long id = null;
        try {
            id = positiveId("itemId", itemId);
            long version = version(single(parameters, "version"));
            carts.remove(actor, id, version);
            return redirect();
        } catch (BusinessException failure) {
            if (!formFailure(failure)) throw failure;
            return cartPage(actor, id, "remove", null, failure);
        }
    }

    private ModelAndView cartPage(SessionIdentity actor, Long itemId, String action,
                                  String quantity, BusinessException failure) {
        CartPage cart = carts.getCart(actor.userId());
        ModelAndView view = new ModelAndView("cart/index");
        view.addObject("cart", cart);
        view.addObject("formItemId", itemId);
        boolean itemPresent = itemId != null
                && cart.items().stream().anyMatch(line -> line.id() == itemId);
        view.addObject("formItemPresent", itemPresent);
        view.addObject("formAction", action);
        view.addObject("quantityInput", quantity);
        view.addObject("reloadUrl", "/cart");
        errors(view, failure, itemPresent && "quantity".equals(action) ? "cart-" + itemId + "-quantity" : null);
        return view;
    }

    private ModelAndView addFailure(SessionIdentity actor, Long productId, String quantity,
                                    BusinessException failure) {
        if (productId != null) {
            ProductDetail detail;
            try {
                detail = catalog.detail(productId);
            } catch (BusinessException unavailable) {
                if (unavailable.getStatus() != HttpStatus.NOT_FOUND) throw unavailable;
                return cartPage(actor, null, "add", quantity, failure);
            }
            ModelAndView view = new ModelAndView("products/detail");
            view.addObject("product", detail.product());
            view.addObject("theme", detail.theme());
            view.addObject("category", detail.category());
            view.addObject("images", detail.images());
            view.addObject("quantityInput", quantity);
            view.addObject("reloadUrl", "/products/" + productId);
            errors(view, failure, "purchase-quantity");
            return view;
        }
        return cartPage(actor, null, "add", quantity, failure);
    }

    private static void errors(ModelAndView view, BusinessException failure, String quantityId) {
        Map<String, String> fields = failure == null ? Map.of() : failure.getFieldErrors();
        view.addObject("fieldErrors", fields);
        Map<String, String> anchors = new LinkedHashMap<>();
        if (quantityId != null && fields.containsKey("quantity")) {
            anchors.put(quantityId, fields.get("quantity"));
        }
        view.addObject("errorAnchors", anchors);
        view.addObject("cartConflict", failure != null && failure.getStatus() == HttpStatus.CONFLICT);
        if (failure != null) {
            view.setStatus(failure.getStatus());
            view.addObject("globalError", failure.getMessage());
        }
    }

    private SessionIdentity actor(HttpServletRequest request) {
        SessionIdentity actor = sessions.identity(request);
        if (actor == null) throw new SessionExpiredException();
        return actor;
    }

    private static String single(MultiValueMap<String, String> parameters, String field) {
        List<String> values = parameters.get(field);
        if (values == null || values.isEmpty()) return null;
        if (values.size() != 1) {
            throw new BusinessException(HttpStatus.BAD_REQUEST, "DUPLICATE_CART_FIELD",
                    "每个购物车字段只能提交一个值。", Map.of(field, "请为此字段提交一个值。"));
        }
        return values.get(0);
    }

    private static String first(MultiValueMap<String, String> parameters, String field) {
        List<String> values = parameters.get(field);
        return values == null || values.isEmpty() ? null : values.get(0);
    }

    private static long positiveId(String field, String value) {
        return InputChecks.longInteger(field, value, 1, Long.MAX_VALUE);
    }

    private static int quantity(String value) { return InputChecks.integer("quantity", value, 1, 99); }

    private static long version(String value) {
        return InputChecks.longInteger("version", value, 0, Long.MAX_VALUE);
    }

    private static boolean formFailure(BusinessException failure) {
        return failure.getStatus() == HttpStatus.BAD_REQUEST || failure.getStatus() == HttpStatus.CONFLICT;
    }

    private static ModelAndView redirect() {
        RedirectView redirect = new RedirectView("/cart", true);
        redirect.setStatusCode(HttpStatus.SEE_OTHER);
        redirect.setExposeModelAttributes(false);
        redirect.setExpandUriTemplateVariables(false);
        return new ModelAndView(redirect);
    }
}
