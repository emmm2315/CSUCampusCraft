package org.csucampuscraft.admin.dashboard;

import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Controller;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.servlet.ModelAndView;

/** Replaces the initialization root reader; authorization remains in the existing AuthFilter. */
@Controller
public final class DashboardController {
    private final DashboardService dashboard;
    public DashboardController(DashboardService dashboard) { this.dashboard = dashboard; }
    @GetMapping("/")
    public ModelAndView home() {
        try {
            return new ModelAndView("home", "dashboardSummary", dashboard.summary());
        } catch (RuntimeException unavailable) {
            ModelAndView view = new ModelAndView("dashboard-error");
            view.setStatus(HttpStatus.INTERNAL_SERVER_ERROR);
            view.addObject("errorStatus", 500);
            view.addObject("errorCode", "DASHBOARD_QUERY_FAILED");
            view.addObject("errorMessage", "控制台暂时无法读取统计，请稍后重试。");
            return view;
        }
    }
}
