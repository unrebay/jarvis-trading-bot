# Jarvis Trading Bot - Makefile for VPS Management
# Используйте переменные окружения для конфигурации VPS
# Use environment variables for VPS configuration
#
# Требуемые переменные окружения / Required environment variables:
#   VPS_HOST     - IP адрес или имя хоста VPS
#   VPS_USER     - Пользователь SSH (обычно root)
#   VPS_SSH_KEY  - Путь к приватному SSH ключу (опционально)

.PHONY: help deploy start stop restart logs status update ssh test

# Цвета для вывода / Color codes
BLUE := \033[0;34m
GREEN := \033[0;32m
RED := \033[0;31m
YELLOW := \033[1;33m
NC := \033[0m

# Переменные конфигурации / Configuration variables
VPS_HOST ?= $(shell echo $$VPS_HOST)
VPS_USER ?= $(shell echo $$VPS_USER)
VPS_SSH_KEY ?= $(shell echo $$VPS_SSH_KEY)
DEPLOY_DIR ?= /opt/jarvis

# SSH опции / SSH options
SSH_CMD = ssh
ifdef VPS_SSH_KEY
	SSH_CMD := ssh -i $(VPS_SSH_KEY)
endif
SSH_OPTS := -o ConnectTimeout=10 -o StrictHostKeyChecking=accept-new

# Проверка конфигурации / Check configuration
ifndef VPS_HOST
$(error VPS_HOST не установлена / VPS_HOST is not set. Установите: export VPS_HOST=your.vps.ip)
endif
ifndef VPS_USER
$(error VPS_USER не установлена / VPS_USER is not set. Установите: export VPS_USER=root)
endif

SSH := $(SSH_CMD) $(SSH_OPTS) $(VPS_USER)@$(VPS_HOST)
SCP := scp $(SSH_OPTS) $(VPS_SSH_KEY:=-i %)

help:
	@echo "$(BLUE)================================$(NC)"
	@echo "$(BLUE)Jarvis Trading Bot - VPS Manager$(NC)"
	@echo "$(BLUE)================================$(NC)"
	@echo ""
	@echo "$(GREEN)Основные команды / Main commands:$(NC)"
	@echo "  $(YELLOW)make deploy$(NC)      - Развернуть бота на VPS"
	@echo "  $(YELLOW)make start$(NC)       - Запустить сервис"
	@echo "  $(YELLOW)make stop$(NC)        - Остановить сервис"
	@echo "  $(YELLOW)make restart$(NC)     - Перезагрузить сервис"
	@echo "  $(YELLOW)make logs$(NC)        - Просмотр логов в реальном времени"
	@echo "  $(YELLOW)make status$(NC)      - Статус сервиса"
	@echo "  $(YELLOW)make update$(NC)      - Обновить код и перезагрузить"
	@echo "  $(YELLOW)make ssh$(NC)         - Открыть SSH сессию"
	@echo ""
	@echo "$(GREEN)Конфигурация / Configuration:$(NC)"
	@echo "  VPS_HOST: $(VPS_HOST)"
	@echo "  VPS_USER: $(VPS_USER)"
	@echo "  VPS_SSH_KEY: $(VPS_SSH_KEY)"
	@echo ""
	@echo "$(GREEN)Примеры / Examples:$(NC)"
	@echo "  export VPS_HOST=123.45.67.89"
	@echo "  export VPS_USER=root"
	@echo "  export VPS_SSH_KEY=~/.ssh/vps_key"
	@echo "  make deploy"
	@echo ""

# Проверка доступности VPS
check-connection:
	@echo "$(BLUE)[CHECK]$(NC) Проверка подключения к VPS..."
	@$(SSH) "echo '$(GREEN)[OK]$(NC) VPS доступен'" || \
		(echo "$(RED)[ERROR]$(NC) Не удалось подключиться к VPS"; exit 1)

# Развертывание бота / Deploy bot
deploy: check-connection
	@echo "$(BLUE)[DEPLOY]$(NC) Запуск процесса развертывания..."
	@echo "$(YELLOW)[INFO]$(NC) Копирование скриптов развертывания..."
	$(SCP) deploy.sh $(VPS_USER)@$(VPS_HOST):/tmp/
	$(SCP) jarvis.service $(VPS_USER)@$(VPS_HOST):/tmp/
	@echo "$(YELLOW)[INFO]$(NC) Запуск deploy.sh на VPS..."
	@$(SSH) "chmod +x /tmp/deploy.sh && /tmp/deploy.sh"
	@echo "$(GREEN)[SUCCESS]$(NC) Развертывание завершено!"

# Запуск сервиса / Start service
start: check-connection
	@echo "$(BLUE)[START]$(NC) Запуск сервиса jarvis-bot..."
	@$(SSH) "systemctl start jarvis-bot"
	@sleep 2
	@$(SSH) "systemctl status jarvis-bot --no-pager | head -5"
	@echo "$(GREEN)[OK]$(NC) Сервис запущен"

# Остановка сервиса / Stop service
stop: check-connection
	@echo "$(BLUE)[STOP]$(NC) Остановка сервиса jarvis-bot..."
	@$(SSH) "systemctl stop jarvis-bot"
	@sleep 1
	@$(SSH) "systemctl status jarvis-bot --no-pager | head -3"
	@echo "$(GREEN)[OK]$(NC) Сервис остановлен"

# Перезагрузка сервиса / Restart service
restart: check-connection
	@echo "$(BLUE)[RESTART]$(NC) Перезагрузка сервиса jarvis-bot..."
	@$(SSH) "systemctl restart jarvis-bot"
	@sleep 2
	@$(SSH) "systemctl status jarvis-bot --no-pager | head -5"
	@echo "$(GREEN)[OK]$(NC) Сервис перезагружен"

# Просмотр логов / View logs
logs: check-connection
	@echo "$(BLUE)[LOGS]$(NC) Подключение к логам (Ctrl+C для выхода)..."
	@$(SSH) "journalctl -u jarvis-bot -f --no-pager"

# Статус сервиса / Service status
status: check-connection
	@echo "$(BLUE)[STATUS]$(NC) Статус сервиса:"
	@echo ""
	@$(SSH) "systemctl status jarvis-bot --no-pager"
	@echo ""
	@echo "$(BLUE)[RECENT LOGS]$(NC) Последние 15 строк логов:"
	@echo ""
	@$(SSH) "journalctl -u jarvis-bot -n 15 --no-pager"

# Обновление кода и перезагрузка / Update code and restart
update: check-connection
	@echo "$(BLUE)[UPDATE]$(NC) Обновление кода..."
	@$(SSH) "cd $(DEPLOY_DIR) && git fetch origin && git reset --hard origin/main || git reset --hard origin/master"
	@echo "$(BLUE)[UPDATE]$(NC) Переустановка зависимостей..."
	@$(SSH) "cd $(DEPLOY_DIR) && source venv/bin/activate && pip install -r requirements.txt"
	@echo "$(BLUE)[RESTART]$(NC) Перезагрузка сервиса..."
	@$(SSH) "systemctl restart jarvis-bot"
	@sleep 2
	@echo "$(GREEN)[OK]$(NC) Обновление завершено"
	@$(SSH) "journalctl -u jarvis-bot -n 5 --no-pager"

# SSH сессия / SSH session
ssh: check-connection
	@echo "$(BLUE)[SSH]$(NC) Открытие SSH сессии..."
	@$(SSH)

# Просмотр переменных окружения / View environment variables
env-status: check-connection
	@echo "$(BLUE)[ENV]$(NC) Переменные окружения бота:"
	@$(SSH) "grep -v '^#' $(DEPLOY_DIR)/.env | grep -v '^$$' | sed 's/=.*/=***/' || echo 'Файл .env не найден'"

# Проверка дискового пространства / Check disk space
disk-usage: check-connection
	@echo "$(BLUE)[DISK]$(NC) Использование диска:"
	@$(SSH) "df -h $(DEPLOY_DIR)"

# Проверка памяти / Check memory usage
memory-usage: check-connection
	@echo "$(BLUE)[MEMORY]$(NC) Использование памяти Python процесса:"
	@$(SSH) "ps aux | grep -E 'python.*main.py|PID' | head -2"

# Тест подключения к Telegram / Test Telegram connection
test-telegram: check-connection
	@echo "$(BLUE)[TEST]$(NC) Тестирование подключения к Telegram..."
	@$(SSH) "cd $(DEPLOY_DIR) && venv/bin/python3 -c 'import os; from dotenv import load_dotenv; load_dotenv(); from telegram import Bot; bot = Bot(token=os.getenv(\"BOT_TOKEN\")); print(f\"[OK] Бот подключен: {bot.get_me().first_name}\")' 2>&1 || echo '[ERROR] Не удалось подключиться'"

# Просмотр процесса бота / View bot process
ps-bot: check-connection
	@echo "$(BLUE)[PROCESS]$(NC) Python процессы на VPS:"
	@$(SSH) "ps aux | grep -E 'python|jarvis' | grep -v grep || echo 'Процесс не найден'"

# Резервная копия конфигурации / Backup configuration
backup-config: check-connection
	@echo "$(BLUE)[BACKUP]$(NC) Создание резервной копии конфигурации..."
	@mkdir -p backups
	@$(SSH) "cat $(DEPLOY_DIR)/.env" > backups/.env.backup.$(shell date +%Y%m%d_%H%M%S) 2>/dev/null || true
	@echo "$(GREEN)[OK]$(NC) Резервная копия создана"

# Просмотр всех команд / List all commands
list:
	@grep -E "^[a-z-]+:" Makefile | awk '{print $$1}' | sed 's/:$$//' | sort

# Установка SSH ключа / Set SSH key (одноразовая команда / one-time command)
setup:
	@echo "$(BLUE)[SETUP]$(NC) Введите параметры VPS:"
	@read -p "VPS IP/Hostname: " vps_host; \
	read -p "VPS User (root): " vps_user; vps_user=$${vps_user:-root}; \
	read -p "SSH Key path [~/.ssh/id_rsa]: " vps_ssh_key; vps_ssh_key=$${vps_ssh_key:-$$HOME/.ssh/id_rsa}; \
	echo ""; \
	echo "$(YELLOW)Добавьте в ~/.bashrc или ~/.zshrc:$(NC)"; \
	echo "export VPS_HOST=$${vps_host}"; \
	echo "export VPS_USER=$${vps_user}"; \
	echo "export VPS_SSH_KEY=$${vps_ssh_key}"; \
	echo ""

.DEFAULT_GOAL := help
