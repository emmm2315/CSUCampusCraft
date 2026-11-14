package org.csucampuscraft.storefront.auth;

import jakarta.servlet.http.HttpServletRequest;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import org.csucampuscraft.storefront.foundation.security.ReturnUrlPolicy;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Controller;
import org.springframework.ui.Model;
import org.springframework.util.MultiValueMap;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.servlet.ModelAndView;
import org.springframework.web.servlet.view.RedirectView;

@Controller
public final class LoginController {
    private static final String FAILED = "用户名或密码不正确，或账号不可用于本端登录。";
    private final AuthService auth;
    private final SessionSupport sessions;
    private final ReturnUrlPolicy returns;

    public LoginController(AuthService auth, SessionSupport sessions, ReturnUrlPolicy returns) {
        this.auth = auth;
        this.sessions = sessions;
        this.returns = returns;
    }

    @GetMapping("/login")
    public String login(@RequestParam MultiValueMap<String, String> parameters, Model model) {
        model.addAttribute("username", "");
        model.addAttribute("returnUrl", returnUrl(parameters));
        return "login";
    }

    @PostMapping("/login")
    public ModelAndView authenticate(@RequestParam MultiValueMap<String, String> parameters,
                                     HttpServletRequest request, Model model) {
        // A failed reauthentication must not leave an old usable identity behind.
        sessions.clear(request);
        model.addAttribute("currentUser", null);
        model.addAttribute("authenticated", false);
        Map<String, String> fields = new LinkedHashMap<>();
        String username = single(parameters, "username", fields);
        username = username == null ? "" : username.strip();
        int length = username.codePointCount(0, username.length());
        if (length < 1 || length > 50) fields.put("username", "请输入 1–50 个字符的用户名。");
        String password = single(parameters, "password", fields);
        if (password == null || password.isEmpty()) fields.put("password", "请输入密码。");
        String target = returnUrl(parameters);
        model.addAttribute("username", username);
        model.addAttribute("returnUrl", target);
        if (!fields.isEmpty()) {
            model.addAttribute("fieldErrors", fields);
            return new ModelAndView("login", model.asMap(), HttpStatus.BAD_REQUEST);
        }
        StoreUser user = auth.authenticate(username, password);
        if (user == null) {
            model.addAttribute("authError", FAILED);
            return new ModelAndView("login", model.asMap());
        }
        sessions.establish(request, user);
        return seeOther(target);
    }

    @PostMapping("/logout")
    public ModelAndView logout(HttpServletRequest request) {
        sessions.invalidate(request);
        return seeOther("/");
    }

    private ModelAndView seeOther(String target) {
        RedirectView view = new RedirectView(target, true);
        view.setStatusCode(HttpStatus.SEE_OTHER);
        view.setExposeModelAttributes(false);
        view.setExpandUriTemplateVariables(false);
        return new ModelAndView(view);
    }

    private String single(MultiValueMap<String, String> parameters, String name,
                          Map<String, String> errors) {
        List<String> values = parameters.get(name);
        if (values == null || values.size() != 1) {
            errors.put(name, "请为此字段填写一个值。");
            return null;
        }
        return values.get(0);
    }

    private String returnUrl(MultiValueMap<String, String> parameters) {
        List<String> values = parameters.get("returnUrl");
        return returns.resolve(values != null && values.size() == 1 ? values.get(0) : null, "/");
    }
}

