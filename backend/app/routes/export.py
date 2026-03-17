import os
import sys
import re
import html as html_module
import platform
import base64
import io
import urllib.parse

import markdown
from fpdf import FPDF
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()


def _get_bundled_font_path():
    """Get font path from bundled assets (PyInstaller or dev environment)."""
    if getattr(sys, 'frozen', False):
        base_dir = sys._MEIPASS
    else:
        base_dir = os.path.dirname(os.path.abspath(__file__))
    font_path = os.path.join(base_dir, "assets", "fonts", "NotoSansTC-Regular.ttf")
    if os.path.exists(font_path):
        return font_path
    return None


def _find_cjk_font_path():
    """
    Font search order:
    1. Bundled font in assets (preferred)
    2. Windows system fonts (fallback, .ttf only)
    """
    bundled = _get_bundled_font_path()
    if bundled:
        return bundled

    if platform.system() == "Windows":
        fonts_dir = os.path.join(
            os.environ.get("WINDIR", r"C:\Windows"), "Fonts"
        )
        for filename in ["kaiu.ttf", "msjhbd.ttf", "msjh.ttf"]:
            fpath = os.path.join(fonts_dir, filename)
            if os.path.exists(fpath):
                return fpath
    return None


class ExportRequest(BaseModel):
    content: str
    path: str
    md_path: str = ""  # source .md file path, used to resolve relative image paths


def _validate_export_path(file_path: str, extension: str) -> str:
    normalized = os.path.normpath(file_path)
    if not os.path.isabs(normalized):
        raise HTTPException(status_code=400, detail="Absolute path required")
    if not normalized.lower().endswith(extension):
        normalized += extension
    return normalized


def _convert_md(md_content: str):
    md_instance = markdown.Markdown(
        extensions=["toc", "fenced_code", "tables"],
        extension_configs={"toc": {"permalink": False, "toc_depth": "1-4"}},
    )
    body = md_instance.convert(md_content)
    toc = md_instance.toc
    return body, toc


def _extract_title(md_content: str) -> str:
    for line in md_content.split("\n"):
        stripped = line.strip()
        if stripped.startswith("#"):
            return stripped.lstrip("#").strip()
    return "Markdown Document"


def _strip_html_tags(text: str) -> str:
    """Remove HTML tags and decode entities."""
    text = re.sub(r"<[^>]+>", "", text)
    text = html_module.unescape(text)
    return text


def _parse_md_blocks(md_content: str):
    """Parse markdown into structured blocks for PDF rendering."""
    blocks = []
    lines = md_content.split("\n")
    i = 0
    in_code_block = False
    code_buf = []

    while i < len(lines):
        line = lines[i]

        # Fenced code block
        if line.strip().startswith("```"):
            if in_code_block:
                blocks.append({"type": "code", "text": "\n".join(code_buf)})
                code_buf = []
                in_code_block = False
            else:
                in_code_block = True
            i += 1
            continue

        if in_code_block:
            code_buf.append(line)
            i += 1
            continue

        stripped = line.strip()

        # Empty line
        if not stripped:
            i += 1
            continue

        # Headings
        if stripped.startswith("#"):
            match = re.match(r"^(#{1,6})\s+(.*)", stripped)
            if match:
                level = len(match.group(1))
                blocks.append({"type": f"h{level}", "text": match.group(2)})
                i += 1
                continue

        # Horizontal rule
        if re.match(r"^(-{3,}|_{3,}|\*{3,})$", stripped):
            blocks.append({"type": "hr"})
            i += 1
            continue

        # Unordered list
        if re.match(r"^[-*+]\s+", stripped):
            items = []
            while i < len(lines) and re.match(r"^\s*[-*+]\s+", lines[i]):
                item_text = re.sub(r"^\s*[-*+]\s+", "", lines[i])
                items.append(item_text.strip())
                i += 1
            blocks.append({"type": "ul", "items": items})
            continue

        # Ordered list
        if re.match(r"^\d+\.\s+", stripped):
            items = []
            while i < len(lines) and re.match(r"^\s*\d+\.\s+", lines[i]):
                item_text = re.sub(r"^\s*\d+\.\s+", "", lines[i])
                items.append(item_text.strip())
                i += 1
            blocks.append({"type": "ol", "items": items})
            continue

        # Blockquote
        if stripped.startswith(">"):
            quote_lines = []
            while i < len(lines) and lines[i].strip().startswith(">"):
                quote_lines.append(lines[i].strip().lstrip(">").strip())
                i += 1
            blocks.append({"type": "blockquote", "text": " ".join(quote_lines)})
            continue

        # Table
        if "|" in stripped:
            table_lines = []
            while i < len(lines) and "|" in lines[i]:
                table_lines.append(lines[i].strip())
                i += 1
            # Parse table
            rows = []
            for tl in table_lines:
                cells = [c.strip() for c in tl.strip("|").split("|")]
                # Skip separator row
                if all(re.match(r"^[-:]+$", c) for c in cells):
                    continue
                rows.append(cells)
            if rows:
                blocks.append({"type": "table", "rows": rows})
            continue

        # Standalone image  ![alt](src)
        img_match = re.match(r"^!\[([^\]]*)\]\((.+?)\)$", stripped)
        if img_match:
            blocks.append({"type": "image", "alt": img_match.group(1), "src": img_match.group(2)})
            i += 1
            continue

        # Regular paragraph
        para_lines = [stripped]
        i += 1
        while i < len(lines) and lines[i].strip() and not lines[i].strip().startswith("#") and not lines[i].strip().startswith("```") and not lines[i].strip().startswith(">") and not re.match(r"^[-*+]\s+", lines[i].strip()) and not re.match(r"^\d+\.\s+", lines[i].strip()):
            para_lines.append(lines[i].strip())
            i += 1
        blocks.append({"type": "p", "text": " ".join(para_lines)})

    if in_code_block and code_buf:
        blocks.append({"type": "code", "text": "\n".join(code_buf)})

    return blocks


def _clean_inline_md(text: str) -> str:
    """Remove inline markdown syntax like **bold**, *italic*, `code`, [link](url)."""
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)  # bold
    text = re.sub(r"\*(.+?)\*", r"\1", text)  # italic
    text = re.sub(r"`(.+?)`", r"\1", text)  # inline code
    text = re.sub(r"\[(.+?)\]\(.+?\)", r"\1", text)  # links
    text = re.sub(r"!\[.*?\]\(.+?\)", "[image]", text)  # images
    return text


def _resolve_image(src: str, md_dir: str = ""):
    """
    Resolve an image src to (image_source, label).
    image_source: absolute file path (str), io.BytesIO, or None
    label: human-readable label shown above the image in PDF
    """
    # Local API URL: http://127.0.0.1:PORT/api/image?path=<abs_path>
    if src.startswith("http://") or src.startswith("https://"):
        try:
            parsed = urllib.parse.urlparse(src)
            params = urllib.parse.parse_qs(parsed.query)
            if "path" in params:
                abs_path = params["path"][0]
                return abs_path, os.path.basename(abs_path)
        except Exception:
            pass
        return None, src

    # Data URL (base64 embedded image)
    m = re.match(r"^data:image/([^;]+);base64,(.+)$", src, re.DOTALL)
    if m:
        ext = m.group(1).split("+")[0]  # e.g. svg+xml → svg
        label = f"embedded_image.{ext}"
        try:
            img_bytes = base64.b64decode(m.group(2))
            return io.BytesIO(img_bytes), label
        except Exception:
            return None, label

    # Absolute path
    if os.path.isabs(src):
        return src, os.path.basename(src)

    # Relative path – resolve against md_dir
    if md_dir:
        abs_path = os.path.normpath(os.path.join(md_dir, src))
        return abs_path, src

    return None, src


class MarkdownPDF(FPDF):
    def __init__(self, font_path=None):
        super().__init__()
        self._has_cjk = False
        if font_path and os.path.exists(font_path):
            try:
                self.add_font("CJK", "", font_path)
                self._has_cjk = True
                print(f"[INFO] CJK font loaded: {font_path}")
            except Exception as e:
                print(f"[WARN] CJK font load failed: {e}")
        else:
            print(f"[WARN] No CJK font found at: {font_path}")

    def _use_font(self, style="", size=10):
        if self._has_cjk:
            self.set_font("CJK", "", size)
        else:
            self.set_font("Helvetica", style, size)

    def _mc(self, w, h, txt, **kwargs):
        """multi_cell with cursor reset to left margin."""
        kwargs.setdefault("new_x", "LMARGIN")
        kwargs.setdefault("new_y", "NEXT")
        self.set_x(self.l_margin)
        self.multi_cell(w, h, txt, **kwargs)

    def header(self):
        pass

    def footer(self):
        self.set_y(-15)
        self._use_font("", 8)
        self.set_text_color(150, 150, 150)
        self.cell(0, 10, f"{self.page_no()}", align="C", new_x="LMARGIN", new_y="NEXT")

    def render_blocks(self, blocks, md_dir=""):
        heading_sizes = {"h1": 22, "h2": 17, "h3": 14, "h4": 12, "h5": 11, "h6": 10}
        toc_entries = []

        for block in blocks:
            btype = block["type"]

            if btype in heading_sizes:
                size = heading_sizes[btype]
                level = int(btype[1])
                text = _clean_inline_md(block["text"])
                self.ln(4 if level > 1 else 6)
                self._use_font("B", size)
                self.set_text_color(44, 62, 80)
                link = self.add_link()
                self.set_link(link, y=self.get_y(), page=self.page)
                toc_entries.append({"level": level, "text": text, "link": link, "page": self.page})
                self.start_section(text, level - 1)
                self._mc(0, size * 0.55, text)
                if level <= 2:
                    self.set_draw_color(200, 200, 200)
                    self.line(self.l_margin, self.get_y() + 1, self.w - self.r_margin, self.get_y() + 1)
                    self.ln(3)
                else:
                    self.ln(2)

            elif btype == "p":
                text = _clean_inline_md(block["text"])
                self._use_font("", 10)
                self.set_text_color(51, 51, 51)
                self._mc(0, 6, text)
                self.ln(2)

            elif btype == "code":
                self.set_fill_color(244, 244, 244)
                self._use_font("", 8)
                self.set_text_color(51, 51, 51)
                self._mc(0, 4.5, block["text"], fill=True)
                self.ln(3)

            elif btype == "ul":
                self._use_font("", 10)
                self.set_text_color(51, 51, 51)
                for item in block["items"]:
                    text = _clean_inline_md(item)
                    self.set_x(self.l_margin)
                    self.cell(6, 6, "-", new_x="RIGHT", new_y="TOP")
                    self.multi_cell(0, 6, text, new_x="LMARGIN", new_y="NEXT")
                self.ln(2)

            elif btype == "ol":
                self._use_font("", 10)
                self.set_text_color(51, 51, 51)
                for idx, item in enumerate(block["items"], 1):
                    text = _clean_inline_md(item)
                    self.set_x(self.l_margin)
                    self.cell(8, 6, f"{idx}.", new_x="RIGHT", new_y="TOP")
                    self.multi_cell(0, 6, text, new_x="LMARGIN", new_y="NEXT")
                self.ln(2)

            elif btype == "blockquote":
                text = _clean_inline_md(block["text"])
                self.set_fill_color(249, 249, 249)
                self.set_draw_color(52, 152, 219)
                self.set_x(self.l_margin)
                y_start = self.get_y()
                self.set_x(self.l_margin + 6)
                self._use_font("I", 10)
                self.set_text_color(85, 85, 85)
                self.multi_cell(self.w - self.l_margin - self.r_margin - 10, 6, text,
                                fill=True, new_x="LMARGIN", new_y="NEXT")
                y_end = self.get_y()
                self.set_draw_color(52, 152, 219)
                self.set_line_width(0.8)
                self.line(self.l_margin + 2, y_start, self.l_margin + 2, y_end)
                self.set_line_width(0.2)
                self.ln(3)

            elif btype == "table":
                rows = block["rows"]
                if not rows:
                    continue
                col_count = max(len(r) for r in rows)
                col_w = (self.w - self.l_margin - self.r_margin) / col_count
                is_header = True
                for row in rows:
                    if is_header:
                        self.set_fill_color(240, 240, 240)
                        self._use_font("B", 9)
                        self.set_text_color(51, 51, 51)
                        is_header = False
                    else:
                        self.set_fill_color(255, 255, 255)
                        self._use_font("", 9)
                        self.set_text_color(51, 51, 51)
                    self.set_x(self.l_margin)
                    for ci, cell_text in enumerate(row):
                        if ci < col_count:
                            txt = _clean_inline_md(cell_text)
                            self.cell(col_w, 7, txt, border=1, fill=True,
                                      new_x="RIGHT", new_y="TOP")
                    self.ln(7)
                self.ln(3)

            elif btype == "hr":
                self.ln(4)
                self.set_draw_color(200, 200, 200)
                self.line(self.l_margin, self.get_y(), self.w - self.r_margin, self.get_y())
                self.ln(4)

            elif btype == "image":
                src = block["src"]
                alt = block.get("alt", "")
                img_source, label = _resolve_image(src, md_dir)

                # Label above: image path / filename
                display_label = label if label else (alt if alt else src)
                self.ln(2)
                self._use_font("", 8)
                self.set_text_color(80, 80, 80)
                self._mc(0, 5, f"[Image] {display_label}")

                # Render image below label
                if img_source is not None:
                    try:
                        if isinstance(img_source, str) and not os.path.exists(img_source):
                            raise FileNotFoundError(f"{img_source}")
                        available_w = self.w - self.l_margin - self.r_margin
                        self.set_x(self.l_margin)
                        self.image(img_source, x=self.l_margin, w=available_w)
                    except Exception as e:
                        self._use_font("", 9)
                        self.set_text_color(180, 0, 0)
                        self._mc(0, 6, f"[Image error: {e}]")
                else:
                    self._use_font("", 9)
                    self.set_text_color(150, 150, 150)
                    self._mc(0, 6, f"[Image not found: {display_label}]")
                self.set_text_color(51, 51, 51)
                self.ln(3)

        return toc_entries


_HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{{TITLE}}</title>
<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Microsoft YaHei',
               Roboto, 'Helvetica Neue', Arial, sans-serif;
  line-height: 1.6;
  color: #333;
  background: #f8f9fa;
}
.container { display: flex; min-height: 100vh; }
.sidebar {
  width: 260px;
  background: #2c3e50;
  color: #ecf0f1;
  padding: 24px 16px;
  position: fixed;
  top: 0; left: 0; bottom: 0;
  overflow-y: auto;
}
.sidebar h3 {
  font-size: 13px;
  text-transform: uppercase;
  letter-spacing: 1.5px;
  margin-bottom: 16px;
  padding-bottom: 10px;
  border-bottom: 1px solid rgba(255,255,255,0.15);
  color: #95a5a6;
}
.toc ul { list-style: none; padding: 0; margin: 0; }
.toc ul ul { padding-left: 14px; }
.toc li { margin: 2px 0; }
.toc a {
  color: #bdc3c7;
  text-decoration: none;
  font-size: 13px;
  display: block;
  padding: 5px 10px;
  border-radius: 4px;
  transition: all 0.2s;
  line-height: 1.4;
}
.toc a:hover { background: rgba(255,255,255,0.1); color: #fff; }
.content {
  margin-left: 260px;
  padding: 48px 64px;
  max-width: calc(100% - 260px);
  width: 100%;
  background: #fff;
  min-height: 100vh;
}
h1, h2, h3, h4, h5, h6 { margin: 28px 0 12px; color: #2c3e50; scroll-margin-top: 20px; }
h1 { font-size: 2em; border-bottom: 2px solid #eee; padding-bottom: 8px; }
h2 { font-size: 1.5em; border-bottom: 1px solid #eee; padding-bottom: 6px; }
h3 { font-size: 1.25em; }
h4 { font-size: 1.1em; }
p { margin: 12px 0; }
code {
  background: #f0f0f0;
  padding: 2px 6px;
  border-radius: 3px;
  font-family: 'SFMono-Regular', Consolas, 'Liberation Mono', Menlo, monospace;
  font-size: 0.9em;
}
pre {
  background: #282c34;
  color: #abb2bf;
  padding: 16px 20px;
  border-radius: 6px;
  overflow-x: auto;
  margin: 16px 0;
  line-height: 1.5;
}
pre code { background: none; padding: 0; color: inherit; font-size: 0.85em; }
table { border-collapse: collapse; width: 100%; margin: 16px 0; }
th, td { border: 1px solid #ddd; padding: 10px 14px; text-align: left; }
th { background: #f5f5f5; font-weight: 600; }
tr:nth-child(even) { background: #fafafa; }
blockquote {
  border-left: 4px solid #3498db;
  margin: 16px 0;
  padding: 10px 20px;
  background: #f9f9f9;
  color: #555;
}
img { max-width: 100%; border-radius: 4px; }
a { color: #3498db; text-decoration: none; }
a:hover { text-decoration: underline; }
ul, ol { margin: 12px 0; padding-left: 28px; }
li { margin: 4px 0; }
hr { border: none; border-top: 1px solid #eee; margin: 28px 0; }
</style>
</head>
<body>
<div class="container">
  <nav class="sidebar">
    <h3>Navigation</h3>
    {{TOC}}
  </nav>
  <main class="content">
    {{BODY}}
  </main>
</div>
</body>
</html>"""


@router.post("/export/html")
async def export_html(req: ExportRequest):
    normalized = _validate_export_path(req.path, ".html")
    try:
        body, toc = _convert_md(req.content)
        title = html_module.escape(_extract_title(req.content))
        full_html = (
            _HTML_TEMPLATE
            .replace("{{TITLE}}", title)
            .replace("{{TOC}}", toc)
            .replace("{{BODY}}", body)
        )
        dir_path = os.path.dirname(normalized)
        if dir_path:
            os.makedirs(dir_path, exist_ok=True)
        with open(normalized, "w", encoding="utf-8") as f:
            f.write(full_html)
        return {"status": "ok", "path": normalized}
    except PermissionError:
        raise HTTPException(status_code=403, detail="Permission denied")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/export/pdf")
async def export_pdf(req: ExportRequest):
    normalized = _validate_export_path(req.path, ".pdf")
    try:
        title = _extract_title(req.content)
        blocks = _parse_md_blocks(req.content)
        font_path = _find_cjk_font_path()
        print(f"[DEBUG] CJK font path resolved: {font_path}")
        md_dir = os.path.dirname(os.path.normpath(req.md_path)) if req.md_path else ""

        pdf = MarkdownPDF(font_path=font_path)
        pdf.set_title(title)
        pdf.set_auto_page_break(auto=True, margin=20)
        pdf.add_page()

        toc_entries = pdf.render_blocks(blocks, md_dir=md_dir)

        dir_path = os.path.dirname(normalized)
        if dir_path:
            os.makedirs(dir_path, exist_ok=True)
        pdf.output(normalized)
        return {"status": "ok", "path": normalized}
    except PermissionError:
        raise HTTPException(status_code=403, detail="Permission denied")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
