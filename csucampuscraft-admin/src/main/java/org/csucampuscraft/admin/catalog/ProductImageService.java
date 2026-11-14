package org.csucampuscraft.admin.catalog;

import java.util.LinkedHashMap;
import java.util.Map;
import java.util.function.Supplier;
import org.csucampuscraft.admin.auth.AdminWriteGuard;
import org.csucampuscraft.admin.auth.SessionIdentity;
import org.csucampuscraft.admin.foundation.validation.InputChecks;
import org.csucampuscraft.admin.foundation.web.BusinessException;
import org.springframework.dao.ConcurrencyFailureException;
import org.springframework.dao.DataIntegrityViolationException;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Isolation;
import org.springframework.transaction.annotation.Transactional;

@Service
public class ProductImageService {
    private final ProductMapper products;
    private final ProductImageMapper images;
    private final AdminWriteGuard actors;

    public ProductImageService(ProductMapper products, ProductImageMapper images, AdminWriteGuard actors) {
        this.products = products;
        this.images = images;
        this.actors = actors;
    }

    @Transactional(readOnly = true)
    public ProductImagePage get(long productId) {
        Product product = products.selectProduct(productId);
        if (product == null) throw missingProduct();
        return new ProductImagePage(product, images.selectImages(productId));
    }

    @Transactional(isolation = Isolation.READ_COMMITTED)
    public void create(SessionIdentity actor, long productId, ProductImageInput input) {
        try {
            actors.lock(actor);
            Product parent = locked(productId);
            long expected = requireVersion(parent, input.productVersion());
            ProductImage image = validated(input);
            capacity(parent);
            image.setProductId(productId);
            if (images.insertImage(image) != 1 || image.getId() == null) {
                throw new IllegalStateException("Album insert did not return an identity");
            }
            increment(productId, expected);
        } catch (DataIntegrityViolationException | ConcurrencyFailureException conflict) {
            throw dataConflict();
        }
    }

    @Transactional(isolation = Isolation.READ_COMMITTED)
    public void update(SessionIdentity actor, long productId, long imageId, ProductImageInput input) {
        try {
            actors.lock(actor);
            Product parent = locked(productId);
            long expected = requireVersion(parent, input.productVersion());
            ProductImage current = owned(productId, imageId);
            ProductImage edited = validated(input);
            if (sameContent(current, edited)) return;
            capacity(parent);
            edited.setId(imageId);
            edited.setProductId(productId);
            if (images.updateImage(edited) != 1) throw dataConflict();
            increment(productId, expected);
        } catch (DataIntegrityViolationException | ConcurrencyFailureException conflict) {
            throw dataConflict();
        }
    }

    @Transactional(isolation = Isolation.READ_COMMITTED)
    public void remove(SessionIdentity actor, long productId, long imageId, String rawProductVersion) {
        try {
            actors.lock(actor);
            Product parent = locked(productId);
            long expected = requireVersion(parent, rawProductVersion);
            owned(productId, imageId);
            capacity(parent);
            if (images.deleteImage(productId, imageId) != 1) throw dataConflict();
            increment(productId, expected);
        } catch (DataIntegrityViolationException | ConcurrencyFailureException conflict) {
            throw dataConflict();
        }
    }

    private Product locked(long productId) {
        Product product = products.lockProduct(productId);
        if (product == null) throw missingProduct();
        return product;
    }

    private ProductImage owned(long productId, long imageId) {
        ProductImage image = images.selectImage(productId, imageId);
        if (image == null) {
            throw new BusinessException(HttpStatus.NOT_FOUND, "PRODUCT_IMAGE_NOT_FOUND",
                    "未找到该商品的相册图片。");
        }
        return image;
    }

    private void increment(long productId, long expectedVersion) {
        if (images.incrementProductVersion(productId, expectedVersion) != 1) throw stale();
    }

    private static long requireVersion(Product parent, String raw) {
        if (raw == null || raw.isBlank()) {
            throw new BusinessException(HttpStatus.CONFLICT, "PRODUCT_IMAGE_VERSION_REQUIRED",
                    "缺少商品版本，操作未提交，请重新载入相册页。",
                    Map.of("productVersion", "请重新载入相册页取得商品版本。"));
        }
        long expected = InputChecks.longInteger("productVersion", raw, 0, Long.MAX_VALUE);
        if (parent.getVersion() != expected) throw stale();
        return expected;
    }

    private static ProductImage validated(ProductImageInput input) {
        Map<String, String> errors = new LinkedHashMap<>();
        String imagePath = checked(errors,
                () -> InputChecks.requiredText("imagePath", input.imagePath(), 255), "");
        if (!imagePath.isEmpty() && !safeImagePath(imagePath)) {
            errors.put("imagePath", "请填写 images/ 下的站内相对路径，且不含穿越、协议或特殊路径标记。");
        }
        String altText = checked(errors,
                () -> InputChecks.text("altText", input.altText(), 0, 120), "");
        Integer sortOrder = checked(errors,
                () -> input.sortOrder() == null || input.sortOrder().isBlank() ? 0
                        : InputChecks.integer("sortOrder", input.sortOrder(), 0, Integer.MAX_VALUE), 0);
        if (!errors.isEmpty()) {
            throw new BusinessException(HttpStatus.BAD_REQUEST, "INVALID_PRODUCT_IMAGE_FIELDS",
                    "请检查并修正相册资料。", errors);
        }
        ProductImage image = new ProductImage();
        image.setImagePath(imagePath);
        image.setAltText(altText.isEmpty() ? null : altText);
        image.setSortOrder(sortOrder);
        return image;
    }

    private static boolean safeImagePath(String path) {
        if (!path.startsWith("images/") || path.contains("..") || path.contains(":")
                || path.contains("\\") || path.contains("%") || path.contains("?")
                || path.contains("#") || path.codePoints().anyMatch(Character::isISOControl)) {
            return false;
        }
        for (String segment : path.split("/", -1)) {
            if (".".equals(segment)) return false;
        }
        return true;
    }

    private static boolean sameContent(ProductImage current, ProductImage edited) {
        return current.getImagePath().equals(edited.getImagePath())
                && optional(current.getAltText()).equals(optional(edited.getAltText()))
                && current.getSortOrder().equals(edited.getSortOrder());
    }

    private static String optional(String text) { return text == null ? "" : text; }

    private static <T> T checked(Map<String, String> errors, Supplier<T> validation, T fallback) {
        try { return validation.get(); }
        catch (BusinessException invalid) { errors.putAll(invalid.getFieldErrors()); return fallback; }
    }

    private static void capacity(Product parent) {
        if (parent.getVersion() == Long.MAX_VALUE) {
            throw new BusinessException(HttpStatus.CONFLICT, "PRODUCT_IMAGE_VERSION_OVERFLOW",
                    "商品版本已到允许上限，操作未提交，请联系组员处理。",
                    Map.of("productVersion", "商品版本已到上限，无法保存实际变更。"));
        }
    }

    private static BusinessException stale() {
        return new BusinessException(HttpStatus.CONFLICT, "PRODUCT_IMAGE_VERSION_CONFLICT",
                "商品资料或相册已发生变化，操作未提交，请重新载入相册页。",
                Map.of("productVersion", "页面版本已过期，请重新载入后确认再提交。"));
    }

    private static BusinessException dataConflict() {
        return new BusinessException(HttpStatus.CONFLICT, "PRODUCT_IMAGE_DATA_CONFLICT",
                "商品或相册数据已变化，操作未提交，请重新载入后重试。",
                Map.of("productVersion", "请重新载入相册页后重试。"));
    }

    private static BusinessException missingProduct() {
        return new BusinessException(HttpStatus.NOT_FOUND, "PRODUCT_NOT_FOUND", "未找到请求的商品。");
    }
}
