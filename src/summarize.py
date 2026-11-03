"""영어 원문을 부모용 한국어 요약으로 바꾼다 (Claude API). 키가 없으면 원문을 잘라 쓴다."""
import json
import os
import re

from common import http

SYSTEM = (
    "너는 로블록스 게임 '99 Nights in the Forest'(99일 야간숲)의 소식을 한국 부모에게 전하는 도우미다. "
    "입력 JSON 배열의 각 항목을 한국어로 정리해라. 규칙: "
    "1) 원문에 없는 내용은 지어내지 말고, 불분명하면 '확인 필요'라고 써라. "
    "2) summary 는 2~3문장, 쉬운 말. 3) tip 은 부모가 아드님께 그대로 전할 수 있는 요령 한 문장(30자~60자). "
    "4) 게임 고유 명사는 한국어 번역 뒤 괄호에 영어 원문을 병기해라. "
    "5) 코드(code) 항목은 새로 생긴 코드 문자열은 원문 그대로 적고, 만료·사용 가능 여부가 불분명하면 그렇게 써라. "
    "출력은 JSON 배열만. 각 요소: {\"id\":입력 id 그대로, \"title\":한국어 제목, \"summary\":..., \"tip\":...}"
)


def _fallback(item):
    body = " ".join(item["body"].split())
    return {
        "title": item["title"],
        "summary": (body[:140] + "…") if len(body) > 140 else (body or "자세한 내용은 링크에서 확인하세요."),
        "tip": "원문 요약이 되지 않았어요. 링크에서 직접 확인해 주세요.",
        "translated": False,
    }


def summarize(items, model):
    """items 에 title_ko, summary, tip, translated 를 채워 돌려준다."""
    key = os.environ.get("ANTHROPIC_API_KEY")
    results = {}
    if key and items:
        for i in range(0, len(items), 6):  # 한 번에 6건씩
            chunk = items[i:i + 6]
            payload = [{"id": x["id"], "kind": x["kind"], "title": x["title"], "text": x["body"][:1500]}
                       for x in chunk]
            try:
                status, body = http(
                    "https://api.anthropic.com/v1/messages",
                    method="POST",
                    headers={"x-api-key": key, "anthropic-version": "2023-06-01",
                             "content-type": "application/json"},
                    data=json.dumps({
                        "model": model, "max_tokens": 4000, "system": SYSTEM,
                        "messages": [{"role": "user", "content": json.dumps(payload, ensure_ascii=False)}],
                    }),
                )
                if status != 200:
                    raise RuntimeError(f"HTTP {status}: {body[:200]}")
                text = json.loads(body)["content"][0]["text"]
                text = re.sub(r"^```(?:json)?|```$", "", text.strip(), flags=re.M).strip()
                for r in json.loads(text):
                    results[r["id"]] = r
            except Exception as e:
                print("요약 실패(원문으로 대체):", e)
    for it in items:
        r = results.get(it["id"])
        if r and r.get("summary"):
            it["title_ko"] = r.get("title") or it["title"]
            it["summary"] = r["summary"]
            it["tip"] = r.get("tip", "")
            it["translated"] = True
        else:
            f = _fallback(it)
            it["title_ko"], it["summary"], it["tip"], it["translated"] = f["title"], f["summary"], f["tip"], False
    return items
