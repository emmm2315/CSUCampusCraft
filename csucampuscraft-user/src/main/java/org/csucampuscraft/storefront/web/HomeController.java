package org.csucampuscraft.storefront.web;

import org.csucampuscraft.storefront.catalog.CategoryService;
import org.springframework.stereotype.Controller;
import org.springframework.ui.Model;
import org.springframework.web.bind.annotation.GetMapping;

@Controller
public class HomeController {
    private final CategoryService categoryService;

    public HomeController(CategoryService categoryService) {
        this.categoryService = categoryService;
    }

    @GetMapping("/")
    public String home(Model model) {
        model.addAttribute("themes", categoryService.listTopLevelThemes());
        return "home";
    }
}
