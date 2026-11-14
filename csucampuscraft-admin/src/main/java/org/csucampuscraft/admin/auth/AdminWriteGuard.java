package org.csucampuscraft.admin.auth;

import java.sql.Connection;
import org.csucampuscraft.admin.foundation.web.BusinessException;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Propagation;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.transaction.support.TransactionSynchronizationManager;

/** Must be the first database operation inside every protected write Service transaction. */
@Service
public class AdminWriteGuard {
    private final StoreUserMapper users;
    public AdminWriteGuard(StoreUserMapper users) { this.users = users; }

    @Transactional(propagation = Propagation.MANDATORY)
    public StoreUser lock(SessionIdentity actor) {
        Integer isolation = TransactionSynchronizationManager.getCurrentTransactionIsolationLevel();
        if (!TransactionSynchronizationManager.isActualTransactionActive()
                || TransactionSynchronizationManager.isCurrentTransactionReadOnly()
                || isolation == null || isolation != Connection.TRANSACTION_READ_COMMITTED) {
            throw new IllegalStateException("Administrator write requires a READ COMMITTED transaction");
        }
        if (actor == null) throw new SessionExpiredException();
        StoreUser current = users.selectForUpdate(actor.userId());
        if (current == null || !"ENABLED".equals(current.getStatus())
                || !actor.authStamp().equals(current.getUpdatedAt())) {
            throw new SessionExpiredException();
        }
        if (!"ADMIN".equals(current.getRole())) {
            throw new BusinessException(HttpStatus.FORBIDDEN, "AUTH_ROLE_FORBIDDEN",
                    "当前账号无权执行此操作。");
        }
        return current;
    }
}
