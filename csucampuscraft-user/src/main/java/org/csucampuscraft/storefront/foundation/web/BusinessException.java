package org.csucampuscraft.storefront.foundation.web;

import java.util.Map;
import java.util.Objects;
import java.util.Set;
import org.springframework.http.HttpStatus;

/** A deliberate, publicly displayable failure; never populate it with exception details. */
public final class BusinessException extends RuntimeException {
    private static final Set<HttpStatus> SUPPORTED = Set.of(HttpStatus.BAD_REQUEST,
            HttpStatus.FORBIDDEN, HttpStatus.NOT_FOUND, HttpStatus.CONFLICT,
            HttpStatus.INTERNAL_SERVER_ERROR);
    private final HttpStatus status;
    private final String code;
    private final Map<String, String> fieldErrors;

    public BusinessException(HttpStatus status, String code, String message) {
        this(status, code, message, Map.of());
    }

    public BusinessException(HttpStatus status, String code, String message,
                             Map<String, String> fieldErrors) {
        super(Objects.requireNonNull(message, "Display message is required"));
        if (!SUPPORTED.contains(status)) {
            throw new IllegalArgumentException("Unsupported page error status");
        }
        if (code == null || !code.matches("[A-Z][A-Z0-9_]{0,63}")) {
            throw new IllegalArgumentException("Stable error code is required");
        }
        this.status = status;
        this.code = code;
        this.fieldErrors = Map.copyOf(fieldErrors);
    }

    public HttpStatus getStatus() { return status; }
    public String getCode() { return code; }
    public Map<String, String> getFieldErrors() { return fieldErrors; }
}
