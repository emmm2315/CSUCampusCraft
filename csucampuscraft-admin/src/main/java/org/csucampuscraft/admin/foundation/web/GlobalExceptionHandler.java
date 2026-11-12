package org.csucampuscraft.admin.foundation.web;

import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import java.io.IOException;
import java.util.LinkedHashMap;
import java.util.Map;
import org.springframework.beans.TypeMismatchException;
import org.springframework.http.HttpStatus;
import org.springframework.http.converter.HttpMessageNotReadableException;
import org.springframework.validation.BindException;
import org.springframework.web.ErrorResponse;
import org.springframework.web.bind.ServletRequestBindingException;
import org.springframework.web.bind.annotation.ControllerAdvice;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.servlet.ModelAndView;

/** Maps expected failures without reflecting submitted values or technical exception messages. */
@ControllerAdvice
public final class GlobalExceptionHandler {
    private final PageModelAdvice pageModels;

    public GlobalExceptionHandler(PageModelAdvice pageModels) { this.pageModels = pageModels; }

    @ExceptionHandler(BusinessException.class)
    public ModelAndView business(BusinessException exception, HttpServletRequest request) {
        return page(request, exception.getStatus(), exception.getCode(), exception.getMessage(),
                exception.getFieldErrors());
    }

    @ExceptionHandler(BindException.class)
    public ModelAndView binding(BindException exception, HttpServletRequest request) {
        Map<String, String> fields = new LinkedHashMap<>();
        exception.getBindingResult().getFieldErrors().forEach(error ->
                fields.putIfAbsent(error.getField(), "请检查输入格式与范围。"));
        return page(request, HttpStatus.BAD_REQUEST, "INVALID_FIELDS", "请检查并修正表单内容。", fields);
    }

    @ExceptionHandler({TypeMismatchException.class, ServletRequestBindingException.class,
            HttpMessageNotReadableException.class})
    public ModelAndView parameters(Exception exception, HttpServletRequest request) {
        return page(request, HttpStatus.BAD_REQUEST, "INVALID_REQUEST", "请求参数不完整或格式不正确。", Map.of());
    }

    @ExceptionHandler(Exception.class)
    public ModelAndView unexpected(Exception exception, HttpServletRequest request,
                                   HttpServletResponse response) throws IOException {
        if (exception instanceof ErrorResponse failure) {
            int status = failure.getStatusCode().value();
            if (status == 400) {
                return page(request, HttpStatus.BAD_REQUEST, "INVALID_REQUEST", "请求参数不完整或格式不正确。", Map.of());
            }
            if (status == 403) {
                return page(request, HttpStatus.FORBIDDEN, "ACCESS_DENIED", "当前请求无法执行。", Map.of());
            }
            if (status == 404) {
                return page(request, HttpStatus.NOT_FOUND, "RESOURCE_NOT_FOUND", "未找到请求的页面或资源。", Map.of());
            }
            if (status == 409) {
                return page(request, HttpStatus.CONFLICT, "REQUEST_CONFLICT", "页面数据已变化，请刷新后重新确认。", Map.of());
            }
            if (status >= 400 && status < 500) {
                // Preserve framework statuses such as 405/415 through Boot's /error fallback.
                response.sendError(status);
                return new ModelAndView();
            }
        }
        return page(request, HttpStatus.INTERNAL_SERVER_ERROR, "INTERNAL_ERROR",
                "服务暂时不可用，请稍后重试。", Map.of());
    }

    private ModelAndView page(HttpServletRequest request, HttpStatus status, String code,
                              String message, Map<String, String> fields) {
        ModelAndView view = new ModelAndView("error/" + status.value());
        view.setStatus(status);
        view.addAllObjects(pageModels.commonModel(request));
        // Even deliberately thrown 500 BusinessExceptions must not disclose supplied details.
        if (status.is5xxServerError()) {
            code = "INTERNAL_ERROR";
            message = "服务暂时不可用，请稍后重试。";
            fields = Map.of();
        }
        view.addObject("errorStatus", status.value());
        view.addObject("errorCode", code);
        view.addObject("errorMessage", message);
        view.addObject("fieldErrors", fields);
        return view;
    }
}
