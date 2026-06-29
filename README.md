# AWG Keygen Bot

Telegram-бот для выдачи ключей AmneziaWG. Работает с Docker-контейнером `amnezia-awg2` (или любым другим AWG-контейнером Amnezia).

## Как это работает

1. Пользователь пишет боту `/start` — отправляется заявка на доступ
2. Администратор получает уведомление с кнопками «Одобрить» / «Отклонить»
3. После одобрения пользователь может:
   - **Получить ключ** — один раз, создаёт peer на сервере
   - **Перечеканить ключ** — сгенерировать новую пару ключей (старый перестаёт работать)
   - **Показать конфиг** — повторно отправить текущий конфиг и QR-код

### Автономные ключи

Для тех, кто **не может зайти в бота** (заблокирован, нет Telegram и т.п.), администратор создаёт **автономный ключ** командой `/keygen <метка>`. Бот присылает конфиг и `.vpn`-файл прямо в чат админу — дальше его можно передать получателю любым способом. Такие ключи не привязаны к Telegram-аккаунту и хранятся только в конфиге сервера (peer `manual_<метка>`).

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

## Продакшен: Docker Hub + Watchtower

На сервере используйте `docker-compose-prod.yml`. Образ всегда `dato1/awgkeygen-bot:latest` — **версию в compose менять не нужно**.

### Как это работает

```
push в main → GitHub Actions публикует :latest в Docker Hub
                    ↓
Watchtower на сервере (каждые 5 мин) видит новый digest
                    ↓
docker pull + перезапуск awgkeygen-bot
```

Watchtower обновляет только контейнеры с label `watchtower.enable=true`. Контейнер `amnezia-awg2` не затрагивается.

### Запуск на сервере

```bash
cd /opt/awgkeygen
cp .env.example .env   # если ещё не настроен
docker compose -f docker-compose-prod.yml up -d
```

### Публикация образа (GitHub Actions)

В репозитории: **Settings → Secrets → Actions**

| Секрет | Описание |
|---|---|
| `DOCKERHUB_USERNAME` | `dato1` |
| `DOCKERHUB_TOKEN` | Access Token Docker Hub |

**Релиз (автоматический):** версия и `CHANGELOG.md` ведутся через
[release-please](https://github.com/googleapis/release-please) на основе
[Conventional Commits](https://www.conventionalcommits.org/ru/) — `VERSION`
вручную **не правится**. Подробнее: [CONTRIBUTING.md](CONTRIBUTING.md).
Коротко: коммиты `feat:`/`fix:` в `main` → release-please открывает release-PR →
мёрж PR бампит `VERSION`, обновляет changelog, создаёт тег `vX.Y.Z` и Release →
сборка образа с новой версией.

GitHub Actions соберёт образ **один раз** и запушит **два тега с одинаковым содержимым**:
- `dato1/awgkeygen-bot:1.0.1` (из `VERSION`)
- `dato1/awgkeygen-bot:latest`

Watchtower на сервере следит за `latest`. Версию `x.y.z` можно использовать для отката.

Альтернатива — git-тег: `git tag v1.0.1 && git push origin v1.0.1` (создаст теги `1.0.1` + `latest`).

**Локально** (без двойной сборки):

```bash
docker build -t dato1/awgkeygen-bot:1.0.1 -t dato1/awgkeygen-bot:latest .
docker push dato1/awgkeygen-bot:1.0.1
docker push dato1/awgkeygen-bot:latest
```

После `push` первого тега можно не пересобирать, а только перетегировать:

```bash
docker tag dato1/awgkeygen-bot:1.0.1 dato1/awgkeygen-bot:latest
docker push dato1/awgkeygen-bot:latest
```

### Без Watchtower (cron)

Если не хотите отдельный контейнер — закомментируйте сервис `watchtower` в compose и добавьте в cron:

```bash
# каждые 5 минут
*/5 * * * * DEPLOY_PATH=/opt/awgkeygen /opt/awgkeygen/scripts/docker-watchdog.sh >> /var/log/awgkeygen-watchdog.log 2>&1
```

Скрипт сравнивает digest образа на Hub и локально; при изменении делает `compose up -d`.

### Откат

```bash
# временно зафиксировать старый образ
docker compose -f docker-compose-prod.yml down
# в compose: image: dato1/awgkeygen-bot:sha-abc1234
docker compose -f docker-compose-prod.yml up -d
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
| `/onboard <id>` | **Одобрить + выдать ключ** (одной командой) |
| `/pending` | Заявки на доступ |
| `/users` | Все пользователи |
| `/user <id>` | Карточка + трафик + кнопки копирования |
| `/traffic` | Трафик всех peers (из `awg show`) |
| `/traffic <id>` | Трафик конкретного пользователя |
| `/approve <id>` | Одобрить |
| `/reject <id>` | Отклонить |
| `/revoke <id>` | Отозвать доступ |
| `/genkey <id>` | Выдать ключ |
| `/genkey <id> remint` | Перечеканить |
| `/delkey <id>` | Удалить ключ с сервера |
| `/repair <id>` | Починить PSK на сервере |
| `/keygen <метка>` | **Автономный ключ** для выдачи вручную (метка опциональна) |
| `/keys` | Список автономных ключей |
| `/keydel <метка>` | Удалить автономный ключ |
| `/notify_user <id> текст` | Уведомление одному пользователю (можно с файлом) |
| `/notify_all текст` | Рассылка всем одобренным (можно с файлом) |

Уведомления о новых заявках содержат **кнопки** — в том числе «📋 /onboard» для копирования команды в буфер.

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
- Автономным ключам (`/keygen`) соответствует peer `manual_<метка>` — без привязки к Telegram-аккаунту
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
