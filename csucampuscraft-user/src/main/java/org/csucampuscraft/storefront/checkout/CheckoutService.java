package org.csucampuscraft.storefront.checkout;

import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpSession;
import java.math.BigDecimal;
import java.math.RoundingMode;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.SecureRandom;
import java.time.Clock;
import java.time.Duration;
import java.time.Instant;
import java.util.ArrayList;
import java.util.Base64;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import org.csucampuscraft.storefront.auth.AuthUser;
import org.csucampuscraft.storefront.auth.SessionExpiredException;
import org.csucampuscraft.storefront.auth.SessionIdentity;
import org.csucampuscraft.storefront.auth.SessionSupport;
import org.csucampuscraft.storefront.cart.CartLine;
import org.csucampuscraft.storefront.cart.CartPage;
import org.csucampuscraft.storefront.cart.CartService;
import org.csucampuscraft.storefront.foundation.validation.InputChecks;
import org.csucampuscraft.storefront.foundation.web.BusinessException;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.util.MultiValueMap;

/** Session confirmation only. Every database call is an ordinary read; STEP09 owns writes. */
@Service
public final class CheckoutService {
    private static final SecureRandom RANDOM = new SecureRandom();
    private static final BigDecimal ZERO = new BigDecimal("0.00");
    private final CartService carts;
    private final SessionSupport sessions;
    private final Duration ttl;
    private final Clock clock;

    @Autowired
    public CheckoutService(CartService carts, SessionSupport sessions,
            @Value("${csucampuscraft.checkout.confirmation-ttl:PT10M}") String configuredTtl) {
        this(carts, sessions, Duration.parse(configuredTtl), Clock.systemUTC());
    }

    CheckoutService(CartService carts, SessionSupport sessions, Duration ttl, Clock clock) {
        if (ttl == null || ttl.isZero() || ttl.isNegative()) {
            throw new IllegalArgumentException("Checkout confirmation TTL must be positive");
        }
        clock.instant().plus(ttl); // Reject an unrepresentable server configuration at startup.
        this.carts = carts;
        this.sessions = sessions;
        this.ttl = ttl;
        this.clock = clock;
    }

    public CheckoutConfirmation prepare(HttpServletRequest request) {
        SessionIdentity expected = actor(request);
        HttpSession session = session(request);
        try {
            synchronized (session) {
                SessionIdentity actor = actor(request);
                if (!actor.equals(expected)) throw new SessionExpiredException();
                // A failed new attempt must never leave an older usable confirmation behind.
                session.removeAttribute(SessionSupport.CHECKOUT_CONFIRMATION_ATTRIBUTE);
                CartValues values = currentCart(actor.userId());
                Instant createdAt = clock.instant();
                byte[] entropy = new byte[32];
                RANDOM.nextBytes(entropy);
                String token = Base64.getUrlEncoder().withoutPadding().encodeToString(entropy);
                CheckoutConfirmation confirmation = new CheckoutConfirmation(token, createdAt,
                        createdAt.plus(ttl), actor.userId(), values.items(), values.total());
                session.setAttribute(SessionSupport.CHECKOUT_CONFIRMATION_ATTRIBUTE, confirmation);
                return confirmation;
            }
        } catch (IllegalStateException expiredSession) {
            throw sessionFailure(session, expiredSession);
        }
    }

    /** Ordered validation: current token -> current complete cart -> shipping fields. */
    public Validation validate(HttpServletRequest request, MultiValueMap<String, String> parameters) {
        SessionIdentity expected = actor(request);
        HttpSession session = session(request);
        try {
            synchronized (session) {
                SessionIdentity actor = actor(request);
                if (!actor.equals(expected)) throw new SessionExpiredException();
                CheckoutConfirmation confirmation;
                try {
                    Object stored = session.getAttribute(SessionSupport.CHECKOUT_CONFIRMATION_ATTRIBUTE);
                    if (!(stored instanceof CheckoutConfirmation candidate)
                            || candidate.getUserId() != actor.userId()) {
                        throw conflict("CHECKOUT_CONFIRMATION_INVALID", "确认已失效，请重新进入结算。");
                    }
                    confirmation = candidate;
                    requireUnexpired(confirmation);
                    List<String> tokens = parameters.get("confirmationToken");
                    String submitted = tokens == null || tokens.size() != 1 ? null : tokens.get(0);
                    if (submitted == null || !submitted.matches("[A-Za-z0-9_-]{43}")
                            || !MessageDigest.isEqual(confirmation.token().getBytes(StandardCharsets.UTF_8),
                                    submitted.getBytes(StandardCharsets.UTF_8))) {
                        throw conflict("CHECKOUT_CONFIRMATION_INVALID",
                                "确认已过期、被替换或不属于当前会话，请重新进入结算。");
                    }
                    CartValues current = currentCart(actor.userId());
                    if (!matches(confirmation, current)) {
                        throw conflict("CHECKOUT_CART_CHANGED", "购物车或商品价格已变化，请重新确认整车。");
                    }
                    requireUnexpired(confirmation);
                } catch (BusinessException conflict) {
                    // Includes stale/foreign tokens: end this session's current confirmation conservatively.
                    session.removeAttribute(SessionSupport.CHECKOUT_CONFIRMATION_ATTRIBUTE);
                    throw conflict;
                }

                ShippingForm raw = new ShippingForm(first(parameters, "receiverName"),
                        first(parameters, "receiverPhone"), first(parameters, "receiverAddress"));
                Map<String, String> errors = new LinkedHashMap<>();
                String name = field(parameters, "receiverName", raw.receiverName(), 50, errors);
                String phone = field(parameters, "receiverPhone", raw.receiverPhone(), 30, errors);
                String address = field(parameters, "receiverAddress", raw.receiverAddress(), 255, errors);
                try {
                    requireUnexpired(confirmation);
                } catch (BusinessException expired) {
                    session.removeAttribute(SessionSupport.CHECKOUT_CONFIRMATION_ATTRIBUTE);
                    throw expired;
                }
                ShippingForm redisplay = errors.isEmpty() ? new ShippingForm(name, phone, address) : raw;
                return new Validation(confirmation, redisplay, errors);
            }
        } catch (IllegalStateException expiredSession) {
            throw sessionFailure(session, expiredSession);
        }
    }

    /** Recheck after product lock waits and immediately before the first order write. No SQL. */
    public void requireCurrent(HttpServletRequest request, CheckoutConfirmation expected) {
        HttpSession session = session(request);
        try {
            synchronized (session) {
                SessionIdentity current = actor(request);
                if (expected == null || expected.getUserId() != current.userId()
                        || session.getAttribute(SessionSupport.CHECKOUT_CONFIRMATION_ATTRIBUTE) != expected) {
                    throw conflict("CHECKOUT_CONFIRMATION_INVALID", "确认已失效，请重新进入结算。");
                }
                requireUnexpired(expected);
            }
        } catch (IllegalStateException expiredSession) {
            throw sessionFailure(session, expiredSession);
        }
    }

    private CartValues currentCart(long userId) {
        CartPage cart = carts.read(userId);
        if (cart.isEmpty()) {
            throw conflict("CHECKOUT_CART_EMPTY", "购物车为空，请先选购商品后再结算。");
        }
        if (!cart.isAllValid()) {
            throw conflict("CHECKOUT_CART_INVALID", "购物车包含下架、售罄或超库存条目，请返回购物车处理。");
        }
        List<CheckoutLine> lines = new ArrayList<>();
        BigDecimal total = ZERO;
        for (CartLine line : cart.items()) {
            BigDecimal unitPrice = amount(line.getPrice());
            BigDecimal subtotal = amount(unitPrice.multiply(BigDecimal.valueOf(line.getQuantity())));
            total = amount(total.add(subtotal));
            lines.add(new CheckoutLine(line.getId(), line.getProductId(), line.getQuantity(),
                    line.getVersion(), unitPrice, subtotal, line.getSku(), line.getName(), line.getCoverImage()));
        }
        return new CartValues(List.copyOf(lines), total);
    }

    private static BigDecimal amount(BigDecimal value) {
        try {
            if (value == null || value.signum() <= 0 || value.compareTo(InputChecks.MAX_MONEY) > 0) {
                throw new ArithmeticException();
            }
            return value.setScale(2, RoundingMode.UNNECESSARY);
        } catch (ArithmeticException invalid) {
            throw conflict("CHECKOUT_AMOUNT_OUT_OF_RANGE", "商品小计或整车金额超过允许范围，请返回购物车调整。");
        }
    }

    private static boolean matches(CheckoutConfirmation confirmation, CartValues current) {
        List<CheckoutLine> expected = confirmation.getItems();
        if (expected.size() != current.items().size()
                || confirmation.getTotal().compareTo(current.total()) != 0) return false;
        // CartService reads the complete own cart in id order using one joined SELECT.
        for (int index = 0; index < expected.size(); index++) {
            CheckoutLine previous = expected.get(index);
            CheckoutLine now = current.items().get(index);
            if (previous.itemId() != now.itemId() || previous.productId() != now.productId()
                    || previous.quantity() != now.quantity() || previous.itemVersion() != now.itemVersion()
                    || previous.unitPrice().compareTo(now.unitPrice()) != 0) return false;
        }
        return true;
    }

    private void requireUnexpired(CheckoutConfirmation confirmation) {
        if (!clock.instant().isBefore(confirmation.getExpiresAt())) {
            throw conflict("CHECKOUT_CONFIRMATION_EXPIRED", "确认已过期，请重新进入结算。");
        }
    }

    private SessionIdentity actor(HttpServletRequest request) {
        SessionIdentity identity = sessions.identity(request);
        AuthUser user = sessions.currentUser(request);
        if (identity == null || user == null || !"CUSTOMER".equals(user.role())
                || !identity.userId().equals(user.userId())) throw new SessionExpiredException();
        return identity;
    }

    private static HttpSession session(HttpServletRequest request) {
        HttpSession session = request.getSession(false);
        if (session == null) throw new SessionExpiredException();
        return session;
    }

    private static RuntimeException sessionFailure(HttpSession session, IllegalStateException failure) {
        try {
            session.getCreationTime();
            // Keep an unrelated technical IllegalStateException on the ordinary generic-500 path.
            return failure;
        } catch (IllegalStateException expired) {
            return new SessionExpiredException();
        }
    }

    private static String field(MultiValueMap<String, String> parameters, String name, String raw,
                                int maximum, Map<String, String> errors) {
        List<String> values = parameters.get(name);
        if (values != null && values.size() != 1) {
            errors.put(name, "此字段只能提交一个值。");
            return "";
        }
        try {
            return InputChecks.requiredText(name, raw, maximum);
        } catch (BusinessException invalid) {
            errors.put(name, "去除首尾空白后须为 1–" + maximum + " 个字符。");
            return "";
        }
    }

    private static String first(MultiValueMap<String, String> parameters, String field) {
        List<String> values = parameters.get(field);
        return values == null || values.isEmpty() ? null : values.get(0);
    }

    private static BusinessException conflict(String code, String message) {
        return new BusinessException(HttpStatus.CONFLICT, code, message);
    }

    private record CartValues(List<CheckoutLine> items, BigDecimal total) { }

    /** Request-scoped result; a valid result is deliberately not an order. */
    public record Validation(CheckoutConfirmation confirmation, ShippingForm form,
                             Map<String, String> fieldErrors) {
        public Validation { fieldErrors = Map.copyOf(fieldErrors); }
        public boolean isValid() { return fieldErrors.isEmpty(); }
        @Override public String toString() { return "CheckoutValidation[REDACTED]"; }
    }
}
