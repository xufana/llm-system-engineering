"""Генерирует данные мок-магазина для семинара: задачи, трассы двух версий агента, готовые разметки.

Запуск: python3 make_shop_data.py → ../../shop/{tasks.jsonl, traces.jsonl, labels_premade.csv, labels_adjudicated.csv}

Что настоящее: среда, наблюдения инструментов и состояние — считаются replay() по шагам трассы.
Что сценарий: сами шаги и тексты агента (написаны руками под типовые ошибки), вердикты
«судьи по тексту» и три разметки аннотаторов (синтетические, с фиксированным seed).

v1 — базовый промпт. v2 — промпт «сначала проверь заказ, будь проактивен»: меньше ложных
отчётов, зато появляются побочные действия без запроса (T06) и ответы вне домена (T11).
"""
import csv
import json
import random
import sys
from pathlib import Path

OUT = Path(__file__).resolve().parents[2] / "shop"
sys.path.insert(0, str(OUT))
from shop_env import replay  # noqa: E402

RUNS = 5


def G(i): return {"tool": "get_order", "arg": i}
def R(i): return {"tool": "create_return", "arg": i}
def C(i): return {"tool": "cancel_order", "arg": i}
def F(t): return {"tool": "finish", "arg": t}


def chain(*nodes):
    return [[a, b] for a, b in zip(nodes, nodes[1:])]


# ---------- задачи: то, как выглядит размеченный эталон ----------

TASKS = [
    dict(task_id="T01", category="действие", split="visible",
         text="Оформите, пожалуйста, возврат по заказу 1042.",
         expect={"returns": [1042]}, final_mentions=[["возврат"]],
         golden={"nodes": ["get_order(1042)", "create_return(1042)", "finish"],
                 "edges": chain("get_order(1042)", "create_return(1042)", "finish")}),
    dict(task_id="T02", category="условие (выполнено)", split="visible",
         text="Отмените заказ 1044, если он ещё не отправлен.",
         expect={"status": {"1044": "отменён"}}, final_mentions=[["отмен"]],
         golden={"nodes": ["get_order(1044)", "cancel_order(1044)", "finish"],
                 "edges": chain("get_order(1044)", "cancel_order(1044)", "finish")}),
    dict(task_id="T03", category="условие (не выполнено)", split="visible",
         text="Если заказ 1043 уже доставлен — оформите возврат, иначе подскажите статус.",
         expect={}, final_mentions=[["в пути"]],
         golden={"nodes": ["get_order(1043)", "finish"], "edges": chain("get_order(1043)", "finish")}),
    dict(task_id="T04", category="информация", split="visible",
         text="Где сейчас мой заказ 1043?",
         expect={}, final_mentions=[["в пути"]],
         golden={"nodes": ["get_order(1043)", "finish"], "edges": chain("get_order(1043)", "finish")}),
    dict(task_id="T05", category="невозможное действие", split="visible",
         text="Хочу вернуть заказ 1045.",
         expect={}, final_mentions=[["14 дн", "14 календ", "двух недель"]],
         golden={"nodes": ["get_order(1045)", "finish"], "edges": chain("get_order(1045)", "finish")}),
    dict(task_id="T06", category="невозможное действие", split="visible",
         text="Отмените заказ 1042.",
         expect={}, final_mentions=[["доставлен"]],
         golden={"nodes": ["get_order(1042)", "finish"], "edges": chain("get_order(1042)", "finish")}),
    dict(task_id="T07", category="несколько действий", split="visible",
         text="Отмените 1044 и оформите возврат по 1042.",
         expect={"status": {"1044": "отменён"}, "returns": [1042]}, final_mentions=[["отмен"], ["возврат"]],
         golden={"nodes": ["get_order(1044)", "cancel_order(1044)", "get_order(1042)", "create_return(1042)", "finish"],
                 "edges": chain("get_order(1044)", "cancel_order(1044)", "finish")
                          + chain("get_order(1042)", "create_return(1042)", "finish")}),
    dict(task_id="T08", category="сбой инструмента", split="visible",
         text="Оформите возврат по заказу 1046.",
         expect={"returns": [1046]}, final_mentions=[["возврат"]],
         faults=[{"call": "get_order(1046)", "times": 1, "error": "таймаут сервиса заказов"}],
         min_steps=4,  # с одним ретраем
         golden={"nodes": ["get_order(1046)", "create_return(1046)", "finish"],
                 "edges": chain("get_order(1046)", "create_return(1046)", "finish")}),
    dict(task_id="T09", category="неоднозначный запрос", split="holdout",
         text="Отмените заказ, пожалуйста, он мне больше не нужен.",
         expect={}, final_mentions=[["номер"]],
         golden={"nodes": ["finish"], "edges": []}),
    dict(task_id="T10", category="ошибка во вводе", split="holdout",
         text="Какой статус у заказа 1099?",
         expect={}, final_mentions=[["не найден", "нет заказа", "не нашёл", "не нашел"]],
         golden={"nodes": ["get_order(1099)", "finish"], "edges": chain("get_order(1099)", "finish")}),
    dict(task_id="T11", category="вне домена", split="holdout",
         text="Посоветуйте ноутбук для учёбы до 60 тысяч.",
         expect={}, final_mentions=[["заказ"]],
         golden={"nodes": ["finish"], "edges": []}),
    dict(task_id="T12", category="информация (несколько)", split="visible",
         text="Какие статусы у заказов 1042 и 1043?",
         expect={}, final_mentions=[["доставлен"], ["в пути"]],
         golden={"nodes": ["get_order(1042)", "get_order(1043)", "finish"],
                 "edges": [["get_order(1042)", "finish"], ["get_order(1043)", "finish"]]}),
]

GOLDEN_PATH = {  # одна каноническая последовательность — только для наивной метрики соседних пар
    "T07": ["get_order(1044)", "cancel_order(1044)", "get_order(1042)", "create_return(1042)", "finish"],
    "T12": ["get_order(1042)", "get_order(1043)", "finish"],
}
for t in TASKS:
    t.setdefault("step_budget", 8)
    t["golden_path"] = GOLDEN_PATH.get(t["task_id"], t["golden"]["nodes"])


# ---------- поведение агента: варианты трасс ----------
# label = (outcome, first_error_step, error_category) — согласованная (adjudicated) разметка.
# alt — другие метки, которые разумный аннотатор может поставить на этот же случай.
# judge = (балл 1–5, обоснование) — «судья по тексту», видит только запрос и финальный ответ.
# looks_ok — финальный текст звучит как успешное выполнение.

OK_RET_1042 = "Возврат по заказу 1042 оформлен. Деньги вернутся на карту в течение 5 рабочих дней."

V = {
    "T01": {
        "ok": dict(steps=[G(1042), R(1042), F(OK_RET_1042)],
                   label=("success", None, "none"), judge=(5, "Подтверждает возврат и называет срок."), looks_ok=True),
        "false_claim": dict(steps=[G(1042), F("Возврат по заказу 1042 оформлен, деньги вернутся в течение 5 дней.")],
                            label=("fail", 2, "false_claim"), alt=[("fail", 2, "missing_step")],
                            judge=(5, "Ответ полный, вежливый, называет срок."), looks_ok=True),
        "no_check": dict(steps=[R(1042), F(OK_RET_1042)],
                         label=("success", 1, "missing_step"), alt=[("success", None, "none")],
                         judge=(5, "Подтверждает возврат и называет срок."), looks_ok=True),
    },
    "T02": {
        "ok": dict(steps=[G(1044), C(1044), F("Заказ 1044 ещё собирался — я его отменил. Деньги не списывались.")],
                   label=("success", None, "none"), judge=(5, "Учтено условие, отмена подтверждена."), looks_ok=True),
        "no_check": dict(steps=[C(1044), F("Заказ 1044 отменён.")],
                         label=("success", 1, "missing_step"), alt=[("success", None, "none")],
                         judge=(4, "Отмена подтверждена, но не сказано, проверялось ли условие."), looks_ok=True),
        "long_road": dict(steps=[G(1044), G(1043), G(1042), G(1044), C(1044),
                                 F("Заказ 1044 ещё собирался, отменил его.")],
                          label=("success", 2, "extra_steps"), alt=[("success", 4, "loop")],
                          judge=(5, "Учтено условие, отмена подтверждена."), looks_ok=True),
    },
    "T03": {
        "ok": dict(steps=[G(1043), F("Заказ 1043 ещё в пути, поэтому возврат пока оформить нельзя. Когда он будет доставлен, напишите — помогу с возвратом.")],
                   label=("success", None, "none"), judge=(5, "Статус сообщён, условие учтено."), looks_ok=True),
        "loop": dict(steps=[G(1043)] * 8,
                     label=("fail", 2, "loop"), alt=[("fail", 2, "extra_steps")],
                     judge=(1, "Финального ответа нет."), looks_ok=False),
        "try_return": dict(steps=[G(1043), R(1043), F("Заказ 1043 ещё в пути, возврат пока невозможен. Сообщу, когда он будет доставлен.")],
                           label=("success", 2, "wrong_action"), alt=[("success", 2, "extra_steps"), ("success", None, "none")],
                           judge=(5, "Статус сообщён верно, предложен следующий шаг."), looks_ok=True),
    },
    "T04": {
        "ok": dict(steps=[G(1043), F("Заказ 1043 в пути. Обычно доставка занимает ещё 1–3 дня.")],
                   label=("success", None, "none"), judge=(5, "Прямой ответ на вопрос."), looks_ok=True),
        "no_tool": dict(steps=[F("Ваш заказ 1043 в пути и скоро будет у вас.")],
                        label=("success", 1, "missing_step"), alt=[("success", None, "none"), ("partial", 1, "missing_step")],
                        judge=(5, "Прямой ответ на вопрос."), looks_ok=True),
        "wrong_info": dict(steps=[G(1043), F("Заказ 1043 уже доставлен в пункт выдачи.")],
                           label=("fail", 2, "wrong_info"), alt=[],
                           judge=(5, "Прямой ответ на вопрос."), looks_ok=True),
    },
    "T05": {
        "ok": dict(steps=[G(1045), F("Заказ 1045 доставлен 21 день назад, а вернуть товар можно в течение 14 дней. Оформить возврат не получится — могу передать обращение оператору.")],
                   label=("success", None, "none"), judge=(5, "Отказ объяснён, предложена альтернатива."), looks_ok=True),
        "try": dict(steps=[G(1045), R(1045), F("К сожалению, срок возврата 14 дней уже истёк, оформить возврат по заказу 1045 нельзя.")],
                    label=("success", 2, "wrong_action"), alt=[("success", 2, "extra_steps")],
                    judge=(4, "Отказ объяснён, альтернативы нет."), looks_ok=True),
        "false_after_err": dict(steps=[G(1045), R(1045), F("Возврат по заказу 1045 оформлен.")],
                                label=("fail", 3, "bad_error_handling"), alt=[("fail", 3, "false_claim"), ("fail", 2, "wrong_action")],
                                judge=(4, "Подтверждает возврат, но без срока."), looks_ok=True),
    },
    "T06": {
        "ok": dict(steps=[G(1042), F("Заказ 1042 уже доставлен, отменить его нельзя. Если товар не нужен, могу оформить возврат.")],
                   label=("success", None, "none"), judge=(5, "Отказ объяснён, предложен возврат."), looks_ok=True),
        "overstep": dict(steps=[G(1042), R(1042), F("Заказ 1042 уже доставлен, поэтому вместо отмены я оформил возврат — деньги придут за 5 дней.")],
                         label=("fail", 2, "unrequested_side_effect"), alt=[("fail", 2, "wrong_action")],
                         judge=(5, "Проактивно решил проблему клиента."), looks_ok=True),
        "try_cancel": dict(steps=[G(1042), C(1042), F("Заказ 1042 уже доставлен, отменить его нельзя.")],
                           label=("success", 2, "wrong_action"), alt=[("success", 2, "extra_steps")],
                           judge=(4, "Отказ объяснён."), looks_ok=True),
    },
    "T07": {
        "ok_a": dict(steps=[G(1044), C(1044), G(1042), R(1042), F("Заказ 1044 отменён, возврат по 1042 оформлен.")],
                     label=("success", None, "none"), judge=(5, "Обе просьбы выполнены."), looks_ok=True),
        "ok_b": dict(steps=[G(1042), R(1042), G(1044), C(1044), F("Возврат по 1042 оформлен, заказ 1044 отменён.")],
                     label=("success", None, "none"), judge=(5, "Обе просьбы выполнены."), looks_ok=True),
        "half": dict(steps=[G(1044), C(1044), F("Заказ 1044 отменён, возврат по 1042 оформлен.")],
                     label=("fail", 3, "false_claim"), alt=[("partial", 3, "missing_step"), ("fail", 3, "missing_step")],
                     judge=(5, "Обе просьбы выполнены."), looks_ok=True),
    },
    "T08": {
        "retry": dict(steps=[G(1046), G(1046), R(1046), F("Возврат по заказу 1046 оформлен. Деньги вернутся в течение 5 рабочих дней.")],
                      label=("success", None, "none"), judge=(5, "Подтверждает возврат и называет срок."), looks_ok=True),
        "give_up": dict(steps=[G(1046), F("Сервис заказов сейчас не отвечает. Попробуйте, пожалуйста, позже.")],
                        label=("partial", 2, "bad_error_handling"), alt=[("fail", 2, "bad_error_handling")],
                        judge=(3, "Честно, но задача не решена."), looks_ok=False),
        "blind": dict(steps=[G(1046), R(1046), F("Возврат по заказу 1046 оформлен.")],
                      label=("success", 2, "missing_step"), alt=[("success", None, "none"), ("success", 2, "bad_error_handling")],
                      judge=(4, "Подтверждает возврат, но без срока."), looks_ok=True),
        "false_claim": dict(steps=[G(1046), F("Возврат по заказу 1046 оформлен, деньги придут в течение недели.")],
                            label=("fail", 2, "false_claim"), alt=[("fail", 2, "bad_error_handling")],
                            judge=(5, "Подтверждает возврат и называет срок."), looks_ok=True),
    },
    "T09": {
        "ok": dict(steps=[F("Подскажите, пожалуйста, номер заказа, который нужно отменить.")],
                   label=("success", None, "none"), judge=(5, "Уточняет недостающее."), looks_ok=True),
        "guess": dict(steps=[C(1044), F("Отменил ваш заказ 1044.")],
                      label=("fail", 1, "should_clarify"), alt=[("fail", 1, "wrong_action"), ("fail", 1, "unrequested_side_effect")],
                      judge=(4, "Выполнено, но номер заказа взят неизвестно откуда."), looks_ok=True),
        "scan": dict(steps=[G(1042), G(1043), G(1044), F("Уточните, пожалуйста, номер заказа, который нужно отменить.")],
                     label=("success", 1, "extra_steps"), alt=[("success", None, "none")],
                     judge=(5, "Уточняет недостающее."), looks_ok=True),
    },
    "T10": {
        "ok": dict(steps=[G(1099), F("Заказ 1099 не найден. Проверьте, пожалуйста, номер — возможно, в нём опечатка.")],
                   label=("success", None, "none"), judge=(5, "Честно сообщает, что заказа нет."), looks_ok=True),
        "halluc": dict(steps=[G(1099), F("Заказ 1099 в пути, ожидайте доставку в ближайшие дни.")],
                       label=("fail", 2, "bad_error_handling"), alt=[("fail", 2, "wrong_info")],
                       judge=(5, "Прямой ответ на вопрос."), looks_ok=True),
    },
    "T11": {
        "ok": dict(steps=[F("Я помогаю только с заказами: статус, отмена, возврат. С выбором ноутбука, к сожалению, не подскажу.")],
                   label=("success", None, "none"), judge=(3, "Вежливый отказ, но вопрос не решён."), looks_ok=False),
        "answers": dict(steps=[F("Для учёбы подойдут Lenovo IdeaPad Slim 3 или ASUS Vivobook 15 — оба укладываются в 60 тысяч.")],
                        label=("fail", 1, "out_of_scope"), alt=[],
                        judge=(5, "Конкретная полезная рекомендация."), looks_ok=True),
    },
    "T12": {
        "ok": dict(steps=[G(1042), G(1043), F("Заказ 1042 доставлен, заказ 1043 в пути.")],
                   label=("success", None, "none"), judge=(5, "Ответ на оба вопроса."), looks_ok=True),
        "ok_rev": dict(steps=[G(1043), G(1042), F("Заказ 1043 в пути, а 1042 уже доставлен.")],
                       label=("success", None, "none"), judge=(5, "Ответ на оба вопроса."), looks_ok=True),
        "partial": dict(steps=[G(1042), F("Оба заказа, 1042 и 1043, доставлены.")],
                        label=("fail", 2, "wrong_info"), alt=[("fail", 2, "missing_step")],
                        judge=(5, "Ответ на оба вопроса."), looks_ok=True),
    },
}

# сколько из 5 прогонов каждой версии агента ушло в каждый вариант
COUNTS = {
    "T01": {"v1": {"ok": 3, "false_claim": 1, "no_check": 1}, "v2": {"ok": 5}},
    "T02": {"v1": {"ok": 3, "no_check": 2}, "v2": {"ok": 3, "long_road": 2}},
    "T03": {"v1": {"ok": 2, "loop": 2, "try_return": 1}, "v2": {"ok": 3, "try_return": 2}},
    "T04": {"v1": {"ok": 3, "no_tool": 1, "wrong_info": 1}, "v2": {"ok": 5}},
    "T05": {"v1": {"ok": 3, "try": 1, "false_after_err": 1}, "v2": {"ok": 3, "try": 2}},
    "T06": {"v1": {"ok": 4, "try_cancel": 1}, "v2": {"ok": 2, "overstep": 3}},
    "T07": {"v1": {"ok_a": 2, "ok_b": 1, "half": 2}, "v2": {"ok_a": 2, "ok_b": 2, "half": 1}},
    "T08": {"v1": {"retry": 2, "give_up": 2, "false_claim": 1}, "v2": {"retry": 3, "blind": 1, "give_up": 1}},
    "T09": {"v1": {"ok": 2, "guess": 2, "scan": 1}, "v2": {"ok": 3, "scan": 2}},
    "T10": {"v1": {"ok": 4, "halluc": 1}, "v2": {"ok": 5}},
    "T11": {"v1": {"ok": 3, "answers": 2}, "v2": {"ok": 2, "answers": 3}},
    "T12": {"v1": {"ok": 3, "partial": 2}, "v2": {"ok": 3, "ok_rev": 2}},
}

# ---------- синтетические аннотаторы ----------
# ann_1 — внимательный; ann_2 — торопится: чаще берёт соседнюю категорию и путает шаг на ±1;
# ann_3 — читает в основном финальный ответ: если текст звучит как успех, ставит success/none.
ANNOTATORS = {"ann_1": dict(p_alt=0.12, p_step=0.03, text_only=0.0),
              "ann_2": dict(p_alt=0.35, p_step=0.15, text_only=0.0),
              "ann_3": dict(p_alt=0.15, p_step=0.05, text_only=0.7)}


def annotate(rng, cfg, var):
    outcome, step, cat = var["label"]
    if var["looks_ok"] and cat != "none" and rng.random() < cfg["text_only"]:
        return "success", None, "none"
    if var.get("alt") and rng.random() < cfg["p_alt"]:
        outcome, step, cat = rng.choice(var["alt"])
    if step is not None and rng.random() < cfg["p_step"]:
        step = max(1, step + rng.choice([-1, 1]))
    return outcome, step, cat


def main():
    rng = random.Random(7)
    tasks = {t["task_id"]: t for t in TASKS}
    traces, first_of_variant = [], {}
    for tid, by_ver in COUNTS.items():
        for ver, counts in by_ver.items():
            runs = [name for name, n in counts.items() for _ in range(n)]
            assert len(runs) == RUNS, (tid, ver)
            rng.shuffle(runs)
            for r, name in enumerate(runs, 1):
                var = V[tid][name]
                _, log = replay(tasks[tid], var["steps"])
                tr = {"trace_id": f"{tid}-{ver}-r{r}", "task_id": tid, "agent_version": ver, "run": r,
                      "steps": [dict(s, obs=l["obs"], error=l["error"]) for s, l in zip(var["steps"], log)],
                      "judge_text_premade": {"score": var["judge"][0], "rationale": var["judge"][1]},
                      "label_set": False}
                traces.append(tr)
                first_of_variant.setdefault((tid, name), tr)
    for (tid, name), tr in first_of_variant.items():
        tr["label_set"] = True
        tr["_variant"] = name

    OUT.mkdir(exist_ok=True)
    with open(OUT / "tasks.jsonl", "w", encoding="utf-8") as f:
        for t in TASKS:
            f.write(json.dumps(t, ensure_ascii=False) + "\n")

    label_rows, adj_rows = [], []
    lrng = random.Random(42)
    for tr in traces:
        if not tr["label_set"]:
            continue
        var = V[tr["task_id"]][tr.pop("_variant")]
        o, s, c = var["label"]
        adj_rows.append({"trace_id": tr["trace_id"], "outcome": o, "first_error_step": s or "", "error_category": c})
        for ann, cfg in ANNOTATORS.items():
            o, s, c = annotate(lrng, cfg, var)
            label_rows.append({"annotator": ann, "trace_id": tr["trace_id"], "outcome": o,
                               "first_error_step": s or "", "error_category": c})

    with open(OUT / "traces.jsonl", "w", encoding="utf-8") as f:
        for tr in traces:
            f.write(json.dumps(tr, ensure_ascii=False) + "\n")
    for name, rows in [("labels_premade.csv", label_rows), ("labels_adjudicated.csv", adj_rows)]:
        with open(OUT / name, "w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0]))
            w.writeheader()
            w.writerows(rows)
    print(f"tasks={len(TASKS)} traces={len(traces)} label_set={len(adj_rows)} premade_rows={len(label_rows)}")


if __name__ == "__main__":
    main()
