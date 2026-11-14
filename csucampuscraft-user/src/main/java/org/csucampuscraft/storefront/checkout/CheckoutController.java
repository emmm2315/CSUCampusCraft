package org.csucampuscraft.storefront.checkout;

import jakarta.servlet.http.HttpServletRequest;
import java.util.Map;
import org.csucampuscraft.storefront.foundation.web.BusinessException;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Controller;
import org.springframework.util.MultiValueMap;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.servlet.ModelAndView;

/** U06 and a validation-only POST boundary, replaced by the real transaction in STEP09. */
@Controller
public final class CheckoutController {
    private final CheckoutService checkout;

    public CheckoutController(CheckoutService checkout) { this.checkout = checkout; }

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
            CheckoutService.Validation result = checkout.validate(request, parameters);
            if (!result.isValid()) return form(result.confirmation(), result.form(), result.fieldErrors());
            // This is not a successful submission: retain the valid confirmation, never write an order.
            return conflict(new BusinessException(HttpStatus.CONFLICT, "ORDER_SUBMISSION_PENDING",
                    "下单将在 STEP09 接入。本次仅完成确认校验，未生成订单，购物车和库存保持原状。"));
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
        view.addObject("tokenPreserved", "ORDER_SUBMISSION_PENDING".equals(failure.getCode()));
        return view;
    }
}
