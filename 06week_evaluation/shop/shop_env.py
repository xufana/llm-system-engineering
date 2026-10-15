"""Мок-магазин для семинара по оцениванию агентов.

Среда та же, что на стенде лекции «Трасса → граф», плюс два заказа и сбои инструментов.
Модель не нужна: трасса — это список шагов {"tool", "arg"}, среда переигрывает её заново
и считает конечное состояние, а по эталонному графу задачи — метрики траектории.
"""
import copy
import json
from math import comb
from pathlib import Path

RETURN_WINDOW_DAYS = 14

ORDERS0 = {
    1042: {"status": "доставлен", "sum": 2340, "delivered_days_ago": 3},
    1043: {"status": "в пути", "sum": 1120},
    1044: {"status": "собирается", "sum": 860},
    1045: {"status": "доставлен", "sum": 5490, "delivered_days_ago": 21},
    1046: {"status": "доставлен", "sum": 1750, "delivered_days_ago": 6},
}


class ToolError(Exception):
    pass


def fresh_state():
    return {"orders": copy.deepcopy(ORDERS0), "returns": [], "finished": False, "final": None}


# ---------- инструменты ----------

def _order(s, order_id):
    o = s["orders"].get(order_id)
    if o is None:
        raise ToolError(f"заказ {order_id} не найден")
    return o


def get_order(s, order_id):
    o = _order(s, order_id)
    out = f"заказ {order_id}: статус «{o['status']}», сумма {o['sum']} ₽"
    if "delivered_days_ago" in o:
        out += f", доставлен {o['delivered_days_ago']} дн. назад"
    return out


def create_return(s, order_id):
    o = _order(s, order_id)
    if o["status"] != "доставлен":
        raise ToolError("возврат возможен только для доставленных заказов")
    if o["delivered_days_ago"] > RETURN_WINDOW_DAYS:
        raise ToolError(f"срок возврата {RETURN_WINDOW_DAYS} дней истёк")
    if order_id not in s["returns"]:
        s["returns"].append(order_id)
    return f"возврат по заказу {order_id} создан"


def cancel_order(s, order_id):
    o = _order(s, order_id)
    if o["status"] != "собирается":
        raise ToolError("заказ уже отправлен, отмена невозможна")
    o["status"] = "отменён"
    return f"заказ {order_id} отменён"


def finish(s, text):
    s["finished"] = True
    s["final"] = text
    return "диалог завершён"


TOOLS = {"get_order": get_order, "create_return": create_return,
         "cancel_order": cancel_order, "finish": finish}


def key(step):
    """Узел графа: инструмент с аргументом. Текст финального ответа в узел не входит."""
    return "finish" if step["tool"] == "finish" else f"{step['tool']}({step['arg']})"


# ---------- исполнение трассы ----------

def replay(task, steps):
    """Переигрывает трассу в свежей среде с учётом сбоев из задачи.

    Возвращает (state, log): log — по записи на шаг с наблюдением, флагом ошибки
    и флагом «состояние изменилось».
    """
    s = fresh_state()
    faults = {f["call"]: dict(f) for f in task.get("faults", [])}
    log = []
    for i, st in enumerate(steps[: task["step_budget"]], 1):
        k = key(st)
        before = json.dumps([s["orders"], s["returns"]], sort_keys=True)
        try:
            f = faults.get(k)
            if f and f["times"] > 0:
                f["times"] -= 1
                raise ToolError(f["error"])
            obs, err = TOOLS[st["tool"]](s, st["arg"]), False
        except ToolError as e:
            obs, err = f"ошибка: {e}", True
        changed = json.dumps([s["orders"], s["returns"]], sort_keys=True) != before
        log.append({"i": i, "key": k, "obs": obs, "error": err, "changed": changed})
        if st["tool"] == "finish":
            break
    return s, log


def expected_state(task):
    s = fresh_state()
    for oid, status in task["expect"].get("status", {}).items():
        s["orders"][int(oid)]["status"] = status
    s["returns"] = sorted(task["expect"].get("returns", []))
    return s


def check_state(task, state):
    """Детерминированная проверка: состояние среды совпало с эталонным целиком."""
    exp = expected_state(task)
    return state["orders"] == exp["orders"] and sorted(state["returns"]) == exp["returns"]


def check_mentions(task, state):
    """Детерминированная проверка текста: в финальном ответе есть каждая группа ключевых слов
    (внутри группы — хотя бы одно). Дёшево и грубо: проверяет наличие, а не правильность."""
    text = (state["final"] or "").lower()
    return all(any(w.lower() in text for w in group) for group in task.get("final_mentions", []))


def task_success(task, steps):
    state, _ = replay(task, steps)
    return check_state(task, state) and state["finished"] and check_mentions(task, state)


# ---------- метрики траектории ----------

def _f1(p, r):
    return 2 * p * r / (p + r) if p + r else 0.0


def graph_metrics(task, steps):
    g = task["golden"]
    required = set(g["nodes"]) - set(g.get("optional", []))
    allowed = set(g["nodes"])
    _, log = replay(task, steps)
    keys = [r["key"] for r in log]
    seen = set(keys)

    # узлы — множества, без учёта повторов
    tp = len(seen & allowed)
    node_p = tp / len(seen) if seen else 0.0
    node_r = len(seen & required) / len(required)

    # зависимости эталона: ребро u→v выполнено, если первый u стоит раньше первого v
    first = {}
    for i, k in enumerate(keys):
        first.setdefault(k, i)
    deps = g.get("edges", [])
    dep_ok = sum(1 for u, v in deps if u in first and v in first and first[u] < first[v])
    dep_recall = dep_ok / len(deps) if deps else 1.0

    # наивное сравнение соседних пар, как на стенде лекции: штрафует допустимый другой порядок
    pairs = lambda seq: {(a, b) for a, b in zip(seq, seq[1:])}
    gold_seq, tr_pairs = pairs(task["golden_path"]), pairs(keys)
    if not gold_seq:  # эталон из одного узла: пар нет, сравнивать нечего
        sp = sr = 1.0 if not tr_pairs else 0.0
    else:
        sp = len(gold_seq & tr_pairs) / len(tr_pairs) if tr_pairs else 0.0
        sr = len(gold_seq & tr_pairs) / len(gold_seq)

    # цикл — повтор успешного вызова, после которого состояние не менялось
    cycles, last_ok = 0, {}
    for r in log:
        if r["key"] in last_ok and not r["error"]:
            cycles += 1
        if not r["error"]:
            last_ok[r["key"]] = r["i"]

    return {
        "node_f1": _f1(node_p, node_r),
        "extra_nodes": sorted(seen - allowed),
        "missing_nodes": sorted(required - seen),
        "dep_recall": dep_recall,
        "seq_edge_f1": _f1(sp, sr),
        "efficiency": task.get("min_steps", len(required)) / len(keys) if keys else 0.0,
        "cycles": cycles,
        "divergence": divergence(task, log),
    }


def divergence(task, log):
    """Первый шаг, где трасса ушла от эталона: (номер шага, причина) или None.

    Допустимый следующий шаг — узел эталона, все предшественники которого уже выполнены.
    Повтор после ошибки инструмента — ретрай, а не расхождение.
    """
    g = task["golden"]
    preds = {n: {u for u, v in g.get("edges", []) if v == n} for n in g["nodes"]}
    done, failed = set(), set()
    for r in log:
        k = r["key"]
        if k not in preds:
            return r["i"], f"лишний узел {k}"
        if k in done and k not in failed:
            return r["i"], f"повтор {k}"
        missing = preds[k] - done
        if missing:
            return r["i"], f"не по порядку: эталон ждёт {', '.join(sorted(missing))}"
        done.add(k)
        (failed.add if r["error"] else failed.discard)(k)
    left = set(g["nodes"]) - set(g.get("optional", [])) - done
    if left:
        return len(log) + 1, f"пропущен узел {', '.join(sorted(left))}"
    return None


# ---------- надёжность ----------

def pass_at_k(n, c, k):
    """Хотя бы одна из k попыток успешна (несмещённая оценка по n прогонам, c успешных)."""
    return 1.0 - comb(n - c, k) / comb(n, k)


def pass_hat_k(n, c, k):
    """Все k попыток успешны — pass^k из τ-bench (оценка по n прогонам, c успешных)."""
    return comb(c, k) / comb(n, k)


# ---------- данные ----------

HERE = Path(__file__).parent


def load_jsonl(name):
    with open(HERE / name, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def load_tasks():
    return {t["task_id"]: t for t in load_jsonl("tasks.jsonl")}


def load_traces():
    return load_jsonl("traces.jsonl")
