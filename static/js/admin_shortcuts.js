/**
 * Keyboard shortcuts for the GCLBA staff admin.
 *
 * Only active on the Application change form (detail view).
 * Ctrl+Shift+R  →  Under Review
 * Ctrl+Shift+D  →  Needs More Info
 * Ctrl+Shift+A  →  Approved
 * Ctrl+Shift+N  →  Declined
 */
(function () {
  "use strict";

  var statusSelect = document.querySelector('select[name="status"]');
  if (!statusSelect) return;

  var STATUS_MAP = {
    R: "under_review",
    D: "needs_more_info",
    A: "approved",
    N: "declined",
  };

  var LABEL_MAP = {
    R: "Under Review",
    D: "Needs More Info",
    A: "Approved",
    N: "Declined",
  };

  document.addEventListener("keydown", function (e) {
    if (!e.ctrlKey || !e.shiftKey) return;

    // Ignore if user is typing in an input/textarea
    var tag = document.activeElement && document.activeElement.tagName;
    if (tag === "INPUT" || tag === "TEXTAREA") return;

    var key = e.key.toUpperCase();
    if (!(key in STATUS_MAP)) return;

    e.preventDefault();

    // Check the option exists before setting
    var option = statusSelect.querySelector(
      'option[value="' + STATUS_MAP[key] + '"]'
    );
    if (!option) return;

    statusSelect.value = STATUS_MAP[key];

    // Trigger change event so Django's form detects the update
    statusSelect.dispatchEvent(new Event("change", { bubbles: true }));

    // Visual flash confirmation
    statusSelect.style.outline = "3px solid #16a34a";
    statusSelect.style.outlineOffset = "2px";

    // Brief toast notification
    var toast = document.createElement("div");
    toast.textContent = "Status → " + LABEL_MAP[key];
    toast.style.cssText =
      "position:fixed;top:16px;right:16px;z-index:9999;" +
      "padding:8px 16px;background:#166534;color:white;" +
      "border-radius:6px;font-size:13px;font-weight:600;" +
      "box-shadow:0 4px 12px rgba(0,0,0,0.15);" +
      "transition:opacity 0.3s ease;";
    document.body.appendChild(toast);

    setTimeout(function () {
      statusSelect.style.outline = "";
      statusSelect.style.outlineOffset = "";
      toast.style.opacity = "0";
      setTimeout(function () {
        toast.remove();
      }, 300);
    }, 1200);
  });
})();
