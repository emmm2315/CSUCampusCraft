package org.csucampuscraft.admin.catalog;

import java.math.BigDecimal;
import java.nio.charset.StandardCharsets;
import java.util.*;
import java.util.function.Supplier;
import org.csucampuscraft.admin.auth.AdminWriteGuard;
import org.csucampuscraft.admin.auth.SessionIdentity;
import org.csucampuscraft.admin.foundation.validation.InputChecks;
import org.csucampuscraft.admin.foundation.web.BusinessException;
import org.springframework.dao.ConcurrencyFailureException;
import org.springframework.dao.DataIntegrityViolationException;
import org.springframework.dao.DuplicateKeyException;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Isolation;
import org.springframework.transaction.annotation.Transactional;

@Service
public class ProductService {
    private static final String DEFAULT_COVER = "images/catalog-placeholder.svg";
    private static final BigDecimal MIN_PRICE = new BigDecimal("0.01");
    private final ProductMapper products;
    private final AdminWriteGuard actors;

    public ProductService(ProductMapper products, AdminWriteGuard actors) {
        this.products = products;
        this.actors = actors;
    }

    @Transactional(readOnly = true)
    public ProductPage list(ProductQuery query) {
        Category scope = query.categoryId() == null ? null : products.selectCategory(query.categoryId());
        if (query.categoryId() != null && scope == null) throw missingCategory();
        boolean root = scope != null && scope.getParentId() == null;
        long total = products.countProducts(query, root);
        long pages = total == 0 ? 0 : 1 + (total - 1) / query.size();
        boolean inRange = query.page() <= pages;
        List<Product> rows = inRange
                ? products.selectProducts(query, root, Math.multiplyExact(query.page() - 1, (long) query.size()))
                : List.of();
        return new ProductPage(query, rows, total, pages,
                inRange ? Math.max(1, query.page() - 1) : Math.max(1, pages),
                inRange && query.page() < pages ? query.page() + 1 : query.page(),
                query.page() > 1, inRange && query.page() < pages);
    }

    @Transactional(readOnly = true)
    public Product get(long id) {
        Product product = products.selectProduct(id);
        if (product == null) throw missingProduct();
        return product;
    }

    @Transactional(readOnly = true)
    public List<ProductCategoryChoice> categories() {
        List<Category> all = products.selectCategories();
        Map<Long, Category> roots = new HashMap<>();
        for (Category c : all) if (c.getParentId() == null) roots.put(c.getId(), c);
        List<ProductCategoryChoice> result = new ArrayList<>();
        for (Category c : all) {
            if (c.getParentId() == null) {
                result.add(new ProductCategoryChoice(c.getId(), "主题：" + c.getName(), false));
                for (Category child : all) {
                    if (c.getId().equals(child.getParentId())) {
                        result.add(new ProductCategoryChoice(child.getId(),
                                c.getName() + " / " + child.getName(), true));
                    }
                }
            }
        }
        return result;
    }

    @Transactional(isolation = Isolation.READ_COMMITTED)
    public Product create(SessionIdentity actor, ProductInput input) {
        try {
            actors.lock(actor);
            Product validated = validated(input, null);
            requireSecondLevel(validated.getCategoryId());
            if (products.countSku(validated.getSku()) != 0) throw duplicateSku();
            validated.setStatus("DRAFT");
            validated.setVersion(0L);
            if (products.insertProduct(validated) != 1 || validated.getId() == null) {
                throw new IllegalStateException("Product insert did not return an identity");
            }
            Product created = products.selectProduct(validated.getId());
            if (created == null || !validated.getSku().equals(created.getSku())) {
                throw new IllegalStateException("Product insert identity could not be verified");
            }
            return created;
        } catch (DuplicateKeyException duplicate) {
            throw duplicateSku();
        } catch (DataIntegrityViolationException | ConcurrencyFailureException conflict) {
            throw databaseConflict();
        }
    }

    @Transactional(isolation = Isolation.READ_COMMITTED)
    public void update(SessionIdentity actor, long id, ProductInput input) {
        try {
            actors.lock(actor);
            Product current = locked(id);
            long version = version(input.version());
            expectVersion(current, version);
            Product edited = validated(input, current);
            requireSecondLevel(edited.getCategoryId());
            if (sameDetails(current, edited)) return;
            capacity(current);
            edited.setId(current.getId());
            if (products.updateDetails(edited, version) != 1) throw stale();
        } catch (DataIntegrityViolationException | ConcurrencyFailureException conflict) {
            throw databaseConflict();
        }
    }

    @Transactional(isolation = Isolation.READ_COMMITTED)
    public void publish(SessionIdentity actor, long id, String rawVersion) {
        try {
            actors.lock(actor);
            Product current = locked(id);
            long version = version(rawVersion);
            expectVersion(current, version);
            if (!"DRAFT".equals(current.getStatus())) throw stateConflict();
            // Validate current locked data without changing name, price, stock or any snapshot.
            validated(ProductInput.fromProduct(current), current);
            requireSecondLevel(current.getCategoryId());
            capacity(current);
            if (products.updateStatus(id, version, "DRAFT", "ON_SALE") != 1) throw stale();
        } catch (DataIntegrityViolationException | ConcurrencyFailureException conflict) {
            throw databaseConflict();
        }
    }

    @Transactional(isolation = Isolation.READ_COMMITTED)
    public void unpublish(SessionIdentity actor, long id, String rawVersion) {
        try {
            actors.lock(actor);
            Product current = locked(id);
            long version = version(rawVersion);
            expectVersion(current, version);
            if (!"ON_SALE".equals(current.getStatus())) throw stateConflict();
            capacity(current);
            if (products.updateStatus(id, version, "ON_SALE", "DRAFT") != 1) throw stale();
        } catch (DataIntegrityViolationException | ConcurrencyFailureException conflict) {
            throw databaseConflict();
        }
    }

    @Transactional(isolation = Isolation.READ_COMMITTED)
    public void restock(SessionIdentity actor, long id, String rawQuantity) {
        try {
            actors.lock(actor);
            Product current = locked(id);
            int quantity = InputChecks.integer("quantity", rawQuantity, 1, Integer.MAX_VALUE);
            capacity(current);
            int maximumBeforeAdd = Integer.MAX_VALUE - quantity;
            if (current.getStock() > maximumBeforeAdd) {
                throw conflict("STOCK_OVERFLOW", "本次补货会超过库存范围，请减少补货量。",
                        Map.of("quantity", "本次增加量超过库存允许范围。"));
            }
            // The SQL adds to the locked database value; no submitted stock/version is used.
            if (products.addStock(id, quantity, maximumBeforeAdd) != 1) throw stale();
        } catch (DataIntegrityViolationException | ConcurrencyFailureException conflict) {
            throw databaseConflict();
        }
    }

    private Product locked(long id) {
        Product current = products.lockProduct(id);
        if (current == null) throw missingProduct();
        return current;
    }

    private void requireSecondLevel(long id) {
        Category category = products.lockCategory(id);
        if (category == null) throw missingCategory();
        Category parent = category.getParentId() == null ? null : products.selectCategory(category.getParentId());
        if (parent == null || parent.getParentId() != null) {
            throw invalid("categoryId", "请选择有效的二级分类。");
        }
    }

    private Product validated(ProductInput input, Product current) {
        Map<String, String> errors = new LinkedHashMap<>();
        String sku = current == null
                ? checked(errors, () -> InputChecks.requiredText("sku", input.sku(), 40), "")
                : current.getSku();
        Long categoryId = checked(errors,
                () -> InputChecks.longInteger("categoryId", input.categoryId(), 1, Long.MAX_VALUE), null);
        String name = checked(errors, () -> InputChecks.requiredText("name", input.name(), 120), "");
        BigDecimal price = checked(errors,
                () -> InputChecks.money("price", input.price(), MIN_PRICE, InputChecks.MAX_MONEY), null);
        String summary = checked(errors, () -> InputChecks.text("summary", input.summary(), 0, 500), "");
        String description = input.description() == null ? "" : input.description();
        if (description.getBytes(StandardCharsets.UTF_8).length > 65535) {
            errors.put("description", "设计说明内容过长，请缩短到 65,535 字节以内。");
        }
        String cover = checked(errors, () -> InputChecks.text("coverImage", input.coverImage(), 0, 255), "");
        if (cover.isEmpty()) cover = DEFAULT_COVER;
        if (!cover.startsWith("images/") || cover.contains("..") || cover.contains(":")
                || cover.contains("%") || cover.contains("?") || cover.contains("#")
                || cover.contains("\\") || cover.codePoints().anyMatch(c -> c < 32 || c == 127)) {
            errors.put("coverImage", "封面应是 images/ 下的站内相对路径，不得含特殊路径标记。");
        }
        Integer stock = current == null ? checked(errors,
                () -> optionalInteger("stock", input.stock()), 0) : current.getStock();
        Integer sortOrder = checked(errors, () -> optionalInteger("sortOrder", input.sortOrder()), 0);
        if (!errors.isEmpty()) {
            throw new BusinessException(HttpStatus.BAD_REQUEST, "INVALID_PRODUCT_FIELDS",
                    "请检查并修正商品资料。", errors);
        }
        Product value = new Product();
        value.setSku(sku);
        value.setCategoryId(categoryId);
        value.setName(name);
        value.setPrice(price);
        value.setSummary(summary);
        value.setDescription(description);
        value.setCoverImage(cover);
        value.setStock(stock);
        value.setSortOrder(sortOrder);
        return value;
    }

    private static int optionalInteger(String name, String raw) {
        return raw == null || raw.isBlank() ? 0 : InputChecks.integer(name, raw, 0, Integer.MAX_VALUE);
    }

    private static <T> T checked(Map<String, String> errors, Supplier<T> check, T fallback) {
        try { return check.get(); }
        catch (BusinessException invalid) { errors.putAll(invalid.getFieldErrors()); return fallback; }
    }

    private static String optional(String text) { return text == null ? "" : text; }

    private static boolean sameDetails(Product a, Product b) {
        return a.getCategoryId().equals(b.getCategoryId()) && a.getName().equals(b.getName())
                && a.getPrice().compareTo(b.getPrice()) == 0
                && optional(a.getSummary()).equals(optional(b.getSummary()))
                && optional(a.getDescription()).equals(optional(b.getDescription()))
                && a.getCoverImage().equals(b.getCoverImage())
                && a.getSortOrder().equals(b.getSortOrder());
    }

    private static long version(String value) {
        return InputChecks.longInteger("version", value, 0, Long.MAX_VALUE);
    }
    private static void expectVersion(Product current, long expected) {
        if (current.getVersion() != expected) throw stale();
    }
    private static void capacity(Product current) {
        if (current.getVersion() == Long.MAX_VALUE) {
            throw conflict("PRODUCT_VERSION_OVERFLOW", "商品版本已到允许上限，操作未提交，请联系组员处理。", Map.of());
        }
    }
    private static BusinessException invalid(String field, String message) {
        return new BusinessException(HttpStatus.BAD_REQUEST, "INVALID_PRODUCT_FIELD", message, Map.of(field, message));
    }
    private static BusinessException duplicateSku() {
        return conflict("SKU_ALREADY_EXISTS", "该 SKU 已存在，请修改后再提交。", Map.of("sku", "该 SKU 已被使用。"));
    }
    private static BusinessException stale() {
        return conflict("PRODUCT_VERSION_CONFLICT", "商品资料已发生变化，请重新载入后确认再提交。",
                Map.of("version", "页面已过期，请重新载入编辑页。"));
    }
    private static BusinessException stateConflict() {
        return conflict("PRODUCT_STATE_CONFLICT", "商品状态已变化，请刷新列表后重新操作。", Map.of());
    }
    private static BusinessException databaseConflict() {
        return conflict("PRODUCT_DATA_CONFLICT", "商品或分类数据已变化，请刷新后重试。", Map.of());
    }
    private static BusinessException conflict(String code, String message, Map<String, String> fields) {
        return new BusinessException(HttpStatus.CONFLICT, code, message, fields);
    }
    private static BusinessException missingProduct() {
        return new BusinessException(HttpStatus.NOT_FOUND, "PRODUCT_NOT_FOUND", "未找到请求的商品。");
    }
    private static BusinessException missingCategory() {
        return new BusinessException(HttpStatus.NOT_FOUND, "CATEGORY_NOT_FOUND", "未找到请求的商品分类。");
    }
}
