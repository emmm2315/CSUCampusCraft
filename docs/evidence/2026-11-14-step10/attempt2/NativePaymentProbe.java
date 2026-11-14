package org.csucampuscraft.storefront.payment;

import com.mysql.cj.jdbc.JdbcConnection;
import java.math.BigDecimal;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.sql.Connection;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.sql.ResultSetMetaData;
import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.HexFormat;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.List;
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
import org.csucampuscraft.storefront.auth.SessionIdentity;
import org.csucampuscraft.storefront.foundation.web.BusinessException;
import org.springframework.aop.support.AopUtils;
import org.springframework.boot.SpringApplication;
import org.springframework.context.ConfigurableApplicationContext;
import org.springframework.http.HttpStatus;
import org.springframework.transaction.annotation.Isolation;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.transaction.support.TransactionSynchronization;
import org.springframework.transaction.support.TransactionSynchronizationManager;
import org.springframework.util.LinkedMultiValueMap;
import org.springframework.util.MultiValueMap;

/** External actual-Service probe only. It creates no orders, threads, fault hooks or business routes. */
public final class NativePaymentProbe {
    private static final List<Map<String,Object>> checks = new ArrayList<>();
    private static final List<Map<String,Object>> sqlEvents = new ArrayList<>();
    private static final List<Map<String,Object>> completions = new ArrayList<>();
    private static final Set<String> registered = new LinkedHashSet<>();
    private static String phase = "setup";

    private static void check(String name, boolean passed) {
        checks.add(Map.of("name",name,"passed",passed));
        if (!passed) throw new AssertionError(name);
    }
    private static MultiValueMap<String,String> result(String value) {
        MultiValueMap<String,String> parameters = new LinkedMultiValueMap<>();
        parameters.add("result",value); return parameters;
    }
    private static Map<String,Object> safeNumbers(Object value) {
        Map<String,Object> found = new LinkedHashMap<>();
        if (value instanceof Map<?,?> map) {
            for (String key : List.of("userId","orderId","productId","quantity","version")) {
                if (map.containsKey(key) && map.get(key) instanceof Number number) found.put(key,number);
            }
        }
        return found;
    }
    @Intercepts({
        @Signature(type=Executor.class,method="query",args={MappedStatement.class,Object.class,RowBounds.class,ResultHandler.class}),
        @Signature(type=Executor.class,method="update",args={MappedStatement.class,Object.class})
    })
    public static final class Trace implements Interceptor {
        @Override public Object intercept(Invocation call) throws Throwable {
            MappedStatement mapped=(MappedStatement)call.getArgs()[0];
            Object parameters=call.getArgs()[1];
            Connection connection=((Executor)call.getTarget()).getTransaction().getConnection();
            boolean active=TransactionSynchronizationManager.isActualTransactionActive();
            if (active && registered.add(phase)) {
                String captured=phase;
                TransactionSynchronizationManager.registerSynchronization(new TransactionSynchronization() {
                    @Override public void afterCompletion(int status) {
                        completions.add(Map.of("phase",captured,"status",status));
                    }
                });
            }
            Map<String,Object> event=new LinkedHashMap<>();
            event.put("phase",phase);event.put("statement",mapped.getId());
            event.put("sql",mapped.getBoundSql(parameters).getSql().replaceAll("\\s+"," ").strip());
            event.put("method",call.getMethod().getName());event.put("activeTransaction",active);
            event.put("readOnly",TransactionSynchronizationManager.isCurrentTransactionReadOnly());
            event.put("springIsolation",TransactionSynchronizationManager.getCurrentTransactionIsolationLevel());
            event.put("jdbcIsolation",connection.getTransactionIsolation());
            // MySQL's cached connection id is read without issuing an extra SQL query.
            event.put("connectionId",connection.unwrap(JdbcConnection.class).getId());
            event.put("safeNumbers",safeNumbers(parameters));sqlEvents.add(event);
            Object returned=call.proceed();
            if (returned instanceof Number number) event.put("affectedRows",number);
            return returned;
        }
    }
    private static List<Map<String,Object>> events(String selected) {
        return sqlEvents.stream().filter(e->selected.equals(e.get("phase"))).toList();
    }
    private static long number(Map<String,Object> event,String key) {
        return ((Number)((Map<?,?>)event.get("safeNumbers")).get(key)).longValue();
    }
    private static void structural() {
        org.apache.ibatis.binding.MapperMethod.ParamMap<Object> userOnly=new org.apache.ibatis.binding.MapperMethod.ParamMap<>();
        userOnly.put("userId",2L);userOnly.put("param1",2L);
        check("ParamMap-fixture-really-misses-optional-keys",!userOnly.containsKey("quantity") && !userOnly.containsKey("version") && !userOnly.containsKey("orderId"));
        check("ParamMap-user-lock-whitelist-does-not-read-missing-keys",safeNumbers(userOnly).equals(Map.of("userId",2L)));
        check("ParamMap-input-is-not-mutated",userOnly.size()==2 && userOnly.containsKey("param1"));
        org.apache.ibatis.binding.MapperMethod.ParamMap<Object> mixed=new org.apache.ibatis.binding.MapperMethod.ParamMap<>();
        mixed.put("userId",2L);mixed.put("orderId",77L);mixed.put("productId",101L);mixed.put("quantity",2);mixed.put("version",3L);
        mixed.put("receiverName","synthetic-not-recorded");mixed.put("confirmationToken","synthetic-not-recorded");
        check("ParamMap-known-numeric-values-retained",safeNumbers(mixed).equals(Map.of("userId",2L,"orderId",77L,"productId",101L,"quantity",2,"version",3L)));
        check("ParamMap-sensitive-and-nonwhitelist-values-excluded",!safeNumbers(mixed).containsKey("receiverName") && !safeNumbers(mixed).containsKey("confirmationToken"));
        mixed.put("quantity","2");mixed.put("version",null);
        check("ParamMap-nonnumeric-and-null-values-excluded",!safeNumbers(mixed).containsKey("quantity") && !safeNumbers(mixed).containsKey("version"));
        check("non-map-and-null-parameters-safe",safeNumbers(2L).isEmpty() && safeNumbers(null).isEmpty());
        check("diagnostic-output-is-ordinary-map",!(safeNumbers(userOnly) instanceof org.apache.ibatis.binding.MapperMethod.ParamMap<?>));
    }
    private static void transaction(String selected,boolean committed) {
        List<Map<String,Object>> events=events(selected);
        check(selected+"-first-user-FOR-UPDATE",!events.isEmpty() && ((String)events.get(0).get("statement")).endsWith("StoreUserMapper.selectForUpdate") && ((String)events.get(0).get("sql")).toUpperCase().contains("FOR UPDATE"));
        check(selected+"-second-own-order-FOR-UPDATE",events.size()>1 && ((String)events.get(1).get("statement")).endsWith("OrderActionMapper.selectOwnForUpdate") && ((String)events.get(1).get("sql")).toUpperCase().contains("FOR UPDATE"));
        check(selected+"-actual-RC-write-transaction",events.stream().allMatch(e->Boolean.TRUE.equals(e.get("activeTransaction")) && Boolean.FALSE.equals(e.get("readOnly")) && Integer.valueOf(Connection.TRANSACTION_READ_COMMITTED).equals(e.get("springIsolation")) && Integer.valueOf(Connection.TRANSACTION_READ_COMMITTED).equals(e.get("jdbcIsolation"))));
        check(selected+"-same-physical-connection",events.stream().map(e->e.get("connectionId")).distinct().count()==1);
        int expected=committed?TransactionSynchronization.STATUS_COMMITTED:TransactionSynchronization.STATUS_ROLLED_BACK;
        check(selected+"-actual-completion",completions.stream().anyMatch(e->selected.equals(e.get("phase")) && Integer.valueOf(expected).equals(e.get("status"))));
        check(selected+"-proxy-returned-after-transaction",!TransactionSynchronizationManager.isActualTransactionActive());
    }
    private static void noDml(String selected) {
        check(selected+"-no-DML",events(selected).stream().noneMatch(e->"update".equals(e.get("method"))));
    }
    private static void noProductReads(String selected) {
        check(selected+"-no-product-or-line-queries",events(selected).stream().noneMatch(e->((String)e.get("statement")).endsWith("selectProductForUpdate") || ((String)e.get("statement")).endsWith("selectForOrder")));
    }
    private static Map<String,Object> order(DataSource data,long userId,String orderNo) throws Exception {
        try(Connection c=data.getConnection();PreparedStatement p=c.prepareStatement("SELECT id,order_no,user_id,status,total_amount,created_at,updated_at,payment_method,payment_no,paid_at,cancelled_at,shipped_at,completed_at,SHA2(receiver_name,256),SHA2(receiver_phone,256),SHA2(receiver_address,256) FROM sales_order WHERE user_id=? AND order_no=?")) {
            p.setLong(1,userId);p.setString(2,orderNo);
            try(ResultSet r=p.executeQuery()) {
                check("fixture-order-owned",r.next());Map<String,Object> row=new LinkedHashMap<>();
                String[] names={"id","orderNo","userId","status","totalAmount","createdAt","updatedAt","paymentMethod","paymentNo","paidAt","cancelledAt","shippedAt","completedAt","receiverNameSha256","receiverPhoneSha256","receiverAddressSha256"};
                for(int i=0;i<names.length;i++)row.put(names[i],r.getString(i+1));
                return row;
            }
        }
    }
    private static List<Map<String,Long>> lines(DataSource data,long orderId) throws Exception {
        List<Map<String,Long>> rows=new ArrayList<>();
        try(Connection c=data.getConnection();PreparedStatement p=c.prepareStatement("SELECT product_id,quantity FROM sales_order_item WHERE order_id=? ORDER BY id")) {
            p.setLong(1,orderId);try(ResultSet r=p.executeQuery()){while(r.next())rows.add(Map.of("productId",r.getLong(1),"quantity",r.getLong(2)));}
        }
        return rows;
    }
    private static Map<Long,Map<String,String>> products(DataSource data,List<Map<String,Long>> lines) throws Exception {
        Map<Long,Map<String,String>> found=new LinkedHashMap<>();
        try(Connection c=data.getConnection();PreparedStatement p=c.prepareStatement("SELECT stock,version,status,sku,name,cover_image,price,category_id,summary,description,sort_order,created_at,updated_at FROM product WHERE id=?")) {
            for(Map<String,Long> line:lines){p.setLong(1,line.get("productId"));try(ResultSet r=p.executeQuery()){
                check("native-line-product-exists",r.next());Map<String,String> row=new LinkedHashMap<>();
                String[] keys={"stock","version","status","sku","name","coverImage","price","categoryId","summary","description","sortOrder","createdAt","updatedAt"};
                for(int i=0;i<keys.length;i++)row.put(keys[i],r.getString(i+1));found.put(line.get("productId"),row);
            }}
        }
        return found;
    }
    private static String digest(DataSource data,String table) throws Exception {
        if(!List.of("product","cart_item","sales_order_item").contains(table))throw new IllegalArgumentException();
        MessageDigest digest=MessageDigest.getInstance("SHA-256");
        try(Connection c=data.getConnection();PreparedStatement p=c.prepareStatement("SELECT * FROM "+table+" ORDER BY id");ResultSet r=p.executeQuery()) {
            ResultSetMetaData metadata=r.getMetaData();
            while(r.next())for(int i=1;i<=metadata.getColumnCount();i++){
                String value=r.getString(i);byte[] bytes=value==null?null:value.getBytes(StandardCharsets.UTF_8);
                digest.update((bytes==null?"-1:":bytes.length+":").getBytes(StandardCharsets.US_ASCII));if(bytes!=null)digest.update(bytes);
            }
        }
        return HexFormat.of().formatHex(digest.digest());
    }
    private static void immutableOrder(String selected,Map<String,Object> before,Map<String,Object> after,Set<String> allowed) {
        check(selected+"-immutable-order-snapshots",before.entrySet().stream().filter(e->!allowed.contains(e.getKey())).allMatch(e->java.util.Objects.equals(e.getValue(),after.get(e.getKey()))));
    }
    private static void conflict(String selected,Runnable call) {
        phase=selected;
        try {call.run();check(selected+"-409",false);}
        catch(BusinessException expected){check(selected+"-409",expected.getStatus()==HttpStatus.CONFLICT);}
        transaction(selected,false);noDml(selected);noProductReads(selected);
    }
    private static void live() throws Exception {
        long userId=Long.parseLong(System.getenv().getOrDefault("STEP10_NATIVE_USER_ID","2"));
        String payNo=System.getenv("STEP10_NATIVE_PAY_ORDER_NO"),cancelNo=System.getenv("STEP10_NATIVE_CANCEL_ORDER_NO");
        check("two-explicit-order-fixtures",payNo!=null && cancelNo!=null && !payNo.equals(cancelNo));
        SpringApplication application=new SpringApplication(Class.forName("org.csucampuscraft.storefront.CSUCampusCraftUserApplication"));
        application.setLogStartupInfo(false);
        try(ConfigurableApplicationContext context=application.run("--server.port=0","--server.address=127.0.0.1","--spring.profiles.active=default","--spring.main.banner-mode=off","--logging.level.root=OFF","--mybatis-plus.global-config.banner=false")) {
            DataSource data=context.getBean(DataSource.class);LocalDateTime stamp;
            try(Connection c=data.getConnection();PreparedStatement p=c.prepareStatement("SELECT updated_at,role,status FROM store_user WHERE id=?")){
                p.setLong(1,userId);try(ResultSet r=p.executeQuery()){check("native-customer-exists",r.next());check("native-enabled-customer","CUSTOMER".equals(r.getString(2)) && "ENABLED".equals(r.getString(3)));stamp=r.getObject(1,LocalDateTime.class);}
            }
            SessionIdentity actor=new SessionIdentity(userId,stamp);PaymentService service=context.getBean(PaymentService.class);
            check("actual-Service-proxy",AopUtils.isAopProxy(service));
            for(String method:List.of("pay","cancel")){
                Transactional annotation=(method.equals("pay")?PaymentService.class.getMethod(method,SessionIdentity.class,String.class,MultiValueMap.class):PaymentService.class.getMethod(method,SessionIdentity.class,String.class)).getAnnotation(Transactional.class);
                check(method+"-declares-RC",annotation!=null && annotation.isolation()==Isolation.READ_COMMITTED);
            }
            context.getBean(SqlSessionFactory.class).getConfiguration().addInterceptor(new Trace());
            Map<String,Object> unpaid=order(data,userId,payNo),toCancel=order(data,userId,cancelNo);
            check("both-native-orders-pending","PENDING_PAYMENT".equals(unpaid.get("status")) && "PENDING_PAYMENT".equals(toCancel.get("status")));
            String allProductBefore=digest(data,"product"),allCartBefore=digest(data,"cart_item"),allLinesBefore=digest(data,"sales_order_item");
            phase="pending-failure";
            check("failure-outcome",service.pay(actor,payNo,result("FAILURE"))==OrderActionResult.PAYMENT_FAILED);
            transaction(phase,true);noDml(phase);noProductReads(phase);
            check("failure-all-order-fields-unchanged",unpaid.equals(order(data,userId,payNo)));
            phase="first-success";
            check("success-outcome",service.pay(actor,payNo,result("SUCCESS"))==OrderActionResult.PAYMENT_SUCCEEDED);
            transaction(phase,true);noProductReads(phase);
            Map<String,Object> paid=order(data,userId,payNo);
            check("paid-fields","PAID".equals(paid.get("status")) && "MOCK".equals(paid.get("paymentMethod")) && paid.get("paidAt")!=null && ((String)paid.get("paymentNo")).matches("CSUPAY-[0-9a-f]{32}"));
            check("paid-time-chain",LocalDateTime.parse(((String)paid.get("paidAt")).replace(' ','T')).compareTo(LocalDateTime.parse(((String)paid.get("createdAt")).replace(' ','T')))>=0);
            immutableOrder("pay",unpaid,paid,Set.of("status","paymentMethod","paymentNo","paidAt","updatedAt"));
            check("success-one-conditional-update",events(phase).stream().filter(e->"update".equals(e.get("method"))).count()==1 && events(phase).stream().filter(e->"update".equals(e.get("method"))).allMatch(e->Integer.valueOf(1).equals(e.get("affectedRows")) && ((String)e.get("statement")).endsWith("markPaid")));
            try(Connection c=data.getConnection();PreparedStatement p=c.prepareStatement("SELECT COUNT(*) FROM sales_order WHERE payment_no=LOWER(?)")){p.setString(1,(String)paid.get("paymentNo"));try(ResultSet r=p.executeQuery()){r.next();check("receipt-global-CI-unique",r.getLong(1)==1);}}
            phase="repeat-success";
            check("repeat-success-outcome",service.pay(actor,payNo,result("SUCCESS"))==OrderActionResult.PAYMENT_ALREADY_SUCCEEDED);
            transaction(phase,true);noDml(phase);noProductReads(phase);
            check("repeat-keeps-entire-paid-row",paid.equals(order(data,userId,payNo)));
            conflict("paid-failure",()->service.pay(actor,payNo,result("FAILURE")));
            conflict("paid-cancel",()->service.cancel(actor,payNo));
            check("all-payment-phases-product-byte-digest-unchanged",allProductBefore.equals(digest(data,"product")));

            List<Map<String,Long>> lines=lines(data,Long.parseLong((String)toCancel.get("id")));
            check("native-cancel-two-line-fixture",lines.size()==2);
            Map<Long,Map<String,String>> productBefore=products(data,lines);
            phase="first-cancel";
            check("cancel-outcome",service.cancel(actor,cancelNo)==OrderActionResult.ORDER_CANCELLED);
            transaction(phase,true);
            Map<String,Object> cancelled=order(data,userId,cancelNo);
            check("cancelled-fields","CANCELLED".equals(cancelled.get("status")) && cancelled.get("cancelledAt")!=null && cancelled.get("paymentMethod")==null && cancelled.get("paymentNo")==null && cancelled.get("paidAt")==null);
            immutableOrder("cancel",toCancel,cancelled,Set.of("status","cancelledAt","updatedAt"));
            check("cancel-time-chain",LocalDateTime.parse(((String)cancelled.get("cancelledAt")).replace(' ','T')).compareTo(LocalDateTime.parse(((String)cancelled.get("createdAt")).replace(' ','T')))>=0);
            List<Map<String,Object>> lockEvents=events(phase).stream().filter(e->((String)e.get("statement")).endsWith("selectProductForUpdate")).toList();
            List<Long> expectedIds=lines.stream().map(x->x.get("productId")).sorted().toList();
            check("cancel-products-lock-ascending",lockEvents.stream().map(e->number(e,"productId")).toList().equals(expectedIds));
            List<Map<String,Object>> phaseEvents=events(phase);
            int firstDml=0;while(firstDml<phaseEvents.size() && !"update".equals(phaseEvents.get(firstDml).get("method")))firstDml++;
            check("all-product-locks-before-first-DML",firstDml>0 && phaseEvents.subList(0,firstDml).stream().filter(e->((String)e.get("statement")).endsWith("selectProductForUpdate")).count()==2);
            Map<Long,Map<String,String>> productAfter=products(data,lines);
            for(Map<String,Long> line:lines){long id=line.get("productId");Map<String,String> before=productBefore.get(id),after=productAfter.get(id);
                check("restock-current-amount-and-version-"+id,Long.parseLong(after.get("stock"))==Long.parseLong(before.get("stock"))+line.get("quantity") && Long.parseLong(after.get("version"))==Long.parseLong(before.get("version"))+1);
                check("restock-preserves-status-and-material-"+id,before.entrySet().stream().filter(e->!Set.of("stock","version","updatedAt").contains(e.getKey())).allMatch(e->java.util.Objects.equals(e.getValue(),after.get(e.getKey()))));
                Map<String,Object> event=phaseEvents.stream().filter(e->((String)e.get("statement")).endsWith("restockProduct") && number(e,"productId")==id).findFirst().orElseThrow();
                check("restock-original-quantity-CAS-"+id,number(event,"quantity")==line.get("quantity") && number(event,"version")==Long.parseLong(before.get("version")) && Integer.valueOf(1).equals(event.get("affectedRows")) && ((String)event.get("sql")).contains("version=?"));
            }
            check("cancel-exactly-three-DML",phaseEvents.stream().filter(e->"update".equals(e.get("method"))).count()==3 && phaseEvents.stream().filter(e->"update".equals(e.get("method"))).allMatch(e->Integer.valueOf(1).equals(e.get("affectedRows"))));
            String productAfterCancel=digest(data,"product");
            phase="repeat-cancel";
            check("repeat-cancel-outcome",service.cancel(actor,cancelNo)==OrderActionResult.ORDER_ALREADY_CANCELLED);
            transaction(phase,true);noDml(phase);noProductReads(phase);
            check("repeat-keeps-entire-cancelled-row",cancelled.equals(order(data,userId,cancelNo)));
            check("repeat-does-not-restock",productAfterCancel.equals(digest(data,"product")));
            conflict("cancelled-success",()->service.pay(actor,cancelNo,result("SUCCESS")));
            conflict("cancelled-failure",()->service.pay(actor,cancelNo,result("FAILURE")));
            check("all-actions-preserve-cart",allCartBefore.equals(digest(data,"cart_item")));
            check("all-actions-preserve-all-order-lines",allLinesBefore.equals(digest(data,"sales_order_item")));
            check("later-actions-preserve-first-receipt",paid.equals(order(data,userId,payNo)));
            check("later-actions-preserve-first-cancellation",cancelled.equals(order(data,userId,cancelNo)));
        }
    }
    public static void main(String[] args) throws Exception {
        boolean completed=false;String failure=null;
        boolean structuralOnly=List.of(args).contains("--structural");
        try{
            structural();
            if(!structuralOnly){if(!List.of(args).contains("--live"))throw new IllegalArgumentException("Use explicit probe mode");live();}
            completed=true;
        }catch(Throwable caught){failure=caught.getClass().getName();}
        Map<String,Object> result=new LinkedHashMap<>();result.put("overall",completed?"PASS":"FAIL");
        result.put("scope",structuralOnly?"Actual MyBatis ParamMap whitelist regression only; no app, DB, HTTP or Service transaction":"ParamMap regression and actual private-DB PaymentService sequential operations; no HTTP, order creation, concurrency or injected-failure claim");
        result.put("checks",checks.size());result.put("checksPassed",checks.stream().filter(e->Boolean.TRUE.equals(e.get("passed"))).count());
        result.put("details",checks);result.put("sqlEvents",sqlEvents);result.put("transactionCompletions",completions);
        result.put("payOrderNo",System.getenv("STEP10_NATIVE_PAY_ORDER_NO"));result.put("cancelOrderNo",System.getenv("STEP10_NATIVE_CANCEL_ORDER_NO"));
        result.put("failureClass",failure);result.put("rawSecretsOrShippingRecorded",false);
        System.out.println(new com.fasterxml.jackson.databind.ObjectMapper().writeValueAsString(result));
        if(!completed)System.exit(1);
    }
}
