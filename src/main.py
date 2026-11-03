"""매일 아침 실행되는 진입점.

사용법:
  python src/main.py              # 평소 실행 (카카오 전송 + 사이트 갱신 + 상태 저장)
  python src/main.py --dry-run    # 아무것도 보내거나 저장하지 않고 결과만 out/preview.html 에 만든다
  python src/main.py --test-kakao # 카카오톡으로 테스트 메시지 1건만 보낸다
"""
import argparse
import os
import sys

import collect
import kakao
import webpage as sitegen
from common import ROOT, load_json, now_kst, save_json
from summarize import summarize

SEED_SHOW = 10  # 처음 실행 때 사이트에 미리 보여줄 최신 항목 수


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--test-kakao", action="store_true")
    args = ap.parse_args()

    cfg = load_json(ROOT / "config.json", {})
    site_url = os.environ.get("SITE_URL") or "https://www.roblox.com/games/" + str(cfg["root_place_id"])

    if args.test_kakao:
        if not kakao.configured():
            sys.exit("KAKAO_REST_API_KEY / KAKAO_REFRESH_TOKEN 이 설정되지 않았어요.")
        kakao.send_text(kakao.get_access_token(), "[99일 야간숲] 테스트 메시지예요. 이게 보이면 연결 성공!", site_url)
        print("테스트 메시지를 보냈어요.")
        return

    now = now_kst()
    today, label = now.strftime("%Y-%m-%d"), now.strftime("%m/%d")
    state = load_json(ROOT / "state" / "state.json", {"initialized": False, "seen": [], "codes_text": None})
    site_items = load_json(ROOT / "state" / "items.json", [])
    seen = set(state["seen"])

    # 1) 수집 — 출처 하나가 실패해도 나머지는 계속한다.
    errors, items = [], []
    game = collect.fetch_game_info(cfg)
    for name, fn in (("배지", lambda: collect.collect_badges(cfg)),
                     ("패치", lambda: collect.collect_patches(cfg, game))):
        try:
            items += fn()
        except Exception as e:
            errors.append(f"{name} 수집 실패: {e}")
    codes_text = state.get("codes_text")
    try:
        code_items, codes_text = collect.collect_codes(cfg, state.get("codes_text"), today)
        items += code_items
    except Exception as e:
        errors.append(f"코드 수집 실패: {e}")
    videos = collect.collect_youtube(cfg)
    for e in errors:
        print("⚠", e)

    # 2) 새 항목 가려내기 (같은 id 는 한 번만)
    new, ids = [], set()
    for it in items:
        if it["id"] not in seen and it["id"] not in ids:
            new.append(it)
            ids.add(it["id"])
    new.sort(key=lambda x: x["date"], reverse=True)
    first_run = not state["initialized"]
    to_process = new[:SEED_SHOW] if first_run else new
    print(f"새 항목 {len(new)}건 (처음 실행: {first_run})")

    # 3) 한국어 요약 + 영상 교차 확인 링크
    collect.attach_youtube_links(to_process, videos)
    summarize(to_process, cfg["summary_model"])

    # 4) 카카오톡 전송 (처음 실행은 보내지 않고 기준선만 만든다)
    sent_ids, send_error = set(), None
    if args.dry_run:
        print("[dry-run] 카카오톡 전송 생략")
        for it in to_process:
            print("-" * 40)
            print(kakao.format_item(it, label))
    elif first_run:
        sent_ids = {it["id"] for it in new}
        print("처음 실행: 기존 소식은 알림 없이 기준선으로만 저장해요.")
    elif kakao.configured():
        try:
            sent_ids = set(kakao.send_digest(to_process, site_url, label, cfg["max_items_per_message_batch"]))
        except Exception as e:
            send_error = str(e)
            print("⚠ 카카오톡 전송 실패:", e)
    else:
        sent_ids = {it["id"] for it in new}
        print("카카오 설정이 없어 전송은 생략하고 웹사이트에만 올려요.")

    # 5) 웹사이트 데이터 갱신: 전송 실패한 항목도 사이트에는 올린다(다음 실행에서 다시 알림).
    existing = {i["id"] for i in site_items}
    for it in to_process:
        if it["id"] not in existing:
            site_items.insert(0, {k: it.get(k) for k in (
                "id", "kind", "title", "title_ko", "summary", "tip", "translated",
                "date", "source", "level", "url", "video")})
    site_items.sort(key=lambda x: x["date"] or "", reverse=True)
    site_items = site_items[: cfg["site_keep_items"]]
    generated = now.strftime("%Y-%m-%d %H:%M")

    if args.dry_run:
        sitegen.build_site(site_items, generated, game, ROOT / "out" / "preview.html")
        print("미리보기:", ROOT / "out" / "preview.html")
        return
    sitegen.build_site(site_items, generated, game, ROOT / "docs" / "index.html")

    # 6) 상태 저장
    state["initialized"] = True
    state["seen"] = sorted(seen | sent_ids)
    state["codes_text"] = codes_text
    save_json(ROOT / "state" / "state.json", state)
    save_json(ROOT / "state" / "items.json", site_items)

    if send_error or errors:
        print("일부 단계에서 오류가 있었어요.")
        sys.exit(1 if send_error else 0)


if __name__ == "__main__":
    main()
