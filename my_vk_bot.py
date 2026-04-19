# Импортируем библиотеку vk_api для работы с API ВКонтакте
import vk_api
# Импортируем модули для работы с Long Poll (получение событий в реальном времени)
from vk_api.bot_longpoll import VkBotLongPoll, VkBotEventType
# Импортируем функцию для генерации уникального ID сообщения
from vk_api.utils import get_random_id
# Импортируем random для случайного выбора участников и предсказаний
import random
# Импортируем time для создания пауз между сообщениями (анимация отсчёта)
import time
# Импортируем json для работы с файлами статистики
import json
# Импортируем os для проверки существования файлов
import os
# Импортируем datetime и timedelta для работы с таймерами (24 часа)
from datetime import datetime, timedelta

# Мой токен доступа к сообществу ВК (берётся из переменных окружения)
VK_TOKEN = os.environ.get("VK_TOKEN")
if not VK_TOKEN:
    print("❌ Ошибка: не найден токен в переменных окружения!")
    exit(1)

# ID моего сообщества (из URL группы vk.com/club237440494)
GROUP_ID = "237440494"
# Сколько часов нужно ждать между выборами (24 часа = 1 раз в сутки)
COOLDOWN_HOURS = 24
# Список файлов, которые нужно удалить при запуске (обнуление статистики)
FILES = ["stats.json", "last_winners.json"]

for f in FILES:
    if os.path.exists(f):
        os.remove(f)
        print(f"🗑️ Удалён {f} (статистика обнулена)")

vk = vk_api.VkApi(token=VK_TOKEN, api_version='5.199').get_api()
longpoll = VkBotLongPoll(vk_api.VkApi(token=VK_TOKEN), GROUP_ID)

def send(chat_id, msg):
    """Отправляет сообщение в беседу"""
    vk.messages.send(
        random_id=get_random_id(),
        chat_id=chat_id,
        message=msg
    )

def get_members(chat_id):
    """Возвращает список ID всех участников беседы (исключая ботов)"""
    members = []
    for offset in range(0, 10000, 200):
        r = vk.messages.getConversationMembers(
            peer_id=2000000000 + chat_id,
            offset=offset,
            count=200
        )
        members += [m['member_id'] for m in r['items'] if m['member_id'] > 0]
        if len(r['items']) < 200:
            break
        time.sleep(0.34)
    return members

def get_name(uid):
    """Получает имя и фамилию пользователя по его VK ID"""
    try:
        user = vk.users.get(user_ids=uid)[0]
        return f"{user['first_name']} {user['last_name']}"
    except:
        return f"Пользователь {uid}"

def load(f):
    """Загружает данные из JSON-файла"""
    if os.path.exists(f):
        with open(f, 'r', encoding='utf-8') as file:
            return json.load(file)
    return {}

def save(f, d):
    """Сохраняет данные в JSON-файл"""
    with open(f, 'w', encoding='utf-8') as file:
        json.dump(d, file, ensure_ascii=False, indent=2)

# СТАТИСТИКА ПОБЕД 
def update_stats(uid, title):
    """Увеличивает счётчик побед для пользователя"""
    d = load("stats.json")
    d.setdefault(str(uid), {}).setdefault(title, 0)
    d[str(uid)][title] += 1
    save("stats.json", d)
    return d[str(uid)][title]

def get_stats(chat_id):
    """Возвращает топ участников беседы по победам"""
    d, members = load("stats.json"), get_members(chat_id)
    res = []
    for uid in members:
        s = d.get(str(uid), {})
        h, t = s.get("красавчик", 0), s.get("пидор", 0)
        if h + t:
            res.append({
                "uid": uid,
                "name": get_name(uid),
                "handsome": h,
                "tomato": t,
                "total": h + t
            })
    return sorted(res, key=lambda x: x["total"], reverse=True)

# ТАЙМЕР ДЛЯ БЕСЕДЫ 
def check_chat_cooldown(chat_id, title):
    """
    Проверяет, выбирался ли уже победитель сегодня в этой беседе.
    Возвращает (можно_выбирать, сообщение_об_ошибке, данные_победителя)
    """
    d = load("last_winners.json")
    key = f"{chat_id}_{title}"
    if key in d:
        last_date = datetime.strptime(d[key]["date"], "%Y-%m-%d %H:%M:%S")
        if datetime.now() - last_date < timedelta(hours=COOLDOWN_HOURS):
            remain = timedelta(hours=COOLDOWN_HOURS) - (datetime.now() - last_date)
            hours = remain.seconds // 3600
            minutes = (remain.seconds % 3600) // 60
            return False, f"⏰ Жди {hours}ч {minutes}мин до следующего выбора!", d[key]
    return True, None, None

def save_winner(chat_id, title, uid, name):
    """Сохраняет победителя для этой беседы"""
    d = load("last_winners.json")
    key = f"{chat_id}_{title}"
    d[key] = {
        "user_id": uid,
        "name": name,
        "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    save("last_winners.json", d)

# ОТСЧЁТЫ 
STEPS = {
    "handsome": [
        ("🎰 КРУТИМ БАРАБАН!", 1),
        ("🔍 Ищем красавчика...", 1.5),
        ("📊 Бинарные опционы...", 1),
        ("🌖 Лунный гороскоп...", 1),
        ("💫 Лунная призма, дай силу...", 1),
        ("🎯 СЕКТОР ПРИЗ!", 1)
    ],
    "tomato": [
        ("🔞 ФЕДЕРАЛЬНЫЙ РОЗЫСК ПИДОРА!", 1.5),
        ("🚀 4 - спутник запущен...", 1),
        ("🚓 3 - сводки Интерпола...", 1),
        ("🙅 2 - друзья опрошены...", 1),
        ("📱 1 - профиль проанализирован...", 1),
        ("🎯 ЦЕЛЬ ОПОЗНАНА!", 1)
    ]
}

def countdown(chat_id, style):
    """Запускает эпичный отсчёт"""
    for t, d in STEPS[style]:
        send(chat_id, t)
        time.sleep(d)

# ПРЕДСКАЗАНИЯ 
def get_prediction():
    """Возвращает случайное предсказание из JSON-файла"""
    if not os.path.exists("predictions_1000.json"):
        return "🔮 Сегодня будет хороший день!"
    data = load("predictions_1000.json")
    preds = data if isinstance(data, list) else data.get("predictions", ["🔮 Удачи!"])
    return random.choice(preds)

# ОСНОВНАЯ ЛОГИКА ВЫБОРА 
def pick(chat_id, title):
    """
    Выбирает случайного участника (только если сегодня ещё не выбирали)
    title = "красавчик" или "пидор"
    """
    # Проверяем, можно ли выбирать сегодня
    can_choose, msg, last_winner = check_chat_cooldown(chat_id, title)
    
    if not can_choose:
        # Если уже выбирали сегодня — показываем кто и сколько осталось ждать
        if last_winner:
            mention = f"[id{last_winner['user_id']}|{last_winner['name']}]"
            emoji = "🏆" if title == "красавчик" else "🔞"
            name_rus = "Красавчик" if title == "красавчик" else "Пидор"
            send(chat_id, f"{emoji} Сегодняшний {name_rus} дня уже выбран!\n{mention}\n{msg}")
        else:
            send(chat_id, msg)
        return
    
    # Если можно выбирать — запускаем отсчёт
    countdown(chat_id, "handsome" if title == "красавчик" else "tomato")
    
    # Получаем список участников
    members = get_members(chat_id)
    if not members:
        send(chat_id, "❌ Сделайте бота администратором!")
        return
    
    # Выбираем случайного участника
    lucky = random.choice(members)
    name = get_name(lucky)
    wins = update_stats(lucky, title)
    save_winner(chat_id, title, lucky, name)
    
    # Формируем итоговое сообщение
    if title == "красавчик":
        emoji = "🎉🏆"
        tu = "КРАСАВЧИК ДНЯ"
        extra = f"✨ {name} был красавчиком {wins} раз(а)! ✨"
    else:
        emoji = "🔞🔴"
        tu = "ПИДОР ДНЯ"
        extra = f"🎯 Пидорас: {wins} раз(а)\n🚨 Приговорён к званию пидора!"
    
    send(chat_id, f"{emoji} {tu} — [id{lucky}|{name}]! {emoji}\n{extra}")

# ЗАПУСК БОТА 
print("✅ Бот запущен! Команды: /красавчик, /пидор, /предсказание, /статистика, /")

for event in longpoll.listen():
    if event.type == VkBotEventType.MESSAGE_NEW and event.from_chat:
        chat = event.chat_id
        text = event.obj.message["text"].lower().strip()
        
        if text == "/":
            send(chat, "📋 **Команды:**\n🏆 /красавчик\n🔞 /пидор\n🔮 /предсказание\n📊 /статистика\n❓ /")
        
        elif text == "/красавчик":
            pick(chat, "красавчик")
        
        elif text == "/пидор":
            pick(chat, "пидор")
        
        elif text == "/предсказание":
            send(chat, f"🔮 **Предсказание:**\n{get_prediction()}")
        
        elif text == "/статистика":
            stats = get_stats(chat)
            if not stats:
                send(chat, "📊 Статистики пока нет!")
            else:
                msg = "🏆 **СТАТИСТИКА** 🏆\n\n"
                for i, x in enumerate(stats[:15], 1):
                    if i == 1:
                        medal = "🥇"
                    elif i == 2:
                        medal = "🥈"
                    elif i == 3:
                        medal = "🥉"
                    else:
                        medal = f"{i}."
                    msg += f"{medal} {x['name']}\n   🏆 Красавчик: {x['handsome']} | 🔞 Пидор: {x['tomato']}\n"
                send(chat, msg)
