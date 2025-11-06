# Contributing to zbxtg

Спасибо за интерес к улучшению zbxtg! Мы приветствуем вклад от сообщества.

## Как внести вклад

### Reporting Bugs

Если вы нашли баг, пожалуйста создайте Issue с:
- Четким описанием проблемы
- Шагами для воспроизведения
- Ожидаемым и фактическим поведением
- Версией zbxtg, Python, OS
- Логами (если применимо)

### Suggesting Enhancements

Предложения по улучшению приветствуются! Создайте Issue с:
- Четким описанием предложения
- Обоснованием необходимости
- Примерами использования
- Возможной реализацией (опционально)

### Pull Requests

1. **Fork репозиторий**

```bash
git clone https://github.com/GezzyDax/zbxtg.git
cd zbxtg
```

2. **Создайте ветку**

```bash
git checkout -b feature/amazing-feature
```

3. **Настройте dev окружение**

```bash
make dev
# или
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install -r requirements-dev.txt
pre-commit install
```

4. **Внесите изменения**

Следуйте стилю кода проекта:
- Используйте black для форматирования
- Следуйте PEP 8
- Добавьте docstrings для новых функций
- Добавьте type hints где возможно

5. **Добавьте тесты**

```bash
# Создайте тесты для новой функциональности
pytest tests/test_your_feature.py

# Убедитесь что все тесты проходят
make test

# Проверьте покрытие
make test-coverage
```

6. **Проверьте код**

```bash
# Запустите все проверки
make lint

# Или по отдельности
black .
isort .
ruff check .
mypy .
bandit -r . -c pyproject.toml
```

7. **Запустите pre-commit хуки**

```bash
pre-commit run --all-files
```

8. **Commit изменений**

Используйте [Conventional Commits](https://www.conventionalcommits.org/):

```bash
git commit -m "feat: add amazing feature"
git commit -m "fix: resolve issue with alerts"
git commit -m "docs: update README"
```

Типы:
- `feat`: Новая функциональность
- `fix`: Исправление бага
- `docs`: Изменения в документации
- `style`: Форматирование кода
- `refactor`: Рефакторинг
- `test`: Добавление тестов
- `chore`: Рутинные задачи

9. **Push и создайте PR**

```bash
git push origin feature/amazing-feature
```

Затем создайте Pull Request на GitHub.

## Стиль кода

### Python

- Следуйте [PEP 8](https://pep8.org/)
- Используйте type hints
- Максимальная длина строки: 100 символов
- Используйте docstrings в Google style

Пример:

```python
def get_problems(self, limit: int = 100, only_active: bool = True) -> List[Dict[str, Any]]:
    """Получает список проблем из Zabbix.

    Args:
        limit: Максимальное количество проблем для получения
        only_active: Получать только активные проблемы

    Returns:
        Список словарей с информацией о проблемах

    Raises:
        ZabbixAPIError: При ошибке API запроса

    Example:
        >>> client = ZabbixClient(config)
        >>> problems = client.get_problems(limit=10)
        >>> len(problems)
        5
    """
    # Implementation
    pass
```

### Commits

- Пишите осмысленные сообщения
- Используйте present tense ("add feature" не "added feature")
- Используйте imperative mood ("move cursor to..." не "moves cursor to...")
- Ограничьте первую строку 72 символами
- Ссылайтесь на issues и PRs

### Tests

- Покрытие новой функциональности тестами обязательно
- Используйте descriptive test names
- Следуйте паттерну Arrange-Act-Assert
- Используйте fixtures где возможно

Пример:

```python
def test_should_send_alert_severity_filter(self, app_config, mock_problem_details):
    """Test alert filtering by severity."""
    # Arrange
    mock_zabbix = MagicMock()
    mock_telegram = MagicMock()
    monitor = AlertMonitor(app_config, mock_zabbix, mock_telegram)

    # Act
    result = monitor._should_send_alert(mock_problem_details)

    # Assert
    assert result is True
```

## Процесс review

1. CI/CD пайплайн должен пройти успешно
2. Код должен быть одобрен минимум одним maintainer
3. Все комментарии должны быть разрешены
4. Покрытие тестами не должно снижаться

## Лицензия

Внося вклад в проект, вы соглашаетесь что ваш код будет лицензирован под MIT License.

## Вопросы?

Не стесняйтесь задавать вопросы в Issues или Discussions!
