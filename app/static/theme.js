(function () {
  const storageKey = "adaptivelearn-theme";

  function getStoredTheme() {
    return localStorage.getItem(storageKey) || "dark";
  }

  function applyTheme(theme) {
    const nextTheme = theme === "light" ? "light" : "dark";
    document.documentElement.dataset.theme = nextTheme;
    localStorage.setItem(storageKey, nextTheme);
    updateThemeToggles(nextTheme);
  }

  function toggleTheme() {
    applyTheme(document.documentElement.dataset.theme === "light" ? "dark" : "light");
  }

  function updateThemeToggles(theme) {
    document.querySelectorAll("[data-theme-toggle]").forEach((button) => {
      const isLight = theme === "light";
      button.setAttribute("aria-label", isLight ? "Switch to dark mode" : "Switch to light mode");
      button.setAttribute("title", isLight ? "Switch to dark mode" : "Switch to light mode");
      button.innerHTML = `
        <span class="theme-toggle-track">
          <span class="theme-toggle-thumb">${isLight ? "☀️" : "🌙"}</span>
        </span>
      `;
    });
  }

  function createToggle() {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "theme-toggle";
    button.dataset.themeToggle = "true";
    button.addEventListener("click", toggleTheme);
    return button;
  }

  function renderThemeToggle(container) {
    if (!container || container.querySelector("[data-theme-toggle]")) return;
    const toggle = createToggle();
    container.appendChild(toggle);
    updateThemeToggles(document.documentElement.dataset.theme || getStoredTheme());
  }

  function ensureFloatingToggle() {
    if (document.querySelector(".top-nav") || document.querySelector(".floating-theme-toggle")) return;
    const wrapper = document.createElement("div");
    wrapper.className = "floating-theme-toggle";
    const toggle = createToggle();
    wrapper.appendChild(toggle);
    document.body.appendChild(wrapper);
    updateThemeToggles(document.documentElement.dataset.theme || getStoredTheme());
  }

  window.applyAdaptiveTheme = applyTheme;
  window.renderThemeToggle = renderThemeToggle;
  window.ensureFloatingThemeToggle = ensureFloatingToggle;

  applyTheme(getStoredTheme());

  document.addEventListener("DOMContentLoaded", () => {
    document.querySelectorAll(".top-nav .nav-links").forEach(renderThemeToggle);
    ensureFloatingToggle();
  });
})();
