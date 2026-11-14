package org.csucampuscraft.admin.customer;

import jakarta.servlet.http.HttpServletRequest;
import java.util.Map;
import java.util.Set;
import org.csucampuscraft.admin.auth.SessionExpiredException;
import org.csucampuscraft.admin.auth.SessionIdentity;
import org.csucampuscraft.admin.auth.SessionSupport;
import org.csucampuscraft.admin.foundation.web.BusinessException;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Controller;
import org.springframework.util.MultiValueMap;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.servlet.ModelAndView;
import org.springframework.web.servlet.mvc.support.RedirectAttributes;
import org.springframework.web.servlet.view.RedirectView;

@Controller
public final class CustomerController {
    private final CustomerService customers;
    private final SessionSupport sessions;
    public CustomerController(CustomerService customers, SessionSupport sessions) {
        this.customers = customers;
        this.sessions = sessions;
    }
    @GetMapping("/customers")
    public ModelAndView list(@RequestParam MultiValueMap<String, String> parameters) {
        for (String field : Set.of("q", "status", "page", "size")) {
            if (parameters.containsKey(field) && parameters.get(field).size() != 1) {
                throw new BusinessException(HttpStatus.BAD_REQUEST, "DUPLICATE_QUERY_FIELD",
                        "查询字段只能提交一个值。", Map.of(field, "请只提交一个值。"));
            }
        }
        CustomerQuery query = CustomerQuery.bind(parameters.getFirst("q"), parameters.getFirst("status"),
                parameters.getFirst("page"), parameters.getFirst("size"));
        ModelAndView view = new ModelAndView("customers/index");
        view.addObject("customerPage", customers.page(query));
        view.addObject("customerQuery", query);
        view.addObject("customerStatuses", CustomerStatus.values());
        return view;
    }
    @GetMapping("/customers/{userId}")
    public ModelAndView detail(@PathVariable("userId") String userId) {
        return new ModelAndView("customers/detail", "customer", customers.detail(userId));
    }
    @PostMapping("/customers/{userId}/status")
    public ModelAndView status(@PathVariable("userId") String userId, @RequestParam MultiValueMap<String, String> parameters,
                               HttpServletRequest request, RedirectAttributes feedback) {
        try {
            CustomerStatusResult result = customers.changeStatus(actor(request), userId, parameters.get("targetStatus"));
            feedback.addFlashAttribute("globalMessage", result == CustomerStatusResult.CHANGED
                    ? "顾客状态已更新。真实切换后的既有会话需重新登录，购物车与历史订单保留。"
                    : "顾客已处于目标状态，未重复更新状态或时间。");
            RedirectView redirect = new RedirectView("/customers/" + Long.parseLong(userId.strip()), true);
            redirect.setStatusCode(HttpStatus.SEE_OTHER);
            redirect.setExposeModelAttributes(false);
            return new ModelAndView(redirect);
        } catch (BusinessException failure) {
            if (failure.getStatus() != HttpStatus.BAD_REQUEST && failure.getStatus() != HttpStatus.CONFLICT) throw failure;
            ModelAndView view = new ModelAndView("customers/action-conflict");
            view.setStatus(failure.getStatus());
            view.addObject("errorStatus", failure.getStatus().value());
            view.addObject("errorCode", failure.getCode());
            view.addObject("errorMessage", failure.getMessage());
            view.addObject("fieldErrors", failure.getFieldErrors());
            view.addObject("userId", safeId(userId));
            return view;
        }
    }
    private SessionIdentity actor(HttpServletRequest request) {
        SessionIdentity actor = sessions.identity(request);
        if (actor == null) throw new SessionExpiredException();
        return actor;
    }
    private static Long safeId(String value) {
        try {
            String stripped = value == null ? "" : value.strip();
            if (!stripped.matches("[0-9]+")) return null;
            long id = Long.parseLong(stripped);
            return id > 0 ? id : null;
        } catch (NumberFormatException invalid) { return null; }
    }
}
