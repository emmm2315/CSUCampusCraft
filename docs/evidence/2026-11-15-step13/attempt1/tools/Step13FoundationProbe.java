import java.io.*;
import java.lang.reflect.*;
import java.nio.charset.StandardCharsets;
import java.util.*;

public final class Step13FoundationProbe {
  static void require(boolean condition, String label) { if (!condition) throw new AssertionError(label); }
  public static void main(String[] args) throws Exception {
    BufferedReader input=new BufferedReader(new InputStreamReader(System.in, StandardCharsets.UTF_8));
    String raw=input.readLine();
    int n=Integer.parseInt(input.readLine());
    List<String> hashes=new ArrayList<>(); for(int i=0;i<n;i++) hashes.add(input.readLine());
    int checks=0;
    for(String prefix:List.of("org.csucampuscraft.storefront","org.csucampuscraft.admin")) {
      Object service=Class.forName(prefix+".foundation.security.PasswordService").getConstructor().newInstance();
      Method matches=service.getClass().getMethod("matches",String.class,String.class);
      Method hash=service.getClass().getMethod("hash",String.class);
      for(String encoded:hashes) {
        require((boolean)matches.invoke(service,raw,encoded),"seed positive");checks++;
        require(!(boolean)matches.invoke(service,raw+"-invalid",encoded),"seed negative");checks++;
      }
      require(!(boolean)matches.invoke(service,null,hashes.get(0)),"null raw rejected");checks++;
      require(!(boolean)matches.invoke(service,raw,"unusable"),"malformed hash rejected");checks++;
      require(!(boolean)matches.invoke(service,"界".repeat(25),hashes.get(0)),"UTF8 bytes above72 rejected");checks++;
      String encoded=(String)hash.invoke(service,raw);
      require(encoded.matches("\\$2[aby]\\$10\\$[./A-Za-z0-9]{53}"),"new hash cost10");checks++;
      require((boolean)matches.invoke(service,raw,encoded),"new hash positive");checks++;
      require(!(boolean)matches.invoke(service,raw+"-invalid",encoded),"new hash negative");checks++;
      System.out.println("{\"module\":\""+prefix+"\",\"seed_count\":"+hashes.size()+",\"positive_negative_verified\":true,\"cost\":10,\"secret_output\":false}");
    }
    System.out.println("{\"result\":\"PASS\",\"checks\":"+checks+",\"source\":\"classes and libraries extracted from both fresh tested JARs\"}");
  }
}
