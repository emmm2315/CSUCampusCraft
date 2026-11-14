package org.csucampuscraft.storefront.checkout;

import jakarta.servlet.http.HttpServletRequest;
import java.util.Map;
import org.csucampuscraft.storefront.foundation.web.BusinessException;
import org.csucampuscraft.storefront.order.OrderSubmissionCoordinator;
import org.csucampuscraft.storefront.order.OrderSubmissionResult;
import org.springframework.web.servlet.view.RedirectView;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Controller;
import org.springframework.util.MultiValueMap;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.servlet.ModelAndView;

/** U06 confirmation and the real atomic order-submission boundary. */
@Controller
public final class CheckoutController {
    private final CheckoutService checkout;

    private final OrderSubmissionCoordinator submissions;

    public CheckoutController(CheckoutService checkout, OrderSubmissionCoordinator submissions) {
        this.checkout = checkout;
        this.submissions = submissions;
    }

    @GetMapping("/checkout")
    public ModelAndView page(HttpServletRequest request) {
        try {
            return form(checkout.prepare(request), ShippingForm.empty(), Map.of());
        } catch (BusinessException failure) {
            return conflict(failure);
        }
    }

    @PostMapping("/orders")
    public ModelAndView submit(@RequestParam MultiValueMap<String, String> parameters,
                               HttpServletRequest request) {
        try {
            OrderSubmissionResult result = submissions.submit(request, parameters);
            if (!result.isCreated()) {
                CheckoutService.Validation invalid = result.getValidation();
                return form(invalid.confirmation(), invalid.form(), invalid.fieldErrors());
            }
            RedirectView redirect = new RedirectView("/orders/" + result.getOrderNo(), true);
            redirect.setStatusCode(HttpStatus.SEE_OTHER);
            redirect.setExposeModelAttributes(false);
            return new ModelAndView(redirect);
        } catch (BusinessException failure) {
            return conflict(failure);
        }
    }

    private static ModelAndView form(CheckoutConfirmation confirmation, ShippingForm form,
                                     Map<String, String> errors) {
        ModelAndView view = new ModelAndView("checkout/index");
        view.addObject("checkout", confirmation);
        view.addObject("confirmationToken", confirmation.token());
        view.addObject("checkoutForm", form);
        view.addObject("fieldErrors", errors);
        view.addObject("errorAnchors", errors);
        if (!errors.isEmpty()) {
            view.setStatus(HttpStatus.BAD_REQUEST);
            view.addObject("errorStatus", 400);
            view.addObject("errorCode", "INVALID_SHIPPING_FIELDS");
            view.addObject("globalError", "请修正收货信息后再次提交，仍有效的确认可以继续使用。");
        }
        return view;
    }

    private static ModelAndView conflict(BusinessException failure) {
        if (failure.getStatus() != HttpStatus.CONFLICT) throw failure;
        ModelAndView view = new ModelAndView("checkout/conflict");
        view.setStatus(HttpStatus.CONFLICT);
        view.addObject("errorStatus", 409);
        view.addObject("errorCode", failure.getCode());
        view.addObject("errorMessage", failure.getMessage());
        view.addObject("canRetryConfirmation", true);
        view.addObject("tokenPreserved", false);
        return view;
    }
}
