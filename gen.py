#!/usr/bin/env python3
from pathlib import Path
import html
import re

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "articles"


from clusters import CLUSTERS, lookup


NAV_ROOT = """        <a href="index.html">Роли</a>
        <a href="plan.html">Таблица статей</a>
        <a href="clusters.html">Кластеры</a>"""

NAV_ARTICLE = """        <a href="../index.html">Роли</a>
        <a href="../plan.html">Таблица статей</a>
        <a href="../clusters.html">Кластеры</a>"""


def inline(text: str) -> str:
    return re.sub(
        r"\[([^\]]+)\]\(([^)]+)\)",
        lambda m: f'<a href="{html.escape(m.group(2))}">{m.group(1)}</a>',
        text,
    )


def md_to_html(text: str) -> str:
    lines = [ln.rstrip() for ln in text.strip().splitlines()]
    out, para, ul, ol = [], [], [], []

    def flush_p():
        nonlocal para
        if para:
            out.append("<p>" + inline(" ".join(para)) + "</p>")
            para = []

    def flush_ul():
        nonlocal ul
        if ul:
            out.append("<ul>" + "".join(f"<li>{inline(i)}</li>" for i in ul) + "</ul>")
            ul = []

    def flush_ol():
        nonlocal ol
        if ol:
            out.append("<ol>" + "".join(f"<li>{inline(i)}</li>" for i in ol) + "</ol>")
            ol = []

    def flush_all():
        flush_p()
        flush_ul()
        flush_ol()

    for line in lines:
        numbered = re.match(r"^\d+\.\s+(.*)$", line)
        if not line:
            flush_all()
        elif line.startswith("### "):
            flush_all()
            out.append(f"<h3>{inline(line[4:])}</h3>")
        elif line.startswith("## "):
            flush_all()
            out.append(f"<h2>{inline(line[3:])}</h2>")
        elif line.startswith("- "):
            flush_p()
            flush_ol()
            ul.append(line[2:])
        elif numbered:
            flush_p()
            flush_ul()
            ol.append(numbered.group(1))
        else:
            flush_ul()
            flush_ol()
            para.append(line)
    flush_all()
    return "\n".join(out)


def page(a: dict, related: list[dict]) -> str:
    related_html = ""
    if related:
        items = "".join(
            f'<li><a href="{r["slug"]}.html">{html.escape(r["title"])}</a></li>'
            for r in related
        )
        related_html = f'<section class="related"><h2>Читать далее</h2><ul>{items}</ul></section>'
    platform = a.get("platforms") or "—"
    meta = lookup(a)
    tags = "".join(f"<li>{html.escape(w)}</li>" for w in meta["words"])
    n = len(meta["words"])
    lead_html = (
        f'      <p class="lead">{html.escape(a["lead"])}</p>\n' if a.get("lead") else ""
    )
    return f"""<!doctype html>
<html lang="ru">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>{html.escape(a["title"])}</title>
    <link rel="stylesheet" href="../style.css" />
  </head>
  <body>
    <header>
      <strong>Контент-план</strong>
      <nav>
{NAV_ARTICLE}
      </nav>
    </header>
    <main class="article">
      <p class="crumbs"><a href="../plan.html">Таблица статей</a> · {html.escape(a["product"])} · <a href="../clusters.html#{meta["id"]}">{html.escape(meta["name"])}</a></p>
      <p class="meta">{html.escape(a["role"])} · {html.escape(a["cjm"])} · {html.escape(a["kind"])} · {html.escape(platform)}</p>
      <h1>{html.escape(a["title"])}</h1>
{lead_html}      <details class="semantics">
        <summary>Семантика кластера · {n} фраз</summary>
        <ul class="tags">{tags}</ul>
      </details>
      {md_to_html(a["body"])}
      {related_html}
    </main>
    <footer><a href="../plan.html">← Назад к таблице</a></footer>
  </body>
</html>
"""


def related_for(a: dict, all_a: list[dict]) -> list[dict]:
    out = []
    seen = {a["slug"]}

    def add(slug):
        if slug in seen:
            return
        for x in all_a:
            if x["slug"] == slug:
                out.append(x)
                seen.add(slug)
                return

    if a["kind"] == "Pillar":
        return []

    if a["hub"] == "both":
        add("fl-guide")
        add("bdp-guide")
    else:
        pillar = next(
            x for x in all_a if x["kind"] == "Pillar" and x["hub"] == a["hub"]
        )
        add(pillar["slug"])
    for x in all_a:
        if (
            x["slug"] != a["slug"]
            and x["cluster"] == a["cluster"]
            and (x["hub"] == a["hub"] or a["hub"] == "both" or x["hub"] == "both")
        ):
            add(x["slug"])
    if a["slug"] == "data-governance-ai":
        add("seven-data-quality")
        add("reduce-ai-risks-governance")
        add("mlops-dataops")
    return out[:12]


def link_table(plan: str, articles: list[dict]) -> str:
    for a in articles:
        title = a["title"]
        href = f'articles/{a["slug"]}.html'
        count = plan.count(f"<td>{title}</td>")
        plan = plan.replace(
            f"<td>{title}</td>",
            f'<td><a href="{href}">{title}</a></td>',
            count or 1,
        )
    return plan


PILLARS = {
    "fl": ("fl-guide", "Федеративное обучение"),
    "bdp": ("bdp-guide", "Big Data Platform"),
}


def pillar_cell(article: dict) -> str:
    hubs = ("fl", "bdp") if article["hub"] == "both" else (article["hub"],)
    parts = []
    for hub in hubs:
        slug, label = PILLARS[hub]
        parts.append(f'<a href="articles/{slug}.html">{html.escape(label)}</a>')
    return "<td>" + " · ".join(parts) + "</td>"


def relabel_clusters(plan: str, articles: list[dict]) -> str:
    by_slug = {a["slug"]: a for a in articles}

    def repl_row(m: re.Match) -> str:
        row = m.group(0)
        sm = re.search(r'href="articles/([a-z0-9-]+)\.html"', row)
        if not sm:
            return row
        tds = list(re.finditer(r"<td\b.*?</td>", row, re.S))
        last = tds[-1]
        new = pillar_cell(by_slug[sm.group(1)])
        return row[: last.start()] + new + row[last.end() :]

    plan = plan.replace("<th>Кластер</th>", "<th>Pillar</th>")
    plan = re.sub(r"<tr\b[^>]*>.*?</tr>", repl_row, plan, flags=re.S)
    plan = re.sub(
        r'(<nav>\s*)<a href="index.html">Роли</a>\s*<a href="plan.html">Таблица статей</a>(\s*</nav>)',
        r"\1" + NAV_ROOT + r"\2",
        plan,
    )
    return plan


def write_clusters_page(articles: list[dict]) -> None:
    fl_keys = [k for k in CLUSTERS if k[0] == "fl"]
    bdp_keys = [k for k in CLUSTERS if k[0] == "bdp"]

    def block(title: str, keys: list) -> str:
        cards = []
        for key in keys:
            meta = CLUSTERS[key]
            hub, old = key
            arts = [
                a
                for a in articles
                if (a["hub"] if a["hub"] != "both" else "fl") == hub
                and a["cluster"] == old
            ]
            tags = "".join(f"<li>{html.escape(w)}</li>" for w in meta["words"])
            n = len(meta["words"])
            links = "".join(
                f'<li><a href="articles/{a["slug"]}.html">{html.escape(a["title"])}</a></li>'
                for a in arts
            )
            cards.append(
                f"""<article class="cluster-card" id="{meta["id"]}">
          <p class="old">{html.escape(old)}</p>
          <h3>{html.escape(meta["name"])}</h3>
          <details class="semantics-fold">
            <summary>Семантика · {n} фраз</summary>
            <ul class="tags">{tags}</ul>
          </details>
          <ul class="arts">{links}</ul>
        </article>"""
            )
        return f'<h2 class="block">{html.escape(title)}</h2>\n      <div class="cluster-grid">\n        {"".join(cards)}\n      </div>'

    html_page = f"""<!doctype html>
<html lang="ru">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>Контент-план — кластеры</title>
    <link rel="stylesheet" href="style.css" />
  </head>
  <body>
    <header>
      <strong>Контент-план</strong>
      <nav>
{NAV_ROOT}
      </nav>
    </header>
    <main>
      <h1>Кластеры и семантика</h1>
      <p class="lead">
        Имя и семантика взяты из направления статей кластера:
        федеративное обучение или Big Data Platform. Фразы свёрнуты — откройте блок, чтобы увидеть ядро.
      </p>
      <p class="toolbar">
        <button type="button" data-fold="open">Развернуть все</button>
        <button type="button" data-fold="close">Свернуть все</button>
      </p>
      {block("Федеративное обучение", fl_keys)}
      {block("Big Data Platform", bdp_keys)}
    </main>
    <footer><a href="plan.html">← К таблице статей</a></footer>
    <script>
      const folds = () => document.querySelectorAll("details.semantics-fold");
      document.querySelectorAll("[data-fold]").forEach((btn) => {{
        btn.addEventListener("click", () => {{
          const open = btn.dataset.fold === "open";
          folds().forEach((el) => {{ el.open = open; }});
        }});
      }});
      const target = location.hash && document.querySelector(location.hash + " details");
      if (target) target.open = true;
      window.addEventListener("hashchange", () => {{
        const el = location.hash && document.querySelector(location.hash + " details");
        if (el) el.open = true;
      }});
    </script>
  </body>
</html>
"""
    (ROOT / "clusters.html").write_text(html_page, encoding="utf-8")


def main():
    from content import ARTICLES as items

    OUT.mkdir(exist_ok=True)
    slugs = [a["slug"] for a in items]
    assert len(slugs) == len(set(slugs)), "duplicate slugs"
    for a in items:
        rel = related_for(a, items)
        (OUT / f"{a['slug']}.html").write_text(page(a, rel), encoding="utf-8")
    plan = (ROOT / "plan.html").read_text(encoding="utf-8")
    plan = re.sub(r'<td><a href="articles/[^"]+">([^<]+)</a></td>', r"<td>\1</td>", plan)
    plan = re.sub(
        r'<td><a href="clusters.html#[^"]+">([^<]+)</a></td>', r"<td>\1</td>", plan
    )
    plan = link_table(plan, items)
    plan = relabel_clusters(plan, items)
    (ROOT / "plan.html").write_text(plan, encoding="utf-8")
    write_clusters_page(items)
    linked = (ROOT / "plan.html").read_text(encoding="utf-8")
    unmatched = [a["title"] for a in items if f'articles/{a["slug"]}.html' not in linked]
    if unmatched:
        raise SystemExit("not linked: " + " | ".join(unmatched))
    print(f"wrote {len(items)} articles and {len(CLUSTERS)} clusters")


if __name__ == "__main__":
    main()
