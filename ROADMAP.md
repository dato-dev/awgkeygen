# Roadmap

План развития AWG Keygen Bot. Задачи сгруппированы по темам; внутри каждой —
цель, объём работ и критерии готовности (DoD). Отметки статуса:

- ✅ сделано
- 🚧 в работе
- ⬜ запланировано

> Текущая версия: см. [`VERSION`](VERSION). CI публикует образ в Docker Hub
> (`dato1/awgkeygen`) при каждом push в `main` — см.
> [`.github/workflows/docker-publish.yml`](.github/workflows/docker-publish.yml).

---

## 1. Локализация (i18n) ⬜

**Цель:** поддержать английский язык наряду с русским, выбор — через `.env`.

- Ввести переменную окружения `BOT_LANG` (`ru` | `en`, по умолчанию `ru`) и
  пробросить её в `Settings` ([`bot/config.py`](bot/config.py)).
- Вынести все строки из [`bot/texts.py`](bot/texts.py) в словари переводов
  (`bot/locales/ru.py`, `bot/locales/en.py` или `.ftl`/`.po`). Рассмотреть
  `aiogram`-совместимый i18n (`gettext` / `fluent`) либо лёгкий собственный
  резолвер `t(key, **kwargs)`.
- Сохранить HTML-разметку и плейсхолдеры (`{ip}`, `{label}` и т.п.) в каждом
  переводе.
- Перевести меню команд (`set_my_commands` в [`bot/main.py`](bot/main.py)) под
  выбранный язык.

**DoD:** при `BOT_LANG=en` все сообщения пользователя и админа на английском;
при отсутствии перевода — фолбэк на ключ/русский без падения. Переменная
задокументирована в `.env.example` и README.

**Возможное развитие:** per-user язык (хранить в БД, определять по
`message.from_user.language_code`) — вне рамок первой итерации.

---

## 2. Автоматическая сборка и публикация Docker-образа ✅

**Цель:** при пуше в `main`/теге `v*` образ собирается и публикуется в registry.

Реализовано в [`docker-publish.yml`](.github/workflows/docker-publish.yml):
сборка через buildx, теги `latest` + версия из `VERSION` + `sha-<commit>`,
GHA-кэш, push в Docker Hub. Доставка на сервер — Watchtower / `docker-watchdog.sh`.

**Возможные улучшения:** multi-arch (`linux/arm64`) для ARM-серверов,
сканирование образа (Trivy/Grype), запуск тестов как gate перед публикацией.

---

## 3. Релизы и changelog (release-please) ✅

**Цель:** автоматизировать версионирование и генерацию `CHANGELOG.md`.

Реализовано:
- [`.github/workflows/release-please.yml`](.github/workflows/release-please.yml)
  — `googleapis/release-please-action@v4`, manifest-режим.
- [`release-please-config.json`](release-please-config.json) — тип `simple`,
  `version-file: VERSION` (пишется плоской строкой через `DefaultUpdater`, без
  аннотаций — файл остаётся парситься как раньше), кастомные секции changelog.
- [`.release-please-manifest.json`](.release-please-manifest.json) — текущая
  версия (`1.3.8`).
- [`CHANGELOG.md`](CHANGELOG.md) + [`CONTRIBUTING.md`](CONTRIBUTING.md) с
  описанием [Conventional Commits](https://www.conventionalcommits.org/ru/).

Flow: коммиты `feat:`/`fix:` → release-please ведёт release-PR → мёрж бампит
`VERSION` + `CHANGELOG.md`, создаёт тег `vX.Y.Z` и GitHub Release.

**Связь со сборкой образа:** мёрж release-PR — это push в `main` с уже
обновлённым `VERSION`, поэтому [docker-publish](.github/workflows/docker-publish.yml)
публикует образ `:X.Y.Z` + `:latest` по push-в-main-пути. ⚠️ Сам тег `vX.Y.Z`,
созданный через `GITHUB_TOKEN`, **не триггерит** другой workflow (защита GitHub
от рекурсии), поэтому полагаемся именно на push-в-main; тег-триггер `v*`
остаётся для ручных тегов.

**DoD:** ✅ мёрж release-PR создаёт тег, Release с changelog и публикует образ с
версией; `VERSION` больше не правится вручную.

**Замечание:** существующие коммиты `Initial commit` не Conventional — первый
release-PR появится после первого `feat:`/`fix:`-коммита.

---

## 4. Бот обновления зависимостей ⬜

**Цель:** автоматические PR на обновление зависимостей.

- Настроить **Dependabot** (`.github/dependabot.yml`) для экосистем:
  - `pip` — [`requirements.txt`](requirements.txt);
  - `docker` — базовый образ в [`Dockerfile`](Dockerfile);
  - `github-actions` — версии экшенов в workflow.
- Задать расписание (например, weekly), лимит открытых PR, метки и группировку
  патч/минор обновлений в один PR.
- Альтернатива — Renovate (более гибкий) при необходимости.

**DoD:** Dependabot открывает PR на обновления; CI прогоняется на них; для
безопасных обновлений возможен auto-merge.

---

## 5. Качественный README 🚧

**Цель:** довести [`README.md`](README.md) до уровня публичного проекта.

Сделано: шапка с бейджами (сборка, релиз, pulls, Conventional Commits), список
возможностей, оглавление, полная таблица переменных `.env`, разделение Quick
Start / Production / разработка, раздел про релизы (release-please) со ссылкой
на `CHANGELOG.md`.

Осталось:
- Реальные скриншоты/GIF — каркас готов в [docs/screenshots/](docs/screenshots/README.md),
  блок в README закомментирован до подкладки PNG.
- `BOT_LANG` в таблицу переменных — после задачи 1 (i18n).
- (Опционально) схема архитектуры, лицензия/`LICENSE`.

**DoD:** README самодостаточен для запуска «с нуля», отражает все команды и
переменные, выглядит опрятно на GitHub.

---

## 6. Публикация образа в GHCR ✅

**Цель:** дублировать публикацию в `ghcr.io` помимо Docker Hub.

Реализовано в [`docker-publish.yml`](.github/workflows/docker-publish.yml):
- `permissions: packages: write` + второй `docker/login-action` для `ghcr.io`
  с автоматическим `GITHUB_TOKEN`.
- `images:` в `metadata-action` расширен до
  `ghcr.io/${{ github.repository_owner }}/awgkeygen` — один build пушит
  одинаковые теги (один digest) в оба реестра.
- [`docker-compose-prod.yml`](docker-compose-prod.yml) — GHCR закомментирован
  как альтернативный `image:`. Имя образа — `awgkeygen` (без суффикса `-bot`).
- README: раздел «Реестры образов» с обоими вариантами.

**Замечание:** GHCR-пакет публикуется публичным автоматически (проверено
анонимным pull) — ручной смены visibility не требуется.

**DoD:** ✅ один и тот же образ (один digest) в Docker Hub и GHCR; Watchtower
может тянуть из любого; README описывает оба варианта.

---

## 7. Переход на uv ✅

**Цель:** воспроизводимые сборки и быстрый менеджер зависимостей.

Реализовано:
- [`pyproject.toml`](pyproject.toml) (PEP 621) + [`uv.lock`](uv.lock) вместо
  `requirements.txt` (удалён). Режим приложения (`[tool.uv] package = false`).
- [`Dockerfile`](Dockerfile) — бинарь uv из `ghcr.io/astral-sh/uv`,
  `uv sync --frozen --no-dev`, кэш слоя зависимостей; `UV_PYTHON_DOWNLOADS=never`
  (используем Python базового образа). Сборка проверена локально.
- Версия в `pyproject.toml` синхронизируется release-please
  (`extra-files`, аннотация `# x-release-please-version`).
- README: раздел запуска без Docker переведён на `uv sync` / `uv run`.
- Dependabot (pip-экосистема) автоматически подхватывает `uv.lock`.

---

## Статус

| # | Задача | Статус |
|---|---|---|
| 2 | Docker-сборка и публикация | ✅ |
| 3 | release-please + changelog | ✅ |
| 4 | Dependabot | ✅ |
| 6 | Публикация в GHCR | ✅ |
| 7 | Переход на uv | ✅ |
| 5 | Качественный README | 🚧 (нужны скриншоты + `BOT_LANG`) |
| 1 | Локализация (i18n) | ⬜ |

Осталось: **1 (i18n)**, затем закрыть хвост **5** (`BOT_LANG` в таблицу
переменных).
