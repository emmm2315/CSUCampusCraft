import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpSession;
import java.lang.reflect.Proxy;
import java.time.LocalDateTime;
import java.util.HashMap;
import java.util.Map;
import org.csucampuscraft.storefront.auth.AuthUser;
import org.csucampuscraft.storefront.auth.SessionExpiredException;
import org.csucampuscraft.storefront.auth.SessionIdentity;
import org.csucampuscraft.storefront.auth.SessionSupport;
import org.csucampuscraft.storefront.cart.CartService;
import org.csucampuscraft.storefront.foundation.security.CsrfTokenService;
import org.csucampuscraft.storefront.foundation.web.BusinessException;
import org.csucampuscraft.storefront.foundation.web.GlobalExceptionHandler;
import org.csucampuscraft.storefront.foundation.web.PageModelAdvice;
import org.springframework.dao.DataAccessResourceFailureException;
import org.springframework.http.HttpStatus;
import org.springframework.transaction.CannotCreateTransactionException;
import org.springframework.transaction.UnexpectedRollbackException;
import org.springframework.web.servlet.ModelAndView;
import org.springframework.web.servlet.view.RedirectView;

/** Temporary direct probe of the actual amended model/error-handler classes. */
public class ModelProbe {
    static int passed;
    static void check(String name, boolean valid) {
        if (!valid) throw new AssertionError(name);
        passed++;
        System.out.println("PASS " + name);
    }

    static final class RequestState {
        final Map<String,Object> request = new HashMap<>();
        final Map<String,Object> session = new HashMap<>();
        int created;
        final HttpSession sessionProxy = (HttpSession) Proxy.newProxyInstance(
                ModelProbe.class.getClassLoader(), new Class<?>[]{HttpSession.class}, (proxy, method, args) -> {
                    return switch (method.getName()) {
                        case "getAttribute" -> session.get((String) args[0]);
                        case "setAttribute" -> { session.put((String)args[0],args[1]); yield null; }
                        case "removeAttribute" -> { session.remove((String)args[0]); yield null; }
                        case "getId" -> "temporary-model-probe";
                        case "isNew" -> false;
                        case "toString" -> "ModelProbeSession";
                        case "hashCode" -> System.identityHashCode(proxy);
                        case "equals" -> proxy == args[0];
                        default -> primitiveDefault(method.getReturnType());
                    };
                });
        final HttpServletRequest proxy = (HttpServletRequest) Proxy.newProxyInstance(
                ModelProbe.class.getClassLoader(), new Class<?>[]{HttpServletRequest.class}, (proxy, method, args) -> {
                    return switch (method.getName()) {
                        case "getAttribute" -> request.get((String)args[0]);
                        case "setAttribute" -> { request.put((String)args[0],args[1]); yield null; }
                        case "removeAttribute" -> { request.remove((String)args[0]); yield null; }
                        case "getMethod" -> "POST";
                        case "getContextPath" -> "";
                        case "getServletPath", "getRequestURI" -> "/cart/items";
                        case "getSession" -> {
                            if (args == null || args.length == 0 || Boolean.TRUE.equals(args[0])) created++;
                            yield sessionProxy;
                        }
                        case "toString" -> "ModelProbeRequest";
                        case "hashCode" -> System.identityHashCode(proxy);
                        case "equals" -> proxy == args[0];
                        default -> primitiveDefault(method.getReturnType());
                    };
                });
        RequestState() {
            request.put(SessionSupport.CURRENT_USER_ATTRIBUTE,new AuthUser(1L,"probe","probe","CUSTOMER"));
            session.put(CsrfTokenService.class.getName()+".TOKEN", "a".repeat(64));
        }
    }

    static Object primitiveDefault(Class<?> type) {
        if (!type.isPrimitive() || type == void.class) return null;
        if (type == boolean.class) return false;
        if (type == long.class) return 0L;
        if (type == double.class) return 0.0;
        if (type == float.class) return 0.0f;
        if (type == short.class) return (short)0;
        if (type == byte.class) return (byte)0;
        if (type == char.class) return '\0';
        return 0;
    }

    public static void main(String[] args) throws Exception {
        for (RuntimeException unavailable : new RuntimeException[]{
                new DataAccessResourceFailureException("temporary query failure"),
                new CannotCreateTransactionException("temporary transaction begin failure"),
                new UnexpectedRollbackException("temporary read transaction completion failure")}) {
            RequestState state = new RequestState();
            CartService broken = new CartService(null,null) {
                @Override public long quantity(long userId) { throw unavailable; }
            };
            PageModelAdvice models = new PageModelAdvice(new CsrfTokenService(),broken);
            Map<String,Object> values = models.commonModel(state.proxy);
            String kind = unavailable.getClass().getSimpleName();
            check(kind+" renders unavailable badge", Boolean.FALSE.equals(values.get("cartQuantityAvailable"))
                    && values.get("cartQuantity") == null);
            check(kind+" preserves safe identity", values.get("currentUser") instanceof AuthUser);
            GlobalExceptionHandler errors = new GlobalExceptionHandler(models,new SessionSupport());
            ModelAndView page = errors.unexpected(unavailable,state.proxy,null);
            check(kind+" renders safe 500 without repeated failure", "error/500".equals(page.getViewName())
                    && page.getStatus() == HttpStatus.INTERNAL_SERVER_ERROR
                    && Boolean.FALSE.equals(page.getModel().get("cartQuantityAvailable")));
            check(kind+" does not create POST session", state.created == 0);
        }
        RequestState state = new RequestState();
        PageModelAdvice models = new PageModelAdvice(new CsrfTokenService(), new CartService(null,null) {
            @Override public long quantity(long userId) { throw new AssertionError("Guest badge queried cart"); }
        });
        state.request.remove(SessionSupport.CURRENT_USER_ATTRIBUTE);
        Map<String,Object> guest = models.commonModel(state.proxy);
        check("guest badge is zero without cart query", Long.valueOf(0).equals(guest.get("cartQuantity")));

        state = new RequestState();
        state.session.put(SessionSupport.IDENTITY_ATTRIBUTE,new SessionIdentity(1L,LocalDateTime.of(2026,11,14,0,0)));
        state.session.put(SessionSupport.CHECKOUT_CONFIRMATION_ATTRIBUTE,"temporary-confirmation");
        PageModelAdvice safeModels = new PageModelAdvice(new CsrfTokenService(),new CartService(null,null) {
            @Override public long quantity(long userId) { return 5; }
        });
        GlobalExceptionHandler errors = new GlobalExceptionHandler(safeModels,new SessionSupport());
        ModelAndView redirect = errors.expired(new SessionExpiredException(),state.proxy);
        check("expired identity redirects to safe cart GET", redirect.getView() instanceof RedirectView
                && "/login?returnUrl=%2Fcart".equals(((RedirectView)redirect.getView()).getUrl()));
        check("expired identity and confirmation are cleared", !state.session.containsKey(SessionSupport.IDENTITY_ATTRIBUTE)
                && !state.session.containsKey(SessionSupport.CHECKOUT_CONFIRMATION_ATTRIBUTE)
                && !state.request.containsKey(SessionSupport.CURRENT_USER_ATTRIBUTE));
        check("expired identity preserves CSRF", state.session.containsKey(CsrfTokenService.class.getName()+".TOKEN"));
        check("expired POST does not create a session", state.created == 0);
        ModelAndView safeError = errors.business(new BusinessException(HttpStatus.INTERNAL_SERVER_ERROR,
                "PRIVATE_MARKER","private-marker-must-never-render"),state.proxy);
        check("500 BusinessException message is sanitized", "INTERNAL_ERROR".equals(safeError.getModel().get("errorCode"))
                && !safeError.getModel().toString().contains("private-marker"));
        System.out.println("MODEL_PROBE_PASSED="+passed);
    }
}
