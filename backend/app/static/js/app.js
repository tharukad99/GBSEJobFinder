import { api } from './api.js';

const DECLINED_JOBS_KEY = 'gb_declined_jobs';

function getDeclinedJobIds() {
  try {
    const raw = sessionStorage.getItem(DECLINED_JOBS_KEY);
    return raw ? JSON.parse(raw) : [];
  } catch (e) {
    return [];
  }
}

function isJobDeclined(jobId) {
  if (!jobId) return false;
  const idStr = String(typeof jobId === 'object' && jobId !== null ? jobId.JobId : jobId);
  return getDeclinedJobIds().some((id) => String(id) === idStr);
}

function declineJob(job, event = null) {
  if (event) {
    event.stopPropagation();
  }
  if (!job || !job.JobId) return;

  const targetJobId = job.JobId;
  const currentDeclined = getDeclinedJobIds();
  if (!currentDeclined.some((id) => String(id) === String(targetJobId))) {
    currentDeclined.push(targetJobId);
    try {
      sessionStorage.setItem(DECLINED_JOBS_KEY, JSON.stringify(currentDeclined));
    } catch (e) {
      console.warn('Could not save declined jobs to sessionStorage', e);
    }
  }

  // Animate and remove cards with this job ID from DOM
  const cards = document.querySelectorAll(`.job-card[data-job-id="${targetJobId}"]`);
  cards.forEach((card) => {
    card.classList.add('job-card-declining');
    setTimeout(() => {
      card.remove();

      // If in jobs results and now empty
      const resultsCol = document.getElementById('jobs-results-container');
      if (resultsCol && resultsCol.querySelectorAll('.job-card').length === 0) {
        resultsCol.innerHTML = `
          <div class="empty-state">
            <div style="font-size: 36px; margin-bottom: 12px;">🔍</div>
            <h3>No jobs to display</h3>
            <p>All matching jobs on this page have been declined or filtered out.</p>
          </div>
        `;
      }
      // If in dashboard recent jobs and now empty
      const recentList = document.getElementById('dashboard-recent-jobs-list');
      if (recentList && recentList.querySelectorAll('.job-card').length === 0) {
        recentList.innerHTML = `
          <div style="text-align: center; padding: 30px 20px; color: #64748b; grid-column: 1 / -1;">
            <p>No recent jobs to display.</p>
          </div>
        `;
      }
    }, 320);
  });

  // Filter out of local state
  if (state.jobs?.items) {
    state.jobs.items = state.jobs.items.filter((j) => String(j.JobId) !== String(targetJobId));
  }
  if (state.dashboard?.recentJobs) {
    state.dashboard.recentJobs = state.dashboard.recentJobs.filter((j) => String(j.JobId) !== String(targetJobId));
  }

  // If modal is currently open for this job, close it
  if (state.selectedJob && String(state.selectedJob.JobId) === String(targetJobId)) {
    closeJobModal();
  }

  const title = job.Title ? `"${job.Title}"` : 'Job';
  showToast(`${title} declined and removed from list`, 'info');
}

function isJobApplied(job) {
  if (!job) return false;
  if (typeof job === 'object' && job.IsApplied !== undefined) {
    return Boolean(job.IsApplied);
  }
  const jobIdStr = String(typeof job === 'object' ? job.JobId : job);
  const found = (state.jobs?.items || []).find(j => String(j.JobId) === jobIdStr) 
    || (state.dashboard?.recentJobs || []).find(j => String(j.JobId) === jobIdStr)
    || (state.selectedJob && String(state.selectedJob.JobId) === jobIdStr ? state.selectedJob : null);
  return Boolean(found?.IsApplied);
}

async function toggleJobApplied(job, event = null) {
  if (event) {
    event.stopPropagation();
  }
  if (!job || !job.JobId) return false;

  const targetJobId = job.JobId;
  const currentStatus = isJobApplied(job);
  const newStatus = !currentStatus;

  // Immediate optimistic UI update
  job.IsApplied = newStatus;
  updateAppliedUI(targetJobId, newStatus);

  try {
    const res = await api.toggleJobApplied(targetJobId, newStatus);
    job.IsApplied = res.IsApplied;
    job.AppliedAt = res.AppliedAt;

    // Update in all local state arrays
    if (state.jobs?.items) {
      state.jobs.items.forEach(j => {
        if (j.JobId === targetJobId) {
          j.IsApplied = res.IsApplied;
          j.AppliedAt = res.AppliedAt;
        }
      });
    }
    if (state.dashboard?.recentJobs) {
      state.dashboard.recentJobs.forEach(j => {
        if (j.JobId === targetJobId) {
          j.IsApplied = res.IsApplied;
          j.AppliedAt = res.AppliedAt;
        }
      });
    }
    if (state.selectedJob && state.selectedJob.JobId === targetJobId) {
      state.selectedJob.IsApplied = res.IsApplied;
      state.selectedJob.AppliedAt = res.AppliedAt;
    }

    if (res.IsApplied) {
      showToast(`Marked "${job.Title}" as Applied in Database! ✓`, 'success');
    } else {
      showToast(`Unmarked "${job.Title}" from Applied status`, 'info');
    }

    updateAppliedUI(targetJobId, res.IsApplied);

    // If filtering by applied status on jobs page, reload results from DB
    if (state.currentRoute === 'jobs' && state.jobs.applied_status !== 'all') {
      loadJobsData();
    }
    return res.IsApplied;
  } catch (err) {
    // Revert optimistic update on error
    job.IsApplied = currentStatus;
    updateAppliedUI(targetJobId, currentStatus);
    showToast(`Failed to update application status: ${err.message}`, 'error');
    return currentStatus;
  }
}

function updateAppliedUI(jobId, isApplied) {
  document.querySelectorAll(`.job-card[data-job-id="${jobId}"]`).forEach(card => {
    const toggleBtn = card.querySelector('.btn-applied-toggle');
    const badgeContainer = card.querySelector('.applied-badge-slot');

    if (toggleBtn) {
      if (isApplied) {
        toggleBtn.classList.add('applied');
        toggleBtn.innerHTML = `<span>✓</span><span>Applied</span>`;
        toggleBtn.title = 'Click to unmark as applied in database';
      } else {
        toggleBtn.classList.remove('applied');
        toggleBtn.innerHTML = `<span>✓</span><span>Mark Applied</span>`;
        toggleBtn.title = 'Mark job as applied in database';
      }
    }

    if (badgeContainer) {
      badgeContainer.innerHTML = isApplied ? `<span class="badge-applied">✓ Applied</span>` : '';
    }
  });

  if (state.selectedJob && String(state.selectedJob.JobId) === String(jobId)) {
    const modalToggleBtn = document.getElementById('modal-applied-toggle-btn');
    const modalBadgeSlot = document.getElementById('modal-applied-badge-slot');
    if (modalToggleBtn) {
      if (isApplied) {
        modalToggleBtn.classList.add('applied');
        modalToggleBtn.innerHTML = `<span>✓</span><span>Applied in DB (Click to Undo)</span>`;
      } else {
        modalToggleBtn.classList.remove('applied');
        modalToggleBtn.innerHTML = `<span>✓</span><span>Mark as Applied</span>`;
      }
    }
    if (modalBadgeSlot) {
      modalBadgeSlot.innerHTML = isApplied ? `<span class="badge-applied">✓ Applied</span>` : '';
    }
  }

  // Update dashboard stat counter if on screen
  const appliedStatEl = document.getElementById('stat-applied-count-val');
  if (appliedStatEl) {
    const currentVal = parseInt(appliedStatEl.innerText, 10) || 0;
    appliedStatEl.innerText = isApplied ? currentVal + 1 : Math.max(0, currentVal - 1);
  }
}

// Application State
const state = {
  currentRoute: 'dashboard',
  user: {
    isAdmin: api.isAdminLoggedIn(),
  },
  dashboard: {
    stats: null,
    recentJobs: [],
    loading: false,
  },
  jobs: {
    items: [],
    total: 0,
    totalPages: 1,
    page: 1,
    pageSize: 15,
    q: '',
    sponsorship: 'confirmed_may_offer',
    location: '',
    skill: '',
    experience_level: 'mid',
    applied_status: 'all',
    days: null,
    work_type: '',
    sort: 'best_match',
    loading: false,
  },
  companies: {
    items: [],
    q: '',
    licensedOnly: false,
    loading: false,
    lookupName: '',
    lookupResult: null,
    lookingUp: false,
  },
  admin: {
    sources: [],
    runs: [],
    subTab: 'monitor',
    loading: false,
    actionLoading: false,
    statusMessage: null,
  },
  monitor: {
    data: null,
    loading: false,
    autoRefresh: true,
    timerId: null,
    filterSource: 'all',
  },
  selectedJob: null,
  modalVerifyResult: null,
  modalVerifying: false,
  modalEditingSponsorship: false,
  modalSavingSponsorship: false,
};

// Utilities
function showToast(message, type = 'info') {
  const container = document.getElementById('toast-container');
  if (!container) return;

  const toast = document.createElement('div');
  toast.className = `toast toast-${type}`;
  toast.innerHTML = `
    <span>${type === 'success' ? '✓' : type === 'error' ? '✕' : 'ℹ'}</span>
    <span>${escapeHtml(message)}</span>
  `;
  container.appendChild(toast);

  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transition = 'opacity 0.3s ease';
    setTimeout(() => toast.remove(), 300);
  }, 4000);
}

function escapeHtml(str) {
  if (typeof str !== 'string') return str || '';
  return str
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

function formatRelativeTime(dateStr) {
  if (!dateStr) return 'Recently';
  const date = new Date(dateStr);
  const now = new Date();
  const diffHours = Math.floor((now - date) / (1000 * 60 * 60));

  if (diffHours < 1) return 'Just now';
  if (diffHours < 24) return `${diffHours}h ago`;
  const diffDays = Math.floor(diffHours / 24);
  if (diffDays === 1) return '1 day ago';
  if (diffDays < 30) return `${diffDays} days ago`;
  return date.toLocaleDateString('en-GB');
}

function getSponsorshipBadgeHtml(status) {
  if (status === 'CONFIRMED') {
    return `<span class="badge-sponsorship confirmed">🛡️ Visa Sponsored</span>`;
  }
  if (status === 'MAY_OFFER') {
    return `<span class="badge-sponsorship may-offer">🏛️ Licensed Sponsor</span>`;
  }
  if (status === 'NO_SPONSORSHIP') {
    return `<span class="badge-sponsorship no-sponsorship">✕ No Sponsorship</span>`;
  }
  return `<span class="badge-sponsorship unknown">❓ Unknown Status</span>`;
}

function getMatchScoreHtml(score) {
  if (!score && score !== 0) return '';
  let cls = 'match-low';
  if (score >= 80) cls = 'match-high';
  else if (score >= 50) cls = 'match-med';
  return `<span class="match-score-pill ${cls}" title="Match Score calculated from visa status, skills, and UK suitability">★ ${score}% Match</span>`;
}

function getExperienceBadgeHtml(level, title = '') {
  const tLower = (title || '').toLowerCase();
  const isSenior = level === 'Senior' || /senior|sr\.?|lead|principal|staff|architect/.test(tLower);
  const isJunior = level === 'Junior' || /junior|graduate|entry|associate|trainee/.test(tLower);

  if (isSenior) {
    return `<span class="exp-badge exp-senior" title="Senior / Lead Level Position">⭐ Senior / Lead</span>`;
  }
  if (isJunior) {
    return `<span class="exp-badge exp-junior" title="Junior / Entry Level Position">🌱 Junior / Graduate</span>`;
  }
  return `<span class="exp-badge exp-mid" title="Mid Level Position">🔹 Mid Level</span>`;
}

function getRemoteBadgeHtml(type) {
  if (type === 'Remote UK') {
    return `<span style="background: #f0fdf4; color: #15803d; border: 1px solid #bbf7d0; padding: 2px 8px; border-radius: 4px; font-size: 0.75rem; font-weight: 600;">🌐 Remote UK</span>`;
  }
  if (type === 'Hybrid') {
    return `<span style="background: #f8fafc; color: #0369a1; border: 1px solid #bae6fd; padding: 2px 8px; border-radius: 4px; font-size: 0.75rem; font-weight: 600;">🏢 Hybrid</span>`;
  }
  if (type === 'On-site') {
    return `<span style="background: #f1f5f9; color: #475569; border: 1px solid #e2e8f0; padding: 2px 8px; border-radius: 4px; font-size: 0.75rem; font-weight: 600;">📍 On-site</span>`;
  }
  return '';
}

// Router & URL Handling
function parseUrlAndNavigate() {
  const path = window.location.pathname;
  const searchParams = new URLSearchParams(window.location.search);

  let route = 'dashboard';
  if (path.startsWith('/jobs')) route = 'jobs';
  else if (path.startsWith('/companies')) route = 'companies';
  else if (path.startsWith('/monitor')) {
    route = 'admin';
    state.admin.subTab = 'monitor';
  } else if (path.startsWith('/admin')) {
    route = 'admin';
    const requestedTab = searchParams.get('tab');
    if (requestedTab) state.admin.subTab = requestedTab;
  }

  state.currentRoute = route;

  if (route === 'jobs') {
    state.jobs.q = searchParams.get('q') || '';
    state.jobs.sponsorship = searchParams.get('sponsorship') || 'confirmed_may_offer';
    state.jobs.location = searchParams.get('location') || '';
    state.jobs.skill = searchParams.get('skill') || '';
    state.jobs.experience_level = searchParams.get('experience_level') || 'mid';
    state.jobs.applied_status = searchParams.get('applied_status') || 'all';
    state.jobs.days = searchParams.get('days') ? Number(searchParams.get('days')) : null;
    state.jobs.work_type = searchParams.get('work_type') || '';
    state.jobs.sort = searchParams.get('sort') || 'best_match';
    state.jobs.page = searchParams.get('page') ? Number(searchParams.get('page')) : 1;
  } else if (route === 'companies') {
    state.companies.q = searchParams.get('q') || '';
  } else if (route === 'admin') {
    const requestedTab = searchParams.get('tab');
    if (requestedTab) state.admin.subTab = requestedTab;
  }

  renderAuthNav();
  updateNavActiveState();
  renderCurrentRoute();
}

function navigateTo(path, params = null, replace = false) {
  let url = path;
  if (params) {
    const qs = new URLSearchParams();
    Object.entries(params).forEach(([k, v]) => {
      if (v !== undefined && v !== null && v !== '') qs.append(k, v);
    });
    const queryString = qs.toString();
    if (queryString) url += `?${queryString}`;
  }

  if (replace) {
    window.history.replaceState({}, '', url);
  } else {
    window.history.pushState({}, '', url);
  }
  parseUrlAndNavigate();
}

function updateNavActiveState() {
  document.querySelectorAll('.nav-link').forEach((link) => {
    const target = link.getAttribute('data-route');
    if (target === state.currentRoute) {
      link.classList.add('active');
    } else {
      link.classList.remove('active');
    }
  });
}

function renderAuthNav() {
  const slot = document.getElementById('nav-auth-slot');
  if (!slot) return;

  const isLoggedIn = api.isAdminLoggedIn();
  state.user.isAdmin = isLoggedIn;

  if (isLoggedIn) {
    slot.innerHTML = `
      <div class="admin-logged-tag">
        <span>👤 Admin</span>
        <button id="nav-logout-btn" class="btn-logout" title="Log out from administrator session">Logout</button>
      </div>
    `;
    document.getElementById('nav-logout-btn')?.addEventListener('click', async () => {
      await api.logout();
      showToast('Logged out successfully', 'info');
      renderAuthNav();
      if (state.currentRoute === 'admin') {
        renderCurrentRoute();
      }
    });
  } else {
    slot.innerHTML = `
      <button id="nav-login-btn" class="btn-login" title="Administrator Login">
        <span>🔐</span>
        <span>Admin Login</span>
      </button>
    `;
    document.getElementById('nav-login-btn')?.addEventListener('click', () => {
      openAuthModal();
    });
  }
}

function openAuthModal(onSuccess = null) {
  const modalRoot = document.getElementById('auth-modal-root');
  if (!modalRoot) return;

  modalRoot.innerHTML = `
    <div class="modal-overlay" id="auth-modal-backdrop">
      <div class="auth-card" id="auth-modal-card">
        <div style="display: flex; align-items: center; justify-content: space-between;">
          <div style="display: flex; align-items: center; gap: 8px;">
            <div style="width: 36px; height: 36px; background: #eff6ff; color: #1d4ed8; border-radius: 8px; display: flex; align-items: center; justify-content: center; font-size: 1.2rem;">
              🔐
            </div>
            <div>
              <h3 style="font-size: 1.15rem; font-weight: 800; color: #0f172a;">Administrator Sign In</h3>
              <p style="font-size: 0.8rem; color: #64748b;">Access feed controls and ingest schedules</p>
            </div>
          </div>
          <button id="auth-modal-close-btn" style="color: #94a3b8; font-size: 1.2rem; cursor: pointer; padding: 4px;">✕</button>
        </div>

        <form id="auth-modal-form" style="display: flex; flex-direction: column; gap: 14px; margin-top: 6px;">
          <div id="auth-error-msg" style="display: none; padding: 8px 12px; background: #fff1f2; border: 1px solid #fecdd3; border-radius: 6px; color: #9f1239; font-size: 0.85rem; font-weight: 600;"></div>

          <div>
            <label style="display: block; font-size: 0.82rem; font-weight: 700; color: #334155; margin-bottom: 4px;">Username</label>
            <input 
              type="text" 
              id="auth-username-input"
              value="admin"
              required
              style="width: 100%; padding: 10px 12px; border-radius: 8px; border: 1px solid #cbd5e1; font-size: 0.9rem; outline: none;"
            />
          </div>

          <div>
            <label style="display: block; font-size: 0.82rem; font-weight: 700; color: #334155; margin-bottom: 4px;">Password</label>
            <input 
              type="password" 
              id="auth-password-input"
              placeholder="Enter admin password..."
              required
              style="width: 100%; padding: 10px 12px; border-radius: 8px; border: 1px solid #cbd5e1; font-size: 0.9rem; outline: none;"
            />
          </div>

          <button 
            type="submit" 
            id="auth-submit-btn"
            class="btn-primary" 
            style="justify-content: center; padding: 12px; font-size: 0.95rem; margin-top: 6px;"
          >
            Sign In as Admin
          </button>
        </form>

        <div style="font-size: 0.78rem; color: #64748b; text-align: center; border-top: 1px solid #f1f5f9; padding-top: 12px;">
          UK Tech Intelligence Admin Portal • Default user: <code>admin</code>
        </div>
      </div>
    </div>
  `;

  modalRoot.classList.remove('hidden');

  document.getElementById('auth-modal-backdrop')?.addEventListener('click', (e) => {
    if (e.target.id === 'auth-modal-backdrop') closeAuthModal();
  });

  document.getElementById('auth-modal-close-btn')?.addEventListener('click', closeAuthModal);

  const form = document.getElementById('auth-modal-form');
  const errorMsg = document.getElementById('auth-error-msg');
  const submitBtn = document.getElementById('auth-submit-btn');

  form?.addEventListener('submit', async (e) => {
    e.preventDefault();
    const username = document.getElementById('auth-username-input').value.trim();
    const password = document.getElementById('auth-password-input').value.trim();

    if (errorMsg) errorMsg.style.display = 'none';
    if (submitBtn) {
      submitBtn.disabled = true;
      submitBtn.innerText = 'Signing in...';
    }

    try {
      await api.login(username, password);
      showToast('Admin authentication successful! 🔓', 'success');
      closeAuthModal();
      renderAuthNav();
      if (onSuccess) onSuccess();
      else if (state.currentRoute === 'admin') renderCurrentRoute();
    } catch (err) {
      if (errorMsg) {
        errorMsg.innerText = err.message || 'Invalid username or password.';
        errorMsg.style.display = 'block';
      }
    } finally {
      if (submitBtn) {
        submitBtn.disabled = false;
        submitBtn.innerText = 'Sign In as Admin';
      }
    }
  });

  document.getElementById('auth-password-input')?.focus();
}

function closeAuthModal() {
  const modalRoot = document.getElementById('auth-modal-root');
  if (modalRoot) modalRoot.classList.add('hidden');
}

// Render Controllers
function renderCurrentRoute() {
  const views = ['dashboard-view', 'jobs-view', 'companies-view', 'monitor-view', 'admin-view'];
  views.forEach((v) => {
    const el = document.getElementById(v);
    if (el) el.classList.add('hidden');
  });

  // Stop monitor auto-refresh interval when navigating away
  if (state.currentRoute !== 'monitor' && state.monitor.timerId) {
    clearInterval(state.monitor.timerId);
    state.monitor.timerId = null;
  }

  const activeView = document.getElementById(`${state.currentRoute}-view`);
  if (activeView) activeView.classList.remove('hidden');

  if (state.currentRoute === 'dashboard') {
    loadDashboardData();
  } else if (state.currentRoute === 'jobs') {
    loadJobsData();
  } else if (state.currentRoute === 'companies') {
    loadCompaniesData();
  } else if (state.currentRoute === 'monitor') {
    loadMonitorData();
  } else if (state.currentRoute === 'admin') {
    loadAdminData();
  }
}

// ==========================================
// 1. DASHBOARD CONTROLLER
// ==========================================
async function loadDashboardData() {
  const container = document.getElementById('dashboard-view');
  if (!container) return;

  state.dashboard.loading = true;
  container.innerHTML = `
    <div style="text-align: center; padding: 60px 20px; color: #64748b;">
      <div class="spinning" style="display: inline-block; font-size: 28px; margin-bottom: 12px;">🔄</div>
      <p style="font-weight: 600;">Loading UK job market statistics...</p>
    </div>
  `;

  try {
    const [stats, recentJobs] = await Promise.all([
      api.getDashboardStats(),
      api.getRecentJobs(6),
    ]);
    state.dashboard.stats = stats;
    state.dashboard.recentJobs = (recentJobs || []).filter((j) => !isJobDeclined(j.JobId));
    renderDashboardView();
  } catch (err) {
    container.innerHTML = `
      <div style="padding: 24px; background: #fff1f2; color: #9f1239; border-radius: 12px; border: 1px solid #fecdd3;">
        <strong>Error loading dashboard:</strong> ${escapeHtml(err.message)}
        <div style="margin-top: 12px;">
          <button id="dashboard-retry-btn" class="btn-primary">Retry</button>
        </div>
      </div>
    `;
    document.getElementById('dashboard-retry-btn')?.addEventListener('click', loadDashboardData);
  } finally {
    state.dashboard.loading = false;
  }
}

function renderDashboardView() {
  const container = document.getElementById('dashboard-view');
  if (!container || !state.dashboard.stats) return;

  const s = state.dashboard.stats;
  const recent = state.dashboard.recentJobs;
  const appliedCount = s.applied_jobs || 0;

  container.innerHTML = `
    <!-- Hero Banner -->
    <div class="hero-banner">
      <div style="max-width: 680px;">
        <div class="hero-pill">
          <span>🇬🇧 UK Tech Hiring Intelligence</span>
        </div>
        <h1 class="hero-title">UK Software Engineering Job Finder</h1>
        <p class="hero-desc">
          Automated aggregation of genuine UK Software Engineering positions with verified Skilled Worker visa sponsorship and official Home Office licence validation.
        </p>
      </div>

      <div style="display: flex; gap: 12px; flex-wrap: wrap;">
        <button id="hero-spons-btn" style="background-color: #10b981; color: #ffffff; padding: 12px 20px; border-radius: 10px; font-weight: 700; font-size: 0.95rem; display: flex; align-items: center; gap: 8px; box-shadow: 0 4px 12px rgba(16, 185, 129, 0.35); transition: all 0.15s;">
          <span>🛡️</span>
          <span>Confirmed Sponsorship (${s.confirmed_sponsorship_jobs || 0})</span>
        </button>

        <button id="hero-senior-btn" style="background-color: #8b5cf6; color: #ffffff; padding: 12px 20px; border-radius: 10px; font-weight: 700; font-size: 0.95rem; display: flex; align-items: center; gap: 8px; box-shadow: 0 4px 12px rgba(139, 92, 246, 0.35); transition: all 0.15s;">
          <span>⭐</span>
          <span>Senior & Lead Roles</span>
        </button>

        <button id="hero-all-btn" style="background-color: rgba(255,255,255,0.15); color: #ffffff; border: 1px solid rgba(255,255,255,0.3); backdrop-filter: blur(4px); padding: 12px 20px; border-radius: 10px; font-weight: 700; font-size: 0.95rem; display: flex; align-items: center; gap: 8px; transition: all 0.15s;">
          <span>Explore All Jobs</span>
          <span>→</span>
        </button>
      </div>
    </div>

    <!-- Metrics Grid -->
    <div class="stats-grid">
      <div class="stat-card clickable" id="stat-all-jobs">
        <div class="stat-icon" style="background: #eff6ff; color: #1d4ed8;">💼</div>
        <div>
          <div class="stat-value">${s.total_active_jobs || 0}</div>
          <div class="stat-label">Active UK Roles</div>
        </div>
      </div>

      <div class="stat-card clickable" id="stat-confirmed-spons">
        <div class="stat-icon" style="background: #ecfdf5; color: #047857;">🛡️</div>
        <div>
          <div class="stat-value" style="color: #047857;">${s.confirmed_sponsorship_jobs || 0}</div>
          <div class="stat-label">Confirmed Visa Sponsorship</div>
        </div>
      </div>

      <div class="stat-card clickable" id="stat-senior-roles">
        <div class="stat-icon" style="background: #fdf4ff; color: #86198f;">⭐</div>
        <div>
          <div class="stat-value" style="color: #86198f;">Senior / Lead</div>
          <div class="stat-label">Engineering Positions</div>
        </div>
      </div>

      <div class="stat-card clickable" id="stat-applied-tracker">
        <div class="stat-icon" style="background: #f0fdf4; color: #15803d;">✅</div>
        <div>
          <div class="stat-value" id="stat-applied-count-val" style="color: #15803d;">${appliedCount}</div>
          <div class="stat-label">Applications Submitted</div>
        </div>
      </div>
    </div>

    <!-- Technology & Role Distribution Bar -->
    <div style="background: white; border: 1px solid var(--border-subtle); border-radius: 14px; padding: 20px; box-shadow: var(--shadow-sm); margin-bottom: 24px;">
      <h3 style="font-size: 1.05rem; font-weight: 800; color: #0f172a; margin-bottom: 12px; display: flex; align-items: center; gap: 8px;">
        <span>🔥 Popular UK Roles & Tech Stacks</span>
      </h3>
      <div style="display: flex; flex-wrap: wrap; gap: 8px;">
        <button class="tech-pill role-shortcut-btn" data-exp="senior" style="padding: 6px 12px; font-size: 0.82rem; cursor: pointer; background-color: #fdf4ff; color: #86198f; border-color: #f0abfc; font-weight: 700;">
          ⭐ Senior Software Engineer
        </button>
        <button class="tech-pill role-shortcut-btn" data-exp="senior" data-skill=".NET" style="padding: 6px 12px; font-size: 0.82rem; cursor: pointer; background-color: #eff6ff; color: #1d4ed8; font-weight: 700;">
          ⭐ Senior .NET Developer
        </button>
        <button class="tech-pill role-shortcut-btn" data-exp="senior" data-skill="React" style="padding: 6px 12px; font-size: 0.82rem; cursor: pointer; background-color: #ecfdf5; color: #047857; font-weight: 700;">
          ⭐ Senior React / Frontend
        </button>
        ${(s.top_technologies || [
          { skill: 'C#', count: 18 },
          { skill: '.NET', count: 16 },
          { skill: 'React', count: 14 },
          { skill: 'TypeScript', count: 12 },
          { skill: 'SQL Server', count: 11 },
          { skill: 'Azure', count: 10 },
          { skill: 'Python', count: 9 },
          { skill: 'Docker', count: 8 },
        ])
          .map(
            (t) => `
          <button class="tech-pill skill-shortcut-btn" data-skill="${escapeHtml(t.skill)}" style="padding: 6px 12px; font-size: 0.82rem; cursor: pointer; display: flex; align-items: center; gap: 6px;">
            <span style="font-weight: 700;">${escapeHtml(t.skill)}</span>
            <span style="background: #e2e8f0; color: #475569; padding: 1px 6px; border-radius: 999px; font-size: 0.72rem;">${t.count}</span>
          </button>
        `
          )
          .join('')}
      </div>
    </div>

    <!-- Recent Job Openings Header -->
    <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 16px;">
      <div>
        <h2 style="font-size: 1.3rem; font-weight: 800; color: #0f172a;">Freshly Ingested UK Opportunities</h2>
        <p style="font-size: 0.875rem; color: #64748b;">Direct ATS feeds with automated verification</p>
      </div>
      <button id="view-all-jobs-link" class="btn-secondary" style="font-size: 0.85rem;">
        <span>View all ${s.total_active_jobs || 0} jobs →</span>
      </button>
    </div>

    <!-- Recent Jobs Cards -->
    <div class="job-grid" id="dashboard-recent-jobs-list">
      ${recent.map((job) => renderJobCardHtml(job)).join('')}
    </div>
  `;

  document.getElementById('hero-spons-btn')?.addEventListener('click', () => {
    navigateTo('/jobs', { sponsorship: 'confirmed' });
  });

  document.getElementById('hero-senior-btn')?.addEventListener('click', () => {
    navigateTo('/jobs', { experience_level: 'senior' });
  });

  document.getElementById('hero-all-btn')?.addEventListener('click', () => {
    navigateTo('/jobs');
  });

  document.getElementById('stat-all-jobs')?.addEventListener('click', () => {
    navigateTo('/jobs');
  });

  document.getElementById('stat-confirmed-spons')?.addEventListener('click', () => {
    navigateTo('/jobs', { sponsorship: 'confirmed' });
  });

  document.getElementById('stat-senior-roles')?.addEventListener('click', () => {
    navigateTo('/jobs', { experience_level: 'senior' });
  });

  document.getElementById('stat-applied-tracker')?.addEventListener('click', () => {
    navigateTo('/jobs', { applied_status: 'applied_only' });
  });

  document.getElementById('view-all-jobs-link')?.addEventListener('click', () => {
    navigateTo('/jobs');
  });

  container.querySelectorAll('.skill-shortcut-btn').forEach((btn) => {
    btn.addEventListener('click', (e) => {
      const skill = e.currentTarget.getAttribute('data-skill');
      navigateTo('/jobs', { skill });
    });
  });

  container.querySelectorAll('.role-shortcut-btn').forEach((btn) => {
    btn.addEventListener('click', (e) => {
      const exp = e.currentTarget.getAttribute('data-exp');
      const skill = e.currentTarget.getAttribute('data-skill');
      navigateTo('/jobs', { experience_level: exp, skill: skill || undefined });
    });
  });

  container.querySelectorAll('.job-card-select-btn').forEach((btn) => {
    btn.addEventListener('click', (e) => {
      const jobId = e.currentTarget.getAttribute('data-job-id');
      const job = recent.find((j) => String(j.JobId) === String(jobId));
      if (job) openJobModal(job);
    });
  });

  container.querySelectorAll('.job-card-decline-btn').forEach((btn) => {
    btn.addEventListener('click', (e) => {
      const jobId = e.currentTarget.getAttribute('data-job-id');
      const job = recent.find((j) => String(j.JobId) === String(jobId));
      if (job) declineJob(job, e);
    });
  });

  container.querySelectorAll('.btn-applied-toggle').forEach((btn) => {
    btn.addEventListener('click', (e) => {
      const jobId = e.currentTarget.getAttribute('data-job-id');
      const job = recent.find((j) => String(j.JobId) === String(jobId));
      if (job) toggleJobApplied(job, e);
    });
  });
}

// ==========================================
// 2. JOBS CONTROLLER
// ==========================================
async function loadJobsData() {
  const container = document.getElementById('jobs-view');
  if (!container) return;

  renderJobsLayout();

  const resultsCol = document.getElementById('jobs-results-container');
  if (resultsCol) {
    resultsCol.innerHTML = `
      <div style="text-align: center; padding: 60px 20px; color: #64748b;">
        <div class="spinning" style="display: inline-block; font-size: 28px; margin-bottom: 12px;">🔄</div>
        <p style="font-weight: 600;">Searching active UK Software Engineering positions...</p>
      </div>
    `;
  }

  try {
    const filters = {
      q: state.jobs.q,
      sponsorship: state.jobs.sponsorship,
      location: state.jobs.location,
      skill: state.jobs.skill,
      experience_level: state.jobs.experience_level,
      applied_status: state.jobs.applied_status !== 'all' ? state.jobs.applied_status : undefined,
      days: state.jobs.days,
      work_type: state.jobs.work_type,
      sort: state.jobs.sort,
      page: state.jobs.page,
      page_size: state.jobs.pageSize,
    };

    const data = await api.getJobs(filters);
    state.jobs.items = (data.items || []).filter((j) => !isJobDeclined(j.JobId));
    state.jobs.total = data.total || 0;
    state.jobs.totalPages = data.total_pages || 1;

    renderJobsResults();
  } catch (err) {
    if (resultsCol) {
      resultsCol.innerHTML = `
        <div style="padding: 24px; background: #fff1f2; color: #9f1239; border-radius: 12px; border: 1px solid #fecdd3;">
          <strong>Error fetching jobs:</strong> ${escapeHtml(err.message)}
          <div style="margin-top: 12px;">
            <button id="jobs-retry-btn" class="btn-primary">Retry Search</button>
          </div>
        </div>
      `;
      document.getElementById('jobs-retry-btn')?.addEventListener('click', loadJobsData);
    }
  }
}

function renderJobsLayout() {
  const container = document.getElementById('jobs-view');
  if (!container) return;

  if (!document.getElementById('jobs-search-form')) {
    container.innerHTML = `
      <div class="jobs-page-layout">
        <!-- Sidebar Filter Panel -->
        <aside class="filter-card" id="jobs-filter-panel">
          <!-- Dynamic Filter Panel inserted here -->
        </aside>

        <!-- Main Column -->
        <main style="display: flex; flex-direction: column; gap: 20px;">
          <!-- Search Bar -->
          <div style="background: white; border: 1px solid #e2e8f0; border-radius: 14px; padding: 16px; box-shadow: var(--shadow-sm); display: flex; flex-direction: column; gap: 14px;">
            <form id="jobs-search-form" style="display: flex; gap: 10px;">
              <div style="flex: 1; position: relative; display: flex; align-items: center;">
                <span style="position: absolute; left: 14px; color: #94a3b8; font-size: 16px;">🔍</span>
                <input 
                  type="text" 
                  id="jobs-search-input"
                  placeholder="Search by title (e.g. Senior Engineer, .NET, React, C#), company, or UK city..."
                  value="${escapeHtml(state.jobs.q)}"
                  style="width: 100%; padding: 12px 14px 12px 42px; border-radius: 10px; border: 1px solid #cbd5e1; font-size: 0.95rem; outline: none; background-color: #f8fafc; color: #0f172a;"
                />
                <button 
                  type="button" 
                  id="jobs-search-clear-btn" 
                  style="position: absolute; right: 12px; color: #94a3b8; font-size: 16px; cursor: pointer; ${state.jobs.q ? '' : 'display: none;'}"
                >
                  ✕
                </button>
              </div>
              <button type="submit" class="btn-primary" style="padding: 0 24px;">
                <span>Search</span>
              </button>
            </form>

            <div style="display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 12px; padding-top: 6px; border-top: 1px solid #f1f5f9;">
              <div id="jobs-count-summary" style="font-size: 0.9rem; color: #475569; font-weight: 600;">
                Loading count...
              </div>

              <div style="display: flex; align-items: center; gap: 8px;">
                <label style="font-size: 0.85rem; font-weight: 600; color: #64748b;">Sort by:</label>
                <select 
                  id="jobs-sort-select"
                  style="padding: 6px 12px; border-radius: 8px; border: 1px solid #cbd5e1; font-size: 0.85rem; background-color: #ffffff; color: #0f172a; outline: none;"
                >
                  <option value="best_match" ${state.jobs.sort === 'best_match' ? 'selected' : ''}>🎯 Best Match & Sponsorship</option>
                  <option value="newest" ${state.jobs.sort === 'newest' ? 'selected' : ''}>⚡ Most Recent First</option>
                  <option value="sponsorship" ${state.jobs.sort === 'sponsorship' ? 'selected' : ''}>🛡️ Confirmed Visa First</option>
                </select>
              </div>
            </div>
          </div>

          <!-- Results List Container -->
          <div id="jobs-results-container" class="job-grid">
            <!-- Jobs cards rendered here -->
          </div>

          <!-- Pagination -->
          <div id="jobs-pagination-container">
            <!-- Pagination buttons -->
          </div>
        </main>
      </div>
    `;

    const searchForm = document.getElementById('jobs-search-form');
    const searchInput = document.getElementById('jobs-search-input');
    const clearBtn = document.getElementById('jobs-search-clear-btn');
    const sortSelect = document.getElementById('jobs-sort-select');

    searchInput?.addEventListener('input', (e) => {
      if (clearBtn) clearBtn.style.display = e.target.value ? 'block' : 'none';
    });

    clearBtn?.addEventListener('click', () => {
      if (searchInput) searchInput.value = '';
      if (clearBtn) clearBtn.style.display = 'none';
      state.jobs.q = '';
      state.jobs.page = 1;
      navigateTo('/jobs', getActiveJobParams());
    });

    searchForm?.addEventListener('submit', (e) => {
      e.preventDefault();
      state.jobs.q = searchInput ? searchInput.value.trim() : '';
      state.jobs.page = 1;
      navigateTo('/jobs', getActiveJobParams());
    });

    sortSelect?.addEventListener('change', (e) => {
      state.jobs.sort = e.target.value;
      state.jobs.page = 1;
      navigateTo('/jobs', getActiveJobParams());
    });
  }

  renderFilterPanel();
}

function getActiveJobParams() {
  return {
    q: state.jobs.q || undefined,
    sponsorship: state.jobs.sponsorship || undefined,
    location: state.jobs.location || undefined,
    skill: state.jobs.skill || undefined,
    experience_level: state.jobs.experience_level || undefined,
    applied_status: state.jobs.applied_status !== 'all' ? state.jobs.applied_status : undefined,
    days: state.jobs.days || undefined,
    work_type: state.jobs.work_type || undefined,
    sort: state.jobs.sort || undefined,
    page: state.jobs.page > 1 ? state.jobs.page : undefined,
  };
}

function renderFilterPanel() {
  const panel = document.getElementById('jobs-filter-panel');
  if (!panel) return;

  const popularSkills = ['C#', '.NET', 'React', 'TypeScript', 'JavaScript', 'SQL Server', 'Azure', 'Python', 'Docker', 'AWS'];

  panel.innerHTML = `
    <div style="display: flex; align-items: center; justify-content: space-between; border-bottom: 1px solid #f1f5f9; padding-bottom: 12px;">
      <div style="display: flex; align-items: center; gap: 6px; font-weight: 700; font-size: 1rem; color: #0f172a;">
        <span>🔍</span>
        <span>Filters</span>
      </div>
      <button 
        id="jobs-reset-filters-btn"
        style="display: flex; align-items: center; gap: 4px; font-size: 0.78rem; color: #64748b; font-weight: 600; cursor: pointer;"
        title="Reset all filters"
      >
        <span>↺</span>
        <span>Reset</span>
      </button>
    </div>

    <!-- Application Status (Applied Tick Filter) -->
    <div class="filter-group" style="background: #f0fdf4; padding: 10px; border-radius: 8px; border: 1px solid #bbf7d0;">
      <div class="filter-group-title" style="color: #15803d; display: flex; align-items: center; gap: 6px;">
        <span>✓</span>
        <span>My Applications</span>
      </div>
      <label class="filter-option">
        <input type="radio" name="filter-applied-status" value="all" ${state.jobs.applied_status === 'all' || !state.jobs.applied_status ? 'checked' : ''} />
        <span>All Roles</span>
      </label>
      <label class="filter-option">
        <input type="radio" name="filter-applied-status" value="not_applied" ${state.jobs.applied_status === 'not_applied' ? 'checked' : ''} />
        <span>Not Applied Yet</span>
      </label>
      <label class="filter-option">
        <input type="radio" name="filter-applied-status" value="applied_only" ${state.jobs.applied_status === 'applied_only' ? 'checked' : ''} />
        <span style="color: #15803d; font-weight: 700;">✓ Applied Roles Only</span>
      </label>
    </div>

    <!-- Experience Level (Senior / Lead / Mid / Junior) -->
    <div class="filter-group">
      <div class="filter-group-title" style="display: flex; align-items: center; gap: 6px;">
        <span>⭐</span>
        <span>Seniority / Experience</span>
      </div>
      <label class="filter-option">
        <input type="radio" name="filter-exp" value="mid" ${state.jobs.experience_level === 'mid' || !state.jobs.experience_level ? 'checked' : ''} />
        <span style="color: #0369a1; font-weight: 700;">🔹 Mid Level Developer</span>
      </label>
      <label class="filter-option">
        <input type="radio" name="filter-exp" value="senior" ${state.jobs.experience_level === 'senior' ? 'checked' : ''} />
        <span style="color: #86198f; font-weight: 700;">⭐ Senior / Lead / Principal</span>
      </label>
      <label class="filter-option">
        <input type="radio" name="filter-exp" value="junior" ${state.jobs.experience_level === 'junior' ? 'checked' : ''} />
        <span>🌱 Junior / Graduate</span>
      </label>
      <label class="filter-option">
        <input type="radio" name="filter-exp" value="all" ${state.jobs.experience_level === 'all' ? 'checked' : ''} />
        <span>All Experience Levels</span>
      </label>
    </div>

    <!-- Visa Sponsorship -->
    <div class="filter-group">
      <div class="filter-group-title">🛡️ Visa Sponsorship</div>
      <label class="filter-option">
        <input type="radio" name="filter-sponsorship" value="confirmed_may_offer" ${state.jobs.sponsorship === 'confirmed_may_offer' ? 'checked' : ''} />
        <span style="font-weight: 600;">Confirmed + May Offer</span>
      </label>
      <label class="filter-option">
        <input type="radio" name="filter-sponsorship" value="confirmed" ${state.jobs.sponsorship === 'confirmed' ? 'checked' : ''} />
        <span style="color: #047857; font-weight: 600;">✅ Confirmed Only</span>
      </label>
      <label class="filter-option">
        <input type="radio" name="filter-sponsorship" value="may_offer" ${state.jobs.sponsorship === 'may_offer' ? 'checked' : ''} />
        <span style="color: #6d28d9; font-weight: 600;">🏛️ May Offer (Licensed)</span>
      </label>
      <label class="filter-option">
        <input type="radio" name="filter-sponsorship" value="unknown" ${state.jobs.sponsorship === 'unknown' ? 'checked' : ''} />
        <span>Unknown</span>
      </label>
      <label class="filter-option">
        <input type="radio" name="filter-sponsorship" value="all" ${state.jobs.sponsorship === 'all' ? 'checked' : ''} />
        <span>All Vacancies</span>
      </label>
    </div>

    <!-- Tech Stack -->
    <div class="filter-group">
      <div class="filter-group-title">💻 Tech Stack</div>
      <div style="display: flex; flex-wrap: wrap; gap: 6px;">
        ${popularSkills
          .map((sk) => {
            const isSelected = state.jobs.skill === sk;
            return `
            <button 
              class="filter-skill-btn" 
              data-skill="${escapeHtml(sk)}"
              style="padding: 4px 10px; border-radius: 6px; font-size: 0.78rem; font-weight: 600; border: ${isSelected ? '1px solid #2563eb' : '1px solid #e2e8f0'}; background-color: ${isSelected ? '#eff6ff' : '#f8fafc'}; color: ${isSelected ? '#1d4ed8' : '#334155'}; cursor: pointer; transition: all 0.15s;"
            >
              ${escapeHtml(sk)}
            </button>
          `;
          })
          .join('')}
      </div>
    </div>

    <!-- Location Priority -->
    <div class="filter-group">
      <div class="filter-group-title">📍 Location Priority</div>
      <label class="filter-option">
        <input type="radio" name="filter-location" value="all" ${!state.jobs.location || state.jobs.location === 'all' ? 'checked' : ''} />
        <span>All UK</span>
      </label>
      <label class="filter-option">
        <input type="radio" name="filter-location" value="london" ${state.jobs.location === 'london' ? 'checked' : ''} />
        <span>London</span>
      </label>
      <label class="filter-option">
        <input type="radio" name="filter-location" value="manchester" ${state.jobs.location === 'manchester' ? 'checked' : ''} />
        <span>Manchester / Greater MCR</span>
      </label>
      <label class="filter-option">
        <input type="radio" name="filter-location" value="north_west" ${state.jobs.location === 'north_west' ? 'checked' : ''} />
        <span>North West England</span>
      </label>
      <label class="filter-option">
        <input type="radio" name="filter-location" value="remote_uk" ${state.jobs.location === 'remote_uk' ? 'checked' : ''} />
        <span>Remote UK</span>
      </label>
      <label class="filter-option">
        <input type="radio" name="filter-location" value="hybrid" ${state.jobs.location === 'hybrid' ? 'checked' : ''} />
        <span>Hybrid UK</span>
      </label>
    </div>

    <!-- Freshness -->
    <div class="filter-group">
      <div class="filter-group-title">⏰ Freshness</div>
      <select 
        id="filter-days-select"
        style="padding: 8px 12px; border-radius: 8px; border: 1px solid #cbd5e1; font-size: 0.85rem; background-color: #ffffff; color: #0f172a; outline: none;"
      >
        <option value="" ${!state.jobs.days ? 'selected' : ''}>Any time</option>
        <option value="1" ${state.jobs.days === 1 ? 'selected' : ''}>Last 24 Hours</option>
        <option value="3" ${state.jobs.days === 3 ? 'selected' : ''}>Last 3 Days</option>
        <option value="7" ${state.jobs.days === 7 ? 'selected' : ''}>Last 7 Days</option>
        <option value="14" ${state.jobs.days === 14 ? 'selected' : ''}>Last 14 Days</option>
      </select>
    </div>

    <!-- Work Arrangement -->
    <div class="filter-group">
      <div class="filter-group-title">🌐 Work Arrangement</div>
      <select 
        id="filter-work-type-select"
        style="padding: 8px 12px; border-radius: 8px; border: 1px solid #cbd5e1; font-size: 0.85rem; background-color: #ffffff; color: #0f172a; outline: none;"
      >
        <option value="all" ${!state.jobs.work_type || state.jobs.work_type === 'all' ? 'selected' : ''}>All Arrangements</option>
        <option value="Remote UK" ${state.jobs.work_type === 'Remote UK' ? 'selected' : ''}>Remote UK Only</option>
        <option value="Hybrid" ${state.jobs.work_type === 'Hybrid' ? 'selected' : ''}>Hybrid Only</option>
        <option value="On-site" ${state.jobs.work_type === 'On-site' ? 'selected' : ''}>On-site Only</option>
      </select>
    </div>
  `;

  document.getElementById('jobs-reset-filters-btn')?.addEventListener('click', () => {
    state.jobs.q = '';
    state.jobs.sponsorship = 'confirmed_may_offer';
    state.jobs.location = '';
    state.jobs.skill = '';
    state.jobs.experience_level = 'mid';
    state.jobs.applied_status = 'all';
    state.jobs.days = null;
    state.jobs.work_type = '';
    state.jobs.page = 1;
    navigateTo('/jobs', getActiveJobParams());
  });

  panel.querySelectorAll('input[name="filter-applied-status"]').forEach((radio) => {
    radio.addEventListener('change', (e) => {
      state.jobs.applied_status = e.target.value;
      state.jobs.page = 1;
      navigateTo('/jobs', getActiveJobParams());
    });
  });

  panel.querySelectorAll('input[name="filter-exp"]').forEach((radio) => {
    radio.addEventListener('change', (e) => {
      state.jobs.experience_level = e.target.value;
      state.jobs.page = 1;
      navigateTo('/jobs', getActiveJobParams());
    });
  });

  panel.querySelectorAll('input[name="filter-sponsorship"]').forEach((radio) => {
    radio.addEventListener('change', (e) => {
      state.jobs.sponsorship = e.target.value;
      state.jobs.page = 1;
      navigateTo('/jobs', getActiveJobParams());
    });
  });

  panel.querySelectorAll('.filter-skill-btn').forEach((btn) => {
    btn.addEventListener('click', (e) => {
      const sk = e.currentTarget.getAttribute('data-skill');
      state.jobs.skill = state.jobs.skill === sk ? '' : sk;
      state.jobs.page = 1;
      navigateTo('/jobs', getActiveJobParams());
    });
  });

  panel.querySelectorAll('input[name="filter-location"]').forEach((radio) => {
    radio.addEventListener('change', (e) => {
      state.jobs.location = e.target.value;
      state.jobs.page = 1;
      navigateTo('/jobs', getActiveJobParams());
    });
  });

  document.getElementById('filter-days-select')?.addEventListener('change', (e) => {
    state.jobs.days = e.target.value ? Number(e.target.value) : null;
    state.jobs.page = 1;
    navigateTo('/jobs', getActiveJobParams());
  });

  document.getElementById('filter-work-type-select')?.addEventListener('change', (e) => {
    state.jobs.work_type = e.target.value;
    state.jobs.page = 1;
    navigateTo('/jobs', getActiveJobParams());
  });
}

function renderJobsResults() {
  const summaryEl = document.getElementById('jobs-count-summary');
  const resultsCol = document.getElementById('jobs-results-container');
  const paginationEl = document.getElementById('jobs-pagination-container');

  if (summaryEl) {
    let extra = '';
    if (state.jobs.experience_level) extra += ` [<strong>${escapeHtml(state.jobs.experience_level.toUpperCase())}</strong> level]`;
    if (state.jobs.skill) extra += ` matching <strong>${escapeHtml(state.jobs.skill)}</strong>`;
    if (state.jobs.location) extra += ` in <strong>${escapeHtml(state.jobs.location)}</strong>`;
    if (state.jobs.applied_status === 'applied_only') extra += ` (<strong>Applied Jobs Only</strong>)`;
    summaryEl.innerHTML = `Found <strong style="color: #0f172a;">${state.jobs.total}</strong> software engineering roles${extra}`;
  }

  if (resultsCol) {
    if (state.jobs.items.length === 0) {
      resultsCol.innerHTML = `
        <div style="background: white; border: 1px solid #e2e8f0; border-radius: 12px; padding: 48px 24px; text-align: center; color: #64748b;">
          <div style="font-size: 32px; margin-bottom: 12px;">🔍</div>
          <h3 style="font-size: 1.15rem; font-weight: 700; color: #0f172a; margin-bottom: 6px;">No matching job vacancies found</h3>
          <p style="font-size: 0.9rem; max-width: 480px; margin: 0 auto 16px;">
            Try clearing filters or switching experience level and sponsorship options.
          </p>
          <button id="jobs-clear-all-filters-btn" class="btn-primary">Clear Filters</button>
        </div>
      `;
      document.getElementById('jobs-clear-all-filters-btn')?.addEventListener('click', () => {
        state.jobs.q = '';
        state.jobs.sponsorship = 'all';
        state.jobs.location = '';
        state.jobs.skill = '';
        state.jobs.experience_level = '';
        state.jobs.applied_status = 'all';
        state.jobs.days = null;
        state.jobs.work_type = '';
        state.jobs.page = 1;
        navigateTo('/jobs', getActiveJobParams());
      });
    } else {
      resultsCol.innerHTML = state.jobs.items.map((job) => renderJobCardHtml(job)).join('');

      resultsCol.querySelectorAll('.job-card-select-btn').forEach((btn) => {
        btn.addEventListener('click', (e) => {
          const jobId = e.currentTarget.getAttribute('data-job-id');
          const job = state.jobs.items.find((j) => String(j.JobId) === String(jobId));
          if (job) openJobModal(job);
        });
      });

      resultsCol.querySelectorAll('.job-card-decline-btn').forEach((btn) => {
        btn.addEventListener('click', (e) => {
          const jobId = e.currentTarget.getAttribute('data-job-id');
          const job = state.jobs.items.find((j) => String(j.JobId) === String(jobId));
          if (job) declineJob(job, e);
        });
      });

      resultsCol.querySelectorAll('.btn-applied-toggle').forEach((btn) => {
        btn.addEventListener('click', (e) => {
          const jobId = e.currentTarget.getAttribute('data-job-id');
          const job = state.jobs.items.find((j) => String(j.JobId) === String(jobId));
          if (job) toggleJobApplied(job, e);
        });
      });
    }
  }

  if (paginationEl) {
    if (state.jobs.totalPages <= 1) {
      paginationEl.innerHTML = '';
    } else {
      const p = state.jobs.page;
      const totalP = state.jobs.totalPages;

      let pagesHtml = '';
      for (let i = 1; i <= Math.min(totalP, 7); i++) {
        pagesHtml += `
          <button class="page-btn ${i === p ? 'active' : ''} jobs-page-num-btn" data-page="${i}">
            ${i}
          </button>
        `;
      }

      paginationEl.innerHTML = `
        <div class="pagination-container">
          <div style="font-size: 0.875rem; color: #64748b;">
            Showing page <strong>${p}</strong> of <strong>${totalP}</strong>
          </div>
          <div class="pagination-pages">
            <button class="page-btn" id="jobs-prev-page-btn" ${p <= 1 ? 'disabled' : ''}>← Previous</button>
            ${pagesHtml}
            <button class="page-btn" id="jobs-next-page-btn" ${p >= totalP ? 'disabled' : ''}>Next →</button>
          </div>
        </div>
      `;

      document.getElementById('jobs-prev-page-btn')?.addEventListener('click', () => {
        if (p > 1) {
          state.jobs.page = p - 1;
          navigateTo('/jobs', getActiveJobParams());
          window.scrollTo({ top: 0, behavior: 'smooth' });
        }
      });

      document.getElementById('jobs-next-page-btn')?.addEventListener('click', () => {
        if (p < totalP) {
          state.jobs.page = p + 1;
          navigateTo('/jobs', getActiveJobParams());
          window.scrollTo({ top: 0, behavior: 'smooth' });
        }
      });

      paginationEl.querySelectorAll('.jobs-page-num-btn').forEach((btn) => {
        btn.addEventListener('click', (e) => {
          const pageNum = Number(e.currentTarget.getAttribute('data-page'));
          state.jobs.page = pageNum;
          navigateTo('/jobs', getActiveJobParams());
          window.scrollTo({ top: 0, behavior: 'smooth' });
        });
      });
    }
  }
}

function renderJobCardHtml(job) {
  const comp = job.Company || {};
  const spons = job.Sponsorship || {};
  const applied = isJobApplied(job.JobId);

  let sourceLabel = 'ATS Direct';
  if (job.SourceJobUrl?.includes('greenhouse')) sourceLabel = 'Greenhouse';
  else if (job.SourceJobUrl?.includes('lever')) sourceLabel = 'Lever';
  else if (job.SourceJobUrl?.includes('ashby')) sourceLabel = 'Ashby';

  return `
    <div class="job-card" data-job-id="${job.JobId}">
      <div class="job-card-header">
        <div style="flex: 1;">
          <div class="job-title-row">
            <h3 class="job-title job-card-select-btn" data-job-id="${job.JobId}">
              ${escapeHtml(job.Title)}
            </h3>
            ${getExperienceBadgeHtml(job.ExperienceLevel, job.Title)}
            ${getRemoteBadgeHtml(job.RemoteType)}
            <span class="applied-badge-slot">
              ${applied ? `<span class="badge-applied">✓ Applied</span>` : ''}
            </span>
          </div>
          <div style="display: flex; align-items: center; gap: 8px; margin-top: 4px;">
            <span class="company-name-link job-card-select-btn" data-job-id="${job.JobId}">
              ${escapeHtml(comp.CompanyName || 'UK Employer')}
            </span>
            ${
              comp.SponsorLicenceStatus === 'LICENSED'
                ? `<span style="font-size: 0.72rem; color: #0284c7; background: #e0f2fe; padding: 1px 6px; border-radius: 4px; font-weight: 700;" title="Company holds an official UK Home Office Worker sponsor licence">Licensed Sponsor</span>`
                : ''
            }
          </div>
        </div>

        <div style="display: flex; flex-direction: column; align-items: flex-end; gap: 6px;">
          ${getSponsorshipBadgeHtml(spons.SponsorshipStatus)}
          ${getMatchScoreHtml(job.MatchScore)}
        </div>
      </div>

      <div class="job-meta-row">
        <div class="job-meta-item">
          <span>📍</span>
          <span>${escapeHtml(job.Location || 'United Kingdom')}</span>
        </div>

        ${
          job.SalaryText
            ? `
          <div class="job-meta-item" style="color: #047857; font-weight: 600;">
            <span>💷 ${escapeHtml(job.SalaryText)}</span>
          </div>
        `
            : ''
        }

        <div class="job-meta-item" title="Date posted at source">
          <span>📅</span>
          <span>Posted: ${formatRelativeTime(job.PostedDate)}</span>
        </div>

        <div class="job-meta-item" title="Last verified active at source URL">
          <span>⏰</span>
          <span>Verified: ${formatRelativeTime(job.LastVerifiedAt)}</span>
        </div>
      </div>

      <!-- Tech Stack Pills -->
      ${
        job.Skills && job.Skills.length > 0
          ? `
        <div style="display: flex; flex-wrap: wrap; gap: 6px; margin-top: -2px;">
          ${job.Skills.map(
            (sk) => `
            <span class="tech-pill ${sk.RequiredOrPreferred === 'Required' ? 'primary' : ''}">
              ${escapeHtml(sk.SkillName)}
            </span>
          `
          ).join('')}
        </div>
      `
          : ''
      }

      <div class="job-card-footer">
        <div style="font-size: 0.78rem; color: #64748b; display: flex; align-items: center; gap: 10px;">
          <span>Source: <strong>${sourceLabel}</strong></span>
          <button 
            class="btn-applied-toggle ${applied ? 'applied' : ''}" 
            data-job-id="${job.JobId}"
            title="${applied ? 'Click to unmark as applied' : 'Mark job as applied'}"
          >
            <span>✓</span>
            <span>${applied ? 'Applied' : 'Mark Applied'}</span>
          </button>
        </div>

        <div style="display: flex; align-items: center; gap: 8px;">
          <button 
            class="btn-decline job-card-decline-btn" 
            data-job-id="${job.JobId}"
            title="Decline this job (remove from list)"
          >
            <span>✕</span>
            <span>Decline</span>
          </button>
          <button class="btn-secondary job-card-select-btn" data-job-id="${job.JobId}">
            View Details
          </button>
          <a 
            href="${escapeHtml(job.ApplyUrl || job.SourceJobUrl)}" 
            target="_blank" 
            rel="noopener noreferrer" 
            class="btn-primary"
            style="text-decoration: none;"
          >
            <span>Apply on Site</span>
            <span>↗</span>
          </a>
        </div>
      </div>
    </div>
  `;
}

// ==========================================
// 3. COMPANIES CONTROLLER
// ==========================================
async function loadCompaniesData() {
  const container = document.getElementById('companies-view');
  if (!container) return;

  renderCompaniesLayout();

  const gridEl = document.getElementById('companies-grid-container');
  if (gridEl) {
    gridEl.innerHTML = `
      <div style="text-align: center; padding: 40px 20px; color: #64748b; grid-column: 1 / -1;">
        <div class="spinning" style="display: inline-block; font-size: 24px; margin-bottom: 8px;">🔄</div>
        <p>Loading company records...</p>
      </div>
    `;
  }

  try {
    const data = await api.getCompanies({
      q: state.companies.q || undefined,
      licensed_only: state.companies.licensedOnly,
    });
    state.companies.items = data.items || [];
    renderCompaniesGrid();
  } catch (err) {
    if (gridEl) {
      gridEl.innerHTML = `
        <div style="grid-column: 1 / -1; padding: 24px; background: #fff1f2; color: #9f1239; border-radius: 12px; border: 1px solid #fecdd3;">
          <strong>Error loading companies:</strong> ${escapeHtml(err.message)}
        </div>
      `;
    }
  }
}

function renderCompaniesLayout() {
  const container = document.getElementById('companies-view');
  if (!container) return;

  if (document.getElementById('companies-lookup-form')) {
    return;
  }

  container.innerHTML = `
    <div style="display: flex; flex-direction: column; gap: 24px;">
      <!-- Header -->
      <div>
        <h1 style="font-size: 1.75rem; font-weight: 800; color: #0f172a;">
          UK Employers & Sponsor Licence Register
        </h1>
        <p style="color: #64748b; font-size: 0.95rem; margin-top: 4px;">
          Cross-referenced database of technology companies and their official UK Home Office Worker sponsorship status.
        </p>
      </div>

      <!-- Live Home Office Sponsor Lookup Tool -->
      <div style="background: linear-gradient(135deg, #eff6ff 0%, #dbeafe 100%); border: 1px solid #bfdbfe; border-radius: 14px; padding: 20px; box-shadow: var(--shadow-sm);">
        <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 10px;">
          <span style="font-size: 20px;">🛡️</span>
          <h3 style="font-size: 1.05rem; font-weight: 800; color: #1e3a8a;">
            Instant UK Government Sponsor Register Verification Tool
          </h3>
        </div>
        <p style="font-size: 0.875rem; color: #1e40af; margin-bottom: 14px;">
          Search any UK company to check if they hold an active Skilled Worker visa sponsor licence.
        </p>

        <form id="companies-lookup-form" style="display: flex; gap: 10px; max-width: 640px;">
          <input 
            type="text" 
            id="companies-lookup-input"
            placeholder="Enter company name (e.g. Monzo, Deliveroo, Spotify, Snyk)..."
            value="${escapeHtml(state.companies.lookupName)}"
            style="flex: 1; padding: 10px 14px; border-radius: 8px; border: 1px solid #93c5fd; background-color: #ffffff; font-size: 0.9rem; outline: none;"
          />
          <button 
            type="submit" 
            id="companies-lookup-submit-btn"
            class="btn-primary" 
            style="padding: 0 20px;"
          >
            <span>Verify Sponsor Status</span>
          </button>
        </form>

        <div id="companies-lookup-result-box"></div>
      </div>

      <!-- Search & Filter Bar -->
      <div style="background: white; border: 1px solid #e2e8f0; border-radius: 14px; padding: 16px; box-shadow: var(--shadow-sm); display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 14px;">
        <div style="position: relative; width: 340px;">
          <span style="position: absolute; left: 12px; top: 12px; color: #94a3b8; font-size: 14px;">🔍</span>
          <input 
            type="text"
            id="companies-search-input"
            placeholder="Search tracked companies..."
            value="${escapeHtml(state.companies.q)}"
            style="width: 100%; padding: 8px 12px 8px 36px; border-radius: 8px; border: 1px solid #cbd5e1; font-size: 0.875rem; outline: none;"
          />
        </div>

        <label style="display: flex; align-items: center; gap: 8px; font-size: 0.875rem; font-weight: 600; color: #334155; cursor: pointer;">
          <input 
            type="checkbox"
            id="companies-licensed-only-check"
            ${state.companies.licensedOnly ? 'checked' : ''}
            style="width: 16px; height: 16px; accent-color: #2563eb;"
          />
          <span>Only show companies with verified sponsor licence</span>
        </label>
      </div>

      <!-- Grid -->
      <div id="companies-grid-container" style="display: grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); gap: 16px;">
      </div>
    </div>
  `;

  const lookupForm = document.getElementById('companies-lookup-form');
  const lookupInput = document.getElementById('companies-lookup-input');
  const searchInput = document.getElementById('companies-search-input');
  const licensedOnlyCheck = document.getElementById('companies-licensed-only-check');

  lookupForm?.addEventListener('submit', async (e) => {
    e.preventDefault();
    const query = lookupInput ? lookupInput.value.trim() : '';
    if (!query) return;

    const resultBox = document.getElementById('companies-lookup-result-box');
    const submitBtn = document.getElementById('companies-lookup-submit-btn');

    if (submitBtn) {
      submitBtn.disabled = true;
      submitBtn.innerText = 'Checking...';
    }

    try {
      const res = await api.lookupSponsor(query);
      if (resultBox) {
        if (res.found) {
          resultBox.innerHTML = `
            <div style="margin-top: 14px; padding: 14px; border-radius: 8px; background-color: #ecfdf5; border: 1px solid #a7f3d0; color: #065f46; font-size: 0.9rem;">
              <div style="display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 10px;">
                <div>
                  <strong>✓ LICENSED SPONSOR: ${escapeHtml(res.company_name)}</strong>
                  <div style="font-size: 0.82rem; margin-top: 2px;">
                    Route: <strong>${escapeHtml(res.route)}</strong> • Rating: <strong>${escapeHtml(res.rating)}</strong> • Location: <strong>${escapeHtml(res.town)}</strong>
                  </div>
                </div>
                <button 
                  id="lookup-view-openings-btn"
                  style="background: #059669; color: white; padding: 6px 12px; border-radius: 6px; font-size: 0.8rem; font-weight: 700; cursor: pointer;"
                >
                  View Openings →
                </button>
              </div>
            </div>
          `;
          document.getElementById('lookup-view-openings-btn')?.addEventListener('click', () => {
            navigateTo('/jobs', { q: res.company_name });
          });
        } else {
          resultBox.innerHTML = `
            <div style="margin-top: 14px; padding: 14px; border-radius: 8px; background-color: #fff1f2; border: 1px solid #fecdd3; color: #9f1239; font-size: 0.9rem;">
              <strong>✕ Not Found on Current Register:</strong> ${escapeHtml(res.message || 'No active sponsor licence found under this exact name.')}
            </div>
          `;
        }
      }
    } catch (err) {
      if (resultBox) {
        resultBox.innerHTML = `
          <div style="margin-top: 14px; padding: 14px; border-radius: 8px; background-color: #fff1f2; border: 1px solid #fecdd3; color: #9f1239; font-size: 0.9rem;">
            Lookup error: ${escapeHtml(err.message)}
          </div>
        `;
      }
    } finally {
      if (submitBtn) {
        submitBtn.disabled = false;
        submitBtn.innerText = 'Verify Sponsor Status';
      }
    }
  });

  let searchTimeout = null;
  searchInput?.addEventListener('input', (e) => {
    clearTimeout(searchTimeout);
    searchTimeout = setTimeout(() => {
      state.companies.q = e.target.value.trim();
      loadCompaniesData();
    }, 300);
  });

  licensedOnlyCheck?.addEventListener('change', (e) => {
    state.companies.licensedOnly = e.target.checked;
    loadCompaniesData();
  });
}

function renderCompaniesGrid() {
  const gridEl = document.getElementById('companies-grid-container');
  if (!gridEl) return;

  if (state.companies.items.length === 0) {
    gridEl.innerHTML = `
      <div style="grid-column: 1 / -1; background: white; border: 1px solid #e2e8f0; border-radius: 12px; padding: 40px; text-align: center; color: #64748b;">
        <p style="font-weight: 600;">No company records match your criteria.</p>
      </div>
    `;
    return;
  }

  gridEl.innerHTML = state.companies.items
    .map(
      (c) => `
    <div style="background: white; border: 1px solid #e2e8f0; border-radius: 12px; padding: 20px; box-shadow: var(--shadow-sm); display: flex; flex-direction: column; justify-content: space-between; gap: 14px;">
      <div>
        <div style="display: flex; align-items: flex-start; justify-content: space-between; gap: 10px;">
          <h3 style="font-size: 1.1rem; font-weight: 700; color: #0f172a;">
            ${escapeHtml(c.CompanyName)}
          </h3>
          ${
            c.SponsorLicenceStatus === 'LICENSED'
              ? `<span style="background: #ecfdf5; color: #047857; border: 1px solid #a7f3d0; padding: 3px 8px; border-radius: 6px; font-size: 0.75rem; font-weight: 700; white-space: nowrap;">✓ Licensed</span>`
              : `<span style="background: #f8fafc; color: #64748b; border: 1px solid #e2e8f0; padding: 3px 8px; border-radius: 6px; font-size: 0.75rem; font-weight: 600; white-space: nowrap;">Status: ${escapeHtml(c.SponsorLicenceStatus)}</span>`
          }
        </div>

        ${
          c.SponsorRoute
            ? `
          <div style="font-size: 0.82rem; color: #475569; margin-top: 6px;">
            Route: <strong>${escapeHtml(c.SponsorRoute)}</strong> (${escapeHtml(c.SponsorRating || 'A rating')})
          </div>
        `
            : ''
        }
      </div>

      <div style="display: flex; align-items: center; justify-content: space-between; padding-top: 12px; border-top: 1px solid #f1f5f9;">
        <div style="font-size: 0.85rem; color: #64748b; display: flex; align-items: center; gap: 6px;">
          <span>💼</span>
          <span><strong>${c.ActiveJobsCount || 0}</strong> active jobs</span>
        </div>

        <div style="display: flex; align-items: center; gap: 8px;">
          ${
            c.CareersUrl
              ? `
            <a href="${escapeHtml(c.CareersUrl)}" target="_blank" rel="noopener noreferrer" class="btn-secondary" style="padding: 4px 10px; font-size: 0.8rem;">
              <span>Careers</span>
              <span>↗</span>
            </a>
          `
              : ''
          }
          <button 
            class="btn-primary company-view-jobs-btn" 
            data-company-name="${escapeHtml(c.CompanyName)}"
            style="padding: 4px 12px; font-size: 0.8rem;"
          >
            View Jobs
          </button>
        </div>
      </div>
    </div>
  `
    )
    .join('');

  gridEl.querySelectorAll('.company-view-jobs-btn').forEach((btn) => {
    btn.addEventListener('click', (e) => {
      const companyName = e.currentTarget.getAttribute('data-company-name');
      navigateTo('/jobs', { q: companyName });
    });
  });
}

// ==========================================
// 4. ADMIN CONTROLLER
// ==========================================
async function loadAdminData() {
  const container = document.getElementById('admin-view');
  if (!container) return;

  // Check if user is logged in as administrator
  if (!api.isAdminLoggedIn()) {
    renderAdminLoginScreen();
    return;
  }

  state.admin.loading = true;
  container.innerHTML = `
    <div style="text-align: center; padding: 60px 20px; color: #64748b;">
      <div class="spinning" style="display: inline-block; font-size: 28px; margin-bottom: 12px;">🔄</div>
      <p style="font-weight: 600;">Loading Admin Portal & Scheduler Telemetry...</p>
    </div>
  `;

  try {
    const [sources, runs, monitorData] = await Promise.all([
      api.getSources(),
      api.getScrapeRuns(30),
      api.getMonitorStatus().catch(() => null),
    ]);
    state.admin.sources = sources;
    state.admin.runs = runs;
    state.admin.monitor = monitorData;
    renderAdminView();
  } catch (err) {
    if (err.message.includes('401') || err.message.includes('unauthorized')) {
      api.logout();
      renderAdminLoginScreen();
    } else {
      container.innerHTML = `
        <div style="padding: 24px; background: #fff1f2; color: #9f1239; border-radius: 12px; border: 1px solid #fecdd3;">
          <strong>Error loading admin:</strong> ${escapeHtml(err.message)}
          <div style="margin-top: 12px;">
            <button id="admin-retry-btn" class="btn-primary">Retry</button>
          </div>
        </div>
      `;
      document.getElementById('admin-retry-btn')?.addEventListener('click', loadAdminData);
    }
  } finally {
    state.admin.loading = false;
  }
}

function renderAdminLoginScreen() {
  const container = document.getElementById('admin-view');
  if (!container) return;

  container.innerHTML = `
    <div style="padding: 40px 20px; display: flex; justify-content: center;">
      <div class="auth-card">
        <div style="text-align: center;">
          <div style="width: 52px; height: 52px; background: #eff6ff; color: #1d4ed8; border-radius: 14px; display: flex; align-items: center; justify-content: center; font-size: 1.8rem; margin: 0 auto 12px;">
            🔐
          </div>
          <h2 style="font-size: 1.4rem; font-weight: 800; color: #0f172a;">Administrator Access Required</h2>
          <p style="font-size: 0.875rem; color: #64748b; margin-top: 4px;">
            Please log in with administrator credentials to manage ATS feeds, trigger manual scrape cycles, and monitor background scheduler telemetry.
          </p>
        </div>

        <form id="inline-admin-login-form" style="display: flex; flex-direction: column; gap: 14px; margin-top: 8px;">
          <div id="inline-auth-error-msg" style="display: none; padding: 10px 14px; background: #fff1f2; border: 1px solid #fecdd3; border-radius: 8px; color: #9f1239; font-size: 0.85rem; font-weight: 600;"></div>

          <div>
            <label style="display: block; font-size: 0.82rem; font-weight: 700; color: #334155; margin-bottom: 4px;">Admin Username</label>
            <input 
              type="text" 
              id="inline-auth-username"
              value="admin"
              required
              style="width: 100%; padding: 10px 14px; border-radius: 8px; border: 1px solid #cbd5e1; font-size: 0.9rem; outline: none;"
            />
          </div>

          <div>
            <label style="display: block; font-size: 0.82rem; font-weight: 700; color: #334155; margin-bottom: 4px;">Admin Password</label>
            <input 
              type="password" 
              id="inline-auth-password"
              placeholder="Enter admin password..."
              required
              style="width: 100%; padding: 10px 14px; border-radius: 8px; border: 1px solid #cbd5e1; font-size: 0.9rem; outline: none;"
            />
          </div>

          <button 
            type="submit" 
            id="inline-auth-submit-btn"
            class="btn-primary" 
            style="justify-content: center; padding: 12px; font-size: 0.95rem; margin-top: 4px;"
          >
            Log In to Admin Panel
          </button>
        </form>

        <div style="font-size: 0.8rem; color: #64748b; text-align: center; border-top: 1px solid #f1f5f9; padding-top: 14px;">
          Only authorized administrators can modify system settings.
        </div>
      </div>
    </div>
  `;

  const form = document.getElementById('inline-admin-login-form');
  const errorMsg = document.getElementById('inline-auth-error-msg');
  const submitBtn = document.getElementById('inline-auth-submit-btn');

  form?.addEventListener('submit', async (e) => {
    e.preventDefault();
    const username = document.getElementById('inline-auth-username').value.trim();
    const password = document.getElementById('inline-auth-password').value.trim();

    if (errorMsg) errorMsg.style.display = 'none';
    if (submitBtn) {
      submitBtn.disabled = true;
      submitBtn.innerText = 'Signing in...';
    }

    try {
      await api.login(username, password);
      showToast('Logged in as Administrator 🔓', 'success');
      renderAuthNav();
      loadAdminData();
    } catch (err) {
      if (errorMsg) {
        errorMsg.innerText = err.message || 'Invalid administrator credentials.';
        errorMsg.style.display = 'block';
      }
    } finally {
      if (submitBtn) {
        submitBtn.disabled = false;
        submitBtn.innerText = 'Log In to Admin Panel';
      }
    }
  });
}

function renderAdminView() {
  const container = document.getElementById('admin-view');
  if (!container) return;

  const currentSubTab = state.admin.subTab || 'monitor';
  const mon = state.admin.monitor || {};
  const isRunning = mon.scheduler_running ?? true;
  const isEnabled = mon.scheduler_enabled ?? true;
  const totalRuns = mon.total_runs || state.admin.runs.length || 0;
  const successRuns = mon.success_runs || state.admin.runs.filter(r => r.Status === 'SUCCESS').length || 0;
  const failedRuns = mon.failed_runs || state.admin.runs.filter(r => r.Status === 'FAILED').length || 0;
  const successRate = totalRuns > 0 ? Math.round((successRuns / totalRuns) * 100) : 100;
  const totalAdded = (mon.total_jobs_added || 0).toLocaleString();
  const totalUpdated = (mon.total_jobs_updated || 0).toLocaleString();
  const totalDups = (mon.total_duplicates_prevented || 0).toLocaleString();
  const nextRunFormatted = mon.next_run_time ? new Date(mon.next_run_time).toLocaleTimeString('en-GB') : 'Active (Every 5 mins)';
  const lastRunFormatted = mon.last_run_time ? formatRelativeTime(mon.last_run_time) : 'Recently';

  let subTabContentHtml = '';

  if (currentSubTab === 'monitor') {
    subTabContentHtml = `
      <!-- Live Scheduler Telemetry & KPIs Section -->
      <div style="display: flex; flex-direction: column; gap: 20px;">
        <!-- Top Engine Banner -->
        <div style="background: white; border: 1px solid #e2e8f0; border-radius: 14px; padding: 20px; box-shadow: var(--shadow-sm); display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 14px;">
          <div>
            <div style="display: flex; align-items: center; gap: 8px;">
              <span class="pulse-dot ${isRunning ? 'active' : 'inactive'}"></span>
              <h2 style="font-size: 1.15rem; font-weight: 800; color: #0f172a; margin: 0;">
                APScheduler Engine Status: ${isRunning ? '<span style="color: #059669;">ACTIVE & RUNNING</span>' : '<span style="color: #dc2626;">PAUSED</span>'}
              </h2>
            </div>
            <p style="color: #64748b; font-size: 0.88rem; margin: 4px 0 0 0;">
              Cadence: <strong>Every 5 minutes</strong> • Next Cycle: <strong style="color: #059669;">⏰ ${nextRunFormatted}</strong> • Last: <strong>${lastRunFormatted}</strong>
            </p>
          </div>

          <div style="display: flex; align-items: center; gap: 10px; flex-wrap: wrap;">
            <button id="admin-subtab-trigger-btn" class="btn-primary" style="padding: 8px 16px; font-size: 0.85rem;">
              <span>⚡ Run Ingestion Now</span>
            </button>
            <button id="admin-subtab-refresh-btn" class="btn-secondary" style="padding: 8px 14px; font-size: 0.85rem;">
              <span>🔄 Refresh</span>
            </button>
          </div>
        </div>

        <!-- 4 KPI Cards -->
        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 14px;">
          <div class="stat-card" style="margin-bottom: 0;">
            <div style="font-size: 1.5rem; width: 44px; height: 44px; border-radius: 10px; background: #eff6ff; display: flex; align-items: center; justify-content: center;">⏱️</div>
            <div>
              <div style="font-size: 0.75rem; font-weight: 700; color: #64748b; text-transform: uppercase;">Scraping Cycles</div>
              <div style="font-size: 1.45rem; font-weight: 800; color: #0f172a; line-height: 1.2;">${totalRuns}</div>
              <div style="font-size: 0.75rem; color: #059669; font-weight: 600;">${successRuns} success • ${failedRuns} fail</div>
            </div>
          </div>

          <div class="stat-card" style="margin-bottom: 0;">
            <div style="font-size: 1.5rem; width: 44px; height: 44px; border-radius: 10px; background: #ecfdf5; display: flex; align-items: center; justify-content: center;">🎯</div>
            <div>
              <div style="font-size: 0.75rem; font-weight: 700; color: #64748b; text-transform: uppercase;">Engine Health</div>
              <div style="font-size: 1.45rem; font-weight: 800; color: ${successRate >= 90 ? '#059669' : '#d97706'}; line-height: 1.2;">${successRate}%</div>
              <div style="font-size: 0.75rem; color: #64748b;">Cycle reliability score</div>
            </div>
          </div>

          <div class="stat-card" style="margin-bottom: 0;">
            <div style="font-size: 1.5rem; width: 44px; height: 44px; border-radius: 10px; background: #f0f9ff; display: flex; align-items: center; justify-content: center;">💼</div>
            <div>
              <div style="font-size: 0.75rem; font-weight: 700; color: #64748b; text-transform: uppercase;">Jobs Ingested</div>
              <div style="font-size: 1.45rem; font-weight: 800; color: #0284c7; line-height: 1.2;">${totalAdded} <span style="font-size: 0.8rem; font-weight: 600; color: #64748b;">new</span></div>
              <div style="font-size: 0.75rem; color: #64748b;">${totalUpdated} updated</div>
            </div>
          </div>

          <div class="stat-card" style="margin-bottom: 0;">
            <div style="font-size: 1.5rem; width: 44px; height: 44px; border-radius: 10px; background: #fdf4ff; display: flex; align-items: center; justify-content: center;">🛡️</div>
            <div>
              <div style="font-size: 0.75rem; font-weight: 700; color: #64748b; text-transform: uppercase;">Duplicate Shield</div>
              <div style="font-size: 1.45rem; font-weight: 800; color: #7c3aed; line-height: 1.2;">${totalDups}</div>
              <div style="font-size: 0.75rem; color: #64748b;">Duplicates blocked</div>
            </div>
          </div>
        </div>

        <!-- Registered Sources Summary & Recent Runs Preview -->
        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); gap: 20px;">
          <!-- Active Sources Quick Card -->
          <div style="background: white; border: 1px solid #e2e8f0; border-radius: 14px; padding: 20px; box-shadow: var(--shadow-sm);">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 14px;">
              <h3 style="font-size: 1rem; font-weight: 700; color: #0f172a; margin: 0; display: flex; align-items: center; gap: 6px;">
                <span>🌐</span> Active Ingestion Sources (${state.admin.sources.length})
              </h3>
              <button class="btn-secondary admin-switch-tab-btn" data-target-tab="sources" style="padding: 3px 8px; font-size: 0.75rem;">
                Manage All →
              </button>
            </div>
            <div style="display: flex; flex-direction: column; gap: 10px;">
              ${state.admin.sources.map(s => `
                <div style="display: flex; justify-content: space-between; align-items: center; padding: 8px 12px; background: #f8fafc; border-radius: 8px; border: 1px solid #f1f5f9;">
                  <div>
                    <span style="font-weight: 600; color: #1e293b; font-size: 0.85rem;">${escapeHtml(s.SourceName)}</span>
                    <span style="font-size: 0.75rem; color: #64748b; margin-left: 6px;">(${s.TotalJobsCount || 0} jobs)</span>
                  </div>
                  <span class="badge-status ${s.IsEnabled ? 'status-success' : 'status-failed'}" style="font-size: 0.72rem;">
                    ${s.IsEnabled ? 'ACTIVE' : 'DISABLED'}
                  </span>
                </div>
              `).join('')}
            </div>
          </div>

          <!-- Quick Engine Specifications -->
          <div style="background: white; border: 1px solid #e2e8f0; border-radius: 14px; padding: 20px; box-shadow: var(--shadow-sm);">
            <h3 style="font-size: 1rem; font-weight: 700; color: #0f172a; margin-top: 0; margin-bottom: 14px; display: flex; align-items: center; gap: 6px;">
              <span>⚙️</span> Engine Specifications
            </h3>
            <div style="display: flex; flex-direction: column; gap: 10px; font-size: 0.85rem;">
              <div style="display: flex; justify-content: space-between; border-bottom: 1px solid #f1f5f9; padding-bottom: 6px;">
                <span style="color: #64748b;">Scheduler Type:</span>
                <span style="font-weight: 600; color: #0f172a;">AsyncIO Background Scheduler</span>
              </div>
              <div style="display: flex; justify-content: space-between; border-bottom: 1px solid #f1f5f9; padding-bottom: 6px;">
                <span style="color: #64748b;">Execution Cadence:</span>
                <span style="font-weight: 700; color: #0284c7;">Every 5 minutes</span>
              </div>
              <div style="display: flex; justify-content: space-between; border-bottom: 1px solid #f1f5f9; padding-bottom: 6px;">
                <span style="color: #64748b;">Duplicate Prevention:</span>
                <span style="font-weight: 600; color: #059669;">SHA-256 Fingerprint Shield</span>
              </div>
              <div style="display: flex; justify-content: space-between;">
                <span style="color: #64748b;">Home Office Sync:</span>
                <span style="font-weight: 600; color: #0f172a;">Daily Auto-Validation</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    `;
  } else if (currentSubTab === 'sources') {
    subTabContentHtml = `
      <div style="display: flex; flex-direction: column; gap: 20px;">
        <!-- AI Auto-Discovery & Ingestion Expansion Card -->
        <div style="background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%); color: white; border-radius: 14px; padding: 22px 24px; box-shadow: var(--shadow-md);">
          <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 14px;">
            <div>
              <div style="display: flex; align-items: center; gap: 8px;">
                <span style="font-size: 1.3rem;">🤖</span>
                <h3 style="font-size: 1.15rem; font-weight: 800; margin: 0; color: white;">
                  Automated UK Job Sources & AI Discovery Engine
                </h3>
                <span style="background: rgba(59, 130, 246, 0.2); color: #93c5fd; border: 1px solid rgba(59, 130, 246, 0.4); font-size: 0.72rem; font-weight: 700; padding: 2px 8px; border-radius: 9999px;">
                  AUTONOMOUS SCHEDULER ACTIVE
                </span>
              </div>
              <p style="color: #94a3b8; font-size: 0.88rem; margin: 6px 0 0 0; max-width: 680px; line-height: 1.4;">
                Automatically scans the internet (via AI + live ATS endpoint probes) for UK tech companies and scaleups hiring software engineers, registers their public feeds, and triggers background ingestion.
              </p>
            </div>

            <div style="display: flex; align-items: center; gap: 10px; flex-wrap: wrap;">
              <button id="admin-trigger-discovery-btn" class="btn-primary" style="background: #2563eb; color: white; padding: 9px 16px; font-size: 0.88rem; font-weight: 700; border-radius: 8px; display: inline-flex; align-items: center; gap: 6px;">
                <span>✨</span>
                <span>Auto-Discover New Sources Now</span>
              </button>

              <button id="admin-toggle-add-form-btn" class="btn-secondary" style="background: rgba(255,255,255,0.1); color: white; border: 1px solid rgba(255,255,255,0.2); padding: 9px 14px; font-size: 0.88rem; font-weight: 600; border-radius: 8px;">
                <span>➕ Add Custom Feed</span>
              </button>
            </div>
          </div>

          <!-- Collapsible Manual Add Custom Company Form -->
          <div id="admin-add-custom-source-panel" style="display: none; margin-top: 18px; padding-top: 18px; border-top: 1px solid rgba(255,255,255,0.15);">
            <form id="admin-add-source-form" style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)) auto; gap: 12px; align-items: flex-end;">
              <div>
                <label style="display: block; font-size: 0.78rem; font-weight: 700; color: #cbd5e1; margin-bottom: 4px;">ATS Provider</label>
                <select id="custom-source-provider" style="width: 100%; padding: 8px 12px; border-radius: 6px; border: 1px solid #475569; background: #1e293b; color: white; font-size: 0.85rem;">
                  <option value="greenhouse">Greenhouse (boards-api.greenhouse.io)</option>
                  <option value="lever">Lever (api.lever.co)</option>
                  <option value="ashby">Ashby (api.ashbyhq.com)</option>
                  <option value="workable">Workable (apply.workable.com)</option>
                  <option value="smartrecruiters">SmartRecruiters (api.smartrecruiters.com)</option>
                </select>
              </div>

              <div>
                <label style="display: block; font-size: 0.78rem; font-weight: 700; color: #cbd5e1; margin-bottom: 4px;">Company Slug / Board ID</label>
                <input type="text" id="custom-source-slug" placeholder="e.g. monzo, deliveroo, revolut" required style="width: 100%; padding: 8px 12px; border-radius: 6px; border: 1px solid #475569; background: #1e293b; color: white; font-size: 0.85rem;" />
              </div>

              <div>
                <label style="display: block; font-size: 0.78rem; font-weight: 700; color: #cbd5e1; margin-bottom: 4px;">Company Name (Optional)</label>
                <input type="text" id="custom-source-name" placeholder="e.g. Monzo Bank" style="width: 100%; padding: 8px 12px; border-radius: 6px; border: 1px solid #475569; background: #1e293b; color: white; font-size: 0.85rem;" />
              </div>

              <button type="submit" id="custom-source-submit-btn" class="btn-primary" style="padding: 9px 18px; font-size: 0.85rem; height: 38px; justify-content: center;">
                <span>Register & Ingest</span>
              </button>
            </form>
          </div>
        </div>

        <!-- Header -->
        <div style="display: flex; align-items: center; justify-content: space-between; margin-top: 6px; flex-wrap: wrap; gap: 12px;">
          <div>
            <h2 style="font-size: 1.2rem; font-weight: 800; color: #0f172a; margin: 0; display: flex; align-items: center; gap: 8px;">
              <span>🗄️</span>
              <span>Configured Job Providers & ATS Feeds (${state.admin.sources.length})</span>
            </h2>
            <p style="color: #64748b; font-size: 0.85rem; margin: 4px 0 0 0;">
              Enable or disable ATS scrapers, trigger test feed runs, and monitor stored vacancies.
            </p>
          </div>

          <button id="admin-full-refresh-btn" class="btn-primary" style="display: flex; align-items: center; gap: 6px;">
            <span>⚡</span>
            <span>Run All Feeds Now</span>
          </button>
        </div>

        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 16px;">
          ${state.admin.sources
            .map(
              (src) => {
                let companyCount = 0;
                if (src.ConfigJson) {
                  try {
                    const cfg = json.parse(src.ConfigJson);
                    companyCount = (cfg.companies || []).length;
                  } catch (e) {
                    try {
                      const cfg = JSON.parse(src.ConfigJson);
                      companyCount = (cfg.companies || []).length;
                    } catch(err) {}
                  }
                }
                return `
            <div style="background: white; border: 1px solid #e2e8f0; border-radius: 12px; padding: 18px; box-shadow: var(--shadow-sm); display: flex; flex-direction: column; justify-content: space-between; gap: 12px;">
              <div>
                <div style="display: flex; align-items: center; justify-content: space-between;">
                  <h3 style="font-size: 1rem; font-weight: 700; color: #0f172a;">
                    ${escapeHtml(src.SourceName)}
                  </h3>
                  <button 
                    class="admin-toggle-source-btn"
                    data-source-id="${src.SourceId}"
                    data-enabled="${src.IsEnabled}"
                    style="cursor: pointer; font-size: 1.3rem;"
                    title="${src.IsEnabled ? 'Enabled (Click to disable)' : 'Disabled (Click to enable)'}"
                  >
                    ${src.IsEnabled ? '🟢' : '⚪'}
                  </button>
                </div>
                <div style="font-size: 0.8rem; color: #64748b; margin-top: 4px;">
                  Type: <code>${escapeHtml(src.SourceType)}</code> ${companyCount > 0 ? `• <strong>${companyCount} employers tracked</strong>` : ''}
                </div>
              </div>

              <div style="display: flex; align-items: center; justify-content: space-between; font-size: 0.82rem; color: #64748b; border-top: 1px solid #f1f5f9; padding-top: 10px;">
                <div>
                  <span>Total Jobs: <strong>${src.TotalJobsCount || 0}</strong></span>
                </div>
                <button 
                  class="btn-secondary admin-run-source-btn"
                  data-source-id="${src.SourceId}"
                  ${!src.IsEnabled ? 'disabled' : ''}
                  style="padding: 3px 8px; font-size: 0.78rem;"
                >
                  <span>▶ Run Feed</span>
                </button>
              </div>
            </div>
          `;
              }
            )
            .join('')}
        </div>
      </div>
    `;
  } else if (currentSubTab === 'history') {
    subTabContentHtml = `
      <div style="background: white; border: 1px solid #e2e8f0; border-radius: 14px; padding: 20px; box-shadow: var(--shadow-sm);">
        <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 16px; flex-wrap: wrap; gap: 10px;">
          <div>
            <h2 style="font-size: 1.2rem; font-weight: 800; color: #0f172a; margin: 0; display: flex; align-items: center; gap: 8px;">
              <span>📋</span>
              <span>Recent Ingestion & Scrape Runs</span>
            </h2>
            <p style="color: #64748b; font-size: 0.82rem; margin: 2px 0 0 0;">Execution log across all ATS parsers and automated background cycles (last 30 runs)</p>
          </div>
          <button id="admin-refresh-logs-btn" class="btn-secondary" style="padding: 6px 12px; font-size: 0.82rem;">
            <span>🔄 Refresh Logs</span>
          </button>
        </div>

        <div style="overflow-x: auto;">
          <table style="width: 100%; border-collapse: collapse; font-size: 0.875rem;">
            <thead>
              <tr style="border-bottom: 2px solid #e2e8f0; text-align: left; color: #475569; font-weight: 700; background: #f8fafc;">
                <th style="padding: 10px 12px;">Run ID</th>
                <th style="padding: 10px 12px;">Source</th>
                <th style="padding: 10px 12px;">Started At</th>
                <th style="padding: 10px 12px;">Duration</th>
                <th style="padding: 10px 12px;">Found</th>
                <th style="padding: 10px 12px;">Added</th>
                <th style="padding: 10px 12px;">Updated</th>
                <th style="padding: 10px 12px;">Duplicates</th>
                <th style="padding: 10px 12px;">Status</th>
              </tr>
            </thead>
            <tbody>
              ${state.admin.runs
                .map(
                  (r) => {
                    const dur = r.CompletedAt && r.StartedAt ? `${Math.round((new Date(r.CompletedAt) - new Date(r.StartedAt))/100)/10}s` : (r.DurationSeconds ? `${r.DurationSeconds}s` : '-');
                    return `
                <tr style="border-bottom: 1px solid #f1f5f9;">
                  <td style="padding: 10px 12px; font-weight: 600; color: #64748b;">#${r.ScrapeRunId || '-'}</td>
                  <td style="padding: 10px 12px; font-weight: 600;">${escapeHtml(r.SourceName || 'All Feeds')}</td>
                  <td style="padding: 10px 12px; color: #64748b;">
                    ${r.StartedAt ? new Date(r.StartedAt).toLocaleString('en-GB') : 'N/A'}
                  </td>
                  <td style="padding: 10px 12px; font-family: monospace; color: #334155;">${dur}</td>
                  <td style="padding: 10px 12px;">${r.JobsFound || 0}</td>
                  <td style="padding: 10px 12px; color: #047857; font-weight: 700;">+${r.JobsAdded || 0}</td>
                  <td style="padding: 10px 12px; color: #2563eb;">${r.JobsUpdated || 0}</td>
                  <td style="padding: 10px 12px; color: #7c3aed;">${r.DuplicatesFound || 0}</td>
                  <td style="padding: 10px 12px;">
                    ${
                      r.Status === 'SUCCESS'
                        ? `<span style="background: #ecfdf5; color: #047857; padding: 2px 8px; border-radius: 4px; font-weight: 700; font-size: 0.75rem;">✓ SUCCESS</span>`
                        : r.Status === 'RUNNING'
                        ? `<span style="background: #eff6ff; color: #1d4ed8; padding: 2px 8px; border-radius: 4px; font-weight: 700; font-size: 0.75rem;">🔄 RUNNING</span>`
                        : `<span style="background: #fff1f2; color: #be123c; padding: 2px 8px; border-radius: 4px; font-weight: 700; font-size: 0.75rem;" title="${escapeHtml(r.ErrorMessage || '')}">✕ FAILED</span>`
                    }
                  </td>
                </tr>
              `;
                  }
                )
                .join('') || `
                  <tr>
                    <td colspan="9" style="text-align: center; padding: 24px; color: #94a3b8;">
                      No scrape runs recorded yet.
                    </td>
                  </tr>
                `}
            </tbody>
          </table>
        </div>
      </div>
    `;
  } else if (currentSubTab === 'sponsors') {
    subTabContentHtml = `
      <div style="background: white; border: 1px solid #e2e8f0; border-radius: 14px; padding: 24px; box-shadow: var(--shadow-sm); max-width: 800px;">
        <div style="display: flex; align-items: flex-start; gap: 16px;">
          <div style="font-size: 2.2rem;">🛡️</div>
          <div>
            <h2 style="font-size: 1.25rem; font-weight: 800; color: #0f172a; margin: 0 0 6px 0;">UK Home Office Licensed Sponsor Register</h2>
            <p style="color: #64748b; font-size: 0.9rem; margin: 0 0 16px 0; line-height: 1.5;">
              Synchronize the official UK Government CSV Register of licensed Skilled Worker sponsors. This database powers automatic validation when job adverts do not explicitly specify visa sponsorship.
            </p>
            <div style="background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 10px; padding: 14px; margin-bottom: 20px; font-size: 0.85rem; color: #475569;">
              <div><strong>Status:</strong> Connected to official GOV.UK CSV feed</div>
              <div style="margin-top: 4px;"><strong>Target Schema:</strong> <code>job.Companies</code> & <code>job.SponsorshipEvidence</code></div>
            </div>
            <button id="admin-sync-sponsors-btn" class="btn-primary" style="padding: 10px 18px; font-size: 0.9rem;">
              <span>🛡️ Synchronize GOV.UK Sponsor Register Now</span>
            </button>
          </div>
        </div>
      </div>
    `;
  }

  container.innerHTML = `
    <div style="display: flex; flex-direction: column; gap: 20px;">
      <!-- Header -->
      <div style="display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 14px;">
        <div>
          <div style="display: flex; align-items: center; gap: 10px; flex-wrap: wrap;">
            <h1 style="font-size: 1.75rem; font-weight: 800; color: #0f172a; margin: 0;">
              ⚙️ Admin Administration & Control Center
            </h1>
            <span class="pulse-dot ${isRunning ? 'active' : 'inactive'}" title="${isRunning ? 'Scheduler is Active & Running' : 'Scheduler is Stopped'}"></span>
            <span style="background: ${isRunning ? '#ecfdf5' : '#fef2f2'}; color: ${isRunning ? '#047857' : '#dc2626'}; border: 1px solid ${isRunning ? '#a7f3d0' : '#fecaca'}; padding: 3px 8px; border-radius: 6px; font-size: 0.75rem; font-weight: 700;">
              ${isRunning ? 'SCHEDULER RUNNING' : 'SCHEDULER PAUSED'}
            </span>
          </div>
          <p style="color: #64748b; font-size: 0.92rem; margin-top: 4px; margin-bottom: 0;">
            Manage background scrapers, configure ATS feeds, inspect execution history, and sync UK Home Office sponsor records.
          </p>
        </div>
      </div>

      <!-- Admin Sub-Menu Navigation -->
      <div class="admin-subnav" id="admin-subnav-container">
        <button class="admin-subnav-btn ${currentSubTab === 'monitor' ? 'active' : ''}" data-subtab="monitor">
          <span>📡</span>
          <span>Scheduler Monitor</span>
        </button>
        <button class="admin-subnav-btn ${currentSubTab === 'sources' ? 'active' : ''}" data-subtab="sources">
          <span>🗄️</span>
          <span>Configured Job Providers & ATS Feeds</span>
          <span class="admin-subnav-badge">${state.admin.sources.length}</span>
        </button>
        <button class="admin-subnav-btn ${currentSubTab === 'history' ? 'active' : ''}" data-subtab="history">
          <span>📋</span>
          <span>Execution History Logs</span>
          <span class="admin-subnav-badge">${state.admin.runs.length}</span>
        </button>
        <button class="admin-subnav-btn ${currentSubTab === 'sponsors' ? 'active' : ''}" data-subtab="sponsors">
          <span>🛡️</span>
          <span>GOV.UK Sponsor Sync</span>
        </button>
      </div>

      <div id="admin-status-message-box"></div>

      <!-- Dynamic Sub-Tab Content -->
      <div id="admin-subtab-content">
        ${subTabContentHtml}
      </div>
    </div>
  `;

  // Subnav click handlers
  container.querySelectorAll('.admin-subnav-btn').forEach(btn => {
    btn.addEventListener('click', (e) => {
      const tab = e.currentTarget.getAttribute('data-subtab');
      state.admin.subTab = tab;
      window.history.replaceState({}, '', `/admin?tab=${tab}`);
      renderAdminView();
    });
  });

  // Switch tab buttons inside content
  container.querySelectorAll('.admin-switch-tab-btn').forEach(btn => {
    btn.addEventListener('click', (e) => {
      const targetTab = e.currentTarget.getAttribute('data-target-tab');
      state.admin.subTab = targetTab;
      window.history.replaceState({}, '', `/admin?tab=${targetTab}`);
      renderAdminView();
    });
  });

  // Specific Action Handlers based on active view
  document.getElementById('admin-subtab-trigger-btn')?.addEventListener('click', async (e) => {
    const btn = e.currentTarget;
    btn.disabled = true;
    btn.innerText = '⚡ Triggering...';
    showToast('Triggering background job refresh...', 'info');

    try {
      await api.triggerJobRefresh();
      showToast('Scheduled scraper sync triggered successfully!', 'success');
      setTimeout(() => loadAdminData(), 1500);
    } catch (err) {
      showToast('Failed to trigger scraper: ' + err.message, 'error');
    } finally {
      btn.disabled = false;
      btn.innerText = '⚡ Run Ingestion Now';
    }
  });

  document.getElementById('admin-subtab-refresh-btn')?.addEventListener('click', () => {
    loadAdminData();
    showToast('Telemetry refreshed', 'info');
  });

  document.getElementById('admin-refresh-logs-btn')?.addEventListener('click', loadAdminData);

  // AI Auto-Discovery & Custom Source Handlers
  document.getElementById('admin-trigger-discovery-btn')?.addEventListener('click', async (e) => {
    const btn = e.currentTarget;
    btn.disabled = true;
    btn.innerHTML = '<span>⏳</span><span>Scanning & Probing ATS Feeds...</span>';
    showToast('Running AI & probe discovery across UK tech employers...', 'info');

    try {
      const res = await api.autoDiscoverSources();
      const added = res.new_sources_added || 0;
      const already = res.already_tracked || 0;
      if (added > 0) {
        showToast(`🎉 Success! Auto-discovered & registered ${added} new UK tech company feeds! Ingestion triggered.`, 'success');
      } else {
        showToast(`Discovery scan finished: All ${already} discovered UK sources are already tracked and active.`, 'info');
      }
      loadAdminData();
    } catch (err) {
      showToast('Auto-discovery error: ' + err.message, 'error');
    } finally {
      btn.disabled = false;
      btn.innerHTML = '<span>✨</span><span>Auto-Discover New Sources Now</span>';
    }
  });

  document.getElementById('admin-toggle-add-form-btn')?.addEventListener('click', () => {
    const panel = document.getElementById('admin-add-custom-source-panel');
    if (panel) {
      const isVisible = panel.style.display !== 'none';
      panel.style.display = isVisible ? 'none' : 'block';
    }
  });

  document.getElementById('admin-add-source-form')?.addEventListener('submit', async (e) => {
    e.preventDefault();
    const provider = document.getElementById('custom-source-provider').value;
    const slug = document.getElementById('custom-source-slug').value.trim();
    const name = document.getElementById('custom-source-name').value.trim();
    const submitBtn = document.getElementById('custom-source-submit-btn');

    if (!slug) return;
    if (submitBtn) {
      submitBtn.disabled = true;
      submitBtn.innerText = 'Registering...';
    }

    try {
      const res = await api.addCompanySource({
        provider,
        company_slug: slug,
        company_name: name || null
      });
      showToast(res.message || `Registered ${slug} under ${provider}!`, 'success');
      document.getElementById('custom-source-slug').value = '';
      document.getElementById('custom-source-name').value = '';
      loadAdminData();
    } catch (err) {
      showToast('Registration failed: ' + err.message, 'error');
    } finally {
      if (submitBtn) {
        submitBtn.disabled = false;
        submitBtn.innerText = 'Register & Ingest';
      }
    }
  });

  document.getElementById('admin-full-refresh-btn')?.addEventListener('click', async () => {
    const btn = document.getElementById('admin-full-refresh-btn');
    if (btn) btn.disabled = true;
    showToast('Triggering full ingestion cycle across all active feeds...', 'info');

    try {
      await api.triggerJobRefresh(null);
      showToast('Ingestion completed successfully!', 'success');
      loadAdminData();
    } catch (err) {
      showToast('Run failed: ' + err.message, 'error');
    } finally {
      if (btn) btn.disabled = false;
    }
  });

  document.getElementById('admin-sync-sponsors-btn')?.addEventListener('click', async () => {
    const btn = document.getElementById('admin-sync-sponsors-btn');
    if (btn) btn.disabled = true;
    showToast('Synchronizing UK Government Sponsor Register...', 'info');

    try {
      const res = await api.updateSponsorRegister();
      showToast(res.message || 'Sponsor Register updated!', 'success');
      loadAdminData();
    } catch (err) {
      showToast('Sponsor sync error: ' + err.message, 'error');
    } finally {
      if (btn) btn.disabled = false;
    }
  });

  container.querySelectorAll('.admin-toggle-source-btn').forEach((btn) => {
    btn.addEventListener('click', async (e) => {
      const sourceId = e.currentTarget.getAttribute('data-source-id');
      const isCurrentlyEnabled = e.currentTarget.getAttribute('data-enabled') === 'true';

      try {
        await api.updateSource(sourceId, { IsEnabled: !isCurrentlyEnabled });
        showToast('Source status updated', 'success');
        loadAdminData();
      } catch (err) {
        showToast('Failed to update source: ' + err.message, 'error');
      }
    });
  });

  container.querySelectorAll('.admin-run-source-btn').forEach((btn) => {
    btn.addEventListener('click', async (e) => {
      const sourceId = e.currentTarget.getAttribute('data-source-id');
      const targetBtn = e.currentTarget;
      targetBtn.disabled = true;
      showToast(`Running ingestion for source #${sourceId}...`, 'info');

      try {
        await api.triggerJobRefresh(sourceId);
        showToast('Source ingestion finished successfully', 'success');
        loadAdminData();
      } catch (err) {
        showToast('Ingestion failed: ' + err.message, 'error');
      } finally {
        targetBtn.disabled = false;
      }
    });
  });
}

// ==========================================
// 4.5 SCHEDULER MONITOR CONTROLLER
async function loadMonitorData(isSilent = false) {
  const container = document.getElementById('monitor-view');
  if (!container) return;

  if (!isSilent && !state.monitor.data) {
    state.monitor.loading = true;
    container.innerHTML = `
      <div style="text-align: center; padding: 60px 20px; color: #64748b;">
        <div class="spinning" style="display: inline-block; font-size: 28px; margin-bottom: 12px;">📡</div>
        <p style="font-weight: 600;">Connecting to APScheduler Engine & Telemetry...</p>
      </div>
    `;
  }

  try {
    const data = await api.getMonitorStatus();
    state.monitor.data = data;
    renderMonitorView();
  } catch (err) {
    if (!isSilent) {
      container.innerHTML = `
        <div style="padding: 24px; background: #fff1f2; color: #9f1239; border-radius: 12px; border: 1px solid #fecdd3;">
          <strong>Error loading Scheduler Telemetry:</strong> ${escapeHtml(err.message)}
          <div style="margin-top: 12px;">
            <button id="monitor-retry-btn" class="btn-primary">Retry</button>
          </div>
        </div>
      `;
      document.getElementById('monitor-retry-btn')?.addEventListener('click', () => loadMonitorData());
    }
  } finally {
    state.monitor.loading = false;
    setupMonitorAutoRefresh();
  }
}

function setupMonitorAutoRefresh() {
  if (state.currentRoute !== 'monitor') {
    if (state.monitor.timerId) {
      clearInterval(state.monitor.timerId);
      state.monitor.timerId = null;
    }
    return;
  }

  if (state.monitor.autoRefresh && !state.monitor.timerId) {
    state.monitor.timerId = setInterval(() => {
      if (state.currentRoute === 'monitor') {
        loadMonitorData(true);
      }
    }, 10000);
  } else if (!state.monitor.autoRefresh && state.monitor.timerId) {
    clearInterval(state.monitor.timerId);
    state.monitor.timerId = null;
  }
}

function renderMonitorView() {
  const container = document.getElementById('monitor-view');
  if (!container) return;

  const data = state.monitor.data;
  if (!data) return;

  const isRunning = data.scheduler_running;
  const isEnabled = data.scheduler_enabled;
  const totalRuns = data.total_runs || 0;
  const successRuns = data.success_runs || 0;
  const failedRuns = data.failed_runs || 0;
  const successRate = totalRuns > 0 ? Math.round((successRuns / totalRuns) * 100) : 100;
  const totalAdded = (data.total_jobs_added || 0).toLocaleString();
  const totalUpdated = (data.total_jobs_updated || 0).toLocaleString();
  const totalDups = (data.total_duplicates_prevented || 0).toLocaleString();

  const nextRunFormatted = data.next_run_time ? new Date(data.next_run_time).toLocaleTimeString('en-GB') : 'Paused / Not scheduled';
  const lastRunFormatted = data.last_run_time ? formatRelativeTime(data.last_run_time) : 'Never';

  container.innerHTML = `
    <!-- Monitor Header -->
    <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 24px; flex-wrap: wrap; gap: 16px;">
      <div>
        <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 4px;">
          <h1 style="font-size: 1.75rem; font-weight: 800; color: #0f172a; margin: 0;">📡 Background Job Scheduler Monitor</h1>
          <span class="pulse-dot ${isRunning ? 'active' : 'inactive'}" title="${isRunning ? 'Scheduler is Active & Running' : 'Scheduler is Inactive'}"></span>
          <span style="font-size: 0.8rem; font-weight: 700; color: ${isRunning ? '#059669' : '#dc2626'}; background: ${isRunning ? '#ecfdf5' : '#fef2f2'}; padding: 3px 8px; border-radius: 9999px; border: 1px solid ${isRunning ? '#a7f3d0' : '#fecaca'};">
            ${isRunning ? 'ACTIVE • RUNNING' : 'STOPPED'}
          </span>
        </div>
        <p style="color: #64748b; font-size: 0.9rem; margin: 0;">
          Real-time diagnostics, ATS feed scrapers telemetry, duplicate deduplication metrics & execution logs.
        </p>
      </div>

      <div style="display: flex; align-items: center; gap: 12px; flex-wrap: wrap;">
        <!-- Auto refresh toggle -->
        <label style="display: flex; align-items: center; gap: 6px; font-size: 0.82rem; font-weight: 600; color: #475569; background: #f8fafc; border: 1px solid #e2e8f0; padding: 6px 12px; border-radius: 8px; cursor: pointer;">
          <input type="checkbox" id="monitor-autorefresh-toggle" ${state.monitor.autoRefresh ? 'checked' : ''} style="cursor: pointer;">
          <span>Auto-refresh (10s)</span>
        </label>

        <!-- Refresh Button -->
        <button id="monitor-manual-refresh-btn" class="btn-secondary" style="padding: 7px 14px; font-size: 0.85rem;" title="Fetch latest status">
          🔄 Refresh
        </button>

        <!-- Trigger Now Button -->
        <button id="monitor-trigger-sync-btn" class="btn-primary" style="padding: 7px 16px; font-size: 0.85rem;" title="Run all active ATS parsers right now">
          ⚡ Run Ingestion Now
        </button>
      </div>
    </div>

    <!-- Quick Stats Cards -->
    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 16px; margin-bottom: 24px;">
      <!-- Total Runs -->
      <div class="stat-card">
        <div style="display: flex; justify-content: space-between; align-items: center;">
          <span style="font-size: 0.82rem; font-weight: 700; color: #64748b; text-transform: uppercase; letter-spacing: 0.05em;">Scraping Cycles</span>
          <span style="font-size: 1.25rem;">⏱️</span>
        </div>
        <div style="font-size: 1.8rem; font-weight: 800; color: #0f172a; margin-top: 6px;">${totalRuns}</div>
        <div style="font-size: 0.8rem; color: #64748b; margin-top: 4px;">
          <span style="color: #059669; font-weight: 600;">${successRuns} success</span> • <span style="color: ${failedRuns > 0 ? '#dc2626' : '#64748b'}; font-weight: 600;">${failedRuns} errors</span>
        </div>
      </div>

      <!-- Success Rate -->
      <div class="stat-card">
        <div style="display: flex; justify-content: space-between; align-items: center;">
          <span style="font-size: 0.82rem; font-weight: 700; color: #64748b; text-transform: uppercase; letter-spacing: 0.05em;">Execution Health</span>
          <span style="font-size: 1.25rem;">🎯</span>
        </div>
        <div style="font-size: 1.8rem; font-weight: 800; color: ${successRate >= 90 ? '#059669' : '#d97706'}; margin-top: 6px;">${successRate}%</div>
        <div style="font-size: 0.8rem; color: #64748b; margin-top: 4px;">
          Cycle reliability score
        </div>
      </div>

      <!-- Jobs Added & Updated -->
      <div class="stat-card">
        <div style="display: flex; justify-content: space-between; align-items: center;">
          <span style="font-size: 0.82rem; font-weight: 700; color: #64748b; text-transform: uppercase; letter-spacing: 0.05em;">Ingested Vacancies</span>
          <span style="font-size: 1.25rem;">💼</span>
        </div>
        <div style="font-size: 1.8rem; font-weight: 800; color: #0284c7; margin-top: 6px;">${totalAdded} <span style="font-size: 0.95rem; font-weight: 600; color: #64748b;">new</span></div>
        <div style="font-size: 0.8rem; color: #64748b; margin-top: 4px;">
          ${totalUpdated} refreshed updates
        </div>
      </div>

      <!-- Duplicates Prevented -->
      <div class="stat-card">
        <div style="display: flex; justify-content: space-between; align-items: center;">
          <span style="font-size: 0.82rem; font-weight: 700; color: #64748b; text-transform: uppercase; letter-spacing: 0.05em;">Duplicate Shield</span>
          <span style="font-size: 1.25rem;">🛡️</span>
        </div>
        <div style="font-size: 1.8rem; font-weight: 800; color: #7c3aed; margin-top: 6px;">${totalDups}</div>
        <div style="font-size: 0.8rem; color: #64748b; margin-top: 4px;">
          Duplicate postings blocked
        </div>
      </div>
    </div>

    <!-- Engine Telemetry & Schedule Grid -->
    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); gap: 20px; margin-bottom: 24px;">
      <!-- Schedule Engine Details -->
      <div class="monitor-card" style="background: white; border: 1px solid #e2e8f0; border-radius: 12px; padding: 20px; box-shadow: 0 1px 3px rgba(0,0,0,0.05);">
        <h3 style="font-size: 1rem; font-weight: 700; color: #0f172a; margin-top: 0; margin-bottom: 16px; display: flex; align-items: center; gap: 8px;">
          <span>⚙️</span> Scheduler Engine Specs
        </h3>
        <div style="display: flex; flex-direction: column; gap: 12px; font-size: 0.88rem;">
          <div style="display: flex; justify-content: space-between; border-bottom: 1px solid #f1f5f9; padding-bottom: 8px;">
            <span style="color: #64748b;">Engine Mode:</span>
            <span style="font-weight: 600; color: #0f172a;">APScheduler Background (AsyncIO)</span>
          </div>
          <div style="display: flex; justify-content: space-between; border-bottom: 1px solid #f1f5f9; padding-bottom: 8px;">
            <span style="color: #64748b;">Sync Cadence:</span>
            <span style="font-weight: 700; color: #0284c7; background: #f0f9ff; padding: 2px 8px; border-radius: 6px;">Every ${data.interval_minutes} Minutes</span>
          </div>
          <div style="display: flex; justify-content: space-between; border-bottom: 1px solid #f1f5f9; padding-bottom: 8px;">
            <span style="color: #64748b;">Next Scheduled Run:</span>
            <span style="font-weight: 600; color: #059669;">⏰ ${nextRunFormatted}</span>
          </div>
          <div style="display: flex; justify-content: space-between; border-bottom: 1px solid #f1f5f9; padding-bottom: 8px;">
            <span style="color: #64748b;">Last Run Executed:</span>
            <span style="font-weight: 600; color: #334155;">${lastRunFormatted}</span>
          </div>
          <div style="display: flex; justify-content: space-between;">
            <span style="color: #64748b;">Scheduler Configuration:</span>
            <span style="font-weight: 600; color: ${isEnabled ? '#059669' : '#dc2626'};">${isEnabled ? 'ENABLE_SCHEDULER=true' : 'ENABLE_SCHEDULER=false'}</span>
          </div>
        </div>
      </div>

      <!-- Configured Feed Sources Summary -->
      <div class="monitor-card" style="background: white; border: 1px solid #e2e8f0; border-radius: 12px; padding: 20px; box-shadow: 0 1px 3px rgba(0,0,0,0.05);">
        <h3 style="font-size: 1rem; font-weight: 700; color: #0f172a; margin-top: 0; margin-bottom: 16px; display: flex; align-items: center; gap: 8px;">
          <span>🌐</span> Registered Job Sources & ATS Feeds (${data.sources ? data.sources.length : 0})
        </h3>
        <div style="display: flex; flex-direction: column; gap: 10px; max-height: 180px; overflow-y: auto; padding-right: 4px;">
          ${(data.sources || []).map(s => `
            <div style="display: flex; justify-content: space-between; align-items: center; padding: 8px 12px; background: #f8fafc; border-radius: 8px; border: 1px solid #f1f5f9;">
              <div>
                <div style="font-weight: 600; color: #1e293b; font-size: 0.88rem;">${escapeHtml(s.SourceName)}</div>
                <div style="font-size: 0.75rem; color: #64748b;">${escapeHtml(s.SourceType || 'ATS Feed')} • ${s.TotalJobsCount} jobs stored</div>
              </div>
              <div>
                <span class="badge-status ${s.IsEnabled ? 'status-success' : 'status-failed'}" style="font-size: 0.72rem; padding: 2px 8px;">
                  ${s.IsEnabled ? 'ENABLED' : 'DISABLED'}
                </span>
              </div>
            </div>
          `).join('') || '<div style="color: #94a3b8; font-size: 0.85rem;">No active sources configured.</div>'}
        </div>
      </div>
    </div>

    <!-- Execution Logs & History Table -->
    <div style="background: white; border: 1px solid #e2e8f0; border-radius: 12px; padding: 20px; box-shadow: 0 1px 3px rgba(0,0,0,0.05);">
      <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; flex-wrap: wrap; gap: 10px;">
        <div>
          <h3 style="font-size: 1.05rem; font-weight: 700; color: #0f172a; margin: 0;">📋 Recent Scheduler Execution History</h3>
          <p style="color: #64748b; font-size: 0.82rem; margin: 2px 0 0 0;">Last 30 automated scraping runs and ingest summaries</p>
        </div>
        <div style="font-size: 0.8rem; color: #64748b;">
          Showing latest ${data.recent_runs ? data.recent_runs.length : 0} runs
        </div>
      </div>

      <div style="overflow-x: auto;">
        <table class="log-table" style="width: 100%; border-collapse: collapse; font-size: 0.85rem; text-align: left;">
          <thead>
            <tr style="background: #f8fafc; border-bottom: 2px solid #e2e8f0; color: #475569;">
              <th style="padding: 10px 12px;">Run ID</th>
              <th style="padding: 10px 12px;">Feed / Source</th>
              <th style="padding: 10px 12px;">Started At</th>
              <th style="padding: 10px 12px;">Duration</th>
              <th style="padding: 10px 12px;">Found</th>
              <th style="padding: 10px 12px;">Added</th>
              <th style="padding: 10px 12px;">Updated</th>
              <th style="padding: 10px 12px;">Duplicates</th>
              <th style="padding: 10px 12px;">Status</th>
            </tr>
          </thead>
          <tbody>
            ${(data.recent_runs || []).map(r => {
              const statusClass = r.Status === 'SUCCESS' ? 'status-success' : r.Status === 'RUNNING' ? 'status-running' : 'status-failed';
              const statusIcon = r.Status === 'SUCCESS' ? '✓' : r.Status === 'RUNNING' ? '🔄' : '✕';
              const durationText = r.DurationSeconds !== null && r.DurationSeconds !== undefined ? `${r.DurationSeconds}s` : (r.Status === 'RUNNING' ? 'In progress...' : '-');
              const startedText = r.StartedAt ? new Date(r.StartedAt).toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit', second: '2-digit', day: '2-digit', month: 'short' }) : '-';

              return `
                <tr style="border-bottom: 1px solid #f1f5f9;">
                  <td style="padding: 10px 12px; font-weight: 600; color: #64748b;">#${r.ScrapeRunId}</td>
                  <td style="padding: 10px 12px; font-weight: 600; color: #1e293b;">${escapeHtml(r.SourceName || 'All Feeds')}</td>
                  <td style="padding: 10px 12px; color: #64748b;">${startedText}</td>
                  <td style="padding: 10px 12px; color: #334155; font-family: monospace;">${durationText}</td>
                  <td style="padding: 10px 12px; font-weight: 600; color: #0284c7;">${r.JobsFound || 0}</td>
                  <td style="padding: 10px 12px; font-weight: 600; color: #059669;">+${r.JobsAdded || 0}</td>
                  <td style="padding: 10px 12px; color: #475569;">${r.JobsUpdated || 0}</td>
                  <td style="padding: 10px 12px; color: #7c3aed;">${r.DuplicatesFound || 0}</td>
                  <td style="padding: 10px 12px;">
                    <span class="badge-status ${statusClass}" title="${escapeHtml(r.ErrorMessage || r.Status)}">
                      ${statusIcon} ${r.Status}
                    </span>
                  </td>
                </tr>
              `;
            }).join('') || `
              <tr>
                <td colspan="9" style="text-align: center; padding: 32px; color: #94a3b8;">
                  No scheduled runs recorded yet. Click <strong>"Run Ingestion Now"</strong> to trigger the first scrape.
                </td>
              </tr>
            `}
          </tbody>
        </table>
      </div>
    </div>
  `;

  // Attach event handlers
  document.getElementById('monitor-autorefresh-toggle')?.addEventListener('change', (e) => {
    state.monitor.autoRefresh = e.target.checked;
    setupMonitorAutoRefresh();
    showToast(state.monitor.autoRefresh ? 'Auto-refresh enabled (10s)' : 'Auto-refresh paused', 'info');
  });

  document.getElementById('monitor-manual-refresh-btn')?.addEventListener('click', () => {
    loadMonitorData();
    showToast('Telemetry refreshed', 'info');
  });

  document.getElementById('monitor-trigger-sync-btn')?.addEventListener('click', async (e) => {
    const btn = e.currentTarget;
    btn.disabled = true;
    btn.innerText = '⚡ Triggering...';
    showToast('Triggering background job refresh...', 'info');

    try {
      await api.triggerJobRefresh();
      showToast('Scheduled scraper sync triggered successfully!', 'success');
      setTimeout(() => loadMonitorData(), 1500);
    } catch (err) {
      showToast('Failed to trigger scraper: ' + err.message, 'error');
    } finally {
      btn.disabled = false;
      btn.innerText = '⚡ Run Ingestion Now';
    }
  });
}

// ==========================================
// 5. JOB DETAILS MODAL
// ==========================================
function openJobModal(job) {
  state.selectedJob = job;
  state.modalVerifyResult = null;
  state.modalEditingSponsorship = false;

  renderJobModal();

  const modalRoot = document.getElementById('job-modal-root');
  if (modalRoot) modalRoot.classList.remove('hidden');
}

function closeJobModal() {
  state.selectedJob = null;
  state.modalVerifyResult = null;
  state.modalEditingSponsorship = false;

  const modalRoot = document.getElementById('job-modal-root');
  if (modalRoot) modalRoot.classList.add('hidden');
}

function renderJobModal() {
  const modalRoot = document.getElementById('job-modal-root');
  if (!modalRoot || !state.selectedJob) return;

  const job = state.selectedJob;
  const comp = job.Company || {};
  const spons = job.Sponsorship || {};
  const applied = isJobApplied(job.JobId);

  modalRoot.innerHTML = `
    <div class="modal-overlay" id="job-modal-backdrop">
      <div class="modal-content" id="job-modal-content">
        <!-- Header -->
        <div class="modal-header">
          <div>
            <div style="display: flex; align-items: center; gap: 10px; flex-wrap: wrap;">
              ${getSponsorshipBadgeHtml(spons.SponsorshipStatus)}
              ${getMatchScoreHtml(job.MatchScore)}
              ${getExperienceBadgeHtml(job.ExperienceLevel, job.Title)}
              <span style="font-size: 0.78rem; color: #64748b; background: #f1f5f9; padding: 3px 8px; border-radius: 4px; font-weight: 600;">
                ${escapeHtml(job.RemoteType || 'UK')}
              </span>
              <span id="modal-applied-badge-slot">
                ${applied ? `<span class="badge-applied">✓ Applied</span>` : ''}
              </span>
            </div>
            <h2 style="font-size: 1.4rem; font-weight: 800; margin-top: 8px; color: #0f172a;">
              ${escapeHtml(job.Title)}
            </h2>
            <div style="display: flex; align-items: center; gap: 12px; margin-top: 4px; font-size: 0.95rem; color: #475569;">
              <span style="font-weight: 700;">${escapeHtml(comp.CompanyName || 'UK Employer')}</span>
              ${
                comp.CareersUrl
                  ? `
                <a href="${escapeHtml(comp.CareersUrl)}" target="_blank" rel="noopener noreferrer" style="color: #2563eb; display: flex; align-items: center; gap: 3px; font-size: 0.85rem;">
                  <span>Careers Page</span>
                  <span>↗</span>
                </a>
              `
                  : ''
              }
            </div>
          </div>

          <button id="job-modal-close-x-btn" style="padding: 6px; border-radius: 6px; color: #64748b; background: #f1f5f9; cursor: pointer; font-size: 1.1rem;">
            ✕
          </button>
        </div>

        <!-- Body -->
        <div class="modal-body">
          <!-- Metadata grid -->
          <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 12px; background: #f8fafc; padding: 16px; border-radius: 10px; border: 1px solid #e2e8f0;">
            <div>
              <div style="font-size: 0.75rem; color: #64748b; font-weight: 600;">Location</div>
              <div style="font-weight: 700; font-size: 0.9rem; margin-top: 2px;">${escapeHtml(job.Location || 'United Kingdom')}</div>
            </div>
            ${
              job.SalaryText
                ? `
              <div>
                <div style="font-size: 0.75rem; color: #64748b; font-weight: 600;">Salary / Compensation</div>
                <div style="font-weight: 700; font-size: 0.9rem; color: #047857; margin-top: 2px;">${escapeHtml(job.SalaryText)}</div>
              </div>
            `
                : ''
            }
            <div>
              <div style="font-size: 0.75rem; color: #64748b; font-weight: 600;">Experience Level</div>
              <div style="font-weight: 700; font-size: 0.9rem; margin-top: 2px;">${escapeHtml(job.ExperienceLevel || 'Mid')} Level</div>
            </div>
            <div>
              <div style="font-size: 0.75rem; color: #64748b; font-weight: 600;">Source Posted Date</div>
              <div style="font-weight: 700; font-size: 0.9rem; margin-top: 2px;">
                ${job.PostedDate ? new Date(job.PostedDate).toLocaleDateString('en-GB') : 'Recently'}
              </div>
            </div>
          </div>

          <!-- Application tracker button in modal -->
          <div style="background: #f0fdf4; border: 1px solid #bbf7d0; padding: 14px 18px; border-radius: 10px; display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 10px;">
            <div>
              <div style="font-weight: 700; font-size: 0.95rem; color: #15803d;">Application Status</div>
              <div style="font-size: 0.82rem; color: #166534;">Track whether you have applied to this UK job opportunity</div>
            </div>
            <button 
              id="modal-applied-toggle-btn"
              class="btn-applied-toggle ${applied ? 'applied' : ''}"
              style="padding: 8px 16px; font-size: 0.88rem;"
            >
              <span>✓</span>
              <span>${applied ? 'Applied (Click to Undo)' : 'Mark as Applied'}</span>
            </button>
          </div>

          <!-- Sponsorship Evaluation Box -->
          <div class="evidence-box">
            <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 8px;">
              <div style="display: flex; align-items: center; gap: 6px; font-weight: 800; font-size: 0.95rem; color: #1e40af;">
                <span>🛡️</span>
                <span>Skilled Worker Sponsorship Evaluation</span>
              </div>
              <button 
                id="modal-toggle-edit-spons-btn"
                style="display: flex; align-items: center; gap: 4px; font-size: 0.78rem; color: #2563eb; font-weight: 600; cursor: pointer;"
              >
                <span>✏️</span>
                <span>${state.modalEditingSponsorship ? 'Cancel Edit' : 'Admin Override'}</span>
              </button>
            </div>

            ${
              !state.modalEditingSponsorship
                ? `
              <div>
                <p style="font-size: 0.9rem; color: #1e293b; line-height: 1.5; font-weight: 500;">
                  "${escapeHtml(spons.EvidenceText || 'No specific sponsorship text extracted.')}"
                </p>
                <div style="display: flex; align-items: center; gap: 14px; margin-top: 10px; font-size: 0.8rem; color: #64748b; flex-wrap: wrap;">
                  <span>Source: <strong>${escapeHtml(spons.EvidenceSource || 'Evaluation Engine')}</strong></span>
                  <span>Confidence: <strong>${escapeHtml(spons.ConfidenceLevel || 'Medium')}</strong></span>
                  ${
                    comp.SponsorLicenceStatus === 'LICENSED'
                      ? `<span style="color: #0369a1; font-weight: 700;">✓ Employer on Home Office Register (${escapeHtml(comp.SponsorRoute || 'Skilled Worker')})</span>`
                      : ''
                  }
                </div>
              </div>
            `
                : `
              <div style="display: flex; flex-direction: column; gap: 10px; margin-top: 8px;">
                <div>
                  <label style="font-size: 0.8rem; font-weight: 700; color: #334155;">Classification:</label>
                  <select 
                    id="modal-override-status-select"
                    style="margin-left: 8px; padding: 4px 10px; border-radius: 6px; border: 1px solid #cbd5e1; font-size: 0.85rem;"
                  >
                    <option value="CONFIRMED" ${spons.SponsorshipStatus === 'CONFIRMED' ? 'selected' : ''}>CONFIRMED (Visa Sponsorship Explicitly Available)</option>
                    <option value="MAY_OFFER" ${spons.SponsorshipStatus === 'MAY_OFFER' ? 'selected' : ''}>MAY_OFFER (Company Licensed Sponsor)</option>
                    <option value="NO_SPONSORSHIP" ${spons.SponsorshipStatus === 'NO_SPONSORSHIP' ? 'selected' : ''}>NO_SPONSORSHIP (Explicitly Excluded)</option>
                    <option value="UNKNOWN" ${spons.SponsorshipStatus === 'UNKNOWN' ? 'selected' : ''}>UNKNOWN</option>
                  </select>
                </div>
                <div>
                  <label style="font-size: 0.8rem; font-weight: 700; color: #334155;">Evidence / Admin Note:</label>
                  <input 
                    type="text" 
                    id="modal-override-evidence-input"
                    value="${escapeHtml(spons.EvidenceText || '')}" 
                    style="width: 100%; margin-top: 4px; padding: 6px 10px; border-radius: 6px; border: 1px solid #cbd5e1; font-size: 0.85rem;"
                  />
                </div>
                <button 
                  id="modal-save-override-btn"
                  class="btn-primary"
                  style="align-self: flex-start; padding: 6px 14px; font-size: 0.82rem;"
                >
                  <span>Save Override</span>
                </button>
              </div>
            `
            }
          </div>

          <!-- Matched Technologies -->
          ${
            job.Skills && job.Skills.length > 0
              ? `
            <div>
              <h4 style="font-size: 0.85rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px; color: #64748b; margin-bottom: 8px;">
                Identified Technologies & Skills
              </h4>
              <div style="display: flex; flex-wrap: wrap; gap: 8px;">
                ${job.Skills.map(
                  (sk) => `
                  <span class="tech-pill ${sk.RequiredOrPreferred === 'Required' ? 'primary' : ''}" style="padding: 4px 10px; font-size: 0.8rem;">
                    ${escapeHtml(sk.SkillName)} ${sk.RequiredOrPreferred === 'Required' ? '★' : ''}
                  </span>
                `
                ).join('')}
              </div>
            </div>
          `
              : ''
          }

          <!-- Full Job Description -->
          <div>
            <h4 style="font-size: 0.85rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px; color: #64748b; margin-bottom: 8px;">
              Job Description
            </h4>
            <div style="background: #ffffff; border: 1px solid #e2e8f0; border-radius: 10px; padding: 20px; max-height: 380px; overflow-y: auto; font-size: 0.925rem; line-height: 1.6; color: #334155; white-space: pre-wrap;">
              ${escapeHtml(job.Description || 'No description text available.')}
            </div>
          </div>

          <!-- Liveness checker -->
          <div style="display: flex; align-items: center; justify-content: space-between; background: #f8fafc; padding: 10px 16px; border-radius: 8px; font-size: 0.82rem; color: #64748b; flex-wrap: wrap; gap: 8px;">
            <div>
              <span>Original ATS URL: </span>
              <a href="${escapeHtml(job.SourceJobUrl)}" target="_blank" rel="noopener noreferrer" style="color: #2563eb; text-decoration: underline;">
                ${escapeHtml((job.SourceJobUrl || '').slice(0, 50))}...
              </a>
            </div>
            <button 
              id="modal-test-liveness-btn"
              style="color: #2563eb; font-weight: 600; cursor: pointer;"
            >
              ${state.modalVerifying ? 'Checking URL...' : '⚡ Test Link Liveness'}
            </button>
          </div>

          ${
            state.modalVerifyResult
              ? `
            <div style="padding: 8px 12px; background: ${state.modalVerifyResult.still_available ? '#ecfdf5' : '#fff1f2'}; color: ${state.modalVerifyResult.still_available ? '#065f46' : '#9f1239'}; border-radius: 6px; font-size: 0.85rem; font-weight: 600;">
              Status: ${escapeHtml(state.modalVerifyResult.notes || '')} (HTTP ${state.modalVerifyResult.http_status || 'N/A'})
            </div>
          `
              : ''
          }
        </div>

        <!-- Footer -->
        <div class="modal-footer">
          <div style="font-size: 0.8rem; color: #64748b;">
            Official Direct Link. No middleman or third-party redirection.
          </div>

          <div style="display: flex; align-items: center; gap: 10px;">
            <button id="job-modal-decline-btn" class="btn-decline" data-job-id="${job.JobId}" title="Decline this job (remove from list)">
              <span>✕</span>
              <span>Decline Job</span>
            </button>
            <button id="job-modal-close-footer-btn" class="btn-secondary">
              Close
            </button>
            <a 
              href="${escapeHtml(job.ApplyUrl || job.SourceJobUrl)}" 
              target="_blank" 
              rel="noopener noreferrer" 
              class="btn-primary"
              style="padding: 10px 20px; font-size: 0.95rem; text-decoration: none;"
            >
              <span>Apply on Company Website</span>
              <span>↗</span>
            </a>
          </div>
        </div>
      </div>
    </div>
  `;

  document.getElementById('job-modal-backdrop')?.addEventListener('click', (e) => {
    if (e.target.id === 'job-modal-backdrop') closeJobModal();
  });

  document.getElementById('job-modal-close-x-btn')?.addEventListener('click', closeJobModal);
  document.getElementById('job-modal-close-footer-btn')?.addEventListener('click', closeJobModal);

  document.getElementById('job-modal-decline-btn')?.addEventListener('click', (e) => {
    declineJob(job, e);
  });

  document.getElementById('modal-applied-toggle-btn')?.addEventListener('click', () => {
    toggleJobApplied(job);
  });

  document.getElementById('modal-toggle-edit-spons-btn')?.addEventListener('click', () => {
    if (!api.isAdminLoggedIn()) {
      openAuthModal(() => {
        state.modalEditingSponsorship = true;
        renderJobModal();
      });
      return;
    }
    state.modalEditingSponsorship = !state.modalEditingSponsorship;
    renderJobModal();
  });

  document.getElementById('modal-save-override-btn')?.addEventListener('click', async () => {
    if (!api.isAdminLoggedIn()) {
      openAuthModal();
      return;
    }

    const statusSelect = document.getElementById('modal-override-status-select');
    const evidenceInput = document.getElementById('modal-override-evidence-input');
    const newStatus = statusSelect ? statusSelect.value : 'UNKNOWN';
    const newEvidence = evidenceInput ? evidenceInput.value.trim() : 'Manually adjusted by administrator.';

    try {
      const res = await api.overrideJobSponsorship(job.JobId, {
        sponsorship_status: newStatus,
        evidence_text: newEvidence,
        confidence_level: 'High',
      });

      job.MatchScore = res.new_match_score;
      if (!job.Sponsorship) job.Sponsorship = {};
      job.Sponsorship.SponsorshipStatus = res.new_status;
      job.Sponsorship.EvidenceText = newEvidence;
      job.Sponsorship.EvidenceSource = 'Manual Admin Override';

      state.modalEditingSponsorship = false;
      showToast('Sponsorship override saved successfully!', 'success');
      renderJobModal();

      if (state.currentRoute === 'jobs') renderJobsResults();
    } catch (err) {
      showToast('Failed to save override: ' + err.message, 'error');
    }
  });

  document.getElementById('modal-test-liveness-btn')?.addEventListener('click', async () => {
    state.modalVerifying = true;
    renderJobModal();

    try {
      const res = await api.verifyJobUrl(job.JobId);
      state.modalVerifyResult = res;
    } catch (err) {
      state.modalVerifyResult = {
        still_available: false,
        notes: 'Verification check failed: ' + err.message,
      };
    } finally {
      state.modalVerifying = false;
      renderJobModal();
    }
  });
}

// Global App Initialization
function init() {
  document.querySelectorAll('.nav-link').forEach((link) => {
    link.addEventListener('click', (e) => {
      e.preventDefault();
      const route = e.currentTarget.getAttribute('data-route');
      navigateTo(`/${route === 'dashboard' ? '' : route}`);
    });
  });

  document.querySelector('.nav-brand')?.addEventListener('click', () => {
    navigateTo('/');
  });

  document.getElementById('global-refresh-btn')?.addEventListener('click', async () => {
    const btn = document.getElementById('global-refresh-btn');
    const icon = btn?.querySelector('.refresh-icon');
    if (btn) btn.disabled = true;
    if (icon) icon.classList.add('spinning');
    showToast('Triggering background ATS ingestion...', 'info');

    try {
      await api.triggerJobRefresh(null);
      showToast('Ingestion completed successfully!', 'success');
      renderCurrentRoute();
    } catch (err) {
      showToast('Refresh error: ' + err.message, 'error');
    } finally {
      if (btn) btn.disabled = false;
      if (icon) icon.classList.remove('spinning');
    }
  });

  window.addEventListener('popstate', () => {
    parseUrlAndNavigate();
  });

  parseUrlAndNavigate();
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', init);
} else {
  init();
}
