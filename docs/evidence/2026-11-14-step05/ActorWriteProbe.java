import java.lang.reflect.*;
import java.sql.*;
import java.time.LocalDateTime;
import java.util.*;
import javax.sql.DataSource;
import org.apache.ibatis.executor.Executor;
import org.apache.ibatis.mapping.MappedStatement;
import org.apache.ibatis.plugin.*;
import org.apache.ibatis.session.*;
import org.springframework.boot.SpringApplication;
import org.springframework.context.ConfigurableApplicationContext;
import org.springframework.transaction.support.TransactionSynchronizationManager;

public final class ActorWriteProbe {
    static final List<Boolean> checks = new ArrayList<>();
    static final List<String> labels = new ArrayList<>();
    static final List<Event> events = new ArrayList<>();
    record Event(String sql, int connection, boolean active, Integer declaredIsolation, int jdbcIsolation) {}
    @Intercepts({
      @Signature(type=Executor.class,method="query",args={MappedStatement.class,Object.class,RowBounds.class,ResultHandler.class}),
      @Signature(type=Executor.class,method="update",args={MappedStatement.class,Object.class})
    })
    public static final class Trace implements Interceptor {
        public Object intercept(Invocation call) throws Throwable {
            MappedStatement ms=(MappedStatement)call.getArgs()[0];
            String sql=ms.getBoundSql(call.getArgs()[1]).getSql().replaceAll("\\s+"," ").trim();
            Connection c=((Executor)call.getTarget()).getTransaction().getConnection();
            boolean active=TransactionSynchronizationManager.isActualTransactionActive();
            Integer iso=TransactionSynchronizationManager.getCurrentTransactionIsolationLevel();
            Object answer=call.proceed();
            events.add(new Event(sql,System.identityHashCode(c),active,iso,c.getTransactionIsolation()));
            return answer;
        }
    }
    static void check(String label,boolean good) {
        labels.add(label);checks.add(good);
        if(!good)throw new IllegalStateException("Probe assertion: "+label);
    }
    static Object identity(Class<?> type,long id,LocalDateTime stamp)throws Exception {
        return type.getConstructor(Long.class,LocalDateTime.class).newInstance(Long.valueOf(id),stamp);
    }
    static LocalDateTime stamp(DataSource ds,long id)throws Exception {
        try(Connection c=ds.getConnection();PreparedStatement p=c.prepareStatement("SELECT updated_at FROM store_user WHERE id=?")){
            p.setLong(1,id);try(ResultSet r=p.executeQuery()){if(!r.next())throw new IllegalStateException("probe account unavailable");return r.getObject(1,LocalDateTime.class);}
        }
    }
    static long[] product(DataSource ds)throws Exception {
        try(Connection c=ds.getConnection();Statement s=c.createStatement();ResultSet r=s.executeQuery("SELECT stock,version FROM product WHERE id=1")){
            r.next();return new long[]{r.getLong(1),r.getLong(2)};
        }
    }
    static Throwable invoke(Method method,Object bean,Object...args)throws Exception {
        try{method.invoke(bean,args);return null;}catch(InvocationTargetException e){return e.getCause();}
    }
    static void trace(String label) {
        for(int i=0;i<events.size();i++){
            Event e=events.get(i);
            System.out.println("SQL_TRACE "+label+" #"+(i+1)+" active="+e.active+" declaredIsolation="+e.declaredIsolation+" jdbcIsolation="+e.jdbcIsolation+" sql="+e.sql);
        }
        check(label+"-sql-present",!events.isEmpty());
        check(label+"-actor-for-update-first",events.get(0).sql.toLowerCase(Locale.ROOT).contains("from store_user")&&events.get(0).sql.toUpperCase(Locale.ROOT).contains("FOR UPDATE"));
        check(label+"-all-active-rc",events.stream().allMatch(e->e.active&&Objects.equals(e.declaredIsolation,Connection.TRANSACTION_READ_COMMITTED)&&e.jdbcIsolation==Connection.TRANSACTION_READ_COMMITTED));
        check(label+"-same-connection",events.stream().map(Event::connection).distinct().count()==1);
    }
    public static void main(String[]args)throws Exception {
        ConfigurableApplicationContext ctx=null;Connection root=null;String originalStatus=null;LocalDateTime originalStamp=null;
        boolean completed=false;
        try {
            Class<?> app=Class.forName("org.csucampuscraft.admin.CSUCampusCraftAdminApplication");
            ctx=SpringApplication.run(app,"--server.port=0","--server.address=127.0.0.1","--spring.profiles.active=default");
            DataSource ds=ctx.getBean(DataSource.class);
            Class<?> ident=Class.forName("org.csucampuscraft.admin.auth.SessionIdentity");
            Object actor=identity(ident,4,stamp(ds,4));
            Object products=ctx.getBean(Class.forName("org.csucampuscraft.admin.catalog.ProductService"));
            Method restock=products.getClass().getMethod("restock",ident,long.class,String.class);
            SqlSessionFactory factory=ctx.getBean(SqlSessionFactory.class);factory.getConfiguration().addInterceptor(new Trace());
            long[] before=product(ds);
            events.clear();check("valid-restock-call",invoke(restock,products,actor,1L,"1")==null);trace("valid-restock");
            check("product-lock-after-actor",events.stream().skip(1).anyMatch(e->e.sql.toLowerCase(Locale.ROOT).contains("from product")&&e.sql.toUpperCase(Locale.ROOT).contains("FOR UPDATE")));
            check("increment-update-sql",events.stream().anyMatch(e->e.sql.toLowerCase(Locale.ROOT).matches(".*stock\\s*=\\s*stock\\s*\\+.*")&&e.sql.toLowerCase(Locale.ROOT).matches(".*version\\s*=\\s*version\\s*\\+.*")));
            long[] after=product(ds);check("committed-stock-version-plus1",after[0]==before[0]+1&&after[1]==before[1]+1);
            Object[] denied={null,identity(ident,4,stamp(ds,4).minusNanos(1000)),identity(ident,1,stamp(ds,1))};
            String[] tags={"missing-actor","stale-stamp","customer-role"};
            for(int i=0;i<denied.length;i++){
                before=product(ds);events.clear();Throwable err=invoke(restock,products,denied[i],1L,"1");
                check(tags[i]+"-refused",err!=null);
                if(i>0){trace(tags[i]);check(tags[i]+"-only-actor-query",events.size()==1);}
                check(tags[i]+"-no-product-write",Arrays.equals(before,product(ds)));
            }
            String port=System.getenv("STEP05_MYSQL_PORT");
            root=DriverManager.getConnection("jdbc:mysql://127.0.0.1:"+port+"/csucampuscraft?connectionTimeZone=UTC&forceConnectionTimeZoneToSession=true","root",System.getenv("STEP05_ROOT_PASSWORD"));
            try(Statement s=root.createStatement()){s.execute("SET SESSION time_zone='+00:00'");try(ResultSet r=s.executeQuery("SELECT status,updated_at FROM store_user WHERE id=4")){r.next();originalStatus=r.getString(1);originalStamp=r.getObject(2,LocalDateTime.class);}s.executeUpdate("UPDATE store_user SET status='DISABLED',updated_at=updated_at WHERE id=4");}
            before=product(ds);events.clear();Throwable err=invoke(restock,products,actor,1L,"1");
            check("disabled-admin-refused",err!=null);trace("disabled-admin");check("disabled-only-actor-query",events.size()==1);check("disabled-no-product-write",Arrays.equals(before,product(ds)));
            try(PreparedStatement p=root.prepareStatement("UPDATE store_user SET status=?,updated_at=? WHERE id=4")){p.setString(1,originalStatus);p.setObject(2,originalStamp);p.executeUpdate();}
            check("actor-status-stamp-restored",stamp(ds,4).equals(originalStamp));
            Object categories=ctx.getBean(Class.forName("org.csucampuscraft.admin.catalog.CategoryService"));
            Class<?> form=Class.forName("org.csucampuscraft.admin.catalog.CategoryForm");
            Object input=form.getConstructor(String.class,String.class,String.class,String.class,String.class).newInstance("STEP05_NATIVE_ID",null,null,"原生回填核对","0");
            Method create=categories.getClass().getMethod("create",ident,form);
            events.clear();Object category=create.invoke(categories,actor,input);trace("native-category-create");
            long id=((Number)category.getClass().getMethod("getId").invoke(category)).longValue();
            System.out.println("AUTO_ID_RETURNED="+id);
            check("native-returned-auto-id",id>0);
            try(Connection c=ds.getConnection();PreparedStatement p=c.prepareStatement("SELECT code,name FROM category WHERE id=?")){
                p.setLong(1,id);try(ResultSet r=p.executeQuery()){check("native-id-select-same-row",r.next()&&r.getString(1).equals("STEP05_NATIVE_ID")&&r.getString(2).equals("原生回填核对"));}
            }
            completed=true;
        } finally {
            if(root!=null){
                if(originalStatus!=null)try(PreparedStatement p=root.prepareStatement("UPDATE store_user SET status=?,updated_at=? WHERE id=4")){p.setString(1,originalStatus);p.setObject(2,originalStamp);p.executeUpdate();}
                root.close();
            }
            if(ctx!=null)ctx.close();
            System.out.println("{\"overall\":\""+(completed&&checks.stream().allMatch(Boolean::booleanValue)?"PASS":"FAIL")+"\",\"checks\":"+checks.size()+",\"rawCredentialsRecorded\":false,\"scope\":\"actual JAR Service transaction, no concurrent request or production fault hook\"}");
            for(int i=0;i<labels.size();i++)System.out.println("CHECK "+labels.get(i)+"="+checks.get(i));
        }
    }
}

