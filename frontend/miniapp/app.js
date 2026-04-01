/* ============================================================
   LINGUA MINI APP — app.js
   Handles: navigation, API calls, calendar, bookings, filters
   ============================================================ */

'use strict';

// ─── Config ──────────────────────────────────────────────────
const CONFIG = {
    API_BASE: '',          // пустая строка = тот же Origin (бэк обслуживает фронт)
    VK_APP_ID: 54520332,
};

// ─── VK Bridge Init ───────────────────────────────────────────
let _vkLaunchParams = '';

async function initVKBridge() {
    try {
        if (typeof vkBridge !== 'undefined') {
            await vkBridge.send('VKWebAppInit', { app_id: CONFIG.VK_APP_ID });
            // VK передаёт параметры запуска в hash или query string
            _vkLaunchParams = window.location.hash.slice(1) ||
                window.location.search.slice(1) || '';
            // Дополнительно получаем имя пользователя через Bridge
            try {
                const userData = await vkBridge.send('VKWebAppGetUserInfo');
                state.student.first_name = userData.first_name || 'Студент';
                state.student.last_name = userData.last_name || '';
                state.student.vk_id = userData.id || null;
                updateStudentUI();
            } catch (_) { /* необязательно */ }
        }
    } catch (e) {
        console.warn('VK Bridge init failed:', e.message);
    }
}

// ─── State ────────────────────────────────────────────────────
const state = {
    currentScreen: 'home',
    student: { id: null, first_name: 'Студент', last_name: '', vk_id: null },

    // Home calendar
    homeWeekOffset: 0,
    selectedHomeDate: new Date(),

    // Booking screen
    bookingWeekOffset: 0,
    selectedBookingDate: null,
    selectedLanguageId: null,
    selectedTeacherId: null,

    // Data
    myBookings: [],
    availableLessons: [],
    languages: [],
    teachers: [],

    // Cancel flow
    cancelBookingId: null,
};

// ─── Utility ──────────────────────────────────────────────────
function getVkParams() {
    // VK передаёт параметры запуска в hash или query string при открытии Mini App
    if (_vkLaunchParams) return _vkLaunchParams;
    return window.location.hash.slice(1) || window.location.search.slice(1) || '';
}

async function apiFetch(path, options = {}) {
    const headers = { 'Content-Type': 'application/json', ...options.headers };
    const vkParams = getVkParams();
    if (vkParams) headers['X-Vk-Params'] = vkParams;

    const res = await fetch(CONFIG.API_BASE + path, { ...options, headers });
    if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: res.statusText }));
        throw new Error(err.detail || 'Ошибка запроса');
    }
    return res.json();
}

function showToast(msg, type = '') {
    const el = document.getElementById('toast');
    el.textContent = msg;
    el.className = `toast show ${type}`;
    clearTimeout(el._timer);
    el._timer = setTimeout(() => { el.className = 'toast'; }, 3000);
}

function formatTime(iso) {
    return new Date(iso).toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' });
}

function formatDate(iso) {
    return new Date(iso).toLocaleDateString('ru-RU', { day: 'numeric', month: 'long' });
}

function isSameDay(d1, d2) {
    return d1.getFullYear() === d2.getFullYear() &&
        d1.getMonth() === d2.getMonth() &&
        d1.getDate() === d2.getDate();
}

// ─── Navigation ───────────────────────────────────────────────
function navigate(screen) {
    document.getElementById(`screen-${state.currentScreen}`)?.classList.remove('active');
    document.getElementById(`nav-${state.currentScreen}`)?.classList.remove('active');

    state.currentScreen = screen;

    document.getElementById(`screen-${screen}`)?.classList.add('active');
    document.getElementById(`nav-${screen}`)?.classList.add('active');

    if (screen === 'home') loadMyBookings();
    if (screen === 'profile') loadProfile();
}
// Expose globally for onclick attributes
window.navigate = navigate;

// ─── Calendar Builder ─────────────────────────────────────────
function buildWeek(containerId, weekOffset, selectedDate, onSelect, bookedDates = []) {
    const container = document.getElementById(containerId);
    if (!container) return;

    const today = new Date();
    const startOfWeek = new Date(today);
    startOfWeek.setDate(today.getDate() - today.getDay() + 1 + weekOffset * 7); // Mon-based

    const days = ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс'];
    container.innerHTML = '';

    for (let i = 0; i < 7; i++) {
        const day = new Date(startOfWeek);
        day.setDate(startOfWeek.getDate() + i);

        const cell = document.createElement('div');
        cell.className = 'day-cell';
        if (isSameDay(day, today)) cell.classList.add('today');
        if (selectedDate && isSameDay(day, selectedDate)) cell.classList.add('selected');
        if (bookedDates.some(d => isSameDay(new Date(d), day))) cell.classList.add('has-event');

        cell.innerHTML = `
      <span class="day-name">${days[i]}</span>
      <span class="day-number">${day.getDate()}</span>
    `;
        cell.addEventListener('click', () => onSelect(day));
        container.appendChild(cell);
    }
}

function updateMonthLabel(weekOffset) {
    const today = new Date();
    const monday = new Date(today);
    monday.setDate(today.getDate() - today.getDay() + 1 + weekOffset * 7);
    const months = ['Январь', 'Февраль', 'Март', 'Апрель', 'Май', 'Июнь',
        'Июль', 'Август', 'Сентябрь', 'Октябрь', 'Ноябрь', 'Декабрь'];
    const label = document.getElementById('calendar-month-label');
    if (label) label.textContent = months[monday.getMonth()];
}

// ─── Home Screen ──────────────────────────────────────────────
async function loadMyBookings() {
    try {
        const bookings = await apiFetch('/bookings/my');
        state.myBookings = bookings;
        renderHomeCalendar();
        renderUpcoming();
    } catch (e) {
        console.error('loadMyBookings:', e);
        renderUpcoming(); // render empty state
    }
}

function renderHomeCalendar() {
    const bookedDates = state.myBookings
        .filter(b => b.status === 'active')
        .map(b => b.lesson?.start_time);

    buildWeek('week-days', state.homeWeekOffset, state.selectedHomeDate,
        (day) => {
            state.selectedHomeDate = day;
            renderHomeCalendar();
            renderUpcoming(day);
        },
        bookedDates
    );
    updateMonthLabel(state.homeWeekOffset);
}

function renderUpcoming(filterDate = null) {
    const list = document.getElementById('upcoming-list');
    const empty = document.getElementById('upcoming-empty');
    const countBadge = document.getElementById('upcoming-count');

    const active = state.myBookings.filter(b => {
        if (b.status !== 'active') return false;
        if (!filterDate) return true;
        return b.lesson?.start_time && isSameDay(new Date(b.lesson.start_time), filterDate);
    });

    if (countBadge) countBadge.textContent = active.length;

    if (active.length === 0) {
        list.innerHTML = '';
        empty?.classList.remove('hidden');
        return;
    }
    empty?.classList.add('hidden');

    list.innerHTML = active.map(b => bookingCardHTML(b)).join('');
}

function bookingCardHTML(booking) {
    const lesson = booking.lesson || {};
    const cancelled = booking.status !== 'active';
    const langName = lesson.language_name || 'Занятие';
    const teacher = lesson.teacher_name || 'Преподаватель';
    const type = lesson.type === 'group' ? 'Группа' : lesson.type === 'individual' ? 'Индивидуально' : lesson.type || '';
    const start = lesson.start_time ? formatTime(lesson.start_time) : '—';
    const end = lesson.end_time ? formatTime(lesson.end_time) : '';
    const date = lesson.start_time ? formatDate(lesson.start_time) : '';

    return `
    <div class="booking-card ${cancelled ? 'cancelled' : ''}">
      <div class="booking-top">
        <div class="booking-info">
          <div class="booking-lang">${langName}</div>
          <div class="booking-teacher">с ${teacher}</div>
        </div>
        ${type ? `<span class="booking-type-badge">${type}</span>` : ''}
      </div>
      <div class="booking-time-row">
        <div class="booking-time">
          <span class="material-symbols-rounded">schedule</span>
          ${start}${end ? ' — ' + end : ''}
        </div>
        <span class="booking-date">${date}</span>
      </div>
      ${!cancelled ? `
        <button class="btn-cancel" onclick="openCancelModal('${booking.id}', '${langName}', '${date}', '${start}')">
          <span class="material-symbols-rounded">close</span>
          Отменить
        </button>
      ` : '<span style="font-size:12px;color:var(--tertiary);font-weight:600;letter-spacing:.05em;text-transform:uppercase">Отменено</span>'}
    </div>
  `;
}

// ─── Cancel Booking ───────────────────────────────────────────
function openCancelModal(bookingId, lang, date, time) {
    state.cancelBookingId = bookingId;
    document.getElementById('modal-lesson-info').textContent =
        `${lang} — ${date} в ${time}`;
    document.getElementById('cancel-modal').classList.remove('hidden');
}
window.openCancelModal = openCancelModal;

function closeModal() {
    document.getElementById('cancel-modal').classList.add('hidden');
    state.cancelBookingId = null;
}
window.closeModal = closeModal;

document.getElementById('modal-confirm-btn').addEventListener('click', async () => {
    if (!state.cancelBookingId) return;
    const btn = document.getElementById('modal-confirm-btn');
    btn.textContent = '...'; btn.disabled = true;
    try {
        await apiFetch(`/bookings/${state.cancelBookingId}/cancel`, { method: 'PATCH' });
        closeModal();
        showToast('Занятие отменено', 'success');
        await loadMyBookings();
    } catch (e) {
        showToast(e.message || 'Ошибка отмены', 'error');
    } finally {
        btn.textContent = 'Отменить'; btn.disabled = false;
    }
});

// Home week navigation
document.getElementById('week-prev').addEventListener('click', () => {
    state.homeWeekOffset--; renderHomeCalendar(); renderUpcoming();
});
document.getElementById('week-next').addEventListener('click', () => {
    state.homeWeekOffset++; renderHomeCalendar(); renderUpcoming();
});

// ─── Booking Screen ───────────────────────────────────────────
async function loadBookingFilters() {
    try {
        const [langs, staff] = await Promise.all([
            apiFetch('/languages/'),
            apiFetch('/staff/'),
        ]);
        state.languages = langs;
        state.teachers = staff.filter(s => s.role === 'teacher');
        renderLanguageChips();
        renderTeacherChips();
    } catch (e) {
        console.error('loadBookingFilters:', e);
    }
}

function renderLanguageChips() {
    const container = document.getElementById('language-list');
    if (!container) return;
    container.innerHTML = state.languages.map(l => `
    <div class="filter-chip ${state.selectedLanguageId === l.id ? 'selected' : ''}"
         onclick="selectLanguage('${l.id}')">
      <span class="chip-name">${l.name}</span>
      <span class="chip-sub">${l.code}</span>
    </div>
  `).join('') || '<p class="filter-hint">Нет доступных языков</p>';
}

function renderTeacherChips() {
    const container = document.getElementById('teacher-list');
    if (!container) return;
    const filtered = state.selectedLanguageId
        ? state.teachers.filter(t => t.languages?.some(l => l.id === state.selectedLanguageId))
        : state.teachers;

    container.innerHTML = filtered.map(t => `
    <div class="filter-chip ${state.selectedTeacherId === t.id ? 'selected' : ''}"
         onclick="selectTeacher('${t.id}')">
      <span class="chip-name">${t.first_name} ${t.last_name}</span>
      <span class="chip-sub">${t.languages?.map(l => l.name).join(', ') || ''}</span>
    </div>
  `).join('') || '<p class="filter-hint">Нет преподавателей для этого языка</p>';
}

window.selectLanguage = function (id) {
    state.selectedLanguageId = state.selectedLanguageId === id ? null : id;
    state.selectedTeacherId = null;
    renderLanguageChips();
    renderTeacherChips();
    loadAvailableLessons();
};

window.selectTeacher = function (id) {
    state.selectedTeacherId = state.selectedTeacherId === id ? null : id;
    renderTeacherChips();
    loadAvailableLessons();
};

function renderBookingCalendar() {
    buildWeek('booking-week-days', state.bookingWeekOffset, state.selectedBookingDate,
        (day) => {
            state.selectedBookingDate = day;
            renderBookingCalendar();
            loadAvailableLessons();
        }
    );
}

async function loadAvailableLessons() {
    const container = document.getElementById('available-list');
    if (!container) return;

    if (!state.selectedLanguageId || !state.selectedTeacherId || !state.selectedBookingDate) {
        container.innerHTML = '<p class="filter-hint">Выберите язык, преподавателя и дату</p>';
        return;
    }

    container.innerHTML = '<div class="skeleton-card"></div><div class="skeleton-card"></div>';

    try {
        const params = new URLSearchParams();
        if (state.selectedTeacherId) params.set('teacher_id', state.selectedTeacherId);
        if (state.selectedBookingDate) {
            const d = state.selectedBookingDate;
            const year = d.getFullYear();
            const month = String(d.getMonth() + 1).padStart(2, '0');
            const day = String(d.getDate()).padStart(2, '0');
            const localDateStr = `${year}-${month}-${day}`;
            params.set('date_from', localDateStr);
            params.set('date_to', localDateStr);
        }
        const lessons = await apiFetch(`/lessons/?${params}`);
        const filtered = state.selectedLanguageId
            ? lessons.filter(l => l.language_id === state.selectedLanguageId)
            : lessons;

        state.availableLessons = filtered;
        renderAvailableLessons();
    } catch (e) {
        container.innerHTML = `<p class="filter-hint" style="color:var(--tertiary)">${e.message}</p>`;
    }
}

function renderAvailableLessons() {
    const container = document.getElementById('available-list');
    if (!container) return;

    const lessons = state.availableLessons;
    if (lessons.length === 0) {
        container.innerHTML = '<p class="filter-hint">Нет доступных занятий по выбранным параметрам</p>';
        return;
    }

    container.innerHTML = lessons.map(l => {
        const few = l.available_slots <= 2;
        return `
      <div class="available-card">
        <div class="available-info">
          <div class="available-time">${formatTime(l.start_time)} — ${formatTime(l.end_time)}</div>
          <div class="available-slots ${few ? 'few' : ''}">
            ${l.available_slots > 0 ? `${l.available_slots} мест${l.available_slots === 1 ? 'о' : 'а'}` : 'Мест нет'}
          </div>
        </div>
        <button class="btn-book" ${l.is_booked_by_me || l.available_slots === 0 ? 'disabled' : ''}
                onclick="bookLesson('${l.id}')">
          ${l.is_booked_by_me ? 'Записан' : 'Записаться'}
        </button>
      </div>
    `;
    }).join('');
}

window.bookLesson = async function (lessonId) {
    if (!state.student.id) {
        showToast('Необходима авторизация', 'error'); return;
    }
    try {
        await apiFetch('/bookings/', {
            method: 'POST',
            body: JSON.stringify({ lesson_id: lessonId, student_id: state.student.id }),
        });
        showToast('Вы записаны на занятие! 🎉', 'success');
        await loadAvailableLessons();
        await loadMyBookings();
    } catch (e) {
        showToast(e.message || 'Ошибка записи', 'error');
    }
};

// Booking week nav
document.getElementById('booking-week-prev').addEventListener('click', () => {
    state.bookingWeekOffset--; renderBookingCalendar();
});
document.getElementById('booking-week-next').addEventListener('click', () => {
    state.bookingWeekOffset++; renderBookingCalendar();
});

// ─── Profile Screen ───────────────────────────────────────────
function loadProfile() {
    const { first_name, last_name } = state.student;
    const initials = ((first_name?.[0] || '') + (last_name?.[0] || '')).toUpperCase() || 'С';

    document.getElementById('profile-name').textContent = `${first_name} ${last_name}`.trim();
    document.getElementById('profile-avatar').textContent = initials;
    document.getElementById('profile-meta').textContent = `VK ID: ${state.student.vk_id || '—'}`;

    const all = state.myBookings.length;
    const upcoming = state.myBookings.filter(b => b.status === 'active').length;
    const cancelled = state.myBookings.filter(b => b.status === 'cancelled_by_student').length;

    document.getElementById('stat-total').textContent = all;
    document.getElementById('stat-upcoming').textContent = upcoming;
    document.getElementById('stat-cancelled').textContent = cancelled;

    const profileBookings = document.getElementById('profile-bookings');
    const active = state.myBookings.filter(b => b.status === 'active');
    if (active.length === 0) {
        profileBookings.innerHTML = '<p class="filter-hint">Нет активных записей</p>';
    } else {
        profileBookings.innerHTML = active.map(b => bookingCardHTML(b)).join('');
    }
}

// ─── Auth ─────────────────────────────────────────────────────
async function initStudent() {
    try {
        const vkParams = getVkParams();
        // Try to authenticate student via VK params header
        const res = await fetch(`${CONFIG.API_BASE}/students/auth`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-Vk-Params': vkParams,
            },
            body: JSON.stringify({
                vk_launch_params: vkParams,
                first_name: state.student.first_name,
                last_name: state.student.last_name
            }),
        });
        if (res.ok) {
            const student = await res.json();
            state.student = student;
            updateStudentUI();
        }
    } catch (e) {
        // Fail silently — app still works for browsing lessons
        console.warn('Auth skipped:', e.message);
    }
}

function updateStudentUI() {
    const { first_name, last_name } = state.student;
    const initials = ((first_name?.[0] || '') + (last_name?.[0] || '')).toUpperCase() || 'С';
    const fullName = `${first_name || ''} ${last_name || ''}`.trim() || 'Студент';

    const homeNameEl = document.getElementById('home-student-name');
    const homeAvatar = document.getElementById('home-avatar');

    if (homeNameEl) homeNameEl.textContent = fullName;
    if (homeAvatar) homeAvatar.textContent = initials;
}

// ─── Init ─────────────────────────────────────────────────────
async function init() {
    // Сначала инициализируем VK Bridge (получаем launch params и имя пользователя)
    await initVKBridge();

    // Рендерим календари сразу без API
    renderHomeCalendar();
    renderBookingCalendar();

    // Загружаем фильтры для экрана записи в фоне
    loadBookingFilters();

    // Авторизация студента и загрузка его записей
    await initStudent();
    await loadMyBookings();
}

document.addEventListener('DOMContentLoaded', init);
