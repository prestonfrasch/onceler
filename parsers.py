import json

def est_tokens_from_text(s: str) -> int:
    return max(1, len(s) // 4)

def tokens_in_from_body(body: bytes) -> int:
    if not body:
        return 0
    try:
        data = json.loads(body.decode("utf-8", "ignore"))
    except Exception:
        return 0
    t = 0
    if isinstance(data, dict):
        if "prompt" in data and isinstance(data["prompt"], str):
            t += est_tokens_from_text(data["prompt"])
        if "messages" in data and isinstance(data["messages"], list):
            for m in data["messages"]:
                c = m.get("content")
                if isinstance(c, str):
                    t += est_tokens_from_text(c)
                elif isinstance(c, list):
                    for part in c:
                        if isinstance(part, dict):
                            if "text" in part:
                                t += est_tokens_from_text(str(part["text"]))
                            if part.get("type") == "input_text" and "text" in part:
                                t += est_tokens_from_text(str(part["text"]))
    return t

def tokens_out_from_len(content_len: int | None) -> int:
    if not content_len:
        return 0
    return max(1, content_len // 4)
