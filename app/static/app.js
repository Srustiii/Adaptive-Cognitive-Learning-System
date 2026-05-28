/**
 * AdaptiveLearn AI - Professional Multi-Page Adaptive Learning Platform
 * Built with modern SPA architecture, RL-based adaptive intelligence, and hesitation analysis
 */

// ============================================================================
// STATE MANAGEMENT
// ============================================================================

const appState = {
  currentPage: 'landing',
  token: localStorage.getItem('token') || null,
  user: null,
  dashboard: null,
  currentCourse: null,
  quizSession: null,
  quizTimerInterval: null,
  quizStartTime: null,
};

// ============================================================================
// API SERVICE
// ============================================================================

const apiService = {
  baseURL: window.location.origin,

  async request(method, path, body = null) {
    const options = {
      method,
      headers: {
        'Content-Type': 'application/json',
      },
    };

    if (appState.token) {
      options.headers['Authorization'] = `Bearer ${appState.token}`;
    }

    if (body) {
      options.body = JSON.stringify(body);
    }

    try {
      const response = await fetch(`${this.baseURL}${path}`, options);
      if (!response.ok) {
        if (response.status === 401) {
          this.handleLogout();
          throw new Error('Session expired. Please log in again.');
        }
        const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
        throw new Error(error.detail || `HTTP ${response.status}`);
      }
      return await response.json();
    } catch (error) {
      console.error('API Error:', error);
      throw error;
    }
  },

  handleLogout() {
    appState.token = null;
    appState.user = null;
    localStorage.removeItem('token');
    navigateTo('landing');
  },

  // Auth Endpoints
  async register(name, email, password) {
    const data = await this.request('POST', '/auth/register', { name, email, password });
    appState.token = data.token;
    appState.user = data.student;
    localStorage.setItem('token', data.token);
    return data;
  },

  async login(email, password) {
    const data = await this.request('POST', '/auth/login', { email, password });
    appState.token = data.token;
    appState.user = data.student;
    localStorage.setItem('token', data.token);
    return data;
  },

  async logout() {
    try {
      await this.request('POST', '/auth/logout');
    } catch (e) {
      // Ignore logout errors
    }
    this.handleLogout();
  },

  async getMe() {
    return this.request('GET', '/auth/me');
  },

  // Dashboard & Courses
  async getDashboard() {
    return this.request('GET', '/dashboard');
  },

  async getCourses() {
    return this.request('GET', '/courses');
  },

  async getCourseDetail(courseName) {
    return this.request('GET', `/courses/${courseName}`);
  },

  async enrollCourse(courseName) {
    return this.request('POST', `/courses/${courseName}/enroll`);
  },

  // Quiz Session Management
  async startQuiz(courseName, sessionType = 'mcq') {
    const data = await this.request('POST', `/quiz/start/${courseName}`, { session_type: sessionType });
    appState.quizSession = data;
    appState.quizStartTime = Date.now();
    return data;
  },

  async submitQuizResponse(sessionId, response) {
    return this.request('POST', `/quiz/${sessionId}/respond`, response);
  },

  async finishQuiz(sessionId) {
    return this.request('POST', `/quiz/${sessionId}/finish`);
  },

  async getQuizSummary(sessionId) {
    return this.request('GET', `/quiz/${sessionId}/summary`);
  },

  // Progress
  async getProgress(studentId) {
    return this.request('GET', `/progress/${studentId}`);
  },
};

// ============================================================================
// TIMER UTILITIES
// ============================================================================

function getQuizElapsedSeconds() {
  if (!appState.quizStartTime) return 0;
  return Math.floor((Date.now() - appState.quizStartTime) / 1000);
}

function formatTimer(seconds) {
  const mins = Math.floor(seconds / 60);
  const secs = seconds % 60;
  return `${mins}:${secs.toString().padStart(2, '0')}`;
}

// ============================================================================
// PAGE RENDERERS
// ============================================================================

function renderLanding() {
  return `
    <nav class="top-nav">
      <a class="brand" href="#"><span></span>AdaptiveLearn AI</a>
      <div class="nav-links">
        <a href="#" onclick="navigateTo('login'); return false;">Login</a>
        <a class="nav-cta" href="#" onclick="navigateTo('register'); return false;">Start learning</a>
      </div>
    </nav>
    <main class="landing">
      <section class="hero">
        <div>
          <p class="kicker">RL-powered adaptive education</p>
          <h1>Master Python & ML at your own pace.</h1>
          <p class="lead">Personalized adaptive quizzes that respond to your confidence, hesitation, and learning patterns. Powered by reinforcement learning and Bayesian proficiency estimation.</p>
          <div class="actions">
            <a class="btn primary" href="#" onclick="navigateTo('register'); return false;">Get started free</a>
            <a class="btn ghost" href="#" onclick="navigateTo('login'); return false;">I have an account</a>
          </div>
        </div>
        <div class="hero-product-card">
          <div class="pulse-ring"></div>
          <p style="color: var(--cyan); font-weight: 600;">Adaptive Intelligence</p>
          <strong>RL + Bayesian</strong>
          <span>Personalized learning path</span>
        </div>
      </section>
      <section class="feature-grid">
        <article>
          <h3>🧠 Adaptive Quizzes</h3>
          <p>MCQs that dynamically adjust based on your confidence, response time, and correctness.</p>
        </article>
        <article>
          <h3>💻 Coding Practice</h3>
          <p>Write Python code with real-time execution feedback and difficulty adaptation.</p>
        </article>
        <article>
          <h3>📊 Smart Insights</h3>
          <p>Detailed cognitive analysis revealing your strengths, hesitation patterns, and growth areas.</p>
        </article>
      </section>
    </main>
  `;
}

function renderLogin() {
  return `
    <nav class="top-nav">
      <a class="brand" href="#" onclick="navigateTo('landing'); return false;"><span></span>AdaptiveLearn AI</a>
    </nav>
    <main class="auth-page">
      <div class="auth-card">
        <h1>Welcome back</h1>
        <p style="color: var(--muted); margin-bottom: 28px;">Sign in to continue your adaptive learning journey.</p>
        <form id="login-form" onsubmit="handleLogin(event)">
          <div class="form-group">
            <label>Email</label>
            <input type="email" id="login-email" required>
          </div>
          <div class="form-group">
            <label>Password</label>
            <input type="password" id="login-password" required>
          </div>
          <button type="submit" class="btn primary" style="width: 100%;">Sign in</button>
          <p id="login-error" style="color: var(--pink); margin-top: 12px; display: none;"></p>
        </form>
        <p style="text-align: center; margin-top: 20px; color: var(--muted);">
          New here? <a href="#" onclick="navigateTo('register'); return false;" style="color: var(--cyan);">Create an account</a>
        </p>
      </div>
    </main>
  `;
}

function renderRegister() {
  return `
    <nav class="top-nav">
      <a class="brand" href="#" onclick="navigateTo('landing'); return false;"><span></span>AdaptiveLearn AI</a>
    </nav>
    <main class="auth-page">
      <div class="auth-card">
        <h1>Join AdaptiveLearn</h1>
        <p style="color: var(--muted); margin-bottom: 28px;">Start your personalized learning journey today.</p>
        <form id="register-form" onsubmit="handleRegister(event)">
          <div class="form-group">
            <label>Full Name</label>
            <input type="text" id="register-name" required>
          </div>
          <div class="form-group">
            <label>Email</label>
            <input type="email" id="register-email" required>
          </div>
          <div class="form-group">
            <label>Password</label>
            <input type="password" id="register-password" required>
          </div>
          <button type="submit" class="btn primary" style="width: 100%;">Create account</button>
          <p id="register-error" style="color: var(--pink); margin-top: 12px; display: none;"></p>
        </form>
        <p style="text-align: center; margin-top: 20px; color: var(--muted);">
          Already have an account? <a href="#" onclick="navigateTo('login'); return false;" style="color: var(--cyan);">Sign in</a>
        </p>
      </div>
    </main>
  `;
}

async function renderDashboard() {
  try {
    const dashboard = await apiService.getDashboard();
    appState.dashboard = dashboard;

    const courseCards = Object.values(dashboard.course_progress || {})
      .map(course => {
        const enrollBtn = course.enrolled
          ? `<a class="btn primary" style="margin-top: 12px; width: 100%; text-align: center;" href="#" onclick="startQuizSession('${course.name}'); return false;">Start Quiz</a>`
          : `<a class="btn ghost" style="margin-top: 12px; width: 100%; text-align: center;" href="#" onclick="enrollInCourse('${course.name}'); return false;">Enroll</a>`;

        return `
          <div class="course-card">
            <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 12px;">
              <div>
                <h3 style="margin: 0 0 8px 0;">${course.name}</h3>
                <p style="margin: 0; font-size: 0.9rem; color: var(--muted);">${course.description}</p>
              </div>
              ${course.enrolled ? '<span style="background: rgba(126, 231, 135, 0.2); color: var(--green); padding: 4px 12px; border-radius: 20px; font-size: 0.8rem; font-weight: 600;">Enrolled</span>' : ''}
            </div>
            <div style="margin-top: 16px;">
              <div class="progress-bar">
                <div class="progress-fill" style="width: ${Math.min(course.progress * 100, 100)}%;"></div>
              </div>
              <p style="font-size: 0.85rem; margin-top: 8px; color: var(--muted);">
                ${course.question_count} questions answered
              </p>
            </div>
            ${enrollBtn}
          </div>
        `;
      }).join('');

    return `
      <nav class="top-nav">
        <a class="brand" href="#" onclick="navigateTo('dashboard'); return false;"><span></span>AdaptiveLearn AI</a>
        <div class="nav-links">
          <a href="#" onclick="navigateTo('progress'); return false;">Progress</a>
          <a href="#" onclick="navigateTo('settings'); return false;">Settings</a>
          <a href="#" onclick="handleLogout(); return false;">Logout</a>
        </div>
      </nav>
      <main style="max-width: 1180px; margin: 0 auto; padding: 28px 14px;">
        <div style="margin-bottom: 48px;">
          <h1>Welcome, ${appState.user.name}! 👋</h1>
          <p class="lead" style="color: var(--muted); margin-top: 8px;">Your adaptive learning path awaits</p>
        </div>
        
        <div class="mini-stats" style="margin-bottom: 48px;">
          <div class="stat-card">
            <div class="stat-label">Proficiency</div>
            <div class="stat-value">${(dashboard.proficiency_estimate * 100).toFixed(0)}%</div>
            <div class="stat-subtext">Overall mastery</div>
          </div>
          <div class="stat-card">
            <div class="stat-label">Confidence</div>
            <div class="stat-value">${Math.round(100 - dashboard.uncertainty * 10 * 100)}%</div>
            <div class="stat-subtext">System confidence</div>
          </div>
          <div class="stat-card">
            <div class="stat-label">Courses</div>
            <div class="stat-value">${dashboard.enrolled_courses.length}</div>
            <div class="stat-subtext">Enrolled</div>
          </div>
        </div>

        <h2 style="margin-bottom: 20px;">Your Courses</h2>
        <div class="course-grid">
          ${courseCards}
        </div>
      </main>
    `;
  } catch (error) {
    console.error('Error rendering dashboard:', error);
    return '<main><p style="color: var(--pink); padding: 28px;">Error loading dashboard: ' + error.message + '</p></main>';
  }
}

async function renderQuizSession(courseName) {
  try {
    if (!appState.quizSession) {
      appState.quizSession = await apiService.startQuiz(courseName);
    }

    const question = appState.quizSession.next_question;

    if (!question) {
      return `
        <main style="max-width: 800px; margin: 0 auto; padding: 28px 14px;">
          <div class="panel" style="text-align: center; padding: 48px 32px;">
            <h1>✨ Quiz Complete!</h1>
            <p class="lead" style="margin: 16px 0; color: var(--muted);">You've completed the adaptive assessment for ${courseName}.</p>
            <div style="margin-top: 28px;">
              <p style="font-size: 1.2rem; margin: 12px 0;"><strong>${appState.quizSession.correct_count || 0}</strong> / <strong>${appState.quizSession.question_count || 0}</strong> correct</p>
              <p style="color: var(--muted); margin: 12px 0;">Proficiency: <strong>${(appState.quizSession.proficiency_estimate * 100).toFixed(0)}%</strong></p>
            </div>
            <button class="btn primary" style="margin-top: 28px;" onclick="navigateTo('dashboard')">Back to Dashboard</button>
          </div>
        </main>
      `;
    }

    const optionsHtml = question.options
      ? question.options.map((opt, i) => `
          <label class="option-label">
            <input type="radio" name="answer" value="${opt}" id="option-${i}">
            <span>${opt}</span>
          </label>
        `).join('')
      : '';

    return `
      <nav class="top-nav">
        <a class="brand" href="#" onclick="navigateTo('dashboard'); return false;"><span></span>AdaptiveLearn AI</a>
        <div style="display: flex; gap: 20px; align-items: center;">
          <div style="text-align: right;">
            <div class="timer-display" style="font-weight: bold; font-size: 1.2rem; color: var(--cyan);">0:00</div>
            <div style="font-size: 0.85rem; color: var(--muted);">Question ${appState.quizSession.question_count || 1}</div>
          </div>
          <span style="color: var(--muted);">${courseName}</span>
        </div>
      </nav>
      <main style="max-width: 800px; margin: 0 auto; padding: 28px 14px;">
        <div class="panel" style="padding: 32px;">
          <div style="margin-bottom: 28px;">
            <h2>${question.text}</h2>
            <div style="display: flex; gap: 12px; margin-top: 12px; flex-wrap: wrap;">
              <span style="background: rgba(102, 140, 255, 0.2); color: var(--blue); padding: 4px 12px; border-radius: 20px; font-size: 0.85rem;">Difficulty: <strong>${question.difficulty_label}</strong></span>
            </div>
          </div>
          
          <form id="quiz-form" onsubmit="handleQuizResponse(event)">
            <div class="options-group">
              ${optionsHtml}
            </div>
            
            <div style="margin-top: 28px;">
              <label style="display: block;">
                <div style="display: flex; justify-content: space-between; margin-bottom: 12px;">
                  <span style="font-weight: 600;">Your Confidence</span>
                  <span id="confidence-value" style="color: var(--cyan); font-weight: 600;">50%</span>
                </div>
                <input type="range" id="confidence" min="0" max="1" step="0.1" value="0.5" style="width: 100%;">
              </label>
            </div>

            <div style="display: flex; gap: 12px; margin-top: 28px;">
              <button type="submit" class="btn primary" style="flex: 1;">Submit Answer</button>
              <button type="button" class="btn ghost" style="flex: 1;" onclick="finishQuizEarly(); return false;">Finish Quiz</button>
            </div>
          </form>
        </div>
      </main>
      <script>
        (function initQuizPage() {
          const timer = setInterval(() => {
            const elapsed = getQuizElapsedSeconds();
            const timerEl = document.querySelector('.timer-display');
            if (timerEl) timerEl.textContent = formatTimer(elapsed);
          }, 1000);
          
          const confInput = document.getElementById('confidence');
          if (confInput) {
            confInput.addEventListener('input', (e) => {
              const confValue = document.getElementById('confidence-value');
              if (confValue) confValue.textContent = Math.round(e.target.value * 100) + '%';
            });
          }

          window.quizTimerInterval = timer;
        })();
      </script>
    `;
  } catch (error) {
    console.error('Error rendering quiz:', error);
    return '<main><p style="color: var(--pink); padding: 28px;">Error loading quiz: ' + error.message + '</p></main>';
  }
}

async function renderProgress() {
  try {
    const dashboard = await apiService.getDashboard();
    const courseProgressCards = Object.values(dashboard.course_progress || {})
      .map(course => `
        <div class="panel" style="padding: 24px;">
          <h3 style="margin-top: 0;">${course.name}</h3>
          <div class="progress-bar" style="margin: 16px 0;">
            <div class="progress-fill" style="width: ${Math.min(course.progress * 100, 100)}%;"></div>
          </div>
          <div style="display: flex; justify-content: space-between; margin-top: 12px; font-size: 0.9rem;">
            <span>${course.question_count} questions answered</span>
            <span style="color: var(--cyan);">${(course.progress * 100).toFixed(0)}% complete</span>
          </div>
        </div>
      `).join('');

    return `
      <nav class="top-nav">
        <a class="brand" href="#" onclick="navigateTo('dashboard'); return false;"><span></span>AdaptiveLearn AI</a>
        <div class="nav-links">
          <a href="#" onclick="navigateTo('dashboard'); return false;">Dashboard</a>
          <a href="#" onclick="handleLogout(); return false;">Logout</a>
        </div>
      </nav>
      <main style="max-width: 1000px; margin: 0 auto; padding: 28px 14px;">
        <h1>Learning Progress 📈</h1>
        <p class="lead" style="color: var(--muted); margin-bottom: 32px;">Track your adaptive learning journey across courses</p>
        
        <div class="progress-summary">
          ${courseProgressCards}
        </div>

        <div class="panel" style="padding: 32px; margin-top: 32px;">
          <h3>Overall Statistics</h3>
          <div style="margin-top: 20px; display: grid; grid-template-columns: repeat(3, 1fr); gap: 20px;">
            <div>
              <div style="color: var(--muted); font-size: 0.9rem; margin-bottom: 8px;">Proficiency</div>
              <div style="font-size: 2rem; color: var(--green); font-weight: bold;">${(dashboard.proficiency_estimate * 100).toFixed(0)}%</div>
            </div>
            <div>
              <div style="color: var(--muted); font-size: 0.9rem; margin-bottom: 8px;">Total Responses</div>
              <div style="font-size: 2rem; color: var(--blue); font-weight: bold;">${Object.values(dashboard.course_progress || {}).reduce((sum, c) => sum + c.question_count, 0)}</div>
            </div>
            <div>
              <div style="color: var(--muted); font-size: 0.9rem; margin-bottom: 8px;">Courses</div>
              <div style="font-size: 2rem; color: var(--cyan); font-weight: bold;">${dashboard.enrolled_courses.length}</div>
            </div>
          </div>
        </div>
      </main>
    `;
  } catch (error) {
    return '<main><p style="color: var(--pink); padding: 28px;">Error loading progress: ' + error.message + '</p></main>';
  }
}

function renderSettings() {
  return `
    <nav class="top-nav">
      <a class="brand" href="#" onclick="navigateTo('dashboard'); return false;"><span></span>AdaptiveLearn AI</a>
      <div class="nav-links">
        <a href="#" onclick="navigateTo('dashboard'); return false;">Dashboard</a>
        <a href="#" onclick="handleLogout(); return false;">Logout</a>
      </div>
    </nav>
    <main style="max-width: 600px; margin: 0 auto; padding: 28px 14px;">
      <h1>Settings & Profile ⚙️</h1>
      <div class="panel" style="padding: 32px; margin-top: 28px;">
        <h3 style="margin-top: 0;">Your Account</h3>
        <div style="margin-top: 20px;">
          <div style="margin-bottom: 20px;">
            <label style="display: block; color: var(--muted); font-size: 0.9rem; margin-bottom: 6px;">Full Name</label>
            <div style="background: rgba(255,255,255,.04); padding: 12px 16px; border-radius: 12px; border: 1px solid var(--line);">
              ${appState.user.name}
            </div>
          </div>
          <div style="margin-bottom: 20px;">
            <label style="display: block; color: var(--muted); font-size: 0.9rem; margin-bottom: 6px;">Email</label>
            <div style="background: rgba(255,255,255,.04); padding: 12px 16px; border-radius: 12px; border: 1px solid var(--line);">
              ${appState.user.email}
            </div>
          </div>
          <div style="margin-bottom: 20px;">
            <label style="display: block; color: var(--muted); font-size: 0.9rem; margin-bottom: 6px;">Member Since</label>
            <div style="background: rgba(255,255,255,.04); padding: 12px 16px; border-radius: 12px; border: 1px solid var(--line);">
              ${new Date(appState.user.created_at).toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric' })}
            </div>
          </div>
        </div>
      </div>
      <div class="panel" style="padding: 32px; margin-top: 28px;">
        <h3 style="margin-top: 0;">Danger Zone</h3>
        <p style="color: var(--muted); font-size: 0.9rem;">Sign out of your account. You'll be able to sign back in anytime.</p>
        <button class="btn ghost" style="margin-top: 16px; width: 100%; border-color: var(--pink); color: var(--pink);" onclick="handleLogout()">Logout</button>
      </div>
    </main>
  `;
}

// ============================================================================
// PAGE NAVIGATION
// ============================================================================

async function navigateTo(page) {
  appState.currentPage = page;

  // Clear quiz timer if switching pages
  if (appState.quizTimerInterval) {
    clearInterval(appState.quizTimerInterval);
    appState.quizTimerInterval = null;
  }

  // Redirect to login if not authenticated and page requires auth
  if (!appState.token && !['landing', 'login', 'register'].includes(page)) {
    navigateTo('login');
    return;
  }

  let html = '';

  try {
    switch (page) {
      case 'landing':
        html = renderLanding();
        break;
      case 'login':
        html = renderLogin();
        break;
      case 'register':
        html = renderRegister();
        break;
      case 'dashboard':
        html = await renderDashboard();
        break;
      case 'progress':
        html = await renderProgress();
        break;
      case 'settings':
        html = renderSettings();
        break;
      default:
        html = renderLanding();
    }
  } catch (error) {
    console.error('Navigation error:', error);
    html = `<main><p style="color: var(--pink); padding: 28px;">Error loading page: ${error.message}</p></main>`;
  }

  document.getElementById('app').innerHTML = html;
  window.scrollTo(0, 0);
}

// ============================================================================
// EVENT HANDLERS
// ============================================================================

async function handleLogin(event) {
  event.preventDefault();
  const email = document.getElementById('login-email').value;
  const password = document.getElementById('login-password').value;
  const errorEl = document.getElementById('login-error');

  try {
    errorEl.style.display = 'none';
    await apiService.login(email, password);
    navigateTo('dashboard');
  } catch (error) {
    errorEl.textContent = error.message;
    errorEl.style.display = 'block';
  }
}

async function handleRegister(event) {
  event.preventDefault();
  const name = document.getElementById('register-name').value;
  const email = document.getElementById('register-email').value;
  const password = document.getElementById('register-password').value;
  const errorEl = document.getElementById('register-error');

  try {
    errorEl.style.display = 'none';
    await apiService.register(name, email, password);
    navigateTo('dashboard');
  } catch (error) {
    errorEl.textContent = error.message;
    errorEl.style.display = 'block';
  }
}

async function handleLogout() {
  if (confirm('Are you sure you want to logout?')) {
    await apiService.logout();
  }
}

async function startQuizSession(courseName) {
  appState.quizSession = null;
  appState.quizStartTime = null;
  appState.currentCourse = courseName;
  const html = await renderQuizSession(courseName);
  document.getElementById('app').innerHTML = html;
}

async function enrollInCourse(courseName) {
  try {
    await apiService.enrollCourse(courseName);
    navigateTo('dashboard');
  } catch (error) {
    alert('Error enrolling: ' + error.message);
  }
}

async function handleQuizResponse(event) {
  event.preventDefault();
  
  if (!appState.quizSession) return;

  const answer = document.querySelector('input[name="answer"]:checked')?.value;
  const confidence = parseFloat(document.getElementById('confidence').value);

  if (!answer) {
    alert('Please select an answer');
    return;
  }

  const elapsedSeconds = getQuizElapsedSeconds();

  try {
    const response = {
      student_id: appState.user.id,
      question_id: appState.quizSession.next_question.id,
      submitted_answer: answer,
      confidence_level: confidence,
      response_time: Math.max(elapsedSeconds, 1),
    };

    const result = await apiService.submitQuizResponse(appState.quizSession.session_id, response);
    
    // Update session state
    appState.quizSession = {
      ...appState.quizSession,
      ...result,
      session_id: result.session_id,
    };

    // Reset timer for next question
    appState.quizStartTime = Date.now();

    // Re-render the quiz page
    const html = await renderQuizSession(appState.currentCourse);
    document.getElementById('app').innerHTML = html;
  } catch (error) {
    alert('Error submitting response: ' + error.message);
  }
}

async function finishQuizEarly() {
  if (!appState.quizSession) return;

  if (confirm('Are you sure you want to finish this quiz?')) {
    try {
      await apiService.finishQuiz(appState.quizSession.session_id);
      appState.quizSession = null;
      appState.quizStartTime = null;
      navigateTo('dashboard');
    } catch (error) {
      alert('Error finishing quiz: ' + error.message);
    }
  }
}

// ============================================================================
// INITIALIZATION
// ============================================================================

async function initApp() {
  // Check if user is already logged in
  if (appState.token) {
    try {
      appState.user = await apiService.getMe();
    } catch (error) {
      apiService.handleLogout();
    }
  }

  // Initial page load
  navigateTo('landing');
}

// Start the app when DOM is ready
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initApp);
} else {
  initApp();
}
