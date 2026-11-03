"""공용 도구: HTTP 요청, 시간, 파일 입출력."""
import json
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

KST = timezone(timedelta(hours=9))
ROOT = Path(__file__).resolve().parent.parent
UA = "Mozilla/5.0 (compatible; NightForestNotifier/1.0)"


def now_kst():
    return datetime.now(KST)


def http(url, *, data=None, headers=None, method=None, retries=3, timeout=25):
    """URL을 호출해 (상태코드, 본문 문자열)을 돌려준다. 일시 오류는 재시도한다."""
    hdrs = {"User-Agent": UA}
    hdrs.update(headers or {})
    if isinstance(data, dict):
        data = urllib.parse.urlencode(data).encode()
    elif isinstance(data, str):
        data = data.encode()
    last = None
    for attempt in range(retries):
        req = urllib.request.Request(url, data=data, headers=hdrs, method=method)
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.status, r.read().decode("utf-8", "replace")
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", "replace")
            if e.code < 500 and e.code != 429:
                return e.code, body
            last = f"HTTP {e.code}: {body[:200]}"
        except Exception as e:  # 네트워크 오류
            last = repr(e)
        time.sleep(2 * (attempt + 1))
    raise RuntimeError(f"요청 실패: {url} ({last})")


def get_json(url, **kw):
    status, body = http(url, **kw)
    if status != 200:
        raise RuntimeError(f"HTTP {status}: {url} {body[:200]}")
    return json.loads(body)


def load_json(path, default):
    p = Path(path)
    if not p.exists():
        return default
    return json.loads(p.read_text(encoding="utf-8"))


def save_json(path, obj):
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")
