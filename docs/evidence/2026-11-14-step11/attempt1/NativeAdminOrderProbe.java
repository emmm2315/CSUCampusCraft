package org.csucampuscraft.admin.order;

import com.mysql.cj.jdbc.JdbcConnection;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.sql.Connection;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.sql.ResultSetMetaData;
import java.time.LocalDateTime;
import java.time.ZoneOffset;
import java.util.ArrayList;
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
import org.csucampuscraft.admin.auth.SessionExpiredException;
import org.csucampuscraft.admin.auth.SessionIdentity;
import org.csucampuscraft.admin.foundation.web.BusinessException;
import org.springframework.aop.support.AopUtils;
import org.springframework.boot.SpringApplication;
import org.springframework.context.ConfigurableApplicationContext;
import org.springframework.http.HttpStatus;
import org.springframework.transaction.annotation.Isolation;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.transaction.support.TransactionSynchronization;
import org.springframework.transaction.support.TransactionSynchronizationManager;

/** External sequential actual-Service observation. No fixture writes, HTTP, faults or production hooks. */
public final class NativeAdminOrderProbe {
    private static final List<Map<String,Object>> checks=new ArrayList<>();
    private static final List<Map<String,Object>> sqlEvents=new ArrayList<>();
    private static final List<Map<String,Object>> completions=new ArrayList<>();
    private static final Set<String> registered=new LinkedHashSet<>();
    private static String phase="setup";

    private static void check(String name,boolean passed) {
        checks.add(Map.of("name",name,"passed",passed));
        if(!passed)throw new AssertionError(name);
    }
    private static Map<String,Object> safeNumbers(Object parameters) {
        Map<String,Object> safe=new LinkedHashMap<>();
        if(parameters instanceof Map<?,?> map)for(String key:List.of("userId","orderId","productId","quantity","version")) {
            // MapperMethod.ParamMap#get throws on an absent key: containsKey must precede every optional get.
            if(map.containsKey(key) && map.get(key) instanceof Number number)safe.put(key,number);
        }
        return safe;
    }
    private static void structural() {
        org.apache.ibatis.binding.MapperMethod.ParamMap<Object> map=new org.apache.ibatis.binding.MapperMethod.ParamMap<>();
        map.put("userId",1L);map.put("param1",1L);
        check("ParamMap-fixture-has-only-userId-and-param1",map.size()==2 && !map.containsKey("quantity") && !map.containsKey("orderId"));
        check("ParamMap-optional-missing-keys-skipped",safeNumbers(map).equals(Map.of("userId",1L)));
        check("ParamMap-input-unmodified",map.size()==2 && map.get("param1").equals(1L));
        map.put("orderId",17L);map.put("productId",9L);map.put("quantity",2);map.put("version",3L);
        map.put("receiverName","synthetic-not-recorded");map.put("csrfToken","synthetic-not-recorded");
        check("ParamMap-known-numeric-values-retained",safeNumbers(map).equals(Map.of("userId",1L,"orderId",17L,"productId",9L,"quantity",2,"version",3L)));
        check("ParamMap-sensitive-keys-excluded",!safeNumbers(map).containsKey("receiverName") && !safeNumbers(map).containsKey("csrfToken"));
        map.put("quantity","2");map.put("version",null);
        check("ParamMap-nonnumeric-and-null-skipped",!safeNumbers(map).containsKey("quantity") && !safeNumbers(map).containsKey("version"));
        check("non-map-and-null-safe",safeNumbers(1L).isEmpty() && safeNumbers(null).isEmpty());
        check("safe-output-ordinary-map",!(safeNumbers(map) instanceof org.apache.ibatis.binding.MapperMethod.ParamMap<?>));
    }
    @Intercepts({
        @Signature(type=Executor.class,method="query",args={MappedStatement.class,Object.class,RowBounds.class,ResultHandler.class}),
        @Signature(type=Executor.class,method="update",args={MappedStatement.class,Object.class})
    })
    public static final class Trace implements Interceptor {
        @Override public Object intercept(Invocation call)throws Throwable {
            MappedStatement mapped=(MappedStatement)call.getArgs()[0];Object parameters=call.getArgs()[1];
            Connection connection=((Executor)call.getTarget()).getTransaction().getConnection();
            boolean active=TransactionSynchronizationManager.isActualTransactionActive();
            if(active && registered.add(phase)) {
                String selected=phase;
                TransactionSynchronizationManager.registerSynchronization(new TransactionSynchronization(){
                    @Override public void afterCompletion(int status){completions.add(Map.of("phase",selected,"status",status));}
                });
            }
            Map<String,Object> event=new LinkedHashMap<>();event.put("phase",phase);event.put("statement",mapped.getId());
            event.put("sql",mapped.getBoundSql(parameters).getSql().replaceAll("\\s+"," ").strip());
            event.put("method",call.getMethod().getName());event.put("activeTransaction",active);
            event.put("readOnly",TransactionSynchronizationManager.isCurrentTransactionReadOnly());
            event.put("springIsolation",TransactionSynchronizationManager.getCurrentTransactionIsolationLevel());
            event.put("jdbcIsolation",connection.getTransactionIsolation());
            event.put("connectionId",connection.unwrap(JdbcConnection.class).getId());
            event.put("safeNumbers",safeNumbers(parameters));sqlEvents.add(event);
            Object result=call.proceed();if(result instanceof Number number)event.put("affectedRows",number);return result;
        }
    }
    private static List<Map<String,Object>> events(String selected){return sqlEvents.stream().filter(e->selected.equals(e.get("phase"))).toList();}
    private static void transaction(String selected,int expectedSqlCount,boolean orderLock,boolean committed) {
        List<Map<String,Object>> events=events(selected);
        check(selected+"-exact-SQL-count",events.size()==expectedSqlCount);
        check(selected+"-first-admin-FOR-UPDATE",!events.isEmpty() && ((String)events.get(0).get("statement")).endsWith("StoreUserMapper.selectForUpdate") && ((String)events.get(0).get("sql")).toUpperCase().contains("FOR UPDATE"));
        if(orderLock)check(selected+"-second-global-order-FOR-UPDATE",events.size()>1 && ((String)events.get(1).get("statement")).endsWith("OrderMapper.selectForUpdate") && ((String)events.get(1).get("sql")).toUpperCase().contains("FOR UPDATE"));
        check(selected+"-actual-RC-write-transaction",events.stream().allMatch(e->Boolean.TRUE.equals(e.get("activeTransaction")) && Boolean.FALSE.equals(e.get("readOnly")) && Integer.valueOf(Connection.TRANSACTION_READ_COMMITTED).equals(e.get("springIsolation")) && Integer.valueOf(Connection.TRANSACTION_READ_COMMITTED).equals(e.get("jdbcIsolation"))));
        check(selected+"-same-physical-connection",events.stream().map(e->e.get("connectionId")).distinct().count()==1);
        check(selected+"-no-product-or-order-item-SQL",events.stream().noneMatch(e->{String sql=((String)e.get("sql")).toLowerCase();return sql.matches(".*\\b(from|update|join|into)\\s+product\\b.*") || sql.contains("sales_order_item");}));
        int expected=committed?TransactionSynchronization.STATUS_COMMITTED:TransactionSynchronization.STATUS_ROLLED_BACK;
        check(selected+"-actual-transaction-completion",completions.stream().anyMatch(e->selected.equals(e.get("phase")) && Integer.valueOf(expected).equals(e.get("status"))));
        check(selected+"-returned-after-transaction",!TransactionSynchronizationManager.isActualTransactionActive());
    }
    private static void noDml(String selected){check(selected+"-no-DML",events(selected).stream().noneMatch(e->"update".equals(e.get("method"))));}
    private static void oneShipmentUpdate(String selected,long orderId) {
        List<Map<String,Object>> updates=events(selected).stream().filter(e->"update".equals(e.get("method"))).toList();
        check(selected+"-one-conditional-order-DML",updates.size()==1 && ((String)updates.get(0).get("statement")).endsWith("OrderMapper.markShipped") && Integer.valueOf(1).equals(updates.get(0).get("affectedRows")));
        Map<String,Object> event=updates.get(0);Map<?,?> numbers=(Map<?,?>)event.get("safeNumbers");
        check(selected+"-updates-only-target-order",numbers.containsKey("orderId") && ((Number)numbers.get("orderId")).longValue()==orderId && ((String)event.get("sql")).contains("WHERE id=?") && ((String)event.get("sql")).contains("status='PAID'"));
    }
    private static Map<String,Object> order(DataSource data,String orderNo)throws Exception {
        try(Connection c=data.getConnection();PreparedStatement p=c.prepareStatement("SELECT id,order_no,user_id,status,total_amount,created_at,updated_at,payment_method,payment_no,paid_at,cancelled_at,shipped_at,completed_at,SHA2(receiver_name,256),SHA2(receiver_phone,256),SHA2(receiver_address,256) FROM sales_order WHERE order_no=?")) {
            p.setString(1,orderNo);try(ResultSet r=p.executeQuery()) {
                check("fixture-order-exists",r.next());Map<String,Object> row=new LinkedHashMap<>();
                String[] keys={"id","orderNo","userId","status","totalAmount","createdAt","updatedAt","paymentMethod","paymentNo","paidAt","cancelledAt","shippedAt","completedAt","receiverNameSha256","receiverPhoneSha256","receiverAddressSha256"};
                for(int i=0;i<keys.length;i++)row.put(keys[i],r.getString(i+1));return row;
            }
        }
    }
    private static String digest(DataSource data,String table)throws Exception {
        if(!List.of("category","product","product_image","cart_item","sales_order_item").contains(table))throw new IllegalArgumentException();
        MessageDigest digest=MessageDigest.getInstance("SHA-256");
        try(Connection c=data.getConnection();PreparedStatement p=c.prepareStatement("SELECT * FROM "+table+" ORDER BY id");ResultSet r=p.executeQuery()) {
            ResultSetMetaData meta=r.getMetaData();while(r.next())for(int i=1;i<=meta.getColumnCount();i++) {
                String value=r.getString(i);byte[] bytes=value==null?null:value.getBytes(StandardCharsets.UTF_8);
                digest.update((bytes==null?"-1:":bytes.length+":").getBytes(StandardCharsets.US_ASCII));if(bytes!=null)digest.update(bytes);
            }
        }return HexFormat.of().formatHex(digest.digest());
    }
    private static LocalDateTime time(Map<String,Object> order,String key){return LocalDateTime.parse(((String)order.get(key)).replace(' ','T'));}
    private static SessionIdentity identity(DataSource data,long id,String role)throws Exception {
        try(Connection c=data.getConnection();PreparedStatement p=c.prepareStatement("SELECT updated_at,role,status FROM store_user WHERE id=?")) {
            p.setLong(1,id);try(ResultSet r=p.executeQuery()) {
                check("native-"+role+"-exists",r.next());check("native-"+role+"-enabled",role.equals(r.getString(2)) && "ENABLED".equals(r.getString(3)));
                return new SessionIdentity(id,r.getObject(1,LocalDateTime.class));
            }
        }
    }
    private static void immutableSnapshot(String selected,Map<String,Object> before,Map<String,Object> after) {
        check(selected+"-preserves-amount-payment-and-order-snapshots",before.entrySet().stream().filter(e->!Set.of("status","shippedAt","updatedAt").contains(e.getKey())).allMatch(e->java.util.Objects.equals(e.getValue(),after.get(e.getKey()))));
    }
    private static void conflict(String selected,AdminOrderService service,SessionIdentity actor,String orderNo,HttpStatus status,String code,int expectedSqlCount,boolean orderLock) {
        phase=selected;try{service.ship(actor,orderNo);check(selected+"-expected-rejection",false);}
        catch(BusinessException failure){check(selected+"-expected-rejection",failure.getStatus()==status && code.equals(failure.getCode()));}
        transaction(selected,expectedSqlCount,orderLock,false);noDml(selected);
    }
    private static void expired(String selected,AdminOrderService service,SessionIdentity actor,String orderNo) {
        phase=selected;try{service.ship(actor,orderNo);check(selected+"-identity-rejected",false);}
        catch(SessionExpiredException failure){check(selected+"-identity-rejected",true);}
        transaction(selected,1,false,false);noDml(selected);
    }
    private static String requiredNo(String key){String value=System.getenv(key);check(key+"-explicit-safe-fixture",value!=null && value.matches("[A-Za-z0-9_-]{1,40}"));return value;}
    private static void live()throws Exception {
        String orderNo=requiredNo("STEP11_NATIVE_ORDER_NO"),futureNo=requiredNo("STEP11_NATIVE_FUTURE_ORDER_NO"),completedNo=requiredNo("STEP11_NATIVE_COMPLETED_ORDER_NO"),pendingNo=requiredNo("STEP11_NATIVE_PENDING_ORDER_NO"),cancelledNo=requiredNo("STEP11_NATIVE_CANCELLED_ORDER_NO");
        check("five-distinct-explicit-order-fixtures",Set.of(orderNo,futureNo,completedNo,pendingNo,cancelledNo).size()==5);
        long adminId=Long.parseLong(System.getenv().getOrDefault("STEP11_NATIVE_ADMIN_ID","1")),customerId=Long.parseLong(System.getenv().getOrDefault("STEP11_NATIVE_CUSTOMER_ID","2"));
        SpringApplication app=new SpringApplication(Class.forName("org.csucampuscraft.admin.CSUCampusCraftAdminApplication"));app.setLogStartupInfo(false);
        try(ConfigurableApplicationContext context=app.run("--server.port=0","--server.address=127.0.0.1","--spring.profiles.active=default","--spring.main.banner-mode=off","--logging.level.root=OFF","--mybatis-plus.global-config.banner=false")) {
            DataSource data=context.getBean(DataSource.class);SessionIdentity actor=identity(data,adminId,"ADMIN"),customer=identity(data,customerId,"CUSTOMER");
            AdminOrderService service=context.getBean(AdminOrderService.class);check("actual-AdminOrderService-proxy",AopUtils.isAopProxy(service));
            Transactional annotation=AdminOrderService.class.getMethod("ship",SessionIdentity.class,String.class).getAnnotation(Transactional.class);
            check("ship-declares-READ-COMMITTED",annotation!=null && annotation.isolation()==Isolation.READ_COMMITTED);
            Map<String,Object> paid=order(data,orderNo),future=order(data,futureNo),completed=order(data,completedNo),pending=order(data,pendingNo),cancelled=order(data,cancelledNo);
            check("state-fixtures-prepared","PAID".equals(paid.get("status")) && "PAID".equals(future.get("status")) && "COMPLETED".equals(completed.get("status")) && "PENDING_PAYMENT".equals(pending.get("status")) && "CANCELLED".equals(cancelled.get("status")));
            check("future-paid-fixture-is-actually-future",time(future,"paidAt").isAfter(LocalDateTime.now(ZoneOffset.UTC)));
            Map<String,String> before=new LinkedHashMap<>();for(String table:List.of("category","product","product_image","cart_item","sales_order_item"))before.put(table,digest(data,table));
            context.getBean(SqlSessionFactory.class).getConfiguration().addInterceptor(new Trace());
            phase="first-ship";check("first-ship-outcome",service.ship(actor,orderNo)==ShipmentResult.SHIPPED);transaction(phase,3,true,true);oneShipmentUpdate(phase,Long.parseLong((String)paid.get("id")));
            Map<String,Object> shipped=order(data,orderNo);check("first-ship-state-time","SHIPPED".equals(shipped.get("status")) && shipped.get("shippedAt")!=null && time(shipped,"shippedAt").compareTo(time(shipped,"paidAt"))>=0);immutableSnapshot(phase,paid,shipped);
            phase="repeat-shipped";check("repeat-shipped-outcome",service.ship(actor,orderNo)==ShipmentResult.ALREADY_SHIPPED);transaction(phase,2,true,true);noDml(phase);check("repeat-shipped-retains-entire-row",shipped.equals(order(data,orderNo)));
            phase="repeat-completed";check("repeat-completed-outcome",service.ship(actor,completedNo)==ShipmentResult.ALREADY_SHIPPED);transaction(phase,2,true,true);noDml(phase);check("repeat-completed-retains-entire-row",completed.equals(order(data,completedNo)));
            conflict("pending-rejected",service,actor,pendingNo,HttpStatus.CONFLICT,"SHIPMENT_STATE_CONFLICT",2,true);check("pending-entire-row-unchanged",pending.equals(order(data,pendingNo)));
            conflict("cancelled-rejected",service,actor,cancelledNo,HttpStatus.CONFLICT,"SHIPMENT_STATE_CONFLICT",2,true);check("cancelled-entire-row-unchanged",cancelled.equals(order(data,cancelledNo)));
            phase="future-paid-ship";check("future-paid-ship-outcome",service.ship(actor,futureNo)==ShipmentResult.SHIPPED);transaction(phase,3,true,true);oneShipmentUpdate(phase,Long.parseLong((String)future.get("id")));
            Map<String,Object> futureShipped=order(data,futureNo);check("future-paid-valid-time-chain","SHIPPED".equals(futureShipped.get("status")) && time(futureShipped,"shippedAt").compareTo(time(futureShipped,"paidAt"))>=0);immutableSnapshot(phase,future,futureShipped);
            phase="future-paid-repeat";check("future-repeat-outcome",service.ship(actor,futureNo)==ShipmentResult.ALREADY_SHIPPED);transaction(phase,2,true,true);noDml(phase);check("future-repeat-retains-first-time",futureShipped.equals(order(data,futureNo)));
            String absentNo="NATIVE-STEP11-ABSENT";try(Connection c=data.getConnection();PreparedStatement p=c.prepareStatement("SELECT COUNT(*) FROM sales_order WHERE order_no=?")){p.setString(1,absentNo);try(ResultSet r=p.executeQuery()){r.next();check("unknown-order-fixture-absent",r.getLong(1)==0);}}
            conflict("unknown-order",service,actor,absentNo,HttpStatus.NOT_FOUND,"ORDER_NOT_FOUND",2,true);
            conflict("invalid-number",service,actor,"invalid/no",HttpStatus.NOT_FOUND,"ORDER_NOT_FOUND",1,false);
            SessionIdentity stale=new SessionIdentity(actor.userId(),actor.authStamp().plusNanos(1000));expired("stale-admin-stamp",service,stale,orderNo);
            conflict("customer-role",service,customer,orderNo,HttpStatus.FORBIDDEN,"AUTH_ROLE_FORBIDDEN",1,false);
            long absentId=Long.MAX_VALUE;try(Connection c=data.getConnection();PreparedStatement p=c.prepareStatement("SELECT COUNT(*) FROM store_user WHERE id=?")){p.setLong(1,absentId);try(ResultSet r=p.executeQuery()){r.next();check("absent-actor-fixture",r.getLong(1)==0);}}
            expired("absent-actor",service,new SessionIdentity(absentId,actor.authStamp()),orderNo);
            phase="null-actor";try{service.ship(null,orderNo);check("null-actor-rejected",false);}catch(SessionExpiredException failure){check("null-actor-rejected",true);}
            check("null-actor-no-SQL",events(phase).isEmpty());check("null-actor-proxy-returned-after-transaction",!TransactionSynchronizationManager.isActualTransactionActive());
            for(String table:before.keySet())check("all-phases-preserve-"+table,before.get(table).equals(digest(data,table)));
            check("later-rejections-preserve-shipped-order",shipped.equals(order(data,orderNo)));check("later-rejections-preserve-future-order",futureShipped.equals(order(data,futureNo)));
        }
    }
    public static void main(String[] args)throws Exception {
        boolean completed=false;String failure=null;boolean structuralOnly=List.of(args).contains("--structural");
        try{structural();if(!structuralOnly){if(!List.of(args).contains("--live"))throw new IllegalArgumentException("Use an explicit probe mode");live();}completed=true;}catch(Throwable caught){failure=caught.getClass().getName();}
        Map<String,Object> result=new LinkedHashMap<>();result.put("overall",completed?"PASS":"FAIL");result.put("scope",structuralOnly?"Actual MyBatis ParamMap whitelist regression only; no app, DB, HTTP or Service action":"Actual private-DB AdminOrderService sequential shipping and state/identity checks; no fixture writes, HTTP, concurrency or fault injection");
        result.put("checks",checks.size());result.put("checksPassed",checks.stream().filter(e->Boolean.TRUE.equals(e.get("passed"))).count());result.put("details",checks);result.put("sqlEvents",sqlEvents);result.put("transactionCompletions",completions);result.put("failureClass",failure);result.put("rawSecretsOrShippingRecorded",false);
        System.out.println(new com.fasterxml.jackson.databind.ObjectMapper().writeValueAsString(result));if(!completed)System.exit(1);
    }
}
