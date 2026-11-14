package org.csucampuscraft.storefront.cart;

import java.math.BigDecimal;
import java.util.List;
import java.util.Map;
import org.csucampuscraft.storefront.auth.CustomerWriteGuard;
import org.csucampuscraft.storefront.auth.SessionIdentity;
import org.csucampuscraft.storefront.catalog.Product;
import org.csucampuscraft.storefront.foundation.web.BusinessException;
import org.springframework.dao.ConcurrencyFailureException;
import org.springframework.dao.DataIntegrityViolationException;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Isolation;
import org.springframework.transaction.annotation.Transactional;

/** Every cart write is serialized by the current customer's row; inventory is never written. */
@Service
public class CartService {
    private final CartItemMapper items;
    private final CustomerWriteGuard customers;

    public CartService(CartItemMapper items, CustomerWriteGuard customers) {
        this.items = items;
        this.customers = customers;
    }

    @Transactional(readOnly = true)
    public CartPage read(long userId) {
        List<CartLine> lines = items.selectLines(userId);
        BigDecimal subtotal = new BigDecimal("0.00");
        long quantity = 0;
        int invalidCount = 0;
        for (CartLine line : lines) {
            quantity += line.getQuantity();
            if (line.isValid()) subtotal = subtotal.add(line.getSubtotal());
            else invalidCount++;
        }
        return new CartPage(lines, quantity, subtotal, invalidCount);
    }

    /** Exact navigation contract: all own quantities, including every invalid row. */
    @Transactional(readOnly = true)
    public long quantityFor(long userId) { return items.selectQuantity(userId); }

    @Transactional(isolation = Isolation.READ_COMMITTED)
    public void add(SessionIdentity actor, long productId, int quantity) {
        try {
            long userId = customers.lock(actor).getId();
            checkId("productId", productId);
            checkQuantity(quantity);
            List<CartItem> cart = items.selectByUser(userId);
            Product product = available(items.selectProduct(productId));
            CartItem existing = cart.stream().filter(item -> item.getProductId() == productId)
                    .findFirst().orElse(null);
            int combined = quantity + (existing == null ? 0 : existing.getQuantity());
            if (combined > 99) {
                throw quantityConflict("CART_QUANTITY_LIMIT", "该商品合计不能超过 99 件，请先核对购物车。");
            }
            if (existing == null && cart.size() >= 20) {
                throw new BusinessException(HttpStatus.CONFLICT, "CART_SKU_LIMIT",
                        "购物车最多保留 20 种商品，请先移除条目后再添加。");
            }
            requireStock(product, combined);
            if (existing == null) {
                CartItem added = new CartItem();
                added.setUserId(userId);
                added.setProductId(productId);
                added.setQuantity(quantity);
                added.setVersion(0L);
                if (items.insertItem(added) != 1 || added.getId() == null) {
                    throw new IllegalStateException("Cart insert did not return an identity");
                }
            } else {
                capacity(existing);
                if (items.updateQuantity(userId, existing.getId(), combined, existing.getVersion()) != 1) {
                    throw versionConflict();
                }
            }
        } catch (DataIntegrityViolationException | ConcurrencyFailureException conflict) {
            throw dataConflict();
        }
    }

    @Transactional(isolation = Isolation.READ_COMMITTED)
    public void changeQuantity(SessionIdentity actor, long itemId, int quantity, long version) {
        try {
            long userId = customers.lock(actor).getId();
            checkId("itemId", itemId);
            checkQuantity(quantity);
            checkVersion(version);
            CartItem current = owned(userId, itemId);
            requireVersion(current, version);
            // A valid same-value request does not modify an invalid row or consume a version.
            if (current.getQuantity() == quantity) return;
            Product product = available(items.selectProduct(current.getProductId()));
            requireStock(product, quantity);
            capacity(current);
            if (items.updateQuantity(userId, itemId, quantity, version) != 1) throw versionConflict();
        } catch (DataIntegrityViolationException | ConcurrencyFailureException conflict) {
            throw dataConflict();
        }
    }

    @Transactional(isolation = Isolation.READ_COMMITTED)
    public void remove(SessionIdentity actor, long itemId, long version) {
        try {
            long userId = customers.lock(actor).getId();
            checkId("itemId", itemId);
            checkVersion(version);
            CartItem current = owned(userId, itemId);
            requireVersion(current, version);
            // Removal never consults product availability and does not increment a deleted version.
            if (items.deleteItem(userId, itemId, version) != 1) throw versionConflict();
        } catch (DataIntegrityViolationException | ConcurrencyFailureException conflict) {
            throw dataConflict();
        }
    }

    private CartItem owned(long userId, long itemId) {
        CartItem item = items.selectItem(itemId);
        if (item == null) {
            throw new BusinessException(HttpStatus.NOT_FOUND, "CART_ITEM_NOT_FOUND",
                    "该购物车条目已不存在，请重新载入购物车。");
        }
        if (item.getUserId() != userId) {
            throw new BusinessException(HttpStatus.FORBIDDEN, "CART_ITEM_FORBIDDEN",
                    "当前账号无权操作此购物车条目。");
        }
        return item;
    }

    private static Product available(Product product) {
        if (product == null || !"ON_SALE".equals(product.getStatus())) {
            throw new BusinessException(HttpStatus.NOT_FOUND, "PRODUCT_NOT_AVAILABLE",
                    "商品不存在或已下架，请返回目录选择其他商品。");
        }
        return product;
    }

    private static void requireStock(Product product, int quantity) {
        if (product.getStock() == 0) {
            throw quantityConflict("PRODUCT_SOLD_OUT", "商品已售罄，购物车未改变。");
        }
        if (quantity > product.getStock()) {
            throw quantityConflict("CART_STOCK_INSUFFICIENT", "购买数量超过当前库存，请减少数量或处理购物车。");
        }
    }

    private static void requireVersion(CartItem item, long version) {
        if (item.getVersion() != version) throw versionConflict();
    }

    private static void capacity(CartItem item) {
        if (item.getVersion() == Long.MAX_VALUE) {
            throw new BusinessException(HttpStatus.CONFLICT, "CART_VERSION_OVERFLOW",
                    "条目版本已到允许上限，数量未修改，请移除后重新添加。",
                    Map.of("version", "条目版本已到上限，无法保存数量变化。"));
        }
    }

    private static void checkId(String field, long id) {
        if (id < 1) {
            throw new BusinessException(HttpStatus.BAD_REQUEST, "INVALID_INTEGER", "请输入允许范围内的整数。",
                    Map.of(field, "请输入正整数。"));
        }
    }

    private static void checkQuantity(int quantity) {
        if (quantity < 1 || quantity > 99) {
            throw new BusinessException(HttpStatus.BAD_REQUEST, "INVALID_INTEGER", "购买数量须为 1–99 的整数。",
                    Map.of("quantity", "购买数量须为 1–99 的整数。"));
        }
    }

    private static void checkVersion(long version) {
        if (version < 0) {
            throw new BusinessException(HttpStatus.BAD_REQUEST, "INVALID_INTEGER", "条目版本格式不正确。",
                    Map.of("version", "请重新载入购物车取得当前版本。"));
        }
    }

    private static BusinessException quantityConflict(String code, String message) {
        return new BusinessException(HttpStatus.CONFLICT, code, message, Map.of("quantity", message));
    }

    private static BusinessException versionConflict() {
        return new BusinessException(HttpStatus.CONFLICT, "CART_VERSION_CONFLICT",
                "购物车条目已发生变化，操作未提交，请重新载入后再确认。",
                Map.of("version", "页面版本已过期，请重新载入购物车。"));
    }

    private static BusinessException dataConflict() {
        return new BusinessException(HttpStatus.CONFLICT, "CART_DATA_CONFLICT",
                "购物车数据已变化，操作未提交，请重新载入后重试。",
                Map.of("version", "请重新载入购物车后重试。"));
    }
}
