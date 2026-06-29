<div align="center">

# 🔑 AWG Keygen Bot

**Telegram-бот для выдачи и управления ключами AmneziaWG**

Заявки на доступ, выдача ключей в один тап, автономные ключи, статистика
трафика и рассылки — всё из чата Telegram.

[![Docker Publish](https://github.com/dato-dev/awgkeygen/actions/workflows/docker-publish.yml/badge.svg)](https://github.com/dato-dev/awgkeygen/actions/workflows/docker-publish.yml)
[![Release Please](https://github.com/dato-dev/awgkeygen/actions/workflows/release-please.yml/badge.svg)](https://github.com/dato-dev/awgkeygen/actions/workflows/release-please.yml)
[![Latest release](https://img.shields.io/github/v/release/dato-dev/awgkeygen?logo=github)](https://github.com/dato-dev/awgkeygen/releases)
[![Docker Hub](https://img.shields.io/docker/pulls/dato1/awgkeygen?logo=docker&label=pulls)](https://hub.docker.com/r/dato1/awgkeygen)
[![Conventional Commits](https://img.shields.io/badge/commits-conventional-fe5196?logo=conventionalcommits)](https://www.conventionalcommits.org/ru/)

</div>

---

## ✨ Возможности

- 📝 **Заявки на доступ** — пользователь жмёт `/start`, админ одобряет кнопкой
- 🚀 **Онбординг в один шаг** — `/onboard` одобряет и сразу выдаёт ключ
- 🔑 **Самообслуживание** — выдача ключа, перечеканка, повторная отправка конфига и QR
- 🎁 **Автономные ключи** — `/keygen` для тех, кто не может зайти в бота
- 📊 **Статистика трафика** — из `awg show`, по каждому peer
- 📢 **Рассылки** — всем одобренным или адресно, с вложениями
- 🔧 **Обслуживание** — починка PSK, удаление peer, отзыв доступа
- 🐳 **Docker-native** — управляет AWG через `docker exec`, автодеплой через Watchtower

## 📑 Содержание

- [Как это работает](#как-это-работает)
- [Скриншоты](#скриншоты)
- [Требования](#требования)
- [Быстрый старт (Docker)](#быстрый-старт-docker)
- [Переменные окружения](#переменные-окружения)
- [Продакшен: Docker Hub + Watchtower](#продакшен-docker-hub--watchtower)
- [Запуск без Docker](#запуск-без-docker-python--systemd)
- [Команды бота](#команды-бота)
- [Структура проекта](#структура-проекта)
- [Релизы и разработка](#релизы-и-разработка)
- [Troubleshooting](#troubleshooting)

---

## Как это работает

1. Пользователь пишет боту `/start` — отправляется заявка на доступ
2. Администратор получает уведомление с кнопками «Одобрить» / «Отклонить»
3. После одобрения пользователь может:
   - **Получить ключ** — один раз, создаёт peer на сервере
   - **Перечеканить ключ** — сгенерировать новую пару ключей (старый перестаёт работать)
   - **Показать конфиг** — повторно отправить текущий конфиг и QR-код

### Автономные ключи

Для тех, кто **не может зайти в бота** (заблокирован, нет Telegram и т.п.), администратор создаёт **автономный ключ** командой `/keygen <метка>`. Бот присылает конфиг и `.vpn`-файл прямо в чат админу — дальше его можно передать получателю любым способом. Такие ключи не привязаны к Telegram-аккаунту и хранятся только в конфиге сервера (peer `manual_<метка>`).

## Скриншоты

<!--
Положите PNG в docs/screenshots/ (см. docs/screenshots/README.md) и
раскомментируйте таблицу ниже.

| | |
|---|---|
| ![Заявка пользователя](docs/screenshots/user-start.png) | ![Уведомление админу](docs/screenshots/admin-request.png) |
| **Заявка отправлена** | **Уведомление админу с кнопками** |
| ![Выдача ключа](docs/screenshots/user-key.png) | ![Панель админа](docs/screenshots/admin-panel.png) |
| **Ключ пользователю** | **Панель администратора** |
| ![Автономный ключ](docs/screenshots/admin-keygen.png) | ![Трафик](docs/screenshots/admin-traffic.png) |
| **Автономный ключ `/keygen`** | **Статистика трафика** |
-->

> 📷 Скриншоты пока не добавлены — см. [docs/screenshots/](docs/screenshots/README.md),
> чтобы их подложить.

## Требования

- Сервер с Docker
- Запущенный контейнер AmneziaWG (`amnezia-awg2`)
- Telegram Bot Token от [@BotFather](https://t.me/BotFather)

---

## Быстрый старт (Docker)

Боту нужен доступ к Docker socket, чтобы выполнять `docker exec` в контейнер AWG. Самый простой способ — запустить бота тоже в Docker и пробросить `/var/run/docker.sock`.

### 1. Скопируйте проект на сервер

```bash
# На сервере, где уже работает amnezia-awg2
cd /opt
git clone https://github.com/dato-dev/awgkeygen.git
cd awgkeygen
```

### 2. Настройте `.env`

```bash
cp .env.example .env
nano .env
```

Минимально нужно задать `BOT_TOKEN`, `ADMIN_IDS` и `SERVER_ENDPOINT` —
полная таблица в разделе [Переменные окружения](#переменные-окружения).
Узнать свой Telegram ID: [@userinfobot](https://t.me/userinfobot).

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

Должно появиться: `AWG container 'amnezia-awg2' is reachable` и `Polling started`.

### Управление

```bash
docker compose restart        # перезапуск
docker compose down           # остановка
docker compose up -d --build  # обновление после git pull
```

---

## Переменные окружения

| Переменная | Обязательна | По умолчанию | Описание |
|---|:---:|---|---|
| `BOT_TOKEN` | ✅ | — | Токен Telegram-бота от [@BotFather](https://t.me/BotFather) |
| `ADMIN_IDS` | ✅ | — | Telegram ID администраторов через запятую |
| `SERVER_ENDPOINT` | ✅ | — | Публичный IP или домен сервера (для клиентского конфига) |
| `DOCKER_CONTAINER` | | `amnezia-awg2` | Имя Docker-контейнера AWG |
| `AWG_CONFIG_PATH` | | `/opt/amnezia/awg/awg0.conf` | Путь к серверному конфигу внутри контейнера |
| `AWG_PORT` | | из `awg0.conf` | UDP-порт AWG |
| `DNS_PRIMARY` | | `1.1.1.1` | Основной DNS для клиентов |
| `DNS_SECONDARY` | | `1.0.0.1` | Резервный DNS |
| `AWG_CONTAINER_TYPE` | | `amnezia-awg2` | Тип контейнера в `vpn://` URI |
| `VPN_DESCRIPTION` | | `AWG Server` | Название подключения в AmneziaVPN |
| `AWG_MTU` | | `1280` | MTU в `vpn://` URI |
| `DATABASE_PATH` | | `./data/bot.db` | Путь к SQLite-базе |
| `LOG_LEVEL` | | `INFO` | Уровень логов: `DEBUG` / `INFO` / `WARNING` |

---

## Продакшен: Docker Hub + Watchtower

На сервере используйте `docker-compose-prod.yml`. Образ всегда `dato1/awgkeygen:latest` — **версию в compose менять не нужно**.

### Реестры образов

Один и тот же образ (один digest) публикуется в **два реестра** — выбирайте любой:

| Реестр | Образ |
|---|---|
| Docker Hub | `dato1/awgkeygen` |
| GitHub Container Registry | `ghcr.io/dato-dev/awgkeygen` |

GHCR-пакет публичный — `docker pull` работает без логина. Для приватного
доступа: `echo $GITHUB_TOKEN | docker login ghcr.io -u <user> --password-stdin`.
Чтобы тянуть из GHCR, раскомментируйте соответствующую строку `image:` в
`docker-compose-prod.yml`.

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

### Без Watchtower (cron)

Если не хотите отдельный контейнер — закомментируйте сервис `watchtower` в compose и добавьте в cron:

```bash
# каждые 5 минут
*/5 * * * * DEPLOY_PATH=/opt/awgkeygen /opt/awgkeygen/scripts/docker-watchdog.sh >> /var/log/awgkeygen-watchdog.log 2>&1
```

Скрипт сравнивает digest образа на Hub и локально; при изменении делает `compose up -d`.

### Откат

```bash
docker compose -f docker-compose-prod.yml down
# в compose временно укажите конкретный тег: image: dato1/awgkeygen:1.3.8
docker compose -f docker-compose-prod.yml up -d
```

> Каждый релиз доступен отдельным тегом `dato1/awgkeygen:X.Y.Z` — удобно для отката.

---

## Запуск без Docker (Python + systemd)

Если не хотите контейнеризировать сам бот. Зависимости управляются через
[uv](https://docs.astral.sh/uv/) (`pyproject.toml` + `uv.lock`):

```bash
cd /opt/awgkeygen

# Установить uv (если ещё нет)
curl -LsSf https://astral.sh/uv/install.sh | sh

uv sync               # создаст .venv и поставит зависимости из uv.lock

cp .env.example .env
# Отредактируйте .env

uv run python -m bot.main
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
├── main.py              # Точка входа, регистрация команд
├── config.py            # Настройки из .env
├── database.py          # SQLite: пользователи и статусы
├── keyboards.py         # Inline-клавиатуры Telegram
├── middleware.py        # Логирование апдейтов
├── texts.py             # Тексты сообщений (HTML)
├── utils.py             # Генерация QR-кодов
├── version.py           # Версия из файла VERSION
├── awg/
│   ├── config_parser.py # Парсер awg0.conf
│   ├── manager.py       # Управление ключами через docker exec
│   ├── stats.py         # Парсинг awg show (трафик)
│   └── vpnuri.py        # Генерация vpn:// URI
├── handlers/
│   ├── user.py          # Хендлеры пользователей
│   └── admin.py         # Хендлеры администратора
└── services/
    ├── keys.py          # Доставка ключей и QR
    ├── admin_actions.py # Бизнес-логика админ-действий
    └── notify.py        # Рассылки и уведомления
```

## Релизы и разработка

Версионирование и `CHANGELOG.md` автоматизированы через
[release-please](https://github.com/googleapis/release-please) на основе
[Conventional Commits](https://www.conventionalcommits.org/ru/) — файл `VERSION`
вручную **не правится**. Подробнее в [CONTRIBUTING.md](CONTRIBUTING.md).

```
коммиты feat:/fix: в main → release-please открывает release-PR
        → мёрж PR бампит VERSION + CHANGELOG, создаёт тег vX.Y.Z и Release
        → сборка образа dato1/awgkeygen:X.Y.Z + :latest
```

Секреты для публикации образа (**Settings → Secrets → Actions**):
`DOCKERHUB_USERNAME` и `DOCKERHUB_TOKEN`.

История изменений — в [CHANGELOG.md](CHANGELOG.md). Планы — в [ROADMAP.md](ROADMAP.md).

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
ls -la /var/run/docker.sock                   # socket должен существовать
docker compose exec awgkeygen-bot docker ps   # тест изнутри бота
```
