"""Pre-render PostgreSQL manuals into a static site (docs/books/<id>/...).

Usage: python build.py [book-id ...]   (default: all)
Requires: pip install pymupdf pillow
Source PDFs are read from the Downloads folder and are never committed.
"""
import io, json, os, re, sys
from multiprocessing import Pool
import fitz
from PIL import Image

DL = os.path.expanduser(r"~\Downloads")
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "docs", "books")
SCALE, QUALITY, CHUNK = 1.25, 55, 20
BOOKS = {
    "16": ("PostgreSQL 16.15 Documentation.pdf", "16.15"),
    "17": ("PostgreSQL 17.11 Documentation.pdf", "17.11"),
    "18": ("PostgreSQL 18.6 Documentation.pdf", "18.6"),
    "19": ("postgresql-19-A4.pdf", "19"),
    "citus": ("Citus Documentation.pdf", "13.0.1"),
}
TITLES = {"citus": "Citus"}
CH = re.compile(r"^(Chapter \d+\. .+|Part [IVX]+\. .+|Appendix [A-Z]\. .+|Preface|Index|Bibliography)\s*$")


def page_lines(page):
    w = page.rect.width
    k = 1000 / w
    out = []
    for b in page.get_text("dict")["blocks"]:
        for ln in b.get("lines", []):
            t = "".join(s["text"] for s in ln["spans"]).rstrip()
            if not t.strip():
                continue
            x0, y0, x1, y1 = ln["bbox"]
            out.append([round(x0 * k), round(y0 * k), round((x1 - x0) * k), round((y1 - y0) * k), t])
    return out


def work(args):
    book, path, start, end = args
    d = fitz.open(path)
    base = os.path.join(OUT, book)
    texts, lines = [], {}
    for i in range(start, end):
        pg = d[i]
        f = os.path.join(base, "p", f"{i + 1}.webp")
        if not os.path.exists(f):
            p = pg.get_pixmap(matrix=fitz.Matrix(SCALE, SCALE), colorspace=fitz.csGRAY)
            Image.frombytes("L", (p.width, p.height), p.samples).save(f, "WEBP", quality=QUALITY, method=4)
        lines[i + 1] = page_lines(pg)
        texts.append(" ".join(l[4] for l in lines[i + 1]))
    with open(os.path.join(base, "t", f"{start // CHUNK}.json"), "w", encoding="utf-8") as fh:
        json.dump(lines, fh, ensure_ascii=False, separators=(",", ":"))
    return start, texts


def toc_for(d):
    toc = [[p, t.strip()] for lvl, t, p in d.get_toc() if lvl <= 2 and p > 0]
    if len(toc) > 10:
        return toc
    toc = []
    for i in range(len(d)):
        head = d[i].get_text().split("\n", 4)
        if head[0].strip() == "CHAPTER" and len(head) > 2:
            toc.append([i + 1, f"Chapter {len(toc) + 1}. " + head[2].strip().title().replace("Sql", "SQL").replace("Api", "API").replace(" An ", " an ")])
    if len(toc) >= 10:
        return toc
    toc = []
    for i in range(len(d)):
        for ln in d[i].get_text().split("\n", 3)[:3]:
            ln = ln.strip()
            if CH.match(ln):
                if not toc or toc[-1][1] != ln:
                    toc.append([i + 1, ln])
                break
    return toc


def build(book):
    fn, label = BOOKS[book]
    path = os.path.join(DL, fn)
    d = fitz.open(path)
    base = os.path.join(OUT, book)
    os.makedirs(os.path.join(base, "p"), exist_ok=True)
    os.makedirs(os.path.join(base, "t"), exist_ok=True)
    n, r = len(d), d[0].rect
    jobs = [(book, path, s, min(s + CHUNK, n)) for s in range(0, n, CHUNK)]
    texts = {}
    with Pool(max(2, (os.cpu_count() or 4) - 1)) as pool:
        for k, (s, t) in enumerate(pool.imap_unordered(work, jobs)):
            texts[s] = t
            if k % 10 == 0:
                print(book, f"{k + 1}/{len(jobs)}", flush=True)
    allt = [x for s in sorted(texts) for x in texts[s]]
    meta = {"id": book, "label": label, "pages": n, "w": r.width, "h": r.height, "chunk": CHUNK, "toc": toc_for(d)}
    if book in TITLES:
        meta["title"] = TITLES[book]
    json.dump(meta, open(os.path.join(base, "meta.json"), "w"), separators=(",", ":"))
    json.dump(allt, open(os.path.join(base, "search.json"), "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
    print(book, "done", n, "pages")


if __name__ == "__main__":
    for b in (sys.argv[1:] or list(BOOKS)):
        build(b)
