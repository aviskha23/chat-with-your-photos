"""
Run 10 test queries against the local API and build quality_report.html.

Usage (uvicorn must be running):
    python quality_check.py

Then open quality_report.html in your browser, mark each query, and click
"Copy summary" to get a Markdown table for your README.
"""

import html
import json
import urllib.parse
import urllib.request

BASE = "http://127.0.0.1:8000"
TOP_K = 6

# A mix of easy queries and ones CLIP is known to struggle with.
QUERIES = [
    "a dog playing outside",          # common object + scene
    "people on a beach",              # scene
    "a man riding a bike",            # action
    "a woman in a red dress",         # color + attribute
    "two people sitting on a bench",  # counting
    "a street with no cars",          # negation
    "a dog to the left of a bicycle", # spatial relation
    "someone reading a sign",         # text / fine detail
    "loneliness",                     # abstract concept
    "asdkjhqwe",                      # gibberish baseline
]


def search(query):
    url = (
        f"{BASE}/search-by-text?q={urllib.parse.quote(query)}"
        f"&top_k={TOP_K}"
    )
    with urllib.request.urlopen(url, timeout=30) as response:
        return json.load(response)["results"]


def esc(value):
    return html.escape(str(value), quote=True)


sections = []
print(f"{'query':36} top-1   top-{TOP_K}")

for query in QUERIES:
    results = search(query)
    if not results:
        print(f"{query:36} no results")
        top1 = 0.0
        cells = '<p>No results returned.</p>'
    else:
        top1 = float(results[0]["score"])
        last = float(results[-1]["score"])
        print(f"{query:36} {top1:.3f}   {last:.3f}")

        cells = "".join(
            f'<figure><img src="{BASE}{esc(result["image_url"])}" '
            f'alt="Result for {esc(query)}">'
            f'<figcaption>{result["rank"]} &nbsp; '
            f'{float(result["score"]):.3f}</figcaption></figure>'
            for result in results
        )

    sections.append(f"""
<section data-q="{esc(query)}" data-top1="{top1:.3f}">
  <h2>{esc(query)}</h2>
  <div class="row">{cells}</div>
  <div class="verdict">
    <select aria-label="Verdict for {esc(query)}">
      <option>good</option>
      <option>mixed</option>
      <option>poor</option>
    </select>
    <input type="text" placeholder="What went right or wrong?"
           aria-label="Notes for {esc(query)}">
  </div>
</section>""")

page = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Search quality report</title>
<style>
  body {{ font-family: system-ui, sans-serif; margin: 32px; max-width: 1200px; }}
  section {{ margin: 0 0 40px; }}
  h2 {{ margin: 0 0 10px; font-size: 1.2rem; }}
  .row {{ display: flex; gap: 8px; flex-wrap: wrap; }}
  figure {{ margin: 0; }}
  img {{ display: block; height: 170px; max-width: 280px; object-fit: contain; background: #ddd; }}
  figcaption {{ font-size: .8rem; color: #555; margin-top: 4px; font-variant-numeric: tabular-nums; }}
  .verdict {{ margin-top: 10px; display: flex; gap: 10px; }}
  .verdict input {{ flex: 1; max-width: 520px; padding: 6px; }}
  button {{ padding: 10px 20px; font: inherit; cursor: pointer; }}
  pre {{ background: #f3f3f3; padding: 14px; white-space: pre-wrap; }}
  @media (max-width: 600px) {{ body {{ margin: 16px; }} .verdict {{ flex-direction: column; }} }}
</style>
</head>
<body>
<h1>Search quality report</h1>
<p>Judge each query by eye, add a short note, then copy the summary.</p>
{''.join(sections)}
<button id="copy" type="button">Copy summary</button>
<pre id="out"></pre>
<script>
document.getElementById("copy").addEventListener("click", async () => {{
  let md = "| Query | Top-1 score | Verdict | Notes |\\n|---|---:|---|---|\\n";
  document.querySelectorAll("section").forEach((section) => {{
    const verdict = section.querySelector("select").value;
    const note = section.querySelector("input").value
      .replace(/\\\\|/g, "/")
      .replace(/\\r?\\n/g, " ");
    md += `| ${{section.dataset.q}} | ${{section.dataset.top1}} | ${{verdict}} | ${{note}} |\\n`;
  }});
  document.getElementById("out").textContent = md;
  try {{
    await navigator.clipboard.writeText(md);
  }} catch (_) {{
    // The Markdown remains visible in the box for manual copying.
  }}
}});
</script>
</body>
</html>
"""

with open("quality_report.html", "w", encoding="utf-8") as report_file:
    report_file.write(page)

print("\nWrote quality_report.html. Open it in your browser.")
