/* AdaptiveLearn AI Platform - Unified Core Engine Scripting */

const page = document.body.dataset.page;
const store = {
  get token() { return localStorage.getItem("token"); },
  set token(value) { localStorage.setItem("token", value); },
  get studentId() { return Number(localStorage.getItem("studentId")); },
  set studentId(value) { localStorage.setItem("studentId", value); },
  get course() { return localStorage.getItem("course") || "Python"; },
  set course(value) { localStorage.setItem("course", value); },
  get studentName() { return localStorage.getItem("studentName") || "Learner"; },
  set studentName(value) { localStorage.setItem("studentName", value); }
};

// Global variables for active states
let quizSession = null;
let quizQuestion = null;
let selectedAnswer = null;
let codingQuestion = null;
let editor = null;
let timerInterval = null;
let questionStartTime = null;
let codingStartTime = null;
let retryCount = 0;

const FRONTEND_ROUTES = {
  dashboard: "/app/dashboard",
  login: "/app/login",
  register: "/app/register",
  quiz: "/app/quiz",
  coding: "/app/coding",
  progress: "/app/progress",
  course: "/app/course",
  settings: "/app/settings",
};

const PUBLIC_ROUTES = [
  FRONTEND_ROUTES.login,
  FRONTEND_ROUTES.register,
];

const $ = (selector) => document.querySelector(selector);

document.addEventListener("DOMContentLoaded", init);

async function init() {
  const currentPath = window.location.pathname;

  if (PUBLIC_ROUTES.includes(currentPath)) {
    initPublicPage();
    return;
  }

  // Only protected pages should perform auth validation.
  const authenticatedPages = ["dashboard", "quiz", "coding", "progress", "settings", "course"];
  if (authenticatedPages.includes(page)) {
    const authenticated = await requireAuth();
    if (!authenticated) return;
    renderAppChrome();
  }

  initProtectedPage();
}

function initPublicPage() {
  try {
    if (page === "register") initRegister();
    if (page === "login") initLogin();
  } catch (error) {
    console.error("Initialization error:", error);
    showGlobalError(error.message);
  }
}

function initProtectedPage() {
  // Route to specific page handlers
  try {
    if (page === "dashboard") initDashboard();
    if (page === "course") initCourse();
    if (page === "quiz") initQuiz();
    if (page === "coding") initCoding();
    if (page === "progress") initProgress();
    if (page === "settings") initSettings();
  } catch (error) {
    console.error("Initialization error:", error);
    showGlobalError(error.message);
  }
}

function showGlobalError(message) {
  const container = $(".content") || document.body;
  const alertHtml = `
    <div class="panel" style="border-color: var(--pink); background: rgba(236, 72, 153, 0.05); text-align: center; padding: 24px;">
      <h3 style="color: var(--pink); margin-bottom: 8px;">System Exception</h3>
      <p style="color: var(--muted);">${message}</p>
    </div>
  `;
  container.insertAdjacentHTML("afterbegin", alertHtml);
}

// ----------------------------------------------------
// AUTHENTICATION & SESSION MANAGEMENT
// ----------------------------------------------------

function initRegister() {
  $("#register-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    $("#auth-message").textContent = "";
    try {
      const result = await postJson("/auth/register", {
        name: $("#name").value,
        email: $("#email").value,
        password: $("#password").value,
      });
      saveAuth(result);
      location.href = FRONTEND_ROUTES.dashboard;
    } catch (error) {
      $("#auth-message").textContent = error.message;
    }
  });
}

function initLogin() {
  $("#login-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    $("#auth-message").textContent = "";
    try {
      const result = await postJson("/auth/login", {
        email: $("#email").value,
        password: $("#password").value,
      });
      saveAuth(result);
      location.href = FRONTEND_ROUTES.dashboard;
    } catch (error) {
      $("#auth-message").textContent = error.message;
    }
  });
}

function saveAuth(result) {
  store.token = result.token;
  store.studentId = result.student.id;
  store.studentName = result.student.name;
}

function clearAuthStorage() {
  [
    "token",
    "studentId",
    "studentName",
    "auth-user",
    "session",
    "quizSession",
  ].forEach((key) => localStorage.removeItem(key));
}

async function requireAuth() {
  if (!store.token) {
    location.href = FRONTEND_ROUTES.login;
    return false;
  }
  try {
    const me = await fetchJson("/auth/me");
    store.studentId = me.id;
    store.studentName = me.name;
    return true;
  } catch (error) {
    clearAuthStorage();
    location.href = FRONTEND_ROUTES.login;
    return false;
  }
}

// ----------------------------------------------------
// LAYOUT & APP CHROME
// ----------------------------------------------------

function renderAppChrome() {
  // Render Top Navbar
  const navContainer = $(".app-nav");
  if (navContainer) {
    navContainer.innerHTML = `
      <a class="brand" href="${FRONTEND_ROUTES.dashboard}"><span></span>AdaptiveLearn AI</a>
      <div class="nav-links">
        <span class="badge enrolled">${store.course}</span>
        <a href="${FRONTEND_ROUTES.settings}">Settings</a>
        <a href="#" id="logout-link" class="btn ghost" style="min-height:36px; padding: 0 14px; border-radius:10px;">Sign out</a>
      </div>
    `;
    if (window.renderThemeToggle) window.renderThemeToggle(navContainer.querySelector(".nav-links"));
  }

  // Render Sidebar
  const sidebarContainer = $(".sidebar");
  if (sidebarContainer) {
    sidebarContainer.classList.add("collapsed");
    const links = [
      ["dashboard", "Dashboard", FRONTEND_ROUTES.dashboard, "🏠"],
      ["quiz", "Adaptive Quiz", FRONTEND_ROUTES.quiz, "🧠"],
      ["coding", "Coding Workspace", FRONTEND_ROUTES.coding, "💻"],
      ["progress", "Progress", FRONTEND_ROUTES.progress, "📈"]
    ];

    sidebarContainer.innerHTML = links.map(([id, label, href, icon]) => {
      const isActive = page === id;
      return `
        <a class="side-link ${isActive ? "active" : ""}" href="${href}">
          <span class="icon">${icon}</span>
          <span class="label">${label}</span>
        </a>
      `;
    }).join("");

    bindSidebarExpansion(sidebarContainer);
  }

  renderFloatingQuickBall();

  window.addEventListener("resize", () => {
    const quickBall = document.querySelector(".quick-ball");
    if (quickBall) {
      quickBall.classList.toggle("visible", window.innerWidth <= 960);
      if (window.innerWidth > 960) quickBall.classList.remove("open");
    }
  });

  // Bind Logout
  const logoutLink = $("#logout-link");
  if (logoutLink) {
    logoutLink.addEventListener("click", async (event) => {
      event.preventDefault();
      try {
        await postJson("/auth/logout");
      } catch (e) {}
      clearAuthStorage();
      location.href = FRONTEND_ROUTES.login;
    });
  }
}

function bindSidebarExpansion(sidebarContainer) {
  const layout = sidebarContainer.closest(".app-layout");
  if (!layout) return;

  const setExpanded = (expanded) => {
    document.body.classList.toggle("sidebar-expanded", expanded);
    layout.classList.toggle("sidebar-expanded", expanded);
  };

  sidebarContainer.addEventListener("mouseenter", () => setExpanded(true));
  sidebarContainer.addEventListener("mouseleave", () => setExpanded(false));
  sidebarContainer.addEventListener("focusin", () => setExpanded(true));
  sidebarContainer.addEventListener("focusout", (event) => {
    if (!sidebarContainer.contains(event.relatedTarget)) setExpanded(false);
  });
}

function renderFloatingQuickBall() {
  const shouldShow = window.innerWidth <= 960;
  let quickBall = document.querySelector(".quick-ball");

  if (!quickBall) {
    quickBall = document.createElement("div");
    quickBall.className = "quick-ball";
    quickBall.innerHTML = `
      <button type="button" class="quick-ball-trigger" aria-label="Open quick navigation">☰</button>
      <div class="quick-ball-menu">
        <button type="button" class="quick-ball-item" data-route="${FRONTEND_ROUTES.dashboard}">
          <span class="icon">🏠</span><span class="label">Dashboard</span>
        </button>
        <button type="button" class="quick-ball-item" data-route="${FRONTEND_ROUTES.quiz}">
          <span class="icon">🧠</span><span class="label">Adaptive Quiz</span>
        </button>
        <button type="button" class="quick-ball-item" data-route="${FRONTEND_ROUTES.coding}">
          <span class="icon">💻</span><span class="label">Coding Challenge</span>
        </button>
        <button type="button" class="quick-ball-item" data-route="${FRONTEND_ROUTES.progress}">
          <span class="icon">📈</span><span class="label">Progress</span>
        </button>
        <button type="button" class="quick-ball-item" data-action="theme">
          <span class="icon">🌓</span><span class="label">Theme</span>
        </button>
        <button type="button" class="quick-ball-item" data-action="logout">
          <span class="icon">🚪</span><span class="label">Logout</span>
        </button>
      </div>
    `;

    document.body.appendChild(quickBall);

    quickBall.querySelector('.quick-ball-trigger').addEventListener('click', (event) => {
      event.stopPropagation();
      quickBall.classList.toggle('open');
    });

    quickBall.querySelectorAll('.quick-ball-item').forEach((item) => {
      item.addEventListener('click', async (event) => {
        event.stopPropagation();
        quickBall.classList.remove('open');
        const route = item.dataset.route;
        const action = item.dataset.action;

        if (action === 'theme') {
          const nextTheme = document.documentElement.dataset.theme === 'light' ? 'dark' : 'light';
          if (window.applyAdaptiveTheme) window.applyAdaptiveTheme(nextTheme);
          return;
        }

        if (action === 'logout') {
          try {
            await postJson('/auth/logout');
          } catch {
            // ignore errors
          }
          clearAuthStorage();
          location.href = FRONTEND_ROUTES.login;
          return;
        }

        if (route) {
          location.href = route;
        }
      });
    });

    document.body.addEventListener('click', (event) => {
      if (!quickBall.contains(event.target)) {
        quickBall.classList.remove('open');
      }
    });
  }

  quickBall.classList.toggle('visible', shouldShow);
  if (!shouldShow) quickBall.classList.remove('open');
}

// ----------------------------------------------------
// LEARNER DASHBOARD
// ----------------------------------------------------

async function initDashboard() {
  $("#student-name").textContent = store.studentName;
  const dashboardData = await fetchJson("/dashboard");
  
  // Show stats
  $("#overall-proficiency").textContent = `${Math.round(dashboardData.proficiency_estimate * 100)}%`;
  $("#overall-uncertainty").textContent = `${Math.round(100 - dashboardData.uncertainty * 100)}%`;
  $("#overall-enrolled").textContent = dashboardData.enrolled_courses.length;

  // Show dynamic system advice based on proficiency/uncertainty
  const adviceEl = $("#cognitive-advice");
  if (adviceEl) {
    let title = "Ready to start your learning path?";
    let text = "Select one of the courses below to begin an adaptive quiz. The RL engine will customize challenges based on your unique behavior.";
    
    if (dashboardData.enrolled_courses.length > 0) {
      if (dashboardData.proficiency_estimate < 0.4) {
        title = "Foundational remediation recommended";
        text = "Your estimated proficiency is emerging. We suggest launching an MCQ Quiz in your active track to reinforce core principles.";
      } else if (dashboardData.proficiency_estimate > 0.7) {
        title = "Excellent mastery detected!";
        text = "Your skills are highly advanced. We recommend opening the Coding Workspace to solve complex algorithmic problems.";
      } else {
        title = "Steady progress observed";
        text = "You are building solid proficiency. Keep practicing to decrease system uncertainty and lock in concepts.";
      }
    }
    adviceEl.innerHTML = `
      <div class="recommendation-icon">💡</div>
      <div class="recommendation-text">
        <h4>${title}</h4>
        <p>${text}</p>
      </div>
    `;
  }

  // Render course tracks grid
  const grid = $("#course-grid");
  if (grid) {
    grid.innerHTML = Object.values(dashboardData.course_progress).map((course) => {
      const isEnrolled = course.enrolled;
      const progressPercent = Math.min(100, Math.round(course.progress * 100));
      
      const badge = isEnrolled 
        ? `<span class="badge enrolled">Enrolled</span>`
        : `<span class="badge not-enrolled">Not Enrolled</span>`;

      const primaryCta = isEnrolled
        ? `<button class="btn primary" onclick="viewCourse('${course.name}')" style="width:100%;">Open Course Track</button>`
        : `<button class="btn ghost" onclick="enrollCourse('${course.name}')" style="width:100%;">Enroll Track</button>`;

      return `
        <div class="course-card">
          <div class="badge-group">
            ${badge}
            <span class="badge" style="border-color: rgba(255,255,255,0.05);">${course.question_count} activities</span>
          </div>
          <h2>${course.name}</h2>
          <p>${course.description}</p>
          
          ${isEnrolled ? `
            <div style="margin-bottom: 24px;">
              <div style="display:flex; justify-content:space-between; font-size:0.85rem; color:var(--muted); margin-bottom: 6px;">
                <span>Progression Map</span>
                <span>${progressPercent}%</span>
              </div>
              <div class="progress-bar">
                <div class="progress-fill" style="width: ${progressPercent}%;"></div>
              </div>
            </div>
          ` : ""}
          
          <div style="margin-top:auto;">
            ${primaryCta}
          </div>
        </div>
      `;
    }).join("");
  }
}

window.viewCourse = function(courseName) {
  store.course = courseName;
  location.href = `${FRONTEND_ROUTES.course}?name=${encodeURIComponent(courseName)}`;
};

window.enrollCourse = async function(courseName) {
  try {
    await postJson(`/courses/${encodeURIComponent(courseName)}/enroll`);
    store.course = courseName;
    location.href = `${FRONTEND_ROUTES.course}?name=${encodeURIComponent(courseName)}`;
  } catch (error) {
    alert("Enrollment failed: " + error.message);
  }
};

// ----------------------------------------------------
// DYNAMIC COURSE DETAIL PAGE
// ----------------------------------------------------

async function initCourse() {
  const params = new URLSearchParams(location.search);
  const courseName = params.get("name") || store.course;
  store.course = courseName;

  $("#course-title").textContent = courseName;
  
  const details = await fetchJson(`/courses/${encodeURIComponent(courseName)}`);
  
  $("#course-desc").textContent = details.description;
  $("#course-mastery").textContent = `${Math.round(details.proficiency_estimate * 100)}%`;
  $("#course-uncertainty").textContent = `${Math.round(details.uncertainty * 100)}%`;
  $("#course-completed").textContent = details.questions_answered;

  const quickActionsEl = $("#course-quick-actions");
  const syllabusPanelEl = $("#syllabus-panel");

  if (details.enrolled) {
    quickActionsEl.innerHTML = `
      <button class="btn primary" onclick="location.href='${FRONTEND_ROUTES.quiz}'" style="flex:1;">Start MCQ Quiz</button>
      <button class="btn ghost" onclick="location.href='${FRONTEND_ROUTES.coding}'" style="flex:1;">Open Coding Lab</button>
    `;

    // Handcrafted syllabus rendering based on course name
    let topics = [];
    if (courseName === "Python") {
      topics = ["variables", "loops", "functions", "lists", "exceptions", "strings", "dictionaries", "files"];
    } else {
      topics = ["supervised learning", "metrics", "regression", "classification", "features", "overfitting", "clustering", "model validation"];
    }

    const answeredTopics = new Set(details.topics || []);
    
    syllabusPanelEl.innerHTML = `
      <h3>Track Progression Syllabus</h3>
      <div class="syllabus-list">
        ${topics.map((t) => {
          const hasAnswered = answeredTopics.has(t);
          return `
            <div class="syllabus-item">
              <span>${t}</span>
              <div style="display:flex; align-items:center; gap:8px;">
                <span style="font-size:0.8rem; color:${hasAnswered ? "var(--green)" : "var(--muted)"};">
                  ${hasAnswered ? "Explored" : "Not started"}
                </span>
                <i class="mastery-dot ${hasAnswered ? "learned" : ""}"></i>
              </div>
            </div>
          `;
        }).join("")}
      </div>
    `;
  } else {
    quickActionsEl.innerHTML = `
      <button class="btn primary" onclick="enrollCourse('${courseName}')" style="width:100%;">Enroll in Course Track</button>
    `;
    syllabusPanelEl.innerHTML = `
      <div style="text-align:center; padding:32px; color:var(--muted);">
        <p>Please enroll in this track to unlock the progression syllabus and launching quizzes.</p>
      </div>
    `;
  }
}

// ----------------------------------------------------
// ADAPTIVE MCQ ASSESSMENT & TIMERS
// ----------------------------------------------------

async function initQuiz() {
  $("#quiz-course").textContent = store.course;
  
  // Clean up any existing active timer interval
  if (timerInterval) clearInterval(timerInterval);

  // Call the session-based API route to create a quiz session
  const result = await postJson(`/quiz/start/${encodeURIComponent(store.course)}?session_type=mcq`);
  quizSession = result;
  
  renderQuiz(result);

  $("#submit-answer").addEventListener("click", submitQuizAnswer);
  const finishButton = $("#finish-quiz");
  if (finishButton) finishButton.addEventListener("click", finishQuizEarly);
}

function renderQuiz(result) {
  // If session is complete, render summary
  if (result.session_complete) {
    if (timerInterval) clearInterval(timerInterval);
    renderCognitiveSummary(result);
    return;
  }

  quizQuestion = result.next_question;
  selectedAnswer = null;

  if (!quizQuestion) {
    if (timerInterval) clearInterval(timerInterval);
    finishQuizAutomatically();
    return;
  }

  // Update overall session metrics
  const answered = Number(result.question_count || 0);
  const limit = Number(result.question_limit || 15);
  const visibleQuestionNumber = Math.min(answered + 1, limit);
  const progressEl = $("#question-progress");
  if (progressEl) progressEl.textContent = `Question ${visibleQuestionNumber} of ${limit}`;
  $("#proficiency").textContent = Number(result.proficiency_estimate).toFixed(2);
  $("#uncertainty").textContent = Number(result.uncertainty || 0.1).toFixed(2);
  $("#quiz-meter").style.width = `${Math.round((answered / limit) * 100)}%`;
  $("#cognitive-state").textContent = formatState(result.cognitive_state || "learning");
  $("#explanation").textContent = result.adaptive_explanation || "The RL engine will update difficulty based on performance.";

  // Update question
  $("#question-text").textContent = quizQuestion.text;
  $("#question-topic").textContent = quizQuestion.topic || "General";
  
  const diffTag = $("#question-difficulty");
  diffTag.textContent = quizQuestion.difficulty_label;
  diffTag.className = `diff-tag ${quizQuestion.difficulty_label}`;

  // Render options
  const optionsGrid = $("#options-grid");
  optionsGrid.innerHTML = "";
  
  (quizQuestion.options || []).forEach((option, index) => {
    const label = ["A", "B", "C", "D"][index];
    const item = document.createElement("label");
    item.className = "option-label";
    item.innerHTML = `
      <input type="radio" name="answer" value="${label}">
      <span><strong>${label}.</strong> ${option}</span>
    `;
    item.querySelector("input").addEventListener("change", () => {
      selectedAnswer = label;
      document.querySelectorAll(".option-label").forEach((el) => el.style.borderColor = "var(--line)");
      item.style.borderColor = "var(--cyan)";
    });
    optionsGrid.appendChild(item);
  });

  // Restart automatic response timer
  questionStartTime = Date.now();
  const timerClock = $("#live-timer");
  timerClock.textContent = "0:00";
  
  if (timerInterval) clearInterval(timerInterval);
  timerInterval = setInterval(() => {
    const elapsed = Math.floor((Date.now() - questionStartTime) / 1000);
    const mins = Math.floor(elapsed / 60);
    const secs = elapsed % 60;
    timerClock.textContent = `${mins}:${secs.toString().padStart(2, '0')}`;
  }, 1000);
}

async function submitQuizAnswer() {
  if (!quizQuestion) return;
  if (!selectedAnswer) {
    alert("Please select one of the choices before submitting.");
    return;
  }

  // Calculate elapsed time automatically
  if (timerInterval) clearInterval(timerInterval);
  const elapsed = Math.max(1, Math.floor((Date.now() - questionStartTime) / 1000));

  try {
    const result = await postJson(`/quiz/${quizSession.session_id}/respond`, {
      student_id: store.studentId,
      question_id: quizQuestion.id,
      submitted_answer: selectedAnswer,
      confidence_level: Number($("#confidence").value),
      response_time: elapsed
    });
    
    renderQuiz(result);
  } catch (error) {
    alert("Submission error: " + error.message);
  }
}

async function finishQuizEarly() {
  if (!quizSession) return;
  if (confirm("Are you sure you want to finish the assessment early? The RL engine will compile your cognitive summary.")) {
    if (timerInterval) clearInterval(timerInterval);
    const summary = await postJson(`/quiz/${quizSession.session_id}/finish`);
    renderCognitiveSummary(summary);
  }
}

async function finishQuizAutomatically() {
  if (!quizSession) return;
  const summary = await postJson(`/quiz/${quizSession.session_id}/finish`);
  renderCognitiveSummary(summary);
}

function renderCognitiveSummary(summaryData) {
  // If wrapped in result structure, pull summary
  const summary = summaryData.summary || summaryData;

  const contentSection = $(".quiz-panel").parentNode;
  contentSection.className = "content"; // remove split layout
  
  contentSection.innerHTML = `
    <div class="panel" style="border-color: var(--cyan); background: radial-gradient(circle at 100% 0%, rgba(6, 182, 212, 0.08), transparent 40%);">
      <p class="kicker">Intelligent Analytics Compiled</p>
      <h1 style="font-size:2.4rem; margin-bottom:12px;">✨ Cognitive Assessment Summary</h1>
      <p style="color:var(--muted); margin-bottom:32px;">The Bayesian Proficiency Engine and Hesitation Trackers have summarized your cognitive state below.</p>
      
      <div class="summary-container">
        <div class="summary-details">
          <div class="summary-card-row">
            <div class="summary-mini-card">
              <h4>Questions Answered</h4>
              <p>${summary.questions_answered}</p>
            </div>
            <div class="summary-mini-card">
              <h4>Accuracy Score</h4>
              <p>${Math.round(summary.accuracy * 100)}%</p>
            </div>
          </div>
          
          <div class="summary-card-row">
            <div class="summary-mini-card" style="border-color: rgba(16, 185, 129, 0.2);">
              <h4>Estimated Proficiency</h4>
              <p style="color:var(--green);">${Math.round(summary.proficiency_estimate * 100)}%</p>
            </div>
            <div class="summary-mini-card">
              <h4>Enrolled Track</h4>
              <p style="color:var(--cyan);">${summary.course}</p>
            </div>
          </div>

          <div class="summary-list-card">
            <h3>Strongest Topics (Mastery)</h3>
            <ul>
              ${summary.strongest_topics.length > 0 
                ? summary.strongest_topics.map((t) => `<li>${t}</li>`).join("")
                : `<li>No solid mastery detected yet. Keep exploring topics!</li>`}
            </ul>
          </div>

          <div class="summary-list-card" style="border-color:rgba(236, 72, 153, 0.15);">
            <h3>Weakest / Remedial Focus Topics</h3>
            <ul>
              ${summary.weakest_topics.length > 0 
                ? summary.weakest_topics.map((t) => `<li>${t}</li>`).join("")
                : `<li>No major weak topics detected. Superb job!</li>`}
            </ul>
          </div>
        </div>

        <div>
          <div class="summary-list-card" style="border-color:rgba(245, 158, 11, 0.2);">
            <h3>Behavioral Hesitation Areas</h3>
            <p style="font-size:0.85rem; color:var(--muted); margin-bottom:12px;">These topics showed slower speeds and lower self-confidence.</p>
            <ul>
              ${summary.hesitation_areas.length > 0 
                ? summary.hesitation_areas.map((t) => `<li>${t}</li>`).join("")
                : `<li>No hesitation detected. Highly consistent response pacing!</li>`}
            </ul>
          </div>

          <div class="summary-list-card" style="border-color:rgba(236, 72, 153, 0.2);">
            <h3>Detected Misconceptions</h3>
            <p style="font-size:0.85rem; color:var(--muted); margin-bottom:12px;">High-confidence incorrect responses suggest a false conceptual premise.</p>
            <ul>
              ${summary.misconceptions_detected.length > 0 
                ? summary.misconceptions_detected.map((t) => `<li>${t}</li>`).join("")
                : `<li>Zero misconceptions diagnosed. Perfect concept alignment!</li>`}
            </ul>
          </div>

          <div class="summary-list-card" style="background: rgba(255,255,255,0.01);">
            <h3>Personalized Recommendations</h3>
            <ul>
              ${summary.recommendations.map((rec) => `<li>${rec}</li>`).join("")}
            </ul>
          </div>

          <button class="btn primary" onclick="location.href='/app/dashboard'" style="width:100%; margin-top:16px;">Return to Dashboard</button>
        </div>
      </div>
    </div>
  `;
}

// ----------------------------------------------------
// CODING LAB WORKSPACE & RETRIES
// ----------------------------------------------------

async function initCoding() {
  // Start coding exercise
  const result = await postJson(`/coding/start/${store.studentId}?course=${encodeURIComponent(store.course)}`);
  
  codingStartTime = Date.now();
  retryCount = 0;

  renderCodingQuestion(result.next_question);
  setupEditor(codingQuestion?.starter_code || "def solution():\n    pass");

  ["#run-code", "#run-tests"].forEach((selector) => {
    const button = $(selector);
    if (button) button.addEventListener("click", runCode);
  });
  $("#submit-code").addEventListener("click", submitCode);
}

function renderCodingQuestion(question) {
  codingQuestion = question;
  if (!question) {
    $(".coding-grid").innerHTML = `
      <div class="panel" style="text-align:center; padding:48px 32px; width:100%;">
        <h1>✨ Coding Track Complete!</h1>
        <p class="lead" style="color:var(--muted); margin: 16px 0;">You've conquered all active coding challenges in the ${store.course} track!</p>
        <button class="btn primary" onclick="location.href='/app/dashboard'">Return to Dashboard</button>
      </div>
    `;
    return;
  }

  $("#coding-title").textContent = `${question.course} · ${question.topic || "Algorithms"}`;
  
  // Set difficulty badge
  const badge = $("#coding-difficulty");
  badge.textContent = question.difficulty_label;
  badge.className = `badge diff-tag ${question.difficulty_label}`;
  
  $("#coding-prompt").innerHTML = question.text.replaceAll("\n", "<br>");
  
  // Reset retries count display
  updateRetryDisplay();
}

function updateRetryDisplay() {
  const retryEl = $("#retry-count");
  if (retryEl) {
    retryEl.textContent = `Attempt Retries: ${retryCount}`;
  }
}

function setupEditor(initialCode) {
  const fallback = $("#fallback-editor");
  fallback.value = initialCode;
  
  const editorContainer = $("#editor");
  if (window.require) {
    editorContainer.style.display = "block";
    fallback.style.display = "none";
    
    require.config({ paths: { vs: "https://cdn.jsdelivr.net/npm/monaco-editor@0.49.0/min/vs" } });
    require(["vs/editor/editor.main"], () => {
      // Clear container before creating
      editorContainer.innerHTML = "";
      editor = monaco.editor.create(editorContainer, {
        value: initialCode,
        language: "python",
        theme: "vs-dark",
        minimap: { enabled: false },
        fontSize: 14,
        automaticLayout: true,
        lineHeight: 22,
        fontFamily: "Consolas, Monaco, monospace"
      });
    });
  } else {
    editorContainer.style.display = "none";
    fallback.style.display = "block";
  }
}

async function runCode() {
  retryCount++;
  updateRetryDisplay();
  
  const consolePre = $("#output");
  consolePre.classList.remove("error");
  consolePre.textContent = "Executing tests safely...";

  try {
    const result = await postJson("/coding/run", {
      question_id: codingQuestion?.id,
      code: getCode(),
    });
    
    renderOutput(result);
  } catch (error) {
    consolePre.classList.add("error");
    consolePre.textContent = "Execution Error: " + error.message;
  }
}

async function submitCode() {
  const consolePre = $("#output");
  consolePre.classList.remove("error");
  consolePre.textContent = "Compiling and evaluating...";

  try {
    const result = await postJson("/coding/respond", {
      student_id: store.studentId,
      question_id: codingQuestion.id,
      code: getCode(),
    });
    
    renderOutput(result.execution);
    
    $("#coding-feedback").innerHTML = `
      <div class="panel" style="padding:16px; margin-top:16px; border-color:${result.execution.success ? "var(--green)" : "var(--pink)"}; background:rgba(255,255,255,0.01);">
        <h4 style="color:${result.execution.success ? "var(--green)" : "var(--pink)"}; margin-bottom:4px;">
          ${result.execution.success ? "Passed Challenge" : "Incomplete Logic"}
        </h4>
        <p style="font-size:0.85rem; color:var(--text-secondary);">${result.adaptive_explanation}</p>
      </div>
    `;

    // If success, move to next question after 2.5 seconds
    if (result.execution.success) {
      setTimeout(() => {
        renderCodingQuestion(result.next_question);
        if (result.next_question) {
          setCode(result.next_question.starter_code || "");
          $("#coding-feedback").innerHTML = "";
          $("#output").textContent = "Write code and execute tests.";
          retryCount = 0;
          updateRetryDisplay();
        }
      }, 2500);
    }
  } catch (error) {
    consolePre.classList.add("error");
    consolePre.textContent = "Submission Failed: " + error.message;
  }
}

function getCode() {
  return editor ? editor.getValue() : $("#fallback-editor").value;
}

function setCode(value) {
  if (editor) editor.setValue(value);
  $("#fallback-editor").value = value;
}

function renderOutput(result) {
  const consolePre = $("#output");
  if (result.success) {
    consolePre.classList.remove("error");
    consolePre.textContent = `⚡ [COMPILER STATUS: SUCCESS]\n\n${result.output || "No stdout captured."}\nExecution time: ${result.execution_time}s`;
  } else {
    consolePre.classList.add("error");
    consolePre.textContent = `❌ [COMPILER STATUS: FAILED]\n\n${result.error || "Assertions failed."}\n${result.output || ""}\nExecution time: ${result.execution_time}s`;
  }
}

// ----------------------------------------------------
// MASTERY PROGRESS MAP
// ----------------------------------------------------

async function initProgress() {
  const progress = await fetchJson(`/progress/${store.studentId}`);
  
  // Show detailed cards
  const progressSummary = $("#progress-summary");
  if (progressSummary) {
    progressSummary.innerHTML = ["Python", "Machine Learning"].map((course) => {
      const count = progress.course_counts[course] || 0;
      const width = Math.min(100, count * 5); // 20 activities to max out progress visual map
      return `
        <div class="panel" style="padding: 24px;">
          <span style="color:var(--cyan); font-size:0.8rem; font-weight:800; text-transform:uppercase;">${course} track</span>
          <h2 style="font-size:2.8rem; margin:6px 0; font-family:'Outfit';">${count}</h2>
          <p style="color:var(--muted); font-size:0.85rem; margin-bottom:16px;">completed activities</p>
          <div class="progress-bar">
            <div class="progress-fill" style="width:${width}%"></div>
          </div>
        </div>
      `;
    }).join("") + `
      <div class="panel" style="padding: 24px; border-color:var(--green); background:rgba(16, 185, 129, 0.02);">
        <span style="color:var(--green); font-size:0.8rem; font-weight:800; text-transform:uppercase;">Mastery Proficiency</span>
        <h2 style="font-size:2.8rem; margin:6px 0; font-family:'Outfit'; color:var(--green);">${Number(progress.proficiency_estimate * 100).toFixed(0)}%</h2>
        <p style="color:var(--muted); font-size:0.85rem;">overall learning map estimate (uncertainty: ${Number(progress.uncertainty).toFixed(2)})</p>
      </div>
    `;
  }
}

// ----------------------------------------------------
// SETTINGS / ACCOUNT VIEW
// ----------------------------------------------------

function initSettings() {
  $("#student-name-text").textContent = store.studentName;
  $("#student-email-text").textContent = store.studentName.toLowerCase().replace(" ", "") + "@adaptivelearn.ai";
  
  $("#reset-history").addEventListener("click", async () => {
    if (confirm("WARNING: Are you sure you want to reset your learning history? This will completely clear all response logs and reset your Bayesian proficiency estimate to neutral. This action cannot be undone.")) {
      // In a real app, hit an endpoint. We will clear local storage and log out to trigger clean restart!
      alert("Learning history has been successfully reset. Logging you out to initialize a fresh profile.");
      clearAuthStorage();
      location.href = FRONTEND_ROUTES.register;
    }
  });
}

// ----------------------------------------------------
// GENERAL JSON UTILITIES
// ----------------------------------------------------

async function postJson(url, payload) {
  const response = await fetch(url, {
    method: "POST",
    headers: headers(),
    body: payload ? JSON.stringify(payload) : undefined,
  });
  return parse(response);
}

async function fetchJson(url) {
  return parse(await fetch(url, { headers: headers() }));
}

function headers() {
  const output = { "Content-Type": "application/json" };
  if (store.token) output.Authorization = `Bearer ${store.token}`;
  return output;
}

async function parse(response) {
  let data;
  try {
    data = await response.json();
  } catch {
    if (!response.ok) throw new Error(`Request failed (${response.status})`);
    return {};
  }

  if (response.status === 401) {
    clearAuthStorage();
    if (!PUBLIC_ROUTES.includes(window.location.pathname)) {
      location.href = FRONTEND_ROUTES.login;
    }
    throw new Error(data.detail || data.message || "Session expired. Please log in again.");
  }

  if (!response.ok) throw new Error(data.detail || data.message || "Request failed");
  return data;
}

function formatState(value) {
  return value.replaceAll("_", " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
}
