package org.csucampuscraft.storefront.web;

import org.csucampuscraft.storefront.catalog.CatalogService;
import org.csucampuscraft.storefront.catalog.HomeCatalog;
import org.springframework.stereotype.Controller;
import org.springframework.ui.Model;
import org.springframework.web.bind.annotation.GetMapping;

@Controller
public class HomeController {
    private final CatalogService catalog;

    public HomeController(CatalogService catalog) { this.catalog = catalog; }

    @GetMapping("/")
    public String home(Model model) {
        HomeCatalog home = catalog.home();
        model.addAttribute("themes", home.themes());
        model.addAttribute("themeNavigation", home.themeNavigation());
        model.addAttribute("graduationTheme", home.graduationTheme());
        model.addAttribute("newProducts", home.newProducts());
        model.addAttribute("featuredProducts", home.featuredProducts());
        return "home";
    }
}
