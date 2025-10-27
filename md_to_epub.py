#!/usr/bin/env python3
"""
Script to convert Markdown files to ePub with beautiful formatting.
Requires: pip install pypandoc markdown ebooklib
"""

import os
import sys
import argparse
from pathlib import Path
import subprocess

def check_pandoc():
    """Check if Pandoc is installed."""
    try:
        subprocess.run(['pandoc', '--version'], capture_output=True, check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("❌ Pandoc is not installed!")
        print("Installation:")
        print("  - macOS: brew install pandoc")
        print("  - Linux: sudo apt install pandoc")
        print("  - Windows: download from https://pandoc.org/installing.html")
        return False

def convert_md_to_epub(md_file, output_dir=None, css_file=None, metadata=None):
    """
    Convert a Markdown file to ePub.
    
    Args:
        md_file: Path to the .md file
        output_dir: Output directory (optional)
        css_file: Custom CSS file (optional)
        metadata: Dictionary with title, author, etc.
    """
    md_path = Path(md_file)
    
    if not md_path.exists():
        print(f"❌ File not found: {md_file}")
        return False
    
    # Determine output name
    if output_dir:
        output_path = Path(output_dir) / f"{md_path.stem}.epub"
        output_path.parent.mkdir(parents=True, exist_ok=True)
    else:
        output_path = md_path.with_suffix('.epub')
    
    # Build pandoc command
    cmd = [
        'pandoc',
        str(md_path),
        '-o', str(output_path),
        '--toc',  # Table of contents
        '--toc-depth=3',
        '--epub-chapter-level=2',
    ]
    
    # Add CSS if provided
    if css_file and Path(css_file).exists():
        cmd.extend(['--css', css_file])
    
    # Add metadata
    if metadata:
        if 'title' in metadata:
            cmd.extend(['--metadata', f'title={metadata["title"]}'])
        if 'author' in metadata:
            cmd.extend(['--metadata', f'author={metadata["author"]}'])
        if 'lang' in metadata:
            cmd.extend(['--metadata', f'lang={metadata["lang"]}'])
        if 'cover' in metadata and Path(metadata['cover']).exists():
            cmd.extend(['--epub-cover-image', metadata['cover']])
    
    # Execute conversion
    try:
        subprocess.run(cmd, check=True, capture_output=True)
        print(f"✅ Converted: {md_path.name} → {output_path.name}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Error converting {md_path.name}")
        print(e.stderr.decode())
        return False

def create_default_css(css_path='style.css'):
    """Create a default CSS file for beautiful rendering."""
    css_content = """/* Style for ePub generated from Markdown */

body {
    font-family: "Georgia", "Times New Roman", serif;
    font-size: 1.1em;
    line-height: 1.6;
    margin: 1em;
    text-align: justify;
}

h1, h2, h3, h4, h5, h6 {
    font-family: "Helvetica", "Arial", sans-serif;
    font-weight: bold;
    margin-top: 1.5em;
    margin-bottom: 0.5em;
    page-break-after: avoid;
}

h1 {
    font-size: 2em;
    border-bottom: 2px solid #333;
    padding-bottom: 0.3em;
}

h2 {
    font-size: 1.6em;
    color: #444;
}

h3 {
    font-size: 1.3em;
    color: #666;
}

p {
    margin: 0.8em 0;
    text-indent: 1.5em;
}

/* No indentation after headings */
h1 + p, h2 + p, h3 + p, h4 + p, h5 + p, h6 + p {
    text-indent: 0;
}

code {
    font-family: "Courier New", monospace;
    background-color: #f5f5f5;
    padding: 0.2em 0.4em;
    border-radius: 3px;
    font-size: 0.9em;
}

pre {
    background-color: #f5f5f5;
    padding: 1em;
    border-radius: 5px;
    overflow-x: auto;
    line-height: 1.4;
}

pre code {
    background-color: transparent;
    padding: 0;
}

blockquote {
    border-left: 4px solid #ccc;
    margin: 1em 0;
    padding-left: 1em;
    color: #666;
    font-style: italic;
}

a {
    color: #0066cc;
    text-decoration: none;
}

a:hover {
    text-decoration: underline;
}

ul, ol {
    margin: 1em 0;
    padding-left: 2em;
}

li {
    margin: 0.5em 0;
}

img {
    max-width: 100%;
    height: auto;
    display: block;
    margin: 1em auto;
}

hr {
    border: none;
    border-top: 1px solid #ccc;
    margin: 2em 0;
}

table {
    border-collapse: collapse;
    width: 100%;
    margin: 1em 0;
}

th, td {
    border: 1px solid #ddd;
    padding: 0.5em;
    text-align: left;
}

th {
    background-color: #f5f5f5;
    font-weight: bold;
}
"""
    
    with open(css_path, 'w', encoding='utf-8') as f:
        f.write(css_content)
    print(f"✅ CSS file created: {css_path}")
    return css_path

def batch_convert(input_dir, output_dir=None, css_file=None, recursive=False):
    """Convert all .md files in a directory."""
    input_path = Path(input_dir)
    
    if not input_path.exists():
        print(f"❌ Directory not found: {input_dir}")
        return
    
    # Find all .md files
    if recursive:
        md_files = list(input_path.rglob('*.md'))
    else:
        md_files = list(input_path.glob('*.md'))
    
    if not md_files:
        print(f"❌ No .md files found in {input_dir}")
        return
    
    print(f"📚 {len(md_files)} Markdown file(s) found\n")
    
    success_count = 0
    for md_file in md_files:
        # Extract title from first heading if possible
        title = md_file.stem.replace('_', ' ').replace('-', ' ').title()
        
        metadata = {
            'title': title,
            'lang': 'en'
        }
        
        if convert_md_to_epub(md_file, output_dir, css_file, metadata):
            success_count += 1
    
    print(f"\n✨ Conversion complete: {success_count}/{len(md_files)} files converted")

def main():
    parser = argparse.ArgumentParser(
        description='Convert Markdown files to ePub with beautiful formatting',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Convert a single file
  python md_to_epub.py my_file.md
  
  # Convert all .md files in a directory
  python md_to_epub.py --dir ./my_notes --output ./epubs
  
  # Create a default CSS file
  python md_to_epub.py --create-css
  
  # Use custom CSS
  python md_to_epub.py my_file.md --css my_style.css
        """
    )
    
    parser.add_argument('input', nargs='?', help='Markdown file or directory to convert')
    parser.add_argument('--dir', '-d', help='Directory containing .md files')
    parser.add_argument('--output', '-o', help='Output directory for ePub files')
    parser.add_argument('--css', '-c', help='Custom CSS file')
    parser.add_argument('--create-css', action='store_true', 
                       help='Create a default CSS file (style.css)')
    parser.add_argument('--recursive', '-r', action='store_true',
                       help='Recursive search in subdirectories')
    parser.add_argument('--author', '-a', help='Author name')
    
    args = parser.parse_args()
    
    # Special case: CSS creation
    if args.create_css:
        create_default_css()
        return
    
    # Check if Pandoc is installed
    if not check_pandoc():
        sys.exit(1)
    
    # Determine operating mode
    if args.dir:
        # Batch mode: convert entire directory
        batch_convert(args.dir, args.output, args.css, args.recursive)
    elif args.input:
        input_path = Path(args.input)
        if input_path.is_dir():
            # Input is actually a directory
            batch_convert(args.input, args.output, args.css, args.recursive)
        elif input_path.suffix == '.md':
            # Convert a single file
            metadata = {
                'title': input_path.stem.replace('_', ' ').replace('-', ' ').title(),
                'lang': 'en'
            }
            if args.author:
                metadata['author'] = args.author
            
            convert_md_to_epub(args.input, args.output, args.css, metadata)
        else:
            print("❌ File must have .md extension")
    else:
        parser.print_help()

if __name__ == '__main__':
    main()
