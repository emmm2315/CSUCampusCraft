package org.csucampuscraft.admin.web;

import jakarta.servlet.http.HttpServletRequest;
import java.util.*;
import org.csucampuscraft.admin.auth.SessionSupport;
import org.csucampuscraft.admin.catalog.*;
import org.csucampuscraft.admin.foundation.validation.InputChecks;
import org.csucampuscraft.admin.foundation.web.BusinessException;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Controller;
import org.springframework.ui.Model;
import org.springframework.util.MultiValueMap;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.servlet.ModelAndView;
import org.springframework.web.servlet.view.RedirectView;

@Controller
public final class ProductController {
    private static final Set<String> CREATE_FIELDS = Set.of("sku", "categoryId", "name", "price",
            "summary", "description", "coverImage", "stock", "sortOrder");
    private static final Set<String> EDIT_FIELDS = Set.of("categoryId", "name", "price",
            "summary", "description", "coverImage", "sortOrder", "version");
    private final ProductService products;
    private final SessionSupport sessions;

    public ProductController(ProductService products, SessionSupport sessions) {
        this.products = products;
        this.sessions = sessions;
    }

    @GetMapping("/products")
    public String list(@RequestParam MultiValueMap<String, String> parameters, Model model) {
        ProductQuery query = ProductQuery.bind(single(parameters, "categoryId"), single(parameters, "q"),
                single(parameters, "status"), single(parameters, "page"), single(parameters, "size"));
        ProductPage page = products.list(query);
        model.addAttribute("query", query);
        model.addAttribute("products", page.products());
        model.addAttribute("total", page.total());
        model.addAttribute("totalPages", page.totalPages());
        model.addAttribute("page", query.page());
        model.addAttribute("size", query.size());
        model.addAttribute("hasPrevious", page.hasPrevious());
        model.addAttribute("previousPage", page.previousPage());
        model.addAttribute("hasNext", page.hasNext());
        model.addAttribute("nextPage", page.nextPage());
        model.addAttribute("categories", products.categories());
        model.addAttribute("returnUrl", query.path(query.page()));
        return "products/list";
    }

    @GetMapping("/products/new")
    public ModelAndView createPage(@RequestParam MultiValueMap<String, String> parameters) {
        return form(null, new ProductInput("", "", "", "", "", "", "", "0", "0", "0"),
                returnUrl(parameters), null, null);
    }

    @GetMapping("/products/{productId}/edit")
    public ModelAndView editPage(@PathVariable("productId") String productId,
                                 @RequestParam MultiValueMap<String, String> parameters) {
        Product product = products.get(id(productId));
        return form(product, ProductInput.fromProduct(product), returnUrl(parameters), null, null);
    }

    @PostMapping("/products")
    public ModelAndView create(@RequestParam MultiValueMap<String, String> parameters,
                               HttpServletRequest request) {
        ProductInput input = input(parameters, true);
        String target = returnUrl(parameters);
        try {
            rejectDuplicates(parameters, CREATE_FIELDS);
            products.create(sessions.identity(request), input);
            return redirect(target);
        } catch (BusinessException failure) {
            if (!formFailure(failure)) throw failure;
            return form(null, input, target, failure, null);
        }
    }

    @PostMapping("/products/{productId}")
    public ModelAndView update(@PathVariable("productId") String productId,
                               @RequestParam MultiValueMap<String, String> parameters,
                               HttpServletRequest request) {
        long id = id(productId);
        ProductInput input = input(parameters, false);
        String target = returnUrl(parameters);
        try {
            rejectDuplicates(parameters, EDIT_FIELDS);
            products.update(sessions.identity(request), id, input);
            return redirect(target);
        } catch (BusinessException failure) {
            if (!formFailure(failure)) throw failure;
            return form(products.get(id), input, target, failure, null);
        }
    }

    @PostMapping("/products/{productId}/publish")
    public ModelAndView publish(@PathVariable("productId") String productId,
                                @RequestParam MultiValueMap<String, String> parameters,
                                HttpServletRequest request) {
        return state(productId, parameters, request, true);
    }

    @PostMapping("/products/{productId}/unpublish")
    public ModelAndView unpublish(@PathVariable("productId") String productId,
                                  @RequestParam MultiValueMap<String, String> parameters,
                                  HttpServletRequest request) {
        return state(productId, parameters, request, false);
    }

    @PostMapping("/products/{productId}/restock")
    public ModelAndView restock(@PathVariable("productId") String productId,
                               @RequestParam MultiValueMap<String, String> parameters,
                               HttpServletRequest request) {
        long id = id(productId);
        String target = returnUrl(parameters);
        String quantity = first(parameters, "quantity");
        try {
            products.restock(sessions.identity(request), id, single(parameters, "quantity"));
            return redirect(target);
        } catch (BusinessException failure) {
            if (!formFailure(failure)) throw failure;
            Product product = products.get(id);
            return form(product, ProductInput.fromProduct(product), target, failure, quantity);
        }
    }

    private ModelAndView state(String rawId, MultiValueMap<String, String> parameters,
                               HttpServletRequest request, boolean publish) {
        long id = id(rawId);
        String target = returnUrl(parameters);
        try {
            String version = single(parameters, "version");
            if (publish) products.publish(sessions.identity(request), id, version);
            else products.unpublish(sessions.identity(request), id, version);
            return redirect(target);
        } catch (BusinessException failure) {
            if (!formFailure(failure)) throw failure;
            Product product = products.get(id);
            return form(product, ProductInput.fromProduct(product), target, failure, null);
        }
    }

    private ModelAndView form(Product product, ProductInput input, String target,
                              BusinessException failure, String quantity) {
        ModelAndView view = new ModelAndView("products/form");
        view.addObject("product", product);
        view.addObject("editing", product != null);
        view.addObject("form", input);
        view.addObject("returnUrl", target);
        List<ProductCategoryChoice> categories = products.categories().stream()
                .filter(ProductCategoryChoice::secondLevel).toList();
        view.addObject("categories", categories);
        view.addObject("restockQuantity", quantity == null ? "1" : quantity);
        if (failure != null) {
            view.setStatus(failure.getStatus());
            view.addObject("fieldErrors", failure.getFieldErrors());
            view.addObject("globalError", failure.getMessage());
        }
        return view;
    }

    private static boolean formFailure(BusinessException failure) {
        return (failure.getStatus() == HttpStatus.BAD_REQUEST || failure.getStatus() == HttpStatus.CONFLICT)
                && !failure.getFieldErrors().isEmpty();
    }

    private static ProductInput input(MultiValueMap<String, String> p, boolean creating) {
        return new ProductInput(creating ? first(p, "sku") : null, first(p, "categoryId"),
                first(p, "name"), first(p, "price"), first(p, "summary"), first(p, "description"),
                first(p, "coverImage"), creating ? first(p, "stock") : null,
                first(p, "sortOrder"), creating ? null : first(p, "version"));
    }

    private static String first(MultiValueMap<String, String> p, String key) {
        List<String> values = p.get(key);
        return values == null || values.isEmpty() ? null : values.get(0);
    }

    private static String single(MultiValueMap<String, String> p, String key) {
        rejectDuplicates(p, Set.of(key));
        return first(p, key);
    }

    private static void rejectDuplicates(MultiValueMap<String, String> parameters, Set<String> fields) {
        for (String key : fields) {
            List<String> values = parameters.get(key);
            if (values != null && values.size() != 1) {
                throw new BusinessException(HttpStatus.BAD_REQUEST, "DUPLICATE_PRODUCT_FIELD",
                        "每个字段只能提交一个值。", Map.of(key, "请为此字段提交一个值。"));
            }
        }
    }

    private static long id(String raw) {
        return InputChecks.longInteger("productId", raw, 1, Long.MAX_VALUE);
    }

    private static String returnUrl(MultiValueMap<String, String> parameters) {
        List<String> values = parameters.get("returnUrl");
        return ProductReturnUrls.resolve(values != null && values.size() == 1 ? values.get(0) : null);
    }

    private static ModelAndView redirect(String target) {
        RedirectView redirect = new RedirectView(target, true);
        redirect.setStatusCode(HttpStatus.SEE_OTHER);
        redirect.setExposeModelAttributes(false);
        redirect.setExpandUriTemplateVariables(false);
        return new ModelAndView(redirect);
    }
}
