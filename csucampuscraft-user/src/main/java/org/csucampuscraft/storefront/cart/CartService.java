package org.csucampuscraft.storefront.cart;

import java.math.BigDecimal;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import org.csucampuscraft.storefront.auth.SessionIdentity;
import org.csucampuscraft.storefront.catalog.Product;
import org.csucampuscraft.storefront.foundation.web.BusinessException;
import org.springframework.dao.ConcurrencyFailureException;
import org.springframework.dao.DataIntegrityViolationException;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Isolation;
import org.springframework.transaction.annotation.Transactional;

@Service
public class CartService {
    private static final BigDecimal ZERO = new BigDecimal("0.00");
    private static final String PLACEHOLDER = "images/catalog-placeholder.svg";
    private final CartItemMapper items;
    private final CustomerWriteGuard actors;

    public CartService(CartItemMapper items, CustomerWriteGuard actors) {
        this.items = items;
        this.actors = actors;
    }

    @Transactional(readOnly = true)
    public CartPage getCart(long userId) {
        positive("userId", userId);
        List<CartLine> lines = new ArrayList<>();
        BigDecimal total = ZERO;
        long quantity = 0;
        boolean allValid = true;
        // Read item, current price and availability in one query; never store price in cart_item.
        for (CartItem row : items.selectCart(userId)) {
            String reason = invalidReason(row);
            boolean valid = reason.isEmpty();
            BigDecimal price = row.getPrice() == null ? ZERO : row.getPrice();
            BigDecimal subtotal = price.multiply(BigDecimal.valueOf(row.getQuantity()));
            lines.add(new CartLine(row.getId(), row.getProductId(),
                    row.getSku() == null ? "" : row.getSku(),
                    row.getName() == null ? "商品已不可用" : row.getName(),
                    row.getCoverImage() == null ? PLACEHOLDER : row.getCoverImage(), price,
                    row.getStock() == null ? 0 : row.getStock(), row.getStatus(),
                    row.getQuantity(), row.getVersion(), subtotal, valid, reason));
            quantity += row.getQuantity();
            if (valid) total = total.add(subtotal);
            else allValid = false;
        }
        return new CartPage(lines, total, !lines.isEmpty() && allValid, quantity);
    }

    @Transactional(readOnly = true)
    public long quantity(long userId) {
        positive("userId", userId);
        return items.sumQuantity(userId);
    }

    @Transactional(isolation = Isolation.READ_COMMITTED)
    public void add(SessionIdentity actor, long productId, int quantity) {
        try {
            actors.lock(actor);
            positive("productId", productId);
            validateQuantity(quantity);
            CartItem current = items.selectForProduct(actor.userId(), productId);
            Product product = items.lockProduct(productId);
            // Product availability wins over quantity/kind/stock conflicts, as specified for add.
            if (product == null || !"ON_SALE".equals(product.getStatus())) throw unavailableProduct();
            int merged = quantity + (current == null ? 0 : current.getQuantity());
            if (merged > 99) {
                throw conflict("CART_QUANTITY_LIMIT", "同一商品合计最多 99 件，请调整购物车数量。",
                        Map.of("quantity", "累加后的数量不能超过 99 件。"));
            }
            if (current == null && items.countKinds(actor.userId()) >= 20) {
                throw conflict("CART_KIND_LIMIT", "购物车最多容纳 20 种商品，请先移除部分商品。", Map.of());
            }
            availableStock(product, merged);
            if (current == null) {
                if (items.insertItem(actor.userId(), productId, quantity) != 1) throw changed();
            } else {
                incrementable(current);
                if (items.updateQuantity(current.getId(), actor.userId(), merged, current.getVersion()) != 1) {
                    throw changed();
                }
            }
        } catch (DataIntegrityViolationException | ConcurrencyFailureException conflict) {
            throw databaseConflict();
        }
    }

    @Transactional(isolation = Isolation.READ_COMMITTED)
    public void changeQuantity(SessionIdentity actor, long itemId, int quantity, long version) {
        try {
            actors.lock(actor);
            positive("itemId", itemId);
            validateQuantity(quantity);
            nonnegativeVersion(version);
            CartItem current = ownedItem(actor.userId(), itemId);
            expectVersion(current, version);
            Product product = items.lockProduct(current.getProductId());
            if (product == null || !"ON_SALE".equals(product.getStatus())) {
                throw conflict("CART_PRODUCT_UNAVAILABLE", "该商品已下架或不可用，请移除后继续选购。", Map.of());
            }
            availableStock(product, quantity);
            // Validate version and availability before treating the same quantity as a no-op.
            if (current.getQuantity() == quantity) return;
            incrementable(current);
            if (items.updateQuantity(itemId, actor.userId(), quantity, version) != 1) throw changed();
        } catch (DataIntegrityViolationException | ConcurrencyFailureException conflict) {
            throw databaseConflict();
        }
    }

    @Transactional(isolation = Isolation.READ_COMMITTED)
    public void remove(SessionIdentity actor, long itemId, long version) {
        try {
            actors.lock(actor);
            positive("itemId", itemId);
            nonnegativeVersion(version);
            CartItem current = ownedItem(actor.userId(), itemId);
            expectVersion(current, version);
            // No product availability test: draft, sold-out and insufficient-stock rows remain removable.
            if (items.deleteItem(itemId, actor.userId(), version) != 1) throw changed();
        } catch (DataIntegrityViolationException | ConcurrencyFailureException conflict) {
            throw databaseConflict();
        }
    }

    private CartItem ownedItem(long userId, long itemId) {
        CartItem row = items.selectItem(itemId);
        if (row == null) {
            throw new BusinessException(HttpStatus.NOT_FOUND, "CART_ITEM_NOT_FOUND", "未找到该购物车条目，请重新读取购物车。");
        }
        if (row.getUserId() != userId) {
            throw new BusinessException(HttpStatus.FORBIDDEN, "CART_ITEM_FORBIDDEN", "无权操作其他账号的购物车条目。");
        }
        return row;
    }

    private static String invalidReason(CartItem row) {
        if (row.getStatus() == null || row.getPrice() == null) return "商品已不存在，请移除。";
        if (!"ON_SALE".equals(row.getStatus())) return "商品已下架，请移除。";
        if (row.getStock() == null || row.getStock() == 0) return "商品已售罄，请调整或移除。";
        if (row.getQuantity() > row.getStock()) return "购买数量超过当前库存，请减少数量或移除。";
        return "";
    }

    private static void availableStock(Product product, int quantity) {
        if (product.getStock() == 0) {
            throw conflict("CART_PRODUCT_SOLD_OUT", "该商品已售罄，请重新选购。",
                    Map.of("quantity", "当前库存为 0，不能加入或增加数量。"));
        }
        if (quantity > product.getStock()) {
            throw conflict("CART_STOCK_INSUFFICIENT", "购买数量超过当前库存，请调整数量后重试。",
                    Map.of("quantity", "购买数量不能超过当前库存。"));
        }
    }

    private static void positive(String field, long value) {
        if (value < 1) throw invalid(field, "请输入正整数。");
    }
    private static void validateQuantity(int value) {
        if (value < 1 || value > 99) throw invalid("quantity", "数量须为 1 至 99 的整数。");
    }
    private static void nonnegativeVersion(long version) {
        if (version < 0) throw invalid("version", "请提交当前条目版本。");
    }
    private static void expectVersion(CartItem current, long expected) {
        if (current.getVersion() != expected) throw changed();
    }
    private static void incrementable(CartItem current) {
        if (current.getVersion() == Long.MAX_VALUE) {
            throw conflict("CART_VERSION_OVERFLOW", "条目版本已到允许上限，本次操作未提交。", Map.of());
        }
    }
    private static BusinessException invalid(String field, String message) {
        return new BusinessException(HttpStatus.BAD_REQUEST, "INVALID_CART_FIELD", message, Map.of(field, message));
    }
    private static BusinessException unavailableProduct() {
        return new BusinessException(HttpStatus.NOT_FOUND, "CART_PRODUCT_NOT_FOUND", "商品不存在或已下架，请返回目录重新选购。");
    }
    private static BusinessException changed() {
        return conflict("CART_VERSION_CONFLICT", "购物车条目已变化，请重新读取购物车后再操作。",
                Map.of("version", "页面版本已过期，请重新读取购物车。"));
    }
    private static BusinessException databaseConflict() {
        return conflict("CART_DATA_CONFLICT", "购物车或商品数据已变化，本次操作未提交，请刷新后重试。", Map.of());
    }
    private static BusinessException conflict(String code, String message, Map<String, String> fields) {
        return new BusinessException(HttpStatus.CONFLICT, code, message, fields);
    }
}
