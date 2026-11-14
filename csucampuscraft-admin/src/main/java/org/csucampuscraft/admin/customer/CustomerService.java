package org.csucampuscraft.admin.customer;

import java.util.List;
import java.util.Map;
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
public class CustomerService {
    private final AdminWriteGuard administrators;
    private final CustomerMapper customers;
    public CustomerService(AdminWriteGuard administrators, CustomerMapper customers) {
        this.administrators = administrators;
        this.customers = customers;
    }
    @Transactional(readOnly = true)
    public CustomerPage page(CustomerQuery query) {
        long count = customers.count(query);
        List<CustomerProfile> rows = count == 0 || !query.isOffsetRepresentable() || query.offset() >= count
                ? List.of() : customers.selectPage(query);
        return new CustomerPage(rows, count, query);
    }
    @Transactional(readOnly = true)
    public CustomerProfile detail(String userId) {
        long id = InputChecks.longInteger("userId", userId, 1, Long.MAX_VALUE);
        CustomerProfile customer = customers.selectCustomer(id);
        if (customer == null) throw missing();
        return customer;
    }
    @Transactional(isolation = Isolation.READ_COMMITTED)
    public CustomerStatusResult changeStatus(SessionIdentity actor, String userId, List<String> targetStatuses) {
        try {
            // First database operation, even for malformed target input.
            administrators.lock(actor);
            long id = InputChecks.longInteger("userId", userId, 1, Long.MAX_VALUE);
            CustomerTarget current = customers.selectTargetForUpdate(id);
            if (current == null || !"CUSTOMER".equals(current.role())) throw missing();
            if (targetStatuses == null || targetStatuses.size() != 1) throw invalidTarget();
            CustomerStatus target = InputChecks.enumeration("targetStatus", targetStatuses.get(0), CustomerStatus.class);
            if (target.name().equals(current.status())) return CustomerStatusResult.UNCHANGED;
            if (customers.changeStatus(id, target.name(), current.status(), current.updatedAt()) != 1) throw writeConflict();
            return CustomerStatusResult.CHANGED;
        } catch (DataIntegrityViolationException | ConcurrencyFailureException failed) {
            // Includes timestamp range rejection: rollback, no automatic write retry, no technical detail.
            throw writeConflict();
        }
    }
    private static BusinessException invalidTarget() {
        return new BusinessException(HttpStatus.BAD_REQUEST, "INVALID_TARGET_STATUS", "请选择唯一的目标启停状态。",
                Map.of("targetStatus", "只能提交一个启用或禁用状态。"));
    }
    private static BusinessException missing() {
        return new BusinessException(HttpStatus.NOT_FOUND, "CUSTOMER_NOT_FOUND", "未找到该普通顾客。");
    }
    private static BusinessException writeConflict() {
        return new BusinessException(HttpStatus.CONFLICT, "CUSTOMER_STATUS_WRITE_CONFLICT",
                "顾客状态未能更新，请先查看当前状态，再决定是否重试。");
    }
}
