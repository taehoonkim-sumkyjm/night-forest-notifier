"""현황 웹사이트(정적 HTML 한 장)를 만든다. 데이터는 페이지 안에 JSON으로 넣는다."""
import json

TEMPLATE = """<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<meta name="theme-color" content="#2f7d59">
<title>99일 야간숲 소식</title>
<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 64 64'%3E%3Crect width='64' height='64' rx='14' fill='%232f7d59'/%3E%3Cpath d='M32 10 18 30h8L14 46h14v8h8v-8h14L38 30h8z' fill='%23fff'/%3E%3C/svg%3E">
<style>
:root{--bg:#f6f7f4;--card:#fff;--ink:#1d2622;--mute:#6a766f;--line:#e6e9e3;--acc:#2f7d59;--acc2:#4aa57c;
--tip:#eef7f1;--shadow:0 1px 2px rgba(20,40,30,.05),0 6px 18px rgba(20,40,30,.06);
--badge:#7a4fb5;--badge-bg:#f1eafb;--patch:#1f7a56;--patch-bg:#e4f4ec;--code:#b4601a;--code-bg:#fdf0e1;--new:#e5484d}
@media(prefers-color-scheme:dark){:root{--bg:#101512;--card:#1a211d;--ink:#e9eeea;--mute:#98a39c;--line:#2a332d;
--acc:#63c595;--acc2:#2f7d59;--tip:#1d2b23;--shadow:none;
--badge:#c0a4f2;--badge-bg:#2a2238;--patch:#7fd6a8;--patch-bg:#1c3026;--code:#f2b077;--code-bg:#35261a}}
*{box-sizing:border-box}html{-webkit-text-size-adjust:100%}
body{margin:0;background:var(--bg);color:var(--ink);
font:16px/1.65 -apple-system,BlinkMacSystemFont,"Apple SD Gothic Neo","Malgun Gothic","Noto Sans KR",sans-serif}
header{background:linear-gradient(135deg,#2f7d59,#4aa57c);color:#fff;
padding:calc(env(safe-area-inset-top) + 28px) 20px 56px}
.wrap{max-width:720px;margin:0 auto}
.eyebrow{font-size:13px;opacity:.85;letter-spacing:.02em;margin:0}
h1{font-size:26px;line-height:1.3;margin:6px 0 14px;font-weight:800}
.stats{display:flex;gap:8px;flex-wrap:wrap}
.stat{background:rgba(255,255,255,.18);border-radius:999px;padding:4px 12px;font-size:13px}
main{max-width:720px;margin:-32px auto 0;padding:0 16px 48px}
.tabs{display:flex;gap:8px;overflow-x:auto;padding:12px;background:var(--card);border-radius:16px;
box-shadow:var(--shadow);position:sticky;top:8px;z-index:5}
.tab{flex:0 0 auto;border:0;background:transparent;color:var(--mute);padding:8px 14px;border-radius:999px;
font:inherit;font-size:14px;font-weight:600;cursor:pointer}
.tab .n{opacity:.7;margin-left:4px;font-weight:500}
.tab[aria-pressed=true]{background:var(--acc);color:#fff}
.tab:focus-visible,a:focus-visible{outline:2px solid var(--acc);outline-offset:2px}
.card{background:var(--card);border-radius:16px;box-shadow:var(--shadow);padding:18px 18px 14px;margin:14px 0;
border:1px solid var(--line)}
.top{display:flex;align-items:center;gap:8px;flex-wrap:wrap}
.pill{font-size:12px;font-weight:700;padding:2px 10px;border-radius:999px}
.pill.badge{color:var(--badge);background:var(--badge-bg)}
.pill.patch{color:var(--patch);background:var(--patch-bg)}
.pill.code{color:var(--code);background:var(--code-bg)}
.pill.new{color:#fff;background:var(--new)}
.date{color:var(--mute);font-size:13px;margin-left:auto}
.card h2{font-size:18px;line-height:1.4;margin:10px 0 6px;font-weight:700}
.card p{margin:6px 0;color:var(--ink)}
.tip{background:var(--tip);border-left:4px solid var(--acc);border-radius:10px;padding:10px 12px;margin-top:10px;font-size:15px}
.tip b{display:block;font-size:12px;color:var(--acc);margin-bottom:2px;letter-spacing:.02em}
.foot{display:flex;gap:6px 14px;flex-wrap:wrap;align-items:center;margin-top:12px;padding-top:10px;
border-top:1px dashed var(--line);font-size:13px;color:var(--mute)}
.foot a{color:var(--acc);font-weight:600;text-decoration:none}
.foot a:hover{text-decoration:underline}
.warn{color:var(--code);font-weight:700}
.empty{color:var(--mute);text-align:center;padding:48px 0}
footer{color:var(--mute);font-size:12.5px;text-align:center;padding:8px 0 32px}
</style>
</head>
<body>
<header><div class="wrap">
<p class="eyebrow">부모를 위한 게임 소식 알리미</p>
<h1>99일 야간숲 소식</h1>
<div class="stats" id="stats"></div>
</div></header>
<main>
<nav class="tabs" id="tabs" aria-label="소식 종류"></nav>
<section id="list"></section>
<footer>매일 아침 6시 30분쯤 자동으로 새 소식을 확인해요.</footer>
</main>
<script id="data" type="application/json">__DATA__</script>
<script>
const D=JSON.parse(document.getElementById('data').textContent);
const TAGS={badge:'신규 배지',patch:'패치',code:'코드'};
const FILTERS=[['all','전체'],['badge','신규 배지'],['patch','패치'],['code','코드']];
let cur='all';
const esc=s=>String(s??'').replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const dayMs=864e5, now=Date.now();
const age=i=>{const t=Date.parse(i.date);return isNaN(t)?1e9:(now-t)/dayMs};
const isNew=i=>age(i)<=2.5;
const week=D.items.filter(i=>age(i)<=7).length;
const g=D.game&&D.game.updated?D.game.updated.slice(0,10):'';
document.getElementById('stats').innerHTML=
  `<span class="stat">전체 ${D.items.length}건</span><span class="stat">최근 7일 ${week}건</span>`+
  `<span class="stat">마지막 확인 ${esc(D.generated)}</span>`+(g?`<span class="stat">게임 갱신 ${esc(g)}</span>`:'');
function render(){
  document.getElementById('tabs').innerHTML=FILTERS.map(([k,l])=>{
    const n=k==='all'?D.items.length:D.items.filter(i=>i.kind===k).length;
    return `<button class="tab" aria-pressed="${k===cur}" data-k="${k}">${l}<span class="n">${n}</span></button>`}).join('');
  document.querySelectorAll('.tab').forEach(b=>b.onclick=()=>{cur=b.dataset.k;render()});
  const rows=D.items.filter(i=>cur==='all'||i.kind===cur);
  document.getElementById('list').innerHTML=rows.length?rows.map(i=>`
  <article class="card">
    <div class="top"><span class="pill ${i.kind}">${TAGS[i.kind]||'소식'}</span>${isNew(i)?'<span class="pill new">NEW</span>':''}
      <span class="date">${esc(i.date)}</span></div>
    <h2>${esc(i.title_ko||i.title)}</h2>
    <p>${esc(i.summary)}</p>
    ${i.tip?`<div class="tip"><b>아이에게 한 줄</b>${esc(i.tip)}</div>`:''}
    <div class="foot"><span>${esc(i.source)}</span>
      ${i.translated===false?'<span class="warn">번역 안 됨</span>':''}
      <a href="${esc(i.url)}" target="_blank" rel="noopener">원문 보기</a>
      ${i.video?`<a href="${esc(i.video)}" target="_blank" rel="noopener">참고 영상</a>`:''}</div>
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
