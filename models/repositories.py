"""
Шар доступу до даних — патерн Repository.
Використовує SQLite для зберігання даних.
"""

import sqlite3
import json
from datetime import time
from contextlib import contextmanager
from models.entities import (
    Teacher, Room, Group, Subject, Lesson, TimeSlot,
    DayOfWeek, LessonType, RoomType
)


DB_PATH = "schedule.db"


# Контекстний менеджер з'єднання

@contextmanager
def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


# Ініціалізація схеми БД

def init_db():
    with get_connection() as conn:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS teachers (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            name      TEXT NOT NULL,
            department TEXT NOT NULL,
            subjects  TEXT NOT NULL DEFAULT '[]'
        );

        CREATE TABLE IF NOT EXISTS rooms (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            number    TEXT NOT NULL UNIQUE,
            capacity  INTEGER NOT NULL,
            room_type TEXT NOT NULL,
            equipment TEXT NOT NULL DEFAULT '[]'
        );

        CREATE TABLE IF NOT EXISTS groups (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            name      TEXT NOT NULL UNIQUE,
            size      INTEGER NOT NULL,
            year      INTEGER NOT NULL,
            specialty TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS subjects (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            name           TEXT NOT NULL,
            hours_per_week INTEGER NOT NULL DEFAULT 2,
            lesson_type    TEXT NOT NULL,
            required_equipment TEXT NOT NULL DEFAULT '[]'
        );

        CREATE TABLE IF NOT EXISTS lessons (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            subject_id INTEGER NOT NULL REFERENCES subjects(id) ON DELETE CASCADE,
            teacher_id INTEGER NOT NULL REFERENCES teachers(id) ON DELETE CASCADE,
            group_id   INTEGER NOT NULL REFERENCES groups(id)   ON DELETE CASCADE,
            room_id    INTEGER NOT NULL REFERENCES rooms(id)    ON DELETE CASCADE,
            day_index  INTEGER NOT NULL,
            slot_number INTEGER NOT NULL,
            UNIQUE(teacher_id, day_index, slot_number),
            UNIQUE(room_id,    day_index, slot_number),
            UNIQUE(group_id,   day_index, slot_number)
        );
        """)


# Repository: Teachers

class TeacherRepository:
    def get_all(self) -> list[Teacher]:
        with get_connection() as conn:
            rows = conn.execute("SELECT * FROM teachers ORDER BY name").fetchall()
        return [self._row_to_entity(r) for r in rows]

    def get_by_id(self, tid: int) -> Teacher | None:
        with get_connection() as conn:
            row = conn.execute("SELECT * FROM teachers WHERE id=?", (tid,)).fetchone()
        return self._row_to_entity(row) if row else None

    def save(self, t: Teacher) -> Teacher:
        subjects_json = json.dumps(t.subjects, ensure_ascii=False)
        with get_connection() as conn:
            if t.id is None:
                cur = conn.execute(
                    "INSERT INTO teachers(name,department,subjects) VALUES(?,?,?)",
                    (t.name, t.department, subjects_json)
                )
                t.id = cur.lastrowid
            else:
                conn.execute(
                    "UPDATE teachers SET name=?,department=?,subjects=? WHERE id=?",
                    (t.name, t.department, subjects_json, t.id)
                )
        return t

    def delete(self, tid: int):
        with get_connection() as conn:
            conn.execute("DELETE FROM teachers WHERE id=?", (tid,))

    @staticmethod
    def _row_to_entity(row) -> Teacher:
        return Teacher(
            id=row["id"],
            name=row["name"],
            department=row["department"],
            subjects=json.loads(row["subjects"])
        )


# Repository: Rooms

class RoomRepository:
    def get_all(self) -> list[Room]:
        with get_connection() as conn:
            rows = conn.execute("SELECT * FROM rooms ORDER BY number").fetchall()
        return [self._row_to_entity(r) for r in rows]

    def get_by_id(self, rid: int) -> Room | None:
        with get_connection() as conn:
            row = conn.execute("SELECT * FROM rooms WHERE id=?", (rid,)).fetchone()
        return self._row_to_entity(row) if row else None

    def save(self, r: Room) -> Room:
        eq_json = json.dumps(r.equipment, ensure_ascii=False)
        with get_connection() as conn:
            if r.id is None:
                cur = conn.execute(
                    "INSERT INTO rooms(number,capacity,room_type,equipment) VALUES(?,?,?,?)",
                    (r.number, r.capacity, r.room_type.name, eq_json)
                )
                r.id = cur.lastrowid
            else:
                conn.execute(
                    "UPDATE rooms SET number=?,capacity=?,room_type=?,equipment=? WHERE id=?",
                    (r.number, r.capacity, r.room_type.name, eq_json, r.id)
                )
        return r

    def delete(self, rid: int):
        with get_connection() as conn:
            conn.execute("DELETE FROM rooms WHERE id=?", (rid,))

    @staticmethod
    def _row_to_entity(row) -> Room:
        return Room(
            id=row["id"],
            number=row["number"],
            capacity=row["capacity"],
            room_type=RoomType[row["room_type"]],
            equipment=json.loads(row["equipment"])
        )


# Repository: Groups

class GroupRepository:
    def get_all(self) -> list[Group]:
        with get_connection() as conn:
            rows = conn.execute("SELECT * FROM groups ORDER BY name").fetchall()
        return [self._row_to_entity(r) for r in rows]

    def get_by_id(self, gid: int) -> Group | None:
        with get_connection() as conn:
            row = conn.execute("SELECT * FROM groups WHERE id=?", (gid,)).fetchone()
        return self._row_to_entity(row) if row else None

    def save(self, g: Group) -> Group:
        with get_connection() as conn:
            if g.id is None:
                cur = conn.execute(
                    "INSERT INTO groups(name,size,year,specialty) VALUES(?,?,?,?)",
                    (g.name, g.size, g.year, g.specialty)
                )
                g.id = cur.lastrowid
            else:
                conn.execute(
                    "UPDATE groups SET name=?,size=?,year=?,specialty=? WHERE id=?",
                    (g.name, g.size, g.year, g.specialty, g.id)
                )
        return g

    def delete(self, gid: int):
        with get_connection() as conn:
            conn.execute("DELETE FROM groups WHERE id=?", (gid,))

    @staticmethod
    def _row_to_entity(row) -> Group:
        return Group(
            id=row["id"],
            name=row["name"],
            size=row["size"],
            year=row["year"],
            specialty=row["specialty"]
        )


# Repository: Subjects

class SubjectRepository:
    def get_all(self) -> list[Subject]:
        with get_connection() as conn:
            rows = conn.execute("SELECT * FROM subjects ORDER BY name").fetchall()
        return [self._row_to_entity(r) for r in rows]

    def get_by_id(self, sid: int) -> Subject | None:
        with get_connection() as conn:
            row = conn.execute("SELECT * FROM subjects WHERE id=?", (sid,)).fetchone()
        return self._row_to_entity(row) if row else None

    def save(self, s: Subject) -> Subject:
        eq_json = json.dumps(s.required_equipment, ensure_ascii=False)
        with get_connection() as conn:
            if s.id is None:
                cur = conn.execute(
                    "INSERT INTO subjects(name,hours_per_week,lesson_type,required_equipment) VALUES(?,?,?,?)",
                    (s.name, s.hours_per_week, s.lesson_type.name, eq_json)
                )
                s.id = cur.lastrowid
            else:
                conn.execute(
                    "UPDATE subjects SET name=?,hours_per_week=?,lesson_type=?,required_equipment=? WHERE id=?",
                    (s.name, s.hours_per_week, s.lesson_type.name, eq_json, s.id)
                )
        return s

    def delete(self, sid: int):
        with get_connection() as conn:
            conn.execute("DELETE FROM subjects WHERE id=?", (sid,))

    @staticmethod
    def _row_to_entity(row) -> Subject:
        return Subject(
            id=row["id"],
            name=row["name"],
            hours_per_week=row["hours_per_week"],
            lesson_type=LessonType[row["lesson_type"]],
            required_equipment=json.loads(row["required_equipment"])
        )


# Repository: Lessons

class LessonRepository:
    def __init__(self):
        self._teacher_repo = TeacherRepository()
        self._room_repo = RoomRepository()
        self._group_repo = GroupRepository()
        self._subject_repo = SubjectRepository()
        self._slots_map = {
            (s.day.index, s.slot_number): s
            for s in TimeSlot.all_slots()
        }

    def get_all(self) -> list[Lesson]:
        with get_connection() as conn:
            rows = conn.execute("SELECT * FROM lessons").fetchall()
        return [self._row_to_entity(r) for r in rows]

    def get_by_group(self, group_id: int) -> list[Lesson]:
        with get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM lessons WHERE group_id=?", (group_id,)
            ).fetchall()
        return [self._row_to_entity(r) for r in rows]

    def get_by_teacher(self, teacher_id: int) -> list[Lesson]:
        with get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM lessons WHERE teacher_id=?", (teacher_id,)
            ).fetchall()
        return [self._row_to_entity(r) for r in rows]

    def save(self, lesson: Lesson) -> Lesson:
        with get_connection() as conn:
            if lesson.id is None:
                cur = conn.execute(
                    """INSERT INTO lessons
                       (subject_id,teacher_id,group_id,room_id,day_index,slot_number)
                       VALUES(?,?,?,?,?,?)""",
                    (lesson.subject.id, lesson.teacher.id, lesson.group.id,
                     lesson.room.id, lesson.time_slot.day.index,
                     lesson.time_slot.slot_number)
                )
                lesson.id = cur.lastrowid
            else:
                conn.execute(
                    """UPDATE lessons SET subject_id=?,teacher_id=?,group_id=?,
                       room_id=?,day_index=?,slot_number=? WHERE id=?""",
                    (lesson.subject.id, lesson.teacher.id, lesson.group.id,
                     lesson.room.id, lesson.time_slot.day.index,
                     lesson.time_slot.slot_number, lesson.id)
                )
        return lesson

    def delete(self, lesson_id: int):
        with get_connection() as conn:
            conn.execute("DELETE FROM lessons WHERE id=?", (lesson_id,))

    def clear_all(self):
        with get_connection() as conn:
            conn.execute("DELETE FROM lessons")

    def _row_to_entity(self, row) -> Lesson:
        slot_key = (row["day_index"], row["slot_number"])
        return Lesson(
            id=row["id"],
            subject=self._subject_repo.get_by_id(row["subject_id"]),
            teacher=self._teacher_repo.get_by_id(row["teacher_id"]),
            group=self._group_repo.get_by_id(row["group_id"]),
            room=self._room_repo.get_by_id(row["room_id"]),
            time_slot=self._slots_map[slot_key]
        )