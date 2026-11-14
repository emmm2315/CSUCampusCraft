package org.csucampuscraft.storefront.order;

import jakarta.servlet.http.HttpServletRequest;
import java.math.BigDecimal;
import java.math.RoundingMode;
import java.security.SecureRandom;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.HexFormat;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import org.csucampuscraft.storefront.auth.CustomerWriteGuard;
import org.csucampuscraft.storefront.auth.SessionIdentity;
import org.csucampuscraft.storefront.catalog.Product;
import org.csucampuscraft.storefront.checkout.CheckoutLine;
import org.csucampuscraft.storefront.checkout.CheckoutService;
import org.csucampuscraft.storefront.checkout.ShippingForm;
import org.csucampuscraft.storefront.foundation.validation.InputChecks;
import org.csucampuscraft.storefront.foundation.web.BusinessException;
import org.springframework.dao.ConcurrencyFailureException;
import org.springframework.dao.DataIntegrityViolationException;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Isolation;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.util.MultiValueMap;

/** The order, all immutable lines, inventory versions and confirmed cart deletion commit together. */
@Service
public class OrderService {
    private static final SecureRandom RANDOM = new SecureRandom();
    private final CustomerWriteGuard customers;
    private final CheckoutService checkout;
    private final OrderMapper orders;
    private final OrderItemMapper items;

    public OrderService(CustomerWriteGuard customers, CheckoutService checkout,
                        OrderMapper orders, OrderItemMapper items) {
        this.customers = customers;
        this.checkout = checkout;
        this.orders = orders;
        this.items = items;
    }

    @Transactional(isolation = Isolation.READ_COMMITTED)
    public OrderSubmissionResult submit(SessionIdentity actor, HttpServletRequest request,
                                         MultiValueMap<String, String> parameters) {
        try {
            // The first database operation must remain the current customer's locked revalidation.
            long userId = customers.lock(actor).getId();
            CheckoutService.Validation validated = checkout.validate(request, parameters);
            if (validated.confirmation().getUserId() != userId) throw changed();
            if (!validated.isValid()) return new OrderSubmissionResult(null, validated);

            List<CheckoutLine> confirmed = validated.confirmation().getItems();
            List<CheckoutLine> sorted = confirmed.stream()
                    .sorted(Comparator.comparingLong(CheckoutLine::productId)).toList();
            Map<Long, Product> locked = new LinkedHashMap<>();
            for (CheckoutLine line : sorted) {
                Product product = orders.selectProductForUpdate(line.productId());
                if (product == null) throw changed();
                locked.put(line.productId(), product);
            }
            BigDecimal total = new BigDecimal("0.00");
            List<SalesOrderItem> snapshots = new ArrayList<>();
            for (CheckoutLine line : sorted) {
                Product product = locked.get(line.productId());
                if (!"ON_SALE".equals(product.getStatus()) || product.getStock() < line.quantity()
                        || product.getVersion() == null || product.getVersion() == Long.MAX_VALUE) throw changed();
                BigDecimal price = amount(product.getPrice());
                if (price.compareTo(line.unitPrice()) != 0) throw changed();
                BigDecimal subtotal = amount(price.multiply(BigDecimal.valueOf(line.quantity())));
                if (subtotal.compareTo(line.subtotal()) != 0) throw changed();
                total = amount(total.add(subtotal));
                SalesOrderItem snapshot = new SalesOrderItem();
                snapshot.setProductId(line.productId());
                snapshot.setSkuSnapshot(product.getSku());
                snapshot.setProductNameSnapshot(product.getName());
                snapshot.setCoverImageSnapshot(product.getCoverImage());
                snapshot.setUnitPrice(price);
                snapshot.setQuantity(line.quantity());
                snapshot.setLineAmount(subtotal);
                snapshots.add(snapshot);
            }
            if (total.compareTo(validated.confirmation().getTotal()) != 0) throw changed();

            ShippingForm shipping = validated.form();
            SalesOrder order = new SalesOrder();
            order.setOrderNo(newOrderNumber());
            order.setUserId(userId);
            order.setStatus("PENDING_PAYMENT");
            order.setTotalAmount(total);
            order.setReceiverName(shipping.receiverName());
            order.setReceiverPhone(shipping.receiverPhone());
            order.setReceiverAddress(shipping.receiverAddress());
            // Product lock waits may outlive the confirmation or the local session.
            checkout.requireCurrent(request, validated.confirmation());
            if (orders.insertOrder(order) != 1 || order.getId() == null) throw changed();
            for (SalesOrderItem snapshot : snapshots) {
                snapshot.setOrderId(order.getId());
                if (items.insertItem(snapshot) != 1 || snapshot.getId() == null) throw changed();
            }
            for (CheckoutLine line : sorted) {
                Product product = locked.get(line.productId());
                if (orders.deductProduct(line.productId(), line.quantity(), product.getVersion()) != 1) throw changed();
            }
            for (CheckoutLine line : confirmed) {
                if (orders.deleteConfirmedCart(userId, line.itemId(), line.productId(),
                        line.quantity(), line.itemVersion()) != 1) throw changed();
            }
            return new OrderSubmissionResult(order.getOrderNo(), validated);
        } catch (DataIntegrityViolationException | ConcurrencyFailureException failed) {
            throw new BusinessException(HttpStatus.CONFLICT, "ORDER_WRITE_CONFLICT",
                    "订单未能完成，请先核对本人订单和购物车，再重新确认。");
        }
    }

    @Transactional(readOnly = true)
    public OrderPage page(long userId, OrderQuery query) {
        long count = orders.countOwn(userId, query);
        List<SalesOrder> rows = count == 0 || !query.isOffsetRepresentable() || query.getOffset() >= count
                ? List.of() : orders.selectOwn(userId, query);
        return new OrderPage(rows, count, query);
    }

    @Transactional(readOnly = true)
    public OrderDetail detail(long userId, String orderNo) {
        // Invalid, unknown and other people's numbers all expose the same not-found page.
        if (orderNo == null || !orderNo.matches("[A-Za-z0-9_-]{1,40}")) throw missing();
        SalesOrder order = orders.selectOwnOrder(userId, orderNo);
        if (order == null) throw missing();
        return new OrderDetail(order, items.selectForOrder(order.getId()));
    }

    private static String newOrderNumber() {
        byte[] entropy = new byte[16];
        RANDOM.nextBytes(entropy);
        // 36 safe characters; the existing unique case-insensitive database key is the final guard.
        return "CSU-" + HexFormat.of().formatHex(entropy);
    }
    private static BigDecimal amount(BigDecimal value) {
        try {
            if (value == null || value.signum() <= 0 || value.compareTo(InputChecks.MAX_MONEY) > 0) {
                throw new ArithmeticException();
            }
            return value.setScale(2, RoundingMode.UNNECESSARY);
        } catch (ArithmeticException invalid) {
            throw new BusinessException(HttpStatus.CONFLICT, "ORDER_AMOUNT_OUT_OF_RANGE",
                    "商品小计或整车金额超过允许范围，请返回购物车调整后重新确认。");
        }
    }
    private static BusinessException changed() {
        return new BusinessException(HttpStatus.CONFLICT, "ORDER_CART_OR_STOCK_CHANGED",
                "购物车、商品价格、状态或库存已变化，本次未生成订单，请重新确认。");
    }
    private static BusinessException missing() {
        return new BusinessException(HttpStatus.NOT_FOUND, "ORDER_NOT_FOUND", "未找到该订单。");
    }
}
