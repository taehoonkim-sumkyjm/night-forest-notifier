"""출처별 소식 수집. 각 항목은 같은 모양의 dict로 돌려준다.

항목 필드: id, kind(badge|patch|code), title, body, date(YYYY-MM-DD), source, level(official|wiki|youtube), url
level 은 신뢰도: official(로블록스 공식 API) / wiki(팬 위키) / youtube(보조 확인용).
"""
import difflib
import re
import urllib.parse
import xml.etree.ElementTree as ET
from datetime import datetime, timezone

from common import get_json, http


def fetch_game_info(cfg):
    """게임 기본 정보(마지막 갱신 시각 등). 실패해도 전체를 멈추지 않는다."""
    url = f"https://games.roblox.com/v1/games?universeIds={cfg['universe_id']}"
    try:
        d = get_json(url)["data"][0]
        return {"updated": d.get("updated"), "playing": d.get("playing"), "visits": d.get("visits")}
    except Exception as e:
        print("게임 정보 조회 실패:", e)
        return {}


def collect_badges(cfg):
    """공식 API의 배지 목록(최신순). 신규 배지 소식의 기준."""
    url = (f"https://badges.roblox.com/v1/universes/{cfg['universe_id']}/badges"
           f"?limit=100&sortOrder=Desc")
    data = get_json(url)["data"][: cfg["badge_fetch_limit"]]
    items = []
    for b in data:
        if not b.get("enabled", True):
            continue
        items.append({
            "id": f"badge:{b['id']}",
            "kind": "badge",
            "title": b.get("displayName") or b.get("name"),
            "body": b.get("displayDescription") or b.get("description") or "",
            "date": (b.get("created") or "")[:10],
            "source": "로블록스 공식 배지 목록",
            "level": "official",
            "url": f"https://www.roblox.com/badges/{b['id']}",
        })
    return items


def _wiki_text(cfg, title):
    q = urllib.parse.urlencode({
        "action": "query", "prop": "revisions", "rvprop": "content", "rvslots": "main",
        "titles": title, "format": "json", "formatversion": 2,
    })
    d = get_json(f"{cfg['wiki_api']}?{q}")
    return d["query"]["pages"][0]["revisions"][0]["slots"]["main"]["content"]


def _clean_wikitext(t):
    t = re.sub(r"\[\[(?:File|Image):[^\]]*\]\]", "", t)
    t = re.sub(r"\[\[([^\]|]*)\|([^\]]*)\]\]", r"\2", t)
    t = re.sub(r"\[\[([^\]]*)\]\]", r"\1", t)
    t = t.replace("'''", "").replace("''", "")
    lines = []
    for ln in t.splitlines():
        ln = ln.strip()
        if not ln or ln in ("|-", "|}", "{|") or ln.startswith("{|") or ln.startswith("!"):
            continue
        ln = ln.lstrip("|").strip()
        if ln:
            lines.append(ln)
    return "\n".join(lines)


HEAD = re.compile(r"^!'''(\d{4})\.(\d{1,2})\.(\d{1,2})\s*[-–]\s*(.+?)'''\s*$", re.M)


def collect_patches(cfg, game_info):
    """위키 '업데이트 로그' 문서를 날짜별 항목으로 쪼갠다."""
    text = _wiki_text(cfg, cfg["wiki_update_log_title"])
    matches = list(HEAD.finditer(text))
    game_updated = (game_info or {}).get("updated")
    items = []
    for i, m in enumerate(matches):
        y, mo, d, title = int(m[1]), int(m[2]), int(m[3]), m[4].strip()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        body = _clean_wikitext(text[m.end():end])[:1800]
        date = f"{y:04d}-{mo:02d}-{d:02d}"
        # 공식 확인: 게임 페이지의 마지막 갱신 시각이 업데이트 날짜 이후이면 '공식 갱신과 일치'로 본다.
        confirmed = bool(game_updated) and game_updated[:10] >= date
        items.append({
            "id": f"patch:{date}:{title}",
            "kind": "patch",
            "title": title,
            "body": body,
            "date": date,
            "source": "팬 위키 업데이트 로그" + ("" if confirmed else " (미확인)"),
            "level": "wiki",
            "url": f"https://99-nights-in-the-forest.fandom.com/wiki/{cfg['wiki_update_log_title']}",
            "confirmed": confirmed,
        })
    return items


def collect_codes(cfg, prev_codes_text, today):
    """위키 '코드' 문서에서 이전 실행 때보다 새로 늘어난 줄만 뽑는다.

    돌려주는 값: (항목 리스트, 이번 문서 전체 텍스트). 처음 실행(prev 없음)이면 항목은 비어 있다.
    """
    text = _clean_wikitext(_wiki_text(cfg, cfg["wiki_codes_title"]))
    if prev_codes_text is None:
        return [], text
    old = set(prev_codes_text.splitlines())
    added = [ln for ln in text.splitlines() if ln not in old]
    if not added:
        return [], text
    body = "\n".join(added)[:1500]
    import hashlib
    h = hashlib.sha1(body.encode()).hexdigest()[:10]
    return [{
        "id": f"code:{h}",
        "kind": "code",
        "title": "코드 목록에 변경이 있어요",
        "body": body,
        "date": today,
        "source": "팬 위키 코드 문서",
        "level": "wiki",
        "url": f"https://99-nights-in-the-forest.fandom.com/wiki/{cfg['wiki_codes_title']}",
    }], text


def collect_youtube(cfg):
    """설정한 채널의 최신 영상 제목. 알림을 단독으로 만들지 않고 교차 확인 링크로만 쓴다."""
    out = []
    for cid in cfg.get("youtube_channel_ids", []):
        try:
            status, body = http(f"https://www.youtube.com/feeds/videos.xml?channel_id={cid}")
            if status != 200:
                continue
            ns = {"a": "http://www.w3.org/2005/Atom"}
            for e in ET.fromstring(body).findall("a:entry", ns)[:15]:
                out.append({
                    "title": e.findtext("a:title", "", ns),
                    "url": e.find("a:link", ns).attrib["href"],
                })
        except Exception as e:
            print("유튜브 수집 실패:", cid, e)
    return out


def attach_youtube_links(items, videos):
    """영상 제목에 항목 제목이 들어 있으면 '참고 영상'으로 붙인다(교차 확인)."""
    for it in items:
        key = it["title"].lower()
        if len(key) < 4:
            continue
        hits = [v for v in videos if key in v["title"].lower()]
        if hits:
            it["video"] = hits[0]["url"]
    return items
