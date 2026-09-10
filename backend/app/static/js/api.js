// API client module for UK Software Engineering Job Finder
const API_BASE_URL = '/api';
const AUTH_TOKEN_KEY = 'uk_se_admin_token_v1';

export function getAdminToken() {
  return localStorage.getItem(AUTH_TOKEN_KEY) || null;
}

export function setAdminToken(token) {
  if (token) {
    localStorage.setItem(AUTH_TOKEN_KEY, token);
  } else {
    localStorage.removeItem(AUTH_TOKEN_KEY);
  }
}

async function request(endpoint, options = {}) {
  const url = `${API_BASE_URL}${endpoint}`;
  const token = getAdminToken();

  const headers = {
    'Content-Type': 'application/json',
    ...options.headers,
  };

  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const config = {
    ...options,
    headers,
  };

  try {
    const response = await fetch(url, config);
    if (!response.ok) {
      let errorDetail = response.statusText;
      try {
        const errorJson = await response.json();
        errorDetail = errorJson.detail || errorJson.message || JSON.stringify(errorJson);
      } catch (e) {
        // ignore fallback
      }
      throw new Error(errorDetail || `Request failed with status ${response.status}`);
    }
    return await response.json();
  } catch (error) {
    console.error(`API Error on ${url}:`, error);
    throw error;
  }
}

export const api = {
  // Authentication
  async login(username, password) {
    const data = await request('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ username, password }),
    });
    if (data.token) {
      setAdminToken(data.token);
    }
    return data;
  },

  async getMe() {
    return await request('/auth/me');
  },

  async logout() {
    try {
      await request('/auth/logout', { method: 'POST' });
    } catch (e) {
      // ignore
    } finally {
      setAdminToken(null);
    }
  },

  isAdminLoggedIn() {
    return Boolean(getAdminToken());
  },

  // Dashboard
  async getDashboardStats() {
    return await request('/dashboard/stats');
  },

  // Jobs
  async getJobs(params = {}) {
    const query = new URLSearchParams();
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined && value !== null && value !== '') {
        query.append(key, value);
      }
    });
    const qs = query.toString();
    return await request(`/jobs${qs ? `?${qs}` : ''}`);
  },

  async getJobById(id) {
    return await request(`/jobs/${id}`);
  },

  async getRecentJobs(limit = 6) {
    return await request(`/jobs/recent?limit=${limit}`);
  },

  async toggleJobApplied(jobId, isApplied = null) {
    return await request(`/jobs/${jobId}/applied`, {
      method: 'POST',
      body: JSON.stringify(isApplied !== null ? { IsApplied: isApplied } : {}),
    });
  },

  // Companies
  async getCompanies(params = {}) {
    const query = new URLSearchParams();
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined && value !== null && value !== '') {
        query.append(key, value);
      }
    });
    const qs = query.toString();
    return await request(`/companies${qs ? `?${qs}` : ''}`);
  },

  async getCompanyById(id) {
    return await request(`/companies/${id}`);
  },

  // Sponsorship lookup
  async lookupSponsor(companyName) {
    const query = new URLSearchParams({ company: companyName });
    return await request(`/sponsorship/lookup?${query.toString()}`);
  },

  // Admin & Sources
  async getSources() {
    return await request('/sources');
  },

  async getScrapeRuns(limit = 25) {
    return await request(`/sources/runs?limit=${limit}`);
  },

  async triggerJobRefresh(sourceId = null) {
    const qs = sourceId ? `?source_id=${sourceId}` : '';
    return await request(`/admin/refresh${qs}`, { method: 'POST' });
  },

  async updateSource(sourceId, payload) {
    return await request(`/admin/sources/${sourceId}`, {
      method: 'PATCH',
      body: JSON.stringify(payload),
    });
  },

  async overrideJobSponsorship(jobId, payload) {
    return await request(`/admin/jobs/${jobId}/sponsorship`, {
      method: 'PATCH',
      body: JSON.stringify(payload),
    });
  },

  async verifyJobUrl(jobId) {
    return await request(`/admin/jobs/${jobId}/verify`, { method: 'POST' });
  },

  async closeJob(jobId) {
    return await request(`/admin/jobs/${jobId}/close`, { method: 'PATCH' });
  },

  async updateSponsorRegister() {
    return await request('/admin/sponsor-register/update', { method: 'POST' });
  }
};
