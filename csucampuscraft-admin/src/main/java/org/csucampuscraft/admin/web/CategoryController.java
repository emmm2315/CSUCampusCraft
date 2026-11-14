package org.csucampuscraft.admin.web;

import jakarta.servlet.http.HttpServletRequest;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import org.csucampuscraft.admin.auth.SessionSupport;
import org.csucampuscraft.admin.catalog.Category;
import org.csucampuscraft.admin.catalog.CategoryForm;
import org.csucampuscraft.admin.catalog.CategoryService;
import org.csucampuscraft.admin.foundation.validation.InputChecks;
import org.csucampuscraft.admin.foundation.web.BusinessException;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Controller;
import org.springframework.ui.Model;
import org.springframework.util.MultiValueMap;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.servlet.ModelAndView;
import org.springframework.web.servlet.view.RedirectView;

@Controller
public final class CategoryController {
    private final CategoryService categories;
    private final SessionSupport sessions;

    public CategoryController(CategoryService categories, SessionSupport sessions) {
        this.categories = categories;
        this.sessions = sessions;
    }

    @GetMapping("/categories")
    public String list(@RequestParam(required = false) String createdId, Model model) {
        List<Category> rows = categories.listAll();
        Map<Long, String> parentNames = new LinkedHashMap<>();
        for (Category row : rows) parentNames.put(row.getId(), row.getName());
        model.addAttribute("categories", rows);
        model.addAttribute("parentNames", parentNames);
        model.addAttribute("createdCategory", createdId == null ? null
                : categories.getRequired(InputChecks.longInteger("createdId", createdId, 1, Long.MAX_VALUE)));
        return "categories/list";
    }

    @GetMapping("/categories/new")
    public String newForm(Model model) {
        fillForm(model, CategoryForm.empty(), null);
        return "categories/form";
    }

    @GetMapping("/categories/{categoryId}/edit")
    public String editForm(@PathVariable String categoryId, Model model) {
        Category category = categories.getRequired(id(categoryId));
        fillForm(model, CategoryForm.edit(category), category);
        return "categories/form";
    }

    @PostMapping("/categories")
    public ModelAndView create(@RequestParam MultiValueMap<String, String> parameters,
                               HttpServletRequest request, Model model) {
        try {
            Category created = categories.create(sessions.identity(request), CategoryForm.bind(parameters, false));
            return seeOther("/categories?createdId=" + created.getId());
        } catch (BusinessException failure) {
            if (!formError(failure)) throw failure;
            fillForm(model, CategoryForm.display(parameters), null);
            return formFailure(model, failure);
        }
    }

    @PostMapping("/categories/{categoryId}")
    public ModelAndView update(@PathVariable String categoryId,
                               @RequestParam MultiValueMap<String, String> parameters,
                               HttpServletRequest request, Model model) {
        long target = id(categoryId);
        try {
            categories.update(sessions.identity(request), target, CategoryForm.bind(parameters, true));
            return seeOther("/categories");
        } catch (BusinessException failure) {
            if (!formError(failure)) throw failure;
            Category current = categories.getRequired(target);
            CategoryForm raw = CategoryForm.display(parameters);
            fillForm(model, new CategoryForm(current.getCode(),
                    current.getParentId() == null ? "" : current.getParentId().toString(), "",
                    raw.name(), raw.sortOrder()), current);
            return formFailure(model, failure);
        }
    }

    @PostMapping("/categories/{categoryId}/remove")
    public ModelAndView remove(@PathVariable String categoryId, HttpServletRequest request) {
        categories.remove(sessions.identity(request), id(categoryId));
        return seeOther("/categories");
    }

    private ModelAndView formFailure(Model model, BusinessException failure) {
        model.addAttribute("fieldErrors", failure.getFieldErrors());
        model.addAttribute("globalError", failure.getMessage());
        return new ModelAndView("categories/form", model.asMap(), failure.getStatus());
    }

    private boolean formError(BusinessException error) {
        return error.getStatus() == HttpStatus.BAD_REQUEST || error.getStatus() == HttpStatus.CONFLICT;
    }

    private void fillForm(Model model, CategoryForm form, Category category) {
        model.addAttribute("form", form);
        model.addAttribute("category", category);
        model.addAttribute("parentThemes", categories.listTopLevelThemes());
    }

    private long id(String raw) { return InputChecks.longInteger("categoryId", raw, 1, Long.MAX_VALUE); }

    private ModelAndView seeOther(String target) {
        RedirectView view = new RedirectView(target, true);
        view.setStatusCode(HttpStatus.SEE_OTHER);
        view.setExposeModelAttributes(false);
        view.setExpandUriTemplateVariables(false);
        return new ModelAndView(view);
    }
}
