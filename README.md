# AWG Keygen Bot

Telegram-бот для выдачи ключей AmneziaWG. Работает с Docker-контейнером `amnezia-awg2` (или любым другим AWG-контейнером Amnezia).

## Как это работает

1. Пользователь пишет боту `/start` — отправляется заявка на доступ
2. Администратор получает уведомление с кнопками «Одобрить» / «Отклонить»
3. После одобрения пользователь может:
   - **Получить ключ** — один раз, создаёт peer на сервере
   - **Перечеканить ключ** — сгенерировать новую пару ключей (старый перестаёт работать)
   - **Показать конфиг** — повторно отправить текущий конфиг и QR-код

## Требования

- Сервер с Docker
- Запущенный контейнер AmneziaWG (`amnezia-awg2`)
- Telegram Bot Token от [@BotFather](https://t.me/BotFather)

---

## Запуск через Docker (рекомендуется)

Боту нужен доступ к Docker socket, чтобы выполнять `docker exec` в контейнер AWG. Самый простой способ — запустить бота тоже в Docker и пробросить `/var/run/docker.sock`.

### 1. Скопируйте проект на сервер

```bash
# На сервере, где уже работает amnezia-awg2
cd /opt
git clone <repo-url> awgkeygen
cd awgkeygen
```

### 2. Настройте `.env`

```bash
cp .env.example .env
nano .env
```

| Переменная | Описание |
|---|---|
| `BOT_TOKEN` | Токен Telegram-бота |
| `ADMIN_IDS` | Telegram ID администраторов через запятую |
| `DOCKER_CONTAINER` | Имя контейнера (по умолчанию `amnezia-awg2`) |
| `AWG_CONFIG_PATH` | Путь к `awg0.conf` внутри контейнера |
| `SERVER_ENDPOINT` | Публичный IP или домен сервера |
| `AWG_PORT` | UDP-порт (опционально, иначе из конфига) |

Узнать свой Telegram ID: [@userinfobot](https://t.me/userinfobot)

### 3. Проверьте, что AWG-контейнер запущен

```bash
docker ps | grep amnezia-awg2
```

### 4. Запустите бота

```bash
docker compose up -d --build
```

### 5. Проверьте логи

```bash
docker compose logs -f
```

Должно появиться: `Бот запущен. Контейнер: amnezia-awg2`

### Управление

```bash
docker compose restart      # перезапуск
docker compose down         # остановка
docker compose up -d --build  # обновление после git pull
```

---

## Запуск без Docker (Python + systemd)

Если не хотите контейнеризировать сам бот:

```bash
cd /opt/awgkeygen
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# Отредактируйте .env

python -m bot.main
```

### Автозапуск через systemd

```bash
sudo cp awgkeygen.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now awgkeygen
sudo systemctl status awgkeygen
```

---

## Команды бота

### Пользователь
| Команда | Описание |
|---|---|
| `/start` | Главное меню |
| `/help` | Справка и ссылки на AmneziaVPN |
| `/status` | Статус доступа и ключа |
| `/key` | Получить VPN-ключ |
| `/remint` | Перечеканить ключ |
| `/config` | Показать текущий конфиг |

### Администратор
| Команда | Описание |
|---|---|
| `/admin` | Панель администратора |
| `/pending` | Заявки на доступ |
| `/users` | Все пользователи |
| `/user <id>` | Карточка пользователя |
| `/approve <id>` | Одобрить |
| `/reject <id>` | Отклонить |
| `/revoke <id>` | Отозвать доступ |
| `/genkey <id>` | Выдать ключ пользователю |
| `/genkey <id> remint` | Перечеканить ключ |
| `/genkey <id> resend` | Повторно отправить конфиг |

## Структура проекта

```
bot/
├── main.py              # Точка входа
├── config.py            # Настройки из .env
├── database.py          # SQLite: пользователи и статусы
├── keyboards.py         # Клавиатуры Telegram
├── utils.py             # Генерация QR-кодов
├── awg/
│   ├── config_parser.py # Парсер awg0.conf
│   └── manager.py       # Управление ключами через docker exec
└── handlers/
    ├── user.py          # Хендлеры пользователей
    └── admin.py         # Хендлеры администратора
```

## Примечания

- Бот и `amnezia-awg2` должны работать на одном сервере (или бот должен иметь доступ к Docker socket этого сервера)
- Каждому пользователю соответствует peer `tg_<telegram_id>` в `awg0.conf`
- При перечеканке старый ключ немедленно перестаёт работать
- Конфиг и QR-код совместимы с [AmneziaWG клиентом](https://github.com/amnezia-vpn/amneziawg-android)

## Troubleshooting

**`Контейнер 'amnezia-awg2' не найден`**
```bash
docker ps -a | grep awg          # проверьте имя контейнера
# Если имя другое — поправьте DOCKER_CONTAINER в .env
```

**`Ошибка в контейнере: awg: not found`**
```bash
docker exec amnezia-awg2 awg --version   # awg должен быть внутри AWG-контейнера
```

**Бот не видит Docker (в Docker-режиме)**
```bash
ls -la /var/run/docker.sock          # socket должен существовать
docker compose exec awgkeygen-bot docker ps   # тест изнутри бота
```
