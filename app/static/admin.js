const adminPage = document.body.dataset.adminPage;

document.addEventListener("DOMContentLoaded", initAdmin);

async function initAdmin() {
  if (adminPage === "login") {
    bindAdminLogin();
    return;
  }

  await requireAdmin();
  renderAdminChrome();

  if (adminPage === "dashboard") loadAdminDashboard();
  if (adminPage === "research") loadResearchGraphs();
  if (adminPage === "analytics") loadAdminAnalytics();
}

function bindAdminLogin() {
  const form = document.querySelector("#admin-login-form");
  const message = document.querySelector("#admin-login-message");
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    message.textContent = "";
    try {
      await adminPost("/admin/api/login", {
        username: document.querySelector("#admin-username").value,
        password: document.querySelector("#admin-password").value,
      });
      location.href = "/admin/dashboard";
    } catch (error) {
      message.textContent = error.message;
    }
  });
}

async function requireAdmin() {
  try {
    await adminGet("/admin/api/me");
  } catch (error) {
    location.href = "/admin/login";
  }
}

function renderAdminChrome() {
  const nav = document.querySelector(".admin-nav");
  if (nav) {
    nav.innerHTML = `
      <a class="brand" href="/admin/dashboard"><span></span>AdaptiveLearn AI Admin</a>
      <div class="nav-links">
        <a href="/admin/dashboard">Dashboard</a>
        <a href="/admin/research">Research</a>
        <a href="/admin/analytics">Analytics</a>
        <a href="#" id="admin-logout" class="btn ghost" style="min-height:36px; padding:0 14px; border-radius:10px;">Sign out</a>
      </div>
    `;
    if (window.renderThemeToggle) window.renderThemeToggle(nav.querySelector(".nav-links"));
  }

  const sidebar = document.querySelector(".admin-sidebar");
  if (sidebar) {
    const links = [
      ["dashboard", "Dashboard", "/admin/dashboard"],
      ["research", "Research Lab", "/admin/research"],
      ["analytics", "Learner Analytics", "/admin/analytics"],
    ];
    sidebar.innerHTML = links.map(([id, label, href]) => (
      `<a class="side-link ${adminPage === id ? "active" : ""}" href="${href}">${label}</a>`
    )).join("");
  }

  const logout = document.querySelector("#admin-logout");
  if (logout) {
    logout.addEventListener("click", async (event) => {
      event.preventDefault();
      await adminPost("/admin/api/logout");
      location.href = "/admin/login";
    });
  }
}

async function loadAdminDashboard() {
  const data = await adminGet("/admin/api/dashboard");
  setText("#admin-learners", data.learner_count);
  setText("#admin-active-sessions", data.active_quiz_sessions);
  setText("#admin-proficiency", formatPercent(data.average_proficiency));
  setText("#admin-misconceptions", data.misconception_count);
  setText("#admin-hesitations", data.hesitation_count);
  setText("#admin-confidence", formatPercent(data.average_confidence));
  renderBarList("#misconception-topics", data.misconception_topics, "topic");
  renderBarList("#hesitation-topics", data.hesitation_topics, "topic");
  renderTrend("#confidence-trends", data.confidence_trends);
}

async function loadResearchGraphs() {
  const runBtn = document.querySelector("#run-simulation");
  if (runBtn) {
    runBtn.addEventListener("click", async () => {
      runBtn.textContent = "Running simulation...";
      runBtn.disabled = true;
      try {
        await adminPost("/internal/evaluation/run");
        await renderResearchGraphs();
      } catch (error) {
        alert("Simulation run error: " + error.message);
      } finally {
        runBtn.textContent = "Run simulator";
        runBtn.disabled = false;
      }
    });
  }
  await renderResearchGraphs();
}

async function renderResearchGraphs() {
  const output = document.querySelector("#research-output");
  const graphs = await adminGet("/internal/evaluation/graphs");
  const values = Object.values(graphs);
  if (!values.length) {
    output.innerHTML = `<div class="empty-state">Run the simulator to generate research graphs.</div>`;
    return;
  }

  const version = Date.now();
  output.innerHTML = values.map((path) => {
    const file = path.split(/[\\/]/).pop();
    return `
      <div class="panel graph-card">
        <img src="/simulation-results/${file}?v=${version}" alt="${file}">
        <p>${file.replaceAll("_", " ").replace(".png", "")}</p>
      </div>
    `;
  }).join("");
}

async function loadAdminAnalytics() {
  const data = await adminGet("/admin/api/analytics");
  renderLearnerTable(data.learners);
  renderBarList("#confidence-distribution", data.confidence_distribution, "label");
  renderBarList("#difficulty-progression", data.difficulty_progression, "label", "accuracy");
  renderBarList("#hesitation-frequency", data.hesitation_frequency, "topic");
  renderProficiencyTracking(data.proficiency_tracking);
}

function renderLearnerTable(learners) {
  const body = document.querySelector("#learner-table-body");
  if (!learners.length) {
    body.innerHTML = `<tr><td colspan="7">No learners registered yet.</td></tr>`;
    return;
  }
  body.innerHTML = learners.map((learner) => `
    <tr>
      <td>${escapeHtml(learner.name)}</td>
      <td>${escapeHtml(learner.email)}</td>
      <td>${learner.responses}</td>
      <td>${formatPercent(learner.proficiency)}</td>
      <td>${formatPercent(learner.average_confidence)}</td>
      <td>${learner.hesitation_count}</td>
      <td>${learner.misconception_count}</td>
    </tr>
  `).join("");
}

function renderBarList(selector, rows, labelKey, valueKey = "count") {
  const container = document.querySelector(selector);
  if (!container) return;
  if (!rows || !rows.length) {
    container.innerHTML = `<div class="empty-state">No data yet.</div>`;
    return;
  }
  const max = Math.max(...rows.map((row) => Number(row[valueKey]) || 0), 1);
  container.innerHTML = rows.map((row) => {
    const value = Number(row[valueKey]) || 0;
    const width = Math.max(4, (value / max) * 100);
    const display = valueKey === "accuracy" ? formatPercent(value) : value;
    return `
      <div class="bar-row">
        <span>${escapeHtml(row[labelKey])}</span>
        <div class="bar-track"><i style="width:${width}%"></i></div>
        <strong>${display}</strong>
      </div>
    `;
  }).join("");
}

function renderTrend(selector, rows) {
  const container = document.querySelector(selector);
  if (!rows || !rows.length) {
    container.innerHTML = `<div class="empty-state">No confidence trend data yet.</div>`;
    return;
  }
  container.innerHTML = rows.map((row) => `
    <div class="trend-point" title="${row.label}">
      <i style="height:${Math.max(6, row.average_confidence * 100)}%"></i>
      <span>${row.label}</span>
    </div>
  `).join("");
}

function renderProficiencyTracking(rows) {
  const container = document.querySelector("#proficiency-tracking");
  if (!rows.length) {
    container.innerHTML = `<div class="empty-state">No learner proficiency data yet.</div>`;
    return;
  }
  container.innerHTML = rows.map((row) => `
    <div class="bar-row">
      <span>${escapeHtml(row.student)}</span>
      <div class="bar-track"><i style="width:${Math.max(4, row.proficiency * 100)}%"></i></div>
      <strong>${formatPercent(row.proficiency)}</strong>
    </div>
  `).join("");
}

async function adminGet(url) {
  return parseAdminResponse(await fetch(url, { headers: { "Content-Type": "application/json" } }));
}

async function adminPost(url, payload) {
  return parseAdminResponse(await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: payload ? JSON.stringify(payload) : undefined,
  }));
}

async function parseAdminResponse(response) {
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(data.detail || "Admin request failed.");
  return data;
}

function setText(selector, value) {
  const element = document.querySelector(selector);
  if (element) element.textContent = value;
}

function formatPercent(value) {
  return `${Math.round(Number(value || 0) * 100)}%`;
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}
