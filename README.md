# solid-state_kinetics

[![.github/workflows/release.yml](https://github.com/kdavjd/solid-state_kinetics/actions/workflows/release.yml/badge.svg)](https://github.com/kdavjd/solid-state_kinetics/actions/workflows/release.yml)
[![.github/workflows/pre-commit.yml](https://github.com/kdavjd/solid-state_kinetics/actions/workflows/pre-commit.yml/badge.svg)](https://github.com/kdavjd/solid-state_kinetics/actions/workflows/pre-commit.yml)

---

## Setup dev environment

```bash
poetry env use python3.12 # В случае ошибки указать полный путь до интерпретатора вместо python3.12
poetry install
poetry run pre-commit install
```
## The entry point to the project
src.gui.__main__
or
```bash
poetry run ssk-gui
```

## Ruff documentation
```bash
poetry run ruff check . # Запуск линтера
poetry run ruff check . --statistics # Выводит небольшую сводку по ошибкам, если они есть
# =====================
poetry run ruff format . # Запуска форматирования
poetry run ruff format . --verbose # Выводит журнал действий
```

## Pre-commit documentation
```bash
poetry run pre-commit run --all-files # Запуск пре-коммита без коммита в git систему
```
