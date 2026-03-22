# Backup Policy

## What to backup
- `/knowledge/` — всегда (это канон)
- `/system/schemas/` — всегда
- `/system/skills/` — всегда
- `/docs/` — всегда
- `/system/progress/` — всегда (состояние ingestion)

## What NOT to backup
- `/knowledge/raw/` — опционально (можно перегенерировать из источника)
- `/media/videos/` — тяжело, только по необходимости

## Frequency
- После каждого значимого ingestion
- После каждого изменения схем или скиллов
- Раз в неделю — полный backup

## Method
```bash
# Push to GitHub
git add knowledge/ system/schemas/ system/skills/ docs/ operations/
git commit -m "chore: backup {date}"
git push origin main
```

## Recovery
See: restore.md
