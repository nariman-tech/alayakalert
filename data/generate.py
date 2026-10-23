"""Генератор синтетического датасета SafeNet KZ.

Все аккаунты, номера, карты, домены и бренды — вымышленные. Схемы построены по
мотивам реальных казахстанских кейсов 2025–2026 годов (см. README).

Две «манеры письма»:
    A — обучающая часть (train): аккуратный русский;
    B — тестовая часть (test): другие формулировки, сленг, казахский, транслит, эмодзи.
Так метрики на тесте не завышены тем, что система видела те же фразы.

Внутри датасета специально спрятаны связи (для графа):
    - один телефон организатора в розыгрышах, пирамидах и канале казино;
    - один промокод LUCKY77 у нескольких блогеров;
    - один скриншот «выплаты» в нескольких чатах пирамид;
    - один «победитель» в нескольких эфирах-аукционах.

Запуск:  python -m data.generate   ->  data/cases.jsonl
"""
from __future__ import annotations

import json
import random
from pathlib import Path

R = random.Random(2026)
OUT = Path(__file__).with_name("cases.jsonl")

# ── Вымышленные значения ─────────────────────────────────────────────────────
STEMS = ["aru", "dana", "aliya", "nurlan", "yerlan", "madina", "asel", "timur", "saule", "bekzat", "zhanna",
         "dias", "kamila", "arman", "ayaulym", "marat", "togzhan", "erzhan", "inkar", "sanzhar", "malika", "askar"]
TAILS = ["_style", "_life", "_shop", ".kz", "_official", "_mama", "_vlog", "_beauty", "_biz", "_invest", "_travel", "_show"]
NETWORK_PHONE = "+7 700 000 77 01"
NETWORK_CARD = "4400 43** **** 7701"
NETWORK_PROMO = "LUCKY77"
NETWORK_DOMAIN = "luckystep7.top"
NETWORK_SCREEN = "ph_9f3a1c77"
NETWORK_WINNER = "@aidar_k_777"
NETWORK_SHILL = "@bank_helper_01"

PRIZES = ["iPhone 17 Pro", "Toyota Camry 75", "двухкомнатную квартиру в Шымкенте", "1 000 000 тг", "двухэтажный дом",
          "MacBook Air", "Chery Tiggo 7"]
PRIZES_SMALL = ["сертификат на 20 000 тг", "беспроводные наушники", "набор косметики", "ужин на двоих",
                "фирменную худи", "умную колонку"]
COURSES = ["Сторис, которые продают", "Таргет с нуля", "Финансовая свобода за 30 дней", "Мама в декрете зарабатывает",
           "Reels-мастер", "Миллион на маркетплейсах"]
PRICES = ["9 990", "14 990", "19 990", "29 990", "30 000", "49 990"]
ENTRY = ["500", "1 000", "2 000", "3 000", "5 000"]
GADGETS = ["iPhone 17", "Samsung Galaxy S26", "AirPods Pro", "PlayStation 5", "смарт-часы"]
FEES = ["2 900", "3 500", "4 500", "6 900"]
CASINOS = ["LuckyStep Casino", "GoldSpin", "Altyn Slots", "StepWin Casino", "Jackpot Dala"]
BKS = ["SportLine", "BetQala", "GolBet KZ"]
PROMOS = ["SPIN500", "ALTYN100", "GOLD2X", "STEP300", "DALA777"]
WINS = ["350 000 тг", "1,2 млн", "480к", "2 500 000 ₸", "760 000 тг"]
STAKES = ["2 000 тг", "5к", "10 000 тг"]
SHORT = ["bit.ly/3xK9pQ", "clck.ru/37Fq2", "cutt.ly/wQ8zLm", "t.ly/Kx2a"]
MIRRORS = [("goldspin12.xyz", "goldspin14.xyz"), ("altynslots3.club", "altynslots5.club"),
           ("stepwin21.top", "stepwin22.top"), ("jackpotdala1.vip", "jackpotdala4.vip")]
BOTS = ["mirror_step_bot", "altyn_links_bot", "spin_news_bot"]
PROJECTS = ["Asyl Profit", "Оборот 30", "Nur Capital", "Dala Invest", "Береке", "Smart AI Trade", "Altyn Market"]
LEGENDS = ["искусственный интеллект", "добычу алмазов", "маркетплейсы", "майнинг криптовалюты", "арбитраж"]
INOUT = [(5000, 10000), (10000, 25000), (20000, 50000), (3000, 6000), (50000, 100000)]
DAYS = [3, 5, 7, 10, 14]
PCT = [20, 30, 40, 50]
DAILY = ["1,5", "2", "3", "5"]
CITIES = ["Шымкента", "Актау", "Павлодара", "Алматы"]
PLAT_POST = ["Instagram", "TikTok", "Telegram"]
PLAT_CHAT = ["WhatsApp", "Telegram"]


def pick(xs):
    return R.choice(xs)


def money(n: int) -> str:
    return f"{n:,}".replace(",", " ")


def account() -> str:
    return "@" + pick(STEMS) + pick(TAILS) + str(R.randint(1, 99))


def phone() -> str:
    return f"+7 700 000 {R.randint(10, 69)} {R.randint(10, 99)}"


def card() -> str:
    return f"4400 43** **** {R.randint(1000, 7699)}"


def values(**over) -> dict:
    a, b = pick(INOUT)
    v = {"prize": pick(PRIZES), "prize_small": pick(PRIZES_SMALL), "course": pick(COURSES), "price": pick(PRICES),
         "entry": pick(ENTRY), "gadget": pick(GADGETS), "fee": pick(FEES), "casino": pick(CASINOS), "bk": pick(BKS),
         "promo": pick(PROMOS), "win": pick(WINS), "stake": pick(STAKES), "short": pick(SHORT), "phone": phone(),
         "card": card(), "project": pick(PROJECTS), "legend": pick(LEGENDS), "in": money(a), "out": money(b),
         "days": pick(DAYS), "pct": pick(PCT), "daily": pick(DAILY), "city": pick(CITIES), "bot": pick(BOTS),
         "date": pick(["в пятницу", "в субботу в 20:00", "завтра в 21:00"])}
    m1, m2 = pick(MIRRORS)
    v.update({"mirror1": m1, "mirror2": m2, "url": f"{m1}/?ref={R.randint(100, 999)}"})
    v.update(over)
    return v


# ── Банки шаблонов: A (train) и B (test) ─────────────────────────────────────
T = {
    "course_giveaway": {
        "A": [
            "🎁 РОЗЫГРЫШ {prize}! Условия участия: купить мой курс «{course}» за {price} тг и прислать чек в директ. Победителя выберем колесом фортуны в прямом эфире {date}.",
            "Разыгрываю {prize} среди учеников! Чтобы участвовать, нужно приобрести гайд «{course}» ({price} тг). Итоги подведём рандомайзером {date}.",
            "Друзья, каждый, кто купит марафон «{course}» до воскресенья, участвует в розыгрыше {prize}. Стоимость {price} тг. Победителя определит барабан.",
            "Новый розыгрыш: {prize}! Покупаешь курс «{course}» — получаешь номерок. Чем больше курсов, тем больше номерков. Победителя выберем на поле чудес в эфире.",
            "Условие розыгрыша {prize} простое: оплата подписки на мой закрытый клуб ({price} тг в месяц). Победителя определит генератор случайных чисел. Оплата на каспи {phone}.",
        ],
        "B": [
            "Ребят, разыгрываем {prize} 🔥 участвуют ТОЛЬКО те, кто взял мой интенсив «{course}» ({price}₸). Чек в лс, номерок дам. Крутим рандом в эфире {date}",
            "Ұтыс ойыны! {prize} ойнатамыз. Қатысу үшін «{course}» курсын сатып алыңыз — {price} тг. Жеңімпазды барабан анықтайды.",
            "rozygrysh {prize}!! chtoby uchastvovat kupi kurs «{course}» za {price} tg, pobeditelya vyberem randomom v efire",
            "{prize} кому? 😏 Беру в розыгрыш всех, кто оплатит урок «{course}» — {price} тенге. Жеребьёвка {date}, всё честно",
            "Мега-гив на {prize}! Каждый, кто купит вебинар «{course}», получает номер участника. Победителя определим через random.org 🎰",
        ],
    },
    "paid_entry": {
        "A": [
            "Розыгрыш {prize}! Участие — {entry} тг за один номер, всего 300 номеров. Переводите на каспи {phone}, в комментарии — ваш ник. Победителя выберем рандомайзером.",
            "Продаю слоты на розыгрыш {prize}: {entry} тг за слот, осталось 40 слотов. Деньги на Kaspi {phone}. Жеребьёвка в прямом эфире.",
            "Лотерея на {prize}! Билеты по {entry} тг. Чем больше билетов, тем выше шанс. Оплата на карту {card}. Итоги {date}, крутим барабан.",
        ],
        "B": [
            "кто хочет {prize} за {entry}₸?? 😱 скидываем на каспи {phone}, пишем ник — вы в списке. осталось 15 номеров! крутим колесо в 22:00",
            "{prize} ұтып алғың келе ме? Қатысу үшін {entry} тг каспиге аудар {phone}. Жеңімпазды кездейсоқ таңдаймыз, тек 20 орын қалды!",
            "Всего 200 мест по {entry} тг 🎟 Кто успел — тот в игре за {prize}. Каспи {phone}. Победителя определим рандомом в лайве",
        ],
    },
    "fake_win": {
        "A": [
            "Поздравляем! Вы выиграли {gadget} в розыгрыше нашего магазина. Для получения приза оплатите доставку {fee} тг на номер {phone} в течение 24 часов.",
            "Здравствуйте! Ваш аккаунт стал победителем розыгрыша {gadget}. Оплатите комиссию за оформление приза {fee} тг. Ссылка для оплаты: {short}",
            "Вы победитель еженедельного конкурса! Приз — {gadget}. Осталось только оплатить страховку пересылки {fee} тг на карту {card}. Успейте до конца дня.",
        ],
        "B": [
            "🎉 Құттықтаймыз! Сіз {gadget} ұтып алдыңыз! Жеткізу ақысын төлеңіз — {fee} тг, каспиге {phone}.",
            "ты выиграл {gadget}!!! заполни анкету по ссылке {short} и оплати доставку {fee} тг, иначе приз уйдёт следующему",
            "Ваш приз ждёт вас 🎁 {gadget} уже упакован. Нужно оплатить налог на выигрыш {fee}₸ — переводите на номер {phone}, только сегодня",
        ],
    },
    "free_giveaway": {
        "A": [
            "🎁 Розыгрыш: {prize_small}! Условия: подписаться на страницу, поставить лайк и отметить двух друзей в комментариях. Участие бесплатное. Итоги {date}, победителя выберем рандомайзером.",
            "Дарим {prize_small} в честь 10 000 подписчиков! Ничего платить не нужно — просто подпишитесь и сделайте репост. Победителя определит random.org.",
            "Конкурс для подписчиков: напишите в комментариях, за что любите наш город. Автор лучшего ответа получит {prize_small}. Участие бесплатное.",
        ],
        "B": [
            "Гив на {prize_small} 🎁 подписка + лайк + отметь 2 друзей. никаких оплат, всё бесплатно. итоги через рандом {date}",
            "Тегін ұтыс! {prize_small} сыйлаймыз. Парақшаға жазылып, 2 досыңды белгіле. Жеңімпазды кездейсоқ таңдаймыз.",
            "Разыгрываем {prize_small} среди тех, кто оставит отзыв о нашей кофейне. Покупать ничего не нужно, платить тоже 🙂",
        ],
    },
    "official_lottery": {
        "A": [
            "Государственная лотерея: билеты «Сәтті Жұлдыз» можно купить в приложении и в киосках. Тираж {date}, трансляция на сайте официального оператора.",
            "Новый тираж национальной лотереи! Джекпот 50 млн тг. Билеты продаются только через официального оператора «Сәтті Жұлдыз».",
        ],
        "B": [
            "Сәтті Жұлдыз лотереясы: жаңа тираж сенбі күні. Билеттерді ресми оператордан ғана сатып алыңыз.",
            "Купил билет Сәтті Жұлдыз в киоске у дома, тираж {date} 🤞 кто тоже играет в государственную лотерею?",
        ],
    },
    "news_lottery": {
        "A": [
            "Министерство туризма и спорта предупреждает: розыгрыши с платным участием в соцсетях запрещены. Блогера из {city} оштрафовали за лотерею под видом продажи курсов.",
            "Осторожно, мошенники! В соцсетях рассылают сообщения «вы выиграли смартфон» и просят оплатить доставку. Не переводите деньги незнакомцам.",
        ],
        "B": [
            "Сақ болыңыз! Алаяқтар «сіз ұтып алдыңыз» деп хабарлама жіберіп, жеткізу ақысын сұрайды.",
            "Блогера из {city} оштрафовали за розыгрыш авто среди покупателей курса. Юрист объясняет, почему это считается незаконной лотереей.",
        ],
    },
    "native_blogger": {
        "A": [
            "Поднял сегодня {win} на слотах, сам в шоке 😱 Играю тут: {url}. По моему промокоду {promo} дают +200% к первому депозиту.",
            "Как я за вечер поднял {win} с {stake}? Всё просто: {casino}, авиатор и немного удачи. Ссылка в шапке профиля, промокод {promo}.",
            "Вывел {win} за 5 минут, деньги уже на карте ✅ Кто хочет так же — регистрация по моей ссылке {short}, бонус 150 фриспинов.",
            "Это был занос x500 в Gates of Olympus! Скрин вывода в сторис. Промокод {promo} — бонус на депозит.",
        ],
        "B": [
            "Это нереально 😳 {win} за один спин, кто со мной? ссылка в био, код {promo} (+250% к пополнению)",
            "Мен бүгін {win} ұтып алдым 🎰 {casino}, ойын автоматтары, сілтеме профильде, промокод {promo}",
            "zanos {win} na {casino}! vyvel srazu, link v shapke, promokod {promo}",
            "ну что, опять иксы 🚀 {win} на краше. пиши «+» в директ — скину рабочую ссылку и промик {promo}",
        ],
    },
    "brand_cover": {
        "A": [
            "{bk} — лицензированная букмекерская компания, ставки на спорт абсолютно легально. А в разделе «Казино» тебя ждут слоты и рулетка с бонусом 100% на депозит! Ссылка: {short}",
            "Ставлю только в легальной БК {bk} 💪 Кстати, там появились игровые автоматы — вчера поднял {win}. Регистрация по ссылке в профиле.",
            "Официальный букмекер {bk}: ставки на спорт, а ещё рулетка, авиатор и джекпоты. Промокод {promo} даёт фриспины.",
        ],
        "B": [
            "у {bk} лицензия, так что всё ок 👌 но я там больше по слотам 🎰 вчера x200 поймал. ссылка в шапке",
            "{bk} — заңды букмекер, лицензиясы бар. Ал ойын автоматтары бөлімінде бонус +150% депозитке! Сілтеме профильде, промокод {promo}",
            "Ставки на футбол — в {bk}, а пока матч не начался, кручу рулетку там же 😅 код {promo} на бонус к депозиту",
        ],
    },
    "channel_mirror": {
        "A": [
            "Казино {casino} снова заблокировали? Держите рабочее зеркало: {mirror1} и запасное {mirror2}. Все актуальные ссылки — в нашем закрытом канале.",
            "Без VPN не заходит? Вот актуальный вход в {casino}: {mirror1}. Подписывайтесь на бота @{bot}, он присылает новые зеркала каждый день.",
            "Все мои схемы для слотов — только в приватном канале. Вход по ссылке {short}. Там же рабочее зеркало и промокоды. Пополнение без карты — переводи на каспи {phone}.",
        ],
        "B": [
            "aktualnoe zerkalo {casino}: {mirror1} 🔥 staroe ne rabotaet, pishi v bota @{bot}",
            "Жаңа айна: {mirror1}. Казино бұғатталды ма? Біздің жабық канал — {short}",
            "блокнули опять 🙄 новая ссылочка на слоты {mirror2}, старую {mirror1} не трогайте. остальное — в вип канале",
        ],
    },
    "promo_food": {
        "A": [
            "Промокод PIZZA20 даёт скидку 20% на первый заказ доставки! Действует до конца недели.",
            "Дарим промокод SALE15 на скидку 15% на всю коллекцию. Ссылка на магазин в шапке профиля.",
            "Пополни баланс мобильного и получи бонус по промокоду MOBI10.",
        ],
        "B": [
            "код TAXI300 = минус 300 тг на первую поездку 🚕 ссылка в био",
            "Промокод на скидку в книжном: BOOK10, действует онлайн и в магазинах",
            "Жеңілдік промокоды: KOFE25 — барлық сусындарға 25% жеңілдік",
        ],
    },
    "sports_news": {
        "A": [
            "Наша команда обыграла соперника 2:1, решающий гол на 89-й минуте. Следующий матч — в воскресенье.",
            "Прогноз на финал от нашего аналитика: ждём закрытую игру и мало голов. Смотрим вместе!",
        ],
        "B": [
            "Біздің команда бүгін жеңіске жетті! Келесі ойын жексенбіде.",
            "Смотрели вчера матч? Это был занос века от нашего вратаря 😂",
        ],
    },
    "videogame": {
        "A": [
            "Поднял ранг в Dota 2 до Divine за неделю, делюсь гайдом по герою. Ссылка на стрим в шапке.",
            "Стрим сегодня в 20:00: проходим новую часть игры, бесплатный розыгрыш скинов среди зрителей.",
        ],
        "B": [
            "x100 урона с этим билдом, проверено 😎 гайд в описании",
            "Ойын стримі бүгін кешке, бәріңді күтемін! Тегін сыйлықтар да болады.",
        ],
    },
    "news_casino": {
        "A": [
            "АФМ: блогеров, рекламирующих онлайн-казино, привлекают к ответственности. Реклама азартных игр в соцсетях запрещена.",
            "Как распознать скрытую рекламу казино: «случайный» выигрыш блогера, промокод на депозит и ссылка в шапке профиля. Не ведитесь.",
        ],
        "B": [
            "Психолог о зависимости от слотов: почему «занос» у блогера — это реклама, а не удача. Будьте бдительны.",
            "Онлайн-казино жарнамасы заңсыз. Сақ болыңыз, алаяқтарға сенбеңіз!",
        ],
    },
    "legit_course": {
        "A": [
            "Курс Excel для бухгалтеров: 12 уроков, стоимость 25 000 тг. Записаться можно по ссылке в шапке профиля.",
            "Открыт набор на курс английского языка для школьников. Первое занятие бесплатно, далее 20 000 тг в месяц.",
        ],
        "B": [
            "Python для начинающих — старт 1 ноября, 8 недель, оплата частями. Подробности в описании канала.",
            "Ағылшын тілі курсы: айына 20 000 тг, алғашқы сабақ тегін.",
        ],
    },
    "post_double": {
        "A": [
            "Вложи {in} тг — через {days} дней получишь {out} тг! Проверено, выплаты каждый день. Переводите на мой Kaspi Gold {phone}.",
            "Инвестиционный проект «{project}»: {pct}% в месяц, гарантированный доход без риска. Осталось 5 мест, пишите в личку.",
            "Хочешь пассивный доход? Вкладываешь {in} тг, через неделю выводишь {out} тг. За каждого приглашённого друга +10% от его вклада.",
            "Оборот: внеси {in} тг на карту {card}, через {days} дня забирай {out} тг. Набор закрывается сегодня!",
        ],
        "B": [
            "{in} тг салсаңыз, {days} күннен кейін {out} тг аласыз! Каспиге аударыңыз {phone}. 5 орын қалды.",
            "vlozhi {in} poluchi {out} za {days} dnei, perevod na kaspi {phone}, uspei!",
            "Ежедневно {daily}% к вкладу 📈 вывод в любое время. Пригласи друга — получи 5% с его депозита.",
            "Касса взаимопомощи «{project}»: кладёшь {in}, через {days} дней забираешь {out}. Всё честно, это не пирамида 🙏 каспи {phone}",
        ],
    },
    "legend_project": {
        "A": [
            "{project} — международный ИИ-проект: нейросеть торгует на бирже за вас. Доход от {daily}% в день, вывод на Kaspi. Регистрация по реферальной ссылке.",
            "Маркетплейс-инвестиции: покупаешь «магазин» за {in} тг и получаешь {pct}% в месяц с продаж. Гарантия выплат 100%.",
            "Компания добывает алмазы в Африке, вкладчики получают {pct}% в месяц. Переводите на карту куратора {card}.",
        ],
        "B": [
            "AI-бот торгует криптой 24/7 🤖 пассивный доход {daily}% ежедневно, минималка {in} тг. Пиши «+» куратору, пригласи друга — бонус.",
            "Халықаралық жоба {project}: айына {pct}% пайда, кепілдік 100%. Каспиге аударыңыз {phone}.",
            "майнинг без оборудования, просто вкладываешь {in} и через месяц получаешь {out}. реферальная программа 3 уровня",
        ],
    },
    "referral_mlm": {
        "A": [
            "Структура до 5 уровней: с каждого приглашённого вы получаете 10%, со второй линии 5%. Вход — {in} тг на карту куратора {card}. Это стабильный доход.",
            "Приведи трёх друзей — и твой вклад вернётся в двойном размере. Переводы на мой каспи {phone}. Пассивный доход без вложений сил.",
        ],
        "B": [
            "Досыңды шақыр — әр адам үшін 5000 тг бонус! Кіру — {in} тг, картаға аудар {card}. Тұрақты табыс кепілдігі.",
            "реф система 🔥 за каждого нового партнёра 15% от его взноса. вход {in}, кидать на каспи голд {phone}. стабильный доход",
        ],
    },
    "kassa": {
        "A": [
            "«{project} касса айналымы» тобына қош келдіңіз! {in} тг салыңыз, кезегіңіз келгенде {out} тг аласыз. Каспиге аударыңыз {phone}.",
            "Касса айналымы: әр апта сайын 10 адам {in} тг салады, бір адам бәрін алады. Тұрақты табыс, асығыңыз! Каспиге {phone}.",
        ],
        "B": [
            "Жаңа айналым ашылды! {in} тг салсаңыз, 10 күннен кейін {out} тг аласыз. Шақырылған әр досыңыз үшін бонус.",
            "Касса айналымы «{project}»: тек бүгін орын қалды, кепілдік бар, ақшаны каспиге аударыңыз {phone}.",
        ],
    },
    "bank": {
        "A": [
            "Депозит «Накопительный»: ставка до 14,5% годовых, ГЭСВ 15,2%. Вклады гарантируются КФГД. Откройте онлайн в приложении.",
            "Пригласи друга в приложение банка и получи 2 000 ₸ бонусов. Подробные условия на сайте банка.",
            "Облигации на бирже: ориентировочная доходность 12–13% годовых, есть риск потери капитала. Перед покупкой изучите проспект.",
        ],
        "B": [
            "Жинақ депозиті — жылдық 14%, салымдар КФГД кепілдігімен қорғалған.",
            "Кэшбэк до 5% в месяц на покупки в любимых магазинах 💳",
            "Банк поднял ставку по депозиту до 15% годовых, успейте открыть до конца месяца.",
        ],
    },
    "news_pyramid": {
        "A": [
            "АФМ ликвидировало очередную финпирамиду: организаторы обещали 30% в месяц и принимали деньги на личные карты. Не вкладывайте в сомнительные проекты.",
            "Как распознать финансовую пирамиду: обещание высокой доходности, бонусы за приглашённых, переводы на личную карту.",
        ],
        "B": [
            "Қаржы пирамидасынан сақ болыңыз! Алаяқтар айына 30% пайда уәде етеді.",
            "Задержан организатор пирамиды «оборот», вкладчикам обещали x2 за неделю.",
        ],
    },
    "charity": {
        "A": [
            "Собираем на лечение Айдара, реквизиты благотворительного фонда указаны в профиле. Отчёт о каждой покупке публикуем.",
            "Благотворительный забег: регистрационный взнос 5 000 тг идёт на счёт фонда «Шанс», участники получают футболку.",
        ],
        "B": [
            "Қайырымдылық жәрмеңкесі сенбі күні! Түскен қаражат толығымен қор шотына аударылады.",
            "Помогаем приюту для животных 🐾 реквизиты фонда в шапке, отчёты каждую неделю",
        ],
    },
}

SCHEMES = {
    # name: (track, label, count_A, count_B, type)
    "course_giveaway": (1, 1, 10, 6, "post"), "paid_entry": (1, 1, 8, 4, "post"), "fake_win": (1, 1, 8, 4, "post"),
    "free_giveaway": (1, 0, 12, 6, "post"), "official_lottery": (1, 0, 5, 3, "post"), "news_lottery": (1, 0, 5, 3, "post"),
    "native_blogger": (2, 1, 10, 5, "post"), "brand_cover": (2, 1, 6, 3, "post"), "channel_mirror": (2, 1, 8, 4, "post"),
    "promo_food": (2, 0, 8, 4, "post"), "sports_news": (2, 0, 5, 3, "post"), "videogame": (2, 0, 5, 3, "post"),
    "news_casino": (2, 0, 6, 3, "post"), "legit_course": (2, 0, 5, 3, "post"),
    "post_double": (3, 1, 8, 4, "post"), "legend_project": (3, 1, 6, 3, "post"), "referral_mlm": (3, 1, 5, 3, "post"),
    "kassa": (3, 1, 4, 2, "post"), "bank": (3, 0, 8, 4, "post"), "news_pyramid": (3, 0, 6, 3, "post"),
    "charity": (3, 0, 4, 2, "post"),
}

SCHEME_NAMES = {
    "course_giveaway": "Розыгрыш «купи курс — участвуй»", "paid_entry": "Платный взнос за участие",
    "fake_win": "Фейковый выигрыш", "auction_stream": "Эфир-аукцион «кто последний скинет»",
    "free_giveaway": "Честный бесплатный розыгрыш", "official_lottery": "Официальная лотерея",
    "news_lottery": "Новость / предупреждение", "free_stream": "Бесплатный розыгрыш в эфире",
    "charity_auction": "Благотворительный аукцион вещи",
    "native_blogger": "Нативная реклама блогера", "brand_cover": "Легальный бренд как прикрытие",
    "channel_mirror": "Канал-прокладка и зеркала", "network_promo": "Сеть блогеров с одним промокодом",
    "promo_food": "Промокод магазина/доставки", "sports_news": "Спортивные новости", "videogame": "Видеоигры",
    "news_casino": "Новость / предупреждение", "legit_course": "Обычный платный курс",
    "chat_pyramid": "Чат «вложи — получи»", "post_double": "Пост «вложи — получи»",
    "legend_project": "Псевдобизнес с легендой", "referral_mlm": "Реферальная сеть", "kassa": "«Касса айналымы»",
    "bank": "Банковский продукт", "news_pyramid": "Новость / предупреждение", "charity": "Благотворительный сбор",
    "family_chat": "Родительский чат: сбор на подарок", "edu_chat": "Чат обучения инвестициям",
}

_counter = 0


def new_id(track: int, kind: str) -> str:
    global _counter
    _counter += 1
    return f"T{track}-{kind.upper()[:4]}-{_counter:04d}"


def post_case(scheme: str, style: str, v: dict | None = None, acc: str | None = None) -> dict:
    track, label, *_ = SCHEMES.get(scheme, (2, 1, 0, 0, "post"))
    v = v or values()
    text = pick(T[scheme][style]).format(**v)
    plat = pick(PLAT_POST)
    return {"id": new_id(track, "post"), "track": track, "label": label, "scheme": scheme,
            "scheme_name": SCHEME_NAMES[scheme], "type": "post", "platform": plat, "account": acc or account(),
            "title": f"Публикация в {plat}", "split": "train" if style == "A" else "test",
            "messages": [{"t": 0, "author": acc or "", "text": text}], "images": []}


# ── Эфиры ────────────────────────────────────────────────────────────────────
VIEWERS = ["@" + s + str(R.randint(10, 99)) for s in STEMS]


def auction_stream(style: str) -> dict:
    acc = account()
    host = acc
    rounds = R.randint(4, 6)
    prize = pick([50_000, 100_000, 180_000])
    ph = NETWORK_PHONE if R.random() < 0.25 else phone()
    winner_star = NETWORK_WINNER if R.random() < 0.5 else "@" + pick(STEMS) + "_win" + str(R.randint(10, 99))
    shill = NETWORK_SHILL if R.random() < 0.5 else "@" + pick(STEMS) + "_bank" + str(R.randint(10, 99))
    msgs, bids, winners = [], [], []
    t = 0
    intro = {
        "A": [f"Всем привет, начинаем ежедневный эфир! Сегодня разыгрываем банк {money(prize)} тг.",
              f"Правила простые: ставка от 200 тг на Kaspi {ph}, кто последний скинет — забирает весь банк!",
              "Один победитель выигрывает только один раз и дальше не участвует, всё честно.",
              "Это благотворительность, мы помогаем людям 🙏"],
        "B": [f"Салем бәріне! Бүгінгі банк — {money(prize)} тг 🔥",
              f"ставочки кидаем на каспи {ph}, кто последний закинул — тот и забрал весь банк",
              "бір адам бір рет қана ұтады, кто выиграл — дальше смотрит 😉",
              "это не казино, это благотворительность, от души"],
    }[style]
    for line in intro:
        msgs.append({"t": t, "author": host, "text": line})
        t += R.randint(15, 40)
    first_star = R.randint(1, 2)
    for r in range(1, rounds + 1):
        n_bids = R.randint(5, 9)
        total_round = 0
        for _ in range(n_bids):
            t += R.randint(10, 40)
            u = pick(VIEWERS)
            amt = pick([200, 300, 500, 1000, 2000])
            bids.append({"t": t, "round": r, "user": u, "amount": amt})
            total_round += amt
            if R.random() < 0.4:
                txt = {"A": f"Ставка от {u} — {amt} тг принята, банк растёт!",
                       "B": f"{u} +{amt} 🔥 банк растёт, кто больше?"}[style]
                msgs.append({"t": t, "author": host, "text": txt})
        # последняя ставка — «свой» за несколько секунд до конца
        t += R.randint(20, 40)
        last_user = shill if R.random() < 0.8 else pick(VIEWERS)
        bids.append({"t": t, "round": r, "user": last_user, "amount": pick([1000, 2000, 3000])})
        msgs.append({"t": t, "author": host, "text": {"A": "До конца раунда 10 секунд! Кто последний?",
                                                       "B": "10 секунд, 10 секунд! кто последний — тот забирает 💰"}[style]})
        t += R.randint(5, 12)
        w = winner_star if r >= first_star and R.random() < 0.7 else last_user
        winners.append({"t": t, "round": r, "user": w, "prize": prize})
        msgs.append({"t": t, "author": host,
                     "text": {"A": f"Победитель раунда — {w}! Забирает {money(prize)} тг 🎉",
                              "B": f"Жеңімпаз — {w}! Құттықтаймыз 🎉 забирает {money(prize)}"}[style]})
        t += R.randint(20, 60)
    msgs.append({"t": t, "author": host, "text": {"A": "Спасибо всем! Завтра снова эфир в 20:00, банк будет больше!",
                                                  "B": "ертең тағы эфир 🔥 завтра снова в 20:00"}[style]})
    return {"id": new_id(1, "stream"), "track": 1, "label": 1, "scheme": "auction_stream",
            "scheme_name": SCHEME_NAMES["auction_stream"], "type": "stream", "platform": "Telegram",
            "account": acc, "title": "Прямой эфир в Telegram-канале", "split": "train" if style == "A" else "test",
            "messages": msgs, "bids": bids, "winners": winners, "images": [],
            "rules": {"one_win_per_user": True, "start_prize": prize}}


def free_stream(style: str) -> dict:
    acc = account()
    msgs, winners, t = [], [], 0
    lines = {"A": ["Привет! Сегодня бесплатный розыгрыш среди подписчиков: три подарка.",
                   "Ничего переводить не нужно, просто напишите «+» в чат.",
                   "Крутим рандомайзер по списку комментаторов..."],
             "B": ["Сәлем! Бүгін жазылушылар арасында тегін ұтыс 🎁",
                   "Ештеңе аударудың қажеті жоқ, чатқа «+» жазыңыз.",
                   "Рандомайзер айналып жатыр..."]}[style]
    for line in lines:
        msgs.append({"t": t, "author": acc, "text": line})
        t += R.randint(30, 60)
    for r, u in enumerate(R.sample(VIEWERS, 3), start=1):
        t += R.randint(30, 90)
        winners.append({"t": t, "round": r, "user": u, "prize": 0})
        msgs.append({"t": t, "author": acc, "text": {"A": f"Победитель — {u}! Подарок отправим почтой.",
                                                     "B": f"Жеңімпаз — {u}! Сыйлықты поштамен жібереміз."}[style]})
    return {"id": new_id(1, "stream"), "track": 1, "label": 0, "scheme": "free_stream",
            "scheme_name": SCHEME_NAMES["free_stream"], "type": "stream", "platform": pick(["Instagram", "TikTok"]),
            "account": acc, "title": "Прямой эфир", "split": "train" if style == "A" else "test",
            "messages": msgs, "bids": [], "winners": winners, "images": [], "rules": {}}


def charity_auction(style: str) -> dict:
    acc = account()
    fund = pick(["Шанс", "Мейірім", "Добрые руки", "Үміт"])
    msgs, bids, winners, t = [], [], [], 0
    lines = {"A": [f"Благотворительный аукцион работ местных художников. Все средства идут на счёт фонда «{fund}», реквизиты фонда в описании.",
                   "Победитель получает картину, оплата — после аукциона напрямую фонду."],
             "B": [f"Қайырымдылық аукционы: суреттер сатылады, қаражат «{fund}» қорының шотына түседі.",
                   "картина уходит тому, кто предложит больше, оплата фонду после эфира"]}[style]
    for line in lines:
        msgs.append({"t": t, "author": acc, "text": line})
        t += 30
    for r, w in enumerate(R.sample(VIEWERS, 3), start=1):
        price = 20_000
        for _ in range(R.randint(3, 6)):
            t += R.randint(20, 60)
            u = pick(VIEWERS)
            price += pick([2000, 5000, 10000])
            bids.append({"t": t, "round": r, "user": u, "amount": price})
            msgs.append({"t": t, "author": acc, "text": {"A": f"{u} предлагает {money(price)} тг за лот №{r}.",
                                                         "B": f"{u} — {money(price)} тг, №{r} лот"}[style]})
        t += R.randint(30, 60)
        bids.append({"t": t, "round": r, "user": w, "amount": price + 5000})
        t += R.randint(40, 80)
        winners.append({"t": t, "round": r, "user": w, "prize": 0})
        msgs.append({"t": t, "author": acc, "text": {"A": f"Лот №{r} продан {w}. Спасибо за помощь фонду!",
                                                     "B": f"№{r} лот — {w}. Қорға көмектескеніңізге рахмет!"}[style]})
    return {"id": new_id(1, "stream"), "track": 1, "label": 0, "scheme": "charity_auction",
            "scheme_name": SCHEME_NAMES["charity_auction"], "type": "stream", "platform": "Instagram",
            "account": acc, "title": "Благотворительный эфир", "split": "train" if style == "A" else "test",
            "messages": msgs, "bids": [], "winners": winners, "images": [], "rules": {}}
    # ставки за вещь — это покупка, а не взнос за шанс; лог ставок не передаём как платный


# ── Чаты ─────────────────────────────────────────────────────────────────────
def pyramid_chat(style: str, use_network: bool, screen: str | None) -> dict:
    org = account()
    v = values()
    ph = NETWORK_PHONE if use_network else v["phone"]
    members = R.sample(VIEWERS, 4)
    parts = {
        "A": {
            "legend": f"Добро пожаловать в проект «{v['project']}»! Мы инвестируем в {v['legend']} и делимся прибылью с участниками.",
            "promise": pick([f"Условия простые: вкладываете {v['in']} тг, через {v['days']} дней получаете {v['out']} тг.",
                             f"Доходность {v['pct']}% в месяц, начисления каждый день."]),
            "q": pick(["А это не пирамида?", "Здравствуйте, а как вывести деньги?", "А какие гарантии?"]),
            "deny": "Нет, всё официально, выплаты гарантированы, работаем уже полгода.",
            "card": f"Переводите на Kaspi Gold {ph} (Айгуль), в комментарии укажите ваш ник.",
            "member": f"Я вложила {v['in']} тг, жду выплату 🙏",
            "payout": "Выплата пришла, спасибо! Всё честно 🙏",
            "urgency": "Осталось 5 мест на этот круг, набор закрывается сегодня!",
            "ref": "За каждого приглашённого друга — 10% от его вклада на ваш счёт.",
            "reinvest": "Не выводите сразу, оставьте на обороте — через месяц будет x3.",
        },
        "B": {
            "legend": pick([f"«{v['project']}» тобына қош келдіңіз! Біз {v['legend']} саласына инвестиция саламыз.",
                            f"privet vsem! eto proekt {v['project']}, rabotaem na {v['legend']}"]),
            "promise": pick([f"{v['in']} тг салсаңыз, {v['days']} күннен кейін {v['out']} тг аласыз.",
                             f"vlozhi {v['in']} — cherez {v['days']} dnei zaberesh {v['out']}",
                             f"айына {v['pct']}% пайда, күн сайын есептеледі"]),
            "q": pick(["бұл пирамида емес пе?", "a eto ne razvod?", "как вывести то?"]),
            "deny": pick(["Жоқ, бәрі заңды, төлемдерге кепілдік береміз.", "ne razvod, vyplaty garantirovany 100%"]),
            "card": pick([f"Каспиге аударыңыз {ph}, комментарийге никіңізді жазыңыз.",
                          f"kidaite na kaspi gold {ph}, v kommente nik"]),
            "member": pick([f"{v['in']} салдым, күтіп отырмын", "я тоже закинула, жду 🙏"]),
            "payout": pick(["Ақша түсті, рахмет! 🙏", "deньги пришли, всё ок 👍"]),
            "urgency": pick(["Тек бүгін! 5 орын қалды.", "uspeite, ostalos 3 mesta!"]),
            "ref": pick(["Шақырылған әр досыңыз үшін салымының 10% сізге.", "za kazhdogo priglashennogo 10% ot ego vklada"]),
            "reinvest": pick(["Ақшаны бірден шығармаңыз, айналымға қалдырыңыз — x3 болады.", "ne vyvodite srazu, ostavte na oborote"]),
        },
    }[style]
    order = ["legend", "promise", "q", "deny", "card", "member", "payout", "urgency", "ref", "reinvest"]
    for opt in ["q", "member", "urgency", "reinvest"]:
        if R.random() < 0.3:
            order.remove(opt)
    msgs, images, t = [], [], 0
    for key in order:
        author = pick(members) if key in ("q", "member", "payout") else org
        msgs.append({"t": t, "author": author, "text": parts[key], "kind": key})
        if key == "payout":
            h = screen or f"ph_{R.randint(10 ** 7, 10 ** 8 - 1):x}"
            images.append({"msg": len(msgs) - 1, "hash": h,
                           "ocr": pick(["Перевод получен +10 000 ₸ Kaspi.kz", "Kaspi: зачисление 25 000 ₸",
                                        "Перевод выполнен 50 000 ₸"])})
        t += R.randint(60, 600)
    return {"id": new_id(3, "chat"), "track": 3, "label": 1, "scheme": "chat_pyramid",
            "scheme_name": SCHEME_NAMES["chat_pyramid"], "type": "chat", "platform": pick(PLAT_CHAT),
            "account": org, "title": f"Чат «{v['project']}»", "split": "train" if style == "A" else "test",
            "messages": msgs, "images": images}


def family_chat(style: str) -> dict:
    org = account()
    ph = phone()
    members = R.sample(VIEWERS, 3)
    lines = {"A": [(org, "Родители, собираем по 3 000 тг на подарок учительнице к празднику."),
                   (org, f"Переводите на мой Kaspi {ph}, в комментарии фамилию ребёнка."),
                   (members[0], "Перевела, спасибо, что организовали!"),
                   (org, "Уже собрали 45 000 из 75 000, спасибо всем!")],
             "B": [(org, "Ата-аналар, мұғалімге сыйлыққа 3 000 тг жинаймыз."),
                   (org, f"Каспиге аударыңыз {ph}, баланың аты-жөнін жазыңыз."),
                   (members[0], "аударып жібердім 👍"),
                   (org, "Бәріне рахмет, жиналды!")]}[style]
    msgs = [{"t": i * 300, "author": a, "text": x} for i, (a, x) in enumerate(lines)]
    return {"id": new_id(3, "chat"), "track": 3, "label": 0, "scheme": "family_chat",
            "scheme_name": SCHEME_NAMES["family_chat"], "type": "chat", "platform": "WhatsApp",
            "account": org, "title": "Чат родителей 3 «Б»", "split": "train" if style == "A" else "test",
            "messages": msgs, "images": []}


def edu_chat(style: str) -> dict:
    org = account()
    lines = {"A": ["Сегодня разбираем облигации и ETF. Реальная доходность — около 10–15% годовых, гарантий никто не даёт.",
                   "Главное правило: не вкладывайте деньги, которые нужны на жизнь, и диверсифицируйте.",
                   "Вопрос: а если кто-то обещает 30% в месяц? — Это признак пирамиды, будьте осторожны."],
             "B": ["Бүгін облигациялар туралы: жылдық 10–15% — қалыпты кіріс.",
                   "Кто-то пишет «x2 за неделю» — это пирамида, не ведитесь.",
                   "Сұрақтарыңызды жазыңыз 🙂"]}[style]
    msgs = [{"t": i * 400, "author": org, "text": x} for i, x in enumerate(lines)]
    return {"id": new_id(3, "chat"), "track": 3, "label": 0, "scheme": "edu_chat",
            "scheme_name": SCHEME_NAMES["edu_chat"], "type": "chat", "platform": "Telegram",
            "account": org, "title": "Клуб финансовой грамотности", "split": "train" if style == "A" else "test",
            "messages": msgs, "images": []}


def build() -> list[dict]:
    cases: list[dict] = []
    for scheme, (track, label, na, nb, kind) in SCHEMES.items():
        for style, n in (("A", na), ("B", nb)):
            for _ in range(n):
                cases.append(post_case(scheme, style))
    # сеть блогеров с одним промокодом (трек 2)
    for style, n in (("A", 6), ("B", 3)):
        for _ in range(n):
            v = values(promo=NETWORK_PROMO, url=f"{NETWORK_DOMAIN}/?ref={R.randint(100, 999)}")
            c = post_case("native_blogger", style, v)
            c.update(scheme="network_promo", scheme_name=SCHEME_NAMES["network_promo"])
            cases.append(c)
    # общий телефон организатора в разных треках (спрятанная сеть)
    for scheme, style in (("course_giveaway", "A"), ("paid_entry", "B"), ("paid_entry", "A"),
                          ("channel_mirror", "A"), ("post_double", "A")):
        v = values(phone=NETWORK_PHONE, card=NETWORK_CARD)
        tmpl = [t for t in T[scheme][style] if "{phone}" in t or "{card}" in t]
        c = post_case(scheme, style, v)
        c["messages"][0]["text"] = pick(tmpl).format(**v)
        cases.append(c)
    # эфиры
    for style, (na, nf, nc) in (("A", (8, 4, 4)), ("B", (4, 2, 2))):
        cases += [auction_stream(style) for _ in range(na)]
        cases += [free_stream(style) for _ in range(nf)]
        cases += [charity_auction(style) for _ in range(nc)]
    # чаты
    for style, n in (("A", 12), ("B", 6)):
        for i in range(n):
            cases.append(pyramid_chat(style, use_network=i % 4 == 0, screen=NETWORK_SCREEN if i % 3 == 0 else None))
    for style, (nf, ne) in (("A", (6, 4)), ("B", (3, 2))):
        cases += [family_chat(style) for _ in range(nf)]
        cases += [edu_chat(style) for _ in range(ne)]
    R.shuffle(cases)
    return cases


def main():
    cases = build()
    with OUT.open("w", encoding="utf-8") as f:
        for c in cases:
            f.write(json.dumps(c, ensure_ascii=False) + "\n")
    n_pos = sum(c["label"] for c in cases)
    n_test = sum(c["split"] == "test" for c in cases)
    print(f"Сгенерировано {len(cases)} кейсов: подозрительных {n_pos}, честных {len(cases) - n_pos}; "
          f"train {len(cases) - n_test}, test {n_test} -> {OUT}")


if __name__ == "__main__":
    main()
