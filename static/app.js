'use strict';

/* ------------------------------------------------------------------ *
 * Conference Room Booking - front-end SPA
 * Talks to the same-origin Flask JSON API. Every API response uses the
 * envelope { data, error, status }.
 * ------------------------------------------------------------------ */

const state = {
  rooms: [],
  employees: [],
  roomsById: {},
  employeesById: {},
};

/* ---------- tiny DOM helpers ---------- */
const $ = (sel, root = document) => root.querySelector(sel);
const $$ = (sel, root = document) => Array.from(root.querySelectorAll(sel));

function el(tag, attrs = {}, children = []) {
  const node = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (k === 'class') node.className = v;
    else if (k === 'html') node.innerHTML = v;
    else if (k.startsWith('on') && typeof v === 'function') node.addEventListener(k.slice(2), v);
    else if (v !== null && v !== undefined) node.setAttribute(k, v);
  }
  for (const c of [].concat(children)) {
    if (c == null) continue;
    node.append(c.nodeType ? c : document.createTextNode(c));
  }
  return node;
}

/* ---------- API layer ---------- */
async function api(path, options = {}) {
  const opts = { headers: {}, ...options };
  if (opts.body && typeof opts.body === 'object') {
    opts.headers['Content-Type'] = 'application/json';
    opts.body = JSON.stringify(opts.body);
  }
  const res = await fetch(path, opts);
  let payload = null;
  try { payload = await res.json(); } catch (_) { /* non-JSON */ }
  if (!res.ok) {
    const message = (payload && payload.error) || `Request failed (${res.status})`;
    const err = new Error(message);
    err.status = res.status;
    throw err;
  }
  return payload;
}

/* ---------- toasts ---------- */
function toast(message, type = 'success', title = null) {
  const t = el('div', { class: `toast ${type}` }, [
    title ? el('strong', {}, title) : null,
    message,
  ]);
  $('#toasts').append(t);
  setTimeout(() => { t.style.opacity = '0'; setTimeout(() => t.remove(), 250); }, 3800);
}

/* ---------- formatting ---------- */
function fmtDateTime(iso) {
  // iso like "2025-07-01T18:00:00" (no timezone) - format without TZ shifts
  const [d, t] = iso.split('T');
  const time = (t || '').slice(0, 5);
  const dt = new Date(d + 'T00:00:00');
  const day = dt.toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' });
  return `${day} ${time}`;
}
function todayStr() {
  const now = new Date();
  const p = (n) => String(n).padStart(2, '0');
  return `${now.getFullYear()}-${p(now.getMonth() + 1)}-${p(now.getDate())}`;
}

/* ---------- reference data ---------- */
async function loadReferenceData() {
  const [rooms, employees] = await Promise.all([
    api('/rooms'),
    api('/employees'),
  ]);
  state.rooms = rooms.data;
  state.employees = employees.data;
  state.roomsById = Object.fromEntries(state.rooms.map((r) => [r.id, r]));
  state.employeesById = Object.fromEntries(state.employees.map((e) => [e.id, e]));

  fillSelect('#f-room', state.rooms, (r) => `${r.name} (cap ${r.capacity})`);
  fillSelect('#fs-room', state.rooms, (r) => r.name);
  fillSelect('#f-organizer', state.employees, (e) => `${e.name} - ${e.department}`);
  fillSelect('#filter-room', state.rooms, (r) => r.name, 'All rooms');
  fillSelect('#filter-organizer', state.employees, (e) => e.name, 'All organizers');
}

function fillSelect(sel, items, labelFn, placeholder = null) {
  const node = $(sel);
  node.innerHTML = '';
  if (placeholder !== null) node.append(el('option', { value: '' }, placeholder));
  for (const item of items) node.append(el('option', { value: item.id }, labelFn(item)));
}

/* ---------- health check ---------- */
async function checkHealth() {
  const dot = $('#apiStatus');
  const text = $('#apiStatusText');
  try {
    await api('/health');
    dot.className = 'status-dot ok';
    text.textContent = 'API online';
  } catch (_) {
    dot.className = 'status-dot down';
    text.textContent = 'API offline';
  }
}

/* ---------- tabs ---------- */
function initTabs() {
  $$('.tab').forEach((tab) => {
    tab.addEventListener('click', () => {
      $$('.tab').forEach((t) => t.classList.remove('is-active'));
      $$('.tab-panel').forEach((p) => p.classList.remove('is-active'));
      tab.classList.add('is-active');
      $(`#tab-${tab.dataset.tab}`).classList.add('is-active');
      if (tab.dataset.tab === 'bookings') loadBookings();
      if (tab.dataset.tab === 'rooms') renderRooms();
    });
  });
}

/* ---------- booking form ---------- */
function initBookingForm() {
  const form = $('#bookingForm');
  $('#f-date').value = todayStr();

  const updateCapacityHint = () => {
    const room = state.roomsById[$('#f-room').value];
    const att = parseInt($('#f-attendees').value, 10);
    const hint = $('#capacityHint');
    if (room && att && att > room.capacity) {
      hint.textContent = `Note: ${att} attendees exceeds ${room.name}'s capacity of ${room.capacity}.`;
      hint.className = 'form-hint warn';
    } else {
      hint.textContent = '';
      hint.className = 'form-hint';
    }
  };
  $('#f-room').addEventListener('change', updateCapacityHint);
  $('#f-attendees').addEventListener('input', updateCapacityHint);

  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    const date = $('#f-date').value;
    const start = $('#f-start').value;
    const end = $('#f-end').value;
    if (!date || !start || !end) { toast('Please fill in date, start and end.', 'error'); return; }
    if (end <= start) { toast('End time must be after start time.', 'error'); return; }

    const body = {
      room_id: parseInt($('#f-room').value, 10),
      organizer_id: parseInt($('#f-organizer').value, 10),
      start_time: `${date}T${start}:00`,
      end_time: `${date}T${end}:00`,
      meeting_title: $('#f-title').value.trim(),
      attendees: parseInt($('#f-attendees').value, 10) || 1,
    };

    const btn = $('#createBtn');
    btn.disabled = true; btn.textContent = 'Creating…';
    try {
      const res = await api('/bookings', { method: 'POST', body });
      toast(`Booking #${res.data.id} created for ${state.roomsById[res.data.room_id].name}.`, 'success', 'Booked');
      form.reset();
      $('#f-date').value = date;
      updateCapacityHint();
    } catch (err) {
      const kind = err.status === 409 ? 'Time conflict' : 'Could not book';
      toast(err.message, 'error', kind);
    } finally {
      btn.disabled = false; btn.textContent = 'Create booking';
    }
  });
}

/* ---------- free slots ---------- */
function initFreeSlots() {
  $('#fs-date').value = todayStr();
  $('#checkSlotsBtn').addEventListener('click', loadFreeSlots);
}

async function loadFreeSlots() {
  const roomId = $('#fs-room').value;
  const date = $('#fs-date').value;
  const box = $('#slotsResult');
  if (!roomId || !date) { toast('Pick a room and date first.', 'error'); return; }
  box.innerHTML = '<div class="state"><div class="spinner"></div>Loading slots…</div>';
  try {
    const res = await api(`/rooms/${roomId}/free-slots?date=${date}`);
    const slots = res.data;
    if (!slots.length) {
      box.innerHTML = '<div class="state">No free slots on this day (09:00–18:00).</div>';
      return;
    }
    const room = state.roomsById[roomId];
    box.innerHTML = '';
    box.append(el('p', { class: 'slots-meta' }, `${slots.length} free 30-min slot(s) for ${room.name} on ${date}`));
    const grid = el('div', { class: 'slots-grid' });
    for (const s of slots) {
      const startT = s.start_time.slice(11, 16);
      const endT = s.end_time.slice(11, 16);
      grid.append(el('button', {
        class: 'slot-chip',
        type: 'button',
        title: 'Use this slot in the booking form',
        onclick: () => useSlot(roomId, date, startT, endT),
      }, `${startT}–${endT}`));
    }
    box.append(grid);
  } catch (err) {
    box.innerHTML = `<div class="state">${err.message}</div>`;
  }
}

function useSlot(roomId, date, startT, endT) {
  // Jump to the Book tab with the form prefilled.
  $('[data-tab="book"]').click();
  $('#f-room').value = roomId;
  $('#f-date').value = date;
  $('#f-start').value = startT;
  $('#f-end').value = endT;
  $('#f-room').dispatchEvent(new Event('change'));
  toast(`Slot ${startT}–${endT} loaded into the form.`, 'success');
  $('#bookingForm').scrollIntoView({ behavior: 'smooth', block: 'center' });
}

/* ---------- bookings list ---------- */
function initBookings() {
  $('#refreshBookingsBtn').addEventListener('click', loadBookings);
  $('#filter-room').addEventListener('change', loadBookings);
  $('#filter-organizer').addEventListener('change', loadBookings);
  $('#filter-hide-cancelled').addEventListener('change', loadBookings);
}

async function loadBookings() {
  const box = $('#bookingsResult');
  box.innerHTML = '<div class="state"><div class="spinner"></div>Loading bookings…</div>';
  const params = new URLSearchParams();
  if ($('#filter-room').value) params.set('room_id', $('#filter-room').value);
  if ($('#filter-organizer').value) params.set('organizer_id', $('#filter-organizer').value);
  try {
    const res = await api(`/bookings?${params.toString()}`);
    let bookings = res.data;
    if ($('#filter-hide-cancelled').checked) bookings = bookings.filter((b) => b.status !== 'cancelled');
    bookings.sort((a, b) => a.start_time.localeCompare(b.start_time));
    renderBookings(bookings);
  } catch (err) {
    box.innerHTML = `<div class="state">${err.message}</div>`;
  }
}

function renderBookings(bookings) {
  const box = $('#bookingsResult');
  if (!bookings.length) {
    box.innerHTML = '<div class="state">No bookings match these filters.</div>';
    return;
  }
  const rows = bookings.map((b) => {
    const room = state.roomsById[b.room_id];
    const org = state.employeesById[b.organizer_id];
    const isScheduled = b.status === 'scheduled';
    const actions = el('div', { class: 'actions' }, [
      el('button', {
        class: 'btn btn-sm', type: 'button',
        disabled: isScheduled ? null : 'disabled',
        onclick: () => openReschedule(b),
      }, 'Reschedule'),
      el('button', {
        class: 'btn btn-sm btn-danger', type: 'button',
        disabled: isScheduled ? null : 'disabled',
        onclick: () => cancelBooking(b),
      }, 'Cancel'),
    ]);
    return el('tr', {}, [
      el('td', {}, `#${b.id}`),
      el('td', {}, room ? room.name : `Room ${b.room_id}`),
      el('td', {}, b.meeting_title || '—'),
      el('td', {}, org ? org.name : `Emp ${b.organizer_id}`),
      el('td', {}, fmtDateTime(b.start_time)),
      el('td', {}, fmtDateTime(b.end_time)),
      el('td', {}, el('span', { class: `badge badge-${b.status}` }, b.status)),
      el('td', {}, actions),
    ]);
  });
  const table = el('table', {}, [
    el('thead', {}, el('tr', {}, ['ID', 'Room', 'Title', 'Organizer', 'Start', 'End', 'Status', 'Actions']
      .map((h) => el('th', {}, h)))),
    el('tbody', {}, rows),
  ]);
  box.innerHTML = '';
  box.append(el('div', { class: 'table-wrap' }, table));
}

async function cancelBooking(b) {
  const room = state.roomsById[b.room_id];
  if (!confirm(`Cancel booking #${b.id} (${b.meeting_title || 'untitled'}) in ${room ? room.name : b.room_id}?`)) return;
  try {
    await api(`/bookings/${b.id}`, { method: 'DELETE' });
    toast(`Booking #${b.id} cancelled.`, 'success');
    loadBookings();
  } catch (err) {
    toast(err.message, 'error', 'Could not cancel');
  }
}

/* ---------- reschedule modal ---------- */
function initReschedule() {
  const modal = $('#rescheduleModal');
  $$('[data-close-modal]', modal).forEach((btn) => btn.addEventListener('click', closeReschedule));
  modal.addEventListener('click', (e) => { if (e.target === modal) closeReschedule(); });

  $('#rescheduleForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    const id = $('#r-id').value;
    const date = $('#r-date').value;
    const start = $('#r-start').value;
    const end = $('#r-end').value;
    if (end <= start) { toast('End time must be after start time.', 'error'); return; }
    const body = { start_time: `${date}T${start}:00`, end_time: `${date}T${end}:00` };
    try {
      await api(`/bookings/${id}`, { method: 'PUT', body });
      toast(`Booking #${id} rescheduled.`, 'success');
      closeReschedule();
      loadBookings();
    } catch (err) {
      const title = err.status === 409 ? 'Time conflict' : 'Reschedule failed';
      toast(`Request could not be rescheduled — ${err.message}`, 'error', title);
    }
  });
}

function openReschedule(b) {
  const room = state.roomsById[b.room_id];
  $('#r-id').value = b.id;
  $('#r-date').value = b.start_time.slice(0, 10);
  $('#r-start').value = b.start_time.slice(11, 16);
  $('#r-end').value = b.end_time.slice(11, 16);
  $('#rescheduleMeta').textContent =
    `#${b.id} · ${room ? room.name : 'Room ' + b.room_id} · ${b.meeting_title || 'untitled'}`;
  $('#rescheduleModal').hidden = false;
}
function closeReschedule() { $('#rescheduleModal').hidden = true; }

/* ---------- rooms ---------- */
function renderRooms() {
  const box = $('#roomsResult');
  if (!state.rooms.length) { box.innerHTML = '<div class="state">No rooms.</div>'; return; }
  box.innerHTML = '';
  for (const r of state.rooms) {
    box.append(el('div', { class: 'room-card' }, [
      el('h3', {}, r.name),
      el('div', { class: 'cap' }, `${r.capacity}`),
      el('div', { class: 'loc' }, `seats · ${r.location}`),
    ]));
  }
}

/* ---------- bootstrap ---------- */
async function init() {
  initTabs();
  initBookingForm();
  initFreeSlots();
  initBookings();
  initReschedule();
  checkHealth();
  try {
    await loadReferenceData();
    renderRooms();
  } catch (err) {
    toast('Failed to load rooms/employees. Is the API running?', 'error', 'Startup error');
  }
}

document.addEventListener('DOMContentLoaded', init);
