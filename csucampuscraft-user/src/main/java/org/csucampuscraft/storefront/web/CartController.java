package org.csucampuscraft.storefront.web;

import jakarta.servlet.http.HttpServletRequest;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;
import org.csucampuscraft.storefront.auth.SessionExpiredException;
import org.csucampuscraft.storefront.auth.SessionIdentity;
import org.csucampuscraft.storefront.auth.SessionSupport;
import org.csucampuscraft.storefront.cart.CartForm;
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
    private final CatalogService catalog;
    private final SessionSupport sessions;

    public CartController(CartService carts, CatalogService catalog, SessionSupport sessions) {
        this.carts = carts;
        this.catalog = catalog;
        this.sessions = sessions;
    }

    @GetMapping("/cart")
    public ModelAndView page(HttpServletRequest request) {
        return cartPage(carts.read(actor(request).userId()), null, null, "", null);
    }

    @PostMapping("/cart/items")
    public ModelAndView add(@RequestParam MultiValueMap<String, String> parameters,
                            HttpServletRequest request) {
        SessionIdentity actor = actor(request);
        String rawProductId = first(parameters, "productId");
        String rawQuantity = first(parameters, "quantity");
        try {
            rejectDuplicates(parameters, Set.of("productId", "quantity"));
            long productId = InputChecks.longInteger("productId", rawProductId, 1, Long.MAX_VALUE);
            int quantity = InputChecks.integer("quantity", rawQuantity, 1, 99);
            carts.add(actor, productId, quantity);
            return redirect();
        } catch (BusinessException failure) {
            if (!formFailure(failure)) throw failure;
            return detailFailure(rawProductId, rawQuantity, failure);
        }
    }

    @PostMapping("/cart/items/{itemId}/quantity")
    public ModelAndView changeQuantity(@PathVariable("itemId") String rawItemId,
                                       @RequestParam MultiValueMap<String, String> parameters,
                                       HttpServletRequest request) {
        SessionIdentity actor = actor(request);
        long itemId = InputChecks.longInteger("itemId", rawItemId, 1, Long.MAX_VALUE);
        CartForm form = new CartForm(first(parameters, "quantity"), first(parameters, "version"));
        try {
            rejectDuplicates(parameters, Set.of("quantity", "version"));
            int quantity = InputChecks.integer("quantity", form.quantity(), 1, 99);
            long version = InputChecks.longInteger("version", form.version(), 0, Long.MAX_VALUE);
            carts.changeQuantity(actor, itemId, quantity, version);
            return redirect();
        } catch (BusinessException failure) {
            if (!formFailure(failure)) throw failure;
            return cartPage(carts.read(actor(request).userId()), form, itemId, "quantity", failure);
        }
    }

    @PostMapping("/cart/items/{itemId}/remove")
    public ModelAndView remove(@PathVariable("itemId") String rawItemId,
                               @RequestParam MultiValueMap<String, String> parameters,
                               HttpServletRequest request) {
        SessionIdentity actor = actor(request);
        long itemId = InputChecks.longInteger("itemId", rawItemId, 1, Long.MAX_VALUE);
        CartForm form = new CartForm(null, first(parameters, "version"));
        try {
            rejectDuplicates(parameters, Set.of("version"));
            long version = InputChecks.longInteger("version", form.version(), 0, Long.MAX_VALUE);
            carts.remove(actor, itemId, version);
            return redirect();
        } catch (BusinessException failure) {
            if (!formFailure(failure)) throw failure;
            return cartPage(carts.read(actor(request).userId()), form, itemId, "remove", failure);
        }
    }

    private ModelAndView detailFailure(String rawProductId, String rawQuantity, BusinessException failure) {
        ProductDetail detail;
        try {
            long productId = InputChecks.longInteger("productId", rawProductId, 1, Long.MAX_VALUE);
            detail = catalog.detail(productId);
        } catch (BusinessException unavailable) {
            // Preserve the original POST status without exposing an unavailable product.
            throw failure;
        }
        ModelAndView view = new ModelAndView("products/detail");
        view.setStatus(failure.getStatus());
        view.addObject("product", detail.product());
        view.addObject("theme", detail.theme());
        view.addObject("category", detail.category());
        view.addObject("images", detail.images());
        view.addObject("purchaseQuantity", rawQuantity);
        view.addObject("purchaseFailure", true);
        view.addObject("reloadUrl", "/products/" + detail.product().getId());
        view.addObject("globalError", failure.getMessage());
        Map<String, String> fields = new LinkedHashMap<>();
        Map<String, String> anchors = new LinkedHashMap<>();
        failure.getFieldErrors().forEach((field, message) -> {
            if ("quantity".equals(field) || "productId".equals(field)) {
                fields.put(field, message);
                anchors.put("purchase-" + field, message);
            }
        });
        view.addObject("fieldErrors", fields);
        view.addObject("errorAnchors", anchors);
        view.addObject("errorStatus", failure.getStatus().value());
        view.addObject("errorCode", failure.getCode());
        return view;
    }

    private ModelAndView cartPage(CartPage cart, CartForm form, Long itemId,
                                  String action, BusinessException failure) {
        ModelAndView view = new ModelAndView("cart/index");
        view.addObject("cart", cart);
        view.addObject("cartForm", form == null ? new CartForm(null, null) : form);
        view.addObject("formItemId", itemId);
        view.addObject("formAction", action);
        view.addObject("formItemPresent", itemId == null || cart.items().stream()
                .anyMatch(line -> itemId.equals(line.getId())));
        view.addObject("reloadUrl", "/cart");
        Map<String, String> fields = failure == null ? Map.of() : failure.getFieldErrors();
        Map<String, String> anchors = new LinkedHashMap<>();
        if (itemId != null) fields.forEach((field, message) ->
                anchors.put("item-" + itemId + "-" + field, message));
        view.addObject("fieldErrors", fields);
        view.addObject("errorAnchors", anchors);
        if (failure != null) {
            view.setStatus(failure.getStatus());
            view.addObject("globalError", failure.getMessage());
            view.addObject("errorStatus", failure.getStatus().value());
            view.addObject("errorCode", failure.getCode());
        }
        return view;
    }

    private SessionIdentity actor(HttpServletRequest request) {
        SessionIdentity identity = sessions.identity(request);
        if (identity == null) throw new SessionExpiredException();
        return identity;
    }

    private static boolean formFailure(BusinessException failure) {
        return failure.getStatus() == HttpStatus.BAD_REQUEST || failure.getStatus() == HttpStatus.CONFLICT;
    }

    private static void rejectDuplicates(MultiValueMap<String, String> parameters, Set<String> fields) {
        for (String field : fields) {
            List<String> values = parameters.get(field);
            if (values != null && values.size() != 1) {
                throw new BusinessException(HttpStatus.BAD_REQUEST, "DUPLICATE_CART_FIELD",
                        "每个购物车字段只能提交一个值。", Map.of(field, "请为此字段提交一个值。"));
            }
        }
    }

    private static String first(MultiValueMap<String, String> parameters, String field) {
        List<String> values = parameters.get(field);
        return values == null || values.isEmpty() ? null : values.get(0);
    }

    private static ModelAndView redirect() {
        RedirectView redirect = new RedirectView("/cart", true);
        redirect.setStatusCode(HttpStatus.SEE_OTHER);
        redirect.setExposeModelAttributes(false);
        redirect.setExpandUriTemplateVariables(false);
        return new ModelAndView(redirect);
    }
}
