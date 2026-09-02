/**
 * Authentication & Route Protection Guard
 */
const Auth = {
  checkAuth() {
    const token = localStorage.getItem('auth_token') || sessionStorage.getItem('auth_token');
    const pathname = window.location.pathname;
    const isAuthPage = pathname.includes('login.html') || pathname.includes('register.html');
    const isIndex = pathname.endsWith('index.html') || pathname === '/' || pathname.endsWith('/');

    if (isIndex) {
      if (token) {
        window.location.replace('dashboard.html');
      } else {
        window.location.replace('login.html');
      }
      return;
    }

    if (!token && !isAuthPage) {
      window.location.replace('login.html');
      return;
    }

    if (token && isAuthPage) {
      window.location.replace('dashboard.html');
      return;
    }
  },

  async login(email, password, rememberMe = false) {
    try {
      const data = await API.post('/auth/login', { email, password });
      
      if (rememberMe) {
        localStorage.setItem('auth_token', data.access_token);
      } else {
        sessionStorage.setItem('auth_token', data.access_token);
      }

      localStorage.setItem('user_info', JSON.stringify(data.user || { email, full_name: 'Dr. Sarah Green' }));
      if (data.settings) {
        localStorage.setItem('user_settings', JSON.stringify(data.settings));
      }

      UI.showToast('Login successful! Redirecting...', 'success');
      setTimeout(() => {
        window.location.replace('dashboard.html');
      }, 400);
    } catch (err) {
      UI.showToast(err.message || 'Login failed', 'error', 'Authentication Error');
      throw err;
    }
  },

  async register(fullName, email, password, confirmPassword) {
    if (password !== confirmPassword) {
      UI.showToast('Passwords do not match.', 'error', 'Validation Error');
      return;
    }

    try {
      const data = await API.post('/auth/register', {
        full_name: fullName,
        email: email,
        password: password
      });

      localStorage.setItem('auth_token', data.access_token);
      localStorage.setItem('user_info', JSON.stringify(data.user || { email, full_name: fullName }));
      if (data.settings) {
        localStorage.setItem('user_settings', JSON.stringify(data.settings));
      }

      UI.showToast('Account created successfully! Redirecting...', 'success');
      setTimeout(() => {
        window.location.replace('dashboard.html');
      }, 500);
    } catch (err) {
      UI.showToast(err.message || 'Registration failed', 'error', 'Registration Error');
      throw err;
    }
  },

  async logout() {
    try {
      if (!CONFIG.DEMO_MODE) {
        await API.post('/auth/logout', {});
      }
    } catch (e) {
      // Continue cleanup
    } finally {
      localStorage.removeItem('auth_token');
      sessionStorage.removeItem('auth_token');
      localStorage.removeItem('user_info');
      UI.showToast('Logged out successfully', 'info');
      setTimeout(() => {
        window.location.replace('login.html');
      }, 300);
    }
  },

  togglePasswordVisibility(inputId, btnElem) {
    const input = document.getElementById(inputId);
    if (!input) return;
    if (input.type === 'password') {
      input.type = 'text';
      btnElem.innerHTML = `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"></path><line x1="1" y1="1" x2="23" y2="23"></line></svg>`;
    } else {
      input.type = 'password';
      btnElem.innerHTML = `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"></path><circle cx="12" cy="12" r="3"></circle></svg>`;
    }
  }
};

if (typeof window !== 'undefined') {
  window.Auth = Auth;
}

// Check authorization guard on page load
Auth.checkAuth();
