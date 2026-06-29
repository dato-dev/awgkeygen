# Contributing

## Conventional Commits

Проект использует [Conventional Commits](https://www.conventionalcommits.org/ru/)
— на их основе [release-please](https://github.com/googleapis/release-please)
автоматически считает версию и генерирует [CHANGELOG.md](CHANGELOG.md).

Формат сообщения коммита:

```
<тип>[(scope)][!]: краткое описание

[тело]

[footer]
```

### Типы и влияние на версию

| Тип | Назначение | Бамп версии | В changelog |
|---|---|---|---|
| `feat` | новая функциональность | **minor** (1.3.8 → 1.4.0) | ✨ Features |
| `fix` | исправление бага | **patch** (1.3.8 → 1.3.9) | 🐛 Bug Fixes |
| `perf` | оптимизация | patch | ⚡ Performance |
| `refactor` | рефакторинг без смены поведения | patch | ♻️ Refactoring |
| `docs` | документация | patch | 📝 Documentation |
| `build` | сборка / зависимости | patch | 📦 Build & Deps |
| `ci` | изменения в CI | patch | 👷 CI |
| `chore` | рутина (не релизится отдельно) | — | скрыто |
| `test` | тесты | — | скрыто |

**Ломающие изменения:** добавьте `!` после типа (`feat!:`) или строку
`BREAKING CHANGE:` в теле — это бампит **major** (1.x.x → 2.0.0).

### Примеры

```
feat: автономные ключи /keygen для выдачи вручную
fix(awg): не падать, если PSK-файл отсутствует
docs: описать GHCR в README
feat!: убрать legacy-формат конфига
```

## Как работает релиз

1. Коммиты с Conventional-сообщениями мёржатся в `main`.
2. [release-please](.github/workflows/release-please.yml) ведёт «release PR»:
   накапливает изменения, обновляет [`VERSION`](VERSION) и
   [`CHANGELOG.md`](CHANGELOG.md).
3. Мёрж release-PR создаёт git-тег `vX.Y.Z` и GitHub Release.
4. Бамп `VERSION` в `main` запускает
   [сборку Docker-образа](.github/workflows/docker-publish.yml) с новой версией
   (`dato1/awgkeygen:X.Y.Z` + `:latest`).

> `VERSION` **не нужно** править вручную — это делает release-please.
> Коммиты без Conventional-префикса в релиз/changelog не попадают.

## Локальный запуск

См. раздел «Запуск без Docker» в [README.md](README.md#запуск-без-docker-python--systemd).
