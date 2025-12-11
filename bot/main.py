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

import asyncio
import json
from typing import Dict

from aiogram import Bot, Dispatcher, F
from aiogram.enums import ParseMode, ContentType
from aiogram.filters import CommandStart
from aiogram.types import (
    Message,
    ReplyKeyboardMarkup,
    KeyboardButton,
    WebAppInfo,
    LabeledPrice,
    PreCheckoutQuery,
    SuccessfulPayment,
)

# ====== НАСТРОЙКИ ======
BOT_TOKEN = "8473584829:AAHsD3ls_zCT9Lem9nyO7RggmvPgALVaWXg"  # токен бота от BotFather
WEBAPP_URL = "https://vibeinamajor.github.io/test_shop/"  # URL мини-приложения (по HTTPS)

# provider_token ты берёшь у Portmone после подключения к Telegram Payments
PAYMENT_PROVIDER_TOKEN = "1661751239:TEST:w6K6-h7hL-75hI-9QwO"

# Цены товаров (копейки, для Telegram Payments)
PRICE_TABLE: Dict[str, int] = {
    "dried_apricots": 150_00,  # 150 грн
    "prunes": 130_00,          # 130 грн
    "walnuts": 200_00,         # 200 грн
    "almonds": 260_00,         # 260 грн
}

dp = Dispatcher()


@dp.message(CommandStart())
async def cmd_start(message: Message) -> None:
    """
    Обработчик /start: отправляет кнопку "Store", открывающую WebApp.
    """
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(
        KeyboardButton(
            text="Store",
            web_app=WebAppInfo(url=WEBAPP_URL)
        )
    )

    await message.answer(
        "Привет! Нажми кнопку <b>Store</b>, чтобы открыть мини-магазин.",
        reply_markup=kb,
        parse_mode=ParseMode.HTML,
    )


@dp.message(F.content_type == ContentType.WEB_APP_DATA)
async def handle_webapp_order(message: Message) -> None:
    """
    Получает заказ из WebApp (message.web_app_data.data),
    собирает позиции и отправляет инвойс пользователю.
    Ожидаемый формат данных от WebApp:
    {
        "items": [
            {"id": "dried_apricots", "name": "Курага", "qty": 2},
            {"id": "walnuts", "name": "Грецкий орех", "qty": 1}
        ]
    }
    """
    raw = message.web_app_data.data
    try:
        order = json.loads(raw)
    except json.JSONDecodeError:
        await message.answer("Не удалось разобрать данные заказа 😕")
        return

    items = order.get("items", [])
    if not items:
        await message.answer("Корзина пуста, заказ не сформирован.")
        return

    prices: list[LabeledPrice] = []
    total = 0

    for item in items:
        item_id = item.get("id")
        name = item.get("name", "Товар")
        qty = int(item.get("qty", 0))

        if not item_id or qty <= 0:
            continue

        unit_price = PRICE_TABLE.get(item_id)
        if unit_price is None:
            # Если из WebApp пришёл неизвестный id — пропускаем
            continue

        amount = unit_price * qty
        prices.append(LabeledPrice(label=f"{name} x{qty}", amount=amount))
        total += amount

    if not prices:
        await message.answer("Не удалось собрать позиции заказа.")
        return

    # Отправляем инвойс
    await message.bot.send_invoice(
        chat_id=message.chat.id,
        title="Заказ: сухофрукты и орехи",
        description="Оплата заказа из мини-магазина.",
        payload=json.dumps(order),  # любые данные, вернутся в successful_payment
        provider_token=PAYMENT_PROVIDER_TOKEN,
        currency="UAH",
        prices=prices,
        max_tip_amount=0,
        need_name=True,
        need_phone_number=True,
        need_email=False,
        need_shipping_address=False,
        is_flexible=False,
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
    """
    Обработка успешной оплаты.
    Здесь можно записать заказ в БД, отправить уведомление себе и т.п.
    """
    payment: SuccessfulPayment = message.successful_payment
    total_uah = payment.total_amount / 100

    await message.answer(
        f"✅ Оплата прошла успешно!\n"
        f"Сумма: <b>{total_uah:.2f} UAH</b>\n"
        f"Спасибо за заказ 🙌",
        parse_mode=ParseMode.HTML,
    )


async def main() -> None:
    """
    Точка входа: создаёт бота и запускает long polling.
    """
    bot = Bot(BOT_TOKEN)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
