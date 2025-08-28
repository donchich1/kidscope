"""
Бот для школи з кнопками, лідерами, профілем і адмін‑режимом
- Меню кнопок для учнів: Мої бали, Мій профіль, Розклад, Правила, Лідери (клас), Лідери (всі)
- /link <PIN> — привʼязка Telegram → учень
- Лідерборд по класу або по всіх
- Профіль показує: імʼя, клас, вік, рік навчання, бали
- Секретна команда /admin <пароль> додає відправника у admins у data.json
- Адмін‑команди: /set, /give, /add_student, /edit_student, /del_student, /broadcast
- Дані у data.json (students, tg_links, admins)

Вимоги: python-telegram-bot==20.*
"""

import json
from pathlib import Path
from typing import Dict, Any
from datetime import datetime

from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters

# ================== НАЛАШТУВАННЯ ==================
BOT_TOKEN = "7811760305:AAHtfRGM20Q9btxdWlmTBcdhJ2SrUZu5YjE"  # ← ВСТАВ СВІЙ ТОКЕН
DATA_FILE = Path("data.json")
ADMIN_SECRET = "secret123"  # ← ЗМІНИ НА СВІЙ ПАРОЛЬ

RULES_TEXT = (
    "📋 Правила балів:\n"
    "• Запросив друга, який записався — +10\n"
    "• Успішність/відвідування — +20\n"
    "• Активність на занятті — +10\n"
    "• Порушення — −10/−15\n"
    "(детальна таблиця у класного керівника)"
)

SCHEDULE_TEXT = (
    "🗓 Розклад на місяць:\n"
    "Пн 18:00 — Англійська\nВт 18:00 — Історія\nЧт 18:00 — Українська\nСб 11:00 — Розмовний клуб\n"
    "(за потреби оновлюйте цей текст у коді)"
)

START_STUDENTS = [
    {"id": "1", "full_name": "Богдан Кокушко", "pin": "1111", "points": 25, "class": "7-А", "age": 13, "year": 2},
    {"id": "2", "full_name": "Данило Шутяк", "pin": "2222", "points": 40, "class": "7-А", "age": 13, "year": 2},
    {"id": "3", "full_name": "Захар Дідун", "pin": "3333", "points": 15, "class": "7-Б", "age": 13, "year": 2},
]

# ================== ЗБЕРЕЖЕННЯ ДАНИХ ==================

def load_db() -> Dict[str, Any]:
    if DATA_FILE.exists():
        return json.loads(DATA_FILE.read_text(encoding="utf-8"))
    db = {
        "students": {s["id"]: s for s in START_STUDENTS},
        "tg_links": {},  # telegram_user_id -> student_id
        "admins": [],
    }
    save_db(db)
    return db


def save_db(db: Dict[str, Any]):
    DATA_FILE.write_text(json.dumps(db, ensure_ascii=False, indent=2), encoding="utf-8")


# ================== КОРИСНІ ФУНКЦІЇ ==================

def is_admin(db: Dict[str, Any], user_id: int) -> bool:
    return str(user_id) in {str(a) for a in db.get("admins", [])}


def get_linked_student(db: Dict[str, Any], user_id: int) -> Dict[str, Any] | None:
    sid = db["tg_links"].get(str(user_id))
    if not sid:
        return None
    return db["students"].get(str(sid))


def main_keyboard(is_admin_flag: bool = False) -> ReplyKeyboardMarkup:
    rows = [
        [KeyboardButton("📊 Мої бали"), KeyboardButton("👤 Мій профіль")],
        [KeyboardButton("🗓 Розклад"), KeyboardButton("📋 Правила")],
        [KeyboardButton("🏆 Лідери (клас)"), KeyboardButton("🌍 Лідери (всі)")],
    ]
    if is_admin_flag:
        rows.append([KeyboardButton("🛠 Адмін меню")])
    return ReplyKeyboardMarkup(rows, resize_keyboard=True)


# ================== ХЕНДЛЕРИ КОМАНД ==================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db = load_db()
    admin_flag = is_admin(db, update.effective_user.id)
    await update.message.reply_text(
        "Привіт! Я твій шкільний бот 👋 Обирай кнопку нижче.\n"
        "Щоб під’єднати профіль, введи: /link PIN (PIN дасть вчитель).\n",
        reply_markup=main_keyboard(admin_flag)
    )


async def link_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db = load_db()
    if not context.args:
        await update.message.reply_text("Вкажіть PIN: /link 1234")
        return
    pin = context.args[0]
    for sid, s in db["students"].items():
        if str(s.get("pin")) == str(pin):
            db["tg_links"][str(update.effective_user.id)] = sid
            save_db(db)
            await update.message.reply_text(f"Привʼязано до: {s['full_name']}", reply_markup=main_keyboard(is_admin(db, update.effective_user.id)))
            return
    await update.message.reply_text("PIN не знайдено. Перевірте у вчителя.")


async def admin_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db = load_db()
    if not context.args:
        await update.message.reply_text("Пароль?: /admin <пароль>")
        return
    if context.args[0] == ADMIN_SECRET:
        admins = set(str(x) for x in db.get("admins", []))
        admins.add(str(update.effective_user.id))
        db["admins"] = list(admins)
        save_db(db)
        await update.message.reply_text("Готово! Адмін‑режим активовано.", reply_markup=main_keyboard(True))
    else:
        await update.message.reply_text("Невірний пароль.")


async def me_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db = load_db()
    s = get_linked_student(db, update.effective_user.id)
    if not s:
        await update.message.reply_text("Спочатку /link <PIN>.")
        return
    await update.message.reply_text(f"{s['full_name']}, ваші бали: {s['points']} ✨")


async def profile_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db = load_db()
    s = get_linked_student(db, update.effective_user.id)
    if not s:
        await update.message.reply_text("Спочатку /link <PIN>.")
        return
    txt = (
        f"👤 {s['full_name']}\n"
        f"Клас: {s.get('class','-')}\n"
        f"Вік: {s.get('age','-')}\n"
        f"Рік навчання: {s.get('year','-')}\n"
        f"Бали: {s['points']}"
        f"Продовжуйте в тому ж дусі! 🎉"
    )
    await update.message.reply_text(txt)


async def rules_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(RULES_TEXT)


async def schedule_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(SCHEDULE_TEXT)


def _leaderboard_text(db: Dict[str, Any], *, class_filter: str | None = None, top: int = 10) -> str:
    # збираємо (student, points) з фільтром за класом
    rows = []
    for s in db["students"].values():
        if class_filter and str(s.get("class")) != str(class_filter):
            continue
        rows.append((s.get("full_name"), int(s.get("points", 0)), s.get("class")))
    if not rows:
        return "Немає даних."
    rows.sort(key=lambda x: x[1], reverse=True)
    lines = [f"🏆 Лідери{' — ' + class_filter if class_filter else ''}:"]
    for i, (name, pts, cls) in enumerate(rows[:top], start=1):
        lines.append(f"{i}. {name} — {pts} балів ({cls})")
    return "\n".join(lines)


async def leaderboard_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db = load_db()
    await update.message.reply_text(_leaderboard_text(db))


async def leaderboard_class(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db = load_db()
    s = get_linked_student(db, update.effective_user.id)
    if not s:
        await update.message.reply_text("Спочатку /link <PIN>.")
        return
    cls = s.get("class")
    await update.message.reply_text(_leaderboard_text(db, class_filter=str(cls)))


# ================== АДМІН КОМАНДИ ==================
async def set_points(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db = load_db()
    if not is_admin(db, update.effective_user.id):
        return
    if len(context.args) < 2:
        await update.message.reply_text("Формат: /set <student_id> <points>")
        return
    sid, pts = context.args[0], int(context.args[1])
    if sid not in db["students"]:
        await update.message.reply_text("Учня з таким ID немає.")
        return
    db["students"][sid]["points"] = pts
    save_db(db)
    await update.message.reply_text("Оновлено ✅")


async def give_points(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db = load_db()
    if not is_admin(db, update.effective_user.id):
        return
    if len(context.args) < 2:
        await update.message.reply_text("Формат: /give <student_id> <delta>")
        return
    sid, delta = context.args[0], int(context.args[1])
    if sid not in db["students"]:
        await update.message.reply_text("Учня з таким ID немає.")
        return
    db["students"][sid]["points"] = int(db["students"][sid].get("points", 0)) + delta
    save_db(db)
    await update.message.reply_text("Готово ✅")


async def add_student(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db = load_db()
    if not is_admin(db, update.effective_user.id):
        return
    # Формат: /add_student id|full_name|pin|class|age|year|points
    raw = " ".join(context.args)
    if "|" not in raw:
        await update.message.reply_text("Формат: /add_student id|full_name|pin|class|age|year|points")
        return
    parts = [p.strip() for p in raw.split("|")]
    if len(parts) < 7:
        await update.message.reply_text("Формат неповний. Потрібно 7 полів.")
        return
    sid, full_name, pin, cls, age, year, pts = parts
    db["students"][sid] = {
        "id": sid,
        "full_name": full_name,
        "pin": pin,
        "class": cls,
        "age": int(age),
        "year": int(year),
        "points": int(pts),
    }
    save_db(db)
    await update.message.reply_text("Учня додано ✅")


async def edit_student(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db = load_db()
    if not is_admin(db, update.effective_user.id):
        return
    # Формат: /edit_student <id> <field> <value>
    if len(context.args) < 3:
        await update.message.reply_text("Формат: /edit_student <id> <field> <value>")
        return
    sid, field, value = context.args[0], context.args[1], " ".join(context.args[2:])
    if sid not in db["students"]:
        await update.message.reply_text("Учня з таким ID немає.")
        return
    if field not in {"full_name", "pin", "class", "age", "year", "points"}:
        await update.message.reply_text("Дозволені поля: full_name, pin, class, age, year, points")
        return
    if field in {"age", "year", "points"}:
        value = int(value)
    db["students"][sid][field] = value
    save_db(db)
    await update.message.reply_text("Оновлено ✅")


async def del_student(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db = load_db()
    if not is_admin(db, update.effective_user.id):
        return
    if len(context.args) < 1:
        await update.message.reply_text("Формат: /del_student <id>")
        return
    sid = context.args[0]
    if sid not in db["students"]:
        await update.message.reply_text("Учня з таким ID немає.")
        return
    db["students"].pop(sid)
    # прибираємо можливі посилання tg_links
    for k, v in list(db["tg_links"].items()):
        if v == sid:
            db["tg_links"].pop(k)
    save_db(db)
    await update.message.reply_text("Видалено ✅")


async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db = load_db()
    if not is_admin(db, update.effective_user.id):
        return
    if not context.args:
        await update.message.reply_text("Формат: /broadcast <повідомлення>")
        return
    msg = " ".join(context.args)
    # Розсилка всім, хто привʼязаний
    sent = 0
    for tg_user_id in db["tg_links"].keys():
        try:
            await context.bot.send_message(chat_id=int(tg_user_id), text=msg)
            sent += 1
        except Exception:
            pass
    await update.message.reply_text(f"Надіслано: {sent}")


# ================== ОБРОБКА КНОПОК (ТЕКСТ) ==================
async def on_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (update.message.text or "").strip()
    if text == "📊 Мої бали":
        return await me_cmd(update, context)
    if text == "👤 Мій профіль":
        return await profile_cmd(update, context)
    if text == "🗓 Розклад":
        return await schedule_cmd(update, context)
    if text == "📋 Правила":
        return await rules_cmd(update, context)
    if text == "🏆 Лідери (клас)":
        return await leaderboard_class(update, context)
    if text == "🌍 Лідери (всі)":
        return await leaderboard_all(update, context)
    if text == "🛠 Адмін меню":
        await update.message.reply_text(
            "Адмін‑команди:\n"
            "• /set <id> <points>\n"
            "• /give <id> <delta>\n"
            "• /add_student id|full_name|pin|class|age|year|points\n"
            "• /edit_student <id> <field> <value>\n"
            "• /del_student <id>\n"
            "• /broadcast <текст>"
        )
        return


# ================== MAIN ==================
async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "/start — головне меню\n"
        "/link <PIN> — привʼязка\n"
        "/me — мої бали\n"
        "/rules — правила\n"
        "/schedule — розклад\n"
        "/leaderboard — лідери (всі)\n"
        "/leaderboard_class — лідери по моєму класу\n"
        "/admin <пароль> — стати адміністратором"
    )


def build_app() -> Application:
    app = Application.builder().token(BOT_TOKEN).build()
    # Команди
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("link", link_cmd))
    app.add_handler(CommandHandler("admin", admin_cmd))
    app.add_handler(CommandHandler("me", me_cmd))
    app.add_handler(CommandHandler("rules", rules_cmd))
    app.add_handler(CommandHandler("schedule", schedule_cmd))
    app.add_handler(CommandHandler("leaderboard", leaderboard_all))
    app.add_handler(CommandHandler("leaderboard_class", leaderboard_class))
    # Адмін-команди
    app.add_handler(CommandHandler("set", set_points))
    app.add_handler(CommandHandler("give", give_points))
    app.add_handler(CommandHandler("add_student", add_student))
    app.add_handler(CommandHandler("edit_student", edit_student))
    app.add_handler(CommandHandler("del_student", del_student))
    app.add_handler(CommandHandler("broadcast", broadcast))
    # Кнопки (текст)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_text))
    return app


def main():
    app = build_app()
    app.run_polling()


if __name__ == "__main__":
    main()
