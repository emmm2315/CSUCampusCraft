import com.baomidou.mybatisplus.core.MybatisConfiguration;
import java.lang.reflect.Proxy;
import java.sql.PreparedStatement;
import java.util.Map;
import org.apache.ibatis.scripting.defaults.DefaultParameterHandler;
import org.csucampuscraft.storefront.order.OrderMapper;
import org.csucampuscraft.storefront.order.OrderQuery;

/** Executes the actual Mapper parameter-binding path without a database or receiver values. */
public class OrderQueryParameterProbe {
    public static void main(String[] args) throws Exception {
        var configuration = new MybatisConfiguration();
        configuration.addMapper(OrderMapper.class);
        var mapped = configuration.getMappedStatement(OrderMapper.class.getName()+".selectOwn");
        var parameters = Map.of("userId",1L,"query",OrderQuery.bind(null,null,null,null));
        var bound = mapped.getBoundSql(parameters);
        System.out.println("parameter_names="+bound.getParameterMappings().stream().map(x->x.getProperty()).toList());
        var statement = (PreparedStatement) Proxy.newProxyInstance(OrderQueryParameterProbe.class.getClassLoader(),
                new Class<?>[]{PreparedStatement.class}, (proxy,method,values) -> null);
        try {
            new DefaultParameterHandler(mapped,parameters,bound).setParameters(statement);
            System.out.println("actual_mapper_parameter_binding=PASS");
        } catch (RuntimeException failure) {
            System.out.println("actual_mapper_parameter_binding=FAIL");
            for (Throwable current=failure;current!=null;current=current.getCause()) {
                System.out.println("failure_type="+current.getClass().getSimpleName());
            }
        }
    }
}
