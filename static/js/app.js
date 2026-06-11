/* ═══════════════════════════════════════════
   Система управління розкладом — JS клієнт
   ═══════════════════════════════════════════ */

'use strict';

// ─── State ───────────────────────────────────
const state = {
  teachers: [], rooms: [], groups: [], subjects: [], lessons: []
};

// ─── Utils ───────────────────────────────────
async function api(path, method = 'GET', body = null) {
  const opts = { method, headers: { 'Content-Type': 'application/json' } };
  if (body) opts.body = JSON.stringify(body);
  const res = await fetch(path, opts);
  return res.json();
}

function toast(msg, type = '') {
  const el = document.getElementById('toast');
  el.textContent = msg;
  el.className = 'toast ' + type;
  setTimeout(() => el.classList.add('hidden'), 3000);
}

function openModal(id) { document.getElementById(id).classList.remove('hidden'); }
function closeModal(id) { document.getElementById(id).classList.add('hidden'); }

function tag(text, cls) {
  return `<span class="tag tag-${cls}">${text}</span>`;
}

// ─── Navigation ──────────────────────────────
document.querySelectorAll('.nav-link').forEach(link => {
  link.addEventListener('click', e => {
    e.preventDefault();
    const tab = link.dataset.tab;
    document.querySelectorAll('.nav-link').forEach(l => l.classList.remove('active'));
    document.querySelectorAll('.tab-content').forEach(t => t.classList.remove('active'));
    link.classList.add('active');
    document.getElementById('tab-' + tab).classList.add('active');
    if (tab === 'schedule')   loadScheduleView();
    if (tab === 'teachers')   renderTeachers();
    if (tab === 'rooms')      renderRooms();
    if (tab === 'groups')     renderGroups();
    if (tab === 'subjects')   renderSubjects();
    if (tab === 'dashboard')  loadDashboard();
  });
});

// ─── Initial Load ────────────────────────────
async function bootstrap() {
  const [t, r, g, s, l] = await Promise.all([
    api('/api/teachers'), api('/api/rooms'),
    api('/api/groups'), api('/api/subjects'), api('/api/lessons')
  ]);
  state.teachers = t.data || [];
  state.rooms    = r.data || [];
  state.groups   = g.data || [];
  state.subjects = s.data || [];
  state.lessons  = l.data || [];
  loadDashboard();
  populateFilterSelects();
}

// ─── Dashboard ───────────────────────────────
async function loadDashboard() {
  const res = await api('/api/statistics');
  const st  = res.data;
  document.getElementById('stat-lessons').textContent   = st.total_lessons;
  document.getElementById('stat-teachers').textContent  = st.total_teachers;
  document.getElementById('stat-rooms').textContent     = st.total_rooms;
  document.getElementById('stat-groups').textContent    = st.total_groups;

  // conflicts
  const cr = await api('/api/conflicts');
  const clist = document.getElementById('conflict-list');
  if (cr.data && cr.data.length) {
    clist.innerHTML = cr.data.map(c =>
      `<div class="conflict-item">⚠ ${c}</div>`
    ).join('');
  } else {
    clist.innerHTML = '<p class="muted">✅ Конфліктів немає</p>';
  }

  // teacher load
  const tl = document.getElementById('teacher-load');
  const load = st.teacher_load || {};
  const maxLoad = Math.max(...Object.values(load), 1);
  tl.innerHTML = Object.entries(load).map(([name, cnt]) => `
    <div class="load-item">
      <div>
        <div>${name}</div>
        <div class="load-bar" style="width:${(cnt/maxLoad)*120}px"></div>
      </div>
      <strong>${cnt} пар</strong>
    </div>
  `).join('') || '<p class="muted">Немає даних</p>';
}

// ─── Schedule view (timetable) ───────────────
function populateFilterSelects() {
  const fg = document.getElementById('filter-group');
  const ft = document.getElementById('filter-teacher');
  fg.innerHTML = '<option value="">Усі групи</option>' +
    state.groups.map(g => `<option value="${g.id}">${g.name}</option>`).join('');
  ft.innerHTML = '<option value="">Усі викладачі</option>' +
    state.teachers.map(t => `<option value="${t.id}">${t.name}</option>`).join('');
}

async function loadScheduleView() {
  const gid = document.getElementById('filter-group').value;
  const tid = document.getElementById('filter-teacher').value;
  let lessons;
  if (gid) {
    const r = await api(`/api/schedule/group/${gid}`);
    lessons = r.data || [];
  } else if (tid) {
    const r = await api(`/api/schedule/teacher/${tid}`);
    lessons = r.data || [];
  } else {
    const r = await api('/api/lessons');
    lessons = r.data || [];
  }
  state.lessons = lessons;
  renderTimetable(lessons);
}

const DAYS   = ['Понеділок','Вівторок','Середа','Четвер','П\'ятниця','Субота'];
const SLOTS  = [
  ['1','08:00–09:35'], ['2','09:45–11:20'], ['3','11:30–13:05'],
  ['4','13:30–15:05'], ['5','15:15–16:50'], ['6','17:00–18:35']
];

function renderTimetable(lessons) {
  // Build lookup: day → slot → [lessons]
  const table = {};
  for (let d = 0; d < 6; d++) {
    table[d] = {};
    for (let s = 1; s <= 6; s++) table[d][s] = [];
  }
  lessons.forEach(l => {
    if (table[l.day_index] && table[l.day_index][l.slot])
      table[l.day_index][l.slot].push(l);
  });

  const typeColorMap = {
    'Лекція': 'LECTURE', 'Практика': 'PRACTICE',
    'Лабораторна': 'LAB', 'Семінар': 'SEMINAR'
  };

  let html = `<table class="timetable"><thead><tr>
    <th>Пара / Час</th>
    ${DAYS.map(d => `<th>${d}</th>`).join('')}
  </tr></thead><tbody>`;

  SLOTS.forEach(([slotNum, time]) => {
    html += `<tr><td class="slot-label"><strong>${slotNum}</strong><br><small>${time}</small></td>`;
    for (let d = 0; d < 6; d++) {
      const cells = table[d][parseInt(slotNum)];
      html += '<td>';
      cells.forEach(l => {
        const tc = typeColorMap[l.lesson_type] || 'LECTURE';
        html += `
          <div class="lesson-cell lesson-type-${tc}">
            <button class="lc-delete" onclick="deleteLesson(${l.id})" title="Видалити">✕</button>
            <div class="lc-subject">${l.subject}</div>
            <div class="lc-meta">👨‍🏫 ${l.teacher}</div>
            <div class="lc-meta">👥 ${l.group}</div>
            <div class="lc-meta">🏛 ауд.${l.room}</div>
            <div class="lc-meta">${tag(l.lesson_type, 'blue')}</div>
          </div>`;
      });
      html += '</td>';
    }
    html += '</tr>';
  });

  html += '</tbody></table>';
  document.getElementById('schedule-grid').innerHTML = html;
}

// ─── Teachers ────────────────────────────────
function renderTeachers() {
  const el = document.getElementById('teachers-list');
  if (!state.teachers.length) { el.innerHTML = '<p class="muted">Викладачів ще немає</p>'; return; }
  el.innerHTML = state.teachers.map(t => `
    <div class="item-card">
      <div class="item-card-header">
        <div class="item-card-title">👨‍🏫 ${t.name}</div>
        <div class="item-card-actions">
          <button class="btn btn-danger btn-sm" onclick="deleteTeacher(${t.id})">Видалити</button>
        </div>
      </div>
      <div class="item-card-meta">
        <div>🏛 ${t.department}</div>
        <div>📚 ${t.subjects.length ? t.subjects.join(', ') : 'усі дисципліни'}</div>
      </div>
    </div>`).join('');
}

function openTeacherModal() {
  document.getElementById('teacher-id').value = '';
  document.getElementById('teacher-name').value = '';
  document.getElementById('teacher-dept').value = '';
  document.getElementById('teacher-subjects').value = '';
  openModal('modal-teacher');
}

async function saveTeacher() {
  const data = {
    id: document.getElementById('teacher-id').value || null,
    name: document.getElementById('teacher-name').value,
    department: document.getElementById('teacher-dept').value,
    subjects: document.getElementById('teacher-subjects').value.split(',').map(s => s.trim()).filter(Boolean)
  };
  if (!data.name || !data.department) { toast('Заповніть усі поля', 'error'); return; }
  const res = data.id
    ? await api(`/api/teachers/${data.id}`, 'PUT', data)
    : await api('/api/teachers', 'POST', data);
  if (res.success) {
    toast('Збережено ✓', 'success');
    closeModal('modal-teacher');
    const r = await api('/api/teachers');
    state.teachers = r.data;
    renderTeachers();
    populateFilterSelects();
  } else toast(res.message, 'error');
}

async function deleteTeacher(id) {
  if (!confirm('Видалити викладача?')) return;
  await api(`/api/teachers/${id}`, 'DELETE');
  const r = await api('/api/teachers');
  state.teachers = r.data;
  renderTeachers();
  toast('Видалено', 'success');
}

// ─── Rooms ───────────────────────────────────
function renderRooms() {
  const el = document.getElementById('rooms-list');
  if (!state.rooms.length) { el.innerHTML = '<p class="muted">Аудиторій ще немає</p>'; return; }
  el.innerHTML = state.rooms.map(r => `
    <div class="item-card">
      <div class="item-card-header">
        <div class="item-card-title">🏛 Ауд. ${r.number}</div>
        <div class="item-card-actions">
          <button class="btn btn-danger btn-sm" onclick="deleteRoom(${r.id})">Видалити</button>
        </div>
      </div>
      <div class="item-card-meta">
        <div>👥 Місткість: ${r.capacity} осіб</div>
        <div>${tag(r.room_type_label, 'blue')}</div>
      </div>
    </div>`).join('');
}

function openRoomModal() { openModal('modal-room'); }

async function saveRoom() {
  const data = {
    number: document.getElementById('room-number').value,
    capacity: document.getElementById('room-capacity').value,
    room_type: document.getElementById('room-type').value
  };
  if (!data.number || !data.capacity) { toast('Заповніть усі поля', 'error'); return; }
  const res = await api('/api/rooms', 'POST', data);
  if (res.success) {
    toast('Аудиторію додано ✓', 'success');
    closeModal('modal-room');
    const r = await api('/api/rooms'); state.rooms = r.data;
    renderRooms();
  } else toast(res.message, 'error');
}

async function deleteRoom(id) {
  if (!confirm('Видалити аудиторію?')) return;
  await api(`/api/rooms/${id}`, 'DELETE');
  const r = await api('/api/rooms'); state.rooms = r.data;
  renderRooms();
}

// ─── Groups ──────────────────────────────────
function renderGroups() {
  const el = document.getElementById('groups-list');
  if (!state.groups.length) { el.innerHTML = '<p class="muted">Груп ще немає</p>'; return; }
  el.innerHTML = state.groups.map(g => `
    <div class="item-card">
      <div class="item-card-header">
        <div class="item-card-title">👥 ${g.name}</div>
        <div class="item-card-actions">
          <button class="btn btn-danger btn-sm" onclick="deleteGroup(${g.id})">Видалити</button>
        </div>
      </div>
      <div class="item-card-meta">
        <div>🎓 ${g.specialty}, ${g.year} курс</div>
        <div>👤 ${g.size} студентів</div>
      </div>
    </div>`).join('');
}

function openGroupModal() { openModal('modal-group'); }

async function saveGroup() {
  const data = {
    name: document.getElementById('group-name').value,
    size: document.getElementById('group-size').value,
    year: document.getElementById('group-year').value,
    specialty: document.getElementById('group-specialty').value
  };
  if (!data.name || !data.size || !data.year || !data.specialty) { toast('Заповніть усі поля', 'error'); return; }
  const res = await api('/api/groups', 'POST', data);
  if (res.success) {
    toast('Групу додано ✓', 'success');
    closeModal('modal-group');
    const r = await api('/api/groups'); state.groups = r.data;
    renderGroups();
    populateFilterSelects();
  } else toast(res.message, 'error');
}

async function deleteGroup(id) {
  if (!confirm('Видалити групу?')) return;
  await api(`/api/groups/${id}`, 'DELETE');
  const r = await api('/api/groups'); state.groups = r.data;
  renderGroups();
}

// ─── Subjects ────────────────────────────────
function renderSubjects() {
  const el = document.getElementById('subjects-list');
  if (!state.subjects.length) { el.innerHTML = '<p class="muted">Дисциплін ще немає</p>'; return; }
  const typeColor = { LECTURE:'blue', PRACTICE:'green', LAB:'orange', SEMINAR:'purple' };
  el.innerHTML = state.subjects.map(s => `
    <div class="item-card">
      <div class="item-card-header">
        <div class="item-card-title">📚 ${s.name}</div>
        <div class="item-card-actions">
          <button class="btn btn-danger btn-sm" onclick="deleteSubject(${s.id})">Видалити</button>
        </div>
      </div>
      <div class="item-card-meta">
        <div>⏱ ${s.hours_per_week} год/тиж</div>
        <div>${tag(s.lesson_type_label, typeColor[s.lesson_type] || 'blue')}</div>
      </div>
    </div>`).join('');
}

function openSubjectModal() { openModal('modal-subject'); }

async function saveSubject() {
  const data = {
    name: document.getElementById('subject-name').value,
    hours_per_week: document.getElementById('subject-hours').value,
    lesson_type: document.getElementById('subject-type').value
  };
  if (!data.name) { toast('Введіть назву', 'error'); return; }
  const res = await api('/api/subjects', 'POST', data);
  if (res.success) {
    toast('Дисципліну додано ✓', 'success');
    closeModal('modal-subject');
    const r = await api('/api/subjects'); state.subjects = r.data;
    renderSubjects();
  } else toast(res.message, 'error');
}

async function deleteSubject(id) {
  if (!confirm('Видалити дисципліну?')) return;
  await api(`/api/subjects/${id}`, 'DELETE');
  const r = await api('/api/subjects'); state.subjects = r.data;
  renderSubjects();
}

// ─── Lessons ─────────────────────────────────
function fillSelects(prefix) {
  const selectors = { subject: 'subjects', teacher: 'teachers', group: 'groups', room: 'rooms' };
  const labels    = { subject: s => s.name, teacher: t => t.name, group: g => g.name, room: r => `${r.number} (${r.capacity} м.)` };
  for (const [field, stateKey] of Object.entries(selectors)) {
    const el = document.getElementById(`${prefix}-${field}`);
    el.innerHTML = state[stateKey].map(item =>
      `<option value="${item.id}">${labels[field](item)}</option>`
    ).join('');
  }
}

function openLessonModal() {
  fillSelects('lesson');
  openModal('modal-lesson');
}

async function saveLesson() {
  const data = {
    subject_id:  document.getElementById('lesson-subject').value,
    teacher_id:  document.getElementById('lesson-teacher').value,
    group_id:    document.getElementById('lesson-group').value,
    room_id:     document.getElementById('lesson-room').value,
    day_index:   document.getElementById('lesson-day').value,
    slot_number: document.getElementById('lesson-slot').value
  };
  const res = await api('/api/lessons', 'POST', data);
  if (res.success) {
    toast('Заняття додано ✓', 'success');
    closeModal('modal-lesson');
    await refreshLessons();
    loadScheduleView();
    loadDashboard();
  } else toast(res.message, 'error');
}

function openAutoModal() {
  fillSelects('auto');
  openModal('modal-auto');
}

async function autoSchedule() {
  const data = {
    subject_id: document.getElementById('auto-subject').value,
    teacher_id: document.getElementById('auto-teacher').value,
    group_id:   document.getElementById('auto-group').value,
    room_id:    document.getElementById('auto-room').value,
    strategy:   document.getElementById('auto-strategy').value
  };
  const res = await api('/api/lessons/auto', 'POST', data);
  if (res.success) {
    toast(`✅ ${res.message}`, 'success');
    closeModal('modal-auto');
    await refreshLessons();
    loadScheduleView();
    loadDashboard();
  } else toast(res.message, 'error');
}

async function deleteLesson(id) {
  if (!confirm('Видалити це заняття?')) return;
  await api(`/api/lessons/${id}`, 'DELETE');
  await refreshLessons();
  loadScheduleView();
  loadDashboard();
  toast('Видалено', 'success');
}

async function clearSchedule() {
  if (!confirm('Очистити весь розклад?')) return;
  await api('/api/lessons/clear', 'DELETE');
  await refreshLessons();
  loadScheduleView();
  loadDashboard();
  toast('Розклад очищено', 'success');
}

async function refreshLessons() {
  const r = await api('/api/lessons');
  state.lessons = r.data || [];
}

// ─── Boot ────────────────────────────────────
bootstrap();
