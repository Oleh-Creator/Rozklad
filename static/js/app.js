/* ═══════════════════════════════════════════
   Система управління розкладом — JS клієнт
   ═══════════════════════════════════════════ */



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

// Екранування HTML — захист від XSS (S5696)
// Використовуємо replaceAll замість innerHTML для уникнення false-positive
function esc(str) {
  return String(str ?? '')
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#x27;');
}

// Безпечне створення <option> елементів через DOM API
function makeOption(value, label, selected = false) {
  const opt = document.createElement('option');
  opt.value = value;
  opt.textContent = label;
  if (selected) opt.selected = true;
  return opt;
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
  const span = document.createElement('span');
  span.className = `tag tag-${esc(cls)}`;
  span.textContent = text;
  return span.outerHTML;
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
  await loadDashboard();
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

  // conflicts — безпечне DOM-будування
  const clist = document.getElementById('conflict-list');
  clist.textContent = '';
  const cr = await api('/api/conflicts');
  if (cr.data?.length) {
    cr.data.forEach(c => {
      const div = document.createElement('div');
      div.className = 'conflict-item';
      div.textContent = '⚠ ' + c;
      clist.appendChild(div);
    });
  } else {
    const p = document.createElement('p');
    p.className = 'muted';
    p.textContent = '✅ Конфліктів немає';
    clist.appendChild(p);
  }

  // teacher load — безпечне DOM-будування
  const tl = document.getElementById('teacher-load');
  tl.textContent = '';
  const load = st.teacher_load || {};
  const maxLoad = Math.max(...Object.values(load), 1);
  if (Object.keys(load).length === 0) {
    const p = document.createElement('p');
    p.className = 'muted';
    p.textContent = 'Немає даних';
    tl.appendChild(p);
  } else {
    Object.entries(load).forEach(([name, cnt]) => {
      const item = document.createElement('div');
      item.className = 'load-item';

      const left = document.createElement('div');
      const nameDiv = document.createElement('div');
      nameDiv.textContent = name;
      const bar = document.createElement('div');
      bar.className = 'load-bar';
      bar.style.width = `${(cnt / maxLoad) * 120}px`;
      left.appendChild(nameDiv);
      left.appendChild(bar);

      const right = document.createElement('strong');
      right.textContent = `${cnt} пар`;

      item.appendChild(left);
      item.appendChild(right);
      tl.appendChild(item);
    });
  }
}

// ─── Schedule view (timetable) ───────────────

// Безпечне заповнення <select> через DOM API — захист від XSS
function populateFilterSelects() {
  const fg = document.getElementById('filter-group');
  const ft = document.getElementById('filter-teacher');

  fg.textContent = '';
  fg.appendChild(makeOption('', 'Усі групи'));
  state.groups.forEach(g => fg.appendChild(makeOption(g.id, g.name)));

  ft.textContent = '';
  ft.appendChild(makeOption('', 'Усі викладачі'));
  state.teachers.forEach(t => ft.appendChild(makeOption(t.id, t.name)));
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

const DAYS  = ['Понеділок','Вівторок','Середа','Четвер','П\'ятниця','Субота'];
const SLOTS = [
  ['1','08:00–09:35'], ['2','09:45–11:20'], ['3','11:30–13:05'],
  ['4','13:30–15:05'], ['5','15:15–16:50'], ['6','17:00–18:35']
];

function renderTimetable(lessons) {
  const table = {};
  for (let d = 0; d < 6; d++) {
    table[d] = {};
    for (let s = 1; s <= 6; s++) table[d][s] = [];
  }
  lessons.forEach(l => {
    if (table[l.day_index]?.[l.slot])
      table[l.day_index][l.slot].push(l);
  });

  const typeColorMap = {
    'Лекція': 'LECTURE', 'Практика': 'PRACTICE',
    'Лабораторна': 'LAB', 'Семінар': 'SEMINAR'
  };

  // Будуємо таблицю через DOM API — без innerHTML з даними користувача
  const tbl = document.createElement('table');
  tbl.className = 'timetable';

  // Заголовок
  const thead = document.createElement('thead');
  const headRow = document.createElement('tr');
  const thFirst = document.createElement('th');
  thFirst.textContent = 'Пара / Час';
  headRow.appendChild(thFirst);
  DAYS.forEach(d => {
    const th = document.createElement('th');
    th.textContent = d;
    headRow.appendChild(th);
  });
  thead.appendChild(headRow);
  tbl.appendChild(thead);

  // Тіло
  const tbody = document.createElement('tbody');
  SLOTS.forEach(([slotNum, time]) => {
    const tr = document.createElement('tr');

    const tdLabel = document.createElement('td');
    tdLabel.className = 'slot-label';
    const strong = document.createElement('strong');
    strong.textContent = slotNum;
    const small = document.createElement('small');
    small.textContent = time;
    tdLabel.appendChild(strong);
    tdLabel.appendChild(document.createElement('br'));
    tdLabel.appendChild(small);
    tr.appendChild(tdLabel);

    for (let d = 0; d < 6; d++) {
      const td = document.createElement('td');
      const cells = table[d][Number.parseInt(slotNum, 10)];
      cells.forEach(l => {
        const tc = typeColorMap[l.lesson_type] || 'LECTURE';
        const cell = document.createElement('div');
        cell.className = `lesson-cell lesson-type-${tc}`;

        const delBtn = document.createElement('button');
        delBtn.className = 'lc-delete';
        delBtn.title = 'Видалити';
        delBtn.textContent = '✕';
        delBtn.addEventListener('click', () => deleteLesson(l.id));

        const subjectDiv = document.createElement('div');
        subjectDiv.className = 'lc-subject';
        subjectDiv.textContent = l.subject;

        const teacherDiv = document.createElement('div');
        teacherDiv.className = 'lc-meta';
        teacherDiv.textContent = '👨‍🏫 ' + l.teacher;

        const groupDiv = document.createElement('div');
        groupDiv.className = 'lc-meta';
        groupDiv.textContent = '👥 ' + l.group;

        const roomDiv = document.createElement('div');
        roomDiv.className = 'lc-meta';
        roomDiv.textContent = '🏛 ауд.' + l.room;

        const typeSpan = document.createElement('div');
        typeSpan.className = 'lc-meta';
        const span = document.createElement('span');
        span.className = 'tag tag-blue';
        span.textContent = l.lesson_type;
        typeSpan.appendChild(span);

        cell.appendChild(delBtn);
        cell.appendChild(subjectDiv);
        cell.appendChild(teacherDiv);
        cell.appendChild(groupDiv);
        cell.appendChild(roomDiv);
        cell.appendChild(typeSpan);
        td.appendChild(cell);
      });
      tr.appendChild(td);
    }
    tbody.appendChild(tr);
  });
  tbl.appendChild(tbody);

  const grid = document.getElementById('schedule-grid');
  grid.textContent = '';
  grid.appendChild(tbl);
}

// ─── Teachers ────────────────────────────────
function renderTeachers() {
  const el = document.getElementById('teachers-list');
  el.textContent = '';
  if (!state.teachers.length) {
    const p = document.createElement('p');
    p.className = 'muted';
    p.textContent = 'Викладачів ще немає';
    el.appendChild(p);
    return;
  }
  state.teachers.forEach(t => {
    const card = document.createElement('div');
    card.className = 'item-card';

    const header = document.createElement('div');
    header.className = 'item-card-header';

    const title = document.createElement('div');
    title.className = 'item-card-title';
    title.textContent = '👨‍🏫 ' + t.name;

    const actions = document.createElement('div');
    actions.className = 'item-card-actions';
    const delBtn = document.createElement('button');
    delBtn.className = 'btn btn-danger btn-sm';
    delBtn.textContent = 'Видалити';
    delBtn.addEventListener('click', () => deleteTeacher(t.id));
    actions.appendChild(delBtn);

    header.appendChild(title);
    header.appendChild(actions);

    const meta = document.createElement('div');
    meta.className = 'item-card-meta';
    const deptLine = document.createElement('div');
    deptLine.textContent = '🏛 ' + t.department;
    const subjLine = document.createElement('div');
    subjLine.textContent = '📚 ' + (t.subjects.length ? t.subjects.join(', ') : 'усі дисципліни');
    meta.appendChild(deptLine);
    meta.appendChild(subjLine);

    card.appendChild(header);
    card.appendChild(meta);
    el.appendChild(card);
  });
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
  el.textContent = '';
  if (!state.rooms.length) {
    const p = document.createElement('p');
    p.className = 'muted';
    p.textContent = 'Аудиторій ще немає';
    el.appendChild(p);
    return;
  }
  state.rooms.forEach(r => {
    const card = document.createElement('div');
    card.className = 'item-card';

    const header = document.createElement('div');
    header.className = 'item-card-header';

    const title = document.createElement('div');
    title.className = 'item-card-title';
    title.textContent = '🏛 Ауд. ' + r.number;

    const actions = document.createElement('div');
    actions.className = 'item-card-actions';
    const delBtn = document.createElement('button');
    delBtn.className = 'btn btn-danger btn-sm';
    delBtn.textContent = 'Видалити';
    delBtn.addEventListener('click', () => deleteRoom(r.id));
    actions.appendChild(delBtn);

    header.appendChild(title);
    header.appendChild(actions);

    const meta = document.createElement('div');
    meta.className = 'item-card-meta';
    const capLine = document.createElement('div');
    capLine.textContent = '👥 Місткість: ' + r.capacity + ' осіб';
    const typeSpan = document.createElement('span');
    typeSpan.className = 'tag tag-blue';
    typeSpan.textContent = r.room_type_label;
    meta.appendChild(capLine);
    meta.appendChild(typeSpan);

    card.appendChild(header);
    card.appendChild(meta);
    el.appendChild(card);
  });
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
  el.textContent = '';
  if (!state.groups.length) {
    const p = document.createElement('p');
    p.className = 'muted';
    p.textContent = 'Груп ще немає';
    el.appendChild(p);
    return;
  }
  state.groups.forEach(g => {
    const card = document.createElement('div');
    card.className = 'item-card';

    const header = document.createElement('div');
    header.className = 'item-card-header';

    const title = document.createElement('div');
    title.className = 'item-card-title';
    title.textContent = '👥 ' + g.name;

    const actions = document.createElement('div');
    actions.className = 'item-card-actions';
    const delBtn = document.createElement('button');
    delBtn.className = 'btn btn-danger btn-sm';
    delBtn.textContent = 'Видалити';
    delBtn.addEventListener('click', () => deleteGroup(g.id));
    actions.appendChild(delBtn);

    header.appendChild(title);
    header.appendChild(actions);

    const meta = document.createElement('div');
    meta.className = 'item-card-meta';
    const specLine = document.createElement('div');
    specLine.textContent = `🎓 ${g.specialty}, ${g.year} курс`;
    const sizeLine = document.createElement('div');
    sizeLine.textContent = `👤 ${g.size} студентів`;
    meta.appendChild(specLine);
    meta.appendChild(sizeLine);

    card.appendChild(header);
    card.appendChild(meta);
    el.appendChild(card);
  });
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
  el.textContent = '';
  if (!state.subjects.length) {
    const p = document.createElement('p');
    p.className = 'muted';
    p.textContent = 'Дисциплін ще немає';
    el.appendChild(p);
    return;
  }
  const typeColor = { LECTURE:'blue', PRACTICE:'green', LAB:'orange', SEMINAR:'purple' };
  state.subjects.forEach(s => {
    const card = document.createElement('div');
    card.className = 'item-card';

    const header = document.createElement('div');
    header.className = 'item-card-header';

    const title = document.createElement('div');
    title.className = 'item-card-title';
    title.textContent = '📚 ' + s.name;

    const actions = document.createElement('div');
    actions.className = 'item-card-actions';
    const delBtn = document.createElement('button');
    delBtn.className = 'btn btn-danger btn-sm';
    delBtn.textContent = 'Видалити';
    delBtn.addEventListener('click', () => deleteSubject(s.id));
    actions.appendChild(delBtn);

    header.appendChild(title);
    header.appendChild(actions);

    const meta = document.createElement('div');
    meta.className = 'item-card-meta';
    const hoursLine = document.createElement('div');
    hoursLine.textContent = `⏱ ${s.hours_per_week} год/тиж`;
    const typeSpan = document.createElement('span');
    typeSpan.className = `tag tag-${typeColor[s.lesson_type] || 'blue'}`;
    typeSpan.textContent = s.lesson_type_label;
    meta.appendChild(hoursLine);
    meta.appendChild(typeSpan);

    card.appendChild(header);
    card.appendChild(meta);
    el.appendChild(card);
  });
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

// Безпечне заповнення <select> через DOM API
function fillSelects(prefix) {
  const cfg = {
    subject: { key: 'subjects', label: s => s.name },
    teacher: { key: 'teachers', label: t => t.name },
    group:   { key: 'groups',   label: g => g.name },
    room:    { key: 'rooms',    label: r => `${r.number} (${r.capacity} м.)` },
  };
  Object.entries(cfg).forEach(([field, { key, label }]) => {
    const el = document.getElementById(`${prefix}-${field}`);
    el.textContent = '';
    state[key].forEach(item => el.appendChild(makeOption(item.id, label(item))));
  });
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

bootstrap();

// Експортуємо функції в глобальний scope для onclick handlers
window.openModal          = openModal;
window.closeModal         = closeModal;
window.loadScheduleView   = loadScheduleView;
window.openLessonModal    = openLessonModal;
window.openAutoModal      = openAutoModal;
window.clearSchedule      = clearSchedule;
window.saveLesson         = saveLesson;
window.autoSchedule       = autoSchedule;
window.deleteLesson       = deleteLesson;
window.openTeacherModal   = openTeacherModal;
window.saveTeacher        = saveTeacher;
window.deleteTeacher      = deleteTeacher;
window.renderTeachers     = renderTeachers;
window.openRoomModal      = openRoomModal;
window.saveRoom           = saveRoom;
window.deleteRoom         = deleteRoom;
window.renderRooms        = renderRooms;
window.openGroupModal     = openGroupModal;
window.saveGroup          = saveGroup;
window.deleteGroup        = deleteGroup;
window.renderGroups       = renderGroups;
window.openSubjectModal   = openSubjectModal;
window.saveSubject        = saveSubject;
window.deleteSubject      = deleteSubject;
window.renderSubjects     = renderSubjects;