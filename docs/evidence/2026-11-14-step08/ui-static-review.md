# STEP08 UI candidate static review

- Candidate files: 5, user module only. No admin, POM, SQL, image assets, JavaScript or original evidence modified.
- U05 changes only the checkout entry block: valid cart gets `a[data-checkout-link]`; empty/invalid cart keeps disabled `button[data-checkout-unavailable]` and reason. Existing cart forms, row markers, input limits and totals are preserved.
- U06 uses `fragments/layout::page`, `alerts::summary`, `fields::csrf`, `fields::text`, new `fields::textarea`, and `images::image`. Exactly one POST form (`/orders`) and one hidden confirmation token; amounts are read-only text/data, never posted as authority.
- Address textarea uses `th:text`, ordinary inputs use `th:value`; labels/errors use escaped text. No `th:utext`, no extra inline JavaScript, no HTML `maxlength` (server counts Unicode code points, HTML would count UTF-16 code units).
- All shipping controls have visible labels linked by for/id. Error links match field IDs receiverName/receiverPhone/receiverAddress; errors use aria-invalid/aria-describedby. Existing shared global alerts remain available.
- Snapshot lines expose stable non-secret data attributes for itemId/productId/quantity/itemVersion/unitPrice/subtotal. Confirmation token occurs only in its hidden form input, never a displayed text or data attribute. Conflict pages contain no token input.
- CSS existing content is a normalized byte-for-byte prefix; appended rules are scoped to `[data-page-id="U06"]` only. Breakpoint 960px stacks the order and shipping sections; table scrolls inside its own container.
- Source UTF-8/no BOM, LF, per-file old/new SHA-256 manifest verified. This is static review; runtime rendering and two-resolution browser screenshots remain integration acceptance work.
