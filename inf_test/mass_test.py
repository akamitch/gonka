"""
Массовый стресс-тест Gonka inference API. Настройки — в config.ini рядом со скриптом.
"""

from __future__ import annotations

import configparser
import random
import re
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from pathlib import Path

from openai import APIStatusError, OpenAIError

from gonka_openai import GonkaOpenAI
from gonka_openai.utils import Endpoint, resolve_endpoints

# --- Словари по 50 слов (рус.) для рандомизации промптов ---

VERBS = [
    "бежит", "шепчет", "тает", "мечтает", "крутится", "падает", "растёт", "спорит",
    "танцует", "прячется", "льётся", "рвётся", "жужжит", "трещит", "молчит", "кричит",
    "пишет", "читает", "ломает", "чинит", "крадёт", "дарит", "жрёт", "спит",
    "летит", "ползёт", "ныряет", "взлетает", "исчезает", "появляется", "тараторит",
    "думает", "сомневается", "верит", "врёт", "строит", "рушит", "жарит", "варит",
    "печёт", "моет", "гладит", "щиплет", "щёлкает", "щурится", "вздыхает", "смеётся",
    "плачет", "зевает", "залипает", "тормозит", "разгоняется",
]

NOUNS = [
    "шкаф", "нейтрино", "борщ", "квант", "ёж", "трамвай", "облако", "компас",
    "пылесос", "сатурн", "гвоздь", "суп", "кот", "робот", "гриб", "радуга",
    "пингвин", "чайник", "носок", "барабан", "кирпич", "мёд", "лёд", "песок",
    "зонт", "кнопка", "провод", "магнит", "лампа", "зеркало", "ключ", "замок",
    "чемодан", "рюкзак", "карандаш", "ластик", "скрепка", "папка", "степлер",
    "кружка", "тарелка", "вилка", "ложка", "кастрюля", "сковорода", "печенье",
    "пирог", "варенье", "огурец", "помидор", "редиска", "капуста", "тыква",
    "арбуз", "дыня", "гранат", "ананас",
]

ADJECTIVES = [
    "липкий", "древний", "злой", "мягкий", "острый", "туманный", "стальной",
    "деревянный", "резиновый", "стеклянный", "пушистый", "колючий", "мокрый",
    "сухой", "горячий", "холодный", "длинный", "короткий", "толстый", "тонкий",
    "быстрый", "медленный", "тихий", "громкий", "яркий", "тусклый", "чистый",
    "грязный", "пустой", "полный", "странный", "обычный", "редкий", "частый",
    "дорогой", "дёшевый", "новый", "старый", "молодой", "усталый", "бодрый",
    "сонный", "весёлый", "грустный", "злорадный", "наивный", "хитрый", "простой",
    "сложный", "кривой", "ровный", "косой", "прямой", "круглый", "квадратный",
    "плоский", "объёмный", "лёгкий", "тяжёлый",
]

ADVERBS = [
    "медленно", "быстро", "вдруг", "тихо", "громко", "ежедневно", "наскоком",
    "наизнанку", "врозь", "втихаря", "нараспашку", "наотмашь", "внаглую",
    "вполголоса", "наизусть", "наугад", "наперекор", "вовсю", "вполсилы",
    "вполоборота", "вдогонку", "вперемешку", "внакидку", "вразброс", "вразвал",
    "вразнобой", "вразрез", "вразумительно", "наспех", "наскоро", "наотрез",
    "наотлету", "вертикально", "горизонтально", "диагонально", "зигзагом", "кругами",
    "змейкой", "прыжками", "шагом", "бегом", "ползком", "вприпрыжку", "вразвалочку",
    "на цыпочках", "вполный рост", "вполсне", "наискосок", "наперевес", "навеселе",
    "набегу", "напролёт", "наотмашь", "внакладе", "внагрузку", "внахлёст",
]

PLACES = [
    "в подвале", "на крыше", "в лифте", "на Марсе", "у остановки", "в интернете",
    "в холодильнике", "под диваном", "в ванной", "на кухне", "в коридоре",
    "на чердаке", "в сарае", "в лесу", "в пустыне", "на острове", "в метро",
    "в автобусе", "в такси", "на вокзале", "в аэропорту", "в библиотеке",
    "в музее", "в театре", "в кино", "на стадионе", "в бассейне", "в океане",
    "на реке", "у пруда", "в гараже", "на парковке", "в офисе", "в школе",
    "в университете", "в лаборатории", "в цеху", "на ферме", "в амбаре",
    "в сеновал", "в погребе", "на балконе", "в лоджии", "в шкафу", "в коробке",
    "в пакете", "в сумке", "в кармане", "в рюкзаке", "в чемодане", "в сейфе",
    "в облаке", "на сервере", "в кэше", "в буфере", "в очереди", "в стеке",
]

# Доп. существительные / «предметы абсурда» для пятого слота или второго существительного
NOUNS_EXTRA = [
    "миф", "закон", "парадокс", "теорема", "ошибка", "баг", "патч", "релиз",
    "деплой", "лог", "дамп", "хэш", "ключ", "соль", "перец", "соус", "бульон",
    "каша", "клякса", "пятно", "дыра", "узел", "петля", "узелок", "бантик",
    "бант", "схема", "чертёж", "эскиз", "набросок", "скетч", "ребус", "загадка",
    "мем", "шутка", "анекдот", "байка", "легенда", "слух", "сплетня", "новость",
    "сенсация", "скандал", "тайна", "головоломка", "лабиринт", "ловушка", "капкан",
    "сеть", "паутина", "нить", "верёвка", "канат", "трос", "цепь", "замок",
    "скоба", "скрепка", "болт", "гайка", "шайба", "шуруп", "гвоздь", "дюбель",
    "клей", "скотч", "изолента", "проволока", "пружина", "шестерня", "винт",
]

# Ровно по 50 слов в каждом пуле (лишнее отбрасываем для предсказуемого размера).
VERBS = VERBS[:50]
NOUNS = NOUNS[:50]
ADJECTIVES = ADJECTIVES[:50]
ADVERBS = ADVERBS[:50]
PLACES = PLACES[:50]
NOUNS_EXTRA = NOUNS_EXTRA[:50]

# 100 шаблонов: 20 вступлений × 5 тел; в каждом теле ровно 5 плейсхолдеров
# v — глагол, n — сущ., a — прилаг., d — наречие, p — место, x — доп. сущ.

_QUESTION_INTROS = [
    "Почему",
    "Как одной фразой объяснить",
    "Объясни бабушке",
    "Смоделируй диалог где фигурируют",
    "Сочини миф о том что",
    "Заголовок жёлтой прессы:",
    "Одним абзацем опиши",
    "Сценарий короткометражки:",
    "Тост за то чтобы",
    "Рекламный слоган услуги",
    "Пункт из устава секты про",
    "Хорор начинается так:",
    "Шуточный SQL про",
    "Сказка на ночь про",
    "Лженаучная статья утверждает",
    "Переговоры зашли в тупик из-за",
    "Мем в двух словах про",
    "Твит-провокация про",
    "Философ спросил бы",
    "Странный сон:",
]

_QUESTION_BODIES = [
    "{a} {n} {v} {d} {p}",
    "{n} {v} {a} {p} {x}",
    "{x} {n} {v} {d} {p}",
    "{p} {a} {n} {v} {x}",
    "{a} {x} {n} {v} {d}",
]


def _build_question_templates() -> list[str]:
    return [f"{intro} {body}?" for intro in _QUESTION_INTROS for body in _QUESTION_BODIES]


QUESTION_TEMPLATES = _build_question_templates()

for _tpl in QUESTION_TEMPLATES:
    if len(re.findall(r"\{(\w+)\}", _tpl)) != 5:
        raise RuntimeError(f"шаблон должен иметь 5 плейсхолдеров: {_tpl!r}")


def _random_prompt() -> str:
    """Случайный вопрос: один из 100 шаблонов, 5 подстановок (только слова)."""
    t = random.choice(QUESTION_TEMPLATES)
    return t.format(
        v=random.choice(VERBS),
        n=random.choice(NOUNS),
        a=random.choice(ADJECTIVES),
        d=random.choice(ADVERBS),
        p=random.choice(PLACES),
        x=random.choice(NOUNS_EXTRA),
    )


def _script_dir() -> Path:
    return Path(__file__).resolve().parent


def load_config(path: Path | None = None) -> configparser.ConfigParser:
    cfg_path = path or (_script_dir() / "config.ini")
    if not cfg_path.is_file():
        print(f"Файл конфигурации не найден: {cfg_path}", file=sys.stderr)
        sys.exit(1)
    p = configparser.ConfigParser()
    p.read(cfg_path, encoding="utf-8")
    return p


def _normalize_private_key(raw: str) -> str:
    s = raw.strip()
    if s.lower().startswith("0x"):
        s = s[2:]
    return s


def _first_source_url(raw: str) -> str:
    for part in raw.replace("\n", ",").split(","):
        u = part.strip()
        if u:
            return u
    raise ValueError("source_urls пусто")


@dataclass
class Stats:
    lock: threading.Lock = field(default_factory=threading.Lock)
    ok: int = 0
    err_429: int = 0
    err_5xx: int = 0
    err_other: int = 0
    total_latency_s: float = 0.0

    def add(self, *, ok: bool, status: int | None, latency_s: float) -> None:
        with self.lock:
            self.total_latency_s += latency_s
            if ok:
                self.ok += 1
            elif status == 429:
                self.err_429 += 1
            elif status is not None and 500 <= status <= 599:
                self.err_5xx += 1
            else:
                self.err_other += 1


_print_lock = threading.Lock()


def _safe_print(msg: str) -> None:
    with _print_lock:
        print(msg, flush=True)


def _extract_assistant_text(resp) -> str:
    """Текст ответа ассистента: content, иначе refusal/tool_calls, иначе пояснение."""
    if not resp.choices:
        return "(нет choices в ответе API)"
    ch = resp.choices[0]
    msg = ch.message
    parts: list[str] = []
    if msg.content:
        parts.append(msg.content)
    if getattr(msg, "refusal", None):
        parts.append(f"[отказ модели] {msg.refusal}")
    tcalls = getattr(msg, "tool_calls", None)
    if tcalls:
        parts.append(f"[tool_calls] {tcalls!r}")
    if not parts:
        try:
            dumped = msg.model_dump(exclude_none=True)
            for key, val in sorted(dumped.items()):
                if key in ("role", "content", "refusal", "tool_calls") or val in (None, "", []):
                    continue
                if isinstance(val, str) and val.strip():
                    parts.append(f"[{key}] {val}")
                elif isinstance(val, list) and val:
                    parts.append(f"[{key}] {val!r}")
        except Exception:
            pass
    if parts:
        return "\n".join(parts).strip()
    fr = getattr(ch, "finish_reason", None)
    return f"(пустой content; finish_reason={fr!r})"


def run_one(
    client: GonkaOpenAI,
    model: str,
    max_tokens: int,
    delay_s: float,
    req_id: int,
    stats: Stats,
) -> None:
    if delay_s > 0:
        time.sleep(delay_s)
    user_content = _random_prompt()
    t0 = time.perf_counter()
    status: int | None = None
    ok = False
    body_preview = ""
    try:
        resp = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": user_content}],
            max_tokens=max_tokens,
        )
        ok = True
        content = _extract_assistant_text(resp)
        body_preview = content if len(content) <= 1200 else content[:1200] + "\n… [обрезано]"
    except APIStatusError as e:
        status = e.status_code
        body_preview = str(e.message)[:800]
    except OpenAIError as e:
        body_preview = str(e)[:800]
    except Exception as e:
        body_preview = f"{type(e).__name__}: {e}"[:800]
    latency = time.perf_counter() - t0
    stats.add(ok=ok, status=status, latency_s=latency)

    head = f"[#{req_id}] max_tokens={max_tokens} {latency:.2f}s "
    if ok:
        head += "OK"
    elif status is not None:
        head += f"HTTP {status}"
    else:
        head += "ERROR"
    _safe_print(f"{head}\n--- prompt ---\n{user_content}\n--- response ---\n{body_preview}\n{'='*60}")


def main() -> None:
    cfg_path = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else None
    cfg = load_config(cfg_path)
    g = cfg["gonka"]
    s = cfg["settings"]

    private_key = _normalize_private_key(g["private_key"])
    model = g["model"].strip()

    explicit_ep = g.get("endpoint", "").strip()
    if explicit_ep:
        endpoints_list: list[Endpoint] = [Endpoint.parse(explicit_ep)]
    else:
        source_url = _first_source_url(g.get("source_urls", g.get("source_url", "")))
        endpoints_list = resolve_endpoints(source_url=source_url, endpoints=None)
        if not endpoints_list:
            print(
                "Список эндпоинтов пуст (часто HTTP 404 на participants). "
                "Задайте в [gonka] явную строку endpoint = URL;gonka1… как в g.py.",
                file=sys.stderr,
            )
            sys.exit(1)

    def _first_endpoint_strategy(eps: list[Endpoint]) -> Endpoint:
        return eps[0]

    client = GonkaOpenAI(
        api_key="mock-api-key",
        gonka_private_key=private_key,
        endpoints=endpoints_list,
        endpoint_selection_strategy=_first_endpoint_strategy,
    )

    num_requests = s.getint("num_requests", fallback=10)
    delay_min = s.getfloat("delay_min", fallback=0.0)
    num_threads = max(1, s.getint("num_threads", fallback=1))
    max_tokens = max(16, s.getint("max_tokens", fallback=512))

    stats = Stats()
    wall0 = time.perf_counter()

    with ThreadPoolExecutor(max_workers=num_threads) as ex:
        futures = [
            ex.submit(run_one, client, model, max_tokens, delay_min, i + 1, stats)
            for i in range(num_requests)
        ]
        for fut in as_completed(futures):
            fut.result()

    wall = time.perf_counter() - wall0
    n = num_requests
    avg = stats.total_latency_s / n if n else 0.0

    print()
    print("========== ИТОГО ==========")
    print(f"Модель:             {model}")
    print(f"Всего запросов:     {n}")
    print(f"OK:                 {stats.ok}")
    print(f"HTTP 5xx:           {stats.err_5xx}")
    print(f"HTTP 429:           {stats.err_429}")
    print(f"Прочие ошибки:      {stats.err_other}")
    print(f"Общее время (стен): {wall:.2f} s")
    print(f"Сумма latency:      {stats.total_latency_s:.2f} s")
    print(f"Среднее latency:    {avg:.2f} s")


if __name__ == "__main__":
    main()
