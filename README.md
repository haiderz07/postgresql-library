# PostgreSQL Library

A static, book-style reader for the official PostgreSQL manuals (16, 17, 18, 19): page-flip reading, contents, full-text search, copy, highlights and bookmarks (stored in the browser).

Served by GitHub Pages from `/docs`.

## Rebuild
```
pip install pymupdf pillow
python build.py            # all books; or: python build.py 16
```
Source PDFs are read from your Downloads folder and are not committed. The build writes WebP page images, a text layer (for selection) and a search index into `docs/books/<id>/`.

## Licence
The manuals are by the PostgreSQL Global Development Group, under the PostgreSQL Licence. This is an unofficial reader.

