.PHONY: help install install-dev test lint format clean docker-build docker-run

help: ## Показать справку
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install: ## Установить production зависимости
	pip install -r requirements.txt

install-dev: ## Установить dev зависимости
	pip install -r requirements.txt
	pip install -r requirements-dev.txt
	pre-commit install

test: ## Запустить тесты
	pytest

test-coverage: ## Запустить тесты с coverage
	pytest --cov=. --cov-report=html --cov-report=term

lint: ## Проверить код линтерами
	black --check .
	isort --check-only .
	ruff check .
	mypy .
	bandit -r . -c pyproject.toml

format: ## Форматировать код
	black .
	isort .
	ruff check --fix .

security: ## Проверить безопасность зависимостей
	safety check
	bandit -r . -c pyproject.toml

pre-commit: ## Запустить pre-commit хуки
	pre-commit run --all-files

clean: ## Очистить временные файлы
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name ".coverage" -delete
	rm -rf htmlcov coverage.xml

docker-build: ## Собрать Docker образ
	docker-compose build

docker-run: ## Запустить в Docker
	docker-compose up -d

docker-logs: ## Показать логи Docker
	docker-compose logs -f

docker-stop: ## Остановить Docker контейнер
	docker-compose down

run: ## Запустить бота локально
	python main.py

dev: install-dev ## Настроить dev окружение
	@echo "Dev окружение готово! Используйте 'make help' для списка команд"
