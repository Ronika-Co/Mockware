document.addEventListener("DOMContentLoaded", () => {
  initTheme();
  initTabs();
  initCopyButtons();
  initNavScroll();
});

/* ── Theme toggle ──────────────────────────────────────── */
function initTheme() {
  const btn = document.getElementById("theme-toggle");
  const stored = localStorage.getItem("theme");

  if (stored === "light") {
    document.documentElement.setAttribute("data-theme", "light");
    btn.textContent = "☀️";
  } else {
    document.documentElement.setAttribute("data-theme", "dark");
    btn.textContent = "🌙";
  }

  btn.addEventListener("click", () => {
    const theme = document.documentElement.getAttribute("data-theme");
    if (theme === "dark") {
      document.documentElement.setAttribute("data-theme", "light");
      localStorage.setItem("theme", "light");
      btn.textContent = "☀️";
    } else {
      document.documentElement.setAttribute("data-theme", "dark");
      localStorage.setItem("theme", "dark");
      btn.textContent = "🌙";
    }
  });
}

/* ── Install tabs ──────────────────────────────────────── */
function initTabs() {
  document.querySelectorAll(".tab-nav").forEach((nav) => {
    const btns = nav.querySelectorAll(".tab-btn");
    const parent = nav.closest(".tabs");
    const panels = parent.querySelectorAll(".tab-content");

    btns.forEach((btn) => {
      btn.addEventListener("click", () => {
        btns.forEach((b) => b.classList.remove("active"));
        panels.forEach((p) => p.classList.remove("active"));
        btn.classList.add("active");
        const target = document.getElementById(btn.dataset.tab);
        if (target) target.classList.add("active");
      });
    });
  });
}

/* ── Copy buttons ──────────────────────────────────────── */
function initCopyButtons() {
  document.querySelectorAll(".code-block").forEach((block) => {
    const btn = document.createElement("button");
    btn.className = "copy-btn";
    btn.textContent = "Copy";
    block.appendChild(btn);

    btn.addEventListener("click", async () => {
      const code = block.querySelector("code");
      if (!code) return;
      try {
        await navigator.clipboard.writeText(code.textContent);
        btn.textContent = "Copied!";
        btn.classList.add("show");
        setTimeout(() => {
          btn.textContent = "Copy";
          btn.classList.remove("show");
        }, 2000);
      } catch {
        btn.textContent = "Error";
      }
    });
  });
}

/* ── Nav active state on scroll ─────────────────────────── */
function initNavScroll() {
  const sections = document.querySelectorAll("section[id]");
  const navLinks = document.querySelectorAll("nav a[href^='#']");

  if (!sections.length || !navLinks.length) return;

  const observer = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (!entry.isIntersecting) return;
        navLinks.forEach((link) => {
          link.style.color = "";
        });
        const active = document.querySelector(
          `nav a[href="#${entry.target.id}"]`
        );
        if (active) active.style.color = "var(--accent)";
      });
    },
    { rootMargin: "-40% 0px -55% 0px" }
  );

  sections.forEach((s) => observer.observe(s));
}
