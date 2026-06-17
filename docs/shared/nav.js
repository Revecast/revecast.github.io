// ── Auto-open active nav group (if collapsible groups are used) ──
(function () {
  var active = document.querySelector(".sidebar-nav a.active");
  if (active) {
    var group = active.closest("details.nav-group");
    if (group) group.open = true;
  }
})();

// ── Mobile hamburger toggle ──
(function () {
  var btn = document.querySelector(".hamburger");
  var sidebar = document.querySelector(".sidebar");
  if (!btn || !sidebar) return;

  // Create overlay
  var overlay = document.createElement("div");
  overlay.className = "sidebar-overlay";
  document.body.appendChild(overlay);

  function openSidebar() {
    sidebar.classList.add("open");
    btn.classList.add("open");
    overlay.classList.add("visible");
    document.body.style.overflow = "hidden";
  }

  function closeSidebar() {
    sidebar.classList.remove("open");
    btn.classList.remove("open");
    overlay.classList.remove("visible");
    document.body.style.overflow = "";
  }

  btn.addEventListener("click", function () {
    sidebar.classList.contains("open") ? closeSidebar() : openSidebar();
  });

  overlay.addEventListener("click", closeSidebar);

  // Close sidebar when a nav link is tapped on mobile
  sidebar.querySelectorAll("a").forEach(function (link) {
    link.addEventListener("click", function () {
      if (window.innerWidth <= 768) closeSidebar();
    });
  });
})();
