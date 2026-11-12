# STEP02 代码变更清单

比较基线 022f50196ceb7b89880dabe1c369360e8f6136c3 与受测实现提交 5d9271d7e32634f947eb9f6077e7a4f3d98806a7。这里只列双端代码和资源，文档同步由后续归档提交单独记录。

共 50 个文件，database 与 assets 无变更。

## csucampuscraft-user

| 状态 | 文件 | 用途 |
| --- | --- | --- |
| A | `src/main/java/org/csucampuscraft/storefront/foundation/security/CsrfFilter.java` | 会话 CSRF、密码或返回地址边界 |
| A | `src/main/java/org/csucampuscraft/storefront/foundation/security/CsrfTokenService.java` | 会话 CSRF、密码或返回地址边界 |
| A | `src/main/java/org/csucampuscraft/storefront/foundation/security/PasswordService.java` | 会话 CSRF、密码或返回地址边界 |
| A | `src/main/java/org/csucampuscraft/storefront/foundation/security/ReturnUrlPolicy.java` | 会话 CSRF、密码或返回地址边界 |
| A | `src/main/java/org/csucampuscraft/storefront/foundation/validation/InputChecks.java` | 类型、长度、枚举与金额范围基础校验 |
| A | `src/main/java/org/csucampuscraft/storefront/foundation/view/ImagePaths.java` | 统一默认图片常量 |
| A | `src/main/java/org/csucampuscraft/storefront/foundation/web/BusinessException.java` | 公共模型、异常映射或 303 辅助 |
| A | `src/main/java/org/csucampuscraft/storefront/foundation/web/GlobalExceptionHandler.java` | 公共模型、异常映射或 303 辅助 |
| A | `src/main/java/org/csucampuscraft/storefront/foundation/web/HttpResponses.java` | 公共模型、异常映射或 303 辅助 |
| A | `src/main/java/org/csucampuscraft/storefront/foundation/web/PageModelAdvice.java` | 公共模型、异常映射或 303 辅助 |
| A | `src/main/java/org/csucampuscraft/storefront/verification/FoundationVerificationController.java` | 仅 verification profile 的无业务探针 |
| M | `src/main/resources/application.yml` | 关闭技术异常细节回显 |
| A | `src/main/resources/static/css/app.css` | 统一 UI Token 与渐进增强 |
| A | `src/main/resources/static/js/app.js` | 统一 UI Token 与渐进增强 |
| A | `src/main/resources/templates/error/400.html` | SSR 错误页 |
| A | `src/main/resources/templates/error/403.html` | SSR 错误页 |
| A | `src/main/resources/templates/error/404.html` | SSR 错误页 |
| A | `src/main/resources/templates/error/409.html` | SSR 错误页 |
| A | `src/main/resources/templates/error/500.html` | SSR 错误页 |
| A | `src/main/resources/templates/fragments/alerts.html` | 共享布局、字段、提示或图片片段 |
| A | `src/main/resources/templates/fragments/fields.html` | 共享布局、字段、提示或图片片段 |
| A | `src/main/resources/templates/fragments/images.html` | 共享布局、字段、提示或图片片段 |
| A | `src/main/resources/templates/fragments/layout.html` | 共享布局、字段、提示或图片片段 |
| M | `src/main/resources/templates/home.html` | 保留 M0 标记和主题的布局接入 |
| A | `src/main/resources/templates/verification/foundation.html` | 仅 verification profile 的无业务探针 |

## csucampuscraft-admin

| 状态 | 文件 | 用途 |
| --- | --- | --- |
| A | `src/main/java/org/csucampuscraft/admin/foundation/security/CsrfFilter.java` | 会话 CSRF、密码或返回地址边界 |
| A | `src/main/java/org/csucampuscraft/admin/foundation/security/CsrfTokenService.java` | 会话 CSRF、密码或返回地址边界 |
| A | `src/main/java/org/csucampuscraft/admin/foundation/security/PasswordService.java` | 会话 CSRF、密码或返回地址边界 |
| A | `src/main/java/org/csucampuscraft/admin/foundation/security/ReturnUrlPolicy.java` | 会话 CSRF、密码或返回地址边界 |
| A | `src/main/java/org/csucampuscraft/admin/foundation/validation/InputChecks.java` | 类型、长度、枚举与金额范围基础校验 |
| A | `src/main/java/org/csucampuscraft/admin/foundation/view/ImagePaths.java` | 统一默认图片常量 |
| A | `src/main/java/org/csucampuscraft/admin/foundation/web/BusinessException.java` | 公共模型、异常映射或 303 辅助 |
| A | `src/main/java/org/csucampuscraft/admin/foundation/web/GlobalExceptionHandler.java` | 公共模型、异常映射或 303 辅助 |
| A | `src/main/java/org/csucampuscraft/admin/foundation/web/HttpResponses.java` | 公共模型、异常映射或 303 辅助 |
| A | `src/main/java/org/csucampuscraft/admin/foundation/web/PageModelAdvice.java` | 公共模型、异常映射或 303 辅助 |
| A | `src/main/java/org/csucampuscraft/admin/verification/FoundationVerificationController.java` | 仅 verification profile 的无业务探针 |
| M | `src/main/resources/application.yml` | 关闭技术异常细节回显 |
| A | `src/main/resources/static/css/app.css` | 统一 UI Token 与渐进增强 |
| A | `src/main/resources/static/js/app.js` | 统一 UI Token 与渐进增强 |
| A | `src/main/resources/templates/error/400.html` | SSR 错误页 |
| A | `src/main/resources/templates/error/403.html` | SSR 错误页 |
| A | `src/main/resources/templates/error/404.html` | SSR 错误页 |
| A | `src/main/resources/templates/error/409.html` | SSR 错误页 |
| A | `src/main/resources/templates/error/500.html` | SSR 错误页 |
| A | `src/main/resources/templates/fragments/alerts.html` | 共享布局、字段、提示或图片片段 |
| A | `src/main/resources/templates/fragments/fields.html` | 共享布局、字段、提示或图片片段 |
| A | `src/main/resources/templates/fragments/images.html` | 共享布局、字段、提示或图片片段 |
| A | `src/main/resources/templates/fragments/layout.html` | 共享布局、字段、提示或图片片段 |
| M | `src/main/resources/templates/home.html` | 保留 M0 标记和主题的布局接入 |
| A | `src/main/resources/templates/verification/foundation.html` | 仅 verification profile 的无业务探针 |
