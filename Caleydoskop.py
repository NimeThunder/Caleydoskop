import nest_asyncio
import asyncio
import logging
import aiosqlite
from aiogram import F
from aiogram import Bot, Dispatcher, types
from aiogram.filters.command import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
from Quiz import quiz_data

nest_asyncio.apply()

logging.basicConfig(level=logging.INFO)

API_TOKEN = '7200169265:AAHtwYWUPsd9Rfp801KbyW26IsEGAaiNDLs'

bot = Bot(token=API_TOKEN)
dp = Dispatcher()

DB_NAME = 'quiz_bot.db'

async def create_table():
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute('''CREATE TABLE IF NOT EXISTS quiz_state (user_id INTEGER PRIMARY KEY, question_index INTEGER, statistics INTEGER)''')
        await db.commit()

async def update_quiz_index(user_id, index, statistic):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute('INSERT OR REPLACE INTO quiz_state (user_id, question_index, statistics) VALUES (?, ?, ?)', (user_id, index, statistic))
        await db.commit()

async def get_quiz_index(user_id):
     async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute('SELECT question_index FROM quiz_state WHERE user_id = (?)', (user_id, )) as cursor:
            results = await cursor.fetchone()
            if results is not None:
                return results[0]
            else:
                return 0

async def get_quiz_statistics(user_id):
     async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute('SELECT statistics FROM quiz_state WHERE user_id = (?)', (user_id, )) as cursor:
            results = await cursor.fetchone()
            if results is not None:
                return results[0]
            else:
                return 0

def generate_options_keyboard(answer_options, right_answer):
    builder = InlineKeyboardBuilder()

    for option in answer_options:
        builder.add(types.InlineKeyboardButton(
            text=option,
            callback_data="True_" + option if option == right_answer else "False" + option)
        )

    builder.adjust(1)
    return builder.as_markup()

async def get_question(message, user_id):
    current_question_index = await get_quiz_index(user_id)
    correct_index = quiz_data[current_question_index]['correct_option']
    opts = quiz_data[current_question_index]['options']

    kb = generate_options_keyboard(opts, opts[correct_index])
    await message.answer(f"{quiz_data[current_question_index]['question']}", reply_markup=kb)

async def new_quiz(message):
    user_id = message.from_user.id
    current_question_index = 0
    statistic = 0
    await update_quiz_index(user_id, current_question_index, statistic)

    await get_question(message, user_id)

async def question_index(callback: types.CallbackQuery):
    await callback.bot.edit_message_reply_markup(
        chat_id=callback.from_user.id,
        message_id=callback.message.message_id,
        reply_markup=None
    )
    await callback.message.answer(f"Ваш ответ: {callback.data[5:]}.")

    current_question_index = await get_quiz_index(callback.from_user.id)
    return current_question_index

async def Next_question(callback: types.CallbackQuery, current_question_index, status):
    current_question_index += 1
    statistic = await get_quiz_statistics(callback.from_user.id)
    if status:
        statistic += 1
    await update_quiz_index(callback.from_user.id, current_question_index, statistic)

    if current_question_index < len(quiz_data):
        await get_question(callback.message, callback.from_user.id)
    else:
        await callback.message.answer("Это был последний вопрос. Квиз завершен!")
        result = await get_quiz_statistics(callback.from_user.id)
        await callback.message.answer(f"Ваша статистика: {result}/{len(quiz_data)}.")

@dp.callback_query(F.data[0] == "T")
async def right_answer(callback: types.CallbackQuery):
    current_question_index = await question_index(callback)

    await callback.message.answer("Верно!")

    await Next_question(callback, current_question_index, True)

@dp.callback_query(F.data[0] == "F")
async def wrong_answer(callback: types.CallbackQuery):
    current_question_index = await question_index(callback)

    correct_option = quiz_data[current_question_index]['correct_option']

    await callback.message.answer(f"Неправильно. Правильный ответ: {quiz_data[current_question_index]['options'][correct_option]}")

    await Next_question(callback, current_question_index, False)

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    builder = ReplyKeyboardBuilder()
    builder.add(types.KeyboardButton(text="Начать игру"))
    await message.answer("Добро пожаловать в квиз!", reply_markup=builder.as_markup(resize_keyboard=True))

@dp.message(F.text=="Начать игру")
@dp.message(Command("quiz"))
async def cmd_quiz(message: types.Message):
    await message.answer(f"Давайте начнем квиз!")
    await new_quiz(message)

async def main():
    await create_table()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())