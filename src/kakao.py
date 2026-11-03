"""카카오톡 '나에게 보내기'. 텍스트 템플릿은 200자 제한이 있어 건별로 줄여서 보낸다."""
import json
import os
import unicodedata
from pathlib import Path

from common import ROOT, http

TAGS = {"badge": "신규 배지", "patch": "패치", "code": "코드"}
LIMIT = 200


def _env(name):
    """비밀값을 읽을 때 공백·줄바꿈·보이지 않는 글자를 모두 제거한다 (복사할 때 딸려 들어오는 경우가 많다)."""
    v = os.environ.get(name, "")
    return "".join(ch for ch in v if unicodedata.category(ch)[0] not in "CZ")


def _diagnose(name):
    """값은 숨기고 길이와 이상한 글자 유무만 출력한다."""
    raw = os.environ.get(name, "")
    clean = _env(name)
    odd = len(raw) - len(clean)
    nonascii = any(ord(ch) > 127 for ch in clean)
    print(f"[점검] {name}: 길이 {len(clean)}자, 제거된 이상한 글자 {odd}개, 한글·특수문자 포함 {'예' if nonascii else '아니오'}")


def configured():
    return bool(_env("KAKAO_REST_API_KEY") and _env("KAKAO_REFRESH_TOKEN"))


def get_access_token():
    """리프레시 토큰으로 액세스 토큰을 새로 받는다. 새 리프레시 토큰이 오면 파일로 남긴다."""
    for n in ("KAKAO_REST_API_KEY", "KAKAO_REFRESH_TOKEN", "KAKAO_CLIENT_SECRET"):
        _diagnose(n)
    data = {
        "grant_type": "refresh_token",
        "client_id": _env("KAKAO_REST_API_KEY"),
        "refresh_token": _env("KAKAO_REFRESH_TOKEN"),
    }
    if _env("KAKAO_CLIENT_SECRET"):
        data["client_secret"] = _env("KAKAO_CLIENT_SECRET")
    status, body = http("https://kauth.kakao.com/oauth/token", data=data, method="POST")
    res = json.loads(body)
    if status != 200 or "access_token" not in res:
        raise RuntimeError(f"카카오 토큰 갱신 실패: {body[:200]}")
    if res.get("refresh_token"):
        out = ROOT / "out"
        out.mkdir(exist_ok=True)
        (out / "new_refresh_token.txt").write_text(res["refresh_token"], encoding="utf-8")
    return res["access_token"]


def send_text(access_token, text, link):
    text = text[:LIMIT]
    tpl = {"object_type": "text", "text": text,
           "link": {"web_url": link, "mobile_web_url": link}, "button_title": "현황 보기"}
    status, body = http(
        "https://kapi.kakao.com/v2/api/talk/memo/default/send",
        data={"template_object": json.dumps(tpl, ensure_ascii=False)},
        headers={"Authorization": f"Bearer {access_token}"}, method="POST",
    )
    if status != 200:
        raise RuntimeError(f"카카오 전송 실패 {status}: {body[:200]}")


def format_item(item, today_label):
    """알림 한 건을 200자 안으로 맞춘다. 줄이는 순서: 요약 → 한 줄 요령."""
    tag = TAGS.get(item["kind"], "소식")
    src = item["source"] + (f" · 확인 {today_label}")
    title = item.get("title_ko") or item["title"]

    def build(summary, tip):
        lines = [f"[{tag}] {title}", f"· {summary}"]
        if tip:
            lines.append(f"· 아이에게: {tip}")
        lines.append(f"· 출처: {src}")
        return "\n".join(lines)

    summary, tip = item.get("summary", ""), item.get("tip", "")
    text = build(summary, tip)
    while len(text) > LIMIT and len(summary) > 20:
        summary = summary[: max(20, len(summary) - 15)].rstrip(" ,.") + "…"
        text = build(summary, tip)
        if len(summary) <= 20:
            break
    if len(text) > LIMIT:
        text = build(summary[:30] + "…", tip[:40])
    return text[:LIMIT]


def send_digest(new_items, site_url, today_label, max_items):
    """하루치 알림: 요약 1건 + 소식별 메시지. 전송 성공한 항목 id 목록을 돌려준다."""
    token = get_access_token()
    sent = []
    if not new_items:
        send_text(token, f"[99일 야간숲] 오늘은 새 소식 없음 ({today_label})", site_url)
        return sent
    shown = new_items[:max_items]
    head = f"[99일 야간숲] 새 소식 {len(new_items)}건 ({today_label})"
    if len(new_items) > len(shown):
        head += f"\n나머지 {len(new_items) - len(shown)}건은 현황 웹사이트에서 확인하세요."
    send_text(token, head, site_url)
    for it in shown:
        send_text(token, format_item(it, today_label), it.get("video") or it.get("url") or site_url)
        sent.append(it["id"])
    # 웹사이트로 안내한 나머지는 사이트에 올라가므로 읽은 것으로 본다.
    sent += [it["id"] for it in new_items[len(shown):]]
    return sent
