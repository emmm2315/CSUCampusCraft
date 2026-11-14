package org.csucampuscraft.storefront.checkout;

import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpSession;
import java.lang.reflect.Proxy;
import java.lang.reflect.Field;
import java.math.BigDecimal;
import java.time.Clock;
import java.time.Duration;
import java.time.Instant;
import java.time.LocalDateTime;
import java.time.ZoneOffset;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import org.csucampuscraft.storefront.auth.AuthUser;
import org.csucampuscraft.storefront.auth.SessionIdentity;
import org.csucampuscraft.storefront.auth.SessionSupport;
import org.csucampuscraft.storefront.cart.CartLine;
import org.csucampuscraft.storefront.cart.CartPage;
import org.csucampuscraft.storefront.cart.CartService;
import org.csucampuscraft.storefront.foundation.validation.InputChecks;
import org.csucampuscraft.storefront.foundation.web.BusinessException;
import org.springframework.http.HttpStatus;

/** Controlled actual-class amount boundaries. No application context, DB, HTTP or business writes. */
public final class CheckoutAmountProbe {
    private static final List<Map<String,Object>> checks=new ArrayList<>();
    private static void check(String name,boolean value) {checks.add(Map.of("name",name,"passed",value));if(!value)throw new AssertionError(name);}
    private static Object value(Class<?> type) {
        if(type==boolean.class)return false;if(type==int.class)return 0;if(type==long.class)return 0L;
        return null;
    }
    private static final class RequestState {
        final Map<String,Object> sessionValues=new HashMap<>();
        final Map<String,Object> attributes=new HashMap<>();
        final HttpSession session;
        final HttpServletRequest request;
        RequestState() {
            sessionValues.put(SessionSupport.IDENTITY_ATTRIBUTE,new SessionIdentity(1L,LocalDateTime.of(2026,11,14,0,0)));
            attributes.put(SessionSupport.CURRENT_USER_ATTRIBUTE,new AuthUser(1L,"controlled","Controlled","CUSTOMER"));
            session=(HttpSession)Proxy.newProxyInstance(HttpSession.class.getClassLoader(),new Class<?>[]{HttpSession.class},(p,m,a)->{
                if(m.getName().equals("equals"))return p==a[0];if(m.getName().equals("hashCode"))return System.identityHashCode(p);
                return switch(m.getName()) {
                    case "getAttribute"->sessionValues.get((String)a[0]);
                    case "setAttribute"->{sessionValues.put((String)a[0],a[1]);yield null;}
                    case "removeAttribute"->{sessionValues.remove((String)a[0]);yield null;}
                    case "getCreationTime"->0L;
                    case "toString"->"ControlledSession[REDACTED]";
                    default->value(m.getReturnType());
                };
            });
            request=(HttpServletRequest)Proxy.newProxyInstance(HttpServletRequest.class.getClassLoader(),new Class<?>[]{HttpServletRequest.class},(p,m,a)->{
                if(m.getName().equals("equals"))return p==a[0];if(m.getName().equals("hashCode"))return System.identityHashCode(p);
                return switch(m.getName()) {
                    case "getSession"->session;
                    case "getAttribute"->attributes.get((String)a[0]);
                    case "removeAttribute"->{attributes.remove((String)a[0]);yield null;}
                    case "setAttribute"->{attributes.put((String)a[0],a[1]);yield null;}
                    case "toString"->"ControlledRequest[REDACTED]";
                    default->value(m.getReturnType());
                };
            });
        }
    }
    private static final class FakeCartService extends CartService {
        final CartPage cart;
        int readCalls;
        FakeCartService(List<CartLine> lines) {
            super(null,null);
            cart=new CartPage(lines,lines.stream().mapToLong(CartLine::getQuantity).sum(),
                    lines.stream().map(CartLine::getSubtotal).reduce(new BigDecimal("0.00"),BigDecimal::add),0);
        }
        @Override public CartPage read(long userId) {readCalls++;return cart;}
    }
    private static void field(CartLine target,String name,Object value) throws Exception {
        Field field=CartLine.class.getDeclaredField(name);field.setAccessible(true);field.set(target,value);
    }
    private static CartLine line(long id,String price) throws Exception {
        CartLine line=new CartLine();
        field(line,"id",id);field(line,"productId",id);field(line,"quantity",1);field(line,"version",0L);
        field(line,"sku","CONTROLLED-"+id);field(line,"name","Controlled item");field(line,"coverImage","images/catalog-placeholder.svg");
        field(line,"price",new BigDecimal(price));field(line,"stock",1);field(line,"status","ON_SALE");
        return line;
    }
    private static CheckoutService service(FakeCartService carts) {
        return new CheckoutService(carts,new SessionSupport(),Duration.ofMinutes(10),Clock.fixed(Instant.parse("2026-11-14T00:00:00Z"),ZoneOffset.UTC));
    }
    private static void controlled() throws Exception {
        CartLine first=line(1,"6000000000.00");CartLine second=line(2,"6000000000.00");
        check("first-line-valid-stock-one",first.isValid() && first.getQuantity()==1);
        check("second-line-valid-stock-one",second.isValid() && second.getQuantity()==1);
        check("first-line-subtotal-six-billion-within-DECIMAL",first.getSubtotal().equals(new BigDecimal("6000000000.00")) && first.getSubtotal().compareTo(InputChecks.MAX_MONEY)<0);
        check("second-line-subtotal-six-billion-within-DECIMAL",second.getSubtotal().equals(new BigDecimal("6000000000.00")) && second.getSubtotal().compareTo(InputChecks.MAX_MONEY)<0);
        FakeCartService sumCart=new FakeCartService(List.of(first,second));RequestState sumRequest=new RequestState();
        sumRequest.sessionValues.put(SessionSupport.CHECKOUT_CONFIRMATION_ATTRIBUTE,"old-controlled-confirmation");
        check("aggregate-only-total-twelve-billion-exceeds-DECIMAL",sumCart.cart.getValidSubtotal().equals(new BigDecimal("12000000000.00")) && sumCart.cart.getValidSubtotal().compareTo(InputChecks.MAX_MONEY)>0);
        try {service(sumCart).prepare(sumRequest.request);check("aggregate-only-overflow-409-code",false);}
        catch(BusinessException invalid) {check("aggregate-only-overflow-409-code",invalid.getStatus()==HttpStatus.CONFLICT && invalid.getCode().equals("CHECKOUT_AMOUNT_OUT_OF_RANGE"));}
        check("aggregate-overflow-removes-old-confirmation",!sumRequest.sessionValues.containsKey(SessionSupport.CHECKOUT_CONFIRMATION_ATTRIBUTE));
        check("aggregate-controlled-cart-read-once",sumCart.readCalls==1);
        check("aggregate-retains-input-quantities",first.getQuantity()==1 && second.getQuantity()==1 && first.getVersion()==0 && second.getVersion()==0);

        FakeCartService maxCart=new FakeCartService(List.of(line(3,"9999999999.99")));RequestState maxRequest=new RequestState();
        CheckoutConfirmation maximum=service(maxCart).prepare(maxRequest.request);
        check("maximum-single-line-amount-accepted",maximum.getTotal().equals(InputChecks.MAX_MONEY));
        check("maximum-subtotal-accepted-with-scale-two",maximum.getItems().get(0).subtotal().equals(InputChecks.MAX_MONEY) && maximum.getTotal().scale()==2);
        check("maximum-confirmation-stored",maxRequest.sessionValues.get(SessionSupport.CHECKOUT_CONFIRMATION_ATTRIBUTE)==maximum);
        check("maximum-controlled-cart-read-once",maxCart.readCalls==1);
    }
    public static void main(String[] args) throws Exception {
        boolean complete=false;String failureClass=null;
        try {controlled();complete=true;}catch(Throwable failure){failureClass=failure.getClass().getName();}
        Map<String,Object> report=new java.util.LinkedHashMap<>();report.put("overall",complete?"PASS":"FAIL");
        report.put("scope","Controlled actual fixed-JAR CheckoutService.prepare with fake read-only CartService; no application startup, live DB, HTTP, order transaction, concurrency or fault-injection claim");
        report.put("checks",checks.size());report.put("checksPassed",checks.stream().filter(x->Boolean.TRUE.equals(x.get("passed"))).count());report.put("details",checks);
        report.put("fixture",Map.of("sumOnly",Map.of("unitPrice","6000000000.00","quantityEach",1,"lines",2,"total","12000000000.00"),"maximumSingle","9999999999.99"));
        report.put("dbConnectionsOpened",0);report.put("orderWrites",0);report.put("rawTokensOrShippingRecorded",false);report.put("failureClass",failureClass);
        System.out.println(new com.fasterxml.jackson.databind.ObjectMapper().writeValueAsString(report));if(!complete)System.exit(1);
    }
}
