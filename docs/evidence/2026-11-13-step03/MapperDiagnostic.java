import org.csucampuscraft.storefront.CSUCampusCraftUserApplication;
import org.csucampuscraft.storefront.catalog.CatalogService;
import org.csucampuscraft.storefront.catalog.CatalogQuery;
import org.springframework.boot.SpringApplication;
public class MapperDiagnostic {
 public static void main(String[] args) {
  try(var context=SpringApplication.run(CSUCampusCraftUserApplication.class,"--spring.main.web-application-type=none","--spring.main.banner-mode=off")) {
   var service=context.getBean(CatalogService.class);
   for(String text:new String[]{"a","毕业","😀","😀".repeat(120)}) {
    try {
     var query=CatalogQuery.bind(null,null,text,null,null,null);
     var page=service.products(query);
     System.out.println("DIAG PASS codepoints="+text.codePointCount(0,text.length())+" total="+page.total());
    } catch(Exception e) {
     System.out.println("DIAG FAIL codepoints="+text.codePointCount(0,text.length()));
     e.printStackTrace(System.out);
    }
   }
  }
 }
}
