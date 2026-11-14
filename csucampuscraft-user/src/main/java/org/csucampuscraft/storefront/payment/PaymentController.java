package org.csucampuscraft.storefront.payment;

import jakarta.servlet.http.HttpServletRequest;
import org.csucampuscraft.storefront.auth.SessionExpiredException;
import org.csucampuscraft.storefront.auth.SessionIdentity;
import org.csucampuscraft.storefront.auth.SessionSupport;
import org.csucampuscraft.storefront.foundation.web.BusinessException;
import org.csucampuscraft.storefront.order.OrderDetail;
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
public final class PaymentController {
    private final PaymentService payments;
    private final SessionSupport sessions;
    public PaymentController(PaymentService payments, SessionSupport sessions) {
        this.payments = payments;
        this.sessions = sessions;
    }

    @GetMapping("/orders/{orderNo}/payment")
    public ModelAndView page(@PathVariable("orderNo") String orderNo, HttpServletRequest request) {
        try {
            OrderDetail detail = payments.paymentPage(actor(request).userId(), orderNo);
            ModelAndView view = new ModelAndView("orders/payment");
            view.addObject("orderDetail", detail);
            view.addObject("paymentOrder", detail.getOrder());
            return view;
        } catch (BusinessException failure) {
            return conflict(orderNo, failure);
        }
    }

    @PostMapping("/orders/{orderNo}/payment")
    public ModelAndView pay(@PathVariable("orderNo") String orderNo,
                            @RequestParam MultiValueMap<String, String> parameters,
                            HttpServletRequest request, RedirectAttributes feedback) {
        try {
            OrderActionResult result = payments.pay(actor(request), orderNo, parameters);
            if (result == OrderActionResult.PAYMENT_FAILED) {
                feedback.addFlashAttribute("globalError", "本次模拟支付失败，订单仍待支付，可以重试或取消。");
            } else if (result == OrderActionResult.PAYMENT_ALREADY_SUCCEEDED) {
                feedback.addFlashAttribute("globalMessage", "该订单已支付，保留首次支付凭证和时间。");
            } else {
                feedback.addFlashAttribute("globalMessage", "模拟支付成功，订单待发货。此操作未进行真实付款。");
            }
            return redirect(orderNo);
        } catch (BusinessException failure) {
            return conflict(orderNo, failure);
        }
    }

    @PostMapping("/orders/{orderNo}/cancel")
    public ModelAndView cancel(@PathVariable("orderNo") String orderNo, HttpServletRequest request,
                               RedirectAttributes feedback) {
        try {
            OrderActionResult result = payments.cancel(actor(request), orderNo);
            feedback.addFlashAttribute("globalMessage", result == OrderActionResult.ORDER_ALREADY_CANCELLED
                    ? "该订单已取消，保留首次取消结果，未重复返还库存。"
                    : "订单已取消，库存已返还，商品不会放回购物车。");
            return redirect(orderNo);
        } catch (BusinessException failure) {
            return conflict(orderNo, failure);
        }
    }

    private SessionIdentity actor(HttpServletRequest request) {
        SessionIdentity identity = sessions.identity(request);
        if (identity == null) throw new SessionExpiredException();
        return identity;
    }
    private static ModelAndView redirect(String orderNo) {
        RedirectView redirect = new RedirectView("/orders/" + orderNo, true);
        redirect.setStatusCode(HttpStatus.SEE_OTHER);
        redirect.setExposeModelAttributes(false);
        return new ModelAndView(redirect);
    }
    private static ModelAndView conflict(String orderNo, BusinessException failure) {
        if (failure.getStatus() != HttpStatus.CONFLICT) throw failure;
        ModelAndView view = new ModelAndView("orders/action-conflict");
        view.setStatus(HttpStatus.CONFLICT);
        view.addObject("errorStatus", 409);
        view.addObject("errorCode", failure.getCode());
        view.addObject("errorMessage", failure.getMessage());
        view.addObject("orderNo", orderNo);
        return view;
    }
}
