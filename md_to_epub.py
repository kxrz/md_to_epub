#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "questionary>=2.0.1",
#   "rich>=13.7.0",
#   "PyYAML>=6.0.1",
#   "pypandoc_binary>=1.13",
# ]
# ///
"""
MD to ePub — turn Markdown notes into clean ePub books.

Created by: kxrz (https://github.com/kxrz)

    md2epub                      # interactive mode
    md2epub notes.md             # one file  -> notes.epub
    md2epub chapters/ --merge    # a folder  -> one book
    md2epub a.md b.md c.md       # several files -> one book

Pandoc is bundled through `pypandoc_binary`; a system Pandoc is used as fallback.
"""

from __future__ import annotations

import json
import locale
import os
import re
import shlex
import shutil
import string
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

__version__ = "3.0.0"

try:
    import yaml
    from rich.console import Console
    from rich.panel import Panel
    from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn
except ImportError:  # pragma: no cover
    print("Missing dependencies. Install them with:  pip install -r requirements.txt")
    sys.exit(1)

console = Console(highlight=False)

MD_EXTENSIONS = {".md", ".markdown", ".mdown", ".mkd"}
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp"}
COVER_EXTENSIONS = (".jpg", ".jpeg", ".png", ".gif")
IGNORED_DIRS = {".git", ".obsidian", ".trash", "node_modules", "__pycache__", ".venv", "venv"}
METADATA_FILES = ("book.yaml", "book.yml", "metadata.yaml", "metadata.yml")
CSS_MARKER = "MD to ePub"

# --------------------------------------------------------------------------- #
# Default stylesheet: tuned for e-ink readers (Kobo, Kindle via Calibre/Send to
# Kindle, PocketBook, Boox, Xteink…) as well as Apple Books / Google Play Books.
# Readers' own font and margin settings keep working: no fixed sizes, no resets.
# --------------------------------------------------------------------------- #
DEFAULT_CSS = """/* Optimized CSS for ePub - MD to ePub Converter */
/* Created by: kxrz (https://github.com/kxrz) */

body {
    font-family: Georgia, Palatino, "Times New Roman", serif;
    line-height: 1.5;
    text-align: justify;
    hyphens: auto;
    -webkit-hyphens: auto;
    -epub-hyphens: auto;
    adobe-hyphenate: auto;
    widows: 2;
    orphans: 2;
}

/* ---------- Headings ---------- */
h1, h2, h3, h4, h5, h6 {
    font-family: "Helvetica Neue", Helvetica, Arial, sans-serif;
    font-weight: bold;
    line-height: 1.25;
    text-align: left;
    hyphens: none;
    -webkit-hyphens: none;
    margin: 1.4em 0 0.5em 0;
    page-break-after: avoid;
    break-after: avoid;
    page-break-inside: avoid;
}
h1 { font-size: 1.8em; margin: 1em 0 1em 0; }
h2 { font-size: 1.4em; }
h3 { font-size: 1.2em; }
h4 { font-size: 1.05em; }
h5, h6 { font-size: 1em; }

/* ---------- Paragraphs ---------- */
p {
    margin: 0;
    text-indent: 1.3em;
}
/* No indent after headings, lists, quotes, figures… (classic book style) */
h1 + p, h2 + p, h3 + p, h4 + p, h5 + p, h6 + p,
blockquote + p, ul + p, ol + p, pre + p, table + p,
figure + p, hr + p, div + p, dl + p,
li p, blockquote p, td p, th p, dd p, .footnotes p,
section > p:first-child {
    text-indent: 0;
}
li p, dd p { margin: 0.3em 0; }

/* ---------- Links ---------- */
a { color: inherit; text-decoration: underline; }
a.footnote-ref, a.footnote-back { text-decoration: none; }

/* ---------- Lists ---------- */
ul, ol { margin: 0.8em 0; padding-left: 1.6em; }
li { margin: 0.25em 0; }
ul ul, ol ol, ul ol, ol ul { margin: 0.2em 0; }
ul.task-list { list-style: none; padding-left: 0.4em; }

/* ---------- Code ---------- */
code {
    font-family: Menlo, Consolas, "Courier New", monospace;
    font-size: 0.85em;
    hyphens: none;
    -webkit-hyphens: none;
}
pre {
    font-size: 0.85em;
    line-height: 1.35;
    margin: 1em 0;
    padding: 0.6em;
    border: 1px solid #999;
    white-space: pre-wrap;
    word-wrap: break-word;
    text-align: left;
    page-break-inside: avoid;
}
pre code { font-size: 1em; }
/* Wrap long code lines instead of cutting them off on small screens */
pre > code.sourceCode, pre > code { white-space: pre-wrap; }
pre a, code a { text-decoration: none; }
div.sourceCode { margin: 1em 0; }

/* ---------- Blockquotes ---------- */
blockquote {
    margin: 1em 1.2em;
    padding-left: 0.8em;
    border-left: 3px solid #888;
    font-style: italic;
}

/* ---------- Images & figures ---------- */
img { max-width: 100%; height: auto; }
/* An image on its own line: centered block, not shifted by the paragraph indent */
p > img { display: block; margin: 1em auto; }
figure {
    margin: 1.2em 0;
    text-align: center;
    page-break-inside: avoid;
}
figure img { display: block; margin: 0 auto; }
figcaption { font-size: 0.85em; font-style: italic; margin-top: 0.4em; text-indent: 0; }

/* ---------- Tables ---------- */
table {
    border-collapse: collapse;
    margin: 1em auto;
    font-size: 0.9em;
}
th, td {
    border: 1px solid #888;
    padding: 0.3em 0.5em;
    text-align: left;
    vertical-align: top;
}
th { font-weight: bold; }

/* ---------- Misc ---------- */
hr {
    border: none;
    border-top: 1px solid #888;
    width: 30%;
    margin: 1.5em auto;
}
mark { background-color: #ddd; }
del, s { text-decoration: line-through; }
sup, sub { font-size: 0.75em; line-height: 0; }
dt { font-weight: bold; margin-top: 0.8em; }
dd { margin: 0 0 0.5em 1.5em; }

/* ---------- Footnotes ---------- */
.footnotes { font-size: 0.85em; margin-top: 2em; }
.footnotes hr { width: 20%; margin-left: 0; }

/* ---------- Title page & TOC (generated by Pandoc) ---------- */
#title-block-header, .titlepage { text-align: center; margin-top: 20%; }
.title { font-size: 2em; text-indent: 0; }
.author { font-size: 1.2em; font-style: italic; text-indent: 0; }
nav#toc ol { list-style: none; padding-left: 1em; }

/* ---------- Helpers usable from Markdown: ::: page-break ---------- */
.page-break { page-break-after: always; break-after: page; }
"""


# --------------------------------------------------------------------------- #
# Small helpers
# --------------------------------------------------------------------------- #
def natural_key(path: Path) -> list:
    """Sort '2-intro' before '10-end' (human order)."""
    return [int(part) if part.isdigit() else part.lower() for part in re.split(r"(\d+)", str(path))]


def title_from_filename(stem: str) -> str:
    """'01_my-first_chapter' -> 'My First Chapter'."""
    name = re.sub(r"^\d+[\s._-]*", "", stem) or stem
    name = re.sub(r"[_-]+", " ", name).strip()
    return string.capwords(name) if name.islower() else name


def safe_filename(name: str) -> str:
    cleaned = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "", name).strip().rstrip(".")
    return cleaned or "book"


def human_size(num_bytes: int) -> str:
    size = float(num_bytes)
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024 or unit == "GB":
            return f"{size:.0f} {unit}" if unit == "B" else f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} GB"


def clean_path(raw: str) -> Path:
    """Accept paths typed, pasted or dragged into a terminal (quotes, escaped spaces, ~)."""
    text = raw.strip()
    if len(text) >= 2 and text[0] == text[-1] and text[0] in "'\"":
        text = text[1:-1]
    if os.name != "nt":
        text = re.sub(r"\\(.)", r"\1", text)
    if text.startswith("file://"):
        from urllib.parse import unquote, urlparse
        text = unquote(urlparse(text).path)
    return Path(os.path.expanduser(text))


def parse_dropped_paths(raw: str) -> List[Path]:
    """Split one or several dragged-and-dropped paths."""
    raw = raw.strip()
    if not raw:
        return []
    single = clean_path(raw)
    if single.exists():
        return [single]
    try:
        parts = shlex.split(raw, posix=(os.name != "nt"))
    except ValueError:
        return [single]
    return [clean_path(p) for p in parts] if parts else [single]


def is_markdown(path: Path) -> bool:
    return path.suffix.lower() in MD_EXTENSIONS


def find_markdown_files(folder: Path, recursive: bool = False) -> List[Path]:
    if recursive:
        files = [
            p for p in folder.rglob("*")
            if p.is_file() and is_markdown(p)
            and not any(part in IGNORED_DIRS or part.startswith(".") for part in p.relative_to(folder).parts[:-1])
        ]
    else:
        files = [p for p in folder.iterdir() if p.is_file() and is_markdown(p)]
    return sorted((f for f in files if not f.name.startswith(".")), key=lambda p: natural_key(p.relative_to(folder)))


def has_markdown_in_subfolders(folder: Path) -> bool:
    return len(find_markdown_files(folder, True)) > len(find_markdown_files(folder, False))


def find_cover(folder: Path) -> Optional[Path]:
    for entry in sorted(folder.iterdir()) if folder.is_dir() else []:
        if entry.is_file() and entry.stem.lower() == "cover" and entry.suffix.lower() in COVER_EXTENSIONS:
            return entry
    return None


# --------------------------------------------------------------------------- #
# Config (remembers the author name between runs)
# --------------------------------------------------------------------------- #
def config_path() -> Path:
    if os.name == "nt":
        base = Path(os.environ.get("APPDATA", Path.home()))
    else:
        base = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    return base / "md2epub" / "config.json"


def load_config() -> Dict:
    try:
        return json.loads(config_path().read_text(encoding="utf-8"))
    except Exception:
        return {}


def save_config(**values) -> None:
    try:
        cfg = load_config()
        cfg.update({k: v for k, v in values.items() if v})
        path = config_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(cfg, indent=2, ensure_ascii=False), encoding="utf-8")
    except Exception:
        pass  # remembering the author is a convenience, never a reason to fail


# --------------------------------------------------------------------------- #
# Markdown reading & preprocessing
# --------------------------------------------------------------------------- #
FRONTMATTER_RE = re.compile(r"\A---[ \t]*\r?\n(.*?)\r?\n(?:---|\.\.\.)[ \t]*(?:\r?\n|\Z)", re.DOTALL)
FENCE_RE = re.compile(r"^(\s*)(```+|~~~+)")
H1_RE = re.compile(r"^#[ \t]+(.+?)[ \t#]*$")
WIKI_EMBED_RE = re.compile(r"!\[\[([^\]|#]+)(?:#[^\]|]*)?(?:\|([^\]]*))?\]\]")
WIKI_LINK_RE = re.compile(r"\[\[([^\]|#]*)(?:#([^\]|]*))?(?:\|([^\]]*))?\]\]")
MD_IMAGE_RE = re.compile(r"!\[([^\]]*)\]\(\s*([^)<>\s]+)(\s+[\"'][^)]*[\"'])?\s*\)")


def read_text(path: Path) -> str:
    data = path.read_bytes()
    for encoding in ("utf-8-sig", "cp1252"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", errors="replace")


def split_frontmatter(text: str) -> Tuple[Dict, str]:
    match = FRONTMATTER_RE.match(text)
    if not match:
        return {}, text
    try:
        meta = yaml.safe_load(match.group(1))
    except yaml.YAMLError:
        return {}, text
    if not isinstance(meta, dict):
        return {}, text
    return meta, text[match.end():]


def outside_code(text: str, transform) -> str:
    """Apply `transform` to every line that is not inside a fenced code block."""
    out, fence = [], None
    for line in text.splitlines(keepends=True):
        m = FENCE_RE.match(line)
        if fence:
            if m and m.group(2)[0] == fence[0] and len(m.group(2)) >= len(fence):
                fence = None
            out.append(line)
        elif m:
            fence = m.group(2)
            out.append(line)
        else:
            out.append(transform(line))
    return "".join(out)


def first_h1(text: str) -> Optional[str]:
    found: List[str] = []

    def grab(line: str) -> str:
        m = H1_RE.match(line.rstrip("\r\n"))
        if m and not found:
            found.append(m.group(1).strip())
        return line

    outside_code(text, grab)
    return found[0] if found else None


class ImageResolver:
    """Finds images referenced by notes (also Obsidian-style `![[image.png]]`)."""

    def __init__(self, root: Path):
        self.root = root
        self._index: Optional[Dict[str, Path]] = None

    def find(self, name: str, base: Path) -> Optional[Path]:
        candidate = (base / name)
        if candidate.is_file():
            return candidate.resolve()
        if self._index is None:
            self._index = {}
            try:
                for p in self.root.rglob("*"):
                    if p.is_file() and p.suffix.lower() in IMAGE_EXTENSIONS:
                        self._index.setdefault(p.name.lower(), p.resolve())
            except OSError:
                pass
        return self._index.get(Path(name).name.lower())


def preprocess(body: str, source: Path, resolver: ImageResolver) -> str:
    """Make notes portable: absolute image paths, Obsidian embeds & wikilinks."""
    base = source.parent

    def embed(m: re.Match) -> str:
        target, alt = m.group(1).strip(), (m.group(2) or "").strip()
        if Path(target).suffix.lower() in IMAGE_EXTENSIONS:
            found = resolver.find(target, base)
            if alt.isdigit():  # Obsidian width syntax: ![[img.png|300]]
                alt = ""
            return f"![{alt}](<{found.as_posix() if found else target}>)"
        return f"*{alt or Path(target).stem}*"

    def link(m: re.Match) -> str:
        page, heading, alias = m.group(1).strip(), (m.group(2) or "").strip(), m.group(3)
        if alias:
            return alias.strip()
        return f"{page} > {heading}" if page and heading else page or heading

    def image(m: re.Match) -> str:
        alt, target, title = m.group(1), m.group(2), m.group(3) or ""
        if re.match(r"^[a-z][a-z0-9+.-]*:", target, re.I) or target.startswith("#"):
            return m.group(0)
        from urllib.parse import unquote
        found = (base / unquote(target))
        if found.is_file():
            return f"![{alt}](<{found.resolve().as_posix()}>{title})"
        return m.group(0)

    def transform(line: str) -> str:
        line = WIKI_EMBED_RE.sub(embed, line)
        line = WIKI_LINK_RE.sub(link, line)
        return MD_IMAGE_RE.sub(image, line)

    return outside_code(body, transform)


# --------------------------------------------------------------------------- #
# Language guessing (drives hyphenation on e-readers)
# --------------------------------------------------------------------------- #
STOPWORDS = {
    "en": "the and of to is in that it with for was on are this you not be have",
    "fr": "le la les et des est une dans que pour pas qui sur du au avec ce sont",
    "de": "der die und das ist nicht ein eine zu den mit sich auch auf für ich",
    "es": "el la los las que de y en es por una para con del se no",
    "it": "il che di la per non una sono con del della gli anche come più",
    "pt": "o os que de não uma para com do da em são mais como também",
    "nl": "de het een en van is dat niet op te zijn voor met ook maar",
}


def guess_language(text: str) -> Optional[str]:
    words = re.findall(r"[^\W\d_]+", text[:20000].lower())
    if len(words) < 30:
        return None
    scores = {lang: sum(1 for w in words if w in set(sw.split())) for lang, sw in STOPWORDS.items()}
    best = max(scores, key=scores.get)
    return best if scores[best] >= max(5, len(words) * 0.04) else None


def system_language() -> str:
    try:
        loc = locale.getlocale()[0] or os.environ.get("LANG", "")
    except Exception:
        loc = ""
    match = re.match(r"([a-zA-Z]{2})", loc or "")
    return match.group(1).lower() if match else "en"


# --------------------------------------------------------------------------- #
# Pandoc
# --------------------------------------------------------------------------- #
def find_pandoc() -> Optional[str]:
    try:
        import pypandoc  # bundled binary from pypandoc_binary

        path = pypandoc.get_pandoc_path()
        if path:
            return path
    except Exception:
        pass
    return shutil.which("pandoc")


def pandoc_version(pandoc: str) -> Tuple[int, ...]:
    try:
        out = subprocess.run([pandoc, "--version"], capture_output=True, text=True, check=True).stdout
        return tuple(int(x) for x in re.search(r"(\d+(?:\.\d+)+)", out).group(1).split("."))
    except Exception:
        return (0,)


def pandoc_missing_message() -> None:
    console.print("[red]✗ Pandoc was not found.[/red]")
    console.print("The easiest fix:  [cyan]pip install pypandoc_binary[/cyan]  (bundles Pandoc)")
    console.print("Or install Pandoc yourself: [cyan]https://pandoc.org/installing.html[/cyan]")


# --------------------------------------------------------------------------- #
# The book model & conversion
# --------------------------------------------------------------------------- #
@dataclass
class Book:
    sources: List[Path]
    output: Path
    meta: Dict = field(default_factory=dict)
    cover: Optional[Path] = None
    css: Optional[Path] = None
    toc: bool = True

    @property
    def title(self) -> str:
        return str(self.meta.get("title", ""))


@dataclass
class Result:
    ok: bool
    output: Path
    warnings: List[str] = field(default_factory=list)
    error: str = ""


def _author_text(author) -> str:
    if isinstance(author, list):
        return ", ".join(str(a) for a in author)
    return str(author or "")


def build_markdown(book: Book) -> str:
    """Combine the sources into one portable Markdown document."""
    roots = {s.parent for s in book.sources}
    root = Path(os.path.commonpath([str(r.resolve()) for r in roots])) if roots else Path.cwd()
    resolver = ImageResolver(root)
    parts = []
    merging = len(book.sources) > 1

    for src in book.sources:
        meta, body = split_frontmatter(read_text(src))
        body = preprocess(body, src, resolver)
        if merging and not first_h1(body):
            chapter = str(meta.get("title") or title_from_filename(src.stem))
            body = f"# {chapter}\n\n{body.lstrip()}"
        parts.append(body.strip("\n"))

    return "\n\n".join(parts) + "\n"


def convert(book: Book, pandoc: str) -> Result:
    """Run Pandoc for one book."""
    markdown = build_markdown(book)
    version = pandoc_version(pandoc)

    meta = {k: v for k, v in book.meta.items() if v not in (None, "", [])}
    meta.pop("cover-image", None)
    if "date" in meta:
        meta["date"] = str(meta["date"])

    ext = "markdown+emoji+autolink_bare_uris-yaml_metadata_block"
    if version >= (3, 0):
        ext += "+mark"

    book.output.parent.mkdir(parents=True, exist_ok=True)
    resource_dirs = list(dict.fromkeys([str(s.parent.resolve()) for s in book.sources] + ["."]))

    with tempfile.TemporaryDirectory(prefix="md2epub-") as tmp:
        tmp_dir = Path(tmp)
        md_file = tmp_dir / "book.md"
        md_file.write_text(markdown, encoding="utf-8")
        meta_file = tmp_dir / "metadata.yaml"
        meta_file.write_text(yaml.safe_dump(meta, allow_unicode=True, sort_keys=False), encoding="utf-8")

        css = book.css
        if not css:
            css = tmp_dir / "epub.css"
            css.write_text(DEFAULT_CSS, encoding="utf-8")

        cmd = [
            pandoc, str(md_file),
            "--from", ext,
            "--to", "epub3",
            "--output", str(book.output.resolve()),
            "--metadata-file", str(meta_file),
            "--resource-path", os.pathsep.join(resource_dirs),
            "--css", str(css),
        ]
        if book.toc:
            cmd += ["--toc", "--toc-depth=2"]
        # Split chapters on H1, or on H2 when the document has no H1 at all.
        level = "1" if first_h1(markdown) else "2"
        cmd.append(f"--split-level={level}" if version >= (3, 0) else f"--epub-chapter-level={level}")
        if book.cover:
            cmd += ["--epub-cover-image", str(book.cover.resolve())]

        proc = subprocess.run(
            cmd, capture_output=True, text=True, encoding="utf-8", errors="replace",
            cwd=str(book.sources[0].parent.resolve()),
        )

    warnings = [
        re.sub(r"^\[WARNING\]\s*", "", line).strip()
        for line in proc.stderr.splitlines()
        if line.startswith("[WARNING]")
    ]
    if proc.returncode != 0:
        return Result(False, book.output, warnings, proc.stderr.strip() or "Pandoc failed")
    return Result(True, book.output, warnings)


# --------------------------------------------------------------------------- #
# Planning: from user input to a list of books
# --------------------------------------------------------------------------- #
def resolve_css(explicit: Optional[str], source_dir: Path) -> Optional[Path]:
    if explicit:
        path = clean_path(explicit)
        if not path.is_file():
            raise SystemExit(f"CSS file not found: {path}")
        return path
    for folder in dict.fromkeys([source_dir, Path.cwd()]):
        candidate = folder / "epub.css"
        if candidate.is_file():
            return candidate
        legacy = folder / "style.css"  # created by earlier versions with --create-css
        if legacy.is_file():
            try:
                if CSS_MARKER in legacy.read_text(encoding="utf-8", errors="ignore")[:300]:
                    return legacy
            except OSError:
                pass
    return None


def load_book_yaml(folder: Path) -> Dict:
    for name in METADATA_FILES:
        path = folder / name
        if path.is_file():
            try:
                data = yaml.safe_load(read_text(path))
                return data if isinstance(data, dict) else {}
            except yaml.YAMLError:
                console.print(f"[yellow]⚠ Could not read {path.name}, ignoring it.[/yellow]")
    return {}


def resolve_output(output: Optional[str], default_dir: Path, filename: str, many: bool = False) -> Path:
    if output:
        out = clean_path(output)
        if out.suffix.lower() == ".epub" and not many:
            return out
        return out / filename
    return default_dir / filename


def plan_single(
    src: Path, *, title=None, author=None, lang=None, cover=None, css=None,
    output=None, toc=True, fallback_author=None, many=False,
) -> Book:
    meta, body = split_frontmatter(read_text(src))
    meta = dict(meta)
    meta["title"] = title or meta.get("title") or first_h1(body) or title_from_filename(src.stem)
    meta["author"] = author or meta.get("author") or fallback_author or ""
    meta["lang"] = lang or meta.get("lang") or meta.get("language") or guess_language(body) or system_language()

    cover_path = None
    if cover:
        cover_path = clean_path(cover)
    elif meta.get("cover-image"):
        cover_path = (src.parent / str(meta["cover-image"]))
    elif not many:
        cover_path = find_cover(src.parent)
    if cover_path and not cover_path.is_file():
        console.print(f"[yellow]⚠ Cover image not found: {cover_path}[/yellow]")
        cover_path = None

    out = resolve_output(output, src.parent, f"{src.stem}.epub", many)
    return Book([src], out, meta, cover_path, css, toc)


def plan_merge(
    sources: List[Path], *, folder: Optional[Path] = None, title=None, author=None, lang=None,
    cover=None, css=None, output=None, toc=True, fallback_author=None,
) -> Book:
    base = folder or sources[0].parent
    meta = dict(load_book_yaml(base))
    first_meta, first_body = split_frontmatter(read_text(sources[0]))

    default_title = (
        meta.get("title")
        or (folder and title_from_filename(folder.resolve().name))
        or (len(sources) == 1 and (first_meta.get("title") or first_h1(first_body)))
        or title_from_filename(sources[0].stem)
    )
    meta["title"] = title or default_title
    meta["author"] = author or meta.get("author") or first_meta.get("author") or fallback_author or ""
    sample = "\n".join(split_frontmatter(read_text(s))[1] for s in sources[:5])
    meta["lang"] = lang or meta.get("lang") or first_meta.get("lang") or guess_language(sample) or system_language()

    cover_path = None
    if cover:
        cover_path = clean_path(cover)
    elif meta.get("cover-image"):
        cover_path = base / str(meta["cover-image"])
    else:
        cover_path = find_cover(base)
    if cover_path and not cover_path.is_file():
        console.print(f"[yellow]⚠ Cover image not found: {cover_path}[/yellow]")
        cover_path = None

    # A folder "my_book/" gives "My Book.epub" next to the folder.
    default_dir = folder.resolve().parent if folder else sources[0].parent
    out = resolve_output(output, default_dir, f"{safe_filename(meta['title'])}.epub")
    return Book(list(sources), out, meta, cover_path, css, toc)


# --------------------------------------------------------------------------- #
# Output
# --------------------------------------------------------------------------- #
def display_path(path: Path) -> str:
    """Short path for humans: relative to the current folder, or with ~ for home."""
    full = path.resolve()
    for base, prefix in ((Path.cwd().resolve(), ""), (Path.home().resolve(), "~/")):
        try:
            return prefix + full.relative_to(base).as_posix()
        except ValueError:
            continue
    return str(full)


def report(result: Result, book: Book, quiet_warnings: bool = False) -> None:
    if result.ok:
        size = human_size(result.output.stat().st_size) if result.output.exists() else "?"
        shown = display_path(result.output)
        console.print(f"[green]✓[/green] [bold]{shown}[/bold] [dim]({size})[/dim]")
    else:
        console.print(f"[red]✗ Could not create {result.output.name}[/red]")
        console.print(f"[red]{result.error}[/red]")
    if result.warnings and not quiet_warnings:
        for w in result.warnings[:8]:
            console.print(f"  [yellow]⚠ {w}[/yellow]")
        if len(result.warnings) > 8:
            console.print(f"  [yellow]… and {len(result.warnings) - 8} more warnings[/yellow]")


def run_books(books: List[Book], pandoc: str) -> int:
    """Convert books, return number of failures."""
    if len(books) == 1:
        book = books[0]
        with console.status(f"Creating [cyan]{book.output.name}[/cyan]…"):
            result = convert(book, pandoc)
        report(result, book)
        return 0 if result.ok else 1

    failures, results = 0, []
    with Progress(SpinnerColumn(), TextColumn("{task.description}"), BarColumn(),
                  TextColumn("{task.completed}/{task.total}"), console=console, transient=True) as progress:
        task = progress.add_task("Converting…", total=len(books))
        for book in books:
            progress.update(task, description=f"[cyan]{book.sources[0].name}[/cyan]")
            results.append((convert(book, pandoc), book))
            progress.advance(task)
    for result, book in results:
        report(result, book)
        failures += 0 if result.ok else 1
    console.print(f"\n[bold]{len(books) - failures}/{len(books)}[/bold] ePub files created.")
    return failures


def write_css(path: Path) -> None:
    path.write_text(DEFAULT_CSS, encoding="utf-8")
    console.print(f"[green]✓[/green] Stylesheet written to [cyan]{path}[/cyan]")
    console.print("  Edit it, it is picked up automatically when it sits next to your Markdown files.")


# --------------------------------------------------------------------------- #
# Interactive mode
# --------------------------------------------------------------------------- #
def interactive(pandoc: str) -> int:
    import questionary
    from questionary import Choice, Style

    style = Style([
        ("qmark", "fg:#8b5cf6 bold"), ("question", "bold"), ("answer", "fg:#2196f3 bold"),
        ("pointer", "fg:#8b5cf6 bold"), ("highlighted", "fg:#8b5cf6 bold"),
        ("selected", "fg:#2196f3"), ("instruction", "fg:#888888"),
    ])

    def ask(question):
        return question.unsafe_ask()  # Ctrl+C raises KeyboardInterrupt -> clean exit

    def validate_sources(text: str):
        paths = parse_dropped_paths(text)
        if not paths:
            return "Type or drag a Markdown file or a folder"
        for p in paths:
            if not p.exists():
                return f"Not found: {p}"
            if p.is_file() and not is_markdown(p) and len(paths) > 1:
                return f"Not a Markdown file: {p.name}"
        return True

    cfg = load_config()
    console.print(Panel.fit(
        "[bold cyan]MD to ePub[/bold cyan]  [dim]v" + __version__ + "[/dim]\n"
        "[dim]Markdown → ePub, ready for your e-reader · by kxrz[/dim]",
        border_style="cyan",
    ))
    if (Path.cwd() / "epub.css").is_file():
        console.print("[dim]Using epub.css from this folder.[/dim]")

    while True:
        console.print()
        # 1. What to convert
        cwd = Path.cwd()
        local = find_markdown_files(cwd) if cwd != Path.home() else []
        sources: List[Path] = []
        if local:
            choices = [Choice(f.name, value=[f]) for f in local[:12]]
            if len(local) > 1:
                choices.insert(0, Choice(f"📁 This whole folder ({len(local)} files)", value=[cwd]))
            choices.append(Choice("🔎 Another file or folder…", value=None))
            sources = ask(questionary.select("What do you want to convert?", choices=choices, style=style))
        if not sources:
            raw = ask(questionary.path(
                "Markdown file or folder (you can drag it here):",
                validate=validate_sources, validate_while_typing=False, style=style,
            ))
            sources = parse_dropped_paths(raw)

        # 2. Expand folders and decide the mode
        mode, folder = "single", None
        files: List[Path] = []
        if len(sources) == 1 and sources[0].is_dir():
            folder = sources[0]
            recursive = False
            if not find_markdown_files(folder):
                recursive = True
            elif has_markdown_in_subfolders(folder):
                recursive = ask(questionary.confirm("Include subfolders?", default=True, style=style))
            files = find_markdown_files(folder, recursive)
            if not files:
                console.print(f"[red]✗ No Markdown files in {folder}[/red]")
                continue
            if len(files) > 1:
                mode = ask(questionary.select(
                    f"{len(files)} Markdown files found. Create…",
                    choices=[
                        Choice(f"📖 One book ({len(files)} chapters, in name order)", value="merge"),
                        Choice("📖 One book, let me pick the chapters", value="pick"),
                        Choice(f"📚 One ePub per file ({len(files)} files)", value="separate"),
                    ], style=style,
                ))
                if mode == "pick":
                    files = ask(questionary.checkbox(
                        "Chapters to include:",
                        choices=[Choice(str(f.relative_to(folder)), value=f, checked=True) for f in files],
                        validate=lambda sel: bool(sel) or "Pick at least one file", style=style,
                    ))
                    mode = "merge"
        else:
            for p in sources:
                files.extend(find_markdown_files(p, True) if p.is_dir() else [p])
            mode = "merge" if len(files) > 1 else "single"

        # 3. Metadata
        css = resolve_css(None, files[0].parent)
        default_author = cfg.get("author", "")
        if mode == "separate":
            author = ask(questionary.text(
                "Author (used when a file has none):", default=default_author, style=style)).strip()
            books = [plan_single(f, css=css, fallback_author=author, many=True) for f in files]
        else:
            draft = (plan_merge(files, folder=folder, css=css, fallback_author=default_author)
                     if mode == "merge" else plan_single(files[0], css=css, fallback_author=default_author))
            if mode == "merge":
                console.print("[dim]Chapters: " + ", ".join(f.name for f in files[:8])
                              + (f" … (+{len(files) - 8})" if len(files) > 8 else "") + "[/dim]")
            title = ask(questionary.text("Title:", default=draft.title, style=style)).strip() or draft.title
            author = ask(questionary.text(
                "Author:", default=_author_text(draft.meta.get("author")),
                validate=lambda a: bool(a.strip()) or "E-readers sort books by author, please fill it in",
                validate_while_typing=False, style=style,
            )).strip()
            if draft.cover:
                console.print(f"[dim]Cover: {draft.cover.name} (found automatically)[/dim]")
                cover = str(draft.cover)
            else:
                raw = ask(questionary.path(
                    "Cover image (optional, Enter to skip):",
                    validate=lambda t: not t.strip() or clean_path(t).is_file() or "Image not found",
                    validate_while_typing=False, style=style,
                ))
                cover = str(clean_path(raw)) if raw.strip() else None
            kwargs = dict(title=title, author=author, cover=cover, css=css, lang=draft.meta.get("lang"))
            books = ([plan_merge(files, folder=folder, **kwargs)] if mode == "merge"
                     else [plan_single(files[0], **kwargs)])

        if author:
            save_config(author=author)
            cfg["author"] = author

        # 4. Convert
        console.print()
        run_books(books, pandoc)

        console.print()
        if not ask(questionary.confirm("Convert something else?", default=False, style=style)):
            return 0


# --------------------------------------------------------------------------- #
# Command line
# --------------------------------------------------------------------------- #
def build_parser():
    import argparse

    parser = argparse.ArgumentParser(
        prog="md2epub",
        description="Convert Markdown files to ePub books. Run without arguments for interactive mode.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""examples:
  md2epub                              interactive mode
  md2epub notes.md                     -> notes.epub
  md2epub notes.md -o ~/Books/         choose where the ePub goes
  md2epub ch1.md ch2.md ch3.md -t "My Book" -a "Jane Doe"
                                       several files -> one book
  md2epub my_book/ --merge             a folder -> one book (my_book.epub)
  md2epub notes/ -r -o epubs/          a folder -> one ePub per file

metadata is read from YAML front matter (title, author, lang, cover-image,
description, publisher, date…) or from a book.yaml file in the folder.
A cover.jpg/cover.png next to your files is used automatically.""",
    )
    parser.add_argument("inputs", nargs="*", metavar="INPUT", help="Markdown file(s) or folder(s)")
    parser.add_argument("-o", "--output", help="output .epub file or folder")
    parser.add_argument("-t", "--title", help="book title")
    parser.add_argument("-a", "--author", help="author name (remembered for next time)")
    parser.add_argument("-l", "--lang", help="language code, e.g. en, fr (auto-detected by default)")
    parser.add_argument("--cover", help="cover image (jpg/png)")
    parser.add_argument("-c", "--css", help="custom stylesheet")
    parser.add_argument("-m", "--merge", action="store_true", help="merge everything into one book")
    parser.add_argument("-r", "--recursive", action="store_true", help="include subfolders")
    parser.add_argument("--no-toc", action="store_true", help="do not add a table of contents page")
    parser.add_argument("--init-css", "--create-css", dest="init_css", action="store_true",
                        help="write the default stylesheet to ./epub.css to customize it")
    parser.add_argument("-d", "--dir", help=argparse.SUPPRESS)  # kept for backward compatibility
    parser.add_argument("-V", "--version", action="version", version=f"%(prog)s {__version__}")
    return parser


def cli(argv: List[str], pandoc: str) -> int:
    args = build_parser().parse_args(argv)
    inputs = [clean_path(i) for i in args.inputs] + ([clean_path(args.dir)] if args.dir else [])

    missing = [p for p in inputs if not p.exists()]
    if missing:
        console.print(f"[red]✗ Not found: {missing[0]}[/red]")
        return 1

    cfg = load_config()
    author = args.author
    if author:
        save_config(author=author)
    fallback = cfg.get("author")
    common = dict(author=author, lang=args.lang, toc=not args.no_toc, fallback_author=fallback)

    files: List[Path] = []
    for p in inputs:
        if p.is_dir():
            found = find_markdown_files(p, args.recursive) or find_markdown_files(p, True)
            if not found:
                console.print(f"[yellow]⚠ No Markdown files in {p}[/yellow]")
            files.extend(found)
        else:
            files.append(p)
    if not files:
        console.print("[red]✗ Nothing to convert.[/red]")
        return 1

    css = resolve_css(args.css, files[0].parent)
    if css:
        console.print(f"[dim]Stylesheet: {css}[/dim]")

    folder = inputs[0] if len(inputs) == 1 and inputs[0].is_dir() else None
    if args.merge or (len(files) > 1 and not folder):
        books = [plan_merge(files, folder=folder, title=args.title, cover=args.cover,
                            css=css, output=args.output, **common)]
    elif len(files) == 1:
        books = [plan_single(files[0], title=args.title, cover=args.cover, css=css,
                             output=args.output, **common)]
    else:
        if args.title:
            console.print("[yellow]⚠ --title ignored: one ePub per file (use --merge for one book)[/yellow]")
        books = [plan_single(f, css=css, output=args.output, many=True, **common) for f in files]

    return 1 if run_books(books, pandoc) else 0


def main(argv: Optional[List[str]] = None) -> None:
    argv = sys.argv[1:] if argv is None else argv
    if os.name == "nt":  # make emoji / box drawing work in old Windows consoles
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass

    if argv and argv[0] in ("-h", "--help", "-V", "--version"):
        build_parser().parse_args(argv)

    if "--init-css" in argv or "--create-css" in argv:
        write_css(Path("epub.css"))
        return

    pandoc = find_pandoc()
    if not pandoc:
        pandoc_missing_message()
        sys.exit(1)

    try:
        if argv:
            code = cli(argv, pandoc)
        elif sys.stdin.isatty():
            code = interactive(pandoc)
        else:
            build_parser().print_help()
            code = 0
    except KeyboardInterrupt:
        console.print("\n[dim]Bye![/dim]")
        code = 130
    sys.exit(code)


if __name__ == "__main__":
    main()
