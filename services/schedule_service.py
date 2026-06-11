"""
Сервісний шар системи управління розкладом.

Реалізує патерн Facade — надає єдиний інтерфейс до всіх підсистем:
репозиторіїв, планувальника та патернів проєктування.

Класи:
    ScheduleService : головний сервіс бізнес-логіки.
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


class ScheduleService:
    """
    Фасад над усіма підсистемами системи управління розкладом.

    Координує репозиторії даних та патерни проєктування:
        - Repository  : збереження та отримання сутностей з БД
        - Strategy    : вибір алгоритму авто-планування
        - Builder     : конструювання об'єктів Lesson
        - Chain of Responsibility : валідація обмежень
        - Observer    : журналювання подій

    Attributes:
        STRATEGIES: словник доступних стратегій планування.

    Приклад::

        svc = ScheduleService()
        teachers = svc.get_teachers()
        ok, msg, lesson = svc.auto_schedule(1, 2, 3, 4, strategy_name='balanced')
    """

    STRATEGIES = {
        "balanced":  BalancedDayStrategy,
        "early":     EarlyMorningStrategy,
        "afternoon": AfternoonPreferenceStrategy,
    }

    def __init__(self) -> None:
        """Ініціалізує репозиторії та планувальник."""
        self._teacher_repo = TeacherRepository()
        self._room_repo    = RoomRepository()
        self._group_repo   = GroupRepository()
        self._subject_repo = SubjectRepository()
        self._lesson_repo  = LessonRepository()
        self._scheduler    = Scheduler()

    # ── Довідники ────────────────────────────────────────────────

    def get_teachers(self) -> list[Teacher]:
        """Повертає список усіх викладачів із бази даних."""
        return self._teacher_repo.get_all()

    def get_rooms(self) -> list[Room]:
        """Повертає список усіх аудиторій із бази даних."""
        return self._room_repo.get_all()

    def get_groups(self) -> list[Group]:
        """Повертає список усіх навчальних груп із бази даних."""
        return self._group_repo.get_all()

    def get_subjects(self) -> list[Subject]:
        """Повертає список усіх дисциплін із бази даних."""
        return self._subject_repo.get_all()

    def save_teacher(self, data: dict) -> Teacher:
        """
        Зберігає або оновлює викладача в базі даних.

        Args:
            data: словник з полями name, department, subjects, id (опційно).

        Returns:
            Збережений об'єкт Teacher з присвоєним id.
        """
        t = Teacher(
            id=data.get("id"),
            name=data["name"].strip(),
            department=data["department"].strip(),
            subjects=[s.strip() for s in data.get("subjects", []) if s.strip()]
        )
        return self._teacher_repo.save(t)

    def save_room(self, data: dict) -> Room:
        """
        Зберігає або оновлює аудиторію в базі даних.

        Args:
            data: словник з полями number, capacity, room_type, id (опційно).

        Returns:
            Збережений об'єкт Room з присвоєним id.
        """
        r = Room(
            id=data.get("id"),
            number=data["number"].strip(),
            capacity=int(data["capacity"]),
            room_type=RoomType[data["room_type"]],
            equipment=[]
        )
        return self._room_repo.save(r)

    def save_group(self, data: dict) -> Group:
        """
        Зберігає або оновлює навчальну групу в базі даних.

        Args:
            data: словник з полями name, size, year, specialty, id (опційно).

        Returns:
            Збережений об'єкт Group з присвоєним id.
        """
        g = Group(
            id=data.get("id"),
            name=data["name"].strip(),
            size=int(data["size"]),
            year=int(data["year"]),
            specialty=data["specialty"].strip()
        )
        return self._group_repo.save(g)

    def save_subject(self, data: dict) -> Subject:
        """
        Зберігає або оновлює навчальну дисципліну в базі даних.

        Args:
            data: словник з полями name, hours_per_week, lesson_type, id (опційно).

        Returns:
            Збережений об'єкт Subject з присвоєним id.
        """
        s = Subject(
            id=data.get("id"),
            name=data["name"].strip(),
            hours_per_week=int(data.get("hours_per_week", 2)),
            lesson_type=LessonType[data["lesson_type"]],
        )
        return self._subject_repo.save(s)

    def delete_teacher(self, tid: int) -> None:
        """Видаляє викладача за ідентифікатором."""
        self._teacher_repo.delete(tid)

    def delete_room(self, rid: int) -> None:
        """Видаляє аудиторію за ідентифікатором."""
        self._room_repo.delete(rid)

    def delete_group(self, gid: int) -> None:
        """Видаляє навчальну групу за ідентифікатором."""
        self._group_repo.delete(gid)

    def delete_subject(self, sid: int) -> None:
        """Видаляє навчальну дисципліну за ідентифікатором."""
        self._subject_repo.delete(sid)

    # ── Заняття ──────────────────────────────────────────────────

    def get_all_lessons(self) -> list[Lesson]:
        """Повертає всі заняття розкладу."""
        return self._lesson_repo.get_all()

    def get_schedule_for_group(self, group_id: int) -> list[Lesson]:
        """
        Повертає розклад для конкретної навчальної групи.

        Args:
            group_id: ідентифікатор групи.

        Returns:
            Список занять групи відсортований за часом.
        """
        return self._lesson_repo.get_by_group(group_id)

    def get_schedule_for_teacher(self, teacher_id: int) -> list[Lesson]:
        """
        Повертає розклад для конкретного викладача.

        Args:
            teacher_id: ідентифікатор викладача.

        Returns:
            Список занять викладача відсортований за часом.
        """
        return self._lesson_repo.get_by_teacher(teacher_id)

    def add_lesson(
        self,
        subject_id: int, teacher_id: int, group_id: int,
        room_id: int, day_index: int, slot_number: int
    ) -> tuple[bool, str, Lesson | None]:
        """
        Додає заняття до розкладу вручну з перевіркою всіх обмежень.

        Використовує патерн Chain of Responsibility для послідовної
        перевірки: конфлікт викладача → конфлікт аудиторії →
        конфлікт групи → придатність аудиторії → кваліфікація викладача.

        Args:
            subject_id  : ідентифікатор дисципліни.
            teacher_id  : ідентифікатор викладача.
            group_id    : ідентифікатор навчальної групи.
            room_id     : ідентифікатор аудиторії.
            day_index   : індекс дня тижня (0=Пн, 5=Сб).
            slot_number : номер пари (1–6).

        Returns:
            Кортеж (success, message, lesson):
                success : True якщо заняття успішно додано.
                message : текст результату або опис конфлікту.
                lesson  : об'єкт Lesson або None при помилці.
        """
        subject = self._subject_repo.get_by_id(subject_id)
        teacher = self._teacher_repo.get_by_id(teacher_id)
        group   = self._group_repo.get_by_id(group_id)
        room    = self._room_repo.get_by_id(room_id)

        if not all([subject, teacher, group, room]):
            return False, "Невірні дані: об'єкт не знайдено", None

        slot_key  = (day_index, slot_number)
        slots_map = {(s.day.index, s.slot_number): s for s in TimeSlot.all_slots()}
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
        result   = self._scheduler.validate_lesson(lesson, existing)
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
        Автоматично підбирає вільний часовий слот за обраною стратегією.

        Використовує патерн Strategy для вибору алгоритму:
            - 'balanced'  : рівномірний розподіл по днях тижня
            - 'early'     : найраніший доступний слот
            - 'afternoon' : перевага слотам після обіду (4–6)

        Args:
            subject_id    : ідентифікатор дисципліни.
            teacher_id    : ідентифікатор викладача.
            group_id      : ідентифікатор навчальної групи.
            room_id       : ідентифікатор аудиторії.
            strategy_name : назва стратегії ('balanced', 'early', 'afternoon').

        Returns:
            Кортеж (success, message, lesson):
                success : True якщо слот знайдено і заняття додано.
                message : опис знайденого слоту або причина відмови.
                lesson  : об'єкт Lesson або None при помилці.
        """
        strategy_cls = self.STRATEGIES.get(strategy_name, BalancedDayStrategy)
        self._scheduler.set_strategy(strategy_cls())

        subject = self._subject_repo.get_by_id(subject_id)
        teacher = self._teacher_repo.get_by_id(teacher_id)
        group   = self._group_repo.get_by_id(group_id)
        room    = self._room_repo.get_by_id(room_id)

        if not all([subject, teacher, group, room]):
            return False, "Невірні дані: об'єкт не знайдено", None

        existing  = self._lesson_repo.get_all()
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

    def delete_lesson(self, lesson_id: int) -> None:
        """
        Видаляє заняття з розкладу та сповіщає спостерігачів.

        Args:
            lesson_id: ідентифікатор заняття.
        """
        self._lesson_repo.delete(lesson_id)
        self._scheduler.notify_removed(lesson_id)

    def clear_schedule(self) -> None:
        """Видаляє всі заняття з розкладу."""
        self._lesson_repo.clear_all()

    def get_conflict_log(self) -> list[str]:
        """
        Повертає журнал конфліктів розкладу.

        Returns:
            Список рядків з описом кожного виявленого конфлікту.
        """
        return self._scheduler.conflict_notifier.conflicts

    def get_statistics(self) -> dict:
        """
        Обчислює статистику завантаженості розкладу.

        Returns:
            Словник зі статистикою:
                total_lessons  : загальна кількість занять
                total_teachers : кількість викладачів
                total_rooms    : кількість аудиторій
                total_groups   : кількість груп
                teacher_load   : словник {ім'я: кількість занять}
                room_load      : словник {номер: кількість занять}
        """
        lessons  = self._lesson_repo.get_all()
        teachers = self._teacher_repo.get_all()
        rooms    = self._room_repo.get_all()
        groups   = self._group_repo.get_all()

        teacher_load: dict[str, int] = {}
        for lesson in lessons:
            teacher_load[lesson.teacher.name] = (
                teacher_load.get(lesson.teacher.name, 0) + 1
            )

        room_load: dict[str, int] = {}
        for lesson in lessons:
            room_load[lesson.room.number] = (
                room_load.get(lesson.room.number, 0) + 1
            )

        return {
            "total_lessons":  len(lessons),
            "total_teachers": len(teachers),
            "total_rooms":    len(rooms),
            "total_groups":   len(groups),
            "teacher_load":   teacher_load,
            "room_load":      room_load,
        }