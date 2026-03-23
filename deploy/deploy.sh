#!/bin/bash

################################################################################
# Скрипт развертывания Jarvis Trading Bot на Ubuntu VPS
# Deployment script for Jarvis Trading Bot on Ubuntu VPS
################################################################################

set -euo pipefail

# Цвета для вывода / Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Функции логирования / Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

################################################################################
# Проверка запуска от root / Check if running as root
################################################################################

if [[ $EUID -ne 0 ]]; then
    log_error "Этот скрипт должен быть запущен от root"
    log_error "This script must be run as root"
    exit 1
fi

log_info "Запуск развертывания Jarvis Trading Bot..."
log_info "Starting Jarvis Trading Bot deployment..."

################################################################################
# Переменные окружения / Environment variables
################################################################################

BOT_DIR="/opt/jarvis"
VENV_DIR="${BOT_DIR}/venv"
BOT_REPO="${GITHUB_REPO:-https://github.com/yourusername/jarvis-bot.git}"
ENV_FILE="${BOT_DIR}/.env"
SERVICE_FILE="/etc/systemd/system/jarvis.service"

log_info "Конфигурация / Configuration:"
log_info "  Bot directory: ${BOT_DIR}"
log_info "  Repository: ${BOT_REPO}"

################################################################################
# Функция создания системного пользователя / Create system user function
################################################################################

create_system_user() {
    if id "jarvis" &>/dev/null; then
        log_success "Пользователь jarvis уже существует / User jarvis already exists"
    else
        log_info "Создание системного пользователя jarvis / Creating system user jarvis..."
        useradd --system --home-dir "${BOT_DIR}" --shell /bin/bash --comment "Jarvis Bot Service" jarvis
        log_success "Пользователь jarvis создан / User jarvis created"
    fi
}

################################################################################
# Установка системных зависимостей / Install system dependencies
################################################################################

install_dependencies() {
    log_info "Обновление списков пакетов / Updating package lists..."
    apt-get update || {
        log_error "Не удалось обновить список пакетов / Failed to update package lists"
        exit 1
    }

    log_info "Установка системных зависимостей / Installing system dependencies..."

    local deps="python3 python3-pip python3-venv python3-dev git curl wget build-essential"

    for dep in $deps; do
        if dpkg -l | grep -q "^ii  $dep"; then
            log_success "$dep уже установлен / $dep already installed"
        else
            log_info "Устанавливаю $dep / Installing $dep..."
            apt-get install -y "$dep" || {
                log_error "Не удалось установить $dep / Failed to install $dep"
                exit 1
            }
        fi
    done

    log_success "Все системные зависимости установлены / All system dependencies installed"
}

################################################################################
# Создание структуры директорий / Create directory structure
################################################################################

create_directories() {
    log_info "Создание структуры директорий / Creating directory structure..."

    mkdir -p "${BOT_DIR}/bot"
    mkdir -p "${BOT_DIR}/logs"
    mkdir -p "${BOT_DIR}/data"

    log_success "Директории созданы / Directories created"
}

################################################################################
# Клонирование или обновление репозитория / Clone or update repository
################################################################################

setup_repository() {
    if [ -d "${BOT_DIR}/.git" ]; then
        log_info "Репозиторий уже существует, обновляю / Repository exists, updating..."
        cd "${BOT_DIR}" || exit 1
        git fetch origin || {
            log_error "Не удалось обновить репозиторий / Failed to fetch repository"
            exit 1
        }
        git reset --hard origin/main || {
            log_warning "Не удалось переключиться на main, пытаюсь master / Failed to switch to main, trying master..."
            git reset --hard origin/master || {
                log_error "Не удалось обновить репозиторий / Failed to update repository"
                exit 1
            }
        }
    else
        log_info "Клонирование репозитория / Cloning repository..."
        git clone "${BOT_REPO}" "${BOT_DIR}" || {
            log_error "Не удалось клонировать репозиторий / Failed to clone repository"
            exit 1
        }
    fi

    log_success "Репозиторий готов / Repository ready"
}

################################################################################
# Установка Python виртуального окружения / Setup Python virtual environment
################################################################################

setup_venv() {
    log_info "Создание виртуального окружения Python / Creating Python virtual environment..."

    if [ -d "${VENV_DIR}" ]; then
        log_warning "Виртуальное окружение уже существует / Virtual environment already exists"
    else
        python3 -m venv "${VENV_DIR}" || {
            log_error "Не удалось создать виртуальное окружение / Failed to create virtual environment"
            exit 1
        }
    fi

    log_success "Виртуальное окружение создано / Virtual environment created"
}

################################################################################
# Установка Python зависимостей / Install Python dependencies
################################################################################

install_python_deps() {
    log_info "Установка Python зависимостей / Installing Python dependencies..."

    # Активируем виртуальное окружение
    # shellcheck disable=SC1091
    source "${VENV_DIR}/bin/activate" || {
        log_error "Не удалось активировать виртуальное окружение / Failed to activate virtual environment"
        exit 1
    }

    # Обновляем pip, setuptools, wheel
    log_info "Обновление pip / Upgrading pip..."
    pip install --upgrade pip setuptools wheel || {
        log_error "Не удалось обновить pip / Failed to upgrade pip"
        exit 1
    }

    # Устанавливаем зависимости из requirements.txt
    if [ -f "${BOT_DIR}/requirements.txt" ]; then
        log_info "Установка зависимостей из requirements.txt / Installing from requirements.txt..."
        pip install -r "${BOT_DIR}/requirements.txt" || {
            log_error "Не удалось установить зависимости / Failed to install dependencies"
            exit 1
        }
        log_success "Python зависимости установлены / Python dependencies installed"
    else
        log_warning "requirements.txt не найден / requirements.txt not found"
    fi
}

################################################################################
# Настройка файла окружения / Setup environment file
################################################################################

setup_env_file() {
    log_info "Настройка файла .env / Setting up .env file..."

    if [ -f "${ENV_FILE}" ]; then
        log_success "Файл .env уже существует / .env file already exists"
        log_info "Текущие переменные окружения / Current environment variables:"
        grep -v '^#' "${ENV_FILE}" | grep -v '^$' | sed 's/=.*/=***/' || true
    else
        log_warning "Файл .env не найден / .env file not found"
        log_info "Необходимо создать файл .env вручную или скопировать .env.example"
        log_info "You need to create .env file manually or copy from .env.example"

        if [ -f "${BOT_DIR}/.env.example" ]; then
            log_info "Копирую .env.example в .env / Copying .env.example to .env..."
            cp "${BOT_DIR}/.env.example" "${ENV_FILE}" || {
                log_error "Не удалось скопировать .env.example / Failed to copy .env.example"
                exit 1
            }
            log_warning "Отредактируйте ${ENV_FILE} с вашими параметрами!"
            log_warning "Edit ${ENV_FILE} with your parameters!"
        else
            log_error "Ни .env ни .env.example не найдены / Neither .env nor .env.example found"
            exit 1
        fi
    fi
}

################################################################################
# Установка прав доступа / Set permissions
################################################################################

set_permissions() {
    log_info "Установка прав доступа / Setting permissions..."

    chown -R jarvis:jarvis "${BOT_DIR}" || {
        log_error "Не удалось изменить владельца / Failed to change owner"
        exit 1
    }

    chmod 750 "${BOT_DIR}"
    chmod 600 "${ENV_FILE}" 2>/dev/null || true
    chmod +x "${BOT_DIR}/bot/main.py" 2>/dev/null || true

    log_success "Права доступа установлены / Permissions set"
}

################################################################################
# Установка systemd сервиса / Install systemd service
################################################################################

install_systemd_service() {
    log_info "Установка systemd сервиса / Installing systemd service..."

    # Копируем файл сервиса
    local script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    local service_template="${script_dir}/jarvis.service"

    if [ ! -f "${service_template}" ]; then
        log_error "Шаблон jarvis.service не найден в ${script_dir}"
        log_error "jarvis.service template not found in ${script_dir}"
        exit 1
    fi

    cp "${service_template}" "${SERVICE_FILE}" || {
        log_error "Не удалось скопировать сервис файл / Failed to copy service file"
        exit 1
    }

    # Перезагружаем systemd
    systemctl daemon-reload || {
        log_error "Не удалось перезагрузить systemd / Failed to reload systemd"
        exit 1
    }

    # Включаем сервис при загрузке
    systemctl enable jarvis-bot || {
        log_error "Не удалось включить сервис / Failed to enable service"
        exit 1
    }

    log_success "Systemd сервис установлен / Systemd service installed"
}

################################################################################
# Запуск сервиса / Start service
################################################################################

start_service() {
    log_info "Запуск сервиса / Starting service..."

    systemctl start jarvis-bot || {
        log_error "Не удалось запустить сервис / Failed to start service"
        exit 1
    }

    # Даем сервису время на запуск
    sleep 3

    log_success "Сервис запущен / Service started"
}

################################################################################
# Показать статус / Show status
################################################################################

show_status() {
    log_info "Статус сервиса / Service status:"
    echo ""
    systemctl status jarvis-bot || true
    echo ""

    log_info "Последние логи / Recent logs:"
    journalctl -u jarvis-bot -n 20 --no-pager || true
}

################################################################################
# Главная функция / Main function
################################################################################

main() {
    log_info "=========================================="
    log_info "Jarvis Trading Bot - Deployment Script"
    log_info "=========================================="
    echo ""

    create_system_user
    echo ""

    install_dependencies
    echo ""

    create_directories
    echo ""

    setup_repository
    echo ""

    setup_venv
    echo ""

    install_python_deps
    echo ""

    setup_env_file
    echo ""

    set_permissions
    echo ""

    install_systemd_service
    echo ""

    start_service
    echo ""

    show_status
    echo ""

    log_success "=========================================="
    log_success "Развертывание завершено успешно!"
    log_success "Deployment completed successfully!"
    log_success "=========================================="
    echo ""
    log_info "Команды для управления / Management commands:"
    log_info "  Статус:       systemctl status jarvis-bot"
    log_info "  Логи:         journalctl -u jarvis-bot -f"
    log_info "  Перезагрузка: systemctl restart jarvis-bot"
    log_info "  Остановка:    systemctl stop jarvis-bot"
    echo ""
    log_warning "Не забудьте отредактировать ${ENV_FILE} с вашими параметрами!"
    log_warning "Don't forget to edit ${ENV_FILE} with your parameters!"
}

# Запуск главной функции / Run main function
main "$@"
