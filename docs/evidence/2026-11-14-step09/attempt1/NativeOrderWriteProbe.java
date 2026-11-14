package org.csucampuscraft.storefront.checkout;

import com.mysql.cj.jdbc.JdbcConnection;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpSession;
import java.lang.reflect.Proxy;
import java.math.BigDecimal;
import java.sql.Connection;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.time.Instant;
import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.Collections;
import java.util.HashMap;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Set;
import javax.sql.DataSource;
import org.apache.ibatis.executor.Executor;
import org.apache.ibatis.mapping.MappedStatement;
import org.apache.ibatis.plugin.Interceptor;
import org.apache.ibatis.plugin.Intercepts;
import org.apache.ibatis.plugin.Invocation;
import org.apache.ibatis.plugin.Signature;
import org.apache.ibatis.session.ResultHandler;
import org.apache.ibatis.session.RowBounds;
import org.apache.ibatis.session.SqlSessionFactory;
import org.csucampuscraft.storefront.auth.AuthUser;
import org.csucampuscraft.storefront.auth.SessionIdentity;
import org.csucampuscraft.storefront.auth.SessionSupport;
import org.csucampuscraft.storefront.foundation.security.ReturnUrlPolicy;
import org.csucampuscraft.storefront.foundation.web.BusinessException;
import org.csucampuscraft.storefront.order.OrderDetail;
import org.csucampuscraft.storefront.order.OrderService;
import org.csucampuscraft.storefront.order.OrderSubmissionCoordinator;
import org.csucampuscraft.storefront.order.OrderSubmissionResult;
import org.csucampuscraft.storefront.order.SalesOrder;
import org.csucampuscraft.storefront.order.SalesOrderItem;
import org.springframework.aop.support.AopUtils;
import org.springframework.boot.SpringApplication;
import org.springframework.context.ConfigurableApplicationContext;
import org.springframework.http.HttpStatus;
import org.springframework.transaction.annotation.Isolation;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.transaction.support.TransactionSynchronizationManager;
import org.springframework.util.LinkedMultiValueMap;
import org.springframework.util.MultiValueMap;

/** External real-Service supplement: one normal private-DB order; no HTTP/fault/concurrency claim. */
public final class NativeOrderWriteProbe {
    private static final List<Map<String,Object>> checks=new ArrayList<>();
    private static final List<Map<String,Object>> sqlEvents=new ArrayList<>();
    private static final List<Map<String,Object>> confirmationRemovals=new ArrayList<>();
    private static boolean recording;
    private static String phase="none";
    private static String createdOrderNo;
    private static DataSource liveDataSource;
    private static Connection observerConnection;

    private static void check(String name,boolean value) {
        checks.add(Map.of("name",name,"passed",value));
        if(!value) throw new AssertionError(name);
    }
    private static Object primitiveDefault(Class<?> type) {
        if(type==boolean.class)return false;
        if(type==int.class)return 0;
        if(type==long.class)return 0L;
        if(type==double.class)return 0D;
        if(type==float.class)return 0F;
        if(type==short.class)return (short)0;
        if(type==byte.class)return (byte)0;
        if(type==char.class)return (char)0;
        return null;
    }
    private static final class RequestState {
        final Map<String,Object> sessionValues=new HashMap<>();
        final Map<String,Object> attributes=new HashMap<>();
        boolean valid=true;
        final HttpSession session;
        final HttpServletRequest request;
        RequestState(long userId,LocalDateTime stamp) {
            sessionValues.put(SessionSupport.IDENTITY_ATTRIBUTE,new SessionIdentity(userId,stamp));
            attributes.put(SessionSupport.CURRENT_USER_ATTRIBUTE,new AuthUser(userId,"native","Native","CUSTOMER"));
            session=(HttpSession)Proxy.newProxyInstance(HttpSession.class.getClassLoader(),new Class<?>[]{HttpSession.class},(p,m,a)->{
                if(m.getName().equals("equals"))return p==a[0];
                if(m.getName().equals("hashCode"))return System.identityHashCode(p);
                if(m.getName().equals("toString"))return "NativeSession[REDACTED]";
                if(!valid)throw new IllegalStateException("Ended native session");
                return switch(m.getName()) {
                    case "getAttribute" -> sessionValues.get((String)a[0]);
                    case "setAttribute" -> {sessionValues.put((String)a[0],a[1]);yield null;}
                    case "removeAttribute" -> {
                        Object previous=sessionValues.remove((String)a[0]);
                        if(SessionSupport.CHECKOUT_CONFIRMATION_ATTRIBUTE.equals(a[0]) && previous!=null) {
                            boolean visible=false;
                            if(createdOrderNo!=null && liveDataSource!=null) {
                                try {visible=countOrder(createdOrderNo)==1;} catch(Exception ignored) { /* Assert captured observation later. */ }
                            }
                            confirmationRemovals.add(Map.of("phase",phase,"transactionActive",TransactionSynchronizationManager.isActualTransactionActive(),"committedOrderVisibleOnSeparateConnection",visible));
                        }
                        yield null;
                    }
                    case "getAttributeNames" -> Collections.enumeration(sessionValues.keySet());
                    case "getCreationTime","getLastAccessedTime" -> Instant.now().toEpochMilli();
                    case "getId" -> "native-session-redacted";
                    case "getMaxInactiveInterval" -> 1800;
                    case "isNew" -> false;
                    case "invalidate" -> {valid=false;sessionValues.clear();yield null;}
                    default -> primitiveDefault(m.getReturnType());
                };
            });
            request=(HttpServletRequest)Proxy.newProxyInstance(HttpServletRequest.class.getClassLoader(),new Class<?>[]{HttpServletRequest.class},(p,m,a)->{
                if(m.getName().equals("equals"))return p==a[0];
                if(m.getName().equals("hashCode"))return System.identityHashCode(p);
                if(m.getName().equals("toString"))return "NativeRequest[REDACTED]";
                return switch(m.getName()) {
                    case "getSession" -> valid ? session : null;
                    case "getAttribute" -> attributes.get((String)a[0]);
                    case "setAttribute" -> {attributes.put((String)a[0],a[1]);yield null;}
                    case "removeAttribute" -> {attributes.remove((String)a[0]);yield null;}
                    case "getAttributeNames" -> Collections.enumeration(attributes.keySet());
                    case "getMethod" -> "POST";
                    case "getRequestURI","getServletPath" -> "/orders";
                    case "getContextPath" -> "";
                    default -> primitiveDefault(m.getReturnType());
                };
            });
        }
    }

    private static MultiValueMap<String,String> form(CheckoutConfirmation confirmation) {
        MultiValueMap<String,String> fields=new LinkedMultiValueMap<>();
        fields.add("confirmationToken",confirmation.token());
        // Deliberately minimal synthetic fixtures, never copied to logs or SQL bind traces.
        fields.add("receiverName","N");fields.add("receiverPhone","1");fields.add("receiverAddress","A");
        return fields;
    }
    private static long countOrder(String number) throws Exception {
        try(PreparedStatement q=observerConnection.prepareStatement("SELECT COUNT(*) FROM sales_order WHERE order_no=?")) {
            q.setString(1,number);try(ResultSet r=q.executeQuery()){r.next();return r.getLong(1);}
        }
    }
    private static long countOwnOrders(long userId) throws Exception {
        try(Connection c=liveDataSource.getConnection();PreparedStatement q=c.prepareStatement("SELECT COUNT(*) FROM sales_order WHERE user_id=?")) {
            q.setLong(1,userId);try(ResultSet r=q.executeQuery()){r.next();return r.getLong(1);}
        }
    }
    private static Map<Long,long[]> productState(List<CheckoutLine> lines) throws Exception {
        Map<Long,long[]> state=new LinkedHashMap<>();
        try(Connection c=liveDataSource.getConnection();PreparedStatement q=c.prepareStatement("SELECT stock,version FROM product WHERE id=?")) {
            for(CheckoutLine line:lines) {
                q.setLong(1,line.productId());try(ResultSet r=q.executeQuery()){check("native-product-exists-"+line.productId(),r.next());state.put(line.productId(),new long[]{r.getLong(1),r.getLong(2)});}
            }
        }
        return state;
    }
    private static Map<String,Object> safeNumbers(Object parameters) {
        Map<String,Object> safe=new LinkedHashMap<>();
        if(parameters instanceof Map<?,?> map) {
            for(String name:List.of("userId","productId","itemId","quantity","version")) {
                if(map.containsKey(name) && map.get(name) instanceof Number number)safe.put(name,number);
            }
            if(map.containsKey("item") && map.get("item") instanceof SalesOrderItem item) {
                safe.put("productId",item.getProductId());safe.put("quantity",item.getQuantity());
            }
        }
        return safe;
    }
    @Intercepts({
        @Signature(type=Executor.class,method="query",args={MappedStatement.class,Object.class,RowBounds.class,ResultHandler.class}),
        @Signature(type=Executor.class,method="update",args={MappedStatement.class,Object.class})
    })
    public static final class WriteTrace implements Interceptor {
        @Override public Object intercept(Invocation call) throws Throwable {
            if(!recording)return call.proceed();
            MappedStatement statement=(MappedStatement)call.getArgs()[0];Object parameters=call.getArgs()[1];
            String sql=statement.getBoundSql(parameters).getSql().replaceAll("\\s+"," ").strip();
            boolean active=TransactionSynchronizationManager.isActualTransactionActive();
            boolean readOnly=TransactionSynchronizationManager.isCurrentTransactionReadOnly();
            Integer isolation=TransactionSynchronizationManager.getCurrentTransactionIsolationLevel();
            Executor executor=(Executor)call.getTarget();Connection connection=executor.getTransaction().getConnection();
            Object result=call.proceed();
            // Cached MySQL connection ID is read without issuing another business SQL statement.
            long connectionId=connection.unwrap(JdbcConnection.class).getId();
            Map<String,Object> event=new LinkedHashMap<>();event.put("phase",phase);event.put("statement",statement.getId());
            event.put("sql",sql);event.put("executorMethod",call.getMethod().getName());event.put("activeTransaction",active);
            event.put("readOnlyTransaction",readOnly);event.put("springIsolation",isolation);event.put("jdbcIsolation",connection.getTransactionIsolation());
            event.put("connectionId",connectionId);event.put("safeNumbers",safeNumbers(parameters));
            if(result instanceof Integer count)event.put("affectedRows",count);
            sqlEvents.add(event);
            if(statement.getId().endsWith(".insertOrder") && parameters instanceof Map<?,?> map && map.containsKey("order") && map.get("order") instanceof SalesOrder order)createdOrderNo=order.getOrderNo();
            return result;
        }
    }
    private static List<Map<String,Object>> events(String name) {return sqlEvents.stream().filter(e->name.equals(e.get("phase"))).toList();}
    private static long number(Map<String,Object> event,String name) {return ((Number)((Map<?,?>)event.get("safeNumbers")).get(name)).longValue();}
    private static void checkTraceStart(String name,List<Map<String,Object>> events) {
        check(name+"-first-mapped-business-SQL-is-operator-FOR-UPDATE",!events.isEmpty() && ((String)events.get(0).get("statement")).endsWith("StoreUserMapper.selectForUpdate") && ((String)events.get(0).get("sql")).toUpperCase(Locale.ROOT).contains("FOR UPDATE"));
        check(name+"-all-statements-write-transaction-RC",events.stream().allMatch(e->Boolean.TRUE.equals(e.get("activeTransaction")) && Boolean.FALSE.equals(e.get("readOnlyTransaction")) && Integer.valueOf(Connection.TRANSACTION_READ_COMMITTED).equals(e.get("springIsolation")) && Integer.valueOf(Connection.TRANSACTION_READ_COMMITTED).equals(e.get("jdbcIsolation"))));
        check(name+"-one-physical-connection",events.stream().map(e->e.get("connectionId")).distinct().count()==1);
    }
    private static void live() throws Exception {
        long userId=Long.parseLong(System.getenv().getOrDefault("STEP09_NATIVE_USER_ID","2"));
        SpringApplication app=new SpringApplication(Class.forName("org.csucampuscraft.storefront.CSUCampusCraftUserApplication"));
        app.setLogStartupInfo(false);
        try(ConfigurableApplicationContext context=app.run("--server.port=0","--server.address=127.0.0.1","--spring.profiles.active=default","--spring.main.banner-mode=off","--logging.level.root=OFF","--mybatis-plus.global-config.banner=false")) {
            liveDataSource=context.getBean(DataSource.class);
            // Retain a distinct physical observer before any business transaction begins.
            try(Connection observer=liveDataSource.getConnection()) {
            observerConnection=observer;
            check("observer-uses-autocommit-read-connection",observer.getAutoCommit());
            LocalDateTime stamp;
            try(Connection c=liveDataSource.getConnection();PreparedStatement q=c.prepareStatement("SELECT updated_at,role,status FROM store_user WHERE id=?")) {
                q.setLong(1,userId);try(ResultSet r=q.executeQuery()){check("native-customer-fixture-exists",r.next());check("native-enabled-customer-fixture","CUSTOMER".equals(r.getString(2)) && "ENABLED".equals(r.getString(3)));stamp=r.getObject(1,LocalDateTime.class);}
            }
            RequestState request=new RequestState(userId,stamp);
            OrderService orders=context.getBean(OrderService.class);
            OrderSubmissionCoordinator coordinator=context.getBean(OrderSubmissionCoordinator.class);
            check("real-Spring-transaction-proxy",AopUtils.isAopProxy(orders));
            Transactional annotation=OrderService.class.getMethod("submit",SessionIdentity.class,HttpServletRequest.class,MultiValueMap.class).getAnnotation(Transactional.class);
            check("real-submit-declares-RC",annotation!=null && annotation.isolation()==Isolation.READ_COMMITTED);
            CheckoutConfirmation confirmation=context.getBean(CheckoutService.class).prepare(request.request);
            check("native-whole-cart-two-lines-three-items-85",confirmation.getItemCount()==2 && confirmation.getQuantity()==3 && confirmation.getTotal().equals(new BigDecimal("85.00")));
            long countBefore=countOwnOrders(userId);Map<Long,long[]> productsBefore=productState(confirmation.getItems());
            context.getBean(SqlSessionFactory.class).getConfiguration().addInterceptor(new WriteTrace());

            phase="fields-400";recording=true;
            MultiValueMap<String,String> invalid=form(confirmation);invalid.set("receiverName","");
            OrderSubmissionResult fields=coordinator.submit(request.request,invalid);recording=false;
            check("fields-result-not-created",!fields.isCreated() && fields.getValidation().fieldErrors().containsKey("receiverName"));
            check("fields-retain-current-confirmation",request.sessionValues.get(SessionSupport.CHECKOUT_CONFIRMATION_ATTRIBUTE)==confirmation);
            check("fields-no-DML",events(phase).stream().noneMatch(e->"update".equals(e.get("executorMethod"))));
            check("fields-no-order-written",countOwnOrders(userId)==countBefore);
            checkTraceStart(phase,events(phase));

            phase="success";recording=true;
            OrderSubmissionResult accepted=coordinator.submit(request.request,form(confirmation));recording=false;
            check("successful-real-order-created",accepted.isCreated() && accepted.getOrderNo()!=null);
            check("safe-unique-order-number-shape",accepted.getOrderNo().matches("[A-Za-z0-9_-]{1,40}"));
            check("real-order-number-is-36-chars",accepted.getOrderNo().length()==36);
            String target="/orders/"+accepted.getOrderNo();
            check("order-detail-target-passes-existing-return-policy",context.getBean(ReturnUrlPolicy.class).resolve(target,"/").equals(target));
            check("real-order-visible-after-proxy-return",countOrder(accepted.getOrderNo())==1 && countOwnOrders(userId)==countBefore+1);
            check("successful-confirmation-consumed",!request.sessionValues.containsKey(SessionSupport.CHECKOUT_CONFIRMATION_ATTRIBUTE));
            check("confirmation-consumed-once-after-commit",confirmationRemovals.size()==1 && Boolean.FALSE.equals(confirmationRemovals.get(0).get("transactionActive")) && Boolean.TRUE.equals(confirmationRemovals.get(0).get("committedOrderVisibleOnSeparateConnection")));
            List<Map<String,Object>> success=events(phase);checkTraceStart(phase,success);
            check("commit-observer-is-distinct-physical-connection",!Long.valueOf(observer.unwrap(JdbcConnection.class).getId()).equals(success.get(0).get("connectionId")));
            List<Map<String,Object>> locks=success.stream().filter(e->((String)e.get("statement")).endsWith(".selectProductForUpdate")).toList();
            List<Long> expectedIds=confirmation.getItems().stream().map(CheckoutLine::productId).sorted().toList();
            check("locks-all-confirmed-products-in-ascending-ID-order",locks.stream().map(e->number(e,"productId")).toList().equals(expectedIds));
            check("all-product-locks-before-first-write",success.indexOf(locks.get(locks.size()-1))<success.indexOf(success.stream().filter(e->"update".equals(e.get("executorMethod"))).findFirst().orElseThrow()));
            check("one-master-order-insert",success.stream().filter(e->((String)e.get("statement")).endsWith(".insertOrder")).count()==1);
            check("two-snapshot-line-inserts",success.stream().filter(e->((String)e.get("statement")).endsWith(".insertItem")).count()==2);
            check("all-write-affected-rows-one",success.stream().filter(e->"update".equals(e.get("executorMethod"))).allMatch(e->Integer.valueOf(1).equals(e.get("affectedRows"))));
            for(CheckoutLine line:confirmation.getItems()) {
                Map<String,Object> deduction=success.stream().filter(e->((String)e.get("statement")).endsWith(".deductProduct") && number(e,"productId")==line.productId()).findFirst().orElseThrow();
                String sql=((String)deduction.get("sql")).toUpperCase(Locale.ROOT).replaceAll("\\s+","");
                check("conditional-stock-version-SQL-"+line.productId(),sql.contains("STOCK=STOCK-?") && sql.contains("VERSION=VERSION+1") && sql.contains("ID=?") && sql.contains("STOCK>=?") && sql.contains("VERSION=?"));
                check("deduction-binds-locked-version-and-confirmed-quantity-"+line.productId(),number(deduction,"quantity")==line.quantity() && number(deduction,"version")==productsBefore.get(line.productId())[1]);
                Map<String,Object> deletion=success.stream().filter(e->((String)e.get("statement")).endsWith(".deleteConfirmedCart") && number(e,"itemId")==line.itemId()).findFirst().orElseThrow();
                String delete=((String)deletion.get("sql")).toUpperCase(Locale.ROOT).replaceAll("\\s+","");
                check("exact-confirmed-cart-delete-SQL-"+line.itemId(),delete.contains("ID=?") && delete.contains("USER_ID=?") && delete.contains("PRODUCT_ID=?") && delete.contains("QUANTITY=?") && delete.contains("VERSION=?"));
                check("exact-confirmed-cart-delete-values-"+line.itemId(),number(deletion,"userId")==userId && number(deletion,"productId")==line.productId() && number(deletion,"quantity")==line.quantity() && number(deletion,"version")==line.itemVersion());
            }
            OrderDetail detail=orders.detail(userId,accepted.getOrderNo());SalesOrder master=detail.getOrder();
            check("master-is-current-user-pending-payment",master.getUserId()==userId && "PENDING_PAYMENT".equals(master.getStatus()));
            check("master-payment-fields-NULL",master.getPaymentMethod()==null && master.getPaymentNo()==null && master.getPaidAt()==null);
            check("master-total-server-85",master.getTotalAmount().equals(new BigDecimal("85.00")));
            check("shipping-snapshot-recorded-without-logging","N".equals(master.getReceiverName()) && "1".equals(master.getReceiverPhone()) && "A".equals(master.getReceiverAddress()));
            check("two-committed-order-lines",detail.getItems().size()==2);
            for(CheckoutLine line:confirmation.getItems()) {
                SalesOrderItem item=detail.getItems().stream().filter(i->i.getProductId()==line.productId()).findFirst().orElseThrow();
                check("committed-line-snapshot-"+line.productId(),item.getQuantity()==line.quantity() && item.getUnitPrice().compareTo(line.unitPrice())==0 && item.getLineAmount().compareTo(line.subtotal())==0 && item.getSkuSnapshot().equals(line.sku()) && item.getProductNameSnapshot().equals(line.name()) && item.getCoverImageSnapshot().equals(line.coverImage()));
            }
            Map<Long,long[]> productsAfter=productState(confirmation.getItems());
            for(CheckoutLine line:confirmation.getItems())check("stock-and-version-increment-exact-"+line.productId(),productsAfter.get(line.productId())[0]==productsBefore.get(line.productId())[0]-line.quantity() && productsAfter.get(line.productId())[1]==productsBefore.get(line.productId())[1]+1);
            try(Connection c=liveDataSource.getConnection();PreparedStatement q=c.prepareStatement("SELECT COUNT(*) FROM cart_item WHERE user_id=?")) {
                q.setLong(1,userId);try(ResultSet r=q.executeQuery()){r.next();check("only-confirmed-native-whole-cart-cleared",r.getLong(1)==0);}
            }

            phase="replay";recording=true;
            try {coordinator.submit(request.request,form(confirmation));check("consumed-confirmation-replay-refused",false);}
            catch(BusinessException conflict){check("consumed-confirmation-replay-refused",conflict.getStatus()==HttpStatus.CONFLICT);}
            finally {recording=false;}
            checkTraceStart(phase,events(phase));
            check("replay-no-DML",events(phase).stream().noneMatch(e->"update".equals(e.get("executorMethod"))));
            check("replay-no-second-order",countOwnOrders(userId)==countBefore+1 && countOrder(accepted.getOrderNo())==1);
            Map<Long,long[]> afterReplay=productState(confirmation.getItems());
            check("replay-no-second-stock-or-version-change",expectedIds.stream().allMatch(id->java.util.Arrays.equals(productsAfter.get(id),afterReplay.get(id))));
            check("safe-result-toString",!accepted.toString().contains(confirmation.token()) && master.toString().equals("SalesOrder[receiver=REDACTED]"));
            }
            observerConnection=null;
        }
    }
    public static void main(String[] args) throws Exception {
        boolean complete=false;String failureClass=null;
        try {if(!List.of(args).contains("--live"))throw new IllegalArgumentException("Use --live with the verifier's private database fixture");live();complete=true;}
        catch(Throwable failure){failureClass=failure.getClass().getName();}
        Map<String,Object> result=new LinkedHashMap<>();
        result.put("overall",complete?"PASS":"FAIL");result.put("checks",checks.size());result.put("checksPassed",checks.stream().filter(c->Boolean.TRUE.equals(c.get("passed"))).count());
        result.put("scope","Actual private-DB Service transaction for one native order, field validation and sequential replay; no HTTP/concurrency/fault-injection claim");
        result.put("orderNo",createdOrderNo);result.put("details",checks);result.put("sqlEvents",sqlEvents);result.put("confirmationRemovalObservations",confirmationRemovals);result.put("failureClass",failureClass);result.put("secretsRecorded",false);
        System.out.println(new com.fasterxml.jackson.databind.ObjectMapper().writeValueAsString(result));
        if(!complete)System.exit(1);
    }
}
