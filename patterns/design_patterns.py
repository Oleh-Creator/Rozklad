"""
Патерни проєктування для системи управління розкладом.

Реалізовані патерни:
  1. Strategy     — алгоритми оптимізації розкладу
  2. Observer     — повідомлення про конфлікти
  3. Builder      — побудова занять крок за кроком
  4. Singleton    — єдиний екземпляр планувальника
  5. Chain of Responsibility — перевірка обмежень (constraints)
"""

from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional
from models.entities import (
    Lesson, Teacher, Room, Group, Subject, TimeSlot, LessonType
)


# 1. STRATEGY — алгоритм вибору часового слоту

class SlotSelectionStrategy(ABC):
    """Абстрактна стратегія вибору часового слоту."""

    @abstractmethod
    def select_slot(
        self,
        available_slots: list[TimeSlot],
        existing_lessons: list[Lesson],
        group: Group
    ) -> Optional[TimeSlot]:
        ...


class EarlyMorningStrategy(SlotSelectionStrategy):
    """Стратегія: заповнення з початку дня."""

    def select_slot(self, available_slots, existing_lessons, group):
        if not available_slots:
            return None
        return min(available_slots, key=lambda s: (s.day.index, s.slot_number))


class BalancedDayStrategy(SlotSelectionStrategy):
    """Стратегія: рівномірне розподілення занять по днях."""

    def select_slot(self, available_slots, existing_lessons, group):
        if not available_slots:
            return None

        # Рахуємо кількість занять групи по днях
        day_load: dict[int, int] = {}
        for lesson in existing_lessons:
            if lesson.group.id == group.id:
                d = lesson.time_slot.day.index
                day_load[d] = day_load.get(d, 0) + 1

        # Вибираємо слот у найменш завантажений день
        return min(
            available_slots,
            key=lambda s: (day_load.get(s.day.index, 0), s.slot_number)
        )


class AfternoonPreferenceStrategy(SlotSelectionStrategy):
    """Стратегія: перевага другій половині дня (слоти 4-6)."""

    def select_slot(self, available_slots, existing_lessons, group):
        if not available_slots:
            return None
        afternoon = [s for s in available_slots if s.slot_number >= 4]
        pool = afternoon if afternoon else available_slots
        return min(pool, key=lambda s: (s.day.index, s.slot_number))


# 2. OBSERVER — повідомлення про конфлікти та події

@dataclass
class ScheduleEvent:
    """Подія в системі розкладу."""
    event_type: str        # "conflict", "lesson_added", "lesson_removed", "info"
    message: str
    details: dict


class ScheduleObserver(ABC):
    """Абстрактний спостерігач."""

    @abstractmethod
    def on_event(self, event: ScheduleEvent) -> None:
        ...


class EventLog(ScheduleObserver):
    """Журнал подій — зберігає всі події в пам'яті."""

    def __init__(self):
        self._events: list[ScheduleEvent] = []

    def on_event(self, event: ScheduleEvent) -> None:
        self._events.append(event)

    def get_all(self) -> list[ScheduleEvent]:
        return list(self._events)

    def get_conflicts(self) -> list[ScheduleEvent]:
        return [e for e in self._events if e.event_type == "conflict"]

    def clear(self):
        self._events.clear()


class ConflictNotifier(ScheduleObserver):
    """Збирає конфлікти розкладу для відображення у UI."""

    def __init__(self):
        self.conflicts: list[str] = []

    def on_event(self, event: ScheduleEvent) -> None:
        if event.event_type == "conflict":
            self.conflicts.append(event.message)

    def clear(self):
        self.conflicts.clear()


class ScheduleSubject:
    """Видавець подій (Subject у патерні Observer)."""

    def __init__(self):
        self._observers: list[ScheduleObserver] = []

    def attach(self, observer: ScheduleObserver) -> None:
        self._observers.append(observer)

    def detach(self, observer: ScheduleObserver) -> None:
        self._observers.remove(observer)

    def notify(self, event: ScheduleEvent) -> None:
        for obs in self._observers:
            obs.on_event(event)


# 3. CHAIN OF RESPONSIBILITY — перевірка обмежень

@dataclass
class ConstraintResult:
    ok: bool
    message: str = ""


class ConstraintHandler(ABC):
    """Базовий обробник ланцюга обмежень."""

    def __init__(self):
        self._next: Optional[ConstraintHandler] = None

    def set_next(self, handler: ConstraintHandler) -> ConstraintHandler:
        self._next = handler
        return handler

    def check(self, lesson: Lesson, existing: list[Lesson]) -> ConstraintResult:
        result = self._handle(lesson, existing)
        if not result.ok:
            return result
        if self._next:
            return self._next.check(lesson, existing)
        return ConstraintResult(ok=True)

    @abstractmethod
    def _handle(self, lesson: Lesson, existing: list[Lesson]) -> ConstraintResult:
        ...


class TeacherConflictHandler(ConstraintHandler):
    """Перевіряє: чи не зайнятий викладач у цей слот."""

    def _handle(self, lesson, existing):
        for ex in existing:
            if (ex.id != lesson.id
                    and ex.teacher.id == lesson.teacher.id
                    and ex.time_slot == lesson.time_slot):
                return ConstraintResult(
                    ok=False,
                    message=(f"Викладач «{lesson.teacher.name}» вже має заняття "
                             f"у {lesson.time_slot}")
                )
        return ConstraintResult(ok=True)


class RoomConflictHandler(ConstraintHandler):
    """Перевіряє: чи не зайнята аудиторія у цей слот."""

    def _handle(self, lesson, existing):
        for ex in existing:
            if (ex.id != lesson.id
                    and ex.room.id == lesson.room.id
                    and ex.time_slot == lesson.time_slot):
                return ConstraintResult(
                    ok=False,
                    message=(f"Аудиторія {lesson.room.number} вже зайнята "
                             f"у {lesson.time_slot}")
                )
        return ConstraintResult(ok=True)


class GroupConflictHandler(ConstraintHandler):
    """Перевіряє: чи немає перетину занять у групи."""

    def _handle(self, lesson, existing):
        for ex in existing:
            if (ex.id != lesson.id
                    and ex.group.id == lesson.group.id
                    and ex.time_slot == lesson.time_slot):
                return ConstraintResult(
                    ok=False,
                    message=(f"Група «{lesson.group.name}» вже має заняття "
                             f"у {lesson.time_slot}")
                )
        return ConstraintResult(ok=True)


class RoomSuitabilityHandler(ConstraintHandler):
    """Перевіряє відповідність аудиторії типу заняття та розміру групи."""

    def _handle(self, lesson, existing):
        if not lesson.room.is_suitable_for(
            lesson.subject.lesson_type, lesson.group.size
        ):
            return ConstraintResult(
                ok=False,
                message=(f"Аудиторія {lesson.room.number} не підходить для "
                         f"{lesson.subject.lesson_type.value} "
                         f"(група: {lesson.group.size} ос., "
                         f"місць: {lesson.room.capacity})")
            )
        return ConstraintResult(ok=True)


class TeacherSubjectHandler(ConstraintHandler):
    """Перевіряє: чи викладач може викладати цей предмет."""

    def _handle(self, lesson, existing):
        if (lesson.teacher.subjects
                and lesson.subject.name not in lesson.teacher.subjects):
            return ConstraintResult(
                ok=False,
                message=(f"Викладач «{lesson.teacher.name}» не може викладати "
                         f"«{lesson.subject.name}»")
            )
        return ConstraintResult(ok=True)


def build_constraint_chain() -> ConstraintHandler:
    """Фабрика: будує ланцюг обмежень."""
    teacher_conflict  = TeacherConflictHandler()
    room_conflict     = RoomConflictHandler()
    group_conflict    = GroupConflictHandler()
    room_suitability  = RoomSuitabilityHandler()
    teacher_subject   = TeacherSubjectHandler()

    teacher_conflict.set_next(room_conflict)\
                    .set_next(group_conflict)\
                    .set_next(room_suitability)\
                    .set_next(teacher_subject)
    return teacher_conflict


# 4. BUILDER — побудова об'єкта Lesson

class LessonBuilder:
    """Будівельник занять — дозволяє поетапно конструювати Lesson."""

    def __init__(self):
        self._id: Optional[int] = None
        self._subject: Optional[Subject] = None
        self._teacher: Optional[Teacher] = None
        self._group: Optional[Group] = None
        self._room: Optional[Room] = None
        self._time_slot: Optional[TimeSlot] = None

    def with_id(self, lid: int) -> LessonBuilder:
        self._id = lid
        return self

    def with_subject(self, s: Subject) -> LessonBuilder:
        self._subject = s
        return self

    def with_teacher(self, t: Teacher) -> LessonBuilder:
        self._teacher = t
        return self

    def with_group(self, g: Group) -> LessonBuilder:
        self._group = g
        return self

    def with_room(self, r: Room) -> LessonBuilder:
        self._room = r
        return self

    def with_time_slot(self, ts: TimeSlot) -> LessonBuilder:
        self._time_slot = ts
        return self

    def build(self) -> Lesson:
        missing = [
            name for name, val in [
                ("subject",   self._subject),
                ("teacher",   self._teacher),
                ("group",     self._group),
                ("room",      self._room),
                ("time_slot", self._time_slot),
            ] if val is None
        ]
        if missing:
            raise ValueError(f"LessonBuilder: не задані поля {missing}")
        return Lesson(
            id=self._id,
            subject=self._subject,
            teacher=self._teacher,
            group=self._group,
            room=self._room,
            time_slot=self._time_slot
        )


# 5. SINGLETON — єдиний планувальник

class SchedulerMeta(type):
    _instances: dict = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super().__call__(*args, **kwargs)
        return cls._instances[cls]


class Scheduler(metaclass=SchedulerMeta):
    """
    Центральний планувальник (Singleton).
    Координує всі підсистеми: Strategy, Observer, Chain of Responsibility.
    """

    def __init__(self):
        # Observer
        self._subject    = ScheduleSubject()
        self.event_log   = EventLog()
        self.conflict_notifier = ConflictNotifier()
        self._subject.attach(self.event_log)
        self._subject.attach(self.conflict_notifier)

        # Strategy (замовчування — збалансований)
        self._strategy: SlotSelectionStrategy = BalancedDayStrategy()

        # Chain of Responsibility
        self._constraint_chain = build_constraint_chain()

    # ── Керування стратегією ────────────────────────────────────
    def set_strategy(self, strategy: SlotSelectionStrategy) -> None:
        self._strategy = strategy

    def get_strategy_name(self) -> str:
        return type(self._strategy).__name__

    # ── Перевірка обмежень ──────────────────────────────────────
    def validate_lesson(
        self, lesson: Lesson, existing: list[Lesson]
    ) -> ConstraintResult:
        result = self._constraint_chain.check(lesson, existing)
        if not result.ok:
            self._subject.notify(ScheduleEvent(
                event_type="conflict",
                message=result.message,
                details={"lesson": str(lesson)}
            ))
        return result

    # ── Авто-підбір слоту ───────────────────────────────────────
    def suggest_slot(
        self,
        teacher: Teacher,
        room: Room,
        group: Group,
        existing: list[Lesson]
    ) -> Optional[TimeSlot]:
        """
        Підбирає вільний часовий слот за поточною стратегією,
        враховуючи всі обмеження.
        """
        all_slots = TimeSlot.all_slots()

        busy_teacher = {(l.time_slot.day.index, l.time_slot.slot_number)
                        for l in existing if l.teacher.id == teacher.id}
        busy_room    = {(l.time_slot.day.index, l.time_slot.slot_number)
                        for l in existing if l.room.id == room.id}
        busy_group   = {(l.time_slot.day.index, l.time_slot.slot_number)
                        for l in existing if l.group.id == group.id}

        available = [
            s for s in all_slots
            if (s.day.index, s.slot_number) not in busy_teacher
            and (s.day.index, s.slot_number) not in busy_room
            and (s.day.index, s.slot_number) not in busy_group
        ]

        return self._strategy.select_slot(available, existing, group)

    # ── Сповіщення ──────────────────────────────────────────────
    def notify_added(self, lesson: Lesson):
        self._subject.notify(ScheduleEvent(
            event_type="lesson_added",
            message=f"Додано заняття: {lesson}",
            details=lesson.to_dict()
        ))

    def notify_removed(self, lesson_id: int):
        self._subject.notify(ScheduleEvent(
            event_type="lesson_removed",
            message=f"Видалено заняття #{lesson_id}",
            details={"id": lesson_id}
        ))