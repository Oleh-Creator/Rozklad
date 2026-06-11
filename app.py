"""
Flask веб-застосунок — система управління розкладом.
Точка входу: python app.py
"""

import os
import json
from flask import Flask, render_template, request, jsonify, redirect, url_for
from flask_wtf.csrf import CSRFProtect
from models.repositories import init_db
from services.schedule_service import ScheduleService
from models.entities import LessonType, RoomType, DayOfWeek

app = Flask(__name__)
# SECRET_KEY береться виключно зі змінної середовища (не хардкодиться)
_secret = os.environ.get("FLASK_SECRET")
if not _secret:
    _secret = os.urandom(32)
app.config["SECRET_KEY"] = _secret
app.config["WTF_CSRF_TIME_LIMIT"] = 3600
csrf = CSRFProtect(app)

service = ScheduleService()

MSG_DELETED = "Видалено"


# ═══════════════════════════════════════════════════════════════
# Допоміжні функції
# ═══════════════════════════════════════════════════════════════

# JSON API не потребує CSRF-токену (захист через Content-Type: application/json)
@app.before_request
def exempt_json_api_from_csrf():
    if request.path.startswith("/api/") and request.is_json:
        pass  # flask-wtf перевіряє тільки форми з Content-Type: form


def ok(data=None, message="OK"):
    return jsonify({"success": True, "message": message, "data": data})

def err(message):
    return jsonify({"success": False, "message": message}), 400


# ═══════════════════════════════════════════════════════════════
# Головна сторінка
# ═══════════════════════════════════════════════════════════════

@app.route("/", methods=["GET"])
def index():
    stats = service.get_statistics()
    return render_template("index.html", stats=stats)


# ═══════════════════════════════════════════════════════════════
# API: Викладачі
# ═══════════════════════════════════════════════════════════════

@app.route("/api/teachers", methods=["GET"])
def api_get_teachers():
    teachers = service.get_teachers()
    return ok([{"id": t.id, "name": t.name,
                "department": t.department, "subjects": t.subjects}
               for t in teachers])

@app.route("/api/teachers", methods=["POST"])
def api_add_teacher():
    data = request.json
    try:
        t = service.save_teacher(data)
        return ok({"id": t.id}, "Викладача додано")
    except Exception as e:
        return err(str(e))

@app.route("/api/teachers/<int:tid>", methods=["PUT"])
def api_update_teacher(tid):
    data = request.json
    data["id"] = tid
    try:
        service.save_teacher(data)
        return ok(message="Оновлено")
    except Exception as e:
        return err(str(e))

@app.route("/api/teachers/<int:tid>", methods=["DELETE"])
def api_delete_teacher(tid):
    try:
        service.delete_teacher(tid)
        return ok(message=MSG_DELETED)
    except Exception as e:
        return err(str(e))


# ═══════════════════════════════════════════════════════════════
# API: Аудиторії
# ═══════════════════════════════════════════════════════════════

@app.route("/api/rooms", methods=["GET"])
def api_get_rooms():
    rooms = service.get_rooms()
    return ok([{"id": r.id, "number": r.number, "capacity": r.capacity,
                "room_type": r.room_type.name,
                "room_type_label": r.room_type.value}
               for r in rooms])

@app.route("/api/rooms", methods=["POST"])
def api_add_room():
    data = request.json
    try:
        r = service.save_room(data)
        return ok({"id": r.id}, "Аудиторію додано")
    except Exception as e:
        return err(str(e))

@app.route("/api/rooms/<int:rid>", methods=["DELETE"])
def api_delete_room(rid):
    try:
        service.delete_room(rid)
        return ok(message=MSG_DELETED)
    except Exception as e:
        return err(str(e))


# ═══════════════════════════════════════════════════════════════
# API: Групи
# ═══════════════════════════════════════════════════════════════

@app.route("/api/groups", methods=["GET"])
def api_get_groups():
    groups = service.get_groups()
    return ok([{"id": g.id, "name": g.name, "size": g.size,
                "year": g.year, "specialty": g.specialty}
               for g in groups])

@app.route("/api/groups", methods=["POST"])
def api_add_group():
    data = request.json
    try:
        g = service.save_group(data)
        return ok({"id": g.id}, "Групу додано")
    except Exception as e:
        return err(str(e))

@app.route("/api/groups/<int:gid>", methods=["DELETE"])
def api_delete_group(gid):
    try:
        service.delete_group(gid)
        return ok(message=MSG_DELETED)
    except Exception as e:
        return err(str(e))


# ═══════════════════════════════════════════════════════════════
# API: Дисципліни
# ═══════════════════════════════════════════════════════════════

@app.route("/api/subjects", methods=["GET"])
def api_get_subjects():
    subjects = service.get_subjects()
    return ok([{"id": s.id, "name": s.name,
                "hours_per_week": s.hours_per_week,
                "lesson_type": s.lesson_type.name,
                "lesson_type_label": s.lesson_type.value}
               for s in subjects])

@app.route("/api/subjects", methods=["POST"])
def api_add_subject():
    data = request.json
    try:
        s = service.save_subject(data)
        return ok({"id": s.id}, "Дисципліну додано")
    except Exception as e:
        return err(str(e))

@app.route("/api/subjects/<int:sid>", methods=["DELETE"])
def api_delete_subject(sid):
    try:
        service.delete_subject(sid)
        return ok(message=MSG_DELETED)
    except Exception as e:
        return err(str(e))


# ═══════════════════════════════════════════════════════════════
# API: Розклад (заняття)
# ═══════════════════════════════════════════════════════════════

@app.route("/api/lessons", methods=["GET"])
def api_get_lessons():
    lessons = service.get_all_lessons()
    return ok([l.to_dict() for l in lessons])

@app.route("/api/lessons", methods=["POST"])
def api_add_lesson():
    data = request.json
    success, message, lesson = service.add_lesson(
        subject_id=int(data["subject_id"]),
        teacher_id=int(data["teacher_id"]),
        group_id=int(data["group_id"]),
        room_id=int(data["room_id"]),
        day_index=int(data["day_index"]),
        slot_number=int(data["slot_number"]),
    )
    if success:
        return ok(lesson.to_dict(), message)
    return err(message)

@app.route("/api/lessons/auto", methods=["POST"])
def api_auto_schedule():
    data = request.json
    success, message, lesson = service.auto_schedule(
        subject_id=int(data["subject_id"]),
        teacher_id=int(data["teacher_id"]),
        group_id=int(data["group_id"]),
        room_id=int(data["room_id"]),
        strategy_name=data.get("strategy", "balanced"),
    )
    if success:
        return ok(lesson.to_dict(), message)
    return err(message)

@app.route("/api/lessons/<int:lid>", methods=["DELETE"])
def api_delete_lesson(lid):
    try:
        service.delete_lesson(lid)
        return ok(message="Заняття видалено")
    except Exception as e:
        return err(str(e))

@app.route("/api/lessons/clear", methods=["DELETE"])
def api_clear_lessons():
    service.clear_schedule()
    return ok(message="Розклад очищено")

@app.route("/api/schedule/group/<int:gid>", methods=["GET"])
def api_schedule_group(gid):
    lessons = service.get_schedule_for_group(gid)
    return ok([l.to_dict() for l in lessons])

@app.route("/api/schedule/teacher/<int:tid>", methods=["GET"])
def api_schedule_teacher(tid):
    lessons = service.get_schedule_for_teacher(tid)
    return ok([l.to_dict() for l in lessons])

@app.route("/api/conflicts", methods=["GET"])
def api_conflicts():
    return ok(service.get_conflict_log())

@app.route("/api/statistics", methods=["GET"])
def api_statistics():
    return ok(service.get_statistics())


# ═══════════════════════════════════════════════════════════════
# API: Довідники (enum values)
# ═══════════════════════════════════════════════════════════════

@app.route("/api/meta", methods=["GET"])
def api_meta():
    return ok({
        "lesson_types": [{"key": lt.name, "label": lt.value} for lt in LessonType],
        "room_types":   [{"key": rt.name, "label": rt.value} for rt in RoomType],
        "days":         [{"index": d.index, "label": d.label} for d in DayOfWeek],
        "slots":        list(range(1, 7)),
    })


# ═══════════════════════════════════════════════════════════════
# Запуск
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    init_db()
    print("=" * 60)
    print("  Система управління розкладом навчального закладу")
    print("  Відкрийте браузер: http://localhost:5000")
    print("=" * 60)
    app.run(debug=os.environ.get("FLASK_DEBUG", "0") == "1", port=5000)