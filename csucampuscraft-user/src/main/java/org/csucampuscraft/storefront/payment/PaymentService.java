package org.csucampuscraft.storefront.payment;

import java.security.SecureRandom;
import java.util.Comparator;
import java.util.HexFormat;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import org.csucampuscraft.storefront.auth.CustomerWriteGuard;
import org.csucampuscraft.storefront.auth.SessionIdentity;
import org.csucampuscraft.storefront.catalog.Product;
import org.csucampuscraft.storefront.foundation.validation.InputChecks;
import org.csucampuscraft.storefront.foundation.web.BusinessException;
import org.csucampuscraft.storefront.order.OrderDetail;
import org.csucampuscraft.storefront.order.OrderItemMapper;
import org.csucampuscraft.storefront.order.OrderService;
import org.csucampuscraft.storefront.order.SalesOrder;
import org.csucampuscraft.storefront.order.SalesOrderItem;
import org.springframework.dao.ConcurrencyFailureException;
import org.springframework.dao.DataIntegrityViolationException;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Isolation;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.util.MultiValueMap;

/** Payment never touches inventory; cancellation refunds each immutable line exactly once. */
@Service
public class PaymentService {
    private static final SecureRandom RANDOM = new SecureRandom();
    private final CustomerWriteGuard customers;
    private final OrderActionMapper actions;
    private final OrderItemMapper items;
    private final OrderService orders;

    public PaymentService(CustomerWriteGuard customers, OrderActionMapper actions,
                          OrderItemMapper items, OrderService orders) {
        this.customers = customers;
        this.actions = actions;
        this.items = items;
        this.orders = orders;
    }

    @Transactional(readOnly = true)
    public OrderDetail paymentPage(long userId, String orderNo) {
        OrderDetail detail = orders.detail(userId, orderNo);
        if (!"PENDING_PAYMENT".equals(detail.getOrder().getStatus())) throw paymentConflict();
        return detail;
    }

    @Transactional(isolation = Isolation.READ_COMMITTED)
    public OrderActionResult pay(SessionIdentity actor, String orderNo,
                                 MultiValueMap<String, String> parameters) {
        try {
            // First database operation: lock and revalidate the current enabled CUSTOMER.
            long userId = customers.lock(actor).getId();
            SalesOrder order = ownLocked(userId, orderNo);
            PaymentResult result = paymentResult(parameters);
            String status = order.getStatus();
            if ("PENDING_PAYMENT".equals(status)) {
                if (result == PaymentResult.FAILURE) return OrderActionResult.PAYMENT_FAILED;
                byte[] entropy = new byte[16];
                RANDOM.nextBytes(entropy);
                String receipt = "CSUPAY-" + HexFormat.of().formatHex(entropy);
                if (actions.markPaid(userId, order.getId(), receipt) != 1) throw writeConflict();
                return OrderActionResult.PAYMENT_SUCCEEDED;
            }
            if (("PAID".equals(status) || "SHIPPED".equals(status) || "COMPLETED".equals(status))
                    && result == PaymentResult.SUCCESS) {
                return OrderActionResult.PAYMENT_ALREADY_SUCCEEDED;
            }
            throw paymentConflict();
        } catch (DataIntegrityViolationException | ConcurrencyFailureException conflict) {
            throw writeConflict();
        }
    }

    @Transactional(isolation = Isolation.READ_COMMITTED)
    public OrderActionResult cancel(SessionIdentity actor, String orderNo) {
        try {
            // Do not move format, resource or state queries ahead of the operator guard.
            long userId = customers.lock(actor).getId();
            SalesOrder order = ownLocked(userId, orderNo);
            if ("CANCELLED".equals(order.getStatus())) return OrderActionResult.ORDER_ALREADY_CANCELLED;
            if (!"PENDING_PAYMENT".equals(order.getStatus())) throw cancelConflict();
            List<SalesOrderItem> lines = items.selectForOrder(order.getId()).stream()
                    .sorted(Comparator.comparing(SalesOrderItem::getProductId)).toList();
            if (lines.isEmpty()) throw inventoryConflict();
            Map<Long, Product> locked = new LinkedHashMap<>();
            // Acquire every product lock in ascending order before any write occurs.
            for (SalesOrderItem line : lines) {
                Product product = actions.selectProductForUpdate(line.getProductId());
                if (product == null) throw inventoryConflict();
                locked.put(line.getProductId(), product);
            }
            for (SalesOrderItem line : lines) {
                Product product = locked.get(line.getProductId());
                if (line.getQuantity() == null || line.getQuantity() < 1 || line.getQuantity() > 99
                        || product.getStock() == null || product.getStock() < 0
                        || product.getVersion() == null || product.getVersion() == Long.MAX_VALUE
                        || (long) product.getStock() + line.getQuantity() > Integer.MAX_VALUE) {
                    throw inventoryConflict();
                }
            }
            for (SalesOrderItem line : lines) {
                Product product = locked.get(line.getProductId());
                if (actions.restockProduct(line.getProductId(), line.getQuantity(), product.getVersion()) != 1) {
                    throw inventoryConflict();
                }
            }
            if (actions.markCancelled(userId, order.getId()) != 1) throw writeConflict();
            return OrderActionResult.ORDER_CANCELLED;
        } catch (DataIntegrityViolationException | ConcurrencyFailureException conflict) {
            throw writeConflict();
        }
    }

    private SalesOrder ownLocked(long userId, String orderNo) {
        if (orderNo == null || !orderNo.matches("[A-Za-z0-9_-]{1,40}")) throw missing();
        SalesOrder order = actions.selectOwnForUpdate(userId, orderNo);
        if (order == null) throw missing();
        return order;
    }
    private static PaymentResult paymentResult(MultiValueMap<String, String> parameters) {
        List<String> values = parameters == null ? null : parameters.get("result");
        if (values != null && values.size() != 1) {
            throw new BusinessException(HttpStatus.BAD_REQUEST, "DUPLICATE_PAYMENT_RESULT",
                    "模拟支付结果只能提交一个值。", Map.of("result", "请只选择一个模拟结果。"));
        }
        return InputChecks.enumeration("result", values == null || values.isEmpty() ? null : values.get(0),
                PaymentResult.class);
    }
    private static BusinessException missing() {
        return new BusinessException(HttpStatus.NOT_FOUND, "ORDER_NOT_FOUND", "未找到该订单。");
    }
    private static BusinessException paymentConflict() {
        return new BusinessException(HttpStatus.CONFLICT, "PAYMENT_STATE_CONFLICT",
                "当前订单状态不允许这次模拟支付，请查看订单详情。");
    }
    private static BusinessException cancelConflict() {
        return new BusinessException(HttpStatus.CONFLICT, "CANCELLATION_STATE_CONFLICT",
                "当前订单状态不允许取消，请查看订单详情。");
    }
    private static BusinessException inventoryConflict() {
        return new BusinessException(HttpStatus.CONFLICT, "CANCELLATION_INVENTORY_CONFLICT",
                "库存或商品版本无法完成返还，本次未取消订单，请查看订单后再处理。");
    }
    private static BusinessException writeConflict() {
        return new BusinessException(HttpStatus.CONFLICT, "ORDER_ACTION_WRITE_CONFLICT",
                "订单操作未能完成，请先核对订单状态，再决定是否重试。");
    }
}
