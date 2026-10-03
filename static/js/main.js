/**
 * MCET College ERP – Seminar Hall Booking System
 * Core UI Script v2.0 (main.js)
 */

document.addEventListener('DOMContentLoaded', () => {
  // 1. Sidebar Toggle
  const sidebar = document.querySelector('.app-sidebar');
  const sidebarToggleBtn = document.querySelector('.sidebar-toggle-btn');
  const mobileMenuBtn = document.querySelector('.mobile-menu-btn');
  const sidebarOverlay = document.getElementById('sidebarOverlay');

  if (sidebarToggleBtn && sidebar) {
    sidebarToggleBtn.addEventListener('click', () => {
      sidebar.classList.toggle('collapsed');
      localStorage.setItem('mcet_sidebar_collapsed', sidebar.classList.contains('collapsed') ? '1' : '0');
    });

    if (localStorage.getItem('mcet_sidebar_collapsed') === '1' && window.innerWidth > 1024) {
      sidebar.classList.add('collapsed');
    }
  }

  // Mobile Drawer
  function openMobileMenu() {
    if (sidebar) sidebar.classList.add('mobile-open');
  }
  function closeMobileMenu() {
    if (sidebar) sidebar.classList.remove('mobile-open');
  }

  if (mobileMenuBtn) {
    mobileMenuBtn.addEventListener('click', (e) => {
      e.stopPropagation();
      sidebar.classList.contains('mobile-open') ? closeMobileMenu() : openMobileMenu();
    });
  }

  if (sidebarOverlay) {
    sidebarOverlay.addEventListener('click', closeMobileMenu);
  }

  // Close mobile menu on nav-item click (mobile)
  document.querySelectorAll('.nav-item').forEach(item => {
    item.addEventListener('click', () => {
      if (window.innerWidth <= 1024) closeMobileMenu();
    });
  });

  // 2. Notification Center Dropdown
  const bellBtn = document.querySelector('.bell-btn');
  const notificationsDropdown = document.querySelector('.notifications-dropdown');
  const profileTrigger = document.querySelector('.profile-trigger-btn');
  const profileDropdown = document.querySelector('.profile-dropdown-menu');

  if (bellBtn && notificationsDropdown) {
    bellBtn.addEventListener('click', (e) => {
      e.stopPropagation();
      notificationsDropdown.classList.toggle('show');
      if (profileDropdown) profileDropdown.classList.remove('show');
    });
  }

  // 3. User Profile Dropdown
  if (profileTrigger && profileDropdown) {
    profileTrigger.addEventListener('click', (e) => {
      e.stopPropagation();
      profileDropdown.classList.toggle('show');
      if (notificationsDropdown) notificationsDropdown.classList.remove('show');
    });
  }

  // Close dropdowns on outside click or ESC
  document.addEventListener('click', () => {
    if (notificationsDropdown) notificationsDropdown.classList.remove('show');
    if (profileDropdown) profileDropdown.classList.remove('show');
  });

  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
      if (notificationsDropdown) notificationsDropdown.classList.remove('show');
      if (profileDropdown) profileDropdown.classList.remove('show');
      closeAllModals();
      if (window.innerWidth <= 1024) closeMobileMenu();
    }
  });

  // 4. Auto-dismiss alerts with smooth animation
  const alerts = document.querySelectorAll('.alert');
  alerts.forEach(alert => {
    const closeBtn = alert.querySelector('.alert-close');
    if (closeBtn) {
      closeBtn.addEventListener('click', () => dismissAlert(alert));
    }
    setTimeout(() => dismissAlert(alert), 6000);
  });

  function dismissAlert(alert) {
    if (!alert || !alert.parentNode) return;
    alert.style.transition = 'opacity 0.3s ease, transform 0.3s ease';
    alert.style.opacity = '0';
    alert.style.transform = 'translateY(-4px)';
    setTimeout(() => { if (alert.parentNode) alert.remove(); }, 300);
  }

  // 5. Responsive: close sidebar on resize to desktop
  window.addEventListener('resize', () => {
    if (window.innerWidth > 1024) closeMobileMenu();
  });
});

// ========================================================
// MODAL HELPERS
// ========================================================
function openModal(modalId) {
  const modal = document.getElementById(modalId);
  if (modal) {
    modal.classList.add('show');
    document.body.style.overflow = 'hidden';
  }
}

function closeModal(modalId) {
  const modal = document.getElementById(modalId);
  if (modal) {
    modal.classList.remove('show');
    document.body.style.overflow = '';
  }
}

function closeAllModals() {
  document.querySelectorAll('.modal-backdrop').forEach(modal => {
    modal.classList.remove('show');
  });
  document.body.style.overflow = '';
}

// ========================================================
// TOAST NOTIFICATIONS
// ========================================================
function showToast(type, title, message, duration = 4000) {
  const container = document.getElementById('toastContainer');
  if (!container) return;

  const icons = {
    success: '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#16A34A" stroke-width="2"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>',
    warning: '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#F59E0B" stroke-width="2"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>',
    error: '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#DC2626" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg>',
    info: '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#3B82F6" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/></svg>'
  };

  const toast = document.createElement('div');
  toast.className = `toast toast-${type}`;
  toast.innerHTML = `
    <span class="toast-icon">${icons[type] || icons.info}</span>
    <div class="toast-body">
      <div class="toast-title">${title}</div>
      ${message ? `<div class="toast-message">${message}</div>` : ''}
    </div>
    <button type="button" class="toast-close" onclick="this.closest('.toast').remove()">&times;</button>
  `;

  container.appendChild(toast);

  setTimeout(() => {
    toast.style.transition = 'opacity 0.3s ease, transform 0.3s ease';
    toast.style.opacity = '0';
    toast.style.transform = 'translateX(20px)';
    setTimeout(() => toast.remove(), 300);
  }, duration);
}
