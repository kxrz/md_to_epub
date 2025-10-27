# Markdown to ePub Converter

Python script to convert your Markdown files to ePub with elegant and professional formatting.

## 📋 Prerequisites

### 1. Install Pandoc

The script uses Pandoc for conversion:

**macOS:**

```bash
brew install pandoc
```

**Linux (Ubuntu/Debian):**

```bash
sudo apt install pandoc
```

**Windows:**
Download the installer from [pandoc.org](https://pandoc.org/installing.html)

### 2. Make the script executable (Linux/macOS)

```bash
chmod +x md_to_epub.py
```

## 🚀 Usage

### Convert a single file

```bash
python md_to_epub.py my_document.md
```

### Convert all files in a directory

```bash
python md_to_epub.py --dir ./my_notes
```

### Specify an output directory

```bash
python md_to_epub.py --dir ./my_notes --output ./my_epubs
```

### Create a default CSS file

```bash
python md_to_epub.py --create-css
```

This creates a `style.css` file that you can customize.

### Use custom CSS

```bash
python md_to_epub.py my_document.md --css my_style.css
```

### Recursive conversion (includes subdirectories)

```bash
python md_to_epub.py --dir ./my_notes --recursive --output ./epubs
```

### Add an author

```bash
python md_to_epub.py my_document.md --author "Your Name"
```

## ✨ Features

- ✅ **Automatic conversion** from .md to .epub
- ✅ **Table of contents** generated automatically
- ✅ **Customizable CSS** for elegant rendering
- ✅ **Batch processing** of multiple files
- ✅ **Metadata** support (title, author, language)
- ✅ **Support for images**, code, tables, etc.
- ✅ **Recursive search** in subdirectories

## 🎨 Style Customization

The script creates a default CSS with:

- Elegant serif font for text
- Sans-serif font for headings
- Syntax highlighting for code
- Clean and readable layout
- Support for tables, quotes, lists

You can modify `style.css` to match your preferences!

## 📝 Supported Markdown Format

The script supports all standard Markdown:

- Headings (`#`, `##`, etc.)
- Numbered and bulleted lists
- **Bold** and *italic*
- `Inline code` and code blocks
- Quotes
- Links and images
- Tables
- And more!

## 💡 Tips

### Chapter Titles

Use `# Title` for main chapters and `## Subtitle` for sections.

### YAML Frontmatter

You can add metadata at the beginning of your files:

```markdown
---
title: My Amazing Book
author: Your Name
lang: en
---

# Chapter 1
...
```

### Images

Local images will be embedded in the ePub:

```markdown
![Description](./images/photo.jpg)
```

## 🔧 Complete Options

```
usage: md_to_epub.py [-h] [--dir DIR] [--output OUTPUT] [--css CSS]
                     [--create-css] [--recursive] [--author AUTHOR]
                     [input]

Options:
  input                 Markdown file or directory to convert
  --dir, -d            Directory containing .md files
  --output, -o         Output directory for ePub files
  --css, -c            Custom CSS file
  --create-css         Create a default CSS file
  --recursive, -r      Recursive search in subdirectories
  --author, -a         Author name
```

## 🎯 Practical Examples

### Convert an entire notes library

```bash
python md_to_epub.py --dir ~/Documents/notes --output ~/Books/epubs --recursive
```

### Create a book with custom style

```bash
# 1. Create the base CSS
python md_to_epub.py --create-css

# 2. Edit style.css to your liking

# 3. Convert with your style
python md_to_epub.py my_book.md --css style.css --author "Your Name"
```

## 📱 For Your Xteink X4

Once the ePub files are generated, simply transfer them to your Xteink X4 via USB or the file management app!

Enjoy your Markdown content with professional formatting on your e-reader 📚

## ❓ Help

To display help:

```bash
python md_to_epub.py --help
```

Happy reading! 🎉
