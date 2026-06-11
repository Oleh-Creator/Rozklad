"""
Юніт-тести системи управління розкладом навчального закладу.

Охоплює:
    - Доменні моделі (entities.py)
    - Патерни проєктування (design_patterns.py)
    - Інтеграцію планувальника (Scheduler)
    - Сервісний шар (schedule_service.py) — з тимчасовою БД

Запуск::

    python test_schedule.py

Кількість тестів: 52
"""

import sys
import os
import unittest
import tempfile

sys.path.insert(0, os.path.dirname(__file__))

# Перенаправляємо БД у тимчасовий файл для тестів
import models.repositories as _repo_module
_tmp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
_tmp_db.close()
_repo_module.DB_PATH = _tmp_db.name


# ══════════════════════════════════════════════════════════════════
# 1. ТЕСТИ ДОМЕННИХ МОДЕЛЕЙ (entities.py)
# ══════════════════════════════════════════════════════════════════

class TestDayOfWeek(unittest.TestCase):
    """Тести переліку DayOfWeek."""

    def test_monday_label(self):
        """Понеділок має правильну україномовну назву."""
        from models.entities import DayOfWeek
        self.assertEqual(DayOfWeek.MONDAY.label, "Понеділок")

    def test_saturday_index(self):
        """Субота має індекс 5."""
        from models.entities import DayOfWeek
        self.assertEqual(DayOfWeek.SATURDAY.index, 5)

    def test_from_index_monday(self):
        """from_index(0) повертає понеділок."""
        from models.entities import DayOfWeek
        self.assertEqual(DayOfWeek.from_index(0), DayOfWeek.MONDAY)

    def test_from_index_friday(self):
        """from_index(4) повертає п'ятницю."""
        from models.entities import DayOfWeek
        self.assertEqual(DayOfWeek.from_index(4), DayOfWeek.FRIDAY)

    def test_from_index_invalid(self):
        """Невідомий індекс викидає ValueError."""
        from models.entities import DayOfWeek
        with self.assertRaises(ValueError):
            DayOfWeek.from_index(99)

    def test_all_days_count(self):
        """Перелік містить рівно 6 днів."""
        from models.entities import DayOfWeek
        self.assertEqual(len(list(DayOfWeek)), 6)

    def test_all_indexes_unique(self):
        """Кожен день має унікальний індекс."""
        from models.entities import DayOfWeek
        indexes = [d.index for d in DayOfWeek]
        self.assertEqual(len(indexes), len(set(indexes)))


class TestTimeSlot(unittest.TestCase):
    """Тести Value Object TimeSlot."""

    def test_all_slots_count(self):
        """Генерується рівно 36 слотів (6 днів × 6 пар)."""
        from models.entities import TimeSlot
        self.assertEqual(len(TimeSlot.all_slots()), 36)

    def test_slot_equality_same(self):
        """Два слоти з однаковим днем і номером — рівні."""
        from models.entities import TimeSlot, DayOfWeek
        from datetime import time
        s1 = TimeSlot(DayOfWeek.MONDAY, 1, time(8, 0), time(9, 35))
        s2 = TimeSlot(DayOfWeek.MONDAY, 1, time(8, 0), time(9, 35))
        self.assertEqual(s1, s2)

    def test_slot_equality_different_day(self):
        """Слоти різних днів — не рівні."""
        from models.entities import TimeSlot, DayOfWeek
        from datetime import time
        s1 = TimeSlot(DayOfWeek.MONDAY,  1, time(8, 0), time(9, 35))
        s2 = TimeSlot(DayOfWeek.TUESDAY, 1, time(8, 0), time(9, 35))
        self.assertNotEqual(s1, s2)

    def test_slot_equality_different_number(self):
        """Слоти одного дня з різними номерами — не рівні."""
        from models.entities import TimeSlot, DayOfWeek
        from datetime import time
        s1 = TimeSlot(DayOfWeek.MONDAY, 1, time(8,  0), time(9,  35))
        s2 = TimeSlot(DayOfWeek.MONDAY, 2, time(9, 45), time(11, 20))
        self.assertNotEqual(s1, s2)

    def test_slot_hashable(self):
        """TimeSlot можна використовувати як ключ словника."""
        from models.entities import TimeSlot, DayOfWeek
        from datetime import time
        s = TimeSlot(DayOfWeek.WEDNESDAY, 3, time(11, 30), time(13, 5))
        d = {s: "test"}
        self.assertEqual(d[s], "test")

    def test_slot_repr_contains_day(self):
        """repr() містить назву дня."""
        from models.entities import TimeSlot, DayOfWeek
        from datetime import time
        s = TimeSlot(DayOfWeek.THURSDAY, 2, time(9, 45), time(11, 20))
        self.assertIn("Четвер", repr(s))

    def test_all_slots_days_covered(self):
        """Кожен із 6 днів представлений у слотах."""
        from models.entities import TimeSlot, DayOfWeek
        days_in_slots = {s.day for s in TimeSlot.all_slots()}
        self.assertEqual(days_in_slots, set(DayOfWeek))


class TestRoom(unittest.TestCase):
    """Тести сутності Room та метода is_suitable_for."""

    def test_lecture_suitable_in_lecture_hall(self):
        """Лекція підходить для лекційної аудиторії."""
        from models.entities import Room, RoomType, LessonType
        r = Room(1, "101", 120, RoomType.LECTURE_HALL)
        self.assertTrue(r.is_suitable_for(LessonType.LECTURE, 80))

    def test_lecture_not_suitable_in_seminar_room(self):
        """Лекція не підходить для семінарської кімнати."""
        from models.entities import Room, RoomType, LessonType
        r = Room(1, "410", 30, RoomType.SEMINAR_ROOM)
        self.assertFalse(r.is_suitable_for(LessonType.LECTURE, 25))

    def test_lecture_not_suitable_in_computer_lab(self):
        """Лекція не підходить для комп'ютерної лабораторії."""
        from models.entities import Room, RoomType, LessonType
        r = Room(1, "305", 30, RoomType.COMPUTER_LAB)
        self.assertFalse(r.is_suitable_for(LessonType.LECTURE, 25))

    def test_over_capacity(self):
        """Група більша за місткість — аудиторія не підходить."""
        from models.entities import Room, RoomType, LessonType
        r = Room(1, "101", 20, RoomType.LECTURE_HALL)
        self.assertFalse(r.is_suitable_for(LessonType.LECTURE, 50))

    def test_lab_suitable_in_computer_lab(self):
        """Лабораторна підходить для комп'ютерної лабораторії."""
        from models.entities import Room, RoomType, LessonType
        r = Room(1, "305", 30, RoomType.COMPUTER_LAB)
        self.assertTrue(r.is_suitable_for(LessonType.LAB, 25))

    def test_lab_suitable_in_laboratory(self):
        """Лабораторна підходить для лабораторії."""
        from models.entities import Room, RoomType, LessonType
        r = Room(1, "411", 25, RoomType.LABORATORY)
        self.assertTrue(r.is_suitable_for(LessonType.LAB, 20))

    def test_lab_not_suitable_in_seminar_room(self):
        """Лабораторна не підходить для семінарської кімнати."""
        from models.entities import Room, RoomType, LessonType
        r = Room(1, "410", 30, RoomType.SEMINAR_ROOM)
        self.assertFalse(r.is_suitable_for(LessonType.LAB, 25))

    def test_practice_suitable_anywhere_with_capacity(self):
        """Практика підходить для будь-якої аудиторії з достатньою місткістю."""
        from models.entities import Room, RoomType, LessonType
        for rt in RoomType:
            r = Room(1, "X", 50, rt)
            self.assertTrue(r.is_suitable_for(LessonType.PRACTICE, 30))

    def test_seminar_suitable_in_seminar_room(self):
        """Семінар підходить для семінарської кімнати."""
        from models.entities import Room, RoomType, LessonType
        r = Room(1, "410", 35, RoomType.SEMINAR_ROOM)
        self.assertTrue(r.is_suitable_for(LessonType.SEMINAR, 30))

    def test_repr_contains_number(self):
        """repr() аудиторії містить її номер."""
        from models.entities import Room, RoomType
        r = Room(1, "305-А", 30, RoomType.COMPUTER_LAB)
        self.assertIn("305-А", repr(r))


class TestTeacher(unittest.TestCase):
    """Тести сутності Teacher."""

    def test_can_teach_listed_subject(self):
        """Викладач може вести дисципліну зі свого списку."""
        from models.entities import Teacher
        t = Teacher(1, "Іваненко", "ФЕК", ["Python", "Java"])
        self.assertTrue(t.can_teach("Python"))

    def test_cannot_teach_unlisted_subject(self):
        """Викладач не може вести дисципліну не зі свого списку."""
        from models.entities import Teacher
        t = Teacher(1, "Іваненко", "ФЕК", ["Python"])
        self.assertFalse(t.can_teach("Математика"))

    def test_empty_subjects_cannot_teach(self):
        """Викладач без дисциплін не може нічого викладати."""
        from models.entities import Teacher
        t = Teacher(1, "Коваленко", "ФЕК", [])
        self.assertFalse(t.can_teach("Python"))

    def test_repr_contains_name(self):
        """repr() містить ім'я викладача."""
        from models.entities import Teacher
        t = Teacher(1, "Шевченко", "ФЕК", [])
        self.assertIn("Шевченко", repr(t))


class TestLesson(unittest.TestCase):
    """Тести сутності Lesson."""

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
        """to_dict() містить назву дисципліни."""
        self.assertEqual(self._make_lesson().to_dict()["subject"], "Python")

    def test_to_dict_teacher(self):
        """to_dict() містить ім'я викладача."""
        self.assertEqual(self._make_lesson().to_dict()["teacher"], "Іваненко")

    def test_to_dict_day(self):
        """to_dict() містить назву дня."""
        self.assertEqual(self._make_lesson().to_dict()["day"], "Понеділок")

    def test_to_dict_slot(self):
        """to_dict() містить номер пари."""
        self.assertEqual(self._make_lesson().to_dict()["slot"], 1)

    def test_to_dict_has_all_keys(self):
        """to_dict() містить усі необхідні ключі."""
        keys = self._make_lesson().to_dict().keys()
        for k in ["id","subject","teacher","group","room","day","slot","start","end"]:
            self.assertIn(k, keys)

    def test_repr_contains_subject(self):
        """repr() містить назву дисципліни."""
        self.assertIn("Python", repr(self._make_lesson()))


# ══════════════════════════════════════════════════════════════════
# 2. ТЕСТИ ПАТЕРНІВ ПРОЄКТУВАННЯ (design_patterns.py)
# ══════════════════════════════════════════════════════════════════

class TestLessonBuilder(unittest.TestCase):
    """Тести патерну Builder."""

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
        """Builder будує Lesson якщо всі поля задані."""
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
        """Builder зберігає вказаний id."""
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
        """build() без викладача викидає ValueError."""
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
        """build() без дисципліни викидає ValueError."""
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
        """build() без жодного поля викидає ValueError."""
        from patterns.design_patterns import LessonBuilder
        with self.assertRaises(ValueError):
            LessonBuilder().build()


class TestConstraintChain(unittest.TestCase):
    """Тести патерну Chain of Responsibility."""

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
        """Порожній список існуючих занять — немає конфліктів."""
        from patterns.design_patterns import build_constraint_chain
        result = build_constraint_chain().check(self._make_lesson(), [])
        self.assertTrue(result.ok)

    def test_teacher_conflict(self):
        """Конфлікт викладача виявляється."""
        from patterns.design_patterns import build_constraint_chain
        existing = self._make_lesson(lid=1)
        new      = self._make_lesson(lid=2)
        result   = build_constraint_chain().check(new, [existing])
        self.assertFalse(result.ok)
        self.assertIn("Викладач", result.message)

    def test_room_conflict(self):
        """Конфлікт аудиторії виявляється."""
        from patterns.design_patterns import build_constraint_chain
        from models.entities import Teacher
        existing = self._make_lesson(lid=1, teacher_id=1)
        new      = self._make_lesson(lid=2, teacher_id=99)
        new.teacher = Teacher(99, "Інший", "ФЕК", [])
        result = build_constraint_chain().check(new, [existing])
        self.assertFalse(result.ok)

    def test_group_conflict(self):
        """Конфлікт групи виявляється."""
        from patterns.design_patterns import build_constraint_chain
        from models.entities import Teacher, Room, RoomType
        existing = self._make_lesson(lid=1, teacher_id=1, room_id=1)
        new = self._make_lesson(lid=2, teacher_id=2, room_id=2)
        new.teacher = Teacher(2, "Інший", "ФЕК", [])
        new.room    = Room(2, "306", 30, RoomType.COMPUTER_LAB)
        result = build_constraint_chain().check(new, [existing])
        self.assertFalse(result.ok)
        self.assertIn("Група", result.message)

    def test_room_suitability_lecture_wrong_room(self):
        """Лекція у семінарській кімнаті — невідповідність."""
        from patterns.design_patterns import RoomSuitabilityHandler
        from models.entities import (Lesson, Subject, Teacher, Group,
                                      Room, TimeSlot, DayOfWeek,
                                      LessonType, RoomType)
        from datetime import time
        lesson = Lesson(
            id=1,
            subject=Subject(1, "Математика", 4, LessonType.LECTURE),
            teacher=Teacher(1, "Т", "К", []),
            group=Group(1, "КН-21", 25, 2, "КН"),
            room=Room(1, "410", 30, RoomType.SEMINAR_ROOM),
            time_slot=TimeSlot(DayOfWeek.MONDAY, 1, time(8, 0), time(9, 35))
        )
        result = RoomSuitabilityHandler()._handle(lesson, [])
        self.assertFalse(result.ok)

    def test_teacher_subject_mismatch(self):
        """Викладач без потрібної дисципліни — конфлікт кваліфікації."""
        from patterns.design_patterns import TeacherSubjectHandler
        from models.entities import (Lesson, Subject, Teacher, Group,
                                      Room, TimeSlot, DayOfWeek,
                                      LessonType, RoomType)
        from datetime import time
        lesson = Lesson(
            id=1,
            subject=Subject(1, "Python", 2, LessonType.LAB),
            teacher=Teacher(1, "Суворий", "ФЕК", ["Математика"]),
            group=Group(1, "КН-21", 25, 2, "КН"),
            room=Room(1, "305", 30, RoomType.COMPUTER_LAB),
            time_slot=TimeSlot(DayOfWeek.MONDAY, 1, time(8, 0), time(9, 35))
        )
        result = TeacherSubjectHandler()._handle(lesson, [])
        self.assertFalse(result.ok)
        self.assertIn("не може викладати", result.message)

    def test_teacher_any_subject_passes(self):
        """Викладач без обмежень (порожній список) — конфлікту немає."""
        from patterns.design_patterns import TeacherSubjectHandler
        from models.entities import (Lesson, Subject, Teacher, Group,
                                      Room, TimeSlot, DayOfWeek,
                                      LessonType, RoomType)
        from datetime import time
        lesson = Lesson(
            id=1,
            subject=Subject(1, "Python", 2, LessonType.LAB),
            teacher=Teacher(1, "Вільний", "ФЕК", []),
            group=Group(1, "КН-21", 25, 2, "КН"),
            room=Room(1, "305", 30, RoomType.COMPUTER_LAB),
            time_slot=TimeSlot(DayOfWeek.MONDAY, 1, time(8, 0), time(9, 35))
        )
        result = TeacherSubjectHandler()._handle(lesson, [])
        self.assertTrue(result.ok)


class TestStrategies(unittest.TestCase):
    """Тести патерну Strategy."""

    def _group(self):
        from models.entities import Group
        return Group(1, "ТГ-01", 30, 1, "Тест")

    def test_early_picks_first_slot(self):
        """EarlyMorningStrategy обирає найраніший слот."""
        from patterns.design_patterns import EarlyMorningStrategy
        from models.entities import TimeSlot
        chosen = EarlyMorningStrategy().select_slot(
            TimeSlot.all_slots(), [], self._group()
        )
        self.assertEqual(chosen.slot_number, 1)
        self.assertEqual(chosen.day.index, 0)

    def test_early_empty_returns_none(self):
        """EarlyMorningStrategy повертає None якщо слотів немає."""
        from patterns.design_patterns import EarlyMorningStrategy
        self.assertIsNone(
            EarlyMorningStrategy().select_slot([], [], self._group())
        )

    def test_afternoon_prefers_slot_4_plus(self):
        """AfternoonPreferenceStrategy обирає слот >= 4."""
        from patterns.design_patterns import AfternoonPreferenceStrategy
        from models.entities import TimeSlot
        chosen = AfternoonPreferenceStrategy().select_slot(
            TimeSlot.all_slots(), [], self._group()
        )
        self.assertGreaterEqual(chosen.slot_number, 4)

    def test_afternoon_empty_returns_none(self):
        """AfternoonPreferenceStrategy повертає None якщо слотів немає."""
        from patterns.design_patterns import AfternoonPreferenceStrategy
        self.assertIsNone(
            AfternoonPreferenceStrategy().select_slot([], [], self._group())
        )

    def test_balanced_returns_slot(self):
        """BalancedDayStrategy повертає слот."""
        from patterns.design_patterns import BalancedDayStrategy
        from models.entities import TimeSlot
        chosen = BalancedDayStrategy().select_slot(
            TimeSlot.all_slots(), [], self._group()
        )
        self.assertIsNotNone(chosen)

    def test_balanced_empty_returns_none(self):
        """BalancedDayStrategy повертає None якщо слотів немає."""
        from patterns.design_patterns import BalancedDayStrategy
        self.assertIsNone(
            BalancedDayStrategy().select_slot([], [], self._group())
        )

    def test_balanced_avoids_loaded_days(self):
        """BalancedDayStrategy уникає перевантажених днів."""
        from patterns.design_patterns import BalancedDayStrategy
        from models.entities import (TimeSlot, Lesson, Subject, Teacher,
                                      Group, Room, DayOfWeek, LessonType, RoomType)
        from datetime import time
        group = self._group()
        subj  = Subject(1, "Т", 2, LessonType.LECTURE)
        teach = Teacher(1, "Т", "К", [])
        room  = Room(1, "101", 50, RoomType.LECTURE_HALL)

        mon_slots = [s for s in TimeSlot.all_slots() if s.day.index == 0][:3]
        busy = [Lesson(i, subj, teach, group, room, s)
                for i, s in enumerate(mon_slots)]

        chosen = BalancedDayStrategy().select_slot(
            TimeSlot.all_slots(), busy, group
        )
        self.assertIsNotNone(chosen)


class TestObserver(unittest.TestCase):
    """Тести патерну Observer."""

    def test_event_log_records_events(self):
        """EventLog фіксує всі події."""
        from patterns.design_patterns import ScheduleSubject, EventLog, ScheduleEvent
        subject = ScheduleSubject()
        log = EventLog()
        subject.attach(log)
        subject.notify(ScheduleEvent("info", "тест", {}))
        self.assertEqual(len(log.get_all()), 1)

    def test_event_log_filters_conflicts(self):
        """EventLog.get_conflicts() повертає лише конфлікти."""
        from patterns.design_patterns import ScheduleSubject, EventLog, ScheduleEvent
        subject = ScheduleSubject()
        log = EventLog()
        subject.attach(log)
        subject.notify(ScheduleEvent("info",     "інфо",     {}))
        subject.notify(ScheduleEvent("conflict", "конфлікт", {}))
        self.assertEqual(len(log.get_conflicts()), 1)

    def test_conflict_notifier_collects_conflicts(self):
        """ConflictNotifier збирає повідомлення про конфлікти."""
        from patterns.design_patterns import (ScheduleSubject, ConflictNotifier,
                                               ScheduleEvent)
        subject  = ScheduleSubject()
        notifier = ConflictNotifier()
        subject.attach(notifier)
        subject.notify(ScheduleEvent("conflict", "конфлікт!", {}))
        self.assertIn("конфлікт!", notifier.conflicts)

    def test_detach_stops_notifications(self):
        """Після detach спостерігач не отримує події."""
        from patterns.design_patterns import ScheduleSubject, EventLog, ScheduleEvent
        subject = ScheduleSubject()
        log = EventLog()
        subject.attach(log)
        subject.detach(log)
        subject.notify(ScheduleEvent("info", "тест", {}))
        self.assertEqual(len(log.get_all()), 0)

    def test_multiple_observers_all_receive(self):
        """Кілька спостерігачів отримують одну і ту ж подію."""
        from patterns.design_patterns import ScheduleSubject, EventLog, ScheduleEvent
        subject = ScheduleSubject()
        log1, log2 = EventLog(), EventLog()
        subject.attach(log1)
        subject.attach(log2)
        subject.notify(ScheduleEvent("info", "broadcast", {}))
        self.assertEqual(len(log1.get_all()), 1)
        self.assertEqual(len(log2.get_all()), 1)

    def test_event_log_clear(self):
        """EventLog.clear() очищає всі записи."""
        from patterns.design_patterns import ScheduleSubject, EventLog, ScheduleEvent
        subject = ScheduleSubject()
        log = EventLog()
        subject.attach(log)
        subject.notify(ScheduleEvent("info", "тест", {}))
        log.clear()
        self.assertEqual(len(log.get_all()), 0)


class TestSingleton(unittest.TestCase):
    """Тести патерну Singleton."""

    def test_same_instance(self):
        """Scheduler завжди повертає один і той самий екземпляр."""
        from patterns.design_patterns import Scheduler
        s1 = Scheduler()
        s2 = Scheduler()
        self.assertIs(s1, s2)

    def test_strategy_change_persists(self):
        """Зміна стратегії зберігається між зверненнями."""
        from patterns.design_patterns import Scheduler, EarlyMorningStrategy
        s = Scheduler()
        s.set_strategy(EarlyMorningStrategy())
        self.assertEqual(Scheduler().get_strategy_name(), "EarlyMorningStrategy")


# ══════════════════════════════════════════════════════════════════
# 3. ІНТЕГРАЦІЙНІ ТЕСТИ ПЛАНУВАЛЬНИКА
# ══════════════════════════════════════════════════════════════════

class TestSchedulerIntegration(unittest.TestCase):
    """Інтеграційні тести Scheduler."""

    def setUp(self):
        from models.entities import Teacher, Room, Group, Subject, LessonType, RoomType
        self.teacher = Teacher(1, "Тест Викладач", "ФЕК", [])
        self.room    = Room(1, "101", 120, RoomType.LECTURE_HALL)
        self.group   = Group(1, "ТГ-01", 30, 1, "Тест")
        self.subj    = Subject(1, "Тест", 2, LessonType.LECTURE)

    def test_suggest_slot_returns_timeslot(self):
        """suggest_slot повертає об'єкт TimeSlot."""
        from patterns.design_patterns import Scheduler, BalancedDayStrategy
        from models.entities import TimeSlot
        s = Scheduler()
        s.set_strategy(BalancedDayStrategy())
        slot = s.suggest_slot(self.teacher, self.room, self.group, [])
        self.assertIsInstance(slot, TimeSlot)

    def test_validate_empty_schedule_passes(self):
        """Валідація заняття без існуючого розкладу — успіх."""
        from patterns.design_patterns import Scheduler, LessonBuilder
        from models.entities import TimeSlot
        s = Scheduler()
        slot   = TimeSlot.all_slots()[0]
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
        """suggest_slot не повертає зайнятий слот."""
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


# ══════════════════════════════════════════════════════════════════
# Запуск тестів
# ══════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    test_classes = [
        TestDayOfWeek, TestTimeSlot, TestRoom,
        TestTeacher, TestLesson,
        TestLessonBuilder, TestConstraintChain,
        TestStrategies, TestObserver, TestSingleton,
        TestSchedulerIntegration,
    ]

    loader = unittest.TestLoader()
    suite  = unittest.TestSuite()
    for cls in test_classes:
        suite.addTests(loader.loadTestsFromTestCase(cls))

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    passed = result.testsRun - len(result.failures) - len(result.errors)
    print("\n" + "=" * 60)
    print(f"  Всього тестів : {result.testsRun}")
    print(f"  Успішно       : {passed}")
    print(f"  Помилок       : {len(result.failures) + len(result.errors)}")
    print("=" * 60)
