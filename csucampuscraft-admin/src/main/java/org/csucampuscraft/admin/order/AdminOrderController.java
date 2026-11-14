package org.csucampuscraft.admin.order;

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
public final class AdminOrderController {
    private final AdminOrderService orders;
    private final SessionSupport sessions;
    public AdminOrderController(AdminOrderService orders, SessionSupport sessions) {
        this.orders = orders;
        this.sessions = sessions;
    }

    @GetMapping("/orders")
    public ModelAndView list(@RequestParam MultiValueMap<String, String> parameters) {
        for (String field : Set.of("orderNo", "status", "userId", "page", "size")) {
            if (parameters.containsKey(field) && parameters.get(field).size() != 1) {
                throw new BusinessException(HttpStatus.BAD_REQUEST, "DUPLICATE_QUERY_FIELD",
                        "查询字段只能提交一个值。", Map.of(field, "请只提交一个值。"));
            }
        }
        OrderQuery query = OrderQuery.bind(parameters.getFirst("orderNo"), parameters.getFirst("status"),
                parameters.getFirst("userId"), parameters.getFirst("page"), parameters.getFirst("size"));
        OrderPage page = orders.page(query);
        ModelAndView view = new ModelAndView("orders/index");
        view.addObject("orderPage", page);
        view.addObject("orderQuery", query);
        view.addObject("orderStatuses", OrderStatus.values());
        view.addObject("selectedCustomer", page.getSelectedCustomer());
        return view;
    }

    @GetMapping("/orders/{orderNo}")
    public ModelAndView detail(@PathVariable("orderNo") String orderNo) {
        ModelAndView view = new ModelAndView("orders/detail");
        view.addObject("orderDetail", orders.detail(orderNo));
        return view;
    }

    @PostMapping("/orders/{orderNo}/ship")
    public ModelAndView ship(@PathVariable("orderNo") String orderNo, HttpServletRequest request,
                             RedirectAttributes feedback) {
        try {
            ShipmentResult result = orders.ship(actor(request), orderNo);
            feedback.addFlashAttribute("globalMessage", result == ShipmentResult.SHIPPED
                    ? "模拟发货已登记，请核对首次发货时间。本操作不涉及真实物流。"
                    : "该订单已发货或已完成，保留首次发货结果，未重复改写时间。");
            RedirectView redirect = new RedirectView("/orders/" + orderNo, true);
            redirect.setStatusCode(HttpStatus.SEE_OTHER);
            redirect.setExposeModelAttributes(false);
            return new ModelAndView(redirect);
        } catch (BusinessException failure) {
            if (failure.getStatus() != HttpStatus.CONFLICT) throw failure;
            ModelAndView view = new ModelAndView("orders/action-conflict");
            view.setStatus(HttpStatus.CONFLICT);
            view.addObject("errorStatus", 409);
            view.addObject("errorCode", failure.getCode());
            view.addObject("errorMessage", failure.getMessage());
            view.addObject("orderNo", orderNo != null && orderNo.matches("[A-Za-z0-9_-]{1,40}") ? orderNo : null);
            return view;
        }
    }
    private SessionIdentity actor(HttpServletRequest request) {
        SessionIdentity actor = sessions.identity(request);
        if (actor == null) throw new SessionExpiredException();
        return actor;
    }
}
