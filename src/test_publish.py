import asyncio
import json
from datetime import datetime, timezone

import aio_pika
import redis.asyncio as aioredis

RABBITMQ_URL = "amqp://the_great_me:supper_secret@localhost:5672/"
REDIS_URL = "redis://:supper_secret@localhost:6379/0"

EXCHANGE = "vacancy.exchange"
ROUTING_KEY = "vacancy.parse"
QUEUE = "vacancy.parse.request"


async def main():
    print("[1] Подключение к RabbitMQ...")
    mq = await aio_pika.connect_robust(RABBITMQ_URL)
    channel = await mq.channel()

    exchange = await channel.declare_exchange(EXCHANGE, aio_pika.ExchangeType.DIRECT)
    queue = await channel.declare_queue(QUEUE, durable=True)
    await queue.bind(exchange, routing_key=ROUTING_KEY)

    message_body = json.dumps({
        "command": "parse_vacancies",
        "hosts": ["hh.ru", "career.habr.com"],
        "query": "Python",
    })

    await exchange.publish(
        aio_pika.Message(body=message_body.encode()),
        routing_key=ROUTING_KEY,
    )
    print(f"[✓] Сообщение отправлено в {EXCHANGE}/{ROUTING_KEY}")
    print(f"    Тело: {message_body}")

    print("\n[2] Ожидание вакансий в Redis...")
    r = aioredis.from_url(REDIS_URL, decode_responses=True)

    try:
        for i in range(60):
            length = await r.llen("vacancy:queue")
            lock = await r.get("vacancy:parser:running")
            print(f"  [{i*2}s] vacancy:queue = {length}, parser_running = {lock}")

            if length > 0:
                items = await r.lrange("vacancy:queue", 0, -1)
                print(f"\n[✓] Получено {length} вакансий:")
                for idx, item in enumerate(items, 1):
                    vacancy = json.loads(item)
                    print(f"\n  --- Вакансия #{idx} ---")
                    print(f"  ID:    {vacancy.get('vacancy_id')}")
                    print(f"  Host:  {vacancy.get('host')}")
                    print(f"  Title: {vacancy.get('title')}")
                    print(f"  URL:   {vacancy.get('url')}")
                break

            await asyncio.sleep(2)
        else:
            print("\n[✗] Таймаут: вакансии не появились за 120 секунд")
    finally:
        await mq.close()
        await r.aclose()


if __name__ == "__main__":
    asyncio.run(main())
