"""
Модуль моделей даних для системи управління розкладом.

Містить доменні сутності та Value Objects:
    - DayOfWeek  : перелік днів тижня
    - LessonType : типи занять (лекція, практика, лаб, семінар)
    - RoomType   : типи аудиторій
    - Teacher    : сутність викладача
    - Room       : сутність аудиторії
    - Group      : навчальна група
    - Subject    : навчальна дисципліна
    - TimeSlot   : незмінний Value Object часового слоту
    - Lesson     : заняття як результат планування

Патерни: Value Object, Entity, Repository Pattern (інтерфейси)
"""

from dataclasses import dataclass, field
from datetime import time
from typing import Optional
from enum import Enum


class DayOfWeek(Enum):
    """
    Перелік днів тижня з українськими назвами та числовим індексом.

    Кожен елемент зберігає:
        label (str) : україномовна назва дня
        index (int) : числовий індекс (0=Пн, 5=Сб)

    Приклад::

        DayOfWeek.MONDAY.label  # 'Понеділок'
        DayOfWeek.from_index(2) # DayOfWeek.WEDNESDAY
    """

    MONDAY    = ("Понеділок", 0)
    TUESDAY   = ("Вівторок",  1)
    WEDNESDAY = ("Середа",    2)
    THURSDAY  = ("Четвер",    3)
    FRIDAY    = ("П'ятниця",  4)
    SATURDAY  = ("Субота",    5)

    def __init__(self, label: str, index: int) -> None:
        """Ініціалізує елемент переліку з назвою та індексом."""
        self.label = label
        self.index = index

    @classmethod
    def from_index(cls, idx: int) -> "DayOfWeek":
        """
        Повертає елемент переліку за числовим індексом.

        Args:
            idx: числовий індекс дня (0–5).

        Returns:
            Відповідний елемент DayOfWeek.

        Raises:
            ValueError: якщо індекс не відповідає жодному дню.
        """
        for d in cls:
            if d.index == idx:
                return d
        raise ValueError(f"Невідомий день: {idx}")


class LessonType(Enum):
    """
    Тип навчального заняття.

    Значення:
        LECTURE  : лекційне заняття
        PRACTICE : практичне заняття
        LAB      : лабораторна робота
        SEMINAR  : семінарське заняття
    """

    LECTURE  = "Лекція"
    PRACTICE = "Практика"
    LAB      = "Лабораторна"
    SEMINAR  = "Семінар"


class RoomType(Enum):
    """
    Тип навчальної аудиторії.

    Значення:
        LECTURE_HALL  : велика лекційна аудиторія
        COMPUTER_LAB  : комп'ютерна лабораторія
        LABORATORY    : науково-практична лабораторія
        SEMINAR_ROOM  : кімната для семінарів та практик
    """

    LECTURE_HALL = "Лекційна аудиторія"
    COMPUTER_LAB = "Комп'ютерна лабораторія"
    LABORATORY   = "Лабораторія"
    SEMINAR_ROOM = "Семінарська кімната"


@dataclass
class Teacher:
    """
    Сутність викладача навчального закладу.

    Attributes:
        id         : унікальний ідентифікатор.
        name       : повне ім'я викладача (ПІБ).
        department : назва кафедри.
        subjects   : список назв дисциплін, які може викладати.

    Приклад::

        t = Teacher(1, "Іваненко І.І.", "Кафедра ІТ", ["Python", "Java"])
        t.can_teach("Python")  # True
    """

    id: int
    name: str
    department: str
    subjects: list = field(default_factory=list)

    def can_teach(self, subject: str) -> bool:
        """
        Перевіряє, чи може викладач вести зазначену дисципліну.

        Args:
            subject: назва дисципліни.

        Returns:
            True якщо дисципліна є у списку викладача, False інакше.
        """
        return subject in self.subjects

    def __repr__(self) -> str:
        return f"Teacher({self.id}, {self.name})"


@dataclass
class Room:
    """
    Сутність навчальної аудиторії.

    Attributes:
        id        : унікальний ідентифікатор.
        number    : номер аудиторії (напр. '101-А').
        capacity  : максимальна кількість місць.
        room_type : тип аудиторії (RoomType).
        equipment : список наявного обладнання.

    Приклад::

        r = Room(1, "305", 30, RoomType.COMPUTER_LAB)
        r.is_suitable_for(LessonType.LAB, 25)  # True
    """

    id: int
    number: str
    capacity: int
    room_type: RoomType
    equipment: list = field(default_factory=list)

    def is_suitable_for(self, lesson_type: LessonType, group_size: int) -> bool:
        """
        Перевіряє придатність аудиторії для заняття.

        Логіка перевірки:
            - Якщо група більша за місткість — False.
            - Лекції проводяться лише у LECTURE_HALL.
            - Лабораторні — у COMPUTER_LAB або LABORATORY.
            - Практики та семінари — у будь-якій аудиторії достатнього розміру.

        Args:
            lesson_type : тип заняття.
            group_size  : кількість студентів у групі.

        Returns:
            True якщо аудиторія підходить, False інакше.
        """
        if group_size > self.capacity:
            return False
        if lesson_type == LessonType.LECTURE:
            return self.room_type == RoomType.LECTURE_HALL
        if lesson_type == LessonType.LAB:
            return self.room_type in (RoomType.COMPUTER_LAB, RoomType.LABORATORY)
        return True

    def __repr__(self) -> str:
        return f"Room({self.number}, cap={self.capacity})"


@dataclass
class Group:
    """
    Навчальна група студентів.

    Attributes:
        id        : унікальний ідентифікатор.
        name      : назва групи (напр. 'КН-21').
        size      : кількість студентів.
        year      : курс навчання (1–6).
        specialty : назва спеціальності.
    """

    id: int
    name: str
    size: int
    year: int
    specialty: str

    def __repr__(self) -> str:
        return f"Group({self.name})"


@dataclass
class Subject:
    """
    Навчальна дисципліна.

    Attributes:
        id                 : унікальний ідентифікатор.
        name               : назва дисципліни.
        hours_per_week     : кількість годин на тиждень.
        lesson_type        : тип заняття (LessonType).
        required_equipment : перелік необхідного обладнання.
    """

    id: int
    name: str
    hours_per_week: int
    lesson_type: LessonType
    required_equipment: list = field(default_factory=list)

    def __repr__(self) -> str:
        return f"Subject({self.name})"


@dataclass
class TimeSlot:
    """
    Часовий слот навчального розкладу (Value Object — незмінний).

    Attributes:
        day         : день тижня (DayOfWeek).
        slot_number : номер пари (1–6).
        start_time  : час початку заняття.
        end_time    : час закінчення заняття.

    Value Object: два слоти рівні, якщо мають однаковий день і номер пари.

    Приклад::

        slots = TimeSlot.all_slots()  # усі 36 слотів тижня
    """

    day: DayOfWeek
    slot_number: int
    start_time: time
    end_time: time

    @staticmethod
    def all_slots() -> list:
        """
        Генерує повний список слотів для всього навчального тижня.

        Returns:
            Список із 36 TimeSlot об'єктів (6 днів × 6 пар).
        """
        times = [
            (time(8,  0),  time(9,  35)),
            (time(9,  45), time(11, 20)),
            (time(11, 30), time(13,  5)),
            (time(13, 30), time(15,  5)),
            (time(15, 15), time(16, 50)),
            (time(17,  0), time(18, 35)),
        ]
        slots = []
        for day in DayOfWeek:
            for i, (start, end) in enumerate(times, start=1):
                slots.append(TimeSlot(day, i, start, end))
        return slots

    def __hash__(self) -> int:
        """Хеш визначається днем і номером пари."""
        return hash((self.day, self.slot_number))

    def __eq__(self, other: object) -> bool:
        """Рівність визначається днем і номером пари."""
        if not isinstance(other, TimeSlot):
            return NotImplemented
        return self.day == other.day and self.slot_number == other.slot_number

    def __repr__(self) -> str:
        return f"{self.day.label} {self.slot_number}({self.start_time}–{self.end_time})"


@dataclass
class Lesson:
    """
    Заняття у розкладі — результат планування.

    Об'єднує дисципліну, викладача, групу, аудиторію та часовий слот
    в єдину сутність розкладу.

    Attributes:
        id        : унікальний ідентифікатор (None до збереження в БД).
        subject   : навчальна дисципліна.
        teacher   : викладач.
        group     : навчальна група.
        room      : аудиторія.
        time_slot : часовий слот.

    Приклад::

        lesson.to_dict()  # серіалізація для JSON API
    """

    id: Optional[int]
    subject: Subject
    teacher: Teacher
    group: Group
    room: Room
    time_slot: TimeSlot

    def to_dict(self) -> dict:
        """
        Серіалізує заняття у словник для JSON API.

        Returns:
            Словник з усіма полями заняття у рядковому форматі.
        """
        return {
            "id":          self.id,
            "subject":     self.subject.name,
            "lesson_type": self.subject.lesson_type.value,
            "teacher":     self.teacher.name,
            "group":       self.group.name,
            "room":        self.room.number,
            "day":         self.time_slot.day.label,
            "day_index":   self.time_slot.day.index,
            "slot":        self.time_slot.slot_number,
            "start":       str(self.time_slot.start_time)[:-3],
            "end":         str(self.time_slot.end_time)[:-3],
        }

    def __repr__(self) -> str:
        return (f"Lesson({self.subject.name} | {self.teacher.name} | "
                f"{self.room.number} | {self.time_slot})")