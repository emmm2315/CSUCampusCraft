package org.csucampuscraft.admin.customer;

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
import org.csucampuscraft.admin.dashboard.DashboardService;
import org.csucampuscraft.admin.dashboard.DashboardSummary;
import org.csucampuscraft.admin.foundation.web.BusinessException;
import org.springframework.aop.support.AopUtils;
import org.springframework.boot.SpringApplication;
import org.springframework.context.ConfigurableApplicationContext;
import org.springframework.http.HttpStatus;
import org.springframework.transaction.annotation.Isolation;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.transaction.support.TransactionSynchronization;
import org.springframework.transaction.support.TransactionSynchronizationManager;

/** External sequential actual-Service probe. No fixture creation, grants, direct SQL writes, hooks or threads. */
public final class NativeCustomerDashboardProbe {
    private static final List<Map<String,Object>> checks=new ArrayList<>(),sqlEvents=new ArrayList<>(),completions=new ArrayList<>(),summaries=new ArrayList<>();
    private static final Set<String> registered=new LinkedHashSet<>();
    private static String phase="setup";
    private static void check(String name,boolean passed){checks.add(Map.of("name",name,"passed",passed));if(!passed)throw new AssertionError(name);}
    private static Map<String,Object> safeNumbers(Object parameters){
        Map<String,Object> safe=new LinkedHashMap<>();
        if(parameters instanceof Map<?,?> map)for(String key:List.of("userId","orderId","productId","quantity","version")){
            if(map.containsKey(key) && map.get(key) instanceof Number number)safe.put(key,number);
        }return safe;
    }
    private static void structural(){
        org.apache.ibatis.binding.MapperMethod.ParamMap<Object> p=new org.apache.ibatis.binding.MapperMethod.ParamMap<>();p.put("userId",4L);p.put("param1",4L);
        check("ParamMap-only-explicit-userId-and-param1",p.size()==2 && !p.containsKey("orderId") && !p.containsKey("quantity"));
        check("ParamMap-missing-optional-keys-not-read",safeNumbers(p).equals(Map.of("userId",4L)));
        check("ParamMap-input-unmodified",p.size()==2 && p.get("param1").equals(4L));
        p.put("orderId",2L);p.put("productId",3L);p.put("quantity",4);p.put("version",5L);p.put("email","synthetic-not-recorded");p.put("csrfToken","synthetic-not-recorded");
        check("ParamMap-present-numeric-values-retained",safeNumbers(p).equals(Map.of("userId",4L,"orderId",2L,"productId",3L,"quantity",4,"version",5L)));
        check("ParamMap-sensitive-and-unlisted-keys-excluded",!safeNumbers(p).containsKey("email") && !safeNumbers(p).containsKey("csrfToken"));
        p.put("quantity","4");p.put("version",null);check("ParamMap-nonnumeric-null-values-skipped",!safeNumbers(p).containsKey("quantity") && !safeNumbers(p).containsKey("version"));
        check("nonmap-and-null-parameters-safe",safeNumbers(null).isEmpty() && safeNumbers(4L).isEmpty());
        check("safe-output-is-ordinary-map",!(safeNumbers(p) instanceof org.apache.ibatis.binding.MapperMethod.ParamMap<?>));
    }
    @Intercepts({@Signature(type=Executor.class,method="query",args={MappedStatement.class,Object.class,RowBounds.class,ResultHandler.class}),@Signature(type=Executor.class,method="update",args={MappedStatement.class,Object.class})})
    public static final class Trace implements Interceptor {
        @Override public Object intercept(Invocation call)throws Throwable {
            MappedStatement mapped=(MappedStatement)call.getArgs()[0];Object parameters=call.getArgs()[1];Connection c=((Executor)call.getTarget()).getTransaction().getConnection();
            boolean active=TransactionSynchronizationManager.isActualTransactionActive();
            if(active && registered.add(phase)){String current=phase;TransactionSynchronizationManager.registerSynchronization(new TransactionSynchronization(){@Override public void afterCompletion(int status){completions.add(Map.of("phase",current,"status",status));}});}
            Map<String,Object> event=new LinkedHashMap<>();event.put("phase",phase);event.put("statement",mapped.getId());event.put("sql",mapped.getBoundSql(parameters).getSql().replaceAll("\\s+"," ").strip());event.put("method",call.getMethod().getName());event.put("activeTransaction",active);event.put("readOnly",TransactionSynchronizationManager.isCurrentTransactionReadOnly());event.put("springIsolation",TransactionSynchronizationManager.getCurrentTransactionIsolationLevel());event.put("jdbcIsolation",c.getTransactionIsolation());event.put("connectionId",c.unwrap(JdbcConnection.class).getId());event.put("safeNumbers",safeNumbers(parameters));sqlEvents.add(event);
            Object result=call.proceed();if(result instanceof Number n)event.put("affectedRows",n);return result;
        }
    }
    private static List<Map<String,Object>> events(String selected){return sqlEvents.stream().filter(e->selected.equals(e.get("phase"))).toList();}
    private static long userId(Map<String,Object> event){Map<?,?> safe=(Map<?,?>)event.get("safeNumbers");return safe.containsKey("userId")?((Number)safe.get("userId")).longValue():-1;}
    private static void completion(String selected,boolean committed){int status=committed?TransactionSynchronization.STATUS_COMMITTED:TransactionSynchronization.STATUS_ROLLED_BACK;check(selected+"-actual-completion",completions.stream().anyMatch(x->selected.equals(x.get("phase")) && Integer.valueOf(status).equals(x.get("status"))));check(selected+"-returned-outside-transaction",!TransactionSynchronizationManager.isActualTransactionActive());}
    private static void transaction(String selected,int count,long actorId,Long targetId,boolean committed){
        List<Map<String,Object>> e=events(selected);check(selected+"-exact-SQL-count",e.size()==count);
        check(selected+"-first-current-actor-lock",!e.isEmpty() && ((String)e.get(0).get("statement")).endsWith("StoreUserMapper.selectForUpdate") && ((String)e.get(0).get("sql")).toUpperCase().contains("FOR UPDATE") && userId(e.get(0))==actorId);
        if(targetId!=null)check(selected+"-second-target-lock",e.size()>1 && ((String)e.get(1).get("statement")).endsWith("CustomerMapper.selectTargetForUpdate") && ((String)e.get(1).get("sql")).toUpperCase().contains("FOR UPDATE") && userId(e.get(1))==targetId);
        check(selected+"-actual-RC-write-transaction",e.stream().allMatch(x->Boolean.TRUE.equals(x.get("activeTransaction")) && Boolean.FALSE.equals(x.get("readOnly")) && Integer.valueOf(Connection.TRANSACTION_READ_COMMITTED).equals(x.get("springIsolation")) && Integer.valueOf(Connection.TRANSACTION_READ_COMMITTED).equals(x.get("jdbcIsolation"))));
        check(selected+"-same-physical-connection",e.stream().map(x->x.get("connectionId")).distinct().count()==1);
        check(selected+"-only-user-table-SQL",e.stream().allMatch(x->{String s=((String)x.get("sql")).toLowerCase();return s.contains("store_user") && !s.contains("sales_order") && !s.contains("cart_item") && !s.matches(".*\\b(from|update|join|into)\\s+product\\b.*");}));completion(selected,committed);
    }
    private static void noDml(String selected){check(selected+"-no-DML",events(selected).stream().noneMatch(x->"update".equals(x.get("method"))));}
    private static void changed(String selected,long targetId){
        List<Map<String,Object>> dml=events(selected).stream().filter(x->"update".equals(x.get("method"))).toList();
        check(selected+"-one-conditional-target-update",dml.size()==1 && ((String)dml.get(0).get("statement")).endsWith("CustomerMapper.changeStatus") && Integer.valueOf(1).equals(dml.get(0).get("affectedRows")) && userId(dml.get(0))==targetId);
        String s=(String)dml.get(0).get("sql");check(selected+"-CAS-and-monotonic-microsecond-SQL",s.contains("role='CUSTOMER'") && s.contains("status=?") && s.contains("updated_at=?") && s.contains("GREATEST(CURRENT_TIMESTAMP(6),updated_at+INTERVAL 1 MICROSECOND)"));
    }
    private static Map<String,String> user(DataSource data,long id)throws Exception{
        String sql="SELECT id,role,status,created_at,updated_at,SHA2(username,256),SHA2(display_name,256),SHA2(email,256),SHA2(phone,256),SHA2(password_hash,256) FROM store_user WHERE id=?";
        try(Connection c=data.getConnection();PreparedStatement p=c.prepareStatement(sql)){p.setLong(1,id);try(ResultSet r=p.executeQuery()){check("fixture-user-exists",r.next());String[] keys={"id","role","status","createdAt","updatedAt","usernameDigest","displayNameDigest","emailDigest","phoneDigest","credentialDigest"};Map<String,String> row=new LinkedHashMap<>();for(int i=0;i<keys.length;i++)row.put(keys[i],r.getString(i+1));return row;}}
    }
    private static SessionIdentity identity(DataSource data,long id,String role)throws Exception{
        try(Connection c=data.getConnection();PreparedStatement p=c.prepareStatement("SELECT role,status,updated_at FROM store_user WHERE id=?")){p.setLong(1,id);try(ResultSet r=p.executeQuery()){check("native-"+role+"-exists",r.next());check("native-"+role+"-enabled",role.equals(r.getString(1)) && "ENABLED".equals(r.getString(2)));return new SessionIdentity(id,r.getObject(3,LocalDateTime.class));}}
    }
    private static String digest(DataSource data,String table,Long excludeUser)throws Exception{
        if(!List.of("store_user","category","product","product_image","cart_item","sales_order","sales_order_item").contains(table))throw new IllegalArgumentException();
        String sql=table.equals("store_user")?"SELECT id,username,display_name,role,status,SHA2(email,256),SHA2(phone,256),created_at,updated_at,SHA2(password_hash,256) FROM store_user WHERE id<>? ORDER BY id":"SELECT * FROM "+table+" ORDER BY id";
        MessageDigest digest=MessageDigest.getInstance("SHA-256");try(Connection c=data.getConnection();PreparedStatement p=c.prepareStatement(sql)){if(table.equals("store_user"))p.setLong(1,excludeUser);try(ResultSet r=p.executeQuery()){ResultSetMetaData meta=r.getMetaData();while(r.next())for(int i=1;i<=meta.getColumnCount();i++){String value=r.getString(i);byte[] b=value==null?null:value.getBytes(StandardCharsets.UTF_8);digest.update((b==null?"-1:":b.length+":").getBytes(StandardCharsets.US_ASCII));if(b!=null)digest.update(b);}}}return HexFormat.of().formatHex(digest.digest());
    }
    private static LocalDateTime stamp(Map<String,String> row){return LocalDateTime.parse(row.get("updatedAt").replace(' ','T'));}
    private static void immutable(String selected,Map<String,String> before,Map<String,String> after){check(selected+"-all-non-status-fields-preserved",before.entrySet().stream().filter(e->!Set.of("status","updatedAt").contains(e.getKey())).allMatch(e->java.util.Objects.equals(e.getValue(),after.get(e.getKey()))));}
    private static DashboardSummary independentCounts(DataSource data)throws Exception{
        String[] sql={"SELECT COUNT(*) FROM product WHERE status='ON_SALE'","SELECT COUNT(*) FROM product WHERE status='DRAFT'","SELECT COUNT(*) FROM sales_order WHERE status='PAID'","SELECT COUNT(*) FROM store_user WHERE role='CUSTOMER' AND status='ENABLED'","SELECT COUNT(*) FROM store_user WHERE role='CUSTOMER' AND status='DISABLED'"};long[] n=new long[5];try(Connection c=data.getConnection()){for(int i=0;i<sql.length;i++)try(PreparedStatement p=c.prepareStatement(sql[i]);ResultSet r=p.executeQuery()){r.next();n[i]=r.getLong(1);}}return new DashboardSummary(n[0],n[1],n[2],n[3],n[4]);
    }
    private static DashboardSummary summary(String selected,DashboardService service,DataSource data)throws Exception{
        phase=selected;DashboardSummary got=service.summary();List<Map<String,Object>> e=events(selected);
        check(selected+"-single-mapped-SELECT",e.size()==1 && ((String)e.get(0).get("statement")).endsWith("DashboardMapper.selectSummary") && "query".equals(e.get(0).get("method")));
        String sql=(String)e.get(0).get("sql");check(selected+"-exactly-five-count-subqueries",sql.split("SELECT COUNT\\(\\*\\)",-1).length-1==5);
        check(selected+"-all-five-business-predicates",sql.contains("product WHERE status='ON_SALE'") && sql.contains("product WHERE status='DRAFT'") && sql.contains("sales_order WHERE status='PAID'") && sql.contains("role='CUSTOMER' AND status='ENABLED'") && sql.contains("role='CUSTOMER' AND status='DISABLED'"));
        check(selected+"-actual-readonly-transaction",Boolean.TRUE.equals(e.get(0).get("activeTransaction")) && Boolean.TRUE.equals(e.get(0).get("readOnly")) && !sql.toUpperCase().contains("FOR UPDATE"));completion(selected,true);noDml(selected);
        check(selected+"-matches-independent-diagnostic-counts",got.equals(independentCounts(data)));
        summaries.add(Map.of("phase",selected,"onSaleProductCount",got.onSaleProductCount(),"draftProductCount",got.draftProductCount(),"paidOrderCount",got.paidOrderCount(),"enabledCustomerCount",got.enabledCustomerCount(),"disabledCustomerCount",got.disabledCustomerCount()));return got;
    }
    private static void rejected(String selected,CustomerService service,SessionIdentity actor,String id,List<String> statuses,HttpStatus status,String code,int sqlCount,long actorId,Long targetId){
        phase=selected;try{service.changeStatus(actor,id,statuses);check(selected+"-expected-rejection",false);}catch(BusinessException failure){check(selected+"-expected-rejection",failure.getStatus()==status && code.equals(failure.getCode()));}transaction(selected,sqlCount,actorId,targetId,false);noDml(selected);
    }
    private static void expired(String selected,CustomerService service,SessionIdentity actor,String id,long actorId){phase=selected;try{service.changeStatus(actor,id,List.of("ENABLED"));check(selected+"-identity-rejected",false);}catch(SessionExpiredException failure){check(selected+"-identity-rejected",true);}transaction(selected,1,actorId,null,false);noDml(selected);}
    private static void live()throws Exception{
        long adminId=Long.parseLong(System.getenv().getOrDefault("STEP12_NATIVE_ADMIN_ID","4")),targetId=Long.parseLong(System.getenv().getOrDefault("STEP12_NATIVE_TARGET_ID","3")),customerId=Long.parseLong(System.getenv().getOrDefault("STEP12_NATIVE_CUSTOMER_ID","2"));check("distinct-explicit-actor-and-target-IDs",adminId>0 && targetId>0 && customerId>0 && Set.of(adminId,targetId,customerId).size()==3);
        SpringApplication app=new SpringApplication(Class.forName("org.csucampuscraft.admin.CSUCampusCraftAdminApplication"));app.setLogStartupInfo(false);
        try(ConfigurableApplicationContext context=app.run("--server.port=0","--server.address=127.0.0.1","--spring.profiles.active=default","--spring.main.banner-mode=off","--logging.level.root=OFF","--mybatis-plus.global-config.banner=false")){
            DataSource data=context.getBean(DataSource.class);SessionIdentity actor=identity(data,adminId,"ADMIN"),customer=identity(data,customerId,"CUSTOMER");CustomerService service=context.getBean(CustomerService.class);DashboardService dashboard=context.getBean(DashboardService.class);
            check("actual-CustomerService-proxy",AopUtils.isAopProxy(service));check("actual-DashboardService-proxy",AopUtils.isAopProxy(dashboard));
            Transactional write=CustomerService.class.getMethod("changeStatus",SessionIdentity.class,String.class,List.class).getAnnotation(Transactional.class);check("changeStatus-declares-RC",write!=null && write.isolation()==Isolation.READ_COMMITTED);check("summary-declares-readonly",DashboardService.class.getMethod("summary").getAnnotation(Transactional.class).readOnly());
            Map<String,String> original=user(data,targetId);check("target-is-disabled-CUSTOMER","CUSTOMER".equals(original.get("role")) && "DISABLED".equals(original.get("status")));check("future-target-stamp-fixture",stamp(original).isAfter(LocalDateTime.now(ZoneOffset.UTC)));
            Map<String,String> before=new LinkedHashMap<>();for(String table:List.of("store_user","category","product","product_image","cart_item","sales_order","sales_order_item"))before.put(table,digest(data,table,targetId));
            context.getBean(SqlSessionFactory.class).getConfiguration().addInterceptor(new Trace());String id=Long.toString(targetId);
            DashboardSummary first=summary("dashboard-before",dashboard,data);
            phase="same-disabled";check("same-disabled-result",service.changeStatus(actor,id,List.of("DISABLED"))==CustomerStatusResult.UNCHANGED);transaction(phase,2,adminId,targetId,true);noDml(phase);check("same-disabled-entire-target-unchanged",original.equals(user(data,targetId)));
            phase="first-enable";check("first-enable-result",service.changeStatus(actor,id,List.of("ENABLED"))==CustomerStatusResult.CHANGED);transaction(phase,3,adminId,targetId,true);changed(phase,targetId);Map<String,String> enabled=user(data,targetId);check("first-enable-state-and-exact-one-microsecond","ENABLED".equals(enabled.get("status")) && stamp(original).plusNanos(1000).equals(stamp(enabled)));immutable(phase,original,enabled);
            DashboardSummary enabledCounts=summary("dashboard-enabled",dashboard,data);check("enabled-counts-change-only-target",enabledCounts.equals(new DashboardSummary(first.onSaleProductCount(),first.draftProductCount(),first.paidOrderCount(),first.enabledCustomerCount()+1,first.disabledCustomerCount()-1)));
            phase="repeat-enabled";check("repeat-enabled-result",service.changeStatus(actor,id,List.of("ENABLED"))==CustomerStatusResult.UNCHANGED);transaction(phase,2,adminId,targetId,true);noDml(phase);check("repeat-enabled-entire-target-unchanged",enabled.equals(user(data,targetId)));
            phase="first-disable";check("first-disable-result",service.changeStatus(actor,id,List.of("DISABLED"))==CustomerStatusResult.CHANGED);transaction(phase,3,adminId,targetId,true);changed(phase,targetId);Map<String,String> disabled=user(data,targetId);check("first-disable-state-and-exact-one-microsecond","DISABLED".equals(disabled.get("status")) && stamp(enabled).plusNanos(1000).equals(stamp(disabled)));immutable(phase,enabled,disabled);check("roundtrip-does-not-restore-old-stamp",!stamp(original).equals(stamp(disabled)));
            DashboardSummary after=summary("dashboard-after-roundtrip",dashboard,data);check("roundtrip-restores-only-counts",first.equals(after));
            phase="repeat-disabled";check("repeat-disabled-result",service.changeStatus(actor,id,List.of("DISABLED"))==CustomerStatusResult.UNCHANGED);transaction(phase,2,adminId,targetId,true);noDml(phase);check("repeat-disabled-entire-target-unchanged",disabled.equals(user(data,targetId)));
            rejected("invalid-target-enum",service,actor,id,List.of("ADMIN"),HttpStatus.BAD_REQUEST,"INVALID_ENUM",2,adminId,targetId);
            rejected("missing-target-status",service,actor,id,null,HttpStatus.BAD_REQUEST,"INVALID_TARGET_STATUS",2,adminId,targetId);
            rejected("duplicate-target-status",service,actor,id,List.of("ENABLED","DISABLED"),HttpStatus.BAD_REQUEST,"INVALID_TARGET_STATUS",2,adminId,targetId);
            rejected("empty-target-status",service,actor,id,List.of(""),HttpStatus.BAD_REQUEST,"INVALID_ENUM",2,adminId,targetId);
            rejected("invalid-target-ID",service,actor,"bad-id",List.of("ENABLED"),HttpStatus.BAD_REQUEST,"INVALID_INTEGER",1,adminId,null);
            rejected("admin-is-not-customer-target",service,actor,Long.toString(adminId),List.of("DISABLED"),HttpStatus.NOT_FOUND,"CUSTOMER_NOT_FOUND",2,adminId,adminId);
            long absentId=Long.MAX_VALUE;try(Connection c=data.getConnection();PreparedStatement p=c.prepareStatement("SELECT COUNT(*) FROM store_user WHERE id=?")){p.setLong(1,absentId);try(ResultSet r=p.executeQuery()){r.next();check("absent-ID-fixture",r.getLong(1)==0);}}
            rejected("unknown-target-ID",service,actor,Long.toString(absentId),List.of("ENABLED"),HttpStatus.NOT_FOUND,"CUSTOMER_NOT_FOUND",2,adminId,absentId);
            expired("stale-admin-stamp",service,new SessionIdentity(adminId,actor.authStamp().plusNanos(1000)),id,adminId);
            rejected("customer-caller-forbidden",service,customer,id,List.of("ENABLED"),HttpStatus.FORBIDDEN,"AUTH_ROLE_FORBIDDEN",1,customerId,null);
            expired("absent-actor",service,new SessionIdentity(absentId,actor.authStamp()),id,absentId);
            phase="null-actor";try{service.changeStatus(null,id,List.of("ENABLED"));check("null-actor-rejected",false);}catch(SessionExpiredException failure){check("null-actor-rejected",true);}check("null-actor-no-SQL",events(phase).isEmpty());check("null-actor-returned-outside-transaction",!TransactionSynchronizationManager.isActualTransactionActive());
            check("rejections-preserve-entire-target",disabled.equals(user(data,targetId)));for(String table:before.keySet())check("all-phases-preserve-"+(table.equals("store_user")?"other-users":table),before.get(table).equals(digest(data,table,targetId)));
        }
    }
    public static void main(String[] args)throws Exception{
        boolean completed=false;String failure=null;boolean structuralOnly=List.of(args).contains("--structural");try{structural();if(!structuralOnly){if(!List.of(args).contains("--live"))throw new IllegalArgumentException("Explicit mode required");live();}completed=true;}catch(Throwable caught){failure=caught.getClass().getName();}
        Map<String,Object> result=new LinkedHashMap<>();result.put("overall",completed?"PASS":"FAIL");result.put("scope",structuralOnly?"Actual MyBatis ParamMap regression; no application, database or HTTP":"Actual private-DB CustomerService sequential target-status changes and readonly DashboardService observations; no fixture writes, HTTP, concurrency or fault injection");result.put("checks",checks.size());result.put("checksPassed",checks.stream().filter(e->Boolean.TRUE.equals(e.get("passed"))).count());result.put("details",checks);result.put("sqlEvents",sqlEvents);result.put("transactionCompletions",completions);result.put("dashboardObservations",summaries);result.put("failureClass",failure);result.put("rawSecretsOrContactsRecorded",false);System.out.println(new com.fasterxml.jackson.databind.ObjectMapper().writeValueAsString(result));if(!completed)System.exit(1);
    }
}
