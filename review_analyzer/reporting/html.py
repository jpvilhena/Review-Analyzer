"""Offline evidence review and static, exportable temporal figures."""
import html
import json
from datetime import datetime, timezone
from pathlib import Path

STYLE = """body{font:16px/1.5 system-ui;max-width:1100px;margin:30px auto;padding:0 20px;color:#182532}
article{border:1px solid #bdc9d3;border-radius:8px;margin:18px 0;padding:18px} blockquote{border-left:4px solid #247388;padding-left:14px}
pre{white-space:pre-wrap;font:inherit;background:#f3f6f8;padding:12px}label{display:inline-block;margin:8px}textarea{display:block;width:95%;min-height:60px}
button,select,input{font:inherit;padding:8px}table{border-collapse:collapse;width:100%}td,th{padding:8px;border-bottom:1px solid #ccd5dc;text-align:left}
.notice{background:#fff3d5;padding:14px}img{width:100%}small{color:#42566b}header{border-bottom:3px solid #247388;padding-bottom:12px}"""


def escape(value):
    return html.escape(str(value), quote=True)


def utc(value):
    return datetime.fromtimestamp(value, timezone.utc).isoformat()


def page(title, body):
    return f'<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>{escape(title)}</title><style>{STYLE}</style><body>{body}</body></html>'


def write_validation(batch, output):
    """Scores and benchmark splits stay hidden during human assessment."""
    options = "".join(f'<option value="{x}">{x.replace("_", " ")}</option>' for x in
                      ("complaint_request", "praise", "neutral_mention", "unrelated", "uncertain"))
    sentiment_options = "".join(f'<option>{x}</option>' for x in ("positive", "negative", "neutral", "mixed", "uncertain"))
    cards = []
    for item in batch["items"]:
        cards.append(f'''<article data-key="{escape(item['key'])}"><h2>{escape(item['change_id'])} · review {escape(item['review_id'])}</h2>
        <p><b>Patch:</b> {escape(item['patch_text'])}</p><small>Created {utc(item['created_at'])}; last edited {utc(item['updated_at'])}</small>
        <blockquote>{escape(item['passage'])}</blockquote><details><summary>Full review context</summary><pre>{escape(item['review_text'])}</pre></details>
        <p><a href="{escape(item['source'])}" target="_blank" rel="noopener">Steam review</a></p>
        <label>Topic judgment <select class="label"><option value="">Unreviewed</option>{options}</select></label>
        <label>Passage sentiment <select class="sentiment"><option value="">Not labeled</option>{sentiment_options}</select></label>
        <label>Rationale<textarea class="rationale"></textarea></label></article>''')
    data = json.dumps({"batch_id": batch["batch_id"]}).replace("<", "\\u003c")
    body = f'''<header><h1>{escape(batch['case']['game'])} evidence review</h1><p>Batch {batch['batch_id']} · {len(cards)} topic/review pairs · patch {escape(batch['case']['release_date'])} UTC</p></header>
    <p class="notice">Judgments concern the topic in the full review. Passage sentiment is optional and applies to the quoted passage. A complaint/request describes a problem or desired change; praise approves the feature; a neutral mention is factual. Unrelated and uncertain judgments remain separate. Scores and benchmark splits are hidden to reduce anchoring.</p>
    <p>Edits after release cannot establish the original wording. Each completed judgment requires a rationale. Downloads contain labels only; database import records the reviewer identity.</p>
    <button id="save">Download judgments</button> <label>Load saved judgments <input id="load" type="file" accept=".json"></label><p id="status" role="status"></p>
    {''.join(cards)}<script type="application/json" id="batch">{data}</script>
    <script>
    const batch=JSON.parse(document.getElementById('batch').textContent);
    const cards=Array.from(document.querySelectorAll('article[data-key]'));
    document.getElementById('save').onclick=()=>{{
      const annotations=cards.map(c=>({{key:c.dataset.key,label:c.querySelector('.label').value,sentiment:c.querySelector('.sentiment').value,rationale:c.querySelector('.rationale').value}}));
      if(annotations.some(a=>a.label&&!a.rationale.trim())){{document.getElementById('status').textContent='A rationale is missing from a completed judgment.';return;}}
      const blob=new Blob([JSON.stringify({{batch_id:batch.batch_id,annotations}},null,2)],{{type:'application/json'}});
      const url=URL.createObjectURL(blob),link=document.createElement('a');link.href=url;link.download='judgments-'+batch.batch_id+'.json';link.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
      document.getElementById('status').textContent='Judgments downloaded.';
    }};
    document.getElementById('load').onchange=async event=>{{
      try{{const saved=JSON.parse(await event.target.files[0].text());if(saved.batch_id!==batch.batch_id)throw Error('Batch mismatch');
      const values=new Map(saved.annotations.map(a=>[a.key,a]));cards.forEach(c=>{{const a=values.get(c.dataset.key);if(a){{c.querySelector('.label').value=a.label||'';c.querySelector('.sentiment').value=a.sentiment||'';c.querySelector('.rationale').value=a.rationale||'';}}}});
      document.getElementById('status').textContent='Saved judgments loaded.';
      }}catch(error){{document.getElementById('status').textContent=error.message;}}
    }};
    </script>'''
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(page("Evidence review", body), encoding="utf-8")


def write_report(report, output):
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    image = output.with_suffix(".png")
    from review_analyzer.reporting.plots import plot_timeline
    plot_timeline(report, image)
    cards = []
    changes = {c["id"]: c["text"] for c in report["case"]["changes"]}
    for match in report["matches"]:
        cards.append(f'''<article><h2>{escape(match['change_id'])} · {escape(match.get('validation','unreviewed'))}</h2>
        <p>Review {escape(match['review_id'])} · {escape(match['period'])} · similarity {match['similarity']:.3f}</p>
        <p>Patch: {escape(changes[match['change_id']])}</p><small>Created {utc(match['created_at'])}; edited {utc(match['updated_at'])}</small>
        <blockquote>{escape(match['passage'])}</blockquote><details><summary>Full review</summary><pre>{escape(match.get('review_text',''))}</pre></details>
        <p>Model sentiment: {escape(match.get('sentiment',{}).get('label','not analyzed'))} · <a href="{escape(match['source'])}">Source review</a></p></article>''')
    warnings = ''.join(f'<li>{escape(w)}</li>' for w in report["limitations"])
    table_rows = ''.join(f"<tr><td>{escape(r['week_start'])}</td><td>{escape(r['period'])}</td><td>{escape(r['topic'])}</td><td>{r['reviews']}</td><td>{r['matched_reviews']}</td><td>{r.get('confirmed_complaints',0)}</td><td>{escape(r['sentiment_counts'])}</td></tr>"
                         for r in report["timeline"] if r["reviews"])
    body = f'''<header><h1>{escape(report['case']['game'])} update analysis</h1><p>Run {report.get('run_id','')} · {report['review_count']} reviews · method {escape(report['method'])}</p></header>
    <p class="notice">Only human-confirmed complaint/request judgments count as confirmed complaints. Unreviewed candidates remain exploratory. Figures do not establish causation.</p>
    <ul>{warnings}</ul><img src="{escape(image.name)}" alt="Weekly topic evidence and sentiment around patch release">
    <details><summary>Weekly counts and denominators</summary><table><thead><tr><th>Week</th><th>Period</th><th>Topic</th><th>Reviews</th><th>Candidates</th><th>Confirmed complaints</th><th>Sentiment counts</th></tr></thead><tbody>{table_rows}</tbody></table></details>
    <h2>Evidence</h2>{''.join(cards)}'''
    output.write_text(page("Update analysis", body), encoding="utf-8")
