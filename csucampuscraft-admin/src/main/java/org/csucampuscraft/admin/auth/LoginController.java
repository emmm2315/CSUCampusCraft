package org.csucampuscraft.admin.auth;

import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import java.util.LinkedHashMap;
import java.util.Map;
import org.csucampuscraft.admin.foundation.security.ReturnUrlPolicy;
import org.csucampuscraft.admin.foundation.validation.InputChecks;
import org.csucampuscraft.admin.foundation.web.BusinessException;
import org.csucampuscraft.admin.foundation.web.PageModelAdvice;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Controller;
import org.springframework.ui.Model;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.servlet.view.RedirectView;
import org.springframework.web.servlet.ModelAndView;

@Controller
public final class LoginController {
    public static final String FAILURE_MESSAGE = "用户名或密码不正确，或账号不可用于本端登录。";
    private final AuthService auth;
    private final SessionSupport sessions;
    private final ReturnUrlPolicy returns;
    private final PageModelAdvice pageModels;

    public LoginController(AuthService auth, SessionSupport sessions, ReturnUrlPolicy returns,
                           PageModelAdvice pageModels) {
        this.auth = auth;
        this.sessions = sessions;
        this.returns = returns;
        this.pageModels = pageModels;
    }

    @GetMapping("/login")
    public String loginPage(HttpServletRequest request, Model model) {
        model.addAttribute("username", "");
        model.addAttribute("returnUrl", returnUrl(request));
        model.addAttribute("loginError", null);
        return "login";
    }

    @PostMapping("/login")
    public ModelAndView login(HttpServletRequest request, HttpServletResponse response, Model model) {
        // CsrfFilter has already accepted this POST. Failed re-login cannot retain an old identity.
        sessions.clear(request);
        model.addAllAttributes(pageModels.commonModel(request));
        Map<String, String> fields = new LinkedHashMap<>();
        String rawUsername = one(request, "username", fields);
        String rawPassword = one(request, "password", fields);
        String username = rawUsername == null ? "" : rawUsername.strip();
        if (!fields.containsKey("username")) {
            try {
                username = InputChecks.requiredText("username", rawUsername, 50);
            } catch (BusinessException invalid) {
                fields.putAll(invalid.getFieldErrors());
            }
        }
        if (!fields.containsKey("password") && (rawPassword == null || rawPassword.isEmpty())) {
            fields.put("password", "请填写密码。");
        }
        String target = returnUrl(request);
        model.addAttribute("username", username);
        model.addAttribute("returnUrl", target);
        model.addAttribute("loginError", null);
        if (!fields.isEmpty()) {
            response.setStatus(HttpServletResponse.SC_BAD_REQUEST);
            model.addAttribute("fieldErrors", fields);
            ModelAndView invalid = new ModelAndView("login", model.asMap());
            invalid.setStatus(HttpStatus.BAD_REQUEST);
            return invalid;
        }
        StoreUser user = auth.authenticate(username, rawPassword);
        if (user == null) {
            model.addAttribute("loginError", FAILURE_MESSAGE);
            return new ModelAndView("login", model.asMap());
        }
        sessions.establish(request, user);
        RedirectView redirect = new RedirectView(target, true);
        redirect.setStatusCode(HttpStatus.SEE_OTHER);
        redirect.setExposeModelAttributes(false);
        return new ModelAndView(redirect);
    }

    @PostMapping("/logout")
    public RedirectView logout(HttpServletRequest request) {
        sessions.invalidate(request);
        // Fixed internal destination, intentionally not a user-supplied returnUrl.
        RedirectView redirect = new RedirectView("/login", true);
        redirect.setStatusCode(HttpStatus.SEE_OTHER);
        redirect.setExposeModelAttributes(false);
        return redirect;
    }

    private String one(HttpServletRequest request, String name, Map<String, String> fields) {
        String[] values = request.getParameterValues(name);
        if (values == null) return null;
        if (values.length != 1) {
            fields.put(name, "每个字段只能提交一个值。");
            return null;
        }
        return values[0];
    }

    private String returnUrl(HttpServletRequest request) {
        String[] values = request.getParameterValues("returnUrl");
        return returns.resolve(values != null && values.length == 1 ? values[0] : null, "/");
    }
}
