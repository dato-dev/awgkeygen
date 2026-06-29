# Roadmap

План развития AWG Keygen Bot. Задачи сгруппированы по темам; внутри каждой —
цель, объём работ и критерии готовности (DoD). Отметки статуса:

- ✅ сделано
- 🚧 в работе
- ⬜ запланировано

> Текущая версия: см. [`VERSION`](VERSION). CI публикует образ в Docker Hub
> (`dato1/awgkeygen-bot`) при каждом push в `main` — см.
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

## 5. Качественный README ⬜

**Цель:** довести [`README.md`](README.md) до уровня публичного проекта.

- Бейджи: версия/релиз, статус сборки, лицензия, pulls образа.
- Краткое «что это» + список возможностей с акцентом на свежие фичи
  (онбординг, автономные ключи `/keygen`, трафик, рассылки).
- Скриншоты/GIF работы бота, схема архитектуры (бот ↔ Docker ↔ AWG-контейнер).
- Чёткое разделение Quick Start / Production / разработка; таблица всех
  переменных `.env` (включая `BOT_LANG` из задачи 1).
- Раздел Contributing (Conventional Commits из задачи 3), ссылка на
  `CHANGELOG.md`, лицензия.

**DoD:** README самодостаточен для запуска «с нуля», отражает все команды и
переменные, выглядит опрятно на GitHub.

---

## 6. Публикация образа в GHCR ⬜

**Цель:** дублировать публикацию в `ghcr.io` помимо Docker Hub.

См. [docs: Container registry](https://docs.github.com/ru/packages/working-with-a-github-packages-registry/working-with-the-container-registry).

- В [`docker-publish.yml`](.github/workflows/docker-publish.yml) добавить
  второй `docker/login-action` для `ghcr.io` с `GITHUB_TOKEN`
  (`permissions: packages: write`).
- Расширить `images:` в `metadata-action` до
  `ghcr.io/<owner>/awgkeygen-bot` (один build → push в оба registry).
- Сделать пакет в GHCR публичным (или задокументировать `docker login ghcr.io`
  для приватного доступа); связать пакет с репозиторием.
- Обновить compose/документацию: указать GHCR как альтернативный источник
  образа.

**DoD:** один и тот же образ (один digest) доступен и в Docker Hub, и в GHCR;
Watchtower может тянуть из любого; README описывает оба варианта.

---

## Очерёдность

```
2 (готово) ──► 6 (GHCR)
              \
3 (release-please) ──► улучшает 2 (релизные образы)
4 (dependabot)         независимо
1 (i18n) ──► 5 (README с BOT_LANG)
```

Рекомендуемый порядок: **6 → 4 → 3 → 1 → 5** (5 закрывает хвосты остальных,
поэтому в самом конце).
