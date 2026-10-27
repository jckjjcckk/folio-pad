# /// script
# requires-python = ">=3.12"
# dependencies = ["pillow"]
# ///
"""One page that links every overlay: out/gallery.html. Run after build_overlay.py.  uv run build_gallery.py"""
import html
import json
from pathlib import Path

from PIL import Image

OUT = Path(__file__).parent / "out"
cards = []
for j in sorted(OUT.glob("final-*.json")):
    d = json.loads(j.read_text())
    name = j.stem[6:]
    thumb = OUT / f"thumb-{name}.jpg"
    if (OUT / f"final-{name}.png").exists():
        im = Image.open(OUT / f"final-{name}.png").convert("RGB"); im.thumbnail((640, 900)); im.save(thumb, quality=80)
    labels = d.get("labels") or {}
    parts = ", ".join(sorted({p for s in d.get("systems", []) for p in (s.get("parts") or []) if p})) or "–"
    doubtful = len(labels.get("doubtful_measures") or [])
    title = labels.get("title") or ""
    composer = labels.get("composer") or ""
    cards.append(f"""
<a class="card" href="{name and f'final-{name}.html'}">
  <img src="thumb-{name}.jpg" loading="lazy" alt="">
  <div class="meta">
    <div class="name">{html.escape(name)}</div>
    <div class="line">{len(d['measures'])} measures · {len(d.get('systems', []))} systems · first {labels.get('first_measure_number', '?')}{' · ' + str(doubtful) + ' doubtful' if doubtful else ''}</div>
    <div class="line dim">{html.escape((title + ' — ' + composer).strip(' —'))}</div>
    <div class="line dim">{html.escape(parts)}</div>
    <div class="line dim">{d.get('latency_s', '?')} s · ${d.get('cost_usd', 0):.3f} · {d.get('engine', '')}</div>
  </div>
</a>""")
page = f"""<!doctype html><meta charset="utf-8"><title>Measure overlays</title>
<style>
body{{margin:0;background:#f4f3ef;font:15px/1.4 -apple-system,system-ui,sans-serif;color:#1b1b1b}}
header{{padding:20px 28px;background:#fff;border-bottom:1px solid #ddd}} h1{{margin:0;font-size:22px}} header p{{margin:6px 0 0;color:#555}}
.grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:18px;padding:24px 28px}}
.card{{display:block;background:#fff;border:1px solid #ddd;border-radius:10px;overflow:hidden;color:inherit;text-decoration:none;box-shadow:0 1px 2px rgba(0,0,0,.05)}}
.card:hover{{border-color:#2a6fdb}} .card img{{width:100%;display:block;background:#eee;aspect-ratio:3/4;object-fit:cover;object-position:top}}
.meta{{padding:10px 12px 12px}} .name{{font-weight:600;word-break:break-all}} .line{{font-size:13px}} .dim{{color:#666}}
</style>
<header><h1>Measure overlays — OpenCV geometry + Muse Spark labels</h1><p>{len(cards)} pages. Click a page to open the tappable overlay. Numbers are the measure numbers Spark assigned; red = doubtful.</p></header>
<div class="grid">{''.join(cards)}</div>"""
(OUT / "gallery.html").write_text(page)
print(f"out/gallery.html {len(cards)} cards")
