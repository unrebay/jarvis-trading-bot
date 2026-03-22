# Skill: knowledge-ingestion

## Purpose
Принять сырой контент (Discord export, Notion, текст, PDF, видео-транскрипт) и сохранить его в `/knowledge/raw/` с правильным именованием.

## Trigger
- Новый файл от пользователя
- Команда: "загрузи", "добавь материал", "зайнджести"
- Новый Discord/Notion экспорт

## Input formats
- `.txt` — Discord exports
- `.md` — Notion / ручной контент
- `.pdf` — документы
- `.mp4 / .mov` — видео (для последующей транскрипции)
- `.png / .jpg` — скриншоты (для аннотаций)

## Steps

### 1. Validate
- Проверить формат
- Проверить, нет ли уже такого файла (dedup по имени и первым 100 символам)

### 2. Name
Формат имени файла:
```
{YYYY-MM-DD}_{source}_{topic}.{ext}
```
Примеры:
- `2026-03-22_discord_risk-management.txt`
- `2026-03-22_notion_tda-entry-models.md`
- `2026-03-22_manual_psychology-rules.md`

### 3. Save
- Сохранить в `/knowledge/raw/`
- Обновить `/system/progress/discord_state.json` (или создать новый state-файл)

### 4. Log
Добавить запись в `/system/progress/ingestion_log.json`:
```json
{
  "timestamp": "ISO datetime",
  "file": "имя файла",
  "source": "discord | notion | manual | web",
  "topic": "тема",
  "lines": number,
  "status": "raw"
}
```

### 5. Trigger structurer
После ingestion — запустить `knowledge-structurer` для обработки.

## Output
- Файл в `/knowledge/raw/`
- Запись в ingestion_log.json
