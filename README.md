# Система управління розкладом навчального закладу
## Предмет: Рефакторинг коду

---

## Реалізовані патерни проєктування

| Патерн | Файл | Призначення |
|--------|------|-------------|
| **Chain of Responsibility** | `patterns/design_patterns.py` | Ланцюг перевірок: TeacherConflict → RoomConflict → GroupConflict → RoomSuitability → TeacherSubject |
| **Strategy** | `patterns/design_patterns.py` | Алгоритми вибору слоту: `BalancedDayStrategy`, `EarlyMorningStrategy`, `AfternoonPreferenceStrategy` |
| **Observer** | `patterns/design_patterns.py` | `ScheduleSubject` → `EventLog`, `ConflictNotifier` |
| **Builder** | `patterns/design_patterns.py` | `LessonBuilder` — поетапне конструювання заняття |
| **Singleton** | `patterns/design_patterns.py` | `Scheduler` — єдиний планувальник |
| **Repository** | `models/repositories.py` | `TeacherRepository`, `RoomRepository`, `LessonRepository` тощо |

---

## Встановлення та запуск

### Вимоги
- Python 3.10 або новіше
- pip

### Кроки

```bash
# 1. Розпакуйте архів
cd schedule_system

# 2. (Рекомендовано) Створіть віртуальне середовище
python -m venv venv
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# 3. Встановіть залежності
pip install -r requirements.txt

# 4. (Необов'язково) Завантажте демо-дані
python seed_data.py

# 5. Запустіть сервер
python app.py
```

### Відкрийте браузер
```
http://localhost:5000
```

---

## Структура проєкту

```
schedule_system/
├── app.py                        # Flask застосунок (точка входу)
├── seed_data.py                  # Скрипт демо-даних
├── requirements.txt
├── models/
│   ├── entities.py               # Доменні моделі (Teacher, Room, Group, Subject, Lesson, TimeSlot)
│   └── repositories.py          # Шар даних (Repository Pattern + SQLite)
├── patterns/
│   └── design_patterns.py       # Усі патерни (Strategy, Observer, Builder, Singleton, Chain)
├── services/
│   └── schedule_service.py      # Сервісний шар (бізнес-логіка, Facade)
├── templates/
│   └── index.html               # Веб-інтерфейс (SPA)
└── static/
    ├── css/style.css
    └── js/app.js
```

---

## Функціональність

- **Управління довідниками**: викладачі, аудиторії, групи, дисципліни
- **Ручне додавання** занять з автоматичною перевіркою конфліктів
- **Авто-підбір слоту** за трьома стратегіями
- **Тижневий розклад** з фільтрацією по групі / викладачу
- **Журнал конфліктів** та статистика навантаження
- **База даних SQLite** — дані зберігаються між запусками

---

## Рефакторинг: ключові принципи

1. **Single Responsibility** — кожен клас має одну відповідальність
2. **Open/Closed** — нові стратегії додаються без зміни планувальника
3. **Dependency Inversion** — сервіс залежить від абстракцій репозиторіїв
4. **DRY** — повторна логіка винесена у базові класи
5. **Type Hints** — повне анотування типів Python 3.10+
