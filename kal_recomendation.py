from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes
import random
import csv
import asyncio
import os, sys
from collections import defaultdict

# Пул доступных ингредиентов
INGREDIENTS_POOL = [
    "Двойное яблоко",       # Классика, самый популярный вкус  
    "Мята",                 # Освежающий хит  
    "Арбуз",                # Летний фаворит  
    "Дыня",                 # Сладкий и сочный  
    "Виноград",             # Чёрный или зелёный  
    "Персик",               # Нежный и фруктовый  
    "Ананас",               # Тропическая сладость  
    "Манго",                # Экзотика №1  
    "Клубника",             # Ягодный must-have  
    "Черника",              # С лёгкой кислинкой  
    "Лимон",                # Для миксов  
    "Лайм",                 # Острый цитрус  
    "Кокос",                # Кремовый тропический вкус  
    "Личи",                 # Восточная экзотика  
    "Гуава",                # Необычно-сладкий  
    "Пина колада",          # Ананас + кокос  
    "Кола",                 # Газированный оттенок  
    "Мохито",               # Мята + лайм  
    "Шоколад",              # Десертный выбор  
    "Карамель",             # Сладкоежкам  
    "Ваниль",               # Нежный кремовый вкус  
    "Чизкейк",              # Десертный хит  
    "Корица",               # Пряный акцент  
    "Роза",                 # Цветочный аромат  
    "Лаванда",             # Успокаивающий вкус  
    "Огурец",              # Свежий и необычный  
    "Чай масала",          # Пряный чайный микс  
    "Красное вино",        # Богатый вкус  
    "Гранат",              # С кислинкой  
    "Малина",              # Яркая ягода  
    "Апельсин",            # Цитрусовый заряд  
    "Мандарин",            # Новогодний вкус  
    "Груша",               # Нежная сладость  
    "Ежевика",             # Глубокая ягодная нота  
    "Маракуйя",            # Тропическая кислинка  
    "Киви",                # Зелёный и свежий  
    "Вишня",               # Классика с глубиной  
    "Облепиха",            # Кисло-сладкий микс  
    "Фейхоа",              # Экзотика  
    "Тамаринд",            # Восточная сладость  
]

MIX_DATABASE = {}
USER_DATABASE = {}
DATABASE_FILE = "mix_database.csv"
USER_DATABASE_FILE = "user_database.csv"
user_active = {}
user_mix_mode = defaultdict(lambda: 'random')  # 'random' или 'top'

def load_database():
    if os.path.exists(DATABASE_FILE):
        with open(DATABASE_FILE, newline="", encoding="utf-8") as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                ingredients_set = frozenset(row["ingredients"].split(","))
                proportions = {kv.split(":")[0]: int(float(kv.split(":")[1])) for kv in row["proportions"].split(";")}
                MIX_DATABASE[ingredients_set] = {
                    "proportions": proportions,
                    "likes": int(row["likes"]),
                    "dislikes": int(row["dislikes"])
                }
    if os.path.exists(USER_DATABASE_FILE):
        with open(USER_DATABASE_FILE, newline="", encoding="utf-8") as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                user_id = int(row["user_id"])
                ingredients_set = frozenset(row["ingredients"].split(","))
                USER_DATABASE.setdefault(user_id, {})[ingredients_set] = {
                    "likes": int(row["likes"]),
                    "dislikes": int(row["dislikes"])
                }

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Привет! Я помогу подобрать тебе кальянный микс!\n"
        "Нажми /mix чтобы начать или /stop чтобы остановить.\n"
        "Другие команды:\n"
        "/top - топ миксов сообщества\n"
        "/mytop - ваши любимые миксы\n"
        "/mytop_clear - очистить ваш топ\n"
        "/mytop_remove - удалить конкретные миксы из вашего топа"
    )

async def send_mix(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if user_mix_mode[user_id] == 'top' and MIX_DATABASE:
        # Получаем все миксы с положительным числом лайков
        liked_mixes = [
            (ingredients, data) 
            for ingredients, data in MIX_DATABASE.items() 
            if data['likes'] > 0
        ]
        
        if liked_mixes:
            # Выбираем случайный микс из понравившихся
            ingredients_set, mix_info = random.choice(liked_mixes)
            proportions = mix_info['proportions']
            user_mix_mode[user_id] = 'random'  # Следующий будет случайный
        else:
            # Если нет миксов с лайками, показываем случайный
            return await send_random_mix(update, context)
    else:
        # Показываем случайный микс
        return await send_random_mix(update, context)
    
    sorted_mix = sorted(proportions.items(), key=lambda x: x[1], reverse=True)
    mix_description = " | ".join(f"{ingredient} {percent}%" for ingredient, percent in sorted_mix)
    message = f"🔥 ПОПУЛЯРНЫЙ МИКС: {mix_description}"

    # Создаем кнопки с правильным форматом callback_data
    ingredients_list = sorted(ingredients_set)
    keyboard = [
        [
            InlineKeyboardButton("👍 За", callback_data=f'like:{"|".join(ingredients_list)}'),
            InlineKeyboardButton("👎 Против", callback_data=f'dislike:{"|".join(ingredients_list)}')
        ]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    if update.message:
        await update.message.reply_text(message, reply_markup=reply_markup)
    elif update.callback_query:
        await update.callback_query.message.reply_text(message, reply_markup=reply_markup)

async def send_random_mix(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    selected_ingredients = random.sample(INGREDIENTS_POOL, 3)
    ingredients_set = frozenset(selected_ingredients)

    if ingredients_set in MIX_DATABASE:
        # Если микс уже есть в базе, показываем его независимо от оценок
        mix_info = MIX_DATABASE[ingredients_set]
        proportions = mix_info['proportions']
    else:
        # Для нового микса создаем пропорции
        proportions_raw = random.sample(range(1, 10), 3)
        total = sum(proportions_raw)
        normalized = [round(p / total * 100, -1) for p in proportions_raw]
        diff = 100 - sum(normalized)
        if diff != 0:
            normalized[0] += diff
        proportions = {ingredient: percent for ingredient, percent in zip(selected_ingredients, normalized) if percent > 0}
        # Не сохраняем новый микс в базу сразу, он будет сохранен только если получит лайк
        MIX_DATABASE[ingredients_set] = {"proportions": proportions, "likes": 0, "dislikes": 0}

    sorted_mix = sorted(proportions.items(), key=lambda x: x[1], reverse=True)
    mix_description = " | ".join(f"{ingredient} {percent}%" for ingredient, percent in sorted_mix)
    message = f"🎲 СЛУЧАЙНЫЙ МИКС: {mix_description}"

    # Создаем кнопки с правильным форматом callback_data
    ingredients_list = sorted(ingredients_set)
    keyboard = [
        [
            InlineKeyboardButton("👍 За", callback_data=f'like:{"|".join(ingredients_list)}'),
            InlineKeyboardButton("👎 Против", callback_data=f'dislike:{"|".join(ingredients_list)}')
        ]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    if update.message:
        await update.message.reply_text(message, reply_markup=reply_markup)
    elif update.callback_query:
        await update.callback_query.message.reply_text(message, reply_markup=reply_markup)
    
    user_mix_mode[user_id] = 'top'  # Следующий будет топовый

async def mix(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_active[user_id] = True
    user_mix_mode[user_id] = 'random'  # Начинаем со случайного
    await send_mix(update, context)

async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_active[update.effective_user.id] = False
    await update.message.reply_text("🚫 Миксование остановлено. Нажми /mix чтобы начать снова!")

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    data = query.data
    
    print(f"Получен callback_data: {data}")  # Отладочная информация
    
    # Обработка кнопок like/dislike
    if data.startswith(('like:', 'dislike:')):
        action, ingredients_str = data.split(":", 1)
        ingredients = frozenset(ingredients_str.split("|"))
        
        print(f"Обработка {action} для микса: {ingredients}")  # Отладочная информация
        
        if ingredients in MIX_DATABASE:
            if action == "like":
                MIX_DATABASE[ingredients]['likes'] += 1
            elif action == "dislike":
                MIX_DATABASE[ingredients]['dislikes'] += 1

            if user_id not in USER_DATABASE:
                USER_DATABASE[user_id] = {}
            if ingredients not in USER_DATABASE[user_id]:
                USER_DATABASE[user_id][ingredients] = {"likes": 0, "dislikes": 0}
            if action == "like":
                USER_DATABASE[user_id][ingredients]['likes'] += 1
            elif action == "dislike":
                USER_DATABASE[user_id][ingredients]['dislikes'] += 1

            print(f"Обновлены счетчики: {MIX_DATABASE[ingredients]}")  # Отладочная информация

            # Получаем текущий текст сообщения
            current_text = query.message.text
            
            # Добавляем информацию о голосовании
            vote_text = "👍 Ваш голос учтен!" if action == "like" else "👎 Ваш голос учтен!"
            new_text = f"{current_text}\n\n{vote_text}"
            
            # Обновляем сообщение без кнопок
            await query.edit_message_text(text=new_text)

            if user_active.get(user_id, False):
                # После любой оценки показываем микс из топа
                user_mix_mode[user_id] = 'top'
                await send_mix(update, context)
            return
        else:
            # Если микс не в базе и это лайк, добавляем его
            if action == "like":
                # Создаем пропорции для нового микса
                proportions_raw = random.sample(range(1, 10), 3)
                total = sum(proportions_raw)
                normalized = [round(p / total * 100, -1) for p in proportions_raw]
                diff = 100 - sum(normalized)
                if diff != 0:
                    normalized[0] += diff
                proportions = {ingredient: percent for ingredient, percent in zip(sorted(ingredients), normalized) if percent > 0}
                
                # Добавляем микс в базу
                MIX_DATABASE[ingredients] = {"proportions": proportions, "likes": 1, "dislikes": 0}
                
                # Добавляем в пользовательскую базу
                if user_id not in USER_DATABASE:
                    USER_DATABASE[user_id] = {}
                USER_DATABASE[user_id][ingredients] = {"likes": 1, "dislikes": 0}
                
                # Получаем текущий текст сообщения
                current_text = query.message.text
                new_text = f"{current_text}\n\n👍 Ваш голос учтен! Микс добавлен в базу."
                
                # Обновляем сообщение без кнопок
                await query.edit_message_text(text=new_text)
                
                if user_active.get(user_id, False):
                    # После любой оценки показываем микс из топа
                    user_mix_mode[user_id] = 'top'
                    await send_mix(update, context)
                return
            else:
                # Если это дизлайк для нового микса, просто показываем сообщение
                current_text = query.message.text
                new_text = f"{current_text}\n\n👎 Ваш голос учтен!"
                await query.edit_message_text(text=new_text)
                
                if user_active.get(user_id, False):
                    # После любой оценки показываем микс из топа
                    user_mix_mode[user_id] = 'top'
                    await send_mix(update, context)
                return

        print(f"Микс не найден в базе данных: {ingredients}")  # Отладочная информация
        await query.edit_message_text(text="❌ Ошибка: микс не найден")
        return

    # Обработка кнопок удаления
    if data == "rc":  # cancel_removal
        await query.edit_message_text(text="Удаление отменено.")
        return
    
    if data == "ra":  # remove_all_mixes
        if user_id in USER_DATABASE:
            USER_DATABASE[user_id].clear()
            await query.edit_message_text(text="✅ Все ваши миксы удалены.")
        else:
            await query.edit_message_text(text="❌ У вас нет миксов для удаления.")
        return
    
    if data.startswith("rm:"):  # remove_mix
        mix_id = int(data.split(":", 1)[1])
        
        # Находим микс по его ID
        for ingredients_set in list(USER_DATABASE[user_id].keys()):
            if hash(frozenset(ingredients_set)) % 10000 == mix_id:
                del USER_DATABASE[user_id][ingredients_set]
                ing_list = ", ".join(sorted(ingredients_set))
                await query.edit_message_text(text=f"✅ Микс '{ing_list}' удалён.")
                return
        
        await query.edit_message_text(text="❌ Микс не найден или уже удалён.")

async def save_database_periodically():
    while True:
        with open(DATABASE_FILE, "w", newline="", encoding="utf-8") as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(["ingredients", "proportions", "likes", "dislikes"])
            for ingredients_set, data in MIX_DATABASE.items():
                ingredients = ",".join(sorted(ingredients_set))
                proportions = ";".join(f"{k}:{int(v)}" for k, v in data['proportions'].items())
                writer.writerow([ingredients, proportions, data['likes'], data['dislikes']])

        with open(USER_DATABASE_FILE, "w", newline="", encoding="utf-8") as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(["user_id", "ingredients", "likes", "dislikes"])
            for user_id, mixes in USER_DATABASE.items():
                for ingredients_set, votes in mixes.items():
                    ingredients = ",".join(sorted(ingredients_set))
                    writer.writerow([user_id, ingredients, votes['likes'], votes['dislikes']])

        await asyncio.sleep(60)

async def top(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not MIX_DATABASE:
        await update.message.reply_text("Пока нет миксов в базе.")
        return

    sorted_mixes = sorted(MIX_DATABASE.items(), key=lambda item: item[1]['likes'], reverse=True)
    top_text = "\n\n".join(
        f"{', '.join(sorted(mix[0]))}: {mix[1]['likes']} 👍 / {mix[1]['dislikes']} 👎\n" +
        " | ".join(f"{ing} {perc}%" for ing, perc in sorted(mix[1]['proportions'].items(), key=lambda x: x[1], reverse=True))
        for mix in sorted_mixes[:5]
    )
    await update.message.reply_text(f"🔥 Топ миксов сообщества:\n\n{top_text}")

async def mytop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in USER_DATABASE or not USER_DATABASE[user_id]:
        await update.message.reply_text("У вас пока нет оценённых миксов.")
        return

    user_mixes = USER_DATABASE[user_id]
    # Фильтруем миксы, оставляя только те, у которых нет дизлайков
    filtered_mixes = {
        ingredients: data 
        for ingredients, data in user_mixes.items() 
        if data['dislikes'] == 0
    }
    
    if not filtered_mixes:
        await update.message.reply_text("У вас пока нет оценённых миксов.")
        return
    
    sorted_user_mixes = sorted(filtered_mixes.items(), key=lambda item: item[1]['likes'], reverse=True)
    
    top_text = "\n\n".join(
        f"{idx+1}. {', '.join(sorted(mix[0]))}: {mix[1]['likes']} 👍\n" +
        " | ".join(f"{ing} {perc}%" for ing, perc in sorted(MIX_DATABASE[mix[0]]['proportions'].items(), key=lambda x: x[1], reverse=True))
        for idx, mix in enumerate(sorted_user_mixes)
    )
    await update.message.reply_text(f"👤 Ваши любимые миксы:\n\n{top_text}\n\n"
                                  "Чтобы удалить миксы, используйте /mytop_remove")

async def mytop_remove(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in USER_DATABASE or not USER_DATABASE[user_id]:
        await update.message.reply_text("У вас пока нет оценённых миксов.")
        return

    user_mixes = USER_DATABASE[user_id]
    sorted_user_mixes = sorted(user_mixes.items(), key=lambda item: item[1]['likes'], reverse=True)
    
    keyboard = []
    for idx, (ingredients_set, _) in enumerate(sorted_user_mixes):
        ingredients_list = sorted(ingredients_set)
        # Формируем уникальный callback_data для каждого микса
        mix_id = hash(frozenset(ingredients_set)) % 10000
        callback_data = f"rm:{mix_id}"
        ingredients_str = ", ".join(ingredients_list)
        btn_text = f"❌ {idx+1}. {ingredients_str[:20]}{'...' if len(ingredients_str) > 20 else ''}"
        keyboard.append([InlineKeyboardButton(btn_text, callback_data=callback_data)])

    keyboard.append([InlineKeyboardButton("🗑️ Удалить все", callback_data="ra")])
    keyboard.append([InlineKeyboardButton("❌ Отмена", callback_data="rc")])

    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "Выберите миксы для удаления:",
        reply_markup=reply_markup
    )

def main():
    load_database()

    async def post_init(app):
        app.create_task(save_database_periodically())

    app = ApplicationBuilder().token(sys.argv[1]).post_init(post_init).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("mix", mix))
    app.add_handler(CommandHandler("stop", stop))
    app.add_handler(CommandHandler("top", top))
    app.add_handler(CommandHandler("mytop", mytop))
    app.add_handler(CommandHandler("mytop_remove", mytop_remove))
    
    # Единый обработчик для всех кнопок
    app.add_handler(CallbackQueryHandler(button))

    app.run_polling()

if __name__ == '__main__':
    main()
