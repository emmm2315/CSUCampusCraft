package org.csucampuscraft.storefront.foundation.web;

import org.csucampuscraft.storefront.foundation.security.ReturnUrlPolicy;
import java.net.URI;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;

/** POST handlers use this after successful work; the browser follows with a new GET. */
public final class HttpResponses {
    private static final ReturnUrlPolicy RETURNS = new ReturnUrlPolicy();
    private HttpResponses() { }

    public static ResponseEntity<Void> seeOther(String readPath) {
        String destination = RETURNS.resolve(readPath, "/");
        if (!destination.equals(readPath)) {
            throw new BusinessException(HttpStatus.BAD_REQUEST, "INVALID_RETURN_URL",
                    "返回地址不可用，请返回本站首页。");
        }
        return ResponseEntity.status(HttpStatus.SEE_OTHER).location(URI.create(destination)).build();
    }
}
