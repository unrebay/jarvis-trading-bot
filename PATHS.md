# JARVIS Bot — All Paths & Locations Reference

> This file exists so that Claude always knows exactly where everything lives.
> Update this file if any paths change.

---

## 📁 Mac (Local Machine)

| What | Path |
|------|------|
| Project root | `/Users/andy/jarvis-trading-bot` |
| Bot source code | `/Users/andy/jarvis-trading-bot/src/bot/` |
| Entry point | `/Users/andy/jarvis-trading-bot/src/bot/main.py` |
| Telegram handler | `/Users/andy/jarvis-trading-bot/src/bot/telegram_handler.py` |
| Claude client | `/Users/andy/jarvis-trading-bot/src/bot/claude_client.py` |
| RAG search | `/Users/andy/jarvis-trading-bot/src/bot/rag_search.py` |
| Cost manager | `/Users/andy/jarvis-trading-bot/src/bot/cost_manager.py` |
| System prompt | `/Users/andy/jarvis-trading-bot/system/prompts/mentor.md` |
| Knowledge base | `/Users/andy/jarvis-trading-bot/kb/` |
| API keys / secrets | `/Users/andy/jarvis-trading-bot/.env` |
| Python deps | `/Users/andy/jarvis-trading-bot/requirements.txt` |
| Deploy scripts | `/Users/andy/jarvis-trading-bot/deploy/` |
| Architecture HTML | `/Users/andy/jarvis-trading-bot/JARVIS-ARCHITECTURE.html` |
| Archive (old files) | `/Users/andy/jarvis-trading-bot/archive/` |

---

## 🖥️ VPS (77.110.126.107)

| What | Path |
|------|------|
| **SSH access** | `ssh root@77.110.126.107` (pwd: `3wvieZOZ5EdV`) |
| **SSH shortcut** | `ssh jarvis-vps` (after running `setup_ssh_keys.sh`) |
| Project root | `/opt/jarvis/` |
| Bot source code | `/opt/jarvis/src/bot/` |
| Entry point | `/opt/jarvis/src/bot/main.py` |
| System prompt | `/opt/jarvis/system/prompts/mentor.md` |
| Knowledge base | `/opt/jarvis/kb/` |
| API keys / secrets | `/opt/jarvis/.env` |
| Python deps | `/opt/jarvis/requirements.txt` |
| Python venv | `/opt/jarvis/venv/` |
| Python binary | `/opt/jarvis/venv/bin/python3` |
| Deploy scripts | `/opt/jarvis/deploy/` |
| Systemd service file | `/etc/systemd/system/jarvis-bot.service` |
| Bot logs | `journalctl -u jarvis-bot` |

---

## ☁️ External Services

| Service | Details |
|---------|---------|
| **Telegram Bot** | Bot token in `.env` → `TELEGRAM_BOT_TOKEN` |
| **Anthropic API** | Key in `.env` → `ANTHROPIC_API_KEY`; default model: Claude Haiku |
| **Supabase project** | ID: `ivifpljgzsmstirlrjar`, region: eu-central-1 |
| **Supabase URL** | In `.env` → `SUPABASE_URL` |
| **Supabase key** | In `.env` → `SUPABASE_ANON_KEY` |
| **Notion page** | https://www.notion.so/32c76cda92398173a5dadb440e652c3f |

---

## 🗄️ Supabase Database Tables

| Table | Purpose | Key columns |
|-------|---------|-------------|
| `knowledge_documents` | RAG knowledge base (61 lessons) | `id`, `section`, `topic`, `title`, `content`, `metadata` |
| `bot_users` | Telegram users registry | `telegram_id`, `username`, `level`, `messages_count` |
| `conversations` | Message history per user | `user_id`, `role`, `content`, `created_at` |

**Sections in `knowledge_documents`** (column name is `section`, NOT `category`):
- `principles` — 20 lessons (ICT/SMC fundamentals, BPR, OB, etc.)
- `market-mechanics` — 13 lessons (Sessions, Asia levels, STDV, etc.)
- `tda-and-entry-models` — 9 lessons (TDA, Wyckoff, Static/Dynamic)
- `gold-mechanics` — 8 lessons (FVG, IMB, targets, timings)
- `risk-management` — 6 lessons (Backtest, RR, position sizing)
- `beginners` — 3 lessons (platforms, terminology, basics)
- `structure-and-liquidity` — 2 lessons (structure, liquidity)

---

## 🔧 Deploy Scripts (run from Mac terminal)

| Script | Where to run | What it does |
|--------|-------------|--------------|
| `deploy/setup_ssh_keys.sh` | Mac (once) | Generates SSH key, uploads to VPS → no more passwords |
| `deploy/push_to_vps.sh` | Mac (each update) | Rsyncs code + triggers VPS setup + restarts bot |
| `deploy/setup_vps.sh` | VPS (auto-called) | Installs deps, configures systemd, starts bot |

**Quick deploy command (from project root):**
```bash
cd /Users/andy/jarvis-trading-bot && bash deploy/push_to_vps.sh
```

---

## 🤖 Bot systemd Service

| Command | Action |
|---------|--------|
| `systemctl status jarvis-bot` | Check if running |
| `systemctl restart jarvis-bot` | Restart after code changes |
| `systemctl stop jarvis-bot` | Stop the bot |
| `systemctl enable jarvis-bot` | Auto-start on VPS reboot |
| `journalctl -u jarvis-bot -f` | Live log stream |
| `journalctl -u jarvis-bot -n 50` | Last 50 log lines |

---

## 📦 Key Python Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| `python-telegram-bot` | 20.7 | Telegram polling |
| `anthropic` | 0.49.0 | Claude API |
| `supabase` | ≥2.0.0 | Database |
| `python-dotenv` | 1.0.0 | Load `.env` |

---

## 🗂️ Source Files Summary

```
src/bot/
├── main.py              ← Entry point, wires everything together
├── telegram_handler.py  ← All message/command handlers, CostManager integration
├── claude_client.py     ← ClaudeClient: ask_mentor(), model routing, prompt cache
├── rag_search.py        ← keyword_search() + format_context() via Supabase
├── cost_manager.py      ← BotMode (FULL/LITE/OFFLINE), $1/day budget, throttling
├── image_handler.py     ← Vision analysis for chart photos
├── chart_annotator.py   ← Chart annotation helper
└── __init__.py
```
