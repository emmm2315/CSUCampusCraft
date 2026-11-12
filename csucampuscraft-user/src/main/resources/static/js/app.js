(() => {
    "use strict";

    function showImageFallback(image) {
        if (!(image instanceof HTMLImageElement) || !image.hasAttribute("data-image-fallback")
                || image.dataset.imageFallbackUsed === "true") return;
        const fallback = image.getAttribute("data-image-fallback");
        if (!fallback || !fallback.startsWith("/") || fallback.startsWith("//")) return;
        image.dataset.imageFallbackUsed = "true";
        image.src = fallback;
    }

    document.addEventListener("error", (event) => showImageFallback(event.target), true);

    function resetForm(form) {
        delete form.dataset.submitting;
        form.classList.remove("is-submitting");
        form.removeAttribute("aria-busy");
        form.querySelectorAll("[data-submitting-control]").forEach((control) => {
            control.removeAttribute("aria-disabled");
            control.removeAttribute("data-submitting-control");
            if (control.hasAttribute("data-original-label")) {
                control.textContent = control.dataset.originalLabel;
                control.removeAttribute("data-original-label");
            }
        });
    }

    document.addEventListener("submit", (event) => {
        const form = event.target;
        if (!(form instanceof HTMLFormElement) || !form.hasAttribute("data-submit-state")
                || event.defaultPrevented) return;
        if (form.dataset.submitting === "true") {
            event.preventDefault();
            return;
        }
        form.dataset.submitting = "true";
        form.classList.add("is-submitting");
        form.setAttribute("aria-busy", "true");
        const submitter = event.submitter;
        if (submitter instanceof HTMLElement) {
            // Retain the enabled control so its name/value remains in the POST.
            submitter.setAttribute("aria-disabled", "true");
            submitter.setAttribute("data-submitting-control", "");
            if (submitter instanceof HTMLButtonElement) {
                submitter.dataset.originalLabel = submitter.textContent;
                submitter.textContent = submitter.dataset.submitLabel || "处理中…";
            }
        }
    });

    function checkImages() {
        document.querySelectorAll("img[data-image-fallback]").forEach((image) => {
            if (image.complete && image.naturalWidth === 0) showImageFallback(image);
        });
    }
    if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", checkImages);
    else checkImages();

    window.addEventListener("pageshow", () => {
        document.querySelectorAll("form[data-submit-state]").forEach(resetForm);
        checkImages();
    });
})();
