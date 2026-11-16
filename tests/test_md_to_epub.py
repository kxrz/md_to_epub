import struct
import sys
import zipfile
import zlib
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import md_to_epub as m  # noqa: E402

PANDOC = m.find_pandoc()
needs_pandoc = pytest.mark.skipif(not PANDOC, reason="pandoc not available")
EXAMPLE = Path(__file__).resolve().parents[1] / "examples" / "sample-book"


def tiny_png(path: Path) -> Path:
    raw = b"\x00\xff\xff\xff"
    chunk = lambda kind, data: struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data))
    path.write_bytes(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0))
                     + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b""))
    return path


def epub_text(path: Path) -> str:
    with zipfile.ZipFile(path) as z:
        assert z.namelist()[0] == "mimetype"
        return "\n".join(z.read(n).decode("utf-8", "ignore") for n in z.namelist() if n.endswith((".xhtml", ".opf")))


def epub_names(path: Path):
    with zipfile.ZipFile(path) as z:
        return z.namelist()


@pytest.fixture(autouse=True)
def isolated_config(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
    monkeypatch.setenv("APPDATA", str(tmp_path / "config"))


# ----------------------------------------------------------------- helpers
@pytest.mark.parametrize("stem,title", [
    ("01_my-first_chapter", "My First Chapter"),
    ("10 - The End", "The End"),
    ("iPhone notes", "iPhone notes"),
    ("2024", "2024"),
])
def test_title_from_filename(stem, title):
    assert m.title_from_filename(stem) == title


def test_natural_sort():
    names = [Path(n) for n in ["10-end.md", "2-middle.md", "1-start.md"]]
    assert [p.name for p in sorted(names, key=m.natural_key)] == ["1-start.md", "2-middle.md", "10-end.md"]


def test_frontmatter():
    meta, body = m.split_frontmatter("---\ntitle: Hello\nauthor: Me\n---\n# Body\n")
    assert meta == {"title": "Hello", "author": "Me"} and body == "# Body\n"
    assert m.split_frontmatter("--- not yaml\ntext") == ({}, "--- not yaml\ntext")


def test_first_h1_ignores_code():
    assert m.first_h1("```\n# not a title\n```\n## Sub\n# Real\n") == "Real"
    assert m.first_h1("## only h2") is None


def test_clean_dragged_paths(tmp_path):
    f = tmp_path / "My Notes.md"
    f.write_text("x")
    assert m.parse_dropped_paths(f"'{f}'") == [f]
    assert m.parse_dropped_paths(str(f).replace(" ", "\\ ") + "  ") == [f]
    g = tmp_path / "b.md"
    g.write_text("y")
    assert m.parse_dropped_paths(f"'{f}' '{g}'") == [f, g]


def test_obsidian_preprocessing(tmp_path):
    (tmp_path / "attachments").mkdir()
    img = tiny_png(tmp_path / "attachments" / "pic one.png")
    note = tmp_path / "note.md"
    out = m.preprocess(
        "See [[Other note]] and [[Other|alias]].\n![[pic one.png|300]]\n```\n[[keep]]\n```\n",
        note, m.ImageResolver(tmp_path),
    )
    assert "See Other note and alias." in out
    assert f"![](<{img.resolve().as_posix()}>)" in out
    assert "[[keep]]" in out


def test_guess_language():
    fr = "Le chat est sur la table et les enfants sont dans le jardin avec une balle pour jouer. " * 3
    en = "The cat is on the table and the children are in the garden with a ball to play with. " * 3
    assert m.guess_language(fr) == "fr"
    assert m.guess_language(en) == "en"
    assert m.guess_language("too short") is None


# ----------------------------------------------------------------- conversions
@needs_pandoc
def test_single_file_with_frontmatter_and_cover(tmp_path):
    tiny_png(tmp_path / "cover.png")
    src = tmp_path / "my_note.md"
    src.write_text("---\ntitle: Front Title\nauthor: Ada\nlang: fr\n---\n\nBonjour le monde.\n", encoding="utf-8")
    book = m.plan_single(src)
    assert book.title == "Front Title" and book.meta["author"] == "Ada" and book.cover
    result = m.convert(book, PANDOC)
    assert result.ok, result.error
    assert result.output == tmp_path / "my_note.epub"
    text = epub_text(result.output)
    assert "Front Title" in text and "Ada" in text and "<dc:language>fr" in text
    assert any("cover" in n for n in epub_names(result.output))


@needs_pandoc
def test_cli_overrides_frontmatter(tmp_path):
    src = tmp_path / "n.md"
    src.write_text("---\ntitle: Old\n---\nText\n")
    out = tmp_path / "out" / "custom.epub"
    assert m.cli([str(src), "-t", "New", "-a", "Bob", "-o", str(out)], PANDOC) == 0
    text = epub_text(out)
    assert "New" in text and "Bob" in text and ">Old<" not in text
    assert m.load_config()["author"] == "Bob"  # remembered


@needs_pandoc
def test_merge_example_book(tmp_path):
    assert m.cli([str(EXAMPLE), "--merge", "-o", str(tmp_path)], PANDOC) == 0
    out = tmp_path / "A Small Sample Book.epub"
    text = epub_text(out)
    names = epub_names(out)
    assert "Introduction" in text and "Notes from Obsidian" in text
    assert sum(n.startswith("EPUB/text/ch") for n in names) == 2  # one file per chapter
    assert any(n.endswith(".svg") for n in names)  # images embedded
    assert "[[Introduction]]" not in text and "[[this is code, not a wikilink]]" in text


@needs_pandoc
def test_folder_one_epub_per_file(tmp_path):
    for i in range(3):
        (tmp_path / f"{i}-note.md").write_text(f"# Note {i}\n\nHello {i}\n")
    out = tmp_path / "out"
    assert m.cli([str(tmp_path), "-o", str(out)], PANDOC) == 0
    assert sorted(p.name for p in out.glob("*.epub")) == ["0-note.epub", "1-note.epub", "2-note.epub"]


@needs_pandoc
def test_several_files_merge_and_images_from_subfolders(tmp_path):
    (tmp_path / "a").mkdir()
    (tmp_path / "b").mkdir()
    tiny_png(tmp_path / "a" / "img.png")
    (tmp_path / "a" / "one.md").write_text("Chapter one ![x](img.png)\n")
    (tmp_path / "b" / "two.md").write_text("## Part\n\nChapter two\n")
    out = tmp_path / "book.epub"
    code = m.cli([str(tmp_path / "a" / "one.md"), str(tmp_path / "b" / "two.md"), "-t", "Both", "-o", str(out)], PANDOC)
    assert code == 0
    text = epub_text(out)
    assert ">One<" in text and ">Two<" in text  # chapter titles from filenames
    assert any(n.endswith(".png") for n in epub_names(out))


def test_init_css(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with pytest.raises(SystemExit):
        m.main(["--init-css"]) or sys.exit(0)
    css = tmp_path / "epub.css"
    assert css.is_file()
    assert m.resolve_css(None, tmp_path) == css
