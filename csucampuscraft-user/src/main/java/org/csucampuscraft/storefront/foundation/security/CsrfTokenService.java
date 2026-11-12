package org.csucampuscraft.storefront.foundation.security;

import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpSession;
import java.security.SecureRandom;
import java.util.HexFormat;
import org.springframework.stereotype.Service;

/** A session token is deliberately separate from login identity and confirmation tokens. */
@Service
public final class CsrfTokenService {
    public static final String PARAMETER_NAME = "_csrf";
    private static final String SESSION_ATTRIBUTE = CsrfTokenService.class.getName() + ".TOKEN";
    private final SecureRandom random = new SecureRandom();

    public String getOrCreate(HttpServletRequest request) {
        HttpSession session = request.getSession(true);
        synchronized (session) {
            Object existing = session.getAttribute(SESSION_ATTRIBUTE);
            if (existing instanceof String token) {
                return token;
            }
            byte[] bytes = new byte[32];
            random.nextBytes(bytes);
            String token = HexFormat.of().formatHex(bytes);
            session.setAttribute(SESSION_ATTRIBUTE, token);
            return token;
        }
    }

    public String getExisting(HttpServletRequest request) {
        HttpSession session = request.getSession(false);
        if (session == null) {
            return null;
        }
        try {
            Object token = session.getAttribute(SESSION_ATTRIBUTE);
            return token instanceof String text ? text : null;
        } catch (IllegalStateException expired) {
            return null;
        }
    }
}
