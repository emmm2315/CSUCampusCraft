import java.lang.reflect.Proxy;
import java.sql.PreparedStatement;
import java.util.*;
import org.apache.ibatis.session.Configuration;
import org.apache.ibatis.scripting.defaults.DefaultParameterHandler;
import org.csucampuscraft.storefront.catalog.*;

public class PatternBindingSmoke {
 public static void main(String[] args) throws Exception {
  var config=new Configuration();config.addMapper(ProductMapper.class);
  int assertions=0;
  for(String raw:List.of("a","毕业","😀","😀".repeat(120),"!%_\\\\","")) {
   var query=CatalogQuery.bind("5","STATIONERY",raw,"NEWEST","1","6");
   Map<String,Object> parameters=Map.of("query",query,"offset",0L);
   for(String method:List.of("countPublic","selectPublic")) {
    var statement=config.getMappedStatement(ProductMapper.class.getName()+"."+method);
    var bound=statement.getBoundSql(parameters);
    // Both checks matter: SQL parsing alone never resolves the JDBC parameter value.
    if(!raw.isEmpty()) {
     if(!bound.hasAdditionalParameter("likePattern")) {
      // Old code still gets exercised to demonstrate its actual binding failure.
      var oldHandler=new DefaultParameterHandler(statement,parameters,bound);
      oldHandler.setParameters(statementProxy(new LinkedHashMap<>()));
      throw new AssertionError("Missing bound pattern");
     }
     if(!query.getLikePattern().equals(bound.getAdditionalParameter("likePattern")))throw new AssertionError("Wrong bound pattern");
     assertions+=2;
    }
    Map<Integer,Object> sent=new LinkedHashMap<>();
    new DefaultParameterHandler(statement,parameters,bound).setParameters(statementProxy(sent));
    if(!raw.isEmpty()&&!sent.containsValue(query.getLikePattern()))throw new AssertionError("Pattern never reached JDBC binding");
    assertions++;
   }
  }
  System.out.printf("{%cassertions%c:%d,%cjdbc_parameter_binding%c:%cPASS%c}%n",34,34,assertions,34,34,34,34);
 }
 static PreparedStatement statementProxy(Map<Integer,Object> values) {
  return (PreparedStatement)Proxy.newProxyInstance(PatternBindingSmoke.class.getClassLoader(),new Class[]{PreparedStatement.class},(proxy,method,args)->{
   if(method.getName().startsWith("set")&&args!=null&&args.length>=2&&args[0] instanceof Integer index){values.put(index,args[1]);return null;}
   if(method.getName().equals("toString"))return "VerificationPreparedStatement";
   if(method.getReturnType()==boolean.class)return false;
   if(method.getReturnType()==int.class)return 0;
   if(method.getReturnType()==long.class)return 0L;
   return null;
  });
 }
}
