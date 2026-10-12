import asyncio
import os
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext
from backend.db import init_db, connection

load_dotenv()
TOKEN = os.getenv("BOT_TOKEN", "")
BOT_USERNAME = os.getenv("BOT_USERNAME", "your_wishlist_bot").lstrip("@")
WEBAPP_URL = os.getenv("WEBAPP_URL", "")
OWNER_IDS = [int(x.strip()) for x in os.getenv("TELEGRAM_OWNER_IDS", "8580512680,1973334354").split(",") if x.strip()]

bot = Bot(TOKEN)
dp = Dispatcher()

class AddFlow(StatesGroup):
    waiting_text = State()
    confirming = State()

def home_keyboard():
    rows = [
        [InlineKeyboardButton(text="💝 Вишлист владельца 1", callback_data="view:8580512680"),
         InlineKeyboardButton(text="💝 Вишлист владельца 2", callback_data="view:1973334354")]
    ]
    if WEBAPP_URL:
        rows.append([InlineKeyboardButton(text="✨ Открыть Mini App", web_app=WebAppInfo(url=WEBAPP_URL))])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def view_keyboard(owner_id):
    rows = [
        [InlineKeyboardButton(text="📋 Все желания", callback_data=f"list:{owner_id}:all"),
         InlineKeyboardButton(text="🗂 Категории", callback_data=f"cats:{owner_id}")],
    ]
    if WEBAPP_URL:
        rows.append([InlineKeyboardButton(text="Открыть Mini App", web_app=WebAppInfo(url=f"{WEBAPP_URL}/?owner={owner_id}"))])
    rows.append([InlineKeyboardButton(text="↩️ На главную", callback_data="home")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def item_keyboard(owner_id, mode="all"):
    rows = []
    if WEBAPP_URL:
        rows.append([InlineKeyboardButton(text="Открыть список в Mini App", web_app=WebAppInfo(url=f"{WEBAPP_URL}/?owner={owner_id}&mode={mode}"))])
    rows.append([InlineKeyboardButton(text="🗂 Категории", callback_data=f"cats:{owner_id}")])
    rows.append([InlineKeyboardButton(text="↩️ Назад", callback_data=f"view:{owner_id}")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def parse_bulk(text):
    parsed = []
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        fields = [x.strip() for x in line.split("|")]
        title = fields[0] if fields else ""
        if not title:
            continue
        category = fields[1] if len(fields) > 1 else ""
        price = fields[2] if len(fields) > 2 else ""
        url = fields[3] if len(fields) > 3 else ""
        description = fields[4] if len(fields) > 4 else ""
        parsed.append({"title": title[:200], "category": category[:80], "price": price[:100],
                       "url": url[:2000], "description": description[:4000]})
    return parsed

def add_to_db(owner_id, parsed):
    with connection() as conn:
        saved = 0
        for item in parsed:
            category_id = None
            if item["category"]:
                row = conn.execute("SELECT id FROM categories WHERE owner_id=? AND name=?",
                                   (owner_id, item["category"])).fetchone()
                if row:
                    category_id = row["id"]
                else:
                    emoji = "🎁"
                    name = item["category"]
                    conn.execute("INSERT INTO categories(owner_id,name,emoji) VALUES(?,?,?)",
                                 (owner_id, name, emoji))
                    category_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
            conn.execute("""
                INSERT INTO items(owner_id,category_id,title,description,url,price)
                VALUES(?,?,?,?,?,?)
            """, (owner_id, category_id, item["title"], item["description"], item["url"], item["price"]))
            saved += 1
        return saved

@dp.message(CommandStart())
async def start(message: Message):
    init_db(OWNER_IDS)
    args = (message.text or "").split(maxsplit=1)
    payload = args[1].strip() if len(args) > 1 else ""
    if payload.isdigit() and int(payload) in OWNER_IDS:
        owner_id = int(payload)
        await message.answer("💝 Вот вишлист. Выбери, как смотреть желания:", reply_markup=view_keyboard(owner_id))
    else:
        await message.answer(
            "Привет! Это наш общий бот желаний 💝\n\n"
            "Выбери вишлист, чтобы посмотреть желания. Добавлять и редактировать их могут только владельцы.",
            reply_markup=home_keyboard()
        )

@dp.callback_query(F.data == "home")
async def home(call: CallbackQuery):
    await call.message.edit_text("Выбери вишлист:", reply_markup=home_keyboard())
    await call.answer()

@dp.callback_query(F.data.startswith("view:"))
async def view(call: CallbackQuery):
    owner_id = int(call.data.split(":")[1])
    await call.message.edit_text("Как посмотреть желания?", reply_markup=view_keyboard(owner_id))
    await call.answer()

@dp.callback_query(F.data.startswith("list:"))
async def list_items(call: CallbackQuery):
    _, owner_str, mode = call.data.split(":")
    owner_id = int(owner_str)
    with connection() as conn:
        rows = conn.execute("""
            SELECT i.title,i.price,i.url,c.name AS category
            FROM items i LEFT JOIN categories c ON c.id=i.category_id
            WHERE i.owner_id=? ORDER BY i.created_at DESC,i.id DESC LIMIT 30
        """, (owner_id,)).fetchall()
    if not rows:
        text = "Пока здесь нет желаний."
    else:
        parts = []
        for idx, row in enumerate(rows, 1):
            line = f"{idx}. {row['title']}"
            if row["category"]: line += f" · {row['category']}"
            if row["price"]: line += f" · {row['price']}"
            if row["url"]: line += f"\n   🔗 {row['url']}"
            parts.append(line)
        text = "💝 Желания:\n\n" + "\n\n".join(parts)
        if len(rows) == 30:
            text += "\n\nПоказаны первые 30. Открой Mini App для полного списка."
    await call.message.edit_text(text, reply_markup=item_keyboard(owner_id, mode), disable_web_page_preview=True)
    await call.answer()

@dp.callback_query(F.data.startswith("cats:"))
async def show_categories(call: CallbackQuery):
    owner_id = int(call.data.split(":")[1])
    with connection() as conn:
        cats = conn.execute("""
            SELECT c.id,c.name,c.emoji,COUNT(i.id) AS n
            FROM categories c LEFT JOIN items i ON i.category_id=c.id
            WHERE c.owner_id=? GROUP BY c.id ORDER BY c.sort_order,c.id
        """, (owner_id,)).fetchall()
    rows = [[InlineKeyboardButton(text=f"{c['emoji']} {c['name']} ({c['n']})",
                                  callback_data=f"cat:{owner_id}:{c['id']}")] for c in cats]
    rows.append([InlineKeyboardButton(text="Открыть категории в Mini App", web_app=WebAppInfo(url=f"{WEBAPP_URL}/?owner={owner_id}&mode=category"))] if WEBAPP_URL else [InlineKeyboardButton(text="Все желания", callback_data=f"list:{owner_id}:all")])
    rows.append([InlineKeyboardButton(text="↩️ Назад", callback_data=f"view:{owner_id}")])
    await call.message.edit_text("Выбери категорию:", reply_markup=InlineKeyboardMarkup(inline_keyboard=rows))
    await call.answer()

@dp.callback_query(F.data.startswith("cat:"))
async def category_items(call: CallbackQuery):
    _, owner_str, cat_str = call.data.split(":")
    owner_id, category_id = int(owner_str), int(cat_str)
    with connection() as conn:
        cat = conn.execute("SELECT name,emoji FROM categories WHERE id=? AND owner_id=?", (category_id, owner_id)).fetchone()
        rows = conn.execute("SELECT title,price,url FROM items WHERE owner_id=? AND category_id=? ORDER BY id DESC LIMIT 30",
                            (owner_id, category_id)).fetchall()
    if not cat:
        await call.answer("Категория не найдена", show_alert=True)
        return
    text = f"{cat['emoji']} {cat['name']}\n\n" + ("\n\n".join(
        f"• {r['title']}" + (f" · {r['price']}" if r['price'] else "") + (f"\n🔗 {r['url']}" if r['url'] else "")
        for r in rows) if rows else "Пока пусто.")
    await call.message.edit_text(text, reply_markup=item_keyboard(owner_id, "category"), disable_web_page_preview=True)
    await call.answer()

@dp.message(Command("add"))
async def add_start(message: Message, state: FSMContext):
    if message.from_user.id not in OWNER_IDS:
        await message.answer("Добавлять желания могут только владельцы.")
        return
    rows = [[InlineKeyboardButton(text=f"Добавить в список {i+1}", callback_data=f"addowner:{owner_id}")]
            for i, owner_id in enumerate(OWNER_IDS) if owner_id == message.from_user.id]
    await message.answer(
        "Отправь желания по одному на строку в формате:\n"
        "Название | Категория | Цена | Ссылка | Описание\n\n"
        "Например:\nНаушники | Техника | 10000 | https://example.com | Чёрные\n\n"
        "Категория, цена, ссылка и описание необязательны.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=rows)
    )
    await state.set_state(AddFlow.waiting_text)
    await state.update_data(owner_id=message.from_user.id)

@dp.callback_query(F.data.startswith("addowner:"))
async def choose_add_owner(call: CallbackQuery, state: FSMContext):
    owner_id = int(call.data.split(":")[1])
    if call.from_user.id != owner_id or owner_id not in OWNER_IDS:
        await call.answer("Нет доступа", show_alert=True)
        return
    await state.update_data(owner_id=owner_id)
    await state.set_state(AddFlow.waiting_text)
    await call.message.answer("Теперь отправь список желаний строками. Формат: Название | Категория | Цена | Ссылка | Описание")
    await call.answer()

@dp.message(AddFlow.waiting_text)
async def receive_bulk(message: Message, state: FSMContext):
    if message.from_user.id not in OWNER_IDS:
        await state.clear()
        return
    data = await state.get_data()
    owner_id = int(data.get("owner_id", message.from_user.id))
    if owner_id != message.from_user.id:
        await message.answer("Можно добавлять желания только в свой список.")
        await state.clear()
        return
    parsed = parse_bulk(message.text or "")
    if not parsed:
        await message.answer("Не нашёл названий. Отправь хотя бы одну строку с названием.")
        return
    await state.update_data(parsed=parsed, owner_id=owner_id)
    preview = "\n".join(f"• {p['title']}" + (f" — {p['category']}" if p["category"] else "") for p in parsed[:15])
    if len(parsed) > 15:
        preview += f"\n…и ещё {len(parsed)-15}"
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"✅ Добавить ({len(parsed)})", callback_data="bulk:confirm"),
         InlineKeyboardButton(text="❌ Отмена", callback_data="bulk:cancel")]
    ])
    await state.set_state(AddFlow.confirming)
    await message.answer("Предпросмотр:\n\n" + preview + "\n\nДобавить эти желания?", reply_markup=kb)

@dp.callback_query(F.data == "bulk:confirm", AddFlow.confirming)
async def bulk_confirm(call: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    owner_id = int(data.get("owner_id", 0))
    if call.from_user.id != owner_id or owner_id not in OWNER_IDS:
        await call.answer("Нет доступа", show_alert=True)
        return
    parsed = data.get("parsed", [])
    count = add_to_db(owner_id, parsed)
    await state.clear()
    await call.message.edit_text(f"Готово! Добавлено желаний: {count} 💝")
    await call.answer()

@dp.callback_query(F.data == "bulk:cancel", AddFlow.confirming)
async def bulk_cancel(call: CallbackQuery, state: FSMContext):
    await state.clear()
    await call.message.edit_text("Импорт отменён.")
    await call.answer()

async def main():
    if not TOKEN:
        raise RuntimeError("Set BOT_TOKEN in .env")
    init_db(OWNER_IDS)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
