package org.csucampuscraft.storefront.cart;

import java.sql.Connection;
import org.csucampuscraft.storefront.auth.SessionExpiredException;
import org.csucampuscraft.storefront.auth.SessionIdentity;
import org.csucampuscraft.storefront.auth.StoreUser;
import org.csucampuscraft.storefront.foundation.web.BusinessException;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Propagation;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.transaction.support.TransactionSynchronizationManager;

/** First database operation in a customer write; coordinates with account disable and checkout. */
@Service
public class CustomerWriteGuard {
    private final CartItemMapper items;

    public CustomerWriteGuard(CartItemMapper items) { this.items = items; }

    @Transactional(propagation = Propagation.MANDATORY)
    public StoreUser lock(SessionIdentity actor) {
        Integer isolation = TransactionSynchronizationManager.getCurrentTransactionIsolationLevel();
        if (!TransactionSynchronizationManager.isActualTransactionActive()
                || TransactionSynchronizationManager.isCurrentTransactionReadOnly()
                || isolation == null || isolation != Connection.TRANSACTION_READ_COMMITTED) {
            throw new IllegalStateException("Customer write requires a READ COMMITTED transaction");
        }
        if (actor == null) throw new SessionExpiredException();
        StoreUser current = items.lockUser(actor.userId());
        if (current == null || !"ENABLED".equals(current.getStatus())
                || !actor.authStamp().equals(current.getUpdatedAt())) {
            throw new SessionExpiredException();
        }
        if (!"CUSTOMER".equals(current.getRole())) {
            throw new BusinessException(HttpStatus.FORBIDDEN, "AUTH_ROLE_FORBIDDEN",
                    "当前账号无权执行此操作。");
        }
        return current;
    }
}
