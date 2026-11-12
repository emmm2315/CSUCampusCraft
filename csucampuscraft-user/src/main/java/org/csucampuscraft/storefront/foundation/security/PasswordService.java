package org.csucampuscraft.storefront.foundation.security;

import java.nio.charset.StandardCharsets;
import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder;
import org.springframework.stereotype.Service;

/** Raw passwords and hashes must never be placed in a view model or a log. */
@Service
public final class PasswordService {
    private final BCryptPasswordEncoder encoder = new BCryptPasswordEncoder(10);

    public boolean matches(String raw, String hash) {
        if (raw == null || hash == null || raw.getBytes(StandardCharsets.UTF_8).length > 72
                || !hash.matches("\\$2[aby]\\$10\\$[./A-Za-z0-9]{53}")) {
            return false;
        }
        return encoder.matches(raw, hash);
    }

    public String hash(String raw) {
        if (raw == null || raw.getBytes(StandardCharsets.UTF_8).length > 72) {
            throw new IllegalArgumentException("Password must fit BCrypt's 72-byte UTF-8 limit");
        }
        return encoder.encode(raw);
    }
}
