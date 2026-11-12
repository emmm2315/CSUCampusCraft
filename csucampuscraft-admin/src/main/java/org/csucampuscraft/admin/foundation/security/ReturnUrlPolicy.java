package org.csucampuscraft.admin.foundation.security;

import java.net.URI;
import java.net.URISyntaxException;
import java.net.URLDecoder;
import java.nio.charset.StandardCharsets;
import java.util.List;
import java.util.regex.Pattern;
import org.springframework.stereotype.Component;

/** Navigation allowlist only: listing a GET destination does not register its controller. */
@Component
public final class ReturnUrlPolicy {
    private static final List<Pattern> READ_PATHS = List.of(
            Pattern.compile("/"),
            Pattern.compile("/categories(?:/new|/[1-9][0-9]*/edit)?"),
            Pattern.compile("/products(?:/new|/[1-9][0-9]*/(?:edit|images))?"),
            Pattern.compile("/orders(?:/[A-Za-z0-9_-]{1,40})?"),
            Pattern.compile("/customers(?:/[1-9][0-9]*)?")
    );

    public String resolve(String returnUrl, String defaultPath) {
        String fallback = allowed(defaultPath) ? defaultPath : "/";
        return allowed(returnUrl) ? returnUrl : fallback;
    }

    private boolean allowed(String value) {
        if (value == null || value.isEmpty() || !value.equals(value.strip())
                || value.contains("\\") || value.contains("..") || value.contains("//")
                || value.chars().anyMatch(c -> c <= 32 || c == 127)) {
            return false;
        }
        try {
            URI uri = new URI(value);
            if (uri.isAbsolute() || uri.getRawAuthority() != null || uri.getRawFragment() != null
                    || !value.startsWith("/") || uri.getRawPath() == null
                    || uri.getRawPath().contains("%")) {
                return false;
            }
            String query = uri.getRawQuery();
            if (query != null) {
                // Inspect one decoded query layer, but preserve the original URL for navigation.
                String decoded = URLDecoder.decode(query, StandardCharsets.UTF_8);
                if (decoded.contains("..") || decoded.contains("\\") || decoded.contains("//")
                        || decoded.chars().anyMatch(c -> c < 32 || c == 127)
                        || decoded.matches("(?is).*%(?:0[0-9a-f]|1[0-9a-f]|2e|2f|5c|7f|25).*")) {
                    return false;
                }
            }
            return READ_PATHS.stream().anyMatch(pattern -> pattern.matcher(uri.getPath()).matches());
        } catch (URISyntaxException | IllegalArgumentException invalid) {
            return false;
        }
    }
}
