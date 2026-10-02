/**
 * MCET College ERP - Seminar Hall Booking Form Script (booking_form.js)
 */

document.addEventListener('DOMContentLoaded', () => {
  const form = document.getElementById('bookingForm');
  const startTimeInput = document.getElementById('startTime');
  const endTimeInput = document.getElementById('endTime');
  const durationDisplay = document.getElementById('durationDisplay');
  const hallSelect = document.getElementById('preferredHall');
  const dateInput = document.getElementById('eventDate');
  const participantsInput = document.getElementById('expectedParticipants');
  const checkBtn = document.getElementById('checkAvailabilityBtn');
  const resultBox = document.getElementById('availabilityResultBox');

  // 1. Duration Calculation
  function calculateDuration() {
    if (!startTimeInput || !endTimeInput || !durationDisplay) return;
    const startVal = startTimeInput.value;
    const endVal = endTimeInput.value;

    if (startVal && endVal) {
      const [h1, m1] = startVal.split(':').map(Number);
      const [h2, m2] = endVal.split(':').map(Number);

      const d1 = new Date(); d1.setHours(h1, m1, 0);
      const d2 = new Date(); d2.setHours(h2, m2, 0);

      const diffMs = d2 - d1;
      if (diffMs > 0) {
        const hours = (diffMs / (1000 * 60 * 60)).toFixed(2);
        durationDisplay.textContent = `${hours} Hours`;
        durationDisplay.className = 'text-success font-semibold';
      } else {
        durationDisplay.textContent = 'Invalid time range (Start must be earlier)';
        durationDisplay.className = 'text-danger font-semibold';
      }
    } else {
      durationDisplay.textContent = 'Select start & end times';
      durationDisplay.className = 'text-muted';
    }
  }

  if (startTimeInput && endTimeInput) {
    startTimeInput.addEventListener('change', calculateDuration);
    endTimeInput.addEventListener('change', calculateDuration);
    calculateDuration();
  }

  // 2. Live Availability Check
  if (checkBtn && resultBox) {
    checkBtn.addEventListener('click', async () => {
      const hallId = hallSelect ? hallSelect.value : '';
      const eventDate = dateInput ? dateInput.value : '';
      const startTime = startTimeInput ? startTimeInput.value : '';
      const endTime = endTimeInput ? endTimeInput.value : '';
      const participants = participantsInput ? participantsInput.value : 0;
      const excludeId = form ? form.dataset.bookingId : '';

      if (!hallId || !eventDate || !startTime || !endTime) {
        resultBox.innerHTML = `
          <div class="alert alert-warning" style="margin: 0;">
            Please select Seminar Hall, Event Date, Start Time, and End Time to check availability.
          </div>
        `;
        resultBox.style.display = 'block';
        return;
      }

      checkBtn.disabled = true;
      checkBtn.innerHTML = `
        <svg class="animate-spin" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="display:inline-block; vertical-align:middle; margin-right:6px;">
          <circle cx="12" cy="12" r="10" stroke-opacity="0.25"/>
          <path d="M12 2a10 10 0 0 1 10 10" stroke-opacity="0.75"/>
        </svg>
        Checking...
      `;

      try {
        const url = `/bookings/api/check-availability/?hall_id=${hallId}&event_date=${eventDate}&start_time=${startTime}&end_time=${endTime}&participants=${participants}&exclude_id=${excludeId}`;
        const resp = await fetch(url);
        const data = await resp.json();

        if (data.is_available) {
          resultBox.innerHTML = `
            <div class="alert alert-success" style="margin: 0; display:flex; align-items:flex-start; gap:12px;">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#16A34A" stroke-width="2">
                <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path>
                <polyline points="22 4 12 14.01 9 11.01"></polyline>
              </svg>
              <div>
                <strong style="font-size:14px;">Hall Available!</strong>
                <p style="margin-top:2px;">The selected seminar hall has no conflicting bookings or maintenance for this time slot.</p>
              </div>
            </div>
          `;
        } else {
          let errorHtml = data.errors.map(err => `<li>${err}</li>`).join('');

          let altHallsHtml = '';
          if (data.alternative_halls && data.alternative_halls.length > 0) {
            altHallsHtml = `
              <div style="margin-top: 14px;">
                <p style="font-weight:600; color:#123B72; margin-bottom:6px;">Available Alternative Halls for this Slot:</p>
                <div style="display:flex; gap:8px; flex-wrap:wrap;">
                  ${data.alternative_halls.map(h => `
                    <button type="button" class="btn btn-sm btn-outline select-alt-hall-btn" data-hall-id="${h.id}" style="background:#FFFFFF; font-size:12px;">
                      ${h.name} (Cap: ${h.capacity})
                    </button>
                  `).join('')}
                </div>
              </div>
            `;
          }

          let suggestedSlotsHtml = '';
          if (data.suggested_slots && data.suggested_slots.length > 0) {
            suggestedSlotsHtml = `
              <div style="margin-top: 14px;">
                <p style="font-weight:600; color:#123B72; margin-bottom:6px;">Available Open Time Slots for this Hall Today:</p>
                <div style="display:flex; gap:8px; flex-wrap:wrap;">
                  ${data.suggested_slots.map(s => `
                    <button type="button" class="btn btn-sm btn-outline select-slot-btn" data-start="${s.start_val}" data-end="${s.end_val}" style="background:#FFFFFF; font-size:12px;">
                      ${s.start_time} - ${s.end_time}
                    </button>
                  `).join('')}
                </div>
              </div>
            `;
          }

          resultBox.innerHTML = `
            <div class="alert alert-error" style="margin: 0; display:block;">
              <div style="display:flex; align-items:flex-start; gap:12px;">
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#DC2626" stroke-width="2" style="flex-shrink:0;">
                  <circle cx="12" cy="12" r="10"></circle>
                  <line x1="12" y1="8" x2="12" y2="12"></line>
                  <line x1="12" y1="16" x2="12.01" y2="16"></line>
                </svg>
                <div style="flex:1;">
                  <strong style="font-size:14px;">Hall Unavailable / Schedule Conflict</strong>
                  <ul style="margin: 6px 0 0 16px; font-size:13px;">
                    ${errorHtml}
                  </ul>
                  ${altHallsHtml}
                  ${suggestedSlotsHtml}
                </div>
              </div>
            </div>
          `;

          // Add click handlers for alternative hall suggestions
          resultBox.querySelectorAll('.select-alt-hall-btn').forEach(btn => {
            btn.addEventListener('click', () => {
              if (hallSelect) {
                hallSelect.value = btn.dataset.hallId;
                checkBtn.click();
              }
            });
          });

          // Add click handlers for suggested open slots
          resultBox.querySelectorAll('.select-slot-btn').forEach(btn => {
            btn.addEventListener('click', () => {
              if (startTimeInput && endTimeInput) {
                startTimeInput.value = btn.dataset.start;
                endTimeInput.value = btn.dataset.end;
                calculateDuration();
                checkBtn.click();
              }
            });
          });
        }
        resultBox.style.display = 'block';
      } catch (err) {
        resultBox.innerHTML = `<div class="alert alert-warning">Unable to connect to availability check service. Please try again.</div>`;
        resultBox.style.display = 'block';
      } finally {
        checkBtn.disabled = false;
        checkBtn.innerHTML = `
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="display:inline-block; vertical-align:middle; margin-right:4px;">
            <circle cx="12" cy="12" r="10"></circle>
            <polyline points="12 6 12 12 14 14"></polyline>
          </svg>
          Check Availability
        `;
      }
    });
  }
});
