/**
 * MCET College ERP - Seminar Hall Booking System
 * Core UI Script (main.js)
 */

document.addEventListener('DOMContentLoaded', () => {
  // 1. Sidebar Toggle
  const sidebar = document.querySelector('.app-sidebar');
  const sidebarToggleBtn = document.querySelector('.sidebar-toggle-btn');
  const mobileMenuBtn = document.querySelector('.mobile-menu-btn');

  if (sidebarToggleBtn && sidebar) {
    sidebarToggleBtn.addEventListener('click', () => {
      sidebar.classList.toggle('collapsed');
      localStorage.setItem('mcet_sidebar_collapsed', sidebar.classList.contains('collapsed') ? '1' : '0');
    });

    // Restore state from localStorage
    if (localStorage.getItem('mcet_sidebar_collapsed') === '1' && window.innerWidth > 1024) {
      sidebar.classList.add('collapsed');
    }
  }

  // Mobile Drawer Toggle
  if (mobileMenuBtn && sidebar) {
    mobileMenuBtn.addEventListener('click', (e) => {
      e.stopPropagation();
      sidebar.classList.toggle('mobile-open');
    });

    document.addEventListener('click', (e) => {
      if (window.innerWidth <= 1024 && !sidebar.contains(e.target) && !mobileMenuBtn.contains(e.target)) {
        sidebar.classList.remove('mobile-open');
      }
    });
  }

  // 2. Notification Center Dropdown
  const bellBtn = document.querySelector('.bell-btn');
  const notificationsDropdown = document.querySelector('.notifications-dropdown');

  if (bellBtn && notificationsDropdown) {
    bellBtn.addEventListener('click', (e) => {
      e.stopPropagation();
      notificationsDropdown.classList.toggle('show');
      if (profileDropdown) profileDropdown.classList.remove('show');
    });
  }

  // 3. User Profile Dropdown
  const profileTrigger = document.querySelector('.profile-trigger-btn');
  const profileDropdown = document.querySelector('.profile-dropdown-menu');

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
    }
  });

  // 4. Auto-dismiss alerts
  const alerts = document.querySelectorAll('.alert');
  alerts.forEach(alert => {
    const closeBtn = alert.querySelector('.alert-close');
    if (closeBtn) {
      closeBtn.addEventListener('click', () => alert.remove());
    }
    setTimeout(() => {
      alert.style.transition = 'opacity 0.4s ease';
      alert.style.opacity = '0';
      setTimeout(() => alert.remove(), 400);
    }, 6000);
  });
});

// Modal Helpers
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
