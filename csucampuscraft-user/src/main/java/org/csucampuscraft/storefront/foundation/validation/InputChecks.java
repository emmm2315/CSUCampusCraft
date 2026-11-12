package org.csucampuscraft.storefront.foundation.validation;

import org.csucampuscraft.storefront.foundation.web.BusinessException;
import java.math.BigDecimal;
import java.math.RoundingMode;
import java.util.Map;
import org.springframework.http.HttpStatus;

/** Type/range primitives; callers supply business-specific minimums and maximums. */
public final class InputChecks {
    public static final BigDecimal MAX_MONEY = new BigDecimal("9999999999.99");
    private InputChecks() { }

    public static String requiredText(String field, String raw, int maxLength) {
        return text(field, raw, 1, maxLength);
    }

    public static String text(String field, String raw, int minLength, int maxLength) {
        if (minLength < 0 || maxLength < minLength) {
            throw new IllegalArgumentException("Invalid text limits");
        }
        String value = raw == null ? "" : raw.strip();
        int length = value.codePointCount(0, value.length());
        if (length < minLength || length > maxLength) {
            throw invalid(field, "INVALID_LENGTH", "请检查文字是否填写及其长度。");
        }
        return value;
    }

    public static int integer(String field, String raw, int minimum, int maximum) {
        return (int) longInteger(field, raw, minimum, maximum);
    }

    public static long longInteger(String field, String raw, long minimum, long maximum) {
        if (minimum > maximum) {
            throw new IllegalArgumentException("Invalid integer limits");
        }
        String value = raw == null ? "" : raw.strip();
        try {
            if (!value.matches("-?[0-9]+")) {
                throw new NumberFormatException();
            }
            long parsed = Long.parseLong(value);
            if (parsed < minimum || parsed > maximum) {
                throw new NumberFormatException();
            }
            return parsed;
        } catch (NumberFormatException invalid) {
            throw invalid(field, "INVALID_INTEGER", "请输入允许范围内的整数。");
        }
    }

    public static <E extends Enum<E>> E enumeration(String field, String raw, Class<E> type) {
        try {
            if (raw == null) {
                throw new IllegalArgumentException();
            }
            return Enum.valueOf(type, raw.strip());
        } catch (IllegalArgumentException invalid) {
            throw invalid(field, "INVALID_ENUM", "请选择允许的选项。");
        }
    }

    public static BigDecimal money(String field, String raw) {
        return money(field, raw, MAX_MONEY.negate(), MAX_MONEY);
    }

    public static BigDecimal money(String field, String raw, BigDecimal minimum, BigDecimal maximum) {
        if (minimum == null || maximum == null || minimum.compareTo(maximum) > 0
                || minimum.compareTo(MAX_MONEY.negate()) < 0 || maximum.compareTo(MAX_MONEY) > 0) {
            throw new IllegalArgumentException("Invalid money limits");
        }
        String value = raw == null ? "" : raw.strip();
        try {
            if (value.length() > 32 || !value.matches("-?[0-9]+(?:\\.[0-9]{1,2})?")) {
                throw new NumberFormatException();
            }
            BigDecimal parsed = new BigDecimal(value).setScale(2, RoundingMode.UNNECESSARY);
            if (parsed.compareTo(minimum) < 0 || parsed.compareTo(maximum) > 0) {
                throw new NumberFormatException();
            }
            return parsed;
        } catch (ArithmeticException | NumberFormatException invalid) {
            throw invalid(field, "INVALID_MONEY", "请输入范围内且最多两位小数的金额。");
        }
    }

    private static BusinessException invalid(String field, String code, String message) {
        return new BusinessException(HttpStatus.BAD_REQUEST, code, message, Map.of(field, message));
    }
}
