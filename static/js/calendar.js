/**
 * MCET College ERP - Outlook-Style Seminar Calendar Engine (calendar.js)
 */

class MCETCalendar {
  constructor(containerId) {
    this.container = document.getElementById(containerId);
    if (!this.container) return;

    this.currentDate = new Date();
    this.currentView = 'month'; // 'month', 'week', 'day', 'agenda'
    this.events = [];

    // Filter elements
    this.deptFilter = document.getElementById('calendarDeptFilter');
    this.hallFilter = document.getElementById('calendarHallFilter');
    this.typeFilter = document.getElementById('calendarTypeFilter');
    this.searchInput = document.getElementById('calendarSearchInput');

    // UI elements
    this.titleDisplay = document.getElementById('calendarCurrentTitle');
    this.prevBtn = document.getElementById('calendarPrevBtn');
    this.nextBtn = document.getElementById('calendarNextBtn');
    this.todayBtn = document.getElementById('calendarTodayBtn');
    this.viewButtons = document.querySelectorAll('.view-mode-btn');
    this.viewContent = document.getElementById('calendarViewContent');

    this.init();
  }

  init() {
    this.bindEvents();
    this.fetchEventsAndRender();
  }

  bindEvents() {
    if (this.prevBtn) {
      this.prevBtn.addEventListener('click', () => this.navigate(-1));
    }
    if (this.nextBtn) {
      this.nextBtn.addEventListener('click', () => this.navigate(1));
    }
    if (this.todayBtn) {
      this.todayBtn.addEventListener('click', () => {
        this.currentDate = new Date();
        this.fetchEventsAndRender();
      });
    }

    this.viewButtons.forEach(btn => {
      btn.addEventListener('click', (e) => {
        this.viewButtons.forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        this.currentView = btn.dataset.view;
        this.render();
      });
    });

    [this.deptFilter, this.hallFilter, this.typeFilter].forEach(el => {
      if (el) el.addEventListener('change', () => this.fetchEventsAndRender());
    });

    if (this.searchInput) {
      let timeout;
      this.searchInput.addEventListener('input', () => {
        clearTimeout(timeout);
        timeout = setTimeout(() => this.fetchEventsAndRender(), 300);
      });
    }
  }

  navigate(direction) {
    if (this.currentView === 'month') {
      this.currentDate.setMonth(this.currentDate.getMonth() + direction);
    } else if (this.currentView === 'week') {
      this.currentDate.setDate(this.currentDate.getDate() + (direction * 7));
    } else if (this.currentView === 'day' || this.currentView === 'agenda') {
      this.currentDate.setDate(this.currentDate.getDate() + direction);
    }
    this.fetchEventsAndRender();
  }

  async fetchEventsAndRender() {
    const range = this.getDateRange();
    const params = new URLSearchParams({
      start: range.start.toISOString(),
      end: range.end.toISOString(),
      department: this.deptFilter ? this.deptFilter.value : '',
      hall: this.hallFilter ? this.hallFilter.value : '',
      event_type: this.typeFilter ? this.typeFilter.value : '',
      search: this.searchInput ? this.searchInput.value : '',
    });

    try {
      const resp = await fetch(`/bookings/api/calendar-events/?${params.toString()}`);
      this.events = await resp.json();
    } catch (err) {
      console.error('Failed to fetch calendar events:', err);
      this.events = [];
    }

    this.render();
  }

  getDateRange() {
    const d = new Date(this.currentDate);
    if (this.currentView === 'month') {
      const start = new Date(d.getFullYear(), d.getMonth(), 1);
      start.setDate(start.getDate() - start.getDay()); // Start of first week
      const end = new Date(d.getFullYear(), d.getMonth() + 1, 0);
      end.setDate(end.getDate() + (6 - end.getDay())); // End of last week
      return { start, end };
    } else if (this.currentView === 'week') {
      const start = new Date(d);
      start.setDate(d.getDate() - d.getDay());
      const end = new Date(start);
      end.setDate(start.getDate() + 6);
      return { start, end };
    } else {
      const start = new Date(d.getFullYear(), d.getMonth(), d.getDate());
      const end = new Date(d.getFullYear(), d.getMonth(), d.getDate(), 23, 59, 59);
      return { start, end };
    }
  }

  updateTitle() {
    if (!this.titleDisplay) return;
    const months = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'];
    const month = months[this.currentDate.getMonth()];
    const year = this.currentDate.getFullYear();

    if (this.currentView === 'month') {
      this.titleDisplay.textContent = `${month} ${year}`;
    } else if (this.currentView === 'week') {
      const range = this.getDateRange();
      this.titleDisplay.textContent = `${range.start.getDate()} ${months[range.start.getMonth()].substring(0,3)} – ${range.end.getDate()} ${months[range.end.getMonth()].substring(0,3)} ${year}`;
    } else if (this.currentView === 'day') {
      this.titleDisplay.textContent = `${this.currentDate.getDate()} ${month} ${year}`;
    } else {
      this.titleDisplay.textContent = `Agenda (${month} ${year})`;
    }
  }

  render() {
    this.updateTitle();
    if (!this.viewContent) return;

    if (this.currentView === 'month') {
      this.renderMonthView();
    } else if (this.currentView === 'week') {
      this.renderWeekView();
    } else if (this.currentView === 'day') {
      this.renderDayView();
    } else if (this.currentView === 'agenda') {
      this.renderAgendaView();
    }
  }

  renderMonthView() {
    const weekdays = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
    const range = this.getDateRange();
    const today = new Date();

    let html = `
      <div class="month-grid">
        ${weekdays.map(w => `<div class="month-weekday-header">${w}</div>`).join('')}
    `;

    let cur = new Date(range.start);
    while (cur <= range.end) {
      const isCurrentMonth = cur.getMonth() === this.currentDate.getMonth();
      const isToday = cur.toDateString() === today.toDateString();
      const dateStr = cur.toISOString().split('T')[0];

      // Filter events for this day
      const dayEvents = this.events.filter(e => e.start.startsWith(dateStr));

      html += `
        <div class="month-day-cell ${!isCurrentMonth ? 'other-month' : ''} ${isToday ? 'today' : ''}" data-date="${dateStr}">
          <div class="day-cell-header">
            <span class="day-number">${cur.getDate()}</span>
            ${dayEvents.length > 0 ? `<span style="font-size:10px; color:#64748B; font-weight:600;">${dayEvents.length}</span>` : ''}
          </div>
          <div class="day-events-container">
            ${dayEvents.map(e => `
              <div class="event-chip" style="background-color: ${e.backgroundColor}; border: 1px solid ${e.borderColor};" data-event-id="${e.id}" title="${e.time_display} - ${e.event_name}">
                <span>${e.time_display.split('-')[0].trim()}</span>
                <strong>${e.title}</strong>
              </div>
            `).join('')}
          </div>
        </div>
      `;

      cur.setDate(cur.getDate() + 1);
    }

    html += `</div>`;
    this.viewContent.innerHTML = html;
    this.attachEventChipListeners();
  }

  renderWeekView() {
    const range = this.getDateRange();
    const days = [];
    let cur = new Date(range.start);
    while (cur <= range.end) {
      days.push(new Date(cur));
      cur.setDate(cur.getDate() + 1);
    }

    const weekdays = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];

    let html = `
      <div class="month-grid" style="min-height: 480px;">
        ${days.map(d => `
          <div class="month-weekday-header" style="${d.toDateString() === new Date().toDateString() ? 'background:#EAF3FF; color:#123B72;' : ''}">
            ${weekdays[d.getDay()]} ${d.getDate()}/${d.getMonth()+1}
          </div>
        `).join('')}
    `;

    days.forEach(d => {
      const dateStr = d.toISOString().split('T')[0];
      const dayEvents = this.events.filter(e => e.start.startsWith(dateStr));

      html += `
        <div class="month-day-cell" style="min-height:480px;" data-date="${dateStr}">
          <div class="day-events-container" style="max-height: 460px;">
            ${dayEvents.map(e => `
              <div class="event-chip" style="background-color: ${e.backgroundColor}; padding: 6px; margin-bottom: 4px; display:block;" data-event-id="${e.id}">
                <div style="font-size:10px; opacity:0.9;">${e.time_display} | ${e.hall_code}</div>
                <div style="font-size:12px; font-weight:700;">${e.event_name}</div>
                <div style="font-size:10.5px; opacity:0.85;">${e.department} - ${e.status}</div>
              </div>
            `).join('')}
          </div>
        </div>
      `;
    });

    html += `</div>`;
    this.viewContent.innerHTML = html;
    this.attachEventChipListeners();
  }

  renderDayView() {
    const dateStr = this.currentDate.toISOString().split('T')[0];
    const dayEvents = this.events.filter(e => e.start.startsWith(dateStr));

    let html = `
      <div style="padding: 20px;">
        <div style="font-size:16px; font-weight:700; color:#123B72; margin-bottom:16px;">
          Schedule for ${this.currentDate.toDateString()} (${dayEvents.length} events)
        </div>
        ${dayEvents.length === 0 ? `
          <div style="padding:40px; text-align:center; color:#64748B; background:#F8FAFC; border-radius:8px;">
            No events or bookings scheduled for this day.
          </div>
        ` : `
          <div style="display:flex; flex-direction:column; gap:10px;">
            ${dayEvents.map(e => `
              <div class="agenda-item" data-event-id="${e.id}">
                <div>
                  <div style="display:flex; align-items:center; gap:8px;">
                    <span class="agenda-time-pill">${e.time_display}</span>
                    <span class="badge badge-secondary">${e.hall_name}</span>
                    <span class="badge badge-neutral">${e.department}</span>
                  </div>
                  <h4 style="margin: 6px 0 2px; font-size:15px; color:#123B72;">${e.event_name}</h4>
                  <p style="font-size:12px; color:#64748B;">Organizer: ${e.requested_by} | Type: ${e.event_type}</p>
                </div>
                <div>
                  <span class="badge" style="background-color:${e.backgroundColor}; color:#FFFFFF;">${e.status}</span>
                </div>
              </div>
            `).join('')}
          </div>
        `}
      </div>
    `;
    this.viewContent.innerHTML = html;
    this.attachEventChipListeners();
  }

  renderAgendaView() {
    if (this.events.length === 0) {
      this.viewContent.innerHTML = `
        <div style="padding:60px; text-align:center; color:#64748B;">
          No events found matching current criteria.
        </div>
      `;
      return;
    }

    // Group by date
    const groups = {};
    this.events.forEach(e => {
      const dateKey = e.start.split('T')[0];
      if (!groups[dateKey]) groups[dateKey] = [];
      groups[dateKey].push(e);
    });

    let html = `<div class="agenda-list">`;
    Object.keys(groups).sort().forEach(dateKey => {
      const dateObj = new Date(dateKey);
      const evs = groups[dateKey];

      html += `
        <div class="agenda-day-group">
          <div class="agenda-date-heading">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <rect x="3" y="4" width="18" height="18" rx="2" ry="2"></rect>
              <line x1="16" y1="2" x2="16" y2="6"></line>
              <line x1="8" y1="2" x2="8" y2="6"></line>
              <line x1="3" y1="10" x2="21" y2="10"></line>
            </svg>
            ${dateObj.toLocaleDateString('en-US', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' })}
          </div>
          ${evs.map(e => `
            <div class="agenda-item" data-event-id="${e.id}">
              <div>
                <div style="display:flex; align-items:center; gap:8px;">
                  <span class="agenda-time-pill">${e.time_display}</span>
                  <span class="badge badge-secondary">${e.hall_code}</span>
                  <span class="badge badge-neutral">${e.department}</span>
                </div>
                <h4 style="margin: 6px 0 2px; font-size:14px; color:#123B72;">${e.event_name}</h4>
                <p style="font-size:12px; color:#64748B;">Organizer: ${e.requested_by} | Type: ${e.event_type}</p>
              </div>
              <div>
                <span class="badge" style="background-color:${e.backgroundColor}; color:#FFFFFF;">${e.status}</span>
              </div>
            </div>
          `).join('')}
        </div>
      `;
    });
    html += `</div>`;
    this.viewContent.innerHTML = html;
    this.attachEventChipListeners();
  }

  attachEventChipListeners() {
    this.viewContent.querySelectorAll('[data-event-id]').forEach(el => {
      el.addEventListener('click', () => {
        const id = el.dataset.eventId;
        const ev = this.events.find(e => String(e.id) === String(id));
        if (ev) {
          this.showEventModal(ev);
        }
      });
    });
  }

  showEventModal(ev) {
    let modal = document.getElementById('calendarEventModal');
    if (!modal) {
      modal = document.createElement('div');
      modal.id = 'calendarEventModal';
      modal.className = 'modal-backdrop';
      document.body.appendChild(modal);
    }

    modal.innerHTML = `
      <div class="modal-content">
        <div class="modal-header">
          <h4>Event Details</h4>
          <button type="button" class="alert-close" onclick="closeModal('calendarEventModal')">&times;</button>
        </div>
        <div class="modal-body">
          <div style="display:flex; align-items:center; gap:8px; margin-bottom:12px;">
            <span class="badge" style="background-color:${ev.backgroundColor}; color:#FFFFFF;">${ev.status}</span>
            <span class="badge badge-secondary">${ev.booking_id}</span>
          </div>
          <h3 style="font-size:17px; color:#123B72; font-weight:700; margin-bottom:14px;">${ev.event_name}</h3>
          
          <div style="display:grid; grid-template-columns: 1fr 1fr; gap:12px; font-size:13px; background:#F8FAFC; padding:14px; border-radius:6px; border:1px solid #E2E8F0;">
            <div>
              <span style="color:#64748B; display:block; font-size:11px; font-weight:600;">SEMINAR HALL</span>
              <strong>${ev.hall_name} (${ev.hall_code})</strong>
            </div>
            <div>
              <span style="color:#64748B; display:block; font-size:11px; font-weight:600;">DEPARTMENT</span>
              <strong>${ev.department}</strong>
            </div>
            <div>
              <span style="color:#64748B; display:block; font-size:11px; font-weight:600;">DATE & TIME</span>
              <strong>${new Date(ev.start).toLocaleDateString()}<br>${ev.time_display}</strong>
            </div>
            <div>
              <span style="color:#64748B; display:block; font-size:11px; font-weight:600;">REQUESTED BY</span>
              <strong>${ev.requested_by}</strong>
            </div>
          </div>
        </div>
        <div class="modal-footer">
          <button type="button" class="btn btn-outline btn-sm" onclick="closeModal('calendarEventModal')">Close</button>
          <a href="${ev.detail_url}" class="btn btn-primary btn-sm">View Full Details</a>
        </div>
      </div>
    `;

    openModal('calendarEventModal');
  }
}

// Global bootstrap
document.addEventListener('DOMContentLoaded', () => {
  if (document.getElementById('mcetCalendarContainer')) {
    window.mcetCalendar = new MCETCalendar('mcetCalendarContainer');
  }
});
