package org.csucampuscraft.storefront.auth;

import java.util.UUID;
import org.csucampuscraft.storefront.foundation.security.PasswordService;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
@Transactional(readOnly = true)
public class AuthService {
    public static final String REQUIRED_ROLE = "CUSTOMER";
    private final StoreUserMapper users;
    private final PasswordService passwords;
    private final String absentUserHash;

    public AuthService(StoreUserMapper users, PasswordService passwords) {
        this.users = users;
        this.passwords = passwords;
        // Unknown accounts also perform a BCrypt comparison; never expose this value.
        this.absentUserHash = passwords.hash(UUID.randomUUID().toString());
    }

    public StoreUser authenticate(String username, String password) {
        StoreUser user = users.selectForLoginByUsername(username);
        boolean matched = passwords.matches(password,
                user == null ? absentUserHash : user.getPasswordHash());
        return user != null && matched && "ENABLED".equals(user.getStatus())
                && REQUIRED_ROLE.equals(user.getRole()) && user.getUpdatedAt() != null ? user : null;
    }

    /** Role follows existence/status/stamp validation in the identity filter. */
    public StoreUser findCurrent(SessionIdentity identity) {
        if (identity == null) return null;
        StoreUser user = users.selectById(identity.userId());
        return user != null && "ENABLED".equals(user.getStatus())
                && identity.authStamp().equals(user.getUpdatedAt()) ? user : null;
    }
}

