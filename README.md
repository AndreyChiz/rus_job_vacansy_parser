# Parser Service

Сервис парсинга вакансий с российских job-сайтов. Получает команды через RabbitMQ, парсит вакансии публикует результат в Redis по мере парсинга.

## Архитектура

```
  RabbitMQ                    Parser Service                   Redis
┌──────────┐    vacancy.parse    ┌──────────────┐    RPUSH     ┌──────────────┐
│  Command  │ ─────────────────► │              │ ───────────► │ vacancy:queue│
│  Queue    │                    │  5 парсеров  │              │ (вакансии)   │
└──────────┘                    │  playwright  │              └──────────────┘
                                │  stealth     │    SADD      ┌──────────────┐
                                │              │ ───────────► │ vacancy:     │
                                └──────────────┘              │ processed    │
                                                              │ (дедуп)      │
                                                              └──────────────┘
```

## Структура проекта

```
src/
├── core/
│   ├── schema.py              # VacancyDTO
│   └── base/
│       ├── base_parser.py     # BaseVacancyParser
│       └── base_lifespan.py   # BaseLifecycle
├── domain/
│   ├── hh.py                  # HeadHunter
│   ├── habr.py                # Habr Career
│   ├── rabota.py              # Работа.ру
│   ├── superjob.py            # SuperJob
│   └── zarplata.py            # Зарплата.ру
├── app/
│   ├── container.py           # DI-контейнер
│   └── usecases/
│       └── parse_vacancies.py # Use case парсинга
├── infra/
│   ├── browser.py             # BrowserProvider (Playwright + stealth)
│   ├── cache.py               # CacheProvider (memory/redis)
│   └── logger.py              # Цветной логгер
├── transport/
│   ├── amqp/
│   │   ├── mq_provider.py     # Подключение к RabbitMQ
│   │   └── handler.py         # Обработчик сообщений
│   └── redis/
│       ├── vacancy_sink.py    # Запись вакансий (RPUSH)
│       └── status_flag.py     # Флаг состояния парсера
└── main.py                    # Точка входа
```

## Установка

```bash
# Клонировать
git clone https://github.com/AndreyChiz/rus_job_vacansy_parser.git
cd rus_job_vacansy_parser

# Установить зависимости
uv sync

# Установить Chromium
uv run python -m playwright install chromium
```

## Конфигурация

Скопируйте `.env.template` в `.env`:

```bash
cp .env.template .env
```

### Переменные окружения

| Переменная | Описание | По умолчанию |
|---|---|---|
| `LOG_LEVEL` | Уровень логирования | `INFO` |
| `RABBITMQ_URL` | URL подключения к RabbitMQ | `amqp://guest:guest@localhost:5672/` |
| `CACHE_TYPE` | Тип кеша (`redis` / `memory`) | `redis` |
| `CACHE_URL` | URL подключения к Redis | `redis://localhost:6379/0` |
| `PARALLEL_WORKERS` | Количество параллельных воркеров | `4` |
| `CARDS_PARSE_LIMIT` | Лимит карточек на парсер | `10` |
| `BROWSER_TYPE` | Тип браузера (`chromium` / `firefox` / `webkit`) | `chromium` |

## Запуск

### Локально

```bash
# Убедитесь что Redis и RabbitMQ запущены
uv run python src/main.py
```

### Docker

```bash
# Собрать образ
docker build -t parser_service .

# Запустить (с доступом к Redis/RabbitMQ на хосте)
docker run --network host --env-file .env parser_service
```

### Docker Compose

```bash
docker compose up --build -d
```

## Использование

### Формат команды в RabbitMQ

**Exchange:** `vacancy.exchange` (direct)
**Routing Key:** `vacancy.parse`
**Queue:** `vacancy.parse.request`

```json
{
    "command": "parse_vacancies",
    "hosts": ["hh.ru", "career.habr.com"],
    "query": "Python"
}
```

| Поле | Описание | Обязательно |
|---|---|---|
| `command` | Команда (всегда `parse_vacancies`) | Да |
| `hosts` | Список хостов (все если пусто) | Нет |
| `query` | Ключевое слово для поиска | Нет |

### Отправка команды

```bash
# Через curl
curl -u the_great_me:supper_secret -X POST \
  http://localhost:15672/api/exchanges/%2F/vacancy.exchange/publish \
  -H "content-type: application/json" \
  -d '{"routing_key":"vacancy.parse","payload":"{\"command\":\"parse_vacancies\",\"hosts\":[\"hh.ru\"],\"query\":\"Python\"}","payload_encoding":"string"}'

# Через RabbitMQ Management UI
# http://localhost:15672 → Exchanges → vacancy.exchange → Publish message
```

### Поддерживаемые сайты

| Хост | Сайт |
|---|---|
| `hh.ru` | HeadHunter |
| `career.habr.com` | Habr Career |
| `www.rabota.ru` | Работа.ру |
| `russia.superjob.ru` | SuperJob |
| `zarplata.ru` | Зарплата.ру |

### Формат вакансии в Redis

**Key:** `vacancy:queue` (List)

```json
{
    "vacancy_id": "1000167371",
    "url": "https://career.habr.com/vacancies/1000167371",
    "host": "career.habr.com",
    "title": "Ведущий разработчик Java",
    "employer": "МТС Финтех",
    "salary": null,
    "experience": null,
    "description": "..."
}
```

## Redis ключи

| Ключ | Тип | Описание |
|---|---|---|
| `vacancy:queue` | List | Очередь готовых вакансий (RPUSH) |
| `vacancy:processed` | Set | Множество обработанных ID (дедупликация) |
| `vacancy:parser:running` | String | Флаг состояния (`1` = работает) |

## Тестирование

```bash
# Все тесты
uv run pytest tests/ -v

# Только unit-тесты
uv run pytest tests/test_parsers.py -v

# Только интеграционные
uv run pytest tests/test_parsers_integration.py -v
```

## Зависимости

- Python >= 3.12
- [Playwright](https://playwright.dev/python/) — парсинг страниц
- [playwright-stealth](https://github.com/Mattwmaster58/playwright_stealth) — обход детекции
- [aio-pika](https://github.com/mosquito/aio-pika) — RabbitMQ
- [redis](https://github.com/redis/redis-py) — Redis
- [Pydantic](https://docs.pydantic.dev/) — валидация данных

## Лицензия

MIT
