# Maintenance

## Weekly checks
- [ ] Проверить `/system/progress/discord_state.json` — всё ли заingestено?
- [ ] Проверить `/knowledge/raw/` — есть ли необработанные файлы?
- [ ] Запустить dedup-проверку в `/knowledge/lessons/`
- [ ] Backup на GitHub

## After new Discord export
1. Запустить `knowledge-ingestion` skill
2. Запустить `knowledge-structurer` skill
3. Обновить discord_state.json
4. Commit + push

## Schema updates
При изменении схем — обязательно:
1. Обновить версию в схеме
2. Написать migration-скрипт для существующих объектов
3. Перепроверить скиллы на совместимость
