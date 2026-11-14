package org.csucampuscraft.admin.dashboard;

import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
public class DashboardService {
    private final DashboardMapper dashboard;
    public DashboardService(DashboardMapper dashboard) { this.dashboard = dashboard; }
    @Transactional(readOnly = true)
    public DashboardSummary summary() {
        DashboardSummary result = dashboard.selectSummary();
        if (result == null) throw new IllegalStateException("Dashboard statistics unavailable");
        return result;
    }
}
