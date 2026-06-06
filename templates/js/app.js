/* ══════════════════════════════════════════════════
   VendorBridge – Shared Application JavaScript
   ══════════════════════════════════════════════════ */

document.addEventListener('DOMContentLoaded', () => {
  initTheme();
  initSidebar();
  initProfileDropdown();
  initNotifications();
  initMobileNav();
  highlightActiveNav();
  initAnimations();

  if (localStorage.getItem('vb-token')) {
      populateUserInfo();
  }
});

/* ── DARK / LIGHT MODE ─────────────────────────── */
function initTheme() {
  const saved = localStorage.getItem('vb-theme') || 'dark';
  document.documentElement.setAttribute('data-theme', saved);
  updateThemeIcon(saved);
}

function toggleTheme() {
  const current = document.documentElement.getAttribute('data-theme');
  const next = current === 'dark' ? 'light' : 'dark';
  document.documentElement.setAttribute('data-theme', next);
  localStorage.setItem('vb-theme', next);
  updateThemeIcon(next);
}

function updateThemeIcon(theme) {
  const btn = document.getElementById('themeToggle');
  if (!btn) return;
  const icon = btn.querySelector('i');
  if (theme === 'dark') {
    icon.className = 'fas fa-sun';
  } else {
    icon.className = 'fas fa-moon';
  }
}

/* ── SIDEBAR ───────────────────────────────────── */
function initSidebar() {
  const toggle = document.getElementById('sidebarToggle');
  const sidebar = document.getElementById('sidebar');
  if (!toggle || !sidebar) return;

  // restore saved state on desktop
  const collapsed = localStorage.getItem('vb-sidebar-collapsed') === 'true';
  if (collapsed && window.innerWidth > 768) {
    sidebar.classList.add('collapsed');
  }

  toggle.addEventListener('click', () => {
    if (window.innerWidth <= 768) {
      sidebar.classList.toggle('mobile-open');
      document.getElementById('mobileOverlay')?.classList.toggle('show');
    } else {
      sidebar.classList.toggle('collapsed');
      localStorage.setItem('vb-sidebar-collapsed', sidebar.classList.contains('collapsed'));
    }
  });
}

function initMobileNav() {
  const overlay = document.getElementById('mobileOverlay');
  if (overlay) {
    overlay.addEventListener('click', () => {
      document.getElementById('sidebar')?.classList.remove('mobile-open');
      overlay.classList.remove('show');
    });
  }
}

/* ── HIGHLIGHT ACTIVE NAV ──────────────────────── */
function highlightActiveNav() {
  const current = window.location.pathname.split('/').pop() || 'index.html';
  document.querySelectorAll('.nav-item').forEach(item => {
    const href = item.getAttribute('href');
    if (href && (href === current || (current === 'index.html' && href === 'dashboard.html'))) {
      item.classList.add('active');
    } else {
      item.classList.remove('active');
    }
  });
}

/* ── PROFILE DROPDOWN ──────────────────────────── */
function initProfileDropdown() {
  const avatarBtn = document.getElementById('profileAvatarBtn');
  const dropdown = document.getElementById('profileDropdown');
  if (!avatarBtn || !dropdown) return;

  avatarBtn.addEventListener('click', (e) => {
    e.stopPropagation();
    dropdown.classList.toggle('open');
    // close notif panel
    document.getElementById('notifPanel')?.classList.remove('open');
  });

  document.addEventListener('click', (e) => {
    if (!dropdown.contains(e.target)) {
      dropdown.classList.remove('open');
    }
  });
}

/* ── NOTIFICATIONS ─────────────────────────────── */
function initNotifications() {
  const btn = document.getElementById('notifBtn');
  const panel = document.getElementById('notifPanel');
  if (!btn || !panel) return;

  btn.addEventListener('click', (e) => {
    e.stopPropagation();
    panel.classList.toggle('open');
    // close profile dropdown
    document.getElementById('profileDropdown')?.classList.remove('open');
  });

  document.addEventListener('click', (e) => {
    if (!panel.contains(e.target)) {
      panel.classList.remove('open');
    }
  });

  const clearBtn = panel.querySelector('.notif-panel-clear');
  if (clearBtn) {
    clearBtn.addEventListener('click', () => {
      panel.querySelectorAll('.notif-item').forEach(item => {
        item.style.opacity = '0';
        item.style.transform = 'translateX(20px)';
        setTimeout(() => item.remove(), 300);
      });
      const dot = document.querySelector('.notif-dot');
      if (dot) dot.style.display = 'none';
    });
  }
}

/* ── TOGGLE SWITCHES ───────────────────────────── */
// Toggle switches use inline onclick handlers in the HTML

/* ── STAGGERED ANIMATIONS ──────────────────────── */
function initAnimations() {
  const cards = document.querySelectorAll('.metric-card, .vb-card');
  cards.forEach((card, i) => {
    card.style.animationDelay = `${i * 0.06}s`;
  });
}

/* ── POPULATE USER INFO ────────────────────────── */
async function populateUserInfo() {
  try {
      const user = await apiFetch('/auth/me');
      if (!user) return;
      
      const nameParts = user.name ? user.name.split(' ') : [];
      const firstInitial = nameParts[0] ? nameParts[0].charAt(0).toUpperCase() : '';
      const lastInitial = nameParts.length > 1 ? nameParts[nameParts.length - 1].charAt(0).toUpperCase() : '';
      const initials = (firstInitial + lastInitial) || 'U';
      const fullName = user.name || 'User';

      // Topbar
      const topAvatar = document.getElementById('profileAvatarBtn');
      if (topAvatar) topAvatar.textContent = initials;
      
      const dropName = document.querySelector('.profile-dropdown-name');
      if (dropName) dropName.textContent = fullName;
      const dropEmail = document.querySelector('.profile-dropdown-email');
      if (dropEmail) dropEmail.textContent = user.email;

      // Sidebar
      const sideAvatar = document.querySelector('.sidebar-avatar');
      if (sideAvatar) sideAvatar.textContent = initials;
      
      const sideName = document.querySelector('.sidebar-user-info');
      if (sideName) sideName.textContent = fullName;
      const sideRole = document.querySelector('.sidebar-user-role');
      if (sideRole) sideRole.textContent = user.role || 'User';

      // Role-Based UI Handling
      // Add 'admin-only' class to elements that vendors shouldn't see
      // Add 'vendor-only' class to elements that only vendors should see
      if (user.role === 'vendor') {
          document.querySelectorAll('.admin-only').forEach(el => el.style.display = 'none');
          // Hide specific sidebar links for vendors
          document.querySelectorAll('.nav-item').forEach(nav => {
              const text = nav.textContent.trim();
              if (['Vendors', 'Approvals', 'Comparison', 'Reports'].includes(text)) {
                  nav.style.display = 'none';
              }
          });
          // Hide "Create RFQ" button explicitly
          const createRfqBtn = document.querySelector('a[href="rfqs.html"].btn-primary-vb');
          if (createRfqBtn && createRfqBtn.textContent.includes('New RFQ')) createRfqBtn.style.display = 'none';
      } else {
          document.querySelectorAll('.vendor-only').forEach(el => el.style.display = 'none');
      }

      // Fetch pending approvals count (only if not a vendor)
      if (user.role !== 'vendor') {
          try {
              const appRes = await apiFetch('/approvals/count');
              const count = appRes.count || 0;
              document.querySelectorAll('.nav-badge').forEach(badge => {
                  if (count > 0) {
                      badge.textContent = count;
                      badge.style.display = 'inline-block';
                  } else {
                      badge.style.display = 'none';
                  }
              });
          } catch (err) {
              console.error("Failed to load approvals count:", err);
          }
      } else {
          // Hide badges for vendors
          document.querySelectorAll('.nav-badge').forEach(b => b.style.display = 'none');
      }

  } catch(err) {
      console.error("Failed to load user info for UI:", err);
  }
}

/* ── TOAST HELPER ──────────────────────────────── */
function showToast(message, type = 'success') {
  let toast = document.getElementById('vbToast');
  if (!toast) {
    toast = document.createElement('div');
    toast.id = 'vbToast';
    document.body.appendChild(toast);
  }
  toast.className = `toast-vb toast-${type}`;
  const icons = { success: 'fa-circle-check', error: 'fa-circle-xmark', info: 'fa-circle-info' };
  toast.innerHTML = `<i class="fas ${icons[type] || icons.success}"></i> ${message}`;

  requestAnimationFrame(() => {
    toast.classList.add('show');
  });

  setTimeout(() => {
    toast.classList.remove('show');
  }, 3000);
}

/* ── PASSWORD STRENGTH CHECKER ─────────────────── */
function checkPasswordStrength(value, segIds, labelId) {
  const segs = segIds.map(id => document.getElementById(id));
  const label = document.getElementById(labelId);
  if (!label) return;

  let score = 0;
  if (value.length >= 8)          score++;
  if (/[A-Z]/.test(value))        score++;
  if (/[0-9]/.test(value))        score++;
  if (/[^A-Za-z0-9]/.test(value)) score++;

  const colors = ['', '#E05C5C', '#F5A623', '#2ABFBF', '#2ecc71'];
  const labels = ['Enter a password', 'Weak', 'Fair', 'Good', 'Strong'];

  segs.forEach((s, i) => {
    if (s) s.style.background = i < score ? colors[score] : 'rgba(107,139,164,.2)';
  });
  label.textContent = labels[score];
  label.style.color = colors[score] || 'var(--muted)';
}

/* ── SEARCH FILTER ─────────────────────────────── */
function filterTable(inputEl, tableId) {
  const query = inputEl.value.toLowerCase();
  const rows = document.querySelectorAll(`#${tableId} tbody tr`);
  rows.forEach(row => {
    const text = row.textContent.toLowerCase();
    row.style.display = text.includes(query) ? '' : 'none';
  });
}

/* ── FILTER PILLS ──────────────────────────────── */
function setFilterPill(pill) {
  pill.parentElement.querySelectorAll('.filter-pill').forEach(p => p.classList.remove('active'));
  pill.classList.add('active');
}

/* ── ROLE CARD SELECTION ───────────────────────── */
function selectRoleCard(card) {
  card.closest('.role-grid').querySelectorAll('.role-card').forEach(c => c.classList.remove('selected'));
  card.classList.add('selected');
  const radio = card.querySelector('input[type=radio]');
  if (radio) radio.checked = true;
}
