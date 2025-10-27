#!/usr/bin/env python3
"""
MD to ePub Converter - Professional Edition
Created by: kxrz (https://github.com/kxrz)
A universal tool to convert Markdown files to beautiful ePub format
with interactive TUI and advanced features.

Requirements: pip install -r requirements.txt
System dependency: pandoc (see README for installation)
"""

import os
import sys
import argparse
import subprocess
import tempfile
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional

try:
    import questionary
    from questionary import Style
    from rich.console import Console
    from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
    from rich.panel import Panel
    from rich.table import Table
    import frontmatter
except ImportError:
    print("❌ Missing dependencies!")
    print("Please install: pip install -r requirements.txt")
    sys.exit(1)

# Initialize Rich console for beautiful output
console = Console()

# Custom style for questionary prompts
custom_style = Style([
    ('qmark', 'fg:#673ab7 bold'),
    ('question', 'bold'),
    ('answer', 'fg:#2196f3 bold'),
    ('pointer', 'fg:#673ab7 bold'),
    ('highlighted', 'fg:#673ab7 bold'),
    ('selected', 'fg:#2196f3'),
    ('separator', 'fg:#cc5454'),
    ('instruction', ''),
    ('text', ''),
])


class EpubConverter:
    """Main class for ePub conversion operations."""

    def __init__(self):
        self.default_css_path = Path('style.css')
        self.author = ""
        self.css_file = None

    def check_pandoc(self) -> bool:
        """Check if Pandoc is installed."""
        try:
            result = subprocess.run(
                ['pandoc', '--version'],
                capture_output=True,
                check=True,
                text=True
            )
            version = result.stdout.split('\n')[0]
            console.print(f"[green]✓[/green] Pandoc detected: {version}")
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            console.print("[red]✗[/red] Pandoc is not installed!")
            console.print("\n[yellow]Installation instructions:[/yellow]")
            console.print("  • macOS:   [cyan]brew install pandoc[/cyan]")
            console.print("  • Linux:   [cyan]sudo apt install pandoc[/cyan]")
            console.print("  • Windows: Download from [cyan]https://pandoc.org/installing.html[/cyan]")
            return False

    def create_optimized_css(self, css_path: str = 'style.css') -> str:
        """Create an optimized CSS file for ePub rendering."""
        css_content = """/* Optimized CSS for ePub - MD to ePub Converter */
/* Created by: kxrz (https://github.com/kxrz) */

/* ========== Reset & Base Styles ========== */
* {
    margin: 0;
    padding: 0;
    box-sizing: border-box;
}

body {
    font-family: "Georgia", "Palatino", "Times New Roman", serif;
    font-size: 1em;
    line-height: 1.7;
    text-align: justify;
    word-wrap: break-word;
    hyphens: auto;
    -webkit-hyphens: auto;
    adobe-hyphenate: auto;
}

/* ========== Headings ========== */
h1, h2, h3, h4, h5, h6 {
    font-family: "Helvetica Neue", "Arial", sans-serif;
    font-weight: bold;
    line-height: 1.3;
    margin-top: 1.5em;
    margin-bottom: 0.5em;
    page-break-after: avoid;
    page-break-inside: avoid;
    -webkit-column-break-after: avoid;
    text-align: left;
}

h1 {
    font-size: 2em;
    margin-top: 0;
    margin-bottom: 1em;
    padding-bottom: 0.3em;
    border-bottom: 2px solid #333;
    page-break-before: always;
}

/* First h1 should not force page break */
h1:first-of-type {
    page-break-before: auto;
}

h2 {
    font-size: 1.6em;
    color: #2c3e50;
    margin-top: 2em;
}

h3 {
    font-size: 1.3em;
    color: #34495e;
}

h4 {
    font-size: 1.1em;
    color: #555;
}

h5, h6 {
    font-size: 1em;
    color: #666;
    font-weight: 600;
}

/* ========== Paragraphs ========== */
p {
    margin: 0.8em 0;
    text-indent: 1.5em;
    orphans: 2;
    widows: 2;
}

/* No indentation for first paragraph or after headings */
p:first-child,
h1 + p, h2 + p, h3 + p,
h4 + p, h5 + p, h6 + p,
blockquote + p,
ul + p, ol + p,
pre + p {
    text-indent: 0;
}

/* ========== Links ========== */
a {
    color: #0066cc;
    text-decoration: none;
}

a[href^="http"]::after {
    content: " (" attr(href) ")";
    font-size: 0.8em;
    color: #666;
}

/* ========== Lists ========== */
ul, ol {
    margin: 1em 0;
    padding-left: 2em;
}

li {
    margin: 0.5em 0;
    line-height: 1.6;
}

li > p {
    text-indent: 0;
}

/* Nested lists */
ul ul, ol ol, ul ol, ol ul {
    margin: 0.3em 0;
}

/* ========== Code ========== */
code {
    font-family: "Courier New", "Consolas", "Monaco", monospace;
    font-size: 0.9em;
    background-color: #f5f5f5;
    padding: 0.2em 0.4em;
    border-radius: 3px;
    word-wrap: break-word;
}

pre {
    background-color: #f8f8f8;
    border: 1px solid #ddd;
    border-radius: 4px;
    padding: 1em;
    margin: 1em 0;
    overflow-x: auto;
    line-height: 1.4;
    page-break-inside: avoid;
}

pre code {
    background-color: transparent;
    padding: 0;
    border: none;
}

/* ========== Blockquotes ========== */
blockquote {
    margin: 1.5em 1em;
    padding: 0.5em 1em;
    border-left: 4px solid #2196f3;
    background-color: #f9f9f9;
    font-style: italic;
    color: #555;
    page-break-inside: avoid;
}

blockquote p {
    text-indent: 0;
}

blockquote cite {
    display: block;
    text-align: right;
    font-size: 0.9em;
    margin-top: 0.5em;
    color: #777;
}

/* ========== Images ========== */
img {
    max-width: 100%;
    height: auto;
    display: block;
    margin: 1.5em auto;
    page-break-inside: avoid;
}

figure {
    margin: 1.5em 0;
    text-align: center;
    page-break-inside: avoid;
}

figcaption {
    font-size: 0.9em;
    font-style: italic;
    color: #666;
    margin-top: 0.5em;
}

/* ========== Tables ========== */
table {
    border-collapse: collapse;
    width: 100%;
    margin: 1.5em 0;
    font-size: 0.9em;
    page-break-inside: avoid;
}

th, td {
    border: 1px solid #ddd;
    padding: 0.6em 0.8em;
    text-align: left;
    text-indent: 0;
}

th {
    background-color: #f5f5f5;
    font-weight: bold;
    color: #333;
}

tr:nth-child(even) {
    background-color: #fafafa;
}

/* ========== Horizontal Rules ========== */
hr {
    border: none;
    border-top: 1px solid #ccc;
    margin: 2em 0;
    page-break-after: avoid;
}

/* ========== Special Elements ========== */
strong, b {
    font-weight: bold;
}

em, i {
    font-style: italic;
}

mark {
    background-color: #ffeb3b;
    padding: 0.1em 0.2em;
}

del, s {
    text-decoration: line-through;
    color: #999;
}

sup, sub {
    font-size: 0.75em;
    line-height: 0;
}

/* ========== Definition Lists ========== */
dl {
    margin: 1em 0;
}

dt {
    font-weight: bold;
    margin-top: 1em;
}

dd {
    margin-left: 2em;
    margin-bottom: 0.5em;
}

/* ========== Footnotes ========== */
.footnote {
    font-size: 0.9em;
    vertical-align: super;
}

.footnotes {
    margin-top: 2em;
    padding-top: 1em;
    border-top: 1px solid #ccc;
    font-size: 0.9em;
}

/* ========== Page Breaks ========== */
.page-break {
    page-break-after: always;
}

.no-break {
    page-break-inside: avoid;
}

/* ========== ePub-specific Optimizations ========== */
@page {
    margin: 1em;
}

/* Prevent awkward breaks */
h1, h2, h3, h4, h5, h6 {
    -webkit-column-break-after: avoid;
    page-break-after: avoid;
}

table, figure, img, pre, blockquote {
    -webkit-column-break-inside: avoid;
    page-break-inside: avoid;
}
"""

        with open(css_path, 'w', encoding='utf-8') as f:
            f.write(css_content)

        console.print(f"[green]✓[/green] Optimized CSS created: [cyan]{css_path}[/cyan]")
        return css_path

    def detect_or_create_css(self) -> str:
        """Detect existing CSS or offer to create one."""
        if self.default_css_path.exists():
            use_existing = questionary.confirm(
                f"Found existing CSS file: {self.default_css_path}\nUse this file?",
                default=True,
                style=custom_style
            ).ask()

            if use_existing:
                console.print(f"[green]✓[/green] Using existing CSS: [cyan]{self.default_css_path}[/cyan]")
                return str(self.default_css_path)
            else:
                custom_path = questionary.path(
                    "Enter path to your custom CSS file:",
                    style=custom_style
                ).ask()

                if custom_path and Path(custom_path).exists():
                    console.print(f"[green]✓[/green] Using custom CSS: [cyan]{custom_path}[/cyan]")
                    return custom_path
                else:
                    console.print("[yellow]⚠[/yellow] Invalid path, creating default CSS")
                    return self.create_optimized_css()
        else:
            create_css = questionary.confirm(
                "No CSS file found. Create optimized CSS?",
                default=True,
                style=custom_style
            ).ask()

            if create_css:
                return self.create_optimized_css()
            else:
                custom_path = questionary.path(
                    "Enter path to your custom CSS file:",
                    style=custom_style
                ).ask()

                if custom_path and Path(custom_path).exists():
                    return custom_path
                else:
                    console.print("[yellow]⚠[/yellow] No valid CSS provided, proceeding without CSS")
                    return None

    def extract_metadata_from_file(self, md_file: Path) -> Dict:
        """Extract metadata from markdown file (frontmatter or filename)."""
        metadata = {}

        try:
            # Try to parse frontmatter
            with open(md_file, 'r', encoding='utf-8') as f:
                post = frontmatter.load(f)
                metadata = post.metadata
        except Exception:
            pass

        # Generate title from filename if not in frontmatter
        if 'title' not in metadata:
            metadata['title'] = md_file.stem.replace('_', ' ').replace('-', ' ').title()

        return metadata

    def get_metadata_interactive(self, default_title: str = None) -> Dict:
        """Interactively collect metadata from user."""
        console.print("\n[bold cyan]📝 ePub Metadata Configuration[/bold cyan]")

        # Title
        title = questionary.text(
            "Book/Document title:",
            default=default_title or "Untitled",
            style=custom_style
        ).ask()

        # Author (mandatory)
        author = None
        while not author or author.strip() == "":
            author = questionary.text(
                "Author name (required):",
                default=self.author,
                style=custom_style
            ).ask()

            if not author or author.strip() == "":
                console.print("[red]✗[/red] Author name is required!")

        # Optional metadata
        add_more = questionary.confirm(
            "Add additional metadata? (description, publisher, etc.)",
            default=False,
            style=custom_style
        ).ask()

        metadata = {
            'title': title,
            'author': author,
            'lang': 'en'
        }

        if add_more:
            description = questionary.text(
                "Description (optional):",
                default="",
                style=custom_style
            ).ask()

            if description:
                metadata['description'] = description

            publisher = questionary.text(
                "Publisher (optional):",
                default="",
                style=custom_style
            ).ask()

            if publisher:
                metadata['publisher'] = publisher

            language = questionary.text(
                "Language code:",
                default="en",
                style=custom_style
            ).ask()

            metadata['lang'] = language

            # Date
            add_date = questionary.confirm(
                "Add publication date?",
                default=False,
                style=custom_style
            ).ask()

            if add_date:
                date = questionary.text(
                    "Date (YYYY-MM-DD):",
                    default=datetime.now().strftime("%Y-%m-%d"),
                    style=custom_style
                ).ask()
                metadata['date'] = date

        return metadata

    def convert_single_file(
        self,
        md_file: Path,
        output_dir: Optional[Path] = None,
        metadata: Optional[Dict] = None
    ) -> bool:
        """Convert a single markdown file to ePub."""

        if not md_file.exists():
            console.print(f"[red]✗[/red] File not found: {md_file}")
            return False

        # Determine output path
        if output_dir:
            output_path = output_dir / f"{md_file.stem}.epub"
            output_path.parent.mkdir(parents=True, exist_ok=True)
        else:
            output_path = md_file.with_suffix('.epub')

        # Build pandoc command
        cmd = [
            'pandoc',
            str(md_file),
            '-o', str(output_path),
            '--toc',
            '--toc-depth=3',
            '--epub-chapter-level=2',
        ]

        # Add CSS
        if self.css_file and Path(self.css_file).exists():
            cmd.extend(['--css', self.css_file])

        # Add metadata
        if metadata:
            for key in ['title', 'author', 'lang', 'description', 'publisher', 'date']:
                if key in metadata and metadata[key]:
                    cmd.extend(['--metadata', f'{key}={metadata[key]}'])

        # Execute conversion
        try:
            subprocess.run(cmd, check=True, capture_output=True)
            console.print(f"[green]✓[/green] Converted: [cyan]{md_file.name}[/cyan] → [cyan]{output_path.name}[/cyan]")
            return True
        except subprocess.CalledProcessError as e:
            console.print(f"[red]✗[/red] Error converting {md_file.name}")
            console.print(f"[red]{e.stderr.decode()}[/red]")
            return False

    def merge_md_files(
        self,
        md_files: List[Path],
        output_name: str,
        output_dir: Optional[Path] = None,
        metadata: Optional[Dict] = None
    ) -> bool:
        """Merge multiple markdown files into a single ePub."""

        if not md_files:
            console.print("[red]✗[/red] No files to merge")
            return False

        console.print(f"\n[cyan]📚 Merging {len(md_files)} file(s)...[/cyan]")

        # Create temporary merged file
        with tempfile.NamedTemporaryFile(
            mode='w',
            suffix='.md',
            delete=False,
            encoding='utf-8'
        ) as tmp_file:
            tmp_path = Path(tmp_file.name)

            # Write merged content
            for i, md_file in enumerate(md_files):
                console.print(f"  [{i+1}/{len(md_files)}] Adding: [cyan]{md_file.name}[/cyan]")

                with open(md_file, 'r', encoding='utf-8') as f:
                    content = f.read()

                    # Remove frontmatter from individual files
                    try:
                        post = frontmatter.loads(content)
                        content = post.content
                    except Exception:
                        pass

                    tmp_file.write(content)

                    # Add page break between files (except for last one)
                    if i < len(md_files) - 1:
                        tmp_file.write("\n\n---\n\n")

        # Determine output path
        if output_dir:
            output_path = output_dir / f"{output_name}.epub"
            output_path.parent.mkdir(parents=True, exist_ok=True)
        else:
            output_path = md_files[0].parent / f"{output_name}.epub"

        # Build pandoc command
        cmd = [
            'pandoc',
            str(tmp_path),
            '-o', str(output_path),
            '--toc',
            '--toc-depth=3',
            '--epub-chapter-level=2',
        ]

        # Add CSS
        if self.css_file and Path(self.css_file).exists():
            cmd.extend(['--css', self.css_file])

        # Add metadata
        if metadata:
            for key in ['title', 'author', 'lang', 'description', 'publisher', 'date']:
                if key in metadata and metadata[key]:
                    cmd.extend(['--metadata', f'{key}={metadata[key]}'])

        # Execute conversion
        try:
            subprocess.run(cmd, check=True, capture_output=True)
            console.print(f"\n[green]✓[/green] Merged ePub created: [cyan]{output_path.name}[/cyan]")
            return True
        except subprocess.CalledProcessError as e:
            console.print(f"[red]✗[/red] Error creating merged ePub")
            console.print(f"[red]{e.stderr.decode()}[/red]")
            return False
        finally:
            # Clean up temp file
            tmp_path.unlink(missing_ok=True)

    def batch_convert_directory(
        self,
        input_dir: Path,
        output_dir: Optional[Path] = None,
        recursive: bool = False,
        metadata_template: Optional[Dict] = None
    ) -> tuple:
        """Convert all markdown files in a directory to individual ePub files."""

        if not input_dir.exists():
            console.print(f"[red]✗[/red] Directory not found: {input_dir}")
            return 0, 0

        # Find all .md files
        if recursive:
            md_files = list(input_dir.rglob('*.md'))
        else:
            md_files = list(input_dir.glob('*.md'))

        if not md_files:
            console.print(f"[red]✗[/red] No .md files found in {input_dir}")
            return 0, 0

        console.print(f"\n[cyan]📚 Found {len(md_files)} markdown file(s)[/cyan]\n")

        success_count = 0

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            console=console
        ) as progress:
            task = progress.add_task("[cyan]Converting files...", total=len(md_files))

            for md_file in md_files:
                # Extract or use template metadata
                if metadata_template:
                    file_metadata = metadata_template.copy()
                    if 'title' not in file_metadata:
                        file_metadata['title'] = md_file.stem.replace('_', ' ').replace('-', ' ').title()
                else:
                    file_metadata = self.extract_metadata_from_file(md_file)
                    if 'author' not in file_metadata:
                        file_metadata['author'] = self.author

                if self.convert_single_file(md_file, output_dir, file_metadata):
                    success_count += 1

                progress.update(task, advance=1)

        console.print(f"\n[green]✓[/green] Conversion complete: {success_count}/{len(md_files)} files converted")
        return success_count, len(md_files)


def display_welcome():
    """Display welcome banner."""
    console.print(Panel.fit(
        "[bold cyan]MD to ePub Converter[/bold cyan]\n"
        "[dim]Professional Edition[/dim]\n\n"
        "Created by: [yellow]kxrz[/yellow] ([dim]https://github.com/kxrz[/dim])\n"
        "Universal tool for converting Markdown to ePub",
        border_style="cyan"
    ))


def main_menu(converter: EpubConverter):
    """Display and handle main menu."""

    choices = [
        "Convert single file to ePub",
        "Merge multiple files into one ePub",
        "Convert directory (one ePub per file)",
        "Merge directory into one ePub",
        "Create/regenerate CSS file",
        "Exit"
    ]

    choice = questionary.select(
        "What would you like to do?",
        choices=choices,
        style=custom_style
    ).ask()

    if choice == choices[0]:  # Single file
        file_path = questionary.path(
            "Select markdown file:",
            only_files=True,
            style=custom_style
        ).ask()

        if file_path:
            md_file = Path(file_path)
            if md_file.suffix != '.md':
                console.print("[red]✗[/red] File must have .md extension")
                return

            # Get metadata
            default_metadata = converter.extract_metadata_from_file(md_file)
            metadata = converter.get_metadata_interactive(default_metadata.get('title'))

            # Output directory
            use_custom_output = questionary.confirm(
                "Use custom output directory?",
                default=False,
                style=custom_style
            ).ask()

            output_dir = None
            if use_custom_output:
                output_path = questionary.path(
                    "Select output directory:",
                    only_directories=True,
                    style=custom_style
                ).ask()
                if output_path:
                    output_dir = Path(output_path)

            converter.convert_single_file(md_file, output_dir, metadata)

    elif choice == choices[1]:  # Merge multiple files
        console.print("\n[cyan]Select multiple markdown files to merge[/cyan]")
        console.print("[dim]Enter file paths one by one. Press Enter with empty input when done.[/dim]\n")

        md_files = []
        while True:
            file_path = questionary.path(
                f"File #{len(md_files) + 1} (or press Enter to finish):",
                only_files=True,
                style=custom_style
            ).ask()

            if not file_path or file_path.strip() == "":
                break

            md_file = Path(file_path)
            if md_file.exists() and md_file.suffix == '.md':
                md_files.append(md_file)
                console.print(f"[green]✓[/green] Added: {md_file.name}")
            else:
                console.print("[red]✗[/red] Invalid file or not a .md file")

        if not md_files:
            console.print("[yellow]⚠[/yellow] No files selected")
            return

        # Get output name
        output_name = questionary.text(
            "Name for merged ePub:",
            default="merged_document",
            style=custom_style
        ).ask()

        # Get metadata
        metadata = converter.get_metadata_interactive(output_name)

        # Output directory
        use_custom_output = questionary.confirm(
            "Use custom output directory?",
            default=False,
            style=custom_style
        ).ask()

        output_dir = None
        if use_custom_output:
            output_path = questionary.path(
                "Select output directory:",
                only_directories=True,
                style=custom_style
            ).ask()
            if output_path:
                output_dir = Path(output_path)

        converter.merge_md_files(md_files, output_name, output_dir, metadata)

    elif choice == choices[2]:  # Directory to multiple ePub
        dir_path = questionary.path(
            "Select directory containing markdown files:",
            only_directories=True,
            style=custom_style
        ).ask()

        if not dir_path:
            return

        input_dir = Path(dir_path)

        # Recursive option
        recursive = questionary.confirm(
            "Include subdirectories?",
            default=False,
            style=custom_style
        ).ask()

        # Output directory
        use_custom_output = questionary.confirm(
            "Use custom output directory?",
            default=False,
            style=custom_style
        ).ask()

        output_dir = None
        if use_custom_output:
            output_path = questionary.path(
                "Select output directory:",
                only_directories=True,
                style=custom_style
            ).ask()
            if output_path:
                output_dir = Path(output_path)

        # Common author for all files
        use_common_author = questionary.confirm(
            "Use same author for all files?",
            default=True,
            style=custom_style
        ).ask()

        metadata_template = {}
        if use_common_author:
            author = questionary.text(
                "Author name:",
                default=converter.author,
                style=custom_style
            ).ask()
            metadata_template['author'] = author

        converter.batch_convert_directory(input_dir, output_dir, recursive, metadata_template)

    elif choice == choices[3]:  # Merge directory into one ePub
        dir_path = questionary.path(
            "Select directory containing markdown files:",
            only_directories=True,
            style=custom_style
        ).ask()

        if not dir_path:
            return

        input_dir = Path(dir_path)

        # Recursive option
        recursive = questionary.confirm(
            "Include subdirectories?",
            default=False,
            style=custom_style
        ).ask()

        # Find files
        if recursive:
            md_files = sorted(list(input_dir.rglob('*.md')))
        else:
            md_files = sorted(list(input_dir.glob('*.md')))

        if not md_files:
            console.print(f"[red]✗[/red] No .md files found in {input_dir}")
            return

        console.print(f"\n[cyan]Found {len(md_files)} file(s):[/cyan]")
        for i, f in enumerate(md_files, 1):
            console.print(f"  {i}. {f.name}")

        proceed = questionary.confirm(
            f"\nMerge all {len(md_files)} files into one ePub?",
            default=True,
            style=custom_style
        ).ask()

        if not proceed:
            return

        # Get output name
        output_name = questionary.text(
            "Name for merged ePub:",
            default=input_dir.name,
            style=custom_style
        ).ask()

        # Get metadata
        metadata = converter.get_metadata_interactive(output_name)

        # Output directory
        use_custom_output = questionary.confirm(
            "Use custom output directory?",
            default=False,
            style=custom_style
        ).ask()

        output_dir = None
        if use_custom_output:
            output_path = questionary.path(
                "Select output directory:",
                only_directories=True,
                style=custom_style
            ).ask()
            if output_path:
                output_dir = Path(output_path)

        converter.merge_md_files(md_files, output_name, output_dir, metadata)

    elif choice == choices[4]:  # Create CSS
        converter.create_optimized_css()

    elif choice == choices[5]:  # Exit
        console.print("\n[cyan]Thanks for using MD to ePub Converter![/cyan]")
        console.print("[dim]Created by kxrz (https://github.com/kxrz)[/dim]\n")
        sys.exit(0)


def cli_mode():
    """Handle legacy CLI mode for backward compatibility."""
    parser = argparse.ArgumentParser(
        description='Convert Markdown files to ePub - Professional Edition',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Interactive mode (default)
  python md_to_epub.py

  # Convert a single file (CLI mode)
  python md_to_epub.py my_file.md --author "Your Name"

  # Convert all files in a directory
  python md_to_epub.py --dir ./my_notes --output ./epubs

  # Create CSS file
  python md_to_epub.py --create-css
        """
    )

    parser.add_argument('input', nargs='?', help='Markdown file or directory')
    parser.add_argument('--dir', '-d', help='Directory containing .md files')
    parser.add_argument('--output', '-o', help='Output directory')
    parser.add_argument('--css', '-c', help='Custom CSS file path')
    parser.add_argument('--create-css', action='store_true', help='Create optimized CSS file')
    parser.add_argument('--recursive', '-r', action='store_true', help='Include subdirectories')
    parser.add_argument('--author', '-a', help='Author name')
    parser.add_argument('--title', '-t', help='Title for ePub')
    parser.add_argument('--merge', '-m', action='store_true', help='Merge multiple files into one ePub')

    args = parser.parse_args()

    # If no arguments, launch interactive mode
    if len(sys.argv) == 1:
        return None

    converter = EpubConverter()

    # Check pandoc
    if not args.create_css:
        if not converter.check_pandoc():
            sys.exit(1)

    # Handle CSS creation
    if args.create_css:
        converter.create_optimized_css()
        return True

    # Set CSS file
    if args.css:
        converter.css_file = args.css
    else:
        converter.css_file = str(converter.default_css_path) if converter.default_css_path.exists() else None

    # Set author
    if args.author:
        converter.author = args.author

    # Handle directory mode
    if args.dir:
        input_dir = Path(args.dir)
        output_dir = Path(args.output) if args.output else None

        if args.merge:
            # Merge all files in directory
            if args.recursive:
                md_files = sorted(list(input_dir.rglob('*.md')))
            else:
                md_files = sorted(list(input_dir.glob('*.md')))

            output_name = args.title or input_dir.name
            metadata = {'author': converter.author, 'title': output_name, 'lang': 'en'}

            converter.merge_md_files(md_files, output_name, output_dir, metadata)
        else:
            # Convert each file individually
            metadata_template = {'author': converter.author, 'lang': 'en'}
            if args.title:
                metadata_template['title'] = args.title

            converter.batch_convert_directory(input_dir, output_dir, args.recursive, metadata_template)

        return True

    # Handle single file mode
    elif args.input:
        input_path = Path(args.input)

        if input_path.is_dir():
            # Treat as directory
            output_dir = Path(args.output) if args.output else None
            metadata_template = {'author': converter.author, 'lang': 'en'}
            converter.batch_convert_directory(input_path, output_dir, args.recursive, metadata_template)
        elif input_path.suffix == '.md':
            output_dir = Path(args.output) if args.output else None
            metadata = {
                'author': converter.author,
                'title': args.title or input_path.stem.replace('_', ' ').replace('-', ' ').title(),
                'lang': 'en'
            }
            converter.convert_single_file(input_path, output_dir, metadata)
        else:
            console.print("[red]✗[/red] File must have .md extension")
            return False

        return True

    else:
        parser.print_help()
        return True


def main():
    """Main entry point."""
    # Try CLI mode first
    cli_result = cli_mode()

    if cli_result is not None:
        # CLI mode was used
        sys.exit(0 if cli_result else 1)

    # Interactive mode
    display_welcome()

    converter = EpubConverter()

    # Check pandoc
    if not converter.check_pandoc():
        console.print("\n[red]Cannot proceed without Pandoc installed.[/red]")
        sys.exit(1)

    console.print()

    # CSS setup
    converter.css_file = converter.detect_or_create_css()

    # Main loop
    while True:
        console.print()
        try:
            main_menu(converter)
        except KeyboardInterrupt:
            console.print("\n\n[cyan]Interrupted by user[/cyan]")
            break

        # Ask to continue
        console.print()
        continue_choice = questionary.confirm(
            "Perform another operation?",
            default=True,
            style=custom_style
        ).ask()

        if not continue_choice:
            break

    console.print("\n[cyan]Thanks for using MD to ePub Converter![/cyan]")
    console.print("[dim]Created by kxrz (https://github.com/kxrz)[/dim]\n")


if __name__ == '__main__':
    main()
