/* Read the local visual preference before CSS paints; light is the default. */
(() => {
    "use strict";
    let theme = "light";
    try { if (localStorage.getItem("csucampuscraft.theme") === "dark") theme = "dark"; } catch (_) { /* Storage may be unavailable. */ }
    document.documentElement.dataset.theme = theme;
})();
