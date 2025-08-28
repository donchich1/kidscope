"""
Admin-панель для редагування даних бота у вигляді таблиці (без зміни бота)
— Працює напряму з вашим data.json (той самий, що читає бот)
— Таблиці: Учні (students), Адміни (admins), Привʼязки (tg_links, read-only)
— Можна додавати/редагувати/видаляти учнів, масово міняти бали, PIN, клас, вік тощо
— Кнопка Зберегти → перезаписує data.json (робить резервну копію)
— ✉️ Нове: розсилка повідомлень «усім користувачам бота» (усі chat_id з tg_links)

Як запустити:
1) pip install streamlit pandas requests
2) streamlit run admin_app.py
3) У інтерфейсі вкажіть шлях до data.json (за замовчуванням ./data.json)

Порада: запускайте на тому ж компʼютері, де лежить data.json. Бот не треба зупиняти — він читає файл під час команд.
"""

import json
from pathlib import Path
from datetime import datetime
import pandas as pd
import streamlit as st
import requests

st.set_page_config(page_title="School Bot Admin", page_icon="📚", layout="wide")
st.title("📚 School Bot — Admin панель")

# -------------------- Вибір файлу --------------------
def default_path():
    p = Path("data.json")
    return str(p.resolve())

path_str = st.text_input("Шлях до data.json", value=default_path(), help="Вкажіть шлях до файлу, який використовує ваш бот")
path = Path(path_str)

if not path.exists():
    st.warning("Файл не знайдено. Створю, якщо натиснете 'Створити порожній data.json'.")
    if st.button("Створити порожній data.json"):
        empty = {"students": {}, "tg_links": {}, "admins": []}
        path.write_text(json.dumps(empty, ensure_ascii=False, indent=2), encoding="utf-8")
        st.success("Створено порожній data.json")

# -------------------- Завантаження --------------------
@st.cache_data(ttl=2)
def load_db(_path: Path):
    try:
        data = json.loads(_path.read_text(encoding="utf-8"))
    except Exception:
        data = {"students": {}, "tg_links": {}, "admins": []}
    # нормалізація ключів
    data.setdefault("students", {})
    data.setdefault("tg_links", {})
    data.setdefault("admins", [])
    return data


def save_db(_path: Path, data: dict):
    # резервна копія
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup = _path.with_name(f"{_path.stem}.backup-{ts}.json")
    try:
        backup.write_text(json.dumps(load_db(_path), ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass
    # збереження
    _path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


data = load_db(path)

# -------------------- Таб: Учні --------------------
st.header("👥 Учні (students)")
st.caption("Додавайте/редагуйте учнів. Поля: id, full_name, pin, class, age, year, points")

# Перетворюємо students у DataFrame
students_dict = data.get("students", {})
rows = []
for sid, s in students_dict.items():
    row = {
        "id": str(s.get("id", sid)),
        "full_name": s.get("full_name", ""),
        "pin": str(s.get("pin", "")),
        "class": s.get("class", ""),
        "age": int(s.get("age", 0)) if str(s.get("age", "0")).isdigit() else 0,
        "year": int(s.get("year", 0)) if str(s.get("year", "0")).isdigit() else 0,
        "points": int(s.get("points", 0)) if str(s.get("points", "0")).lstrip("-").isdigit() else 0,
    }
    rows.append(row)

students_df = pd.DataFrame(rows, columns=["id", "full_name", "pin", "class", "age", "year", "points"]).sort_values("id")

edited_df = st.data_editor(
    students_df,
    use_container_width=True,
    num_rows="dynamic",
    column_config={
        "id": st.column_config.TextColumn("ID", help="Унікальний ідентифікатор учня"),
        "full_name": st.column_config.TextColumn("ПІБ"),
        "pin": st.column_config.TextColumn("PIN"),
        "class": st.column_config.TextColumn("Клас"),
        "age": st.column_config.NumberColumn("Вік", min_value=0, max_value=100),
        "year": st.column_config.NumberColumn("Рік навчання", min_value=0, max_value=12),
        "points": st.column_config.NumberColumn("Бали", min_value=-100000, max_value=100000),
    },
    hide_index=True,
)

col1, col2 = st.columns([1,1])
with col1:
    if st.button("💾 Зберегти учнів у data.json", type="primary"):
        # валідація ID
        ids = list(edited_df["id"].astype(str))
        if len(ids) != len(set(ids)):
            st.error("ID мають бути унікальними. Перевірте дублікати.")
        else:
            # збираємо назад у dict
            new_students = {}
            for _, r in edited_df.iterrows():
                sid = str(r["id"]) or ""
                if not sid:
                    continue
                new_students[sid] = {
                    "id": sid,
                    "full_name": str(r["full_name"] or "").strip(),
                    "pin": str(r["pin"] or "").strip(),
                    "class": str(r["class"] or "").strip(),
                    "age": int(r["age"]) if pd.notna(r["age"]) else 0,
                    "year": int(r["year"]) if pd.notna(r["year"]) else 0,
                    "points": int(r["points"]) if pd.notna(r["points"]) else 0,
                }
            data["students"] = new_students
            save_db(path, data)
            st.success("Збережено ✅")

with col2:
    st.download_button(
        "⬇️ Завантажити data.json",
        data=json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8"),
        file_name="data.json",
        mime="application/json",
    )

# -------------------- Таб: Лінки і адміни --------------------
st.header("🔗 Привʼязки (tg_links) та 👑 Адміни")

colA, colB = st.columns(2)
with colA:
    st.subheader("🔗 tg_links (read‑only)")
    if data.get("tg_links"):
        tl_df = pd.DataFrame(
            sorted([{"telegram_user_id": k, "student_id": v} for k, v in data.get("tg_links", {}).items()], key=lambda x: x["student_id"])
        )
    else:
        tl_df = pd.DataFrame(columns=["telegram_user_id", "student_id"])
    st.dataframe(tl_df, use_container_width=True)

with colB:
    st.subheader("👑 admins")
    admins_list = data.get("admins", [])
    admins_text = st.text_area("Список admin user_id (по одному в рядку)", value="".join(map(str, admins_list)))
    if st.button("💾 Зберегти адміністраторів"):
        new_list = [x.strip() for x in admins_text.splitlines() if x.strip()]
        data["admins"] = new_list
        save_db(path, data)
        st.success("Адміністраторів збережено ✅")

st.caption("Підказка: tg_user_id зʼявляється в tg_links після /link від учня (або перше повідомлення боту).")

# -------------------- ✉️ Розсилка в Telegram (усім користувачам) --------------------
st.header("✉️ Розсилка в Telegram — усім користувачам бота")
with st.expander("Надіслати повідомлення всім, хто привʼязався (усі chat_id з tg_links)", expanded=True):
    token = st.text_input("BOT_TOKEN від @BotFather", type="password", help="Токен вашого бота. Зберігайте його в секреті.")
    msg = st.text_area("Текст повідомлення", placeholder="Напишіть оголошення для всіх…")
    disable_notif = st.checkbox("Надіслати без звуку (disable_notification)", value=False)

    if st.button("🚀 Відправити всім"):
        if not token:
            st.error("Вкажіть BOT_TOKEN.")
        elif not msg.strip():
            st.error("Повідомлення не може бути порожнім.")
        else:
            tg_ids = list(data.get("tg_links", {}).keys())
            if not tg_ids:
                st.warning("tg_links порожній — немає кому відправляти.")
            else:
                sent = 0
                failed = 0
                for chat_id in tg_ids:
                    try:
                        resp = requests.post(
                            f"https://api.telegram.org/bot{token}/sendMessage",
                            json={
                                "chat_id": int(chat_id),
                                "text": msg,
                                "disable_notification": disable_notif,
                            },
                            timeout=15,
                        )
                        if resp.status_code == 200:
                            sent += 1
                        else:
                            failed += 1
                    except Exception:
                        failed += 1
                st.success(f"Готово: надіслано {sent}, помилок {failed} ✅")
                if failed:
                    st.info("Переконайтесь, що всі користувачі писали боту хоча б 1 раз і не блокували бота.")

st.caption("© School Bot Admin • Streamlit • Працює з локальним JSON і API Telegram")

# Переміщено до папки admin
