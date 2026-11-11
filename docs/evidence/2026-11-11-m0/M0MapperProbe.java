import java.sql.*;
import java.util.*;
import javax.sql.DataSource;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.WebApplicationType;
import org.springframework.jdbc.datasource.DataSourceUtils;
import org.springframework.transaction.PlatformTransactionManager;
import org.springframework.transaction.support.TransactionTemplate;
import com.baomidou.mybatisplus.core.mapper.BaseMapper;

public class M0MapperProbe {
 @SuppressWarnings({"rawtypes","unchecked"})
 public static void main(String[] args) throws Exception {
  var app=new SpringApplication(Class.forName(args[0]));
  app.setWebApplicationType(WebApplicationType.NONE);
  try(var ctx=app.run()) {
   var ds=ctx.getBean(DataSource.class);
   var tx=new TransactionTemplate(ctx.getBean(PlatformTransactionManager.class));
   Class<?> entity=Class.forName(args[1]+".Category");
   BaseMapper mapper=(BaseMapper)ctx.getBean(Class.forName(args[1]+".CategoryMapper"));
   String code="M0_"+args[2].toUpperCase(Locale.ROOT);
   Object category=entity.getConstructor().newInstance();
   for(var pair:Map.of("code",code,"name","M0 rollback fixture","sortOrder",0).entrySet()){
    var f=entity.getDeclaredField(pair.getKey());f.setAccessible(true);f.set(category,pair.getValue());
   }
   String observed=tx.execute(status->{
    try {
     var c=DataSourceUtils.getConnection(ds);
     String zone,db;long id,last;int count;
     try(var s=c.createStatement();var r=s.executeQuery("SELECT @@session.time_zone,DATABASE()")){r.next();zone=r.getString(1);db=r.getString(2);}
     if(!zone.equals("+00:00")||!db.equals("csucampuscraft"))throw new AssertionError("connection context");
     count=mapper.insert(category);
     id=((Number)entity.getMethod("getId").invoke(category)).longValue();
     try(var s=c.createStatement();var r=s.executeQuery("SELECT LAST_INSERT_ID()")){r.next();last=r.getLong(1);}
     Object reread=mapper.selectById(id);
     if(count!=1||id!=last||id<1||id>10000||!entity.getMethod("getCode").invoke(reread).equals(code))throw new AssertionError("mapper primary key");
     status.setRollbackOnly();
     return "M0_MAPPER_PROBE_PASS id="+id+" last_insert_id="+last+" time_zone="+zone+" database="+db+" rollback=true";
    } catch(Exception e){throw new RuntimeException(e);}
   });
   System.out.println(observed);
  }
 }
}
