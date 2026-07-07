#!/usr/bin/env python3
import asyncio
import json
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

import aio_pika
import redis.asyncio as aioredis

RABBITMQ_URL = "amqp://the_great_me:supper_secret@localhost:5672/"
REDIS_URL = "redis://:supper_secret@localhost:6379/0"

EXCHANGE = "vacancy.exchange"
ROUTING_KEY = "vacancy.parse"
QUEUE = "vacancy.parse.request"


async def send_parse_command(hosts: list, query: str):
    mq = await aio_pika.connect_robust(RABBITMQ_URL)
    channel = await mq.channel()
    exchange = await channel.declare_exchange(EXCHANGE, aio_pika.ExchangeType.DIRECT)
    queue = await channel.declare_queue(QUEUE, durable=True)
    await queue.bind(exchange, routing_key=ROUTING_KEY)

    message_body = json.dumps({
        "command": "parse_vacancies",
        "hosts": hosts,
        "query": query,
    })

    await exchange.publish(
        aio_pika.Message(body=message_body.encode()),
        routing_key=ROUTING_KEY,
    )
    print(f"[✓] Отправлено: hosts={hosts}, query={query}")
    await mq.close()


async def wait_and_collect_results(timeout_s=180):
    r = aioredis.from_url(REDIS_URL, decode_responses=True)

    try:
        await r.delete("vacancy:queue")

        for i in range(timeout_s):
            length = await r.llen("vacancy:queue")
            lock = await r.get("vacancy:parser:running")

            if length > 0 and lock is None:
                await asyncio.sleep(1)
                length = await r.llen("vacancy:queue")
                if await r.get("vacancy:parser:running") is None:
                    items = await r.lrange("vacancy:queue", 0, -1)
                    await r.delete("vacancy:queue")
                    return [json.loads(item) for item in items]

            if i % 10 == 0:
                print(f"  [{i}s] queue={length}, running={lock is not None}")

            await asyncio.sleep(1)

        print("[!] Таймаут")
        items = await r.lrange("vacancy:queue", 0, -1)
        await r.delete("vacancy:queue")
        return [json.loads(item) for item in items] if items else []

    finally:
        await r.aclose()


def validate_vacancy(v: dict, test_name: str) -> list:
    errors = []
    required = ["vacancy_id", "url", "host", "title"]
    for field in required:
        if not v.get(field):
            errors.append(f"  {test_name}: missing {field}={v.get(field)}")

    url = v.get("url", "")
    host = v.get("host", "")
    vid = v.get("vacancy_id", "")

    if host == "hh.ru":
        if "/vacancy/" not in url:
            errors.append(f"  {test_name}: hh.ru URL missing /vacancy/: {url}")
        url_id = url.split("/vacancy/")[-1].split("?")[0]
        if url_id != vid:
            errors.append(f"  {test_name}: hh.ru ID mismatch: url={url_id}, field={vid}")

    elif host == "career.habr.com":
        if "/vacancies/" not in url:
            errors.append(f"  {test_name}: habr URL missing /vacancies/: {url}")
        url_id = url.split("/")[-1].split("?")[0]
        if url_id != vid:
            errors.append(f"  {test_name}: habr ID mismatch: url={url_id}, field={vid}")

    elif host == "www.rabota.ru":
        if "/vacancy/" not in url:
            errors.append(f"  {test_name}: rabota URL missing /vacancy/: {url}")

    elif host == "russia.superjob.ru":
        if "/vakansii/" not in url:
            errors.append(f"  {test_name}: superjob URL missing /vakansii/: {url}")

    elif host == "zarplata.ru":
        if "/vacancy/" not in url:
            errors.append(f"  {test_name}: zarplata URL missing /vacancy/: {url}")

    return errors


def print_results(vacancies: list, test_name: str):
    print(f"\n{'='*60}")
    print(f"  {test_name}: {len(vacancies)} вакансий")
    print(f"{'='*60}")

    all_errors = []
    hosts = {}
    for v in vacancies:
        host = v.get("host", "unknown")
        hosts[host] = hosts.get(host, 0) + 1
        errs = validate_vacancy(v, test_name)
        all_errors.extend(errs)

    for h, c in sorted(hosts.items()):
        print(f"  {h}: {c}")

    if all_errors:
        print(f"\n  [!] ОШИБКИ ({len(all_errors)}):")
        for e in all_errors:
            print(e)
    else:
        print(f"  [✓] Все ID корректны")

    for i, v in enumerate(vacancies[:3], 1):
        print(f"\n  --- #{i} ---")
        print(f"  ID:     {v.get('vacancy_id')}")
        print(f"  Host:   {v.get('host')}")
        print(f"  Title:  {v.get('title', '')[:50]}")
        print(f"  URL:    {v.get('url', '')[:80]}")
        print(f"  Salary: {v.get('salary', 'N/A')}")
        print(f"  Employer: {v.get('employer', 'N/A')}")


async def test_single(host: str, query: str):
    await send_parse_command([host], query)
    results = await wait_and_collect_results(timeout_s=120)
    print_results(results, f"Один парсер: {host}")
    return results


async def test_pair(host1: str, host2: str, query: str):
    await send_parse_command([host1, host2], query)
    results = await wait_and_collect_results(timeout_s=120)
    print_results(results, f"Два парсера: {host1} + {host2}")
    return results


async def test_all(query: str):
    await send_parse_command([], query)
    results = await wait_and_collect_results(timeout_s=180)
    print_results(results, "Все парсеры")
    return results


async def main():
    query = "Python"

    tests = [
        ("hh.ru", ),
        ("career.habr.com", ),
        ("www.rabota.ru", ),
        ("russia.superjob.ru", ),
        ("zarplata.ru", ),
    ]

    print("\n" + "="*60)
    print("  ТЕСТ 1: Каждый парсер по отдельности")
    print("="*60)

    all_ok = True
    for host in tests:
        results = await test_single(host[0], query)
        if not results:
            print(f"  [✗] {host[0]} вернул 0 вакансий")
            all_ok = False

    print("\n" + "="*60)
    print("  ТЕСТ 2: Пары парсеров")
    print("="*60)

    await test_pair("hh.ru", "career.habr.com", query)
    await test_pair("russia.superjob.ru", "zarplata.ru", query)

    print("\n" + "="*60)
    print("  ТЕСТ 3: Все парсеры вместе")
    print("="*60)

    results = await test_all(query)

    print("\n" + "="*60)
    print("  ИТОГИ")
    print("="*60)

    hosts_found = set(v.get("host") for v in results)
    expected = {"hh.ru", "career.habr.com", "www.rabota.ru", "russia.superjob.ru", "zarplata.ru"}
    missing = expected - hosts_found

    if missing:
        print(f"  [✗] Отсутствуют: {missing}")
    else:
        print(f"  [✓] Все 5 парсеров вернули результаты")

    print(f"  Всего вакансий: {len(results)}")


if __name__ == "__main__":
    asyncio.run(main())
