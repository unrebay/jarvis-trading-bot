# Skill: knowledge-structurer

## Purpose
Взять сырой файл из `/knowledge/raw/` и преобразовать его в структурированные объекты по схемам `lesson.json`, `rule.json`, `pattern.json`.

## Trigger
- После завершения ingestion
- Команда: "структурируй", "обработай raw", "разбери материал"
- Ручной запуск на конкретный файл

## Input
- Файл из `/knowledge/raw/*.txt` или `*.md`

## Steps

### 1. Parse
- Убрать Discord-мусор: временны́е метки, реакции `{Reactions}`, ссылки на embed, имена пользователей
- Извлечь чистый текст

### 2. Classify
Определить тип контента:
- Это урок/теория? → `lesson`
- Это правило/запрет? → `rule`
- Это паттерн с условиями входа? → `pattern`
- Это пример/кейс? → `example`

### 3. Extract
По каждому объекту заполнить поля из соответствующей схемы.

### 4. Save
- Уроки → `/knowledge/lessons/{topic}/lesson_{id}.json`
- Правила → `/knowledge/rules/rule_{id}.json`
- Паттерны → `/knowledge/patterns/pattern_{id}.json`
- Примеры → `/knowledge/examples/`

### 5. Update processed marker
Создать файл-маркер: `/knowledge/processed/{original_filename}.done`

## Naming convention
```
lesson_001.json
lesson_002.json
rule_001.json
pattern_001.json
```

## Output
- JSON-файлы по схемам
- Маркер обработки
- Лог в `/system/progress/structuring_log.json`
