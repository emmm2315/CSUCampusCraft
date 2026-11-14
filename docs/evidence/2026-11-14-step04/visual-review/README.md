# STEP04 截图视觉复核

受测代码：`74e6272e5b60ac1604964f7e50909f4a1490086f`；完整通过轮次：`attempt4`。56 张 PNG（1366×768 与 1920×1080 各 28 张）均已逐张用 view_image 打开查看，未发现阻断排版、遮挡、横向溢出、状态缺失或可见秘密文本。每图路径、SHA-256、视口、实际尺寸、观察及自动浏览器数据见 [final-step04.json](final-step04.json)。

本复核由 Codex 辅助执行，不替代组员交叉复核。会话更换、认证戳、身份/CSRF顺序、数据库只读结论须看真实 HTTP、原生会话探针和 SQL 记录；截图本身仅证明可见结果。303 行记录的是提交响应，截图是跟随后的 GET；字段400浏览器场景用 noValidate 触发服务端校验。完整页面高度超过视口时属于正常纵向滚动。

旧失败 attempt3 的6张抽查保留在 [interim-attempt3.json](interim-attempt3.json)，没有混入本轮56张计数。

| 图片 | 视口 | 可见观察 |
| --- | --- | --- |
| [admin-before-correct-1366.png](../attempt4/browser/admin-before-correct-1366.png) | 1366×768 | 管理端登录准备页：空用户名与密码、标题和登录按钮均清楚，页头为登录入口。 |
| [admin-before-correct-1920.png](../attempt4/browser/admin-before-correct-1920.png) | 1920×1080 | 管理端登录准备页：空用户名与密码、标题和登录按钮均清楚，页头为登录入口。 |
| [admin-before-csrf-rejection-1366.png](../attempt4/browser/admin-before-csrf-rejection-1366.png) | 1366×768 | 管理端 CSRF 试验前登录页：空输入、管理员说明和登录按钮可读。 |
| [admin-before-csrf-rejection-1920.png](../attempt4/browser/admin-before-csrf-rejection-1920.png) | 1920×1080 | 管理端 CSRF 试验前登录页：空输入、管理员说明和登录按钮可读。 |
| [admin-before-invalid-fields-1366.png](../attempt4/browser/admin-before-invalid-fields-1366.png) | 1366×768 | 管理端字段校验前登录页：用户名/密码标签及空输入可读，匿名页头未显示旧身份。 |
| [admin-before-invalid-fields-1920.png](../attempt4/browser/admin-before-invalid-fields-1920.png) | 1920×1080 | 管理端字段校验前登录页：用户名/密码标签及空输入可读，匿名页头未显示旧身份。 |
| [admin-before-logout-1366.png](../attempt4/browser/admin-before-logout-1366.png) | 1366×768 | 管理端退出前：初始化五主题页保持，页头显示商城管理员与退出控件，无明显遮挡。 |
| [admin-before-logout-1920.png](../attempt4/browser/admin-before-logout-1920.png) | 1920×1080 | 管理端退出前：初始化五主题页保持，页头显示商城管理员与退出控件，无明显遮挡。 |
| [admin-fields-400-1366.png](../attempt4/browser/admin-fields-400-1366.png) | 1366×768 | 管理端字段400：用户名admin保留，密码为空；错误摘要和密码行内提示可读，按钮可操作。 |
| [admin-fields-400-1920.png](../attempt4/browser/admin-fields-400-1920.png) | 1920×1080 | 管理端字段400：用户名admin保留，密码为空；错误摘要和密码行内提示可读，按钮可操作。 |
| [admin-logged-in-1366.png](../attempt4/browser/admin-logged-in-1366.png) | 1366×768 | 管理端登录后：初始化主题页保留五主题，显示商城管理员和退出按钮，未显示未开发控制台内容。 |
| [admin-logged-in-1920.png](../attempt4/browser/admin-logged-in-1920.png) | 1920×1080 | 管理端登录后：初始化主题页保留五主题，显示商城管理员和退出按钮，未显示未开发控制台内容。 |
| [admin-logged-out-1366.png](../attempt4/browser/admin-logged-out-1366.png) | 1366×768 | 管理端退出后：回到空登录表单，页头无旧管理员名或退出控件。 |
| [admin-logged-out-1920.png](../attempt4/browser/admin-logged-out-1920.png) | 1920×1080 | 管理端退出后：回到空登录表单，页头无旧管理员名或退出控件。 |
| [admin-login-1366.png](../attempt4/browser/admin-login-1366.png) | 1366×768 | 管理端初始登录页：应用身份、管理员登录说明、字段标签和按钮清楚，输入为空。 |
| [admin-login-1920.png](../attempt4/browser/admin-login-1920.png) | 1920×1080 | 管理端初始登录页：应用身份、管理员登录说明、字段标签和按钮清楚，输入为空。 |
| [admin-login-csrf-403-1366.png](../attempt4/browser/admin-login-csrf-403-1366.png) | 1366×768 | 管理端 CSRF 403：状态/安全提示/返回入口可读，无堆栈、SQL或秘密文本；匿名页头为登录入口。 |
| [admin-login-csrf-403-1920.png](../attempt4/browser/admin-login-csrf-403-1920.png) | 1920×1080 | 管理端 CSRF 403：状态/安全提示/返回入口可读，无堆栈、SQL或秘密文本；匿名页头为登录入口。 |
| [admin-survives-user-logout-1366.png](../attempt4/browser/admin-survives-user-logout-1366.png) | 1366×768 | 用户端退出后管理端画面：管理员名称和退出控件仍在，五主题正常展示。 |
| [admin-survives-user-logout-1920.png](../attempt4/browser/admin-survives-user-logout-1920.png) | 1920×1080 | 用户端退出后管理端画面：管理员名称和退出控件仍在，五主题正常展示。 |
| [admin-unimplemented-404-1366.png](../attempt4/browser/admin-unimplemented-404-1366.png) | 1366×768 | 管理端未实现页：404状态与恢复入口可读，保留已认证管理员导航；未渲染业务列表。 |
| [admin-unimplemented-404-1920.png](../attempt4/browser/admin-unimplemented-404-1920.png) | 1920×1080 | 管理端未实现页：404状态与恢复入口可读，保留已认证管理员导航；未渲染业务列表。 |
| [admin-wrong-password-1366.png](../attempt4/browser/admin-wrong-password-1366.png) | 1366×768 | 管理端凭证失败：统一拒绝文案，用户名admin回显、密码空；未出现可用旧身份导航。 |
| [admin-wrong-password-1920.png](../attempt4/browser/admin-wrong-password-1920.png) | 1920×1080 | 管理端凭证失败：统一拒绝文案，用户名admin回显、密码空；未出现可用旧身份导航。 |
| [user-before-correct-1366.png](../attempt4/browser/user-before-correct-1366.png) | 1366×768 | 用户端登录准备页：表单与提示可读，用户名/密码空，页头为游客登录入口。 |
| [user-before-correct-1920.png](../attempt4/browser/user-before-correct-1920.png) | 1920×1080 | 用户端登录准备页：表单与提示可读，用户名/密码空，页头为游客登录入口。 |
| [user-before-csrf-rejection-1366.png](../attempt4/browser/user-before-csrf-rejection-1366.png) | 1366×768 | 已登录用户再次打开登录页：林同学及退出控件可见，登录表单仍空，导航没有挤压遮挡。 |
| [user-before-csrf-rejection-1920.png](../attempt4/browser/user-before-csrf-rejection-1920.png) | 1920×1080 | 已登录用户再次打开登录页：林同学及退出控件可见，登录表单仍空，导航没有挤压遮挡。 |
| [user-before-invalid-fields-1366.png](../attempt4/browser/user-before-invalid-fields-1366.png) | 1366×768 | 用户端字段校验前登录页：字段空、标签清楚，登录和返回首页入口可见。 |
| [user-before-invalid-fields-1920.png](../attempt4/browser/user-before-invalid-fields-1920.png) | 1920×1080 | 用户端字段校验前登录页：字段空、标签清楚，登录和返回首页入口可见。 |
| [user-before-logout-1366.png](../attempt4/browser/user-before-logout-1366.png) | 1366×768 | 用户端退出前：首页目录和毕业入口正常，页头林同学/退出控件可见，徽标仍为本步固定0。 |
| [user-before-logout-1920.png](../attempt4/browser/user-before-logout-1920.png) | 1920×1080 | 用户端退出前：首页目录和毕业入口正常，页头林同学/退出控件可见，徽标仍为本步固定0。 |
| [user-before-script-name-1366.png](../attempt4/browser/user-before-script-name-1366.png) | 1366×768 | 脚本用户名试验前：用户登录页正常，字段空，未残留前次输入。 |
| [user-before-script-name-1920.png](../attempt4/browser/user-before-script-name-1920.png) | 1920×1080 | 脚本用户名试验前：用户登录页正常，字段空，未残留前次输入。 |
| [user-escaped-username-1366.png](../attempt4/browser/user-escaped-username-1366.png) | 1366×768 | 脚本样式用户名以字面文字呈现在输入中；统一失败提示可读、密码空，无脚本界面或异常覆盖。 |
| [user-escaped-username-1920.png](../attempt4/browser/user-escaped-username-1920.png) | 1920×1080 | 脚本样式用户名以字面文字呈现在输入中；统一失败提示可读、密码空，无脚本界面或异常覆盖。 |
| [user-fields-400-1366.png](../attempt4/browser/user-fields-400-1366.png) | 1366×768 | 用户端字段400：用户名摘要和行内错误清楚，密码空，登录/返回首页入口可见；允许正常纵向滚动。 |
| [user-fields-400-1920.png](../attempt4/browser/user-fields-400-1920.png) | 1920×1080 | 用户端字段400：用户名摘要和行内错误清楚，密码空，登录/返回首页入口可见；允许正常纵向滚动。 |
| [user-logged-in-1366.png](../attempt4/browser/user-logged-in-1366.png) | 1366×768 | 用户端登录后：首页目录保持，显示林同学及退出控件，徽标0，无明显溢出。 |
| [user-logged-in-1920.png](../attempt4/browser/user-logged-in-1920.png) | 1920×1080 | 用户端登录后：首页目录保持，显示林同学及退出控件，徽标0，无明显溢出。 |
| [user-logged-in-again-1366.png](../attempt4/browser/user-logged-in-again-1366.png) | 1366×768 | 用户端再次登录后：姓名/退出控件恢复，目录和毕业专区外观保持，徽标0。 |
| [user-logged-in-again-1920.png](../attempt4/browser/user-logged-in-again-1920.png) | 1920×1080 | 用户端再次登录后：姓名/退出控件恢复，目录和毕业专区外观保持，徽标0。 |
| [user-logged-out-1366.png](../attempt4/browser/user-logged-out-1366.png) | 1366×768 | 用户端退出后：首页仍可浏览，页头回到登录入口，林同学与退出控件消失，徽标0。 |
| [user-logged-out-1920.png](../attempt4/browser/user-logged-out-1920.png) | 1920×1080 | 用户端退出后：首页仍可浏览，页头回到登录入口，林同学与退出控件消失，徽标0。 |
| [user-login-1366.png](../attempt4/browser/user-login-1366.png) | 1366×768 | 用户端初始登录页：标题/应用标识/字段标签清楚，输入空，登录和返回首页入口可见。 |
| [user-login-1920.png](../attempt4/browser/user-login-1920.png) | 1920×1080 | 用户端初始登录页：标题/应用标识/字段标签清楚，输入空，登录和返回首页入口可见。 |
| [user-login-again-1366.png](../attempt4/browser/user-login-again-1366.png) | 1366×768 | 用户端再次进入登录页：字段空、游客登录入口可见，没有旧身份残留。 |
| [user-login-again-1920.png](../attempt4/browser/user-login-again-1920.png) | 1920×1080 | 用户端再次进入登录页：字段空、游客登录入口可见，没有旧身份残留。 |
| [user-login-csrf-403-1366.png](../attempt4/browser/user-login-csrf-403-1366.png) | 1366×768 | 用户端 CSRF 403：错误状态/安全提示/恢复入口清楚；原有效用户导航仍可见，未显示秘密值。 |
| [user-login-csrf-403-1920.png](../attempt4/browser/user-login-csrf-403-1920.png) | 1920×1080 | 用户端 CSRF 403：错误状态/安全提示/恢复入口清楚；原有效用户导航仍可见，未显示秘密值。 |
| [user-survives-admin-logout-1366.png](../attempt4/browser/user-survives-admin-logout-1366.png) | 1366×768 | 管理端退出后用户端画面：林同学/退出控件仍在，目录保持；这只是隔离场景的可见结果，完整身份依据见HTTP/探针。 |
| [user-survives-admin-logout-1920.png](../attempt4/browser/user-survives-admin-logout-1920.png) | 1920×1080 | 管理端退出后用户端画面：林同学/退出控件仍在，目录保持；这只是隔离场景的可见结果，完整身份依据见HTTP/探针。 |
| [user-unimplemented-404-1366.png](../attempt4/browser/user-unimplemented-404-1366.png) | 1366×768 | 用户端未实现页：404提示与返回首页入口清楚，已认证导航保持，未显示购物车内容。 |
| [user-unimplemented-404-1920.png](../attempt4/browser/user-unimplemented-404-1920.png) | 1920×1080 | 用户端未实现页：404提示与返回首页入口清楚，已认证导航保持，未显示购物车内容。 |
| [user-wrong-password-1366.png](../attempt4/browser/user-wrong-password-1366.png) | 1366×768 | 用户端凭证失败：统一拒绝文案，alice回显、密码空；页头为游客登录入口。 |
| [user-wrong-password-1920.png](../attempt4/browser/user-wrong-password-1920.png) | 1920×1080 | 用户端凭证失败：统一拒绝文案，alice回显、密码空；页头为游客登录入口。 |
