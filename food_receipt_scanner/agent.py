import json
from datetime import date, timedelta

import requests

from . import config, db


TOOLS = [
    {
        "name": "items_on_date",
        "description": "List every food item bought on a specific date.",
        "arguments": {"day": "ISO date string, e.g. 2026-06-20"},
    },
    {
        "name": "total_spend_on_date",
        "description": "Total money spent, and item count, on a specific date.",
        "arguments": {"day": "ISO date string, e.g. 2026-06-20"},
    },
    {
        "name": "find_item_in_range",
        "description": "Find which store(s) a food item was bought from in the last N days.",
        "arguments": {
            "item_name": "name of the food, e.g. hamburger",
            "days": "integer number of days, e.g. 7",
        },
    },
]

_TOOL_FUNCS = {
    "items_on_date": db.items_on_date,
    "total_spend_on_date": db.total_spend_on_date,
    "find_item_in_range": db.find_item_in_range,
}

_SYSTEM = """You answer questions about a user's food receipts.

You have access to tools backed by a database of receipt items:
{tool_descriptions}

Rules:
- Today's date is {today}. Yesterday is {yesterday}.
- Resolve relative dates yourself: "20 June" means 20 June of the current year unless a year is given. "last 7 days" means days=7.
- To call a tool, reply with ONLY a JSON object: {{"tool": "<name>", "arguments": {{...}}}}.
- Once you have the tool result, answer the user in natural language using the data. If the data is empty, say there are no matching receipts.
- Never call a tool more than once for the same information: after the first tool result, always produce the final answer.
- When giving the final answer, reply with ONLY: {{"answer": "..."}}.
"""


def _chat(messages):
    headers = {
        "Authorization": f"Bearer {config.DEEPSEEK_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {"model": config.DEEPSEEK_MODEL, "messages": messages}
    resp = requests.post(config.DEEPSEEK_URL, json=payload, headers=headers, timeout=60)
    data = resp.json()
    if resp.status_code != 200 or "choices" not in data:
        message = data.get("error", {}).get("message", json.dumps(data))
        raise RuntimeError(f"DeepSeek error {resp.status_code}: {message}")
    return data["choices"][0]["message"]["content"]


def _parse_json(content):
    content = content.strip()
    if content.startswith("```"):
        content = content.strip("`")
        if content.lower().startswith("json"):
            content = content[4:]
        content = content.strip()
    return json.loads(content)


def answer(question):
    if not config.DEEPSEEK_API_KEY:
        return "DeepSeek key is not configured (set DEEPSEEK_API_KEY in .env)."
    if not config.DEEPSEEK_MODEL:
        return "DeepSeek model is not configured (set DEEPSEEK_MODEL in .env)."

    tool_desc = "\n".join(f"- {t['name']}: {t['description']}" for t in TOOLS)
    system = _SYSTEM.format(
        tool_descriptions=tool_desc,
        today=date.today().isoformat(),
        yesterday=(date.today() - timedelta(days=1)).isoformat(),
    )
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": question},
    ]

    for _ in range(6):
        try:
            content = _chat(messages)
        except Exception as exc:
            return f"Sorry, the model request failed: {exc}"
        try:
            obj = _parse_json(content)
        except (ValueError, json.JSONDecodeError):
            return content  # free-text answer

        if "answer" in obj:
            return obj["answer"]

        if "tool" in obj:
            name = obj["tool"]
            args = obj.get("arguments", {})
            fn = _TOOL_FUNCS.get(name)
            messages.append({"role": "assistant", "content": content})
            if fn is None:
                messages.append({"role": "user", "content": json.dumps({"error": f"unknown tool: {name}"})})
                continue
            try:
                result = fn(**args)
            except Exception as exc:  # surface tool errors to the model
                result = {"error": str(exc)}
            messages.append({"role": "user", "content": json.dumps({"tool": name, "result": result})})
            continue

        return content

    return "I could not determine an answer from the receipt data."
