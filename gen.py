#!/usr/bin/env python3
from pathlib import Path
import html
import re

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "articles"


from clusters import CLUSTERS, lookup


NAV_ROOT = ""
NAV_ARTICLE = ""


def inline(text: str) -> str:
    text = re.sub(
        r"\[([^\]]+)\]\(([^)]+)\)",
        lambda m: f'<a href="{html.escape(m.group(2))}">{m.group(1)}</a>',
        text,
    )
    return re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", text)


def table_html(rows: list[str]) -> str:
    parsed = []
    for row in rows:
        if re.match(r"^\|?\s*:?-+:?\s*(\|\s*:?-+:?\s*)+\|?\s*$", row):
            continue
        cells = [c.strip() for c in row.strip().strip("|").split("|")]
        parsed.append(cells)
    if not parsed:
        return ""
    head, *body = parsed
    thead = (
        "<thead><tr>"
        + "".join(f"<th>{inline(c)}</th>" for c in head)
        + "</tr></thead>"
    )
    tbody = (
        "<tbody>"
        + "".join(
            "<tr>" + "".join(f"<td>{inline(c)}</td>" for c in r) + "</tr>"
            for r in body
        )
        + "</tbody>"
    )
    return f'<div class="md-table"><table>{thead}{tbody}</table></div>'


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

    i = 0
    while i < len(lines):
        line = lines[i]
        numbered = re.match(r"^\d+\.\s+(.*)$", line)
        if line.startswith("|"):
            flush_all()
            rows = []
            while i < len(lines) and lines[i].startswith("|"):
                rows.append(lines[i])
                i += 1
            html_table = table_html(rows)
            if html_table:
                out.append(html_table)
            continue
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
        i += 1
    flush_all()
    return "\n".join(out)


def num_label(nums: list[dict]) -> str:
    if not nums:
        return ""
    bits = [
        f"№ {x['n']} / {x['total']} · {html.escape(x['hub'])}" for x in nums
    ]
    return " · ".join(bits) + " · "


def page(a: dict, related: list[dict], nums: list[dict] | None = None) -> str:
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
    prefix = num_label(nums or [])
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
    </header>
    <main class="article">
      <p class="crumbs"><a href="../index.html">Таблица статей</a> · {html.escape(a["product"])} · {html.escape(meta["name"])}</p>
      <p class="meta">{prefix}{html.escape(a["role"])} · {html.escape(a["cjm"])} · {html.escape(a["kind"])} · {html.escape(platform)}</p>
      <h1>{html.escape(a["title"])}</h1>
{lead_html}      <details class="semantics">
        <summary>Семантика кластера · {n} фраз</summary>
        <ul class="tags">{tags}</ul>
      </details>
      {md_to_html(a["body"])}
      {related_html}
    </main>
    <footer><a href="../index.html">Таблица статей</a></footer>
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
    if a["slug"] == "train-ai-multi-company":
        add("fl-vs-centralized")
        add("fl-sandbox-or-embeddings")
        add("fl-what-is")
        add("fate-flower-nvflare")
        add("fl-antifraud")
        add("data-governance-ai")
        add("homomorphic-encryption")
    if a["slug"] == "fl-vs-centralized":
        add("fl-sandbox-or-embeddings")
        add("fl-what-is")
        add("train-ai-multi-company")
        add("replace-data-lake")
        add("fl-antifraud")
        add("data-governance-ai")
    if a["slug"] == "data-governance-ai":
        add("mlops-dataops")
        add("eighty-percent-data")
        add("train-ai-multi-company")
        add("fl-what-is")
        add("confidential-computing-partner")
        add("fate-flower-nvflare")
        add("scale-to-federated")
    if a["slug"] == "tco-big-data":
        add("choose-bdp-15")
        add("vendor-lock-in")
        add("opensource-enterprise")
        add("ha-big-data-platform")
    if a["slug"] == "choose-bdp-15":
        add("tco-big-data")
        add("vendor-lock-in")
        add("opensource-enterprise")
        add("scale-to-federated")
        add("ha-big-data-platform")
        add("ai-ready-platform")
    if a["slug"] == "big-data-2026":
        add("eighty-percent-data")
        add("vendor-lock-in")
        add("opensource-enterprise")
        add("tco-big-data")
        add("scale-to-federated")
        add("ha-big-data-platform")
        add("ai-ready-platform")
        add("choose-bdp-15")
        add("mlops-dataops")
    if a["slug"] == "eighty-percent-data":
        add("ai-ready-platform")
        add("mlops-dataops")
        add("data-governance-ai")
        add("ha-big-data-platform")
        add("bdp-guide")
    if a["slug"] == "mlops-dataops":
        add("ai-ready-platform")
        add("data-governance-ai")
        add("eighty-percent-data")
    if a["slug"] == "ai-ready-platform":
        add("mlops-dataops")
        add("ha-big-data-platform")
        add("scale-to-federated")
        add("choose-bdp-15")
        add("data-governance-ai")
    if a["slug"] == "vendor-lock-in":
        add("opensource-enterprise")
        add("tco-big-data")
        add("choose-bdp-15")
    if a["slug"] == "opensource-enterprise":
        add("vendor-lock-in")
        add("tco-big-data")
        add("choose-bdp-15")
    if a["slug"] == "scale-to-federated":
        add("ha-big-data-platform")
        add("ai-ready-platform")
        add("data-governance-ai")
        add("fate-flower-nvflare")
        add("choose-bdp-15")
    if a["slug"] == "ha-big-data-platform":
        add("scale-to-federated")
        add("ai-ready-platform")
        add("tco-big-data")
        add("choose-bdp-15")
    if a["slug"] == "confidential-computing-partner":
        add("homomorphic-encryption")
        add("confidential-computing-152")
        add("federated-xgboost-how")
        add("fate-flower-nvflare")
        add("fl-what-is")
        add("vfl-or-hfl")
    if a["slug"] == "vfl-or-hfl":
        add("fl-vs-centralized")
        add("train-ai-multi-company")
        add("fl-sandbox-or-embeddings")
        add("fl-what-is")
        add("raise-scoring-accuracy")
        add("fl-antifraud")
        add("federated-xgboost-how")
        add("homomorphic-encryption")
        add("confidential-computing-152")
        add("data-governance-ai")
    if a["slug"] == "raise-scoring-accuracy":
        add("vfl-or-hfl")
        add("fate-flower-nvflare")
        add("federated-xgboost-how")
        add("homomorphic-encryption")
        add("fl-what-is")
        add("partner-scoring-quality")
        add("fl-uplift-cases")
    if a["slug"] == "partner-scoring-quality":
        add("replace-data-lake")
        add("fl-uplift-cases")
        add("vfl-or-hfl")
        add("federated-xgboost-how")
        add("fl-what-is")
        add("fate-flower-nvflare")
        add("federated-xgboost-experiments")
        add("raise-scoring-accuracy")
    if a["slug"] == "replace-data-lake":
        add("partner-scoring-quality")
        add("fl-uplift-cases")
        add("fl-vs-centralized")
        add("fl-what-is")
        add("homomorphic-encryption")
        add("fate-flower-nvflare")
        add("federated-xgboost-how")
    if a["slug"] == "fl-uplift-cases":
        add("partner-scoring-quality")
        add("replace-data-lake")
        add("federated-xgboost-experiments")
        add("federated-xgboost-how")
        add("fl-sandbox-or-embeddings")
        add("fate-flower-nvflare")
        add("fl-what-is")
        add("raise-scoring-accuracy")
        add("fl-antifraud")
        add("confidential-computing-partner")
    if a["slug"] == "fl-antifraud":
        add("fl-uplift-cases")
        add("fl-what-is")
        add("vfl-or-hfl")
        add("fate-flower-nvflare")
        add("homomorphic-encryption")
        add("replace-data-lake")
        add("train-ai-multi-company")
        add("confidential-computing-partner")
    if a["slug"] == "federated-xgboost-how":
        add("vfl-or-hfl")
        add("fate-flower-nvflare")
        add("homomorphic-encryption")
        add("raise-scoring-accuracy")
        add("fl-what-is")
        add("federated-xgboost-experiments")
    if a["slug"] == "homomorphic-encryption":
        add("confidential-computing-partner")
        add("federated-xgboost-how")
        add("confidential-computing-152")
        add("fate-flower-nvflare")
        add("vfl-or-hfl")
        add("fl-what-is")
    if a["slug"] == "why-classic-xgboost-fails":
        add("federated-xgboost-how")
        add("vfl-or-hfl")
        add("fate-flower-nvflare")
        add("fl-sandbox-or-embeddings")
        add("fl-what-is")
        add("raise-scoring-accuracy")
        add("federated-xgboost-experiments")
    if a["slug"] == "federated-xgboost-experiments":
        add("federated-xgboost-how")
        add("why-classic-xgboost-fails")
        add("fl-sandbox-or-embeddings")
        add("fate-flower-nvflare")
        add("fl-what-is")
        add("raise-scoring-accuracy")
        add("fl-uplift-cases")
    if a["slug"] == "fate-flower-nvflare":
        add("federated-xgboost-how")
        add("vfl-or-hfl")
        add("fl-what-is")
        add("confidential-computing-partner")
        add("homomorphic-encryption")
        add("raise-scoring-accuracy")
        add("partner-scoring-quality")
        add("fl-antifraud")
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
        r"<header>\s*<strong>Контент-план</strong>\s*<nav>.*?</nav>\s*</header>",
        "<header>\n      <strong>Контент-план</strong>\n    </header>",
        plan,
        count=1,
        flags=re.S,
    )
    return plan


def number_plan(plan: str) -> str:
    if '<th class="n">№</th>' not in plan and "<th>№</th>" not in plan:
        plan = plan.replace(
            "<th>Тип пользователя</th>",
            '<th class="n">№</th>\n              <th>Тип пользователя</th>',
        )

    def number_tbody(m: re.Match) -> str:
        body = m.group(0)
        n = 0

        def num_row(rm: re.Match) -> str:
            nonlocal n
            row = rm.group(0)
            if "<th" in row:
                return row
            n += 1
            cell = f'<td class="n">{n}</td>'
            if re.search(r'<td class="n">\d+</td>', row):
                return re.sub(r'<td class="n">\d+</td>', cell, row, count=1)
            return re.sub(
                r"(<tr\b[^>]*>\s*)",
                rf"\1{cell}\n              ",
                row,
                count=1,
            )

        return re.sub(r"<tr\b[^>]*>.*?</tr>", num_row, body, flags=re.S)

    return re.sub(r"<tbody>.*?</tbody>", number_tbody, plan, flags=re.S)


def extract_numbers(plan: str) -> dict[str, list[dict]]:
    result: dict[str, list[dict]] = {}
    parts = re.split(r"(<h2 class=\"block\">.*?</h2>)", plan)
    i = 1
    while i < len(parts):
        heading = re.search(r"<h2 class=\"block\">(.*?)</h2>", parts[i])
        hub = heading.group(1) if heading else ""
        chunk = parts[i + 1] if i + 1 < len(parts) else ""
        tbody = re.search(r"<tbody>(.*?)</tbody>", chunk, re.S)
        slugs: list[str] = []
        if tbody:
            for row in re.finditer(r"<tr\b[^>]*>.*?</tr>", tbody.group(1), re.S):
                sm = re.search(
                    r'href="articles/([a-z0-9-]+)\.html"', row.group(0)
                )
                if sm:
                    slugs.append(sm.group(1))
        total = len(slugs)
        for n, slug in enumerate(slugs, 1):
            result.setdefault(slug, []).append(
                {"hub": hub, "n": n, "total": total}
            )
        i += 2
    return result


def write_clusters_page(articles: list[dict], numbers: dict | None = None) -> None:
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

            def num_for(slug: str) -> str:
                for x in (numbers or {}).get(slug, []):
                    if x["hub"] == title:
                        return f'<span class="n">{x["n"]}.</span> '
                found = (numbers or {}).get(slug, [])
                if found:
                    return f'<span class="n">{found[0]["n"]}.</span> '
                return ""

            links = "".join(
                f'<li>{num_for(a["slug"])}<a href="articles/{a["slug"]}.html">{html.escape(a["title"])}</a></li>'
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
    plan = (ROOT / "plan.html").read_text(encoding="utf-8")
    plan = re.sub(r'<td><a href="articles/[^"]+">([^<]+)</a></td>', r"<td>\1</td>", plan)
    plan = re.sub(
        r'<td><a href="clusters.html#[^"]+">([^<]+)</a></td>', r"<td>\1</td>", plan
    )
    plan = link_table(plan, items)
    plan = relabel_clusters(plan, items)
    plan = number_plan(plan)
    plan = re.sub(
        r"<footer>.*?</footer>",
        "<footer><a href=\"index.html\">Таблица статей</a></footer>",
        plan,
        count=1,
        flags=re.S,
    )
    nums = extract_numbers(plan)
    for a in items:
        rel = related_for(a, items)
        (OUT / f"{a['slug']}.html").write_text(
            page(a, rel, nums.get(a["slug"], [])), encoding="utf-8"
        )
    (ROOT / "plan.html").write_text(plan, encoding="utf-8")
    (ROOT / "index.html").write_text(plan, encoding="utf-8")
    clusters_page = ROOT / "clusters.html"
    if clusters_page.exists():
        clusters_page.unlink()
    linked = (ROOT / "plan.html").read_text(encoding="utf-8")
    unmatched = [a["title"] for a in items if f'articles/{a["slug"]}.html' not in linked]
    if unmatched:
        raise SystemExit("not linked: " + " | ".join(unmatched))
    print(f"wrote {len(items)} articles")


if __name__ == "__main__":
    main()
