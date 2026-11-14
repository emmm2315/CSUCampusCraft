package org.csucampuscraft.storefront.order;

import jakarta.servlet.http.HttpServletRequest;
import java.util.Map;
import java.util.Set;
import org.csucampuscraft.storefront.auth.SessionExpiredException;
import org.csucampuscraft.storefront.auth.SessionIdentity;
import org.csucampuscraft.storefront.auth.SessionSupport;
import org.csucampuscraft.storefront.foundation.web.BusinessException;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Controller;
import org.springframework.util.MultiValueMap;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.servlet.ModelAndView;

@Controller
public final class OrderController {
    private final OrderService orders;
    private final SessionSupport sessions;
    public OrderController(OrderService orders, SessionSupport sessions) {
        this.orders = orders;
        this.sessions = sessions;
    }
    @GetMapping("/orders")
    public ModelAndView list(@RequestParam MultiValueMap<String, String> parameters,
                             HttpServletRequest request) {
        for (String field : Set.of("orderNo", "status", "page", "size")) {
            if (parameters.containsKey(field) && parameters.get(field).size() != 1) {
                throw new BusinessException(HttpStatus.BAD_REQUEST, "DUPLICATE_QUERY_FIELD",
                        "查询字段只能提交一个值。", Map.of(field, "请只提交一个值。"));
            }
        }
        OrderQuery query = OrderQuery.bind(parameters.getFirst("orderNo"), parameters.getFirst("status"),
                parameters.getFirst("page"), parameters.getFirst("size"));
        ModelAndView view = new ModelAndView("orders/index");
        view.addObject("orderPage", orders.page(actor(request).userId(), query));
        view.addObject("orderQuery", query);
        view.addObject("orderStatuses", OrderStatus.values());
        return view;
    }
    @GetMapping("/orders/{orderNo}")
    public ModelAndView detail(@PathVariable("orderNo") String orderNo, HttpServletRequest request) {
        ModelAndView view = new ModelAndView("orders/detail");
        view.addObject("orderDetail", orders.detail(actor(request).userId(), orderNo));
        return view;
    }
    private SessionIdentity actor(HttpServletRequest request) {
        SessionIdentity actor = sessions.identity(request);
        if (actor == null) throw new SessionExpiredException();
        return actor;
    }
}
