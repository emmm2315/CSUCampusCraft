package org.csucampuscraft.storefront.order;

import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpSession;
import org.csucampuscraft.storefront.auth.SessionExpiredException;
import org.csucampuscraft.storefront.auth.SessionIdentity;
import org.csucampuscraft.storefront.auth.SessionSupport;
import org.csucampuscraft.storefront.foundation.web.BusinessException;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.util.MultiValueMap;

/** Keeps the local session stable through the separate Spring transaction proxy and its commit. */
@Service
public final class OrderSubmissionCoordinator {
    private final OrderService orders;
    private final SessionSupport sessions;
    public OrderSubmissionCoordinator(OrderService orders, SessionSupport sessions) {
        this.orders = orders;
        this.sessions = sessions;
    }
    public OrderSubmissionResult submit(HttpServletRequest request,
                                         MultiValueMap<String, String> parameters) {
        SessionIdentity expected = sessions.identity(request);
        HttpSession session = request.getSession(false);
        if (expected == null || session == null) throw new SessionExpiredException();
        synchronized (session) {
            if (!expected.equals(sessions.identity(request))) throw new SessionExpiredException();
            OrderSubmissionResult result;
            try {
                // The injected service is a separate bean: returning means its transaction committed.
                result = orders.submit(expected, request, parameters);
            } catch (BusinessException failure) {
                if (failure.getStatus() == HttpStatus.CONFLICT) clear(session);
                throw failure;
            } catch (RuntimeException failure) {
                // An uncertain technical outcome must not make the same confirmation replayable.
                clear(session);
                throw failure;
            }
            if (result.isCreated()) {
                try {
                    if (session.getAttribute(SessionSupport.CHECKOUT_CONFIRMATION_ATTRIBUTE)
                            == result.validation().confirmation()) {
                        session.removeAttribute(SessionSupport.CHECKOUT_CONFIRMATION_ATTRIBUTE);
                    }
                } catch (IllegalStateException ended) {
                    // Commit already succeeded; ending a session cannot roll that order back.
                }
            }
            return result;
        }
    }
    private static void clear(HttpSession session) {
        try { session.removeAttribute(SessionSupport.CHECKOUT_CONFIRMATION_ATTRIBUTE); }
        catch (IllegalStateException ended) { /* An ended session has no usable confirmation. */ }
    }
}
