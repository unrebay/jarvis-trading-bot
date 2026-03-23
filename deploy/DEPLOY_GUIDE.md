# Jarvis Bot — Deployment Guide

**VPS:** 77.110.126.107 (Ubuntu) | **Dir:** `/opt/jarvis` | **Service:** `jarvis-bot`
**Repo:** https://github.com/unrebay/jarvis-trading-bot | **Deploy branch:** `production`

---

## ⚡ Daily workflow (after initial setup)

```bash
git add . && git commit -m "fix: описание изменений" && git push origin production
```

GitHub Actions автоматически задеплоит через ~30 сек. Смотреть прогресс:
`https://github.com/unrebay/jarvis-trading-bot/actions`

---

## 🛠️ First-time setup (one-time, ~5 min)

### Step 1 — Create `production` branch and push code

```bash
cd /Users/andy/jarvis-trading-bot
git checkout -b production
git push origin production
```

### Step 2 — Generate deploy key for GitHub Actions

```bash
bash deploy/setup_github_actions.sh
```

Этот скрипт:
- Генерирует SSH-ключ `~/.ssh/jarvis_github_actions`
- Устанавливает его на VPS
- Показывает 3 секрета для добавления в GitHub

### Step 3 — Add secrets to GitHub

Перейди в: **`https://github.com/unrebay/jarvis-trading-bot/settings/secrets/actions`**

Добавь 3 секрета (кнопка `New repository secret`):

| Name | Value |
|------|-------|
| `VPS_HOST` | `77.110.126.107` |
| `VPS_USER` | `root` |
| `VPS_SSH_KEY` | *(приватный ключ из вывода скрипта выше)* |

### Step 4 — Initialize git on VPS (one-time)

```bash
bash deploy/init_git_on_vps.sh
```

Конвертирует `/opt/jarvis` из rsync-деплоя в git-репо, привязанное к `production`.

### Step 5 — Test the pipeline

```bash
git commit --allow-empty -m "test: github actions deploy" && git push origin production
```

Открой `https://github.com/unrebay/jarvis-trading-bot/actions` — увидишь зелёный чекмарк через ~30 сек.

---

## 📊 Monitor the bot

**Live logs:**
```bash
ssh root@77.110.126.107 'journalctl -u jarvis-bot -f'
```

**Status:**
```bash
ssh root@77.110.126.107 'systemctl status jarvis-bot'
```

**Manual restart (экстренный случай):**
```bash
ssh root@77.110.126.107 'systemctl restart jarvis-bot'
```

**SSH напрямую:**
```bash
ssh jarvis-vps   # если настроен ~/.ssh/config
# или
ssh root@77.110.126.107   # пароль: 3wvieZOZ5EdV
```

---

## 🗂️ Deploy files

| File | Назначение |
|------|-----------|
| `.github/workflows/deploy.yml` | GitHub Actions workflow (авто-деплой при push в production) |
| `deploy/setup_github_actions.sh` | Генерирует deploy key + инструкции по GitHub Secrets |
| `deploy/init_git_on_vps.sh` | Один раз: конвертирует VPS в git-репо |
| `deploy/setup_vps.sh` | Устанавливает Python окружение, systemd сервис на VPS |
| `deploy/push_to_vps.sh` | Старый rsync-деплой (резервный вариант, если git не работает) |
| `deploy/jarvis.service` | Systemd service definition |

---

## 🔑 Installed SSH keys

| Key | Назначение |
|-----|-----------|
| `~/.ssh/jarvis_vps` | Твой Mac → VPS (без пароля) |
| `~/.ssh/jarvis_github_actions` | GitHub Actions → VPS (без пароля) |

---

## 🔧 Troubleshooting

**Actions упали — смотреть детали:**
```
https://github.com/unrebay/jarvis-trading-bot/actions
```

**Бот не отвечает после деплоя:**
```bash
ssh root@77.110.126.107 'journalctl -u jarvis-bot -n 50 --no-pager'
```

**Ручной деплой (если GitHub Actions не работает):**
```bash
bash deploy/push_to_vps.sh
```

**Обновить только .env на VPS:**
```bash
ssh root@77.110.126.107 'nano /opt/jarvis/.env && systemctl restart jarvis-bot'
```
