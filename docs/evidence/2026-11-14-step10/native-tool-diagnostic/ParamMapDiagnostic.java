import java.lang.reflect.InvocationTargetException;
import java.lang.reflect.Method;
import org.apache.ibatis.binding.MapperMethod;

/** Offline diagnosis of the original external trace helper, never a database or Service call. */
public final class ParamMapDiagnostic {
    public static void main(String[] args) throws Exception {
        MapperMethod.ParamMap<Object> values=new MapperMethod.ParamMap<>();
        values.put("userId",2L);values.put("param1",2L);
        boolean present=values.containsKey("quantity");
        String directFailure=null,helperFailure=null;
        try{values.get("quantity");}catch(RuntimeException failure){directFailure=failure.getClass().getName();}
        Method helper=Class.forName("org.csucampuscraft.storefront.payment.NativePaymentProbe").getDeclaredMethod("safeNumbers",Object.class);
        helper.setAccessible(true);
        try{helper.invoke(null,values);}catch(InvocationTargetException failure){helperFailure=failure.getCause().getClass().getName();}
        boolean confirmed=!present && "org.apache.ibatis.binding.BindingException".equals(directFailure) && directFailure.equals(helperFailure);
        System.out.println("{\"scope\":\"Offline original external trace helper and actual MyBatis ParamMap; no app/DB/HTTP\",\"confirmed\":"+confirmed+",\"missingKeyPresent\":"+present+",\"directFailureClass\":\""+directFailure+"\",\"originalHelperFailureClass\":\""+helperFailure+"\",\"rawParametersRecorded\":false}");
        if(!confirmed)System.exit(1);
    }
}
