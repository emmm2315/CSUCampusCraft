package org.csucampuscraft.admin.order;

import java.util.List;
import org.csucampuscraft.admin.auth.AdminWriteGuard;
import org.csucampuscraft.admin.auth.SessionIdentity;
import org.csucampuscraft.admin.foundation.web.BusinessException;
import org.springframework.dao.ConcurrencyFailureException;
import org.springframework.dao.DataIntegrityViolationException;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Isolation;
import org.springframework.transaction.annotation.Transactional;

/** Administrator-wide reads and a single order-row state transition; no inventory mapper. */
@Service
public class AdminOrderService {
    private final AdminWriteGuard administrators;
    private final OrderMapper orders;
    private final OrderItemMapper items;
    public AdminOrderService(AdminWriteGuard administrators, OrderMapper orders, OrderItemMapper items) {
        this.administrators = administrators;
        this.orders = orders;
        this.items = items;
    }

    @Transactional(readOnly = true)
    public OrderPage page(OrderQuery query) {
        OrderCustomer customer = query.userId() == null ? null : orders.selectCustomer(query.userId());
        if (query.userId() != null && customer == null) {
            throw new BusinessException(HttpStatus.NOT_FOUND, "ORDER_CUSTOMER_NOT_FOUND", "未找到该普通顾客。");
        }
        long count = orders.count(query);
        List<SalesOrder> rows = count == 0 || !query.isOffsetRepresentable() || query.getOffset() >= count
                ? List.of() : orders.selectPage(query);
        return new OrderPage(rows, count, query, customer);
    }

    @Transactional(readOnly = true)
    public OrderDetail detail(String orderNo) {
        requireNumber(orderNo);
        SalesOrder order = orders.selectOrder(orderNo);
        if (order == null) throw missing();
        return new OrderDetail(order, items.selectForOrder(order.getId()));
    }

    @Transactional(isolation = Isolation.READ_COMMITTED)
    public ShipmentResult ship(SessionIdentity actor, String orderNo) {
        try {
            // First database operation: lock the current administrator and revalidate the UTC stamp.
            administrators.lock(actor);
            requireNumber(orderNo);
            // Deliberately no user join or product/item query in the locked write path.
            SalesOrder order = orders.selectForUpdate(orderNo);
            if (order == null) throw missing();
            if ("SHIPPED".equals(order.getStatus()) || "COMPLETED".equals(order.getStatus())) {
                return ShipmentResult.ALREADY_SHIPPED;
            }
            if (!"PAID".equals(order.getStatus())) {
                throw new BusinessException(HttpStatus.CONFLICT, "SHIPMENT_STATE_CONFLICT",
                        "当前订单尚未付款或已经取消，不能模拟发货，请核对订单状态。");
            }
            if (orders.markShipped(order.getId()) != 1) throw writeConflict();
            return ShipmentResult.SHIPPED;
        } catch (DataIntegrityViolationException | ConcurrencyFailureException failed) {
            throw writeConflict();
        }
    }

    private static void requireNumber(String orderNo) {
        if (orderNo == null || !orderNo.matches("[A-Za-z0-9_-]{1,40}")) throw missing();
    }
    private static BusinessException missing() {
        return new BusinessException(HttpStatus.NOT_FOUND, "ORDER_NOT_FOUND", "未找到该订单。");
    }
    private static BusinessException writeConflict() {
        return new BusinessException(HttpStatus.CONFLICT, "SHIPMENT_WRITE_CONFLICT",
                "模拟发货未能完成，请先查看订单状态，再决定是否重试。");
    }
}
