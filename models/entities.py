"""
Модуль моделей даних для системи управління розкладом.
Патерни: Value Object, Entity, Repository Pattern (інтерфейси)
"""

from dataclasses import dataclass, field
from datetime import time
from typing import Optional
from enum import Enum


# ─────────────────────────────────────────────
# Перелічення (Enum) — Value Objects
# ─────────────────────────────────────────────

class DayOfWeek(Enum):
    MONDAY = ("Понеділок", 0)
    TUESDAY = ("Вівторок", 1)
    WEDNESDAY = ("Середа", 2)
    THURSDAY = ("Четвер", 3)
    FRIDAY = ("П'ятниця", 4)
    SATURDAY = ("Субота", 5)

    def __init__(self, label: str, index: int):
        self.label = label
        self.index = index

    @classmethod
    def from_index(cls, idx: int) -> "DayOfWeek":
        for d in cls:
            if d.index == idx:
                return d
        raise ValueError(f"Невідомий день: {idx}")


class LessonType(Enum):
    LECTURE = "Лекція"
    PRACTICE = "Практика"
    LAB = "Лабораторна"
    SEMINAR = "Семінар"


class RoomType(Enum):
    LECTURE_HALL = "Лекційна аудиторія"
    COMPUTER_LAB = "Комп'ютерна лабораторія"
    LABORATORY = "Лабораторія"
    SEMINAR_ROOM = "Семінарська кімната"


# ─────────────────────────────────────────────
# Сутності (Entity)
# ─────────────────────────────────────────────

@dataclass
class Teacher:
    """Викладач — незмінна сутність із унікальним ID."""
    id: int
    name: str
    department: str
    subjects: list = field(default_factory=list)   # назви дисциплін

    def can_teach(self, subject: str) -> bool:
        return subject in self.subjects

    def __repr__(self) -> str:
        return f"Teacher({self.id}, {self.name})"


@dataclass
class Room:
    """Аудиторія."""
    id: int
    number: str
    capacity: int
    room_type: RoomType
    equipment: list = field(default_factory=list)

    def is_suitable_for(self, lesson_type: LessonType, group_size: int) -> bool:
        if group_size > self.capacity:
            return False
        type_map = {
            LessonType.LECTURE: RoomType.LECTURE_HALL,
            LessonType.LAB: RoomType.COMPUTER_LAB,
            LessonType.SEMINAR: RoomType.SEMINAR_ROOM,
            LessonType.PRACTICE: RoomType.SEMINAR_ROOM,
        }
        preferred = type_map.get(lesson_type)
        # Лекції — тільки в лекційних; решта може йти у семінарській або лекційній
        if lesson_type == LessonType.LECTURE:
            return self.room_type == RoomType.LECTURE_HALL
        if lesson_type == LessonType.LAB:
            return self.room_type in (RoomType.COMPUTER_LAB, RoomType.LABORATORY)
        return True

    def __repr__(self) -> str:
        return f"Room({self.number}, cap={self.capacity})"


@dataclass
class Group:
    """Навчальна група."""
    id: int
    name: str
    size: int
    year: int
    specialty: str

    def __repr__(self) -> str:
        return f"Group({self.name})"


@dataclass
class Subject:
    """Навчальна дисципліна."""
    id: int
    name: str
    hours_per_week: int
    lesson_type: LessonType
    required_equipment: list = field(default_factory=list)

    def __repr__(self) -> str:
        return f"Subject({self.name})"


@dataclass
class TimeSlot:
    """Часовий слот — Value Object (незмінний)."""
    day: DayOfWeek
    slot_number: int          # 1..8
    start_time: time
    end_time: time

    @staticmethod
    def all_slots() -> list:
        """Повертає всі доступні слоти тижня."""
        times = [
            (time(8, 0),  time(9, 35)),
            (time(9, 45), time(11, 20)),
            (time(11, 30), time(13, 5)),
            (time(13, 30), time(15, 5)),
            (time(15, 15), time(16, 50)),
            (time(17, 0), time(18, 35)),
        ]
        slots = []
        for day in DayOfWeek:
            for i, (start, end) in enumerate(times, start=1):
                slots.append(TimeSlot(day, i, start, end))
        return slots

    def __hash__(self):
        return hash((self.day, self.slot_number))

    def __eq__(self, other):
        return self.day == other.day and self.slot_number == other.slot_number

    def __repr__(self) -> str:
        return f"{self.day.label} {self.slot_number}({self.start_time}–{self.end_time})"


@dataclass
class Lesson:
    """Заняття — результат планування (Entity)."""
    id: Optional[int]
    subject: Subject
    teacher: Teacher
    group: Group
    room: Room
    time_slot: TimeSlot

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "subject": self.subject.name,
            "lesson_type": self.subject.lesson_type.value,
            "teacher": self.teacher.name,
            "group": self.group.name,
            "room": self.room.number,
            "day": self.time_slot.day.label,
            "day_index": self.time_slot.day.index,
            "slot": self.time_slot.slot_number,
            "start": str(self.time_slot.start_time)[:-3],
            "end": str(self.time_slot.end_time)[:-3],
        }

    def __repr__(self) -> str:
        return (f"Lesson({self.subject.name} | {self.teacher.name} | "
                f"{self.room.number} | {self.time_slot})")
