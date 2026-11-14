package org.csucampuscraft.admin.web;

import jakarta.servlet.http.HttpServletRequest;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;
import org.csucampuscraft.admin.auth.SessionSupport;
import org.csucampuscraft.admin.catalog.Product;
import org.csucampuscraft.admin.catalog.ProductImageInput;
import org.csucampuscraft.admin.catalog.ProductImagePage;
import org.csucampuscraft.admin.catalog.ProductImageService;
import org.csucampuscraft.admin.foundation.validation.InputChecks;
import org.csucampuscraft.admin.foundation.web.BusinessException;
import org.springframework.beans.factory.annotation.Value;
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
public final class ProductImageController {
    private static final Set<String> IMAGE_FIELDS = Set.of("imagePath", "altText", "sortOrder", "productVersion");
    private final ProductImageService images;
    private final SessionSupport sessions;
    private final String userBaseUrl;

    public ProductImageController(ProductImageService images, SessionSupport sessions,
            @Value("${csucampuscraft.user-base-url:http://127.0.0.1:8080}") String userBaseUrl) {
        this.images = images;
        this.sessions = sessions;
        // Trusted server configuration only; a request cannot supply the target host or redirect URL.
        this.userBaseUrl = userBaseUrl.strip().replaceAll("/+$", "");
    }

    @GetMapping("/products/{productId}/images")
    public ModelAndView page(@PathVariable("productId") String productId) {
        long id = id("productId", productId);
        return page(images.get(id), null, null, "add", null);
    }

    @PostMapping("/products/{productId}/images")
    public ModelAndView create(@PathVariable("productId") String productId,
                               @RequestParam MultiValueMap<String, String> parameters,
                               HttpServletRequest request) {
        long id = id("productId", productId);
        ProductImageInput input = input(parameters);
        try {
            rejectDuplicates(parameters, IMAGE_FIELDS);
            images.create(sessions.identity(request), id, input);
            return redirect(id);
        } catch (BusinessException failure) {
            if (!formFailure(failure)) throw failure;
            return page(images.get(id), input, null, "add", failure);
        }
    }

    @PostMapping("/products/{productId}/images/{imageId}")
    public ModelAndView update(@PathVariable("productId") String productId,
                               @PathVariable("imageId") String imageId,
                               @RequestParam MultiValueMap<String, String> parameters,
                               HttpServletRequest request) {
        long parentId = id("productId", productId);
        long rowId = id("imageId", imageId);
        ProductImageInput input = input(parameters);
        try {
            rejectDuplicates(parameters, IMAGE_FIELDS);
            images.update(sessions.identity(request), parentId, rowId, input);
            return redirect(parentId);
        } catch (BusinessException failure) {
            if (!formFailure(failure)) throw failure;
            return page(images.get(parentId), input, rowId, "edit", failure);
        }
    }

    @PostMapping("/products/{productId}/images/{imageId}/remove")
    public ModelAndView remove(@PathVariable("productId") String productId,
                               @PathVariable("imageId") String imageId,
                               @RequestParam MultiValueMap<String, String> parameters,
                               HttpServletRequest request) {
        long parentId = id("productId", productId);
        long rowId = id("imageId", imageId);
        ProductImageInput input = new ProductImageInput(null, null, null, first(parameters, "productVersion"));
        try {
            rejectDuplicates(parameters, Set.of("productVersion"));
            images.remove(sessions.identity(request), parentId, rowId, input.productVersion());
            return redirect(parentId);
        } catch (BusinessException failure) {
            if (!formFailure(failure)) throw failure;
            return page(images.get(parentId), input, rowId, "remove", failure);
        }
    }

    private ModelAndView page(ProductImagePage page, ProductImageInput input, Long formImageId,
                              String action, BusinessException failure) {
        Product product = page.product();
        ModelAndView view = new ModelAndView("products/images");
        view.addObject("product", product);
        view.addObject("images", page.images());
        view.addObject("productVersion", product.getVersion());
        view.addObject("imageForm", input == null
                ? new ProductImageInput("", "", "0", product.getVersion().toString()) : input);
        view.addObject("formImageId", formImageId);
        view.addObject("formImagePresent", formImageId == null || page.images().stream()
                .anyMatch(image -> formImageId.equals(image.getId())));
        view.addObject("formAction", action);
        view.addObject("reloadUrl", path(product.getId()));
        view.addObject("userDetailUrl", userBaseUrl + "/products/" + product.getId());
        Map<String, String> fieldErrors = failure == null ? Map.of() : failure.getFieldErrors();
        view.addObject("fieldErrors", fieldErrors);
        Map<String, String> anchors = new LinkedHashMap<>();
        String prefix = formImageId == null ? "add-" : "image-" + formImageId + "-";
        fieldErrors.forEach((field, message) -> anchors.put(prefix + field, message));
        view.addObject("errorAnchors", anchors);
        if (failure != null) {
            view.setStatus(failure.getStatus());
            view.addObject("globalError", failure.getMessage());
        }
        return view;
    }

    private static ProductImageInput input(MultiValueMap<String, String> parameters) {
        return new ProductImageInput(first(parameters, "imagePath"), first(parameters, "altText"),
                first(parameters, "sortOrder"), first(parameters, "productVersion"));
    }

    private static boolean formFailure(BusinessException failure) {
        return failure.getStatus() == HttpStatus.BAD_REQUEST || failure.getStatus() == HttpStatus.CONFLICT;
    }

    private static void rejectDuplicates(MultiValueMap<String, String> parameters, Set<String> fields) {
        for (String field : fields) {
            List<String> values = parameters.get(field);
            if (values != null && values.size() != 1) {
                throw new BusinessException(HttpStatus.BAD_REQUEST, "DUPLICATE_PRODUCT_IMAGE_FIELD",
                        "每个相册字段只能提交一个值。", Map.of(field, "请为此字段提交一个值。"));
            }
        }
    }

    private static String first(MultiValueMap<String, String> parameters, String field) {
        List<String> values = parameters.get(field);
        return values == null || values.isEmpty() ? null : values.get(0);
    }

    private static long id(String field, String raw) {
        return InputChecks.longInteger(field, raw, 1, Long.MAX_VALUE);
    }

    private static String path(long productId) { return "/products/" + productId + "/images"; }

    private static ModelAndView redirect(long productId) {
        RedirectView redirect = new RedirectView(path(productId), true);
        redirect.setStatusCode(HttpStatus.SEE_OTHER);
        redirect.setExposeModelAttributes(false);
        redirect.setExpandUriTemplateVariables(false);
        return new ModelAndView(redirect);
    }
}
