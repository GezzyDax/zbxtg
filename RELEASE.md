# Руководство по созданию релизов

Этот документ описывает процесс создания новых релизов для Zabbix Telegram Bot.

## Версионирование

Проект использует [Semantic Versioning](https://semver.org/lang/ru/) (SemVer):

- **MAJOR** (первая цифра): несовместимые изменения API
- **MINOR** (вторая цифра): новая функциональность с обратной совместимостью
- **PATCH** (третья цифра): исправления ошибок с обратной совместимостью

Примеры:
- `2.0.0` → `2.0.1` - исправление ошибок
- `2.0.1` → `2.1.0` - новая функциональность
- `2.1.0` → `3.0.0` - breaking changes

## Процесс создания релиза

### Способ 1: Автоматический (через GitHub Actions)

1. **Обновите версию в файле VERSION:**
   ```bash
   echo "2.1.0" > VERSION
   git add VERSION
   git commit -m "chore: bump version to 2.1.0"
   git push origin main
   ```

2. **Создайте и отправьте тег:**
   ```bash
   git tag -a v2.1.0 -m "Release v2.1.0"
   git push origin v2.1.0
   ```

3. **Автоматика сработает:**
   - GitHub Actions автоматически создаст релиз
   - Сгенерирует changelog из коммитов
   - Создаст архив с исходниками
   - Соберет и опубликует Docker образ (если настроено)

### Способ 2: Ручной релиз через GitHub UI

1. **Обновите версию:**
   ```bash
   echo "2.1.0" > VERSION
   git add VERSION
   git commit -m "chore: bump version to 2.1.0"
   git push
   ```

2. **Создайте релиз на GitHub:**
   - Перейдите на страницу [Releases](https://github.com/GezzyDax/zbxtg/releases)
   - Нажмите "Draft a new release"
   - Создайте новый тег: `v2.1.0`
   - Заполните описание релиза
   - Нажмите "Publish release"

### Способ 3: Через GitHub Actions вручную

1. Перейдите в раздел [Actions](https://github.com/GezzyDax/zbxtg/actions)
2. Выберите workflow "Create Release"
3. Нажмите "Run workflow"
4. Укажите версию (например: `2.1.0`)
5. Запустите workflow

## Чек-лист перед релизом

Перед созданием нового релиза убедитесь:

- [ ] Все тесты пройдены (`pytest`)
- [ ] Линтеры не выдают ошибок (`ruff check`, `mypy`)
- [ ] CHANGELOG.md обновлен с описанием изменений
- [ ] VERSION файл содержит правильную версию
- [ ] Docker образ собирается без ошибок
- [ ] Документация актуальна (README.md)
- [ ] Все issue, связанные с релизом, закрыты

## Структура changelog

При обновлении CHANGELOG.md следуйте формату:

```markdown
## [2.1.0] - 2024-11-07

### Added
- Новая функциональность A
- Новая функциональность B

### Changed
- Изменено поведение C
- Улучшено D

### Fixed
- Исправлена ошибка E
- Исправлена ошибка F

### Security
- Устранена уязвимость G

### Deprecated
- Функция H будет удалена в версии 3.0.0
```

## Откат релиза

Если обнаружена критическая ошибка в релизе:

1. **Удалите тег локально и удаленно:**
   ```bash
   git tag -d v2.1.0
   git push --delete origin v2.1.0
   ```

2. **Удалите релиз на GitHub:**
   - Перейдите на страницу релиза
   - Нажмите "Delete this release"

3. **Создайте hotfix:**
   ```bash
   # Исправьте проблему
   echo "2.1.1" > VERSION
   git add .
   git commit -m "fix: critical bug in 2.1.0"
   git push

   # Создайте новый релиз
   git tag -a v2.1.1 -m "Hotfix release v2.1.1"
   git push origin v2.1.1
   ```

## Hotfix релизы

Для срочных исправлений:

1. Создайте hotfix ветку от последнего релиза:
   ```bash
   git checkout -b hotfix/2.0.1 v2.0.0
   ```

2. Внесите исправления:
   ```bash
   # Исправьте баг
   echo "2.0.1" > VERSION
   git add .
   git commit -m "fix: critical security issue"
   ```

3. Слейте в main:
   ```bash
   git checkout main
   git merge --no-ff hotfix/2.0.1
   git push
   ```

4. Создайте тег:
   ```bash
   git tag -a v2.0.1 -m "Hotfix v2.0.1"
   git push origin v2.0.1
   ```

## Docker публикация

### Типы образов

#### Production образы (релизы)
При создании тега `v*.*.*` автоматически публикуются образы в **GitHub Container Registry (GHCR)**:
- `ghcr.io/gezzydax/zbxtg:latest` - всегда указывает на последний релиз
- `ghcr.io/gezzydax/zbxtg:X.Y.Z` - конкретная версия (например, `1.0.0`)

#### Development образы
При push в ветку `main` или `master` автоматически публикуются:
- `ghcr.io/gezzydax/zbxtg:dev` - последняя версия из main/master
- `ghcr.io/gezzydax/zbxtg:main` или `ghcr.io/gezzydax/zbxtg:master` - версия из конкретной ветки

### Использование образов

**Production (рекомендуется):**
```yaml
# docker-compose.yml
services:
  zbxtg:
    image: ghcr.io/gezzydax/zbxtg:1.0.0  # Конкретная версия
```

**Development:**
```yaml
services:
  zbxtg:
    image: ghcr.io/gezzydax/zbxtg:dev
```

**Latest (не рекомендуется для production):**
```yaml
services:
  zbxtg:
    image: ghcr.io/gezzydax/zbxtg:latest
```

### Доступ к образам

Образы публикуются в GitHub Container Registry. Для публичного доступа:

1. Откройте [Packages](https://github.com/orgs/GezzyDax/packages?repo_name=zbxtg)
2. Выберите пакет `zbxtg`
3. Перейдите в **Package settings**
4. Измените видимость на **Public**

Для приватных образов нужна авторизация:
```bash
echo "YOUR_GITHUB_TOKEN" | docker login ghcr.io -u YOUR_GITHUB_USERNAME --password-stdin
docker pull ghcr.io/gezzydax/zbxtg:latest
```

### Локальная сборка

Для разработки можно собирать образ локально:
```yaml
# docker-compose.yml
services:
  zbxtg:
    build:
      context: .
      dockerfile: Dockerfile
```

**Требования:**
- Для публикации используется `GITHUB_TOKEN` (автоматически доступен в GitHub Actions)
- Не требуются дополнительные secrets для GHCR

## Примеры сообщений коммитов

Используйте [Conventional Commits](https://www.conventionalcommits.org/):

- `feat: добавить поддержку фильтров алертов` - новая функциональность
- `fix: исправить утечку памяти в мониторе` - исправление бага
- `docs: обновить README с инструкциями` - обновление документации
- `chore: обновить зависимости` - технические изменения
- `refactor: переписать модуль конфигурации` - рефакторинг
- `test: добавить тесты для фильтров` - добавление тестов
- `perf: оптимизировать запросы к API` - улучшение производительности

## Поддержка версий

- **Текущая stable версия** (2.x.x): полная поддержка, исправления багов
- **Предыдущая major версия** (1.x.x): только критические исправления безопасности
- **Старые версии** (<1.0.0): не поддерживаются

## Контакты

Вопросы по релизам:
- GitHub Issues: https://github.com/GezzyDax/zbxtg/issues
- Maintainer: @GezzyDax
