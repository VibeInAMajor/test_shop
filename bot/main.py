"""
main.py

Этот скрипт поднимает Telegram-бота интернет-магазина с мини-приложением (WebApp).

Функции:
- Обрабатывает команду /start и отправляет пользователю кнопку "Store".
  Нажатие на эту кнопку открывает WebApp (мини-магазин) внутри Telegram.
- Получает данные заказа из WebApp через web_app_data (список товаров и количеств).
- По данным заказа формирует позиции и сумму.
- Создаёт платёжный инвойс через Telegram Payments (например, Portmone как провайдер).
- Обрабатывает pre_checkout_query и подтверждает платёж.
- При успешной оплате отправляет пользователю подтверждение с суммой заказа.
"""

import time

t0 = time.perf_counter()
print(f"[LOG] Start: imports begin at {t0:.6f}")

import asyncio
import json
import uuid
from typing import Dict

from aiogram import Bot, Dispatcher, F
from aiogram.enums import ParseMode, ContentType
from aiogram.filters import CommandStart
from aiogram.types import (
    Message,
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardMarkup, 
    InlineKeyboardButton,
    WebAppInfo,
    MenuButtonWebApp,
    LabeledPrice,
    PreCheckoutQuery,
    SuccessfulPayment,
)
import socket
import aiohttp
from aiogram.client.session.aiohttp import AiohttpSession
import logging
logging.basicConfig(level=logging.INFO)
from pathlib import Path

t1 = time.perf_counter()
print(f"[LOG] Imports finished: {t1:.6f}, delta={t1 - t0:.6f} sec")

# ====== НАСТРОЙКИ ======
BOT_TOKEN = "8473584829:AAHsD3ls_zCT9Lem9nyO7RggmvPgALVaWXg"  # токен бота от BotFather
WEBAPP_URL = "https://vibeinamajor.github.io/test_shop/"  # URL мини-приложения (по HTTPS)

# provider_token ты берёшь у Portmone после подключения к Telegram Payments
PAYMENT_PROVIDER_TOKEN = "1661751239:TEST:w6K6-h7hL-75hI-9QwO"

CATALOG_PATH = Path(__file__).with_name("catalog.json")


dp = Dispatcher()

class IPv4AiohttpSession(AiohttpSession):
    def __init__(self, *args, **kwargs):
        # обычная инициализация AiohttpSession
        super().__init__(*args, **kwargs)
        # подмешиваем настройку для TCPConnector: только IPv4
        self._connector_init["family"] = socket.AF_INET


@dp.message(CommandStart())
async def cmd_start(message: Message) -> None:
    session_id = uuid.uuid4().hex
    web_url = f"{WEBAPP_URL}?session={session_id}&v=2"

    await message.bot.set_chat_menu_button(
        chat_id=message.chat.id,
        menu_button=MenuButtonWebApp(
            text="Магазин",
            web_app=WebAppInfo(url=web_url),
        ),
    )

    await message.answer("Открой магазин через кнопку «Магазин».")



def load_catalog() -> dict:
    with CATALOG_PATH.open("r", encoding="utf-8") as f:
        return json.load(f)


@dp.message(F.web_app_data)
async def on_webapp_order(message: Message) -> None:
    """
    Получает заказ из WebApp.
    WebApp передаёт ТОЛЬКО id и qty.
    Цены и названия подтягиваются из catalog.json.
    """
    raw = message.web_app_data.data
    print("[LOG] WEB_APP_DATA:", raw)
    await message.answer(f"[DEBUG] web_app_data пришло: {raw[:500]}")

    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        await message.answer("❌ Ошибка данных заказа.")
        return

    items = payload.get("items", [])
    if not items:
        await message.answer("Корзина пуста.")
        return

    catalog = load_catalog()

    prices: list[LabeledPrice] = []
    total_kopeks = 0

    for item in items:
        product_id = item.get("id")
        qty = int(item.get("qty", 0))

        if qty <= 0 or product_id not in catalog:
            continue

        product = catalog[product_id]
        name = product["name"]
        price_uah = float(product["price_uah_per_100g"])
        price_kopeks = int(price_uah * 100)

        amount = price_kopeks * qty
        total_kopeks += amount

        prices.append(
            LabeledPrice(
                label=f"{name} × {qty}",
                amount=amount,
            )
        )

    if not prices or total_kopeks <= 0:
        await message.answer("❌ Не удалось сформировать заказ.")
        return

    await message.answer_invoice(
        title="Заказ: сухофрукты и орехи",
        description="Оплата заказа",
        payload="order_v1",
        provider_token=PAYMENT_PROVIDER_TOKEN,
        currency="UAH",
        prices=prices,
    )


@dp.pre_checkout_query()
async def process_pre_checkout(pre_checkout_query: PreCheckoutQuery, bot: Bot) -> None:
    """
    Обязательный шаг: Telegram присылает pre_checkout_query перед списанием денег.
    Нужно ответить ok=True, иначе платёж отменится.
    """
    await bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True)


@dp.message(F.successful_payment)
async def successful_payment_handler(message: Message) -> None:
    payment: SuccessfulPayment = message.successful_payment
    total_uah = payment.total_amount / 100

    session_id = uuid.uuid4().hex
    web_url = f"{WEBAPP_URL}?session={session_id}&clear_cart=1&v=2"

    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(
            text="Вернуться в магазин",
            web_app=WebAppInfo(url=web_url),
        )
    ]])


    await message.answer(
        f"✅ Оплата прошла успешно!\n"
        f"Сумма: <b>{total_uah:.2f} UAH</b>\n"
        f"Спасибо за заказ 🙌",
        parse_mode=ParseMode.HTML,
        reply_markup=kb,
    )

async def main() -> None:
    """
    Точка входа: создаёт бота и запускает long polling.
    """
    t2 = time.perf_counter()
    print(f"[LOG] Before Bot(): {t2:.6f}, delta={t2 - t1:.6f}")

    session = IPv4AiohttpSession()

    bot = Bot(BOT_TOKEN, session=session)

    t3 = time.perf_counter()
    print(f"[LOG] After Bot(): {t3:.6f}, delta={t3 - t2:.6f}")

    t4 = time.perf_counter()
    print(f"[LOG] Before start_polling: {t4:.6f}, delta={t4 - t3:.6f}")

    print("[LOG] Polling is starting now. Bot should be ONLINE.")
    await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    print("[LOG] Polling stopped (this should not happen under normal run).")


if __name__ == "__main__":
    asyncio.run(main())
