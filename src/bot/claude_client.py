"""
Модуль клиента Anthropic Claude API для trading education bot JARVIS.
Поддерживает маршрутизацию затрат через различные модели с кешированием промптов.
"""

import anthropic
from typing import Optional, Union, Any
import json
import time
from dataclasses import dataclass

# Lazy import to avoid circular — cost_manager is a module-level singleton
def _record_cost(model_name: str, feature: str, usage: "TokenUsage") -> None:
    """Wire actual API usage into CostManager for budget tracking."""
    try:
        from .cost_manager import cost_manager
        cost_manager.reset_daily_limit()  # ensure today's tracker
        cost_manager.record_cost(
            model=model_name,
            feature=feature,
            input_tokens=usage.input_tokens + usage.cache_creation_input_tokens,
            output_tokens=usage.output_tokens,
        )
    except Exception:
        pass  # cost tracking is non-critical


# Константы моделей
HAIKU = "claude-haiku-4-5-20251001"
SONNET = "claude-sonnet-4-6"
OPUS = "claude-opus-4-6"

# Константы для retry логики
MAX_RETRIES = 3
INITIAL_BACKOFF = 1
MAX_BACKOFF = 8


@dataclass
class TokenUsage:
    """Класс для отслеживания использования токенов и стоимости."""
    input_tokens: int = 0
    output_tokens: int = 0
    cache_creation_input_tokens: int = 0
    cache_read_input_tokens: int = 0

    def get_haiku_cost(self) -> float:
        """Расчет стоимости для Haiku модели."""
        input_cost = (self.input_tokens + self.cache_creation_input_tokens) * 0.80 / 1_000_000
        cache_read_cost = self.cache_read_input_tokens * 0.10 / 1_000_000
        output_cost = self.output_tokens * 4.00 / 1_000_000
        return input_cost + cache_read_cost + output_cost

    def get_sonnet_cost(self) -> float:
        """Расчет стоимости для Sonnet модели."""
        input_cost = (self.input_tokens + self.cache_creation_input_tokens) * 3.00 / 1_000_000
        cache_read_cost = self.cache_read_input_tokens * 0.30 / 1_000_000
        output_cost = self.output_tokens * 15.00 / 1_000_000
        return input_cost + cache_read_cost + output_cost

    def get_opus_cost(self) -> float:
        """Расчет стоимости для Opus модели."""
        input_cost = (self.input_tokens + self.cache_creation_input_tokens) * 15.00 / 1_000_000
        cache_read_cost = self.cache_read_input_tokens * 1.50 / 1_000_000
        output_cost = self.output_tokens * 75.00 / 1_000_000
        return input_cost + cache_read_cost + output_cost

    def to_dict(self) -> dict:
        """Преобразование в словарь для логирования."""
        return {
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "cache_creation_input_tokens": self.cache_creation_input_tokens,
            "cache_read_input_tokens": self.cache_read_input_tokens,
            "haiku_cost_usd": round(self.get_haiku_cost(), 6),
            "sonnet_cost_usd": round(self.get_sonnet_cost(), 6),
            "opus_cost_usd": round(self.get_opus_cost(), 6),
        }


class ClaudeClient:
    """
    Клиент для взаимодействия с Anthropic Claude API.
    Поддерживает маршрутизацию затрат и кеширование системных промптов.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        enable_caching: bool = True,
        cache_ttl_minutes: int = 5,
    ):
        """
        Инициализация Claude клиента.

        Args:
            api_key: API ключ Anthropic (если None, используется переменная окружения).
            enable_caching: Включить кеширование промптов.
            cache_ttl_minutes: Время жизни кеша в минутах.
        """
        self.client = anthropic.Anthropic(api_key=api_key)
        self.enable_caching = enable_caching
        self.cache_ttl_minutes = cache_ttl_minutes
        self.last_usage = None
        self._system_prompt_cache = None

    def _get_system_prompt(self) -> str:
        """
        Получить системный промпт для JARVIS из файла или кеша.

        Returns:
            Системный промпт в виде строки.
        """
        if self._system_prompt_cache is not None:
            return self._system_prompt_cache

        try:
            with open("system/prompts/mentor.md", "r", encoding="utf-8") as f:
                self._system_prompt_cache = f.read()
        except FileNotFoundError:
            # Fallback промпт если файл не найден
            self._system_prompt_cache = "Ты - JARVIS, профессиональный торговый ментор, специалист в методологии ICT/SMC."

        return self._system_prompt_cache

    def _build_cached_system(self) -> dict:
        """
        Построить системный блок с поддержкой кеширования.

        Returns:
            Словарь с системным контентом и кешем-контролем.
        """
        system_prompt = self._get_system_prompt()
        system_block = {
            "type": "text",
            "text": system_prompt,
        }

        if self.enable_caching:
            system_block["cache_control"] = {"type": "ephemeral"}

        return system_block

    def _retry_with_backoff(
        self,
        func,
        *args,
        **kwargs
    ) -> Any:
        """
        Выполнить функцию с экспоненциальным backoff при ошибках.

        Args:
            func: Функция для выполнения.
            *args: Позиционные аргументы.
            **kwargs: Именованные аргументы.

        Returns:
            Результат функции.

        Raises:
            anthropic.APIError: Если все retry попытки исчерпаны.
        """
        backoff = INITIAL_BACKOFF

        for attempt in range(MAX_RETRIES):
            try:
                return func(*args, **kwargs)
            except anthropic.RateLimitError as e:
                if attempt == MAX_RETRIES - 1:
                    raise
                time.sleep(backoff)
                backoff = min(backoff * 2, MAX_BACKOFF)
            except anthropic.APIStatusError as e:
                # Только retry для 5xx ошибок
                if not (500 <= e.status_code < 600):
                    raise
                if attempt == MAX_RETRIES - 1:
                    raise
                time.sleep(backoff)
                backoff = min(backoff * 2, MAX_BACKOFF)

    def ask_mentor(
        self,
        user_message: str,
        history: Optional[list] = None,
        level: str = "Beginner",
        knowledge_context: Optional[str] = None,
    ) -> str:
        """
        Получить ответ от торгового ментора JARVIS (быстро, используя Haiku).

        Основной метод для интерактивного общения в Telegram боте.
        Поддерживает кеширование системного промпта для снижения затрат.

        Args:
            user_message: Сообщение пользователя.
            history: История сообщений в формате [{"role": "user/assistant", "content": "..."}].
            level: Уровень обучения пользователя (Beginner/Elementary/Intermediate/Advanced/Professional).
            knowledge_context: Дополнительный контекст знаний (график, анализ и т.д.).

        Returns:
            Ответ ментора в виде строки.

        Raises:
            anthropic.APIError: При ошибке API.
        """
        if history is None:
            history = []

        # Уровень передаётся через системный блок — НЕ в тело user-сообщения,
        # чтобы бот не упоминал уровень в каждом ответе.
        dynamic_system: list[dict] = [self._build_cached_system()]

        level_block_parts = [f"Уровень ученика: {level}."]
        if knowledge_context:
            level_block_parts.append(f"\nДополнительный контекст:\n{knowledge_context}")
        dynamic_system.append({"type": "text", "text": "".join(level_block_parts)})

        # Построение сообщений — только реальные сообщения, без вшитого уровня
        messages = history.copy()
        if not any(msg.get("role") == "user" and msg.get("content") == user_message for msg in messages):
            messages.append({"role": "user", "content": user_message})

        def _call_haiku():
            return self.client.messages.create(
                model=HAIKU,
                max_tokens=1024,
                system=dynamic_system,
                messages=messages,
            )

        response = self._retry_with_backoff(_call_haiku)
        self.last_usage = TokenUsage(
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
            cache_creation_input_tokens=getattr(response.usage, "cache_creation_input_tokens", 0),
            cache_read_input_tokens=getattr(response.usage, "cache_read_input_tokens", 0),
        )
        _record_cost("haiku", "mentoring", self.last_usage)  # FIX: wire into budget tracker

        return response.content[0].text

    def structure_knowledge(
        self,
        raw_text: str,
        schema_type: str = "concept",
    ) -> dict:
        """
        Структурировать raw knowledge для ingestion pipeline (используя Sonnet).

        Преобразует неструктурированный текст в структурированный JSON для хранения в БД.
        Оптимизирована для cost-efficiency через Sonnet модель.

        Args:
            raw_text: Неструктурированный текст для структурирования.
            schema_type: Тип схемы (concept/setup/strategy/riskmanagement/pattern).

        Returns:
            Словарь с структурированными данными согласно схеме.

        Raises:
            anthropic.APIError: При ошибке API.
            json.JSONDecodeError: Если ответ не содержит валидный JSON.
        """
        schema_prompts = {
            "concept": """Структурируй текст о торговом концепте в JSON с полями:
            {
                "name": "название концепта",
                "description": "описание",
                "key_points": ["пункт1", "пункт2"],
                "application_level": "уровень (Beginner/Elementary/Intermediate/Advanced/Professional)",
                "related_concepts": ["связанный1", "связанный2"]
            }""",
            "setup": """Структурируй торговый сетап в JSON:
            {
                "name": "название сетапа",
                "trigger": "условие входа",
                "confirmation": "подтверждение",
                "entry_rules": ["правило1", "правило2"],
                "tp_levels": ["уровень1", "уровень2"],
                "stop_loss": "расчет стопа",
                "timeframes": ["TF1", "TF2"],
                "probability": "процент вероятности"
            }""",
            "strategy": """Структурируй стратегию в JSON:
            {
                "name": "название",
                "framework": "методология (ICT/SMC/...)",
                "steps": ["шаг1", "шаг2"],
                "risk_reward_ratio": "рекомендуемое соотношение",
                "best_pairs": ["пара1", "пара2"],
                "market_conditions": "рыночные условия",
                "advanced_tips": ["совет1", "совет2"]
            }""",
            "riskmanagement": """Структурируй управление рисками в JSON:
            {
                "principle": "принцип",
                "position_sizing": "расчет размера",
                "max_loss_per_trade": "максимум",
                "rules": ["правило1", "правило2"],
                "examples": ["пример1", "пример2"]
            }""",
            "pattern": """Структурируй паттерн в JSON:
            {
                "name": "название паттерна",
                "visuals": "описание визуально",
                "confirmation_signals": ["сигнал1", "сигнал2"],
                "trading_rules": ["правило1", "правило2"],
                "win_rate": "процент успеха",
                "best_timeframe": "лучший TF"
            }""",
        }

        prompt = schema_prompts.get(
            schema_type,
            schema_prompts["concept"]
        )

        def _call_sonnet():
            return self.client.messages.create(
                model=SONNET,
                max_tokens=2048,
                system=[
                    {
                        "type": "text",
                        "text": "Ты эксперт в структурировании торговой информации. Преобразуй входной текст в валидный JSON согласно схеме. Отвечай ТОЛЬКО JSON без дополнительного текста.",
                    }
                ],
                messages=[
                    {
                        "role": "user",
                        "content": f"{prompt}\n\nТекст для структурирования:\n{raw_text}",
                    }
                ],
            )

        response = self._retry_with_backoff(_call_sonnet)
        self.last_usage = TokenUsage(
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
            cache_creation_input_tokens=getattr(response.usage, "cache_creation_input_tokens", 0),
            cache_read_input_tokens=getattr(response.usage, "cache_read_input_tokens", 0),
        )

        # Парсинг JSON из ответа
        response_text = response.content[0].text
        try:
            # Попытка найти JSON блок в ответе
            if "```json" in response_text:
                json_str = response_text.split("```json")[1].split("```")[0]
            elif "```" in response_text:
                json_str = response_text.split("```")[1].split("```")[0]
            else:
                json_str = response_text

            return json.loads(json_str.strip())
        except json.JSONDecodeError as e:
            raise json.JSONDecodeError(
                f"Не удалось распарсить JSON из ответа Sonnet: {response_text[:200]}",
                response_text,
                0,
            ) from e

    def analyze_complex(
        self,
        prompt: str,
        context_data: Optional[dict] = None,
        max_tokens: int = 4096,
    ) -> str:
        """
        Выполнить сложный анализ используя Opus модель (для критических задач).

        Используется для глубокого анализа, синтеза сложной информации, принятия критических решений.
        Самая мощная модель, используется экономно для максимизации ROI.

        Args:
            prompt: Промпт для анализа.
            context_data: Дополнительные данные контекста (словарь).
            max_tokens: Максимум токенов в ответе.

        Returns:
            Результат анализа в виде строки.

        Raises:
            anthropic.APIError: При ошибке API.
        """
        # Подготовка контекстных данных
        context_str = ""
        if context_data:
            context_str = "\n\nКонтекстные данные:\n" + json.dumps(context_data, ensure_ascii=False, indent=2)

        full_prompt = prompt + context_str

        def _call_opus():
            return self.client.messages.create(
                model=OPUS,
                max_tokens=max_tokens,
                system=[
                    self._build_cached_system(),
                ],
                messages=[
                    {
                        "role": "user",
                        "content": full_prompt,
                    }
                ],
            )

        response = self._retry_with_backoff(_call_opus)
        self.last_usage = TokenUsage(
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
            cache_creation_input_tokens=getattr(response.usage, "cache_creation_input_tokens", 0),
            cache_read_input_tokens=getattr(response.usage, "cache_read_input_tokens", 0),
        )

        return response.content[0].text

    def count_tokens(
        self,
        messages: list,
        model: str = HAIKU,
    ) -> int:
        """
        Подсчитать количество токенов для сообщений.

        Args:
            messages: Список сообщений в формате [{"role": "...", "content": "..."}].
            model: Модель для подсчета (по умолчанию Haiku).

        Returns:
            Количество токенов.
        """
        return self.client.messages.count_tokens(
            model=model,
            messages=messages,
        ).input_tokens

    def get_last_usage_stats(self) -> Optional[dict]:
        """
        Получить статистику использования последнего запроса.

        Returns:
            Словарь со статистикой затрат или None если запросов не было.
        """
        if self.last_usage is None:
            return None
        return self.last_usage.to_dict()

    def estimate_cost_for_prompt(
        self,
        user_message: str,
        model: str = HAIKU,
    ) -> dict:
        """
        Оценить стоимость выполнения промпта для конкретной модели.

        Args:
            user_message: Сообщение пользователя.
            model: Целевая модель.

        Returns:
            Словарь с оценкой стоимости.
        """
        input_tokens = self.count_tokens(
            [{"role": "user", "content": user_message}],
            model=model,
        )

        # Оценка output токенов (примерно 20% от input)
        estimated_output_tokens = int(input_tokens * 0.2)

        usage = TokenUsage(
            input_tokens=input_tokens,
            output_tokens=estimated_output_tokens,
        )

        model_costs = {
            HAIKU: usage.get_haiku_cost(),
            SONNET: usage.get_sonnet_cost(),
            OPUS: usage.get_opus_cost(),
        }

        return {
            "input_tokens": input_tokens,
            "estimated_output_tokens": estimated_output_tokens,
            "estimated_cost_usd": model_costs.get(model, 0),
            "model": model,
        }

    def extract_memory_update(
        self,
        recent_messages: list,
        current_memory: dict,
    ) -> dict:
        """
        Extract new information from recent conversation and update user memory portrait.

        Uses Haiku (cheap). Called every MEMORY_UPDATE_INTERVAL messages.
        Analyses the last 10 messages and merges newly discovered facts into
        the existing portrait (name, experience, style, topics, etc.)

        Args:
            recent_messages: [{"role": "user/assistant", "content": "..."}]
            current_memory:  Current memory dict (from UserMemory.load())

        Returns:
            Updated memory dict (or current_memory unchanged on error).
        """
        # Build conversation snippet (last 10 messages, truncated)
        conversation_text = ""
        for msg in recent_messages[-10:]:
            role = "Ученик" if msg["role"] == "user" else "JARVIS"
            conversation_text += f"{role}: {msg['content'][:300]}\n"

        current_json = json.dumps(current_memory, ensure_ascii=False, indent=2)

        prompt = (
            "Ты анализируешь диалог ученика с торговым ментором JARVIS.\n"
            "Обнови «портрет ученика» на основе новых сообщений.\n\n"
            f"ТЕКУЩИЙ ПОРТРЕТ:\n{current_json}\n\n"
            f"ПОСЛЕДНИЕ СООБЩЕНИЯ:\n{conversation_text}\n"
            "ПРАВИЛА ОБНОВЛЕНИЯ:\n"
            "- Обновляй ТОЛЬКО поля, для которых есть явные свидетельства в диалоге\n"
            "- Не придумывай — только то, что реально сказал или показал ученик\n"
            "- profile.name — имя, если ученик представился или подписывался\n"
            "- profile.experience — опыт (годы, «новичок», «2 года» и т.д.)\n"
            "- profile.style — стиль торговли (swing/scalp/day/position)\n"
            "- profile.pairs — инструменты, которые упоминал\n"
            "- profile.timeframes — таймфреймы, которые упоминал\n"
            "- profile.goals — цель обучения\n"
            "- learning.topics_known — концепты, которые ученик уже понимает\n"
            "- learning.topics_struggling — темы, где путается или переспрашивает\n"
            "- learning.current_focus — тема, которую изучает прямо сейчас\n"
            "- personality.tone — «formal» / «informal» / «mixed» по стилю речи\n"
            "- personality.traits — черты характера (прямой, нетерпеливый, аналитический...)\n"
            "- conversations.summary — краткое резюме ВСЕГО что знаешь об ученике (2-4 предложения, "
            "включи информацию из предыдущего summary)\n\n"
            "Верни ТОЛЬКО валидный JSON обновлённого портрета (без markdown блоков, без пояснений):"
        )

        def _call():
            return self.client.messages.create(
                model=HAIKU,
                max_tokens=1024,
                system=[{
                    "type": "text",
                    "text": (
                        "Ты аналитик данных. Извлекаешь структурированную информацию "
                        "о пользователе из диалога. Отвечай ТОЛЬКО валидным JSON."
                    ),
                }],
                messages=[{"role": "user", "content": prompt}],
            )

        try:
            response = self._retry_with_backoff(_call)
            text = response.content[0].text.strip()
            # Strip markdown code fences if present
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0]
            elif "```" in text:
                text = text.split("```")[1].split("```")[0]
            updated = json.loads(text.strip())
            return updated
        except Exception as e:
            print(f"⚠️ Memory extraction error: {e}")
            return current_memory  # return unchanged on any error

    def clear_cache(self):
        """
        Очистить локальный кеш системного промпта.
        Используется для обновления промпта при его изменении.
        """
        self._system_prompt_cache = None


if __name__ == "__main__":
    # Пример использования
    client = ClaudeClient(enable_caching=True)

    # Пример: запрос к ментору
    response = client.ask_mentor(
        user_message="Что такое FVG и как его торговать?",
        level="Beginner",
        knowledge_context="Ищу понимание принципов Fair Value Gap на EUR/USD",
    )
    print("Ответ ментора:")
    print(response)
    print("\nСтатистика использования:")
    print(client.get_last_usage_stats())
