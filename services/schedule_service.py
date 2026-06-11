"""
Сервісний шар — бізнес-логіка системи.
Координує репозиторії та патерни.
"""

from models.entities import (
    Teacher, Room, Group, Subject, Lesson, TimeSlot,
    DayOfWeek, LessonType, RoomType
)
from models.repositories import (
    TeacherRepository, RoomRepository, GroupRepository,
    SubjectRepository, LessonRepository
)
from patterns.design_patterns import (
    Scheduler, LessonBuilder, ConstraintResult,
    EarlyMorningStrategy, BalancedDayStrategy, AfternoonPreferenceStrategy
)


# ─────────────────────────────────────────────
# Сервіс управління розкладом
# ─────────────────────────────────────────────

class ScheduleService:
    """Фасад над усіма підсистемами."""

    STRATEGIES = {
        "balanced":  BalancedDayStrategy,
        "early":     EarlyMorningStrategy,
        "afternoon": AfternoonPreferenceStrategy,
    }

    def __init__(self):
        self._teacher_repo = TeacherRepository()
        self._room_repo    = RoomRepository()
        self._group_repo   = GroupRepository()
        self._subject_repo = SubjectRepository()
        self._lesson_repo  = LessonRepository()
        self._scheduler    = Scheduler()

    # ── Довідники ────────────────────────────────────────────────

    def get_teachers(self): return self._teacher_repo.get_all()
    def get_rooms(self):    return self._room_repo.get_all()
    def get_groups(self):   return self._group_repo.get_all()
    def get_subjects(self): return self._subject_repo.get_all()

    def save_teacher(self, data: dict) -> Teacher:
        t = Teacher(
            id=data.get("id"),
            name=data["name"].strip(),
            department=data["department"].strip(),
            subjects=[s.strip() for s in data.get("subjects", []) if s.strip()]
        )
        return self._teacher_repo.save(t)

    def save_room(self, data: dict) -> Room:
        r = Room(
            id=data.get("id"),
            number=data["number"].strip(),
            capacity=int(data["capacity"]),
            room_type=RoomType[data["room_type"]],
            equipment=[]
        )
        return self._room_repo.save(r)

    def save_group(self, data: dict) -> Group:
        g = Group(
            id=data.get("id"),
            name=data["name"].strip(),
            size=int(data["size"]),
            year=int(data["year"]),
            specialty=data["specialty"].strip()
        )
        return self._group_repo.save(g)

    def save_subject(self, data: dict) -> Subject:
        s = Subject(
            id=data.get("id"),
            name=data["name"].strip(),
            hours_per_week=int(data.get("hours_per_week", 2)),
            lesson_type=LessonType[data["lesson_type"]],
        )
        return self._subject_repo.save(s)

    def delete_teacher(self, tid: int): self._teacher_repo.delete(tid)
    def delete_room(self, rid: int):    self._room_repo.delete(rid)
    def delete_group(self, gid: int):   self._group_repo.delete(gid)
    def delete_subject(self, sid: int): self._subject_repo.delete(sid)

    # ── Заняття ──────────────────────────────────────────────────

    def get_all_lessons(self) -> list[Lesson]:
        return self._lesson_repo.get_all()

    def get_schedule_for_group(self, group_id: int):
        return self._lesson_repo.get_by_group(group_id)

    def get_schedule_for_teacher(self, teacher_id: int):
        return self._lesson_repo.get_by_teacher(teacher_id)

    def add_lesson(
        self,
        subject_id: int, teacher_id: int, group_id: int,
        room_id: int, day_index: int, slot_number: int
    ) -> tuple[bool, str, Lesson | None]:
        """
        Додає заняття з перевіркою всіх обмежень (Chain of Responsibility).
        Повертає (success, message, lesson).
        """
        subject = self._subject_repo.get_by_id(subject_id)
        teacher = self._teacher_repo.get_by_id(teacher_id)
        group   = self._group_repo.get_by_id(group_id)
        room    = self._room_repo.get_by_id(room_id)

        if not all([subject, teacher, group, room]):
            return False, "Невірні дані: об'єкт не знайдено", None

        slot_key = (day_index, slot_number)
        slots_map = {
            (s.day.index, s.slot_number): s for s in TimeSlot.all_slots()
        }
        time_slot = slots_map.get(slot_key)
        if not time_slot:
            return False, "Невірний часовий слот", None

        lesson = (LessonBuilder()
                  .with_subject(subject)
                  .with_teacher(teacher)
                  .with_group(group)
                  .with_room(room)
                  .with_time_slot(time_slot)
                  .build())

        existing = self._lesson_repo.get_all()
        result = self._scheduler.validate_lesson(lesson, existing)
        if not result.ok:
            return False, result.message, None

        saved = self._lesson_repo.save(lesson)
        self._scheduler.notify_added(saved)
        return True, "Заняття успішно додано", saved

    def auto_schedule(
        self,
        subject_id: int, teacher_id: int,
        group_id: int, room_id: int,
        strategy_name: str = "balanced"
    ) -> tuple[bool, str, Lesson | None]:
        """
        Автоматичний підбір слоту за обраною стратегією.
        """
        strategy_cls = self.STRATEGIES.get(strategy_name, BalancedDayStrategy)
        self._scheduler.set_strategy(strategy_cls())

        subject = self._subject_repo.get_by_id(subject_id)
        teacher = self._teacher_repo.get_by_id(teacher_id)
        group   = self._group_repo.get_by_id(group_id)
        room    = self._room_repo.get_by_id(room_id)

        if not all([subject, teacher, group, room]):
            return False, "Невірні дані: об'єкт не знайдено", None

        existing = self._lesson_repo.get_all()
        time_slot = self._scheduler.suggest_slot(teacher, room, group, existing)

        if not time_slot:
            return False, "Немає вільних слотів для цього набору ресурсів", None

        lesson = (LessonBuilder()
                  .with_subject(subject)
                  .with_teacher(teacher)
                  .with_group(group)
                  .with_room(room)
                  .with_time_slot(time_slot)
                  .build())

        result = self._scheduler.validate_lesson(lesson, existing)
        if not result.ok:
            return False, result.message, None

        saved = self._lesson_repo.save(lesson)
        self._scheduler.notify_added(saved)
        return (True,
                f"Авто-розклад: {time_slot.day.label}, слот {time_slot.slot_number}",
                saved)

    def delete_lesson(self, lesson_id: int):
        self._lesson_repo.delete(lesson_id)
        self._scheduler.notify_removed(lesson_id)

    def clear_schedule(self):
        self._lesson_repo.clear_all()

    def get_conflict_log(self) -> list[str]:
        return self._scheduler.conflict_notifier.conflicts

    def get_statistics(self) -> dict:
        lessons = self._lesson_repo.get_all()
        teachers = self._teacher_repo.get_all()
        rooms    = self._room_repo.get_all()
        groups   = self._group_repo.get_all()

        teacher_load: dict[str, int] = {}
        for l in lessons:
            teacher_load[l.teacher.name] = teacher_load.get(l.teacher.name, 0) + 1

        room_load: dict[str, int] = {}
        for l in lessons:
            room_load[l.room.number] = room_load.get(l.room.number, 0) + 1

        return {
            "total_lessons": len(lessons),
            "total_teachers": len(teachers),
            "total_rooms": len(rooms),
            "total_groups": len(groups),
            "teacher_load": teacher_load,
            "room_load": room_load,
        }
