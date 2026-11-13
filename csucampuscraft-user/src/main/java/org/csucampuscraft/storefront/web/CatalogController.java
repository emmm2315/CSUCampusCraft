package org.csucampuscraft.storefront.web;

import org.csucampuscraft.storefront.catalog.CatalogPage;
import org.csucampuscraft.storefront.catalog.CatalogQuery;
import org.csucampuscraft.storefront.catalog.CatalogService;
import org.csucampuscraft.storefront.catalog.ProductDetail;
import org.csucampuscraft.storefront.foundation.validation.InputChecks;
import org.csucampuscraft.storefront.foundation.web.BusinessException;
import org.springframework.http.HttpStatus;
import org.springframework.util.MultiValueMap;
import java.util.List;
import org.springframework.stereotype.Controller;
import org.springframework.ui.Model;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestParam;

@Controller
public class CatalogController {
    private final CatalogService catalog;

    public CatalogController(CatalogService catalog) { this.catalog = catalog; }

    @GetMapping("/products")
    public String products(@RequestParam MultiValueMap<String, String> parameters, Model model) {
        CatalogPage result = catalog.products(CatalogQuery.bind(
                single(parameters, "categoryId"), single(parameters, "type"),
                single(parameters, "q"), single(parameters, "sort"),
                single(parameters, "page"), single(parameters, "size")));
        model.addAttribute("query", result.query());
        model.addAttribute("selectedTheme", result.selectedTheme());
        model.addAttribute("products", result.products());
        model.addAttribute("total", result.total());
        model.addAttribute("totalPages", result.totalPages());
        model.addAttribute("page", result.query().page());
        model.addAttribute("size", result.query().size());
        model.addAttribute("hasPrevious", result.hasPrevious());
        model.addAttribute("hasNext", result.hasNext());
        model.addAttribute("previousPage", result.previousPage());
        model.addAttribute("nextPage", result.nextPage());
        model.addAttribute("themes", result.themes());
        model.addAttribute("themeNavigation", result.themeNavigation());
        return "products/list";
    }

    @GetMapping("/products/{productId}")
    public String detail(@PathVariable(name = "productId") String productId, Model model) {
        long id = InputChecks.longInteger("productId", productId, Long.MIN_VALUE, Long.MAX_VALUE);
        ProductDetail detail = catalog.detail(id);
        model.addAttribute("product", detail.product());
        model.addAttribute("theme", detail.theme());
        model.addAttribute("category", detail.category());
        model.addAttribute("images", detail.images());
        return "products/detail";
    }
    private String single(MultiValueMap<String, String> parameters, String name) {
        List<String> values = parameters.get(name);
        if (values == null) return null;
        if (values.size() != 1) {
            throw new BusinessException(HttpStatus.BAD_REQUEST, "DUPLICATE_QUERY_PARAMETER",
                    "每个筛选条件只能提交一个值。");
        }
        return values.get(0);
    }

}
