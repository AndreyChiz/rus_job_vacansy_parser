# Parser Service

Сервис парсинга вакансий с российских job-сайтов. Получает команды через RabbitMQ, парсит вакансии, публикует результат в Redis.

## Архитектура

```
                    Agent
                      │
                      │ get_new_vacancy()
                      ▼
                mcp_service
                 │       │
      LPOP       │       │ Publish
                 │       ▼
              Redis     RabbitMQ
                 ▲          │
                 │          ▼
             RPUSH     parser_service
```

### Слои

```
src/
├── core/                  # Доменные сущности и абстракции
│   ├── schema.py          # VacancyDTO
│   └── base/              # Абстрактные базовые классы
├── domain/                # Парсеры сайтов
│   ├── hh.py
│   ├── habr.py
│   ├── rabota.py
│   ├── superjob.py
│   └── zarplata.py
├── app/                   # Бизнес-логика
│   ├── container.py       # DI-контейнер
│   └── usecases/
│       └── parse_vacancies.py
├── infra/                 # Инфраструктура
│   ├── cache.py           # CacheProvider (memory/redis)
│   ├── browser.py         # BrowserProvider (Playwright)
│   └── logger.py
├── transport/             # Внешние интерфейсы
│   ├── amqp/              # RabbitMQ
│   │   ├── mq_provider.py
│   │   └── handler.py
│   └── redis/             # Redis (вывод)
│       ├── status_flag.py
│       └── vacancy_sink.py
├── main.py                # Точка входа
└── test_publish.py        # Тестовый скрипт
```

## Установка

### Через uv (рекомендуется)

```bash
cd parser_service
uv sync
```

### Через pip

```bash
pip install -e .
```

### Установка Playwright

```bash
python -m playwright install chromium
```

## Конфигурация

Создайте `.env` файл на основе `.env.template`:

```bash
cp .env.template .env
```

### Переменные окружения

| Переменная | Описание | По умолчанию |
|---|---|---|
| `JOB_HUNTER__HOST` | Хост Redis | `dev.loc` |
| `JOB_HUNTER__RABBITMQ_URL` | URL RabbitMQ | `amqp://guest:guest@localhost:5672/` |
| `JOB_HUNTER__REDIS__PASSWORD` | Пароль Redis | - |
| `JOB_HUNTER__PARSER_SERVICE__CACHE_TYPE` | Тип кеша (`redis`/`memory`) | `redis` |
| `JOB_HUNTER__PARSER_SERVICE__CACHE_URL` | URL Redis | `redis://:password@host:6379/0` |
| `JOB_HUNTER__PARSER_SERVICE__QUERY_WORDS` | Ключевые слова для поиска | - |
| `JOB_HUNTER__PARSER_SERVICE__PARALLEL_WORKERS` | Количество параллельных воркеров | `4` |
| `JOB_HUNTER__PARSER_SERVICE__CARDS_PARSE_LIMIT` | Лимит карточек на парсер | `10` |
| `JOB_HUNTER__PARSER_SERVICE__PARSE_TIMEOUT_S` | Таймаут парсинга (сек) | `60` |

## Запуск

### Локально

```bash
cd src
python main.py
```

### Через Docker Compose

```bash
docker compose up -d
```

Запустит Redis + RabbitMQ + парсер.

## Использование

### Формат сообщения в RabbitMQ

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
| `hosts` | Список хостов для парсинга (все если не указано) | Нет |
| `query` | Ключевое слово для поиска | Нет |

### Поддерживаемые сайты

| Хост | Сайт |
|---|---|
| `hh.ru` | HeadHunter |
| `career.habr.com` | Habr Career |
| `www.rabota.ru` | Работа.ру |
| `russia.superjob.ru` | SuperJob |
| `zarplata.ru` | Зарплата.ру |

### Формат вакансии в Redis

**Queue:** `vacancy:queue` (List)

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

## Тестирование

### Тестовый скрипт

```bash
cd src
python test_publish.py
```

Отправит команду в RabbitMQ и покажет результат из Redis.

### Вручную через RabbitMQ Management

1. Откройте `http://localhost:15672`
2. Логин: `the_great_me`, пароль: `supper_secret`
3. Перейдите в **Exchanges** → `vacancy.exchange`
4. В поле **Routing Key** введите `vacancy.parse`
5. В поле **Payload** вставьте JSON сообщение
6. Нажмите **Publish message**

### через curl

```bash
curl -u the_great_me:supper_secret -X POST \
  http://localhost:15672/api/exchanges/%2F/vacancy.exchange/publish \
  -H "content-type: application/json" \
  -d '{"routing_key":"vacancy.parse","payload":"{\"command\":\"parse_vacancies\",\"hosts\":[\"hh.ru\"],\"query\":\"Python\"}","payload_encoding":"string"}'
```

## Redis ключи

| Ключ | Тип | Описание |
|---|---|---|
| `vacancy:queue` | List | Очередь готовых вакансий |
| `vacancy:processed` | Set | Множество обработанных ID (дедупликация) |
| `vacancy:parser:running` | String | Флаг запуска парсера (`1` = работает) |

## Зависимости

- Python >= 3.12
- aio-pika (RabbitMQ)
- redis (Redis)
- playwright (браузер)
- pydantic (схемы данных)
