package org.csucampuscraft.admin.verification;
import org.csucampuscraft.admin.foundation.web.BusinessException;
import org.csucampuscraft.admin.foundation.web.HttpResponses;
import org.csucampuscraft.admin.foundation.validation.InputChecks;
import org.springframework.context.annotation.Profile;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.stereotype.Controller;
import org.springframework.ui.Model;
import org.springframework.web.bind.annotation.*;
import java.util.Map;
import java.util.concurrent.atomic.AtomicLong;

/** Nonpersistent probes for STEP02 acceptance. No production or business routes. */
@Controller
@Profile("verification")
@RequestMapping("/__verification")
public class FoundationVerificationController {
    private final AtomicLong acceptedPosts = new AtomicLong();

    @GetMapping("/foundation")
    public String foundation(@RequestParam(defaultValue = "普通文本") String text, Model model) {
        model.addAttribute("echoText", text);
        model.addAttribute("fieldErrors", Map.of("probeText", "请修改此验证字段"));
        return "verification/foundation";
    }

    @GetMapping("/errors/{status}")
    public String error(@PathVariable int status, @RequestParam(defaultValue = "验证请求无法完成") String text) {
        switch (status) {
            case 400, 403, 404, 409 -> throw new BusinessException(HttpStatus.valueOf(status),
                    "VERIFICATION_" + status, text);
            case 500 -> throw new IllegalStateException("VERIFICATION_SQL_PASSWORD_STACK_SENTINEL");
            default -> throw new BusinessException(HttpStatus.BAD_REQUEST, "VERIFICATION_STATUS",
                    "验证状态无效");
        }
    }

    @PostMapping("/submit")
    public ResponseEntity<Void> submit() {
        acceptedPosts.incrementAndGet();
        return HttpResponses.seeOther("/");
    }

    @GetMapping("/counter")
    @ResponseBody
    public Map<String, Long> counter() {
        return Map.of("acceptedPosts", acceptedPosts.get());
    }

    @GetMapping("/validation")
    @ResponseBody
    public Map<String, Object> validation(@RequestParam String kind, @RequestParam String value) {
        Object checked = switch (kind) {
            case "integer" -> InputChecks.integer("probeNumber", value, 0, 99);
            case "money" -> InputChecks.money("probeAmount", value);
            case "length" -> InputChecks.requiredText("probeText", value, 4);
            case "enum" -> InputChecks.enumeration("probeState", value, ProbeState.class);
            default -> throw new BusinessException(HttpStatus.BAD_REQUEST, "VERIFICATION_KIND",
                    "验证类型无效");
        };
        return Map.of("checked", checked.toString());
    }
    public enum ProbeState { FIRST, SECOND }
}
