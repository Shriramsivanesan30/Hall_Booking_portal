/**
 * MCET College ERP – Interactive Seminar Hall Booking Wizard
 * Simple, direct time range selection (e.g. 09:00 AM – 12:30 PM),
 * with visual daily availability schedule ribbon, academic session presets,
 * real-time conflict checking, and alternative hall switching.
 */

document.addEventListener('DOMContentLoaded', () => {
  let currentStep = 2; // Default to Step 2
  let currentDate = new Date('2026-10-15T00:00:00');
  let selectedDate = new Date('2026-10-15T00:00:00');

  // Active time range (defaults to user's 09:00 AM to 12:30 PM example)
  let rangeStart = '09:00';
  let rangeEnd = '12:30';

  // DOM Elements
  const stepNodes = document.querySelectorAll('.wizard-step-node');
  const stepPanes = document.querySelectorAll('.wizard-step-pane');
  const dateTrack = document.getElementById('dateCarouselTrack');
  const prevDayBtn = document.getElementById('prevDayBtn');
  const nextDayBtn = document.getElementById('nextDayBtn');
  const jumpDatePicker = document.getElementById('jumpDatePicker');

  // Hidden Inputs
  const eventDateInput = document.getElementById('eventDateInput');
  const preferredHallInput = document.getElementById('preferredHallInput');
  const startTimeInput = document.getElementById('startTimeInput');
  const endTimeInput = document.getElementById('endTimeInput');
  const actionTypeInput = document.getElementById('actionTypeInput');
  const bookingForm = document.getElementById('bookingMasterForm');

  // Time Range Controls
  const rangeStartTimeSelect = document.getElementById('rangeStartTime');
  const rangeEndTimeSelect = document.getElementById('rangeEndTime');
  const calculatedDurationBadge = document.getElementById('calculatedDurationBadge');
  const sessionPresetBtns = document.querySelectorAll('.session-preset-btn');

  // Timeline Ribbon Elements
  const userSelectedTimelineBlock = document.getElementById('userSelectedTimelineBlock');
  const timelineUserRangeLabel = document.getElementById('timelineUserRangeLabel');
  const bookedTimelineBlock = document.getElementById('bookedTimelineBlock');
  const timelineStatusBadge = document.getElementById('timelineStatusBadge');

  // Sticky Bar Elements
  const stickyHallVal = document.getElementById('stickyHallVal');
  const stickyDateVal = document.getElementById('stickyDateVal');
  const stickyTimeVal = document.getElementById('stickyTimeVal');
  const stickyCapacityVal = document.getElementById('stickyCapacityVal');
  const stickyBackBtn = document.getElementById('stickyBackBtn');
  const stickyContinueBtn = document.getElementById('stickyContinueBtn');

  // View Switchers
  const btnCardView = document.getElementById('btnCardView');
  const btnListView = document.getElementById('btnListView');
  const hallCardsGrid = document.getElementById('hallCardsGrid');

  // Conflict & Alternatives
  const conflictBanner = document.getElementById('conflictAlertBanner');
  const suggestedAlternatives = document.getElementById('suggestedAlternativesCard');
  const selectedHallSlotTitle = document.getElementById('selectedHallSlotTitle');
  const conflictAlertTitle = document.getElementById('conflictAlertTitle');
  const conflictAlertDesc = document.getElementById('conflictAlertDesc');

  // ----------------------------------------------------
  // TIME UTILITIES
  // ----------------------------------------------------
  function parseTimeToMinutes(t) {
    if (!t) return 0;
    const parts = t.split(':');
    return parseInt(parts[0], 10) * 60 + parseInt(parts[1], 10);
  }

  function formatMinutesTo12h(mins) {
    let h = Math.floor(mins / 60);
    const m = mins % 60;
    const ampm = h >= 12 ? 'PM' : 'AM';
    h = h % 12;
    if (h === 0) h = 12;
    const hStr = String(h).padStart(2, '0');
    const mStr = String(m).padStart(2, '0');
    return `${hStr}:${mStr} ${ampm}`;
  }

  function formatDuration(startMins, endMins) {
    const diff = Math.max(0, endMins - startMins);
    const h = Math.floor(diff / 60);
    const m = diff % 60;
    const decimalHours = (diff / 60).toFixed(1).replace('.0', '');

    if (m === 0) {
      return `${h} Hour${h !== 1 ? 's' : ''}`;
    }
    return `${h}h ${m}m (${decimalHours} Hours)`;
  }

  // ----------------------------------------------------
  // 1. STEP NAVIGATION
  // ----------------------------------------------------
  function goToStep(step) {
    if (step < 1 || step > 5) return;
    currentStep = step;

    // Update Stepper Nodes
    stepNodes.forEach((node) => {
      const s = parseInt(node.getAttribute('data-step'), 10);
      node.classList.remove('active', 'completed');
      if (s === currentStep) {
        node.classList.add('active');
      } else if (s < currentStep) {
        node.classList.add('completed');
      }
    });

    // Toggle Step Panes
    stepPanes.forEach((pane) => {
      pane.style.display = 'none';
    });
    const activePane = document.getElementById(`stepPane${currentStep}`);
    if (activePane) activePane.style.display = 'block';

    // Update Sticky Bar Buttons
    if (stickyContinueBtn) {
      if (currentStep === 1) {
        stickyContinueBtn.textContent = 'Continue to Hall & Time Slot →';
      } else if (currentStep === 2) {
        stickyContinueBtn.textContent = 'Continue to Facilities →';
      } else if (currentStep === 3) {
        stickyContinueBtn.textContent = 'Continue to Additional Info →';
      } else if (currentStep === 4) {
        stickyContinueBtn.textContent = 'Review & Submit →';
      } else if (currentStep === 5) {
        stickyContinueBtn.textContent = 'Submit for Approval';
      }
    }

    // Populate Review Summary Pane
    if (currentStep === 5) {
      const eventName = document.getElementById('eventName')?.value || 'Technology Seminar';
      const deptSelect = document.getElementById('deptSelect');
      const deptName = deptSelect ? deptSelect.options[deptSelect.selectedIndex]?.text : '';
      const participants = document.getElementById('expectedParticipants')?.value || '200';

      const revEvent = document.getElementById('reviewEventName');
      const revHall = document.getElementById('reviewHallName');
      const revDate = document.getElementById('reviewDate');
      const revTime = document.getElementById('reviewTime');
      const revDept = document.getElementById('reviewDept');
      const revPart = document.getElementById('reviewParticipants');

      if (revEvent) revEvent.textContent = eventName;
      if (revHall) revHall.textContent = stickyHallVal?.textContent || 'Seminar Hall – 1';
      if (revDate) revDate.textContent = stickyDateVal?.textContent || '15 Oct 2026';
      if (revTime) revTime.textContent = stickyTimeVal?.textContent || '09:00 AM – 12:30 PM (3.5 Hours)';
      if (revDept) revDept.textContent = deptName;
      if (revPart) revPart.textContent = `${participants} Attendees`;
    }

    window.scrollTo({ top: 0, behavior: 'smooth' });
  }

  stepNodes.forEach((node) => {
    node.addEventListener('click', () => {
      const s = parseInt(node.getAttribute('data-step'), 10);
      goToStep(s);
    });
  });

  // Pane action buttons
  document.getElementById('btnNextToStep2')?.addEventListener('click', () => goToStep(2));
  document.getElementById('btnBackToStep1')?.addEventListener('click', () => goToStep(1));
  document.getElementById('btnNextToStep3')?.addEventListener('click', () => goToStep(3));
  document.getElementById('btnBackToStep2')?.addEventListener('click', () => goToStep(2));
  document.getElementById('btnNextToStep4')?.addEventListener('click', () => goToStep(4));
  document.getElementById('btnBackToStep3')?.addEventListener('click', () => goToStep(3));
  document.getElementById('btnNextToStep5')?.addEventListener('click', () => goToStep(5));
  document.getElementById('btnBackToStep4')?.addEventListener('click', () => goToStep(4));

  // Sticky Bar Navigation
  stickyBackBtn?.addEventListener('click', () => {
    if (currentStep > 1) {
      goToStep(currentStep - 1);
    } else {
      window.history.back();
    }
  });

  stickyContinueBtn?.addEventListener('click', () => {
    if (currentStep < 5) {
      goToStep(currentStep + 1);
    } else {
      actionTypeInput.value = 'SUBMIT';
      bookingForm.submit();
    }
  });

  document.getElementById('saveDraftActionBtn')?.addEventListener('click', () => {
    actionTypeInput.value = 'DRAFT';
    bookingForm.submit();
  });

  document.getElementById('finalSubmitActionBtn')?.addEventListener('click', () => {
    actionTypeInput.value = 'SUBMIT';
    bookingForm.submit();
  });

  // ----------------------------------------------------
  // 2. DATE CAROUSEL
  // ----------------------------------------------------
  const monthNames = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
  const dayNames = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];

  function formatDateIso(d) {
    const y = d.getFullYear();
    const m = String(d.getMonth() + 1).padStart(2, '0');
    const day = String(d.getDate()).padStart(2, '0');
    return `${y}-${m}-${day}`;
  }

  function renderDateCarousel() {
    if (!dateTrack) return;
    dateTrack.innerHTML = '';

    // Generate 7 days around currentDate
    for (let i = -1; i <= 5; i++) {
      const d = new Date(currentDate);
      d.setDate(currentDate.getDate() + i);

      const dayStr = dayNames[d.getDay()];
      const dateStr = `${d.getDate()} ${monthNames[d.getMonth()]}`;
      const fullDateStr = `${dateStr} ${d.getFullYear()}`;
      const isSelected = formatDateIso(d) === formatDateIso(selectedDate);

      const pill = document.createElement('div');
      pill.className = `date-pill-btn ${isSelected ? 'active' : ''}`;
      pill.setAttribute('data-date', formatDateIso(d));
      pill.innerHTML = `
        <span class="date-pill-day">${dayStr}</span>
        <span class="date-pill-date">${isSelected ? fullDateStr : dateStr}</span>
      `;

      pill.addEventListener('click', () => {
        selectedDate = new Date(d);
        if (eventDateInput) eventDateInput.value = formatDateIso(selectedDate);
        if (stickyDateVal) {
          stickyDateVal.textContent = `${selectedDate.getDate()} ${monthNames[selectedDate.getMonth()]} ${selectedDate.getFullYear()}`;
        }
        renderDateCarousel();
        updateTimeSlotVisuals();
      });

      dateTrack.appendChild(pill);
    }
  }

  prevDayBtn?.addEventListener('click', () => {
    currentDate.setDate(currentDate.getDate() - 1);
    renderDateCarousel();
  });

  nextDayBtn?.addEventListener('click', () => {
    currentDate.setDate(currentDate.getDate() + 1);
    renderDateCarousel();
  });

  jumpDatePicker?.addEventListener('change', (e) => {
    if (e.target.value) {
      selectedDate = new Date(e.target.value + 'T00:00:00');
      currentDate = new Date(selectedDate);
      if (eventDateInput) eventDateInput.value = formatDateIso(selectedDate);
      if (stickyDateVal) {
        stickyDateVal.textContent = `${selectedDate.getDate()} ${monthNames[selectedDate.getMonth()]} ${selectedDate.getFullYear()}`;
      }
      renderDateCarousel();
      updateTimeSlotVisuals();
    }
  });

  // ----------------------------------------------------
  // 3. SEMINAR HALL SELECTION
  // ----------------------------------------------------
  const hallCards = document.querySelectorAll('.hall-visual-card');

  hallCards.forEach((card) => {
    card.addEventListener('click', () => {
      hallCards.forEach((c) => c.classList.remove('selected'));
      card.classList.add('selected');

      const hallId = card.getAttribute('data-hall-id');
      const hallName = card.getAttribute('data-hall-name');
      const capacity = card.getAttribute('data-capacity');

      if (preferredHallInput) preferredHallInput.value = hallId;
      if (stickyHallVal) stickyHallVal.textContent = hallName;
      if (stickyCapacityVal) stickyCapacityVal.textContent = capacity;
      if (selectedHallSlotTitle) {
        selectedHallSlotTitle.textContent = `Select Time Slot – ${hallName}`;
      }

      updateTimeSlotVisuals();
    });
  });

  // Card View / List View Toggle
  btnCardView?.addEventListener('click', () => {
    btnCardView.classList.add('active');
    btnListView?.classList.remove('active');
    hallCardsGrid?.classList.remove('list-view');
  });

  btnListView?.addEventListener('click', () => {
    btnListView.classList.add('active');
    btnCardView?.classList.remove('active');
    hallCardsGrid?.classList.add('list-view');
  });

  // ----------------------------------------------------
  // 4. DIRECT TIME RANGE & VISUAL TIMELINE RIBBON
  // ----------------------------------------------------
  function applyTimeRange(start, end) {
    rangeStart = start;
    rangeEnd = end;

    if (rangeStartTimeSelect) rangeStartTimeSelect.value = start;
    if (rangeEndTimeSelect) rangeEndTimeSelect.value = end;
    if (startTimeInput) startTimeInput.value = start;
    if (endTimeInput) endTimeInput.value = end;

    // Highlight matching preset button if any
    sessionPresetBtns.forEach((btn) => {
      const bStart = btn.getAttribute('data-start');
      const bEnd = btn.getAttribute('data-end');
      if (bStart === start && bEnd === end) {
        btn.classList.add('active');
      } else {
        btn.classList.remove('active');
      }
    });

    updateTimeSlotVisuals();
  }

  function updateTimeSlotVisuals() {
    const startMins = parseTimeToMinutes(rangeStart);
    const endMins = parseTimeToMinutes(rangeEnd);

    // Validate that End > Start
    if (endMins <= startMins) {
      if (calculatedDurationBadge) {
        calculatedDurationBadge.textContent = '⚠️ End must be after Start';
      }
      return;
    }

    const durationText = formatDuration(startMins, endMins);
    if (calculatedDurationBadge) {
      calculatedDurationBadge.textContent = `⏱ ${durationText}`;
    }

    const start12 = formatMinutesTo12h(startMins);
    const end12 = formatMinutesTo12h(endMins);
    if (stickyTimeVal) {
      stickyTimeVal.textContent = `${start12} – ${end12} (${durationText})`;
    }

    // ----------------------------------------------------
    // Update Timeline Ribbon (Operating window 08:00 to 18:00 = 600 mins)
    // ----------------------------------------------------
    const timelineStartMins = 8 * 60; // 480
    const timelineTotalMins = 10 * 60; // 600

    const leftPercent = Math.max(0, Math.min(100, ((startMins - timelineStartMins) / timelineTotalMins) * 100));
    const widthPercent = Math.max(3, Math.min(100 - leftPercent, ((endMins - startMins) / timelineTotalMins) * 100));

    if (userSelectedTimelineBlock) {
      userSelectedTimelineBlock.style.left = `${leftPercent}%`;
      userSelectedTimelineBlock.style.width = `${widthPercent}%`;
    }
    if (timelineUserRangeLabel) {
      timelineUserRangeLabel.textContent = `Your Event: ${start12} – ${end12} (${durationText})`;
    }

    // Check conflict overlap on current hall
    const currentSelectedHall = document.querySelector('.hall-visual-card.selected');
    const hallName = currentSelectedHall?.getAttribute('data-hall-name') || 'Seminar Hall 1';
    // Seminar Hall 4 and 1 have mock booking 10:00 AM - 12:00 PM for demonstration
    const isConflictHall = hallName.includes('4') || hallName.includes('1');

    let hasConflict = false;
    let conflictDetails = '';

    const bookedStartMins = 10 * 60; // 10:00 AM
    const bookedEndMins = 12 * 60;   // 12:00 PM

    if (isConflictHall) {
      if (bookedTimelineBlock) {
        bookedTimelineBlock.style.display = 'flex';
        // 10:00 is (600 - 480)/600 = 20%, 2 hours is 120/600 = 20%
        bookedTimelineBlock.style.left = '20%';
        bookedTimelineBlock.style.width = '20%';
      }

      // Check overlap: (startA < endB) && (endA > startB)
      if (startMins < bookedEndMins && endMins > bookedStartMins) {
        hasConflict = true;
        conflictDetails = `${hallName} is unavailable from 10:00 AM – 12:00 PM. This time slot is already booked for "Faculty Meeting" by Mechanical Engineering Department.`;
      }
    } else {
      // Hall 2, Hall 3, Conference Hall have NO booking on this date
      if (bookedTimelineBlock) {
        bookedTimelineBlock.style.display = 'none';
      }
    }

    // Toggle Visual Conflict State
    if (hasConflict) {
      if (userSelectedTimelineBlock) {
        userSelectedTimelineBlock.classList.add('conflict-pulse');
      }
      if (timelineStatusBadge) {
        timelineStatusBadge.className = 'timeline-status-badge has-conflict';
        timelineStatusBadge.innerHTML = '<span class="legend-dot-sm dot-red"></span> Time Conflict Detected';
      }
      if (conflictBanner) {
        conflictBanner.style.display = 'flex';
        if (conflictAlertTitle) conflictAlertTitle.textContent = `${hallName} is unavailable from 10:00 AM – 12:00 PM.`;
        if (conflictAlertDesc) conflictAlertDesc.textContent = conflictDetails;
      }
      if (suggestedAlternatives) {
        suggestedAlternatives.style.display = 'flex';
      }
    } else {
      if (userSelectedTimelineBlock) {
        userSelectedTimelineBlock.classList.remove('conflict-pulse');
      }
      if (timelineStatusBadge) {
        timelineStatusBadge.className = 'timeline-status-badge';
        timelineStatusBadge.innerHTML = '<span class="legend-dot-sm dot-green"></span> Available for Selected Time';
      }
      if (conflictBanner) conflictBanner.style.display = 'none';
      if (suggestedAlternatives) suggestedAlternatives.style.display = 'none';
    }
  }

  // Handle Start & End Dropdowns Change
  rangeStartTimeSelect?.addEventListener('change', (e) => {
    rangeStart = e.target.value;
    if (parseTimeToMinutes(rangeEnd) <= parseTimeToMinutes(rangeStart)) {
      const nextEndMins = parseTimeToMinutes(rangeStart) + 120; // default +2 hours
      const h = String(Math.floor(nextEndMins / 60)).padStart(2, '0');
      const m = String(nextEndMins % 60).padStart(2, '0');
      rangeEnd = `${h}:${m}`;
      if (rangeEndTimeSelect) rangeEndTimeSelect.value = rangeEnd;
    }
    applyTimeRange(rangeStart, rangeEnd);
  });

  rangeEndTimeSelect?.addEventListener('change', (e) => {
    rangeEnd = e.target.value;
    applyTimeRange(rangeStart, rangeEnd);
  });

  // Handle Preset Buttons Click
  sessionPresetBtns.forEach((btn) => {
    btn.addEventListener('click', () => {
      const start = btn.getAttribute('data-start');
      const end = btn.getAttribute('data-end');
      applyTimeRange(start, end);
    });
  });

  // ----------------------------------------------------
  // 5. SUGGESTED ALTERNATIVE HALL SELECTION
  // ----------------------------------------------------
  const selectAltBtns = document.querySelectorAll('.select-alt-hall-btn');
  selectAltBtns.forEach((btn) => {
    btn.addEventListener('click', (e) => {
      e.stopPropagation();
      const altId = btn.getAttribute('data-hall-id');
      const altName = btn.getAttribute('data-hall-name');
      const altCap = btn.getAttribute('data-capacity');

      // Find matching hall card and activate it
      let matched = false;
      hallCards.forEach((c) => {
        if (c.getAttribute('data-hall-id') === altId || c.getAttribute('data-hall-name') === altName) {
          c.click();
          matched = true;
        }
      });

      if (!matched) {
        if (preferredHallInput) preferredHallInput.value = altId;
        if (stickyHallVal) stickyHallVal.textContent = altName;
        if (stickyCapacityVal) stickyCapacityVal.textContent = altCap;
        if (selectedHallSlotTitle) {
          selectedHallSlotTitle.textContent = `Select Time Slot – ${altName}`;
        }
      }

      // Re-apply range: on the alternative hall, conflict vanishes!
      applyTimeRange(rangeStart, rangeEnd);
    });
  });

  // ----------------------------------------------------
  // INITIALIZATION
  // ----------------------------------------------------
  renderDateCarousel();
  applyTimeRange('09:00', '12:30'); // Automatically set 09:00 AM - 12:30 PM
  goToStep(2); // Open on Step 2
});
