// Revecast feedback site — fetches issue snapshot, renders filterable list.
// Pure vanilla JS, no build step.

(function () {
  "use strict";

  const DATA_URL =
    "https://raw.githubusercontent.com/Revecast/feature-requests/main/data.json";
  const REPO_URL = "https://github.com/Revecast/feature-requests";

  const PRODUCT_LABEL = {
    psacore: "PSA",
    recruiter: "Recruiter",
    forms: "Forms",
    kanban: "Kanban",
    reporting: "Reporting",
    connect: "Connect",
    desktop: "Desktop",
  };

  const STATUS_LABEL = {
    "under-review": "Under review",
    planned: "Planned",
    "in-progress": "In progress",
    shipped: "Shipped",
    declined: "Declined",
  };

  // ── State ──
  const params = new URLSearchParams(window.location.search);
  const state = {
    product: params.get("product") || "",
    status: params.get("status") || "",
    sort: params.get("sort") || "votes",
    search: params.get("q") || "",
    items: [],
    summary: null,
  };

  // ── Fetch snapshot ──
  async function load() {
    try {
      const res = await fetch(DATA_URL, { cache: "no-cache" });
      if (!res.ok) throw new Error("snapshot fetch failed: " + res.status);
      const data = await res.json();
      state.items = Array.isArray(data.items) ? data.items : [];
      state.summary = data.summary || null;
    } catch (err) {
      console.warn("Could not load snapshot:", err);
      state.items = [];
      state.summary = null;
    }
    render();
  }

  // ── Filter / sort ──
  function visible() {
    const q = state.search.trim().toLowerCase();
    return state.items
      .filter((it) => {
        if (state.product && it.product !== state.product) return false;
        if (state.status) {
          if (it.status !== state.status) return false;
        } else {
          // "All open" hides shipped + declined by default
          if (it.status === "shipped" || it.status === "declined") return false;
          if (it.state === "CLOSED" && it.status !== "in-progress") return false;
        }
        if (q) {
          const hay = (it.title + " " + (it.body || "")).toLowerCase();
          if (!hay.includes(q)) return false;
        }
        return true;
      })
      .sort((a, b) => {
        if (state.sort === "newest") {
          return new Date(b.createdAt) - new Date(a.createdAt);
        }
        if (state.sort === "updated") {
          return new Date(b.updatedAt) - new Date(a.updatedAt);
        }
        // votes (default): votes desc, tiebreak newest
        if (b.votes !== a.votes) return b.votes - a.votes;
        return new Date(b.createdAt) - new Date(a.createdAt);
      });
  }

  // ── Render ──
  function render() {
    syncChips();
    renderStats();
    renderList();
    syncUrl();
  }

  function syncChips() {
    document.querySelectorAll("#product-chips .chip").forEach((c) => {
      c.classList.toggle("active", (c.dataset.product || "") === state.product);
    });
    document.querySelectorAll("#status-chips .chip").forEach((c) => {
      c.classList.toggle("active", (c.dataset.status || "") === state.status);
    });
    const search = document.getElementById("search");
    if (search && search.value !== state.search) search.value = state.search;
    const sort = document.getElementById("sort");
    if (sort && sort.value !== state.sort) sort.value = state.sort;
  }

  function renderStats() {
    const el = document.getElementById("stats");
    if (!el) return;
    const items = state.items;
    const open = items.filter((i) => i.state === "OPEN").length;
    const planned = items.filter((i) => i.status === "planned").length;
    const inProgress = items.filter((i) => i.status === "in-progress").length;
    const shipped = items.filter((i) => i.status === "shipped").length;
    el.innerHTML = `
      <div class="stat-tile stat-tile-accent-blue">
        <div class="stat-tile-value">${open}</div>
        <div class="stat-tile-label">Open requests</div>
      </div>
      <div class="stat-tile stat-tile-accent-purple">
        <div class="stat-tile-value">${planned}</div>
        <div class="stat-tile-label">Planned</div>
      </div>
      <div class="stat-tile stat-tile-accent-yellow">
        <div class="stat-tile-value">${inProgress}</div>
        <div class="stat-tile-label">In progress</div>
      </div>
      <div class="stat-tile stat-tile-accent-green">
        <div class="stat-tile-value">${shipped}</div>
        <div class="stat-tile-label">Shipped</div>
      </div>
    `;
  }

  function renderList() {
    const list = document.getElementById("request-list");
    if (!list) return;
    const rows = visible();

    if (state.items.length === 0) {
      list.innerHTML = emptyAll();
      return;
    }

    if (rows.length === 0) {
      list.innerHTML = emptyFiltered();
      return;
    }

    list.innerHTML = rows.map(card).join("");
  }

  function card(it) {
    const product = it.product || "";
    const status = it.status || "under-review";
    const productName = PRODUCT_LABEL[product] || product;
    const statusName = STATUS_LABEL[status] || status;
    const snippet = stripMarkdown(it.body).slice(0, 220);
    const date = formatDate(it.createdAt);
    const author = escapeHtml(it.author || "anonymous");
    const avatar = it.authorAvatar
      ? `<img src="${escapeAttr(it.authorAvatar)}" alt="" loading="lazy" onerror="this.style.display='none'">`
      : "";

    return `
      <a class="request-card" href="${escapeAttr(it.url)}" target="_blank" rel="noopener">
        <div class="vote-pill" title="Vote 👍 on GitHub">
          <span class="vote-pill-arrow">▲</span>
          <span class="vote-pill-count">${it.votes || 0}</span>
        </div>
        <div class="request-body">
          <div class="request-title">${escapeHtml(it.title)}</div>
          ${snippet ? `<div class="request-snippet">${escapeHtml(snippet)}</div>` : ""}
          <div class="request-meta">
            <span class="author">${avatar}${author}</span>
            <span>·</span>
            <span>${date}</span>
            ${it.comments ? `<span>·</span><span>💬 ${it.comments}</span>` : ""}
          </div>
        </div>
        <div class="request-side">
          ${product ? `<span class="badge-product badge-product-${product}">${productName}</span>` : ""}
          <span class="badge-status badge-status-${status}">${statusName}</span>
        </div>
      </a>
    `;
  }

  function emptyAll() {
    return `
      <div class="empty-state">
        <div class="empty-state-emoji">💡</div>
        <div class="empty-state-title">No feature requests yet</div>
        <p>Be the first to share an idea — we read every one.</p>
        <a href="submit.html" class="btn-submit">+ Submit the first request</a>
      </div>
    `;
  }

  function emptyFiltered() {
    return `
      <div class="empty-state">
        <div class="empty-state-emoji">🔍</div>
        <div class="empty-state-title">No matches</div>
        <p>Try clearing the filter or submitting your own idea.</p>
        <a href="submit.html${state.product ? "?product=" + state.product : ""}" class="btn-submit">+ Submit a request</a>
      </div>
    `;
  }

  // ── URL sync ──
  function syncUrl() {
    const p = new URLSearchParams();
    if (state.product) p.set("product", state.product);
    if (state.status) p.set("status", state.status);
    if (state.sort && state.sort !== "votes") p.set("sort", state.sort);
    if (state.search) p.set("q", state.search);
    const qs = p.toString();
    const url = window.location.pathname + (qs ? "?" + qs : "");
    window.history.replaceState(null, "", url);
  }

  // ── Bindings ──
  function bind() {
    document.querySelectorAll("#product-chips .chip").forEach((c) => {
      c.addEventListener("click", () => {
        state.product = c.dataset.product || "";
        render();
      });
    });
    document.querySelectorAll("#status-chips .chip").forEach((c) => {
      c.addEventListener("click", () => {
        state.status = c.dataset.status || "";
        render();
      });
    });
    const search = document.getElementById("search");
    if (search) {
      let t;
      search.addEventListener("input", () => {
        clearTimeout(t);
        t = setTimeout(() => {
          state.search = search.value;
          render();
        }, 150);
      });
    }
    const sort = document.getElementById("sort");
    if (sort) {
      sort.addEventListener("change", () => {
        state.sort = sort.value;
        render();
      });
    }
  }

  // ── Helpers ──
  function escapeHtml(str) {
    return String(str || "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;");
  }
  function escapeAttr(str) {
    return escapeHtml(str).replace(/"/g, "&quot;");
  }
  function stripMarkdown(s) {
    if (!s) return "";
    return s
      .replace(/^#{1,6}\s+/gm, "")
      .replace(/[*_~`]+/g, "")
      .replace(/!\[[^\]]*\]\([^)]*\)/g, "")
      .replace(/\[([^\]]+)\]\([^)]+\)/g, "$1")
      .replace(/<[^>]+>/g, "")
      .replace(/\r?\n+/g, " ")
      .replace(/\s+/g, " ")
      .trim();
  }
  function formatDate(iso) {
    if (!iso) return "";
    const d = new Date(iso);
    const diff = (Date.now() - d.getTime()) / 1000;
    if (diff < 60) return "just now";
    if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
    if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
    if (diff < 86400 * 30) return `${Math.floor(diff / 86400)}d ago`;
    return d.toLocaleDateString(undefined, { year: "numeric", month: "short", day: "numeric" });
  }

  // ── Boot ──
  document.addEventListener("DOMContentLoaded", () => {
    bind();
    load();
  });
})();
