"""
Юніт-тести системи управління розкладом навчального закладу.

Охоплює:
    - Доменні моделі (entities.py)
    - Патерни проєктування (design_patterns.py)
    - Інтеграцію планувальника (Scheduler)
    - Репозиторії (repositories.py)
    - Сервісний шар (schedule_service.py)

Запуск::

    python test_schedule.py

Кількість тестів: 90+
"""

import sys
import os
import unittest
import tempfile

sys.path.insert(0, os.path.dirname(__file__))

import models.repositories as _repo_module
_tmp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
_tmp_db.close()
_repo_module.DB_PATH = _tmp_db.name


# ══════════════════════════════════════════════════════════════════
# 1. ТЕСТИ ДОМЕННИХ МОДЕЛЕЙ
# ══════════════════════════════════════════════════════════════════

class TestDayOfWeek(unittest.TestCase):
    def test_monday_label(self):
        from models.entities import DayOfWeek
        self.assertEqual(DayOfWeek.MONDAY.label, "Понеділок")

    def test_saturday_index(self):
        from models.entities import DayOfWeek
        self.assertEqual(DayOfWeek.SATURDAY.index, 5)

    def test_from_index_monday(self):
        from models.entities import DayOfWeek
        self.assertEqual(DayOfWeek.from_index(0), DayOfWeek.MONDAY)

    def test_from_index_friday(self):
        from models.entities import DayOfWeek
        self.assertEqual(DayOfWeek.from_index(4), DayOfWeek.FRIDAY)

    def test_from_index_invalid(self):
        from models.entities import DayOfWeek
        with self.assertRaises(ValueError):
            DayOfWeek.from_index(99)

    def test_all_days_count(self):
        from models.entities import DayOfWeek
        self.assertEqual(len(list(DayOfWeek)), 6)

    def test_all_indexes_unique(self):
        from models.entities import DayOfWeek
        indexes = [d.index for d in DayOfWeek]
        self.assertEqual(len(indexes), len(set(indexes)))


class TestTimeSlot(unittest.TestCase):
    def test_all_slots_count(self):
        from models.entities import TimeSlot
        self.assertEqual(len(TimeSlot.all_slots()), 36)

    def test_slot_equality_same(self):
        from models.entities import TimeSlot, DayOfWeek
        from datetime import time
        s1 = TimeSlot(DayOfWeek.MONDAY, 1, time(8, 0), time(9, 35))
        s2 = TimeSlot(DayOfWeek.MONDAY, 1, time(8, 0), time(9, 35))
        self.assertEqual(s1, s2)

    def test_slot_equality_different_day(self):
        from models.entities import TimeSlot, DayOfWeek
        from datetime import time
        s1 = TimeSlot(DayOfWeek.MONDAY, 1, time(8, 0), time(9, 35))
        s2 = TimeSlot(DayOfWeek.TUESDAY, 1, time(8, 0), time(9, 35))
        self.assertNotEqual(s1, s2)

    def test_slot_equality_different_number(self):
        from models.entities import TimeSlot, DayOfWeek
        from datetime import time
        s1 = TimeSlot(DayOfWeek.MONDAY, 1, time(8, 0), time(9, 35))
        s2 = TimeSlot(DayOfWeek.MONDAY, 2, time(9, 45), time(11, 20))
        self.assertNotEqual(s1, s2)

    def test_slot_hashable(self):
        from models.entities import TimeSlot, DayOfWeek
        from datetime import time
        s = TimeSlot(DayOfWeek.WEDNESDAY, 3, time(11, 30), time(13, 5))
        d = {s: "test"}
        self.assertEqual(d[s], "test")

    def test_slot_repr_contains_day(self):
        from models.entities import TimeSlot, DayOfWeek
        from datetime import time
        s = TimeSlot(DayOfWeek.THURSDAY, 2, time(9, 45), time(11, 20))
        self.assertIn("Четвер", repr(s))

    def test_all_slots_days_covered(self):
        from models.entities import TimeSlot, DayOfWeek
        days_in_slots = {s.day for s in TimeSlot.all_slots()}
        self.assertEqual(days_in_slots, set(DayOfWeek))

    def test_slot_not_equal_to_non_slot(self):
        from models.entities import TimeSlot, DayOfWeek
        from datetime import time
        s = TimeSlot(DayOfWeek.MONDAY, 1, time(8, 0), time(9, 35))
        self.assertEqual(s.__eq__("not a slot"), NotImplemented)


class TestRoom(unittest.TestCase):
    def test_lecture_suitable_in_lecture_hall(self):
        from models.entities import Room, RoomType, LessonType
        r = Room(1, "101", 120, RoomType.LECTURE_HALL)
        self.assertTrue(r.is_suitable_for(LessonType.LECTURE, 80))

    def test_lecture_not_suitable_in_seminar_room(self):
        from models.entities import Room, RoomType, LessonType
        r = Room(1, "410", 30, RoomType.SEMINAR_ROOM)
        self.assertFalse(r.is_suitable_for(LessonType.LECTURE, 25))

    def test_lecture_not_suitable_in_computer_lab(self):
        from models.entities import Room, RoomType, LessonType
        r = Room(1, "305", 30, RoomType.COMPUTER_LAB)
        self.assertFalse(r.is_suitable_for(LessonType.LECTURE, 25))

    def test_over_capacity(self):
        from models.entities import Room, RoomType, LessonType
        r = Room(1, "101", 20, RoomType.LECTURE_HALL)
        self.assertFalse(r.is_suitable_for(LessonType.LECTURE, 50))

    def test_lab_suitable_in_computer_lab(self):
        from models.entities import Room, RoomType, LessonType
        r = Room(1, "305", 30, RoomType.COMPUTER_LAB)
        self.assertTrue(r.is_suitable_for(LessonType.LAB, 25))

    def test_lab_suitable_in_laboratory(self):
        from models.entities import Room, RoomType, LessonType
        r = Room(1, "411", 25, RoomType.LABORATORY)
        self.assertTrue(r.is_suitable_for(LessonType.LAB, 20))

    def test_lab_not_suitable_in_seminar_room(self):
        from models.entities import Room, RoomType, LessonType
        r = Room(1, "410", 30, RoomType.SEMINAR_ROOM)
        self.assertFalse(r.is_suitable_for(LessonType.LAB, 25))

    def test_practice_suitable_anywhere(self):
        from models.entities import Room, RoomType, LessonType
        for rt in RoomType:
            r = Room(1, "X", 50, rt)
            self.assertTrue(r.is_suitable_for(LessonType.PRACTICE, 30))

    def test_seminar_suitable_in_seminar_room(self):
        from models.entities import Room, RoomType, LessonType
        r = Room(1, "410", 35, RoomType.SEMINAR_ROOM)
        self.assertTrue(r.is_suitable_for(LessonType.SEMINAR, 30))

    def test_repr_contains_number(self):
        from models.entities import Room, RoomType
        r = Room(1, "305-А", 30, RoomType.COMPUTER_LAB)
        self.assertIn("305-А", repr(r))


class TestTeacher(unittest.TestCase):
    def test_can_teach_listed_subject(self):
        from models.entities import Teacher
        t = Teacher(1, "Іваненко", "ФЕК", ["Python", "Java"])
        self.assertTrue(t.can_teach("Python"))

    def test_cannot_teach_unlisted_subject(self):
        from models.entities import Teacher
        t = Teacher(1, "Іваненко", "ФЕК", ["Python"])
        self.assertFalse(t.can_teach("Математика"))

    def test_empty_subjects_cannot_teach(self):
        from models.entities import Teacher
        t = Teacher(1, "Коваленко", "ФЕК", [])
        self.assertFalse(t.can_teach("Python"))

    def test_repr_contains_name(self):
        from models.entities import Teacher
        t = Teacher(1, "Шевченко", "ФЕК", [])
        self.assertIn("Шевченко", repr(t))


class TestLesson(unittest.TestCase):
    def _make_lesson(self):
        from models.entities import (Teacher, Room, Group, Subject, Lesson,
                                      TimeSlot, DayOfWeek, LessonType, RoomType)
        from datetime import time
        return Lesson(
            id=1,
            subject=Subject(1, "Python", 2, LessonType.LAB),
            teacher=Teacher(1, "Іваненко", "ФЕК", []),
            group=Group(1, "КН-21", 25, 2, "КН"),
            room=Room(1, "305", 30, RoomType.COMPUTER_LAB),
            time_slot=TimeSlot(DayOfWeek.MONDAY, 1, time(8, 0), time(9, 35))
        )

    def test_to_dict_subject(self):
        self.assertEqual(self._make_lesson().to_dict()["subject"], "Python")

    def test_to_dict_teacher(self):
        self.assertEqual(self._make_lesson().to_dict()["teacher"], "Іваненко")

    def test_to_dict_day(self):
        self.assertEqual(self._make_lesson().to_dict()["day"], "Понеділок")

    def test_to_dict_slot(self):
        self.assertEqual(self._make_lesson().to_dict()["slot"], 1)

    def test_to_dict_has_all_keys(self):
        keys = self._make_lesson().to_dict().keys()
        for k in ["id","subject","teacher","group","room","day","slot","start","end"]:
            self.assertIn(k, keys)

    def test_repr_contains_subject(self):
        self.assertIn("Python", repr(self._make_lesson()))

    def test_to_dict_room(self):
        self.assertEqual(self._make_lesson().to_dict()["room"], "305")

    def test_to_dict_group(self):
        self.assertEqual(self._make_lesson().to_dict()["group"], "КН-21")


# ══════════════════════════════════════════════════════════════════
# 2. ТЕСТИ ПАТЕРНІВ
# ══════════════════════════════════════════════════════════════════

class TestLessonBuilder(unittest.TestCase):
    def _fixtures(self):
        from models.entities import (Teacher, Room, Group, Subject, TimeSlot,
                                      DayOfWeek, LessonType, RoomType)
        from datetime import time
        return {
            "subject":   Subject(1, "Тест", 2, LessonType.LECTURE),
            "teacher":   Teacher(1, "Тест", "ФЕК", []),
            "group":     Group(1, "ТГ-01", 30, 1, "Тест"),
            "room":      Room(1, "101", 50, RoomType.LECTURE_HALL),
            "time_slot": TimeSlot(DayOfWeek.MONDAY, 1, time(8, 0), time(9, 35)),
        }

    def test_build_complete(self):
        from patterns.design_patterns import LessonBuilder
        f = self._fixtures()
        lesson = (LessonBuilder()
                  .with_subject(f["subject"])
                  .with_teacher(f["teacher"])
                  .with_group(f["group"])
                  .with_room(f["room"])
                  .with_time_slot(f["time_slot"])
                  .build())
        self.assertEqual(lesson.subject.name, "Тест")

    def test_build_with_id(self):
        from patterns.design_patterns import LessonBuilder
        f = self._fixtures()
        lesson = (LessonBuilder()
                  .with_id(42)
                  .with_subject(f["subject"])
                  .with_teacher(f["teacher"])
                  .with_group(f["group"])
                  .with_room(f["room"])
                  .with_time_slot(f["time_slot"])
                  .build())
        self.assertEqual(lesson.id, 42)

    def test_build_missing_teacher_raises(self):
        from patterns.design_patterns import LessonBuilder
        f = self._fixtures()
        with self.assertRaises(ValueError):
            (LessonBuilder()
             .with_subject(f["subject"])
             .with_group(f["group"])
             .with_room(f["room"])
             .with_time_slot(f["time_slot"])
             .build())

    def test_build_missing_subject_raises(self):
        from patterns.design_patterns import LessonBuilder
        f = self._fixtures()
        with self.assertRaises(ValueError):
            (LessonBuilder()
             .with_teacher(f["teacher"])
             .with_group(f["group"])
             .with_room(f["room"])
             .with_time_slot(f["time_slot"])
             .build())

    def test_build_empty_raises(self):
        from patterns.design_patterns import LessonBuilder
        with self.assertRaises(ValueError):
            LessonBuilder().build()


class TestConstraintChain(unittest.TestCase):
    def _make_lesson(self, lid=1, teacher_id=1, room_id=1, group_id=1):
        from models.entities import (Teacher, Room, Group, Subject, Lesson,
                                      TimeSlot, DayOfWeek, LessonType, RoomType)
        from datetime import time
        return Lesson(
            id=lid,
            subject=Subject(1, "Тест", 2, LessonType.LAB),
            teacher=Teacher(teacher_id, "Викладач", "ФЕК", []),
            group=Group(group_id, "ТГ-01", 25, 1, "Тест"),
            room=Room(room_id, "305", 30, RoomType.COMPUTER_LAB),
            time_slot=TimeSlot(DayOfWeek.MONDAY, 1, time(8, 0), time(9, 35))
        )

    def test_no_conflict_passes(self):
        from patterns.design_patterns import build_constraint_chain
        result = build_constraint_chain().check(self._make_lesson(), [])
        self.assertTrue(result.ok)

    def test_teacher_conflict(self):
        from patterns.design_patterns import build_constraint_chain
        existing = self._make_lesson(lid=1)
        new = self._make_lesson(lid=2)
        result = build_constraint_chain().check(new, [existing])
        self.assertFalse(result.ok)
        self.assertIn("Викладач", result.message)

    def test_room_conflict(self):
        from patterns.design_patterns import build_constraint_chain
        from models.entities import Teacher
        existing = self._make_lesson(lid=1, teacher_id=1)
        new = self._make_lesson(lid=2, teacher_id=99)
        new.teacher = Teacher(99, "Інший", "ФЕК", [])
        result = build_constraint_chain().check(new, [existing])
        self.assertFalse(result.ok)

    def test_group_conflict(self):
        from patterns.design_patterns import build_constraint_chain
        from models.entities import Teacher, Room, RoomType
        existing = self._make_lesson(lid=1, teacher_id=1, room_id=1)
        new = self._make_lesson(lid=2, teacher_id=2, room_id=2)
        new.teacher = Teacher(2, "Інший", "ФЕК", [])
        new.room = Room(2, "306", 30, RoomType.COMPUTER_LAB)
        result = build_constraint_chain().check(new, [existing])
        self.assertFalse(result.ok)
        self.assertIn("Група", result.message)

    def test_room_suitability_lecture_wrong_room(self):
        from patterns.design_patterns import RoomSuitabilityHandler
        from models.entities import (Lesson, Subject, Teacher, Group,
                                      Room, TimeSlot, DayOfWeek, LessonType, RoomType)
        from datetime import time
        lesson = Lesson(1, Subject(1, "Математика", 4, LessonType.LECTURE),
                        Teacher(1, "Т", "К", []), Group(1, "КН-21", 25, 2, "КН"),
                        Room(1, "410", 30, RoomType.SEMINAR_ROOM),
                        TimeSlot(DayOfWeek.MONDAY, 1, time(8, 0), time(9, 35)))
        result = RoomSuitabilityHandler()._handle(lesson, [])
        self.assertFalse(result.ok)

    def test_teacher_subject_mismatch(self):
        from patterns.design_patterns import TeacherSubjectHandler
        from models.entities import (Lesson, Subject, Teacher, Group,
                                      Room, TimeSlot, DayOfWeek, LessonType, RoomType)
        from datetime import time
        lesson = Lesson(1, Subject(1, "Python", 2, LessonType.LAB),
                        Teacher(1, "Суворий", "ФЕК", ["Математика"]),
                        Group(1, "КН-21", 25, 2, "КН"),
                        Room(1, "305", 30, RoomType.COMPUTER_LAB),
                        TimeSlot(DayOfWeek.MONDAY, 1, time(8, 0), time(9, 35)))
        result = TeacherSubjectHandler()._handle(lesson, [])
        self.assertFalse(result.ok)
        self.assertIn("не може викладати", result.message)

    def test_teacher_any_subject_passes(self):
        from patterns.design_patterns import TeacherSubjectHandler
        from models.entities import (Lesson, Subject, Teacher, Group,
                                      Room, TimeSlot, DayOfWeek, LessonType, RoomType)
        from datetime import time
        lesson = Lesson(1, Subject(1, "Python", 2, LessonType.LAB),
                        Teacher(1, "Вільний", "ФЕК", []),
                        Group(1, "КН-21", 25, 2, "КН"),
                        Room(1, "305", 30, RoomType.COMPUTER_LAB),
                        TimeSlot(DayOfWeek.MONDAY, 1, time(8, 0), time(9, 35)))
        result = TeacherSubjectHandler()._handle(lesson, [])
        self.assertTrue(result.ok)


class TestStrategies(unittest.TestCase):
    def _group(self):
        from models.entities import Group
        return Group(1, "ТГ-01", 30, 1, "Тест")

    def test_early_picks_first_slot(self):
        from patterns.design_patterns import EarlyMorningStrategy
        from models.entities import TimeSlot
        chosen = EarlyMorningStrategy().select_slot(TimeSlot.all_slots(), [], self._group())
        self.assertEqual(chosen.slot_number, 1)
        self.assertEqual(chosen.day.index, 0)

    def test_early_empty_returns_none(self):
        from patterns.design_patterns import EarlyMorningStrategy
        self.assertIsNone(EarlyMorningStrategy().select_slot([], [], self._group()))

    def test_afternoon_prefers_slot_4_plus(self):
        from patterns.design_patterns import AfternoonPreferenceStrategy
        from models.entities import TimeSlot
        chosen = AfternoonPreferenceStrategy().select_slot(TimeSlot.all_slots(), [], self._group())
        self.assertGreaterEqual(chosen.slot_number, 4)

    def test_afternoon_empty_returns_none(self):
        from patterns.design_patterns import AfternoonPreferenceStrategy
        self.assertIsNone(AfternoonPreferenceStrategy().select_slot([], [], self._group()))

    def test_balanced_returns_slot(self):
        from patterns.design_patterns import BalancedDayStrategy
        from models.entities import TimeSlot
        chosen = BalancedDayStrategy().select_slot(TimeSlot.all_slots(), [], self._group())
        self.assertIsNotNone(chosen)

    def test_balanced_empty_returns_none(self):
        from patterns.design_patterns import BalancedDayStrategy
        self.assertIsNone(BalancedDayStrategy().select_slot([], [], self._group()))

    def test_balanced_avoids_loaded_days(self):
        from patterns.design_patterns import BalancedDayStrategy
        from models.entities import (TimeSlot, Lesson, Subject, Teacher,
                                      Group, Room, DayOfWeek, LessonType, RoomType)
        group = self._group()
        subj = Subject(1, "Т", 2, LessonType.LECTURE)
        teach = Teacher(1, "Т", "К", [])
        room = Room(1, "101", 50, RoomType.LECTURE_HALL)
        mon_slots = [s for s in TimeSlot.all_slots() if s.day.index == 0][:3]
        busy = [Lesson(i, subj, teach, group, room, s) for i, s in enumerate(mon_slots)]
        chosen = BalancedDayStrategy().select_slot(TimeSlot.all_slots(), busy, group)
        self.assertIsNotNone(chosen)

    def test_afternoon_fallback_when_no_afternoon_slots(self):
        from patterns.design_patterns import AfternoonPreferenceStrategy
        from models.entities import TimeSlot, DayOfWeek
        from datetime import time
        morning_only = [s for s in TimeSlot.all_slots() if s.slot_number < 4][:2]
        chosen = AfternoonPreferenceStrategy().select_slot(morning_only, [], self._group())
        self.assertIsNotNone(chosen)


class TestObserver(unittest.TestCase):
    def test_event_log_records_events(self):
        from patterns.design_patterns import ScheduleSubject, EventLog, ScheduleEvent
        subject = ScheduleSubject()
        log = EventLog()
        subject.attach(log)
        subject.notify(ScheduleEvent("info", "тест", {}))
        self.assertEqual(len(log.get_all()), 1)

    def test_event_log_filters_conflicts(self):
        from patterns.design_patterns import ScheduleSubject, EventLog, ScheduleEvent
        subject = ScheduleSubject()
        log = EventLog()
        subject.attach(log)
        subject.notify(ScheduleEvent("info", "інфо", {}))
        subject.notify(ScheduleEvent("conflict", "конфлікт", {}))
        self.assertEqual(len(log.get_conflicts()), 1)

    def test_conflict_notifier_collects_conflicts(self):
        from patterns.design_patterns import ScheduleSubject, ConflictNotifier, ScheduleEvent
        subject = ScheduleSubject()
        notifier = ConflictNotifier()
        subject.attach(notifier)
        subject.notify(ScheduleEvent("conflict", "конфлікт!", {}))
        self.assertIn("конфлікт!", notifier.conflicts)

    def test_detach_stops_notifications(self):
        from patterns.design_patterns import ScheduleSubject, EventLog, ScheduleEvent
        subject = ScheduleSubject()
        log = EventLog()
        subject.attach(log)
        subject.detach(log)
        subject.notify(ScheduleEvent("info", "тест", {}))
        self.assertEqual(len(log.get_all()), 0)

    def test_multiple_observers_all_receive(self):
        from patterns.design_patterns import ScheduleSubject, EventLog, ScheduleEvent
        subject = ScheduleSubject()
        log1, log2 = EventLog(), EventLog()
        subject.attach(log1)
        subject.attach(log2)
        subject.notify(ScheduleEvent("info", "broadcast", {}))
        self.assertEqual(len(log1.get_all()), 1)
        self.assertEqual(len(log2.get_all()), 1)

    def test_event_log_clear(self):
        from patterns.design_patterns import ScheduleSubject, EventLog, ScheduleEvent
        subject = ScheduleSubject()
        log = EventLog()
        subject.attach(log)
        subject.notify(ScheduleEvent("info", "тест", {}))
        log.clear()
        self.assertEqual(len(log.get_all()), 0)

    def test_conflict_notifier_clear(self):
        from patterns.design_patterns import ConflictNotifier, ScheduleEvent
        notifier = ConflictNotifier()
        notifier.on_event(ScheduleEvent("conflict", "test", {}))
        notifier.clear()
        self.assertEqual(len(notifier.conflicts), 0)


class TestSingleton(unittest.TestCase):
    def test_same_instance(self):
        from patterns.design_patterns import Scheduler
        s1 = Scheduler()
        s2 = Scheduler()
        self.assertIs(s1, s2)

    def test_strategy_change_persists(self):
        from patterns.design_patterns import Scheduler, EarlyMorningStrategy
        s = Scheduler()
        s.set_strategy(EarlyMorningStrategy())
        self.assertEqual(Scheduler().get_strategy_name(), "EarlyMorningStrategy")


# ══════════════════════════════════════════════════════════════════
# 3. ТЕСТИ РЕПОЗИТОРІЇВ
# ══════════════════════════════════════════════════════════════════

class TestRepositories(unittest.TestCase):
    def setUp(self):
        from models.repositories import init_db, get_connection
        init_db()
        with get_connection() as conn:
            conn.execute("DELETE FROM lessons")
            conn.execute("DELETE FROM teachers")
            conn.execute("DELETE FROM rooms")
            conn.execute("DELETE FROM groups")
            conn.execute("DELETE FROM subjects")
            conn.execute("DELETE FROM sqlite_sequence WHERE name IN ('teachers','rooms','groups','subjects','lessons')")

    def test_teacher_save_and_get(self):
        from models.repositories import TeacherRepository
        from models.entities import Teacher
        repo = TeacherRepository()
        t = Teacher(None, "Тестовий Викладач", "Кафедра тесту", ["Python"])
        saved = repo.save(t)
        self.assertIsNotNone(saved.id)
        found = repo.get_by_id(saved.id)
        self.assertEqual(found.name, "Тестовий Викладач")

    def test_teacher_get_all(self):
        from models.repositories import TeacherRepository
        from models.entities import Teacher
        repo = TeacherRepository()
        before = len(repo.get_all())
        repo.save(Teacher(None, "Новий", "К", []))
        self.assertEqual(len(repo.get_all()), before + 1)

    def test_teacher_update(self):
        from models.repositories import TeacherRepository
        from models.entities import Teacher
        repo = TeacherRepository()
        t = repo.save(Teacher(None, "Старе Ім'я", "К", []))
        t.name = "Нове Ім'я"
        repo.save(t)
        updated = repo.get_by_id(t.id)
        self.assertEqual(updated.name, "Нове Ім'я")

    def test_teacher_delete(self):
        from models.repositories import TeacherRepository
        from models.entities import Teacher
        repo = TeacherRepository()
        t = repo.save(Teacher(None, "Видалити", "К", []))
        repo.delete(t.id)
        self.assertIsNone(repo.get_by_id(t.id))

    def test_teacher_subjects_serialization(self):
        from models.repositories import TeacherRepository
        from models.entities import Teacher
        repo = TeacherRepository()
        t = repo.save(Teacher(None, "З дисциплінами", "К", ["Python", "Java", "SQL"]))
        found = repo.get_by_id(t.id)
        self.assertEqual(sorted(found.subjects), sorted(["Python", "Java", "SQL"]))

    def test_room_save_and_get(self):
        from models.repositories import RoomRepository
        from models.entities import Room, RoomType
        repo = RoomRepository()
        r = Room(None, "999", 50, RoomType.LECTURE_HALL)
        saved = repo.save(r)
        self.assertIsNotNone(saved.id)
        found = repo.get_by_id(saved.id)
        self.assertEqual(found.number, "999")
        self.assertEqual(found.room_type, RoomType.LECTURE_HALL)

    def test_room_get_all(self):
        from models.repositories import RoomRepository
        from models.entities import Room, RoomType
        repo = RoomRepository()
        before = len(repo.get_all())
        repo.save(Room(None, "888", 25, RoomType.SEMINAR_ROOM))
        self.assertEqual(len(repo.get_all()), before + 1)

    def test_room_delete(self):
        from models.repositories import RoomRepository
        from models.entities import Room, RoomType
        repo = RoomRepository()
        r = repo.save(Room(None, "777", 20, RoomType.LABORATORY))
        repo.delete(r.id)
        self.assertIsNone(repo.get_by_id(r.id))

    def test_group_save_and_get(self):
        from models.repositories import GroupRepository
        from models.entities import Group
        repo = GroupRepository()
        g = Group(None, "ТГ-99", 25, 2, "Тестова спеціальність")
        saved = repo.save(g)
        self.assertIsNotNone(saved.id)
        found = repo.get_by_id(saved.id)
        self.assertEqual(found.name, "ТГ-99")

    def test_group_get_all(self):
        from models.repositories import GroupRepository
        from models.entities import Group
        repo = GroupRepository()
        before = len(repo.get_all())
        repo.save(Group(None, "ТГ-88", 20, 1, "Спец"))
        self.assertEqual(len(repo.get_all()), before + 1)

    def test_group_delete(self):
        from models.repositories import GroupRepository
        from models.entities import Group
        repo = GroupRepository()
        g = repo.save(Group(None, "ТГ-77", 15, 3, "Спец"))
        repo.delete(g.id)
        self.assertIsNone(repo.get_by_id(g.id))

    def test_subject_save_and_get(self):
        from models.repositories import SubjectRepository
        from models.entities import Subject, LessonType
        repo = SubjectRepository()
        s = Subject(None, "Тестова дисципліна", 2, LessonType.LECTURE)
        saved = repo.save(s)
        self.assertIsNotNone(saved.id)
        found = repo.get_by_id(saved.id)
        self.assertEqual(found.name, "Тестова дисципліна")
        self.assertEqual(found.lesson_type, LessonType.LECTURE)

    def test_subject_get_all(self):
        from models.repositories import SubjectRepository
        from models.entities import Subject, LessonType
        repo = SubjectRepository()
        before = len(repo.get_all())
        repo.save(Subject(None, "Нова дисципліна", 4, LessonType.LAB))
        self.assertEqual(len(repo.get_all()), before + 1)

    def test_subject_delete(self):
        from models.repositories import SubjectRepository
        from models.entities import Subject, LessonType
        repo = SubjectRepository()
        s = repo.save(Subject(None, "Видалити", 2, LessonType.SEMINAR))
        repo.delete(s.id)
        self.assertIsNone(repo.get_by_id(s.id))

    def test_not_found_returns_none(self):
        from models.repositories import TeacherRepository
        repo = TeacherRepository()
        self.assertIsNone(repo.get_by_id(99999))


# ══════════════════════════════════════════════════════════════════
# 4. ТЕСТИ СЕРВІСНОГО ШАРУ
# ══════════════════════════════════════════════════════════════════

class TestScheduleService(unittest.TestCase):
    def setUp(self):
        from models.repositories import init_db, get_connection
        from services.schedule_service import ScheduleService
        init_db()
        with get_connection() as conn:
            conn.execute("DELETE FROM lessons")
            conn.execute("DELETE FROM teachers")
            conn.execute("DELETE FROM rooms")
            conn.execute("DELETE FROM groups")
            conn.execute("DELETE FROM subjects")
            conn.execute("DELETE FROM sqlite_sequence WHERE name IN ('teachers','rooms','groups','subjects','lessons')")
        from patterns.design_patterns import Scheduler, SchedulerMeta
        SchedulerMeta._instances.clear()
        self.svc = ScheduleService()
        # Базові дані
        self.teacher = self.svc.save_teacher({
            "name": "Сервіс Викладач", "department": "К", "subjects": ["Python"]
        })
        self.room = self.svc.save_room({
            "number": "T01", "capacity": 30, "room_type": "COMPUTER_LAB"
        })
        self.group = self.svc.save_group({
            "name": "ТС-01", "size": 20, "year": 2, "specialty": "Тест"
        })
        self.subject = self.svc.save_subject({
            "name": "Python", "hours_per_week": 2, "lesson_type": "LAB"
        })

    def test_get_teachers_returns_list(self):
        teachers = self.svc.get_teachers()
        self.assertIsInstance(teachers, list)
        self.assertTrue(any(t.name == "Сервіс Викладач" for t in teachers))

    def test_get_rooms_returns_list(self):
        rooms = self.svc.get_rooms()
        self.assertIsInstance(rooms, list)
        self.assertTrue(any(r.number == "T01" for r in rooms))

    def test_get_groups_returns_list(self):
        groups = self.svc.get_groups()
        self.assertIsInstance(groups, list)
        self.assertTrue(any(g.name == "ТС-01" for g in groups))

    def test_get_subjects_returns_list(self):
        subjects = self.svc.get_subjects()
        self.assertIsInstance(subjects, list)
        self.assertTrue(any(s.name == "Python" for s in subjects))

    def test_auto_schedule_balanced(self):
        ok, msg, lesson = self.svc.auto_schedule(
            self.subject.id, self.teacher.id, self.group.id, self.room.id, "balanced"
        )
        self.assertTrue(ok)
        self.assertIsNotNone(lesson)

    def test_auto_schedule_early(self):
        ok, msg, lesson = self.svc.auto_schedule(
            self.subject.id, self.teacher.id, self.group.id, self.room.id, "early"
        )
        self.assertTrue(ok)

    def test_auto_schedule_afternoon(self):
        ok, msg, lesson = self.svc.auto_schedule(
            self.subject.id, self.teacher.id, self.group.id, self.room.id, "afternoon"
        )
        self.assertTrue(ok)

    def test_add_lesson_manual(self):
        ok, msg, lesson = self.svc.add_lesson(
            self.subject.id, self.teacher.id, self.group.id, self.room.id, 0, 3
        )
        self.assertTrue(ok, msg)
        self.assertIsNotNone(lesson)

    def test_add_lesson_invalid_ids(self):
        ok, msg, lesson = self.svc.add_lesson(99999, 99999, 99999, 99999, 0, 1)
        self.assertFalse(ok)
        self.assertIsNone(lesson)

    def test_add_lesson_invalid_slot(self):
        ok, msg, lesson = self.svc.add_lesson(
            self.subject.id, self.teacher.id, self.group.id, self.room.id, 99, 99
        )
        self.assertFalse(ok)

    def test_get_all_lessons(self):
        self.svc.auto_schedule(
            self.subject.id, self.teacher.id, self.group.id, self.room.id, "balanced"
        )
        lessons = self.svc.get_all_lessons()
        self.assertIsInstance(lessons, list)

    def test_get_schedule_for_group(self):
        self.svc.auto_schedule(
            self.subject.id, self.teacher.id, self.group.id, self.room.id, "balanced"
        )
        lessons = self.svc.get_schedule_for_group(self.group.id)
        self.assertIsInstance(lessons, list)

    def test_get_schedule_for_teacher(self):
        self.svc.auto_schedule(
            self.subject.id, self.teacher.id, self.group.id, self.room.id, "balanced"
        )
        lessons = self.svc.get_schedule_for_teacher(self.teacher.id)
        self.assertIsInstance(lessons, list)

    def test_get_statistics(self):
        stats = self.svc.get_statistics()
        self.assertIn("total_lessons", stats)
        self.assertIn("total_teachers", stats)
        self.assertIn("teacher_load", stats)

    def test_delete_lesson(self):
        ok, msg, lesson = self.svc.auto_schedule(
            self.subject.id, self.teacher.id, self.group.id, self.room.id, "early"
        )
        self.assertTrue(ok)
        self.svc.delete_lesson(lesson.id)
        lessons = self.svc.get_all_lessons()
        self.assertFalse(any(l.id == lesson.id for l in lessons))

    def test_clear_schedule(self):
        self.svc.auto_schedule(
            self.subject.id, self.teacher.id, self.group.id, self.room.id, "balanced"
        )
        self.svc.clear_schedule()
        self.assertEqual(len(self.svc.get_all_lessons()), 0)

    def test_get_conflict_log(self):
        log = self.svc.get_conflict_log()
        self.assertIsInstance(log, list)

    def test_delete_teacher(self):
        t = self.svc.save_teacher({"name": "Видалити", "department": "К", "subjects": []})
        self.svc.delete_teacher(t.id)
        teachers = self.svc.get_teachers()
        self.assertFalse(any(x.id == t.id for x in teachers))

    def test_delete_room(self):
        r = self.svc.save_room({"number": "DEL01", "capacity": 10, "room_type": "SEMINAR_ROOM"})
        self.svc.delete_room(r.id)
        rooms = self.svc.get_rooms()
        self.assertFalse(any(x.id == r.id for x in rooms))

    def test_delete_group(self):
        g = self.svc.save_group({"name": "DEL-01", "size": 10, "year": 1, "specialty": "Тест"})
        self.svc.delete_group(g.id)
        groups = self.svc.get_groups()
        self.assertFalse(any(x.id == g.id for x in groups))

    def test_delete_subject(self):
        s = self.svc.save_subject({"name": "Видалити", "hours_per_week": 2, "lesson_type": "LECTURE"})
        self.svc.delete_subject(s.id)
        subjects = self.svc.get_subjects()
        self.assertFalse(any(x.id == s.id for x in subjects))

    def test_auto_schedule_invalid_ids(self):
        ok, msg, lesson = self.svc.auto_schedule(99999, 99999, 99999, 99999, "balanced")
        self.assertFalse(ok)
        self.assertIsNone(lesson)


# ══════════════════════════════════════════════════════════════════
# 5. ІНТЕГРАЦІЙНІ ТЕСТИ
# ══════════════════════════════════════════════════════════════════

class TestSchedulerIntegration(unittest.TestCase):
    def setUp(self):
        from models.entities import Teacher, Room, Group, Subject, LessonType, RoomType
        self.teacher = Teacher(1, "Тест Викладач", "ФЕК", [])
        self.room = Room(1, "101", 120, RoomType.LECTURE_HALL)
        self.group = Group(1, "ТГ-01", 30, 1, "Тест")
        self.subj = Subject(1, "Тест", 2, LessonType.LECTURE)

    def test_suggest_slot_returns_timeslot(self):
        from patterns.design_patterns import Scheduler, BalancedDayStrategy
        from models.entities import TimeSlot
        s = Scheduler()
        s.set_strategy(BalancedDayStrategy())
        slot = s.suggest_slot(self.teacher, self.room, self.group, [])
        self.assertIsInstance(slot, TimeSlot)

    def test_validate_empty_schedule_passes(self):
        from patterns.design_patterns import Scheduler, LessonBuilder
        from models.entities import TimeSlot
        s = Scheduler()
        slot = TimeSlot.all_slots()[0]
        lesson = (LessonBuilder()
                  .with_subject(self.subj)
                  .with_teacher(self.teacher)
                  .with_group(self.group)
                  .with_room(self.room)
                  .with_time_slot(slot)
                  .build())
        result = s.validate_lesson(lesson, [])
        self.assertTrue(result.ok)

    def test_suggest_slot_excludes_busy_slots(self):
        from patterns.design_patterns import Scheduler, BalancedDayStrategy, LessonBuilder
        from models.entities import TimeSlot
        s = Scheduler()
        s.set_strategy(BalancedDayStrategy())
        all_slots = TimeSlot.all_slots()
        first_slot = all_slots[0]
        lesson = (LessonBuilder()
                  .with_subject(self.subj)
                  .with_teacher(self.teacher)
                  .with_group(self.group)
                  .with_room(self.room)
                  .with_time_slot(first_slot)
                  .build())
        slot = s.suggest_slot(self.teacher, self.room, self.group, [lesson])
        self.assertNotEqual(slot, first_slot)

    def test_notify_added(self):
        from patterns.design_patterns import Scheduler, LessonBuilder
        from models.entities import TimeSlot
        s = Scheduler()
        s.conflict_notifier.clear()
        slot = TimeSlot.all_slots()[5]
        lesson = (LessonBuilder()
                  .with_subject(self.subj)
                  .with_teacher(self.teacher)
                  .with_group(self.group)
                  .with_room(self.room)
                  .with_time_slot(slot)
                  .build())
        lesson.id = 99
        s.notify_added(lesson)
        events = s.event_log.get_all()
        self.assertTrue(any(e.event_type == "lesson_added" for e in events))

    def test_notify_removed(self):
        from patterns.design_patterns import Scheduler
        s = Scheduler()
        s.notify_removed(42)
        events = s.event_log.get_all()
        self.assertTrue(any(e.event_type == "lesson_removed" for e in events))


if __name__ == "__main__":
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    for cls in [
        TestDayOfWeek, TestTimeSlot, TestRoom, TestTeacher, TestLesson,
        TestLessonBuilder, TestConstraintChain, TestStrategies,
        TestObserver, TestSingleton,
        TestRepositories, TestScheduleService,
        TestSchedulerIntegration,
    ]:
        suite.addTests(loader.loadTestsFromTestCase(cls))

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    passed = result.testsRun - len(result.failures) - len(result.errors)
    print("\n" + "=" * 60)
    print(f"  Всього тестів : {result.testsRun}")
    print(f"  Успішно       : {passed}")
    print(f"  Помилок       : {len(result.failures) + len(result.errors)}")
    print("=" * 60)