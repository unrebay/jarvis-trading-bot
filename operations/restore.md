# Restore Guide

## Full restore from GitHub

```bash
git clone {repo_url} trading-agent
cd trading-agent
```

## Partial restore (knowledge only)

```bash
git checkout main -- knowledge/
git checkout main -- system/schemas/
git checkout main -- system/skills/
```

## Re-run ingestion after restore

1. Check `/system/progress/discord_state.json` — смотрим last_updated
2. Re-run `knowledge-ingestion` skill на недостающих файлах
3. Re-run `knowledge-structurer` на всех необработанных raw файлах
