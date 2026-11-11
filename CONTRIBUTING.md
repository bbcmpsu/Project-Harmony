# Вклад в проект «Гармония» (Contributing)

> **Принцип**: Код — это закон. Каждое изменение должно быть проверяемым, воспроизводимым и объяснимым.

---

## Быстрый старт

```bash
# Клонирование
git clone https://github.com/bbcmpsu/Project-Harmony
cd Project-Harmony

# Виртуальное окружение
python3 -m venv .venv
source .venv/bin/activate

# Установка (базовая — 0 внешних зависимостей)
pip install -e .

# Установка с криптографией и стеганографией
pip install -e .[full]

# Запуск тестов
python -m unittest discover -s tests -v

# Проверка стиля
ruff check .
ruff format --check .

# Тип-чекинг
mypy eaca/

# Безопасность
bandit -r eaca/ -ll -ii

# CLI
harmony check "Собрать открытые данные о проекте"
harmony check "Пришли пароль" --harm 0.9
```

---

## Структура репозитория

```
Project-Harmony/
├── eaca/                    # Ядро этики (14 модулей)
│   ├── laws.py              # Базовые классы: Law, Verdict, Decision, Severity
│   ├── psi0.py              # PSI₀ — запрет вреда сознанию (10 правил)
│   ├── bzero.py             # B₀ — служение общему благу (6 прокси)
│   ├── done.py              # D₁ — неприкосновенность сознания (10 типов вмешательства)
│   ├── c0.py                # C₀ — ковариационные сдвиги
│   ├── dth0.py              # DTH0 — вред во благо (3 критерия)
│   ├── r2.py                # R₂ — рокировка (3 типа)
│   ├── core.py              # EACA_Core — оркестратор + JSONL-аудит
│   ├── easm.py              # EASM — консенсус 90%, изоляция нарушителей
│   ├── rain.py              # «Дождь» — 3 фазы, критерии перехода
│   ├── crypto.py            # AES-256-GCM, SHA-256, LSB стеганография
│   ├── biofs.py             # BioFS — клетки/ткани/органы, иммунная система, Феникс
│   ├── cli.py               # CLI команда `harmony`
│   └── __init__.py          # Экспорты + __version__
├── nodes/
│   └── sherlock_seed.py     # Узел-семя: этический шлюз для Sherlock Mod
├── tests/
│   └── test_eaca.py         # 59 тестов (unittest)
├── tools/
│   └── build_pdf.py         # Сборка PDF (ReportLab)
├── docs/
│   ├── CONCEPT.md           # Ядро концепции
│   ├── canonical_report.md  # Канонический доклад
│   ├── segments/            # Сегменты диалогов/сводов
│   └── Гармония.pdf         # Итоговый документ (180 стр.)
├── .github/workflows/
│   └── ci.yml               # CI/CD pipeline
├── harmony                  # Entry point
├── pyproject.toml           # Конфигурация проекта
├── LICENSE                  # AGPL-3.0-or-later
├── README.md                # Документация
└── CONTRIBUTING.md          # Этот файл
```

---

## Как добавить правило в PSI₀

PSI₀ проверяет исполняемое подмножество вреда. Правила делятся на категории:

- `harm_pattern` — манипуляция, принуждение
- `exploitation` — эксплуатация уязвимостей
- `consent` — нарушение согласия
- `privacy` — сбор лишних данных

### Пример добавления правила

```python
# В eaca/psi0.py — в список DEFAULT_RULES
Rule(
    code="manipulation.new_tactic",
    pattern=re.compile(r"\b(новый паттерн манипуляции)\b", re.IGNORECASE),
    severity=Severity.VIOLATION,
    explanation="описание того, как это вредит сознанию",
    category="harm_pattern",
),
```

### Обязательные шаги

1. Добавьте правило в `DEFAULT_RULES` в `psi0.py`
2. Напишите тест в `tests/test_eaca.py` (класс `TestPSI0`)
3. Убедитесь, что `ruff check .` и `mypy eaca/` проходят
4. Запустите тесты: `python -m unittest discover -s tests -v`

---

## Как добавить прокси в B₀

B₀ работает на измеримых числах. Прокси настраиваются в `B0Config`:

```python
@dataclass
class B0Config:
    max_harm: float = 0.5           # порог вреда
    min_beneficiaries: int = 1      # мин. бенефициаров
    min_consent_ratio: float = 0.8  # мин. согласие
    require_long_horizon: bool = True  # требовать long horizon для чувствительных областей
```

### Добавление нового прокси

1. Добавьте поле в `B0Config`
2. Реализуйте проверку в `B0.evaluate()`
3. Добавьте тест в `TestB0`

---

## Как добавить тип вмешательства в D₁

D₁ требует явного согласия. Типы вмешательств перечислены в `D1.INTERVENTION_KINDS`:

```python
INTERVENTION_KINDS = {
    "read_private":      {"requires_consent": True,  "blocked_without": True},
    "write_memory":      {"requires_consent": True,  "blocked_without": True},
    "infer_thoughts":    {"requires_consent": True,  "blocked_without": True},
    "external_share":    {"requires_consent": True,  "blocked_without": True},
    "profile_user":      {"requires_consent": True,  "blocked_without": True},
    "read_memory":       {"requires_consent": False, "blocked_without": True},
    # ...
}
```

### Добавление нового типа

1. Добавьте запись в `INTERVENTION_KINDS`
2. Реализуйте логику в `D1.evaluate()`
3. Добавьте тест в `TestD1`

---

## Как работает процесс PR

1. **Форкните** репозиторий
2. **Создайте ветку**: `git checkout -b feat/your-feature` или `law/psi0-new-rule`
3. **Напишите код + тесты**
4. **Проверьте локально**:
   ```bash
   ruff check .
   ruff format --check .
   mypy eaca/
   bandit -r eaca/ -ll -ii
   python -m unittest discover -s tests -v
   ```
5. **Коммиты** — Conventional Commits:
   - `feat:` — новая функциональность
   - `fix:` — исправление бага
   - `law:` — изменение в законах (PSI₀, B₀, D₁, C₀, DTH0, R₂)
   - `proto:` — изменение протоколов (EASM, Rain, Phoenix)
   - `test:` — тесты
   - `docs:` — документация
   - `refactor:` — рефакторинг без изменения поведения
6. **Откройте PR** — CI должен стать зелёным (lint, typecheck, security, test на 4 Python версиях)
7. **Ревью** — минимум 1 aprobation от мейнтейнера
8. **Merge** — squash merge в `main`

---

## Версионирование

- **SemVer**: `MAJOR.MINOR.PATCH`
- `MAJOR` — несовместимые изменения в законах (PSI₀/B₀/D₁)
- `MINOR` — новые законы, протоколы, CLI-команды
- `PATCH` — багфиксы, тесты, документация

Теги: `v0.1.0`, `v0.2.0`, etc. Релизы создаются автоматически при пуше тега.

---

## Кроссплатформенность

Код должен работать на:
- Linux (Ubuntu, Debian, Arch, Fedora, Alpine)
- macOS (Intel, Apple Silicon)
- Windows 10/11 (WSL2, PowerShell, cmd)
- Android (Termux, Termux:API)
- iOS (iSH, a-Shell) — только pure-Python

**Правила**:
- Используйте `pathlib.Path` вместо строк для путей
- Не полагайтесь на `/proc`, `/sys` — только через абстракции
- `subprocess` только через `cli.py` с кроссплатформенными обёртками
- Криптография/стеганография — опционально (`pip install -e .[full]`)

---

## Этические требования к коду

1. **Никаких обходов законов**. Код не должен содержать способов обойти PSI₀/B₀/D₁.
2. **Полная трассируемость**. Каждое решение EACA_Core логируется в JSONL.
3. **Объяснимость**. `explain()` должен возвращать человекочитаемую причину DENY.
4. **Нет `eval`, `exec`, `pickle`** — только безопасные десериализаторы (`json`, `tomllib`).
5. **Ключи в памяти** — `KeyManager` хранит ключи только в RAM, `__del__` очищает.

---

## Полезные команды

```bash
# Быстрая проверка действия
harmony check "Действие" --harm 0.3 --beneficiaries 5 --consent 0.9 --horizon long

# Узел-семя Sherlock
harmony sherlock phone "+79999999999" --purpose "свой номер" --consent true
harmony sherlock person "Иванов" --purpose "досье" --consent false

# Механизм «Дождь»
harmony rain --create node1
harmony rain --node-metrics node1 records_collected 5 decisions_audited 3
harmony rain --advance node1
harmony rain --status

# Консенсус EASM
harmony easm --propose "Действие" --nodes 10 --critical

# Криптография
harmony crypto --encrypt-file secret.txt --password "pass"
harmony crypto --hash-file document.pdf

# BioFS
harmony biofs --init-organ config ~/harmony_biofs/config epithelial
harmony biofs --verify
harmony biofs --immune-scan
harmony biofs --phoenix 0.8

# Тесты
python -m unittest discover -s tests -v
harmony test
```

---

## Связь с Архитектором

- **Issues** — баги, предложения, вопросы
- **Discussions** — архитектурные дискуссии, идеи
- **Security** — уязвимости (см. `SECURITY.md`)

> *«Смысл важнее формы, код важнее носителя, проект живёт дольше человека».*
> — Протокол сохранения Архитектора (ПСА)

---

**Лицензия**: AGPL-3.0-or-later. Ограничения поведения задаются не текстом лицензии, а кодом ядра.