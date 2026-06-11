"""
Скрипт заповнення демонстраційними даними.
Запустіть: python seed_data.py
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from models.repositories import init_db
from services.schedule_service import ScheduleService

def seed():
    init_db()
    svc = ScheduleService()

    print("🌱 Заповнення демо-даними...")

    # ── Викладачі ──────────────────────────────────────────────
    teachers_data = [
        {"name": "Іваненко Петро Сергійович",  "department": "Кафедра інформатики",       "subjects": ["Алгоритми", "Структури даних"]},
        {"name": "Коваленко Марія Іванівна",    "department": "Кафедра математики",         "subjects": ["Вища математика", "Лінійна алгебра"]},
        {"name": "Шевченко Олег Вікторович",    "department": "Кафедра програмування",      "subjects": ["Python", "Java", "Рефакторинг коду"]},
        {"name": "Бондаренко Ірина Юріївна",    "department": "Кафедра баз даних",          "subjects": ["Бази даних", "SQL"]},
        {"name": "Мельник Андрій Олександрович","department": "Кафедра мережевих технологій","subjects": ["Комп'ютерні мережі", "Кібербезпека"]},
    ]
    teacher_ids = []
    for td in teachers_data:
        t = svc.save_teacher(td)
        teacher_ids.append(t.id)
        print(f"  ✓ Викладач: {t.name}")

    # ── Аудиторії ──────────────────────────────────────────────
    rooms_data = [
        {"number": "101", "capacity": 120, "room_type": "LECTURE_HALL"},
        {"number": "202", "capacity": 80,  "room_type": "LECTURE_HALL"},
        {"number": "305", "capacity": 30,  "room_type": "COMPUTER_LAB"},
        {"number": "306", "capacity": 25,  "room_type": "COMPUTER_LAB"},
        {"number": "410", "capacity": 35,  "room_type": "SEMINAR_ROOM"},
        {"number": "411", "capacity": 30,  "room_type": "LABORATORY"},
    ]
    room_ids = []
    for rd in rooms_data:
        r = svc.save_room(rd)
        room_ids.append(r.id)
        print(f"  ✓ Аудиторія: {r.number}")

    # ── Групи ──────────────────────────────────────────────────
    groups_data = [
        {"name": "КН-21", "size": 25, "year": 2, "specialty": "Комп'ютерні науки"},
        {"name": "КН-22", "size": 28, "year": 2, "specialty": "Комп'ютерні науки"},
        {"name": "ІТ-31", "size": 22, "year": 3, "specialty": "Інформаційні технології"},
        {"name": "ПЗ-41", "size": 20, "year": 4, "specialty": "Програмна інженерія"},
    ]
    group_ids = []
    for gd in groups_data:
        g = svc.save_group(gd)
        group_ids.append(g.id)
        print(f"  ✓ Група: {g.name}")

    # ── Дисципліни ─────────────────────────────────────────────
    subjects_data = [
        {"name": "Алгоритми",        "hours_per_week": 2, "lesson_type": "LECTURE"},
        {"name": "Структури даних",  "hours_per_week": 2, "lesson_type": "PRACTICE"},
        {"name": "Вища математика",  "hours_per_week": 4, "lesson_type": "LECTURE"},
        {"name": "Python",           "hours_per_week": 2, "lesson_type": "LAB"},
        {"name": "Рефакторинг коду", "hours_per_week": 2, "lesson_type": "PRACTICE"},
        {"name": "Бази даних",       "hours_per_week": 2, "lesson_type": "LAB"},
    ]
    subject_ids = []
    for sd in subjects_data:
        s = svc.save_subject(sd)
        subject_ids.append(s.id)
        print(f"  ✓ Дисципліна: {s.name}")

    # ── Розклад (авто-підбір) ──────────────────────────────────
    print("\n📅 Генерація розкладу (Strategy: balanced)...")
    schedule_plan = [
        # subject_idx, teacher_idx, group_idx, room_idx
        (0, 0, 0, 0),   # Алгоритми — КН-21 — лекційна 101
        (1, 0, 0, 4),   # Структури даних — КН-21 — семінарська 410
        (2, 1, 1, 1),   # Вища математика — КН-22 — лекційна 202
        (3, 2, 2, 2),   # Python — ІТ-31 — комп. лаб 305
        (4, 2, 3, 4),   # Рефакторинг — ПЗ-41 — семінарська 410
        (5, 3, 0, 3),   # Бази даних — КН-21 — комп. лаб 306
        (0, 0, 1, 0),   # Алгоритми — КН-22
        (3, 2, 3, 2),   # Python — ПЗ-41
    ]

    for (si, ti, gi, ri) in schedule_plan:
        ok, msg, lesson = svc.auto_schedule(
            subject_id=subject_ids[si],
            teacher_id=teacher_ids[ti],
            group_id=group_ids[gi],
            room_id=room_ids[ri],
            strategy_name="balanced"
        )
        status = "✓" if ok else "✗"
        lname = subjects_data[si]["name"]
        gname = groups_data[gi]["name"]
        print(f"  {status} {lname} / {gname}: {msg}")

    print("\n✅ Демо-дані успішно завантажено!")
    print("   Запустіть: python app.py")

if __name__ == "__main__":
    seed()
