"""현황 웹사이트(정적 HTML 한 장)를 만든다. 데이터는 페이지 안에 JSON으로 넣는다."""
import json

TEMPLATE = """<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>99일 야간숲 소식</title>
<style>
:root{--bg:#f6f5f1;--card:#fff;--ink:#1f2421;--mute:#667068;--line:#e3e1d8;--acc:#2f6b4f;
--badge:#7a4fb5;--patch:#2f6b4f;--code:#b5651d}
@media(prefers-color-scheme:dark){:root{--bg:#141815;--card:#1d231f;--ink:#e8ece9;--mute:#9aa59d;--line:#2d352f;--acc:#6fcf9f;
--badge:#b99af0;--patch:#6fcf9f;--code:#f0a868}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);
font:16px/1.6 -apple-system,"Malgun Gothic","Apple SD Gothic Neo",sans-serif}
main{max-width:720px;margin:0 auto;padding:20px 16px 48px}
h1{font-size:22px;margin:8px 0 2px}.sub{color:var(--mute);font-size:14px;margin:0 0 16px}
.tabs{display:flex;gap:8px;flex-wrap:wrap;margin:12px 0 16px}
.tab{border:1px solid var(--line);background:var(--card);color:var(--ink);padding:6px 14px;border-radius:999px;
font:inherit;font-size:14px;cursor:pointer}.tab[aria-pressed=true]{background:var(--acc);color:#fff;border-color:var(--acc)}
.card{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:14px 16px;margin:10px 0}
.tag{display:inline-block;font-size:12px;font-weight:700;padding:1px 8px;border-radius:6px;border:1px solid currentColor}
.badge{color:var(--badge)}.patch{color:var(--patch)}.code{color:var(--code)}
.card h2{font-size:17px;margin:6px 0 4px}.card p{margin:4px 0}
.tip{background:rgba(47,107,79,.10);border-radius:8px;padding:6px 10px;font-size:15px}
.meta{color:var(--mute);font-size:13px;margin-top:8px}.meta a{color:var(--acc)}
.warn{color:var(--code);font-weight:700}.empty{color:var(--mute);text-align:center;padding:32px 0}
details{margin-top:6px}summary{cursor:pointer;color:var(--mute);font-size:13px}
</style>
</head>
<body><main>
<h1>99일 야간숲 소식</h1>
<p class="sub" id="sub"></p>
<div class="tabs" id="tabs"></div>
<div id="list"></div>
</main>
<script id="data" type="application/json">__DATA__</script>
<script>
const D=JSON.parse(document.getElementById('data').textContent);
const TAGS={badge:'신규 배지',patch:'패치',code:'코드'};
const FILTERS=[['all','전체'],['badge','신규 배지'],['patch','패치'],['code','코드']];
let cur='all';
const esc=s=>String(s??'').replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
document.getElementById('sub').textContent='마지막 확인: '+D.generated+(D.game&&D.game.updated?' · 게임 마지막 갱신: '+D.game.updated.slice(0,10):'');
function render(){
  document.getElementById('tabs').innerHTML=FILTERS.map(([k,l])=>
    `<button class="tab" aria-pressed="${k===cur}" data-k="${k}">${l}</button>`).join('');
  document.querySelectorAll('.tab').forEach(b=>b.onclick=()=>{cur=b.dataset.k;render()});
  const rows=D.items.filter(i=>cur==='all'||i.kind===cur);
  document.getElementById('list').innerHTML=rows.length?rows.map(i=>`
  <article class="card">
    <span class="tag ${i.kind}">${TAGS[i.kind]||'소식'}</span>
    <h2>${esc(i.title_ko||i.title)}</h2>
    <p>${esc(i.summary)}</p>
    ${i.tip?`<p class="tip">아이에게 한 줄: ${esc(i.tip)}</p>`:''}
    <div class="meta">${esc(i.date)} · ${esc(i.source)}
      ${i.translated===false?' · <span class="warn">번역 안 됨</span>':''}
      · <a href="${esc(i.url)}" target="_blank" rel="noopener">원문</a>
      ${i.video?` · <a href="${esc(i.video)}" target="_blank" rel="noopener">참고 영상</a>`:''}</div>
  </article>`).join(''):'<p class="empty">아직 표시할 소식이 없어요.</p>';
}
render();
</script>
</body></html>
"""


def build_site(items, generated, game_info, out_path):
    data = {"items": items, "generated": generated, "game": game_info or {}}
    blob = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(TEMPLATE.replace("__DATA__", blob), encoding="utf-8")
