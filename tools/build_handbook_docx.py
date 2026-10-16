#!/usr/bin/env python
"""Build the TwinGuard project handbook DOCX from its master Markdown.

The preferred renderer uses python-docx. A small OOXML fallback is included so
the export can still be built in restricted environments without installing a
dependency. It handles headings, paragraphs, simple Markdown tables, lists,
code blocks, a title page, a generated contents page, header/footer and page
number fields. Mermaid blocks remain readable code text unless a future
renderer with image support is available.

Run from the project root:
    .venv\\Scripts\\python.exe tools\\build_handbook_docx.py

The source Markdown and output DOCX are both under docs/handbook. The script
does not read or modify raw, processed or feature data.
"""

from __future__ import annotations

import html
import re
import sys
import zipfile
from datetime import date
from pathlib import Path
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
HANDBOOK = ROOT / "docs" / "handbook"
SOURCE = HANDBOOK / "TwinGuard_Project_Handbook.md"
OUTPUT = HANDBOOK / "TwinGuard_Project_Handbook.docx"


def plain(text: str) -> str:
    """Convert the inline Markdown used in this handbook to readable text."""
    text = re.sub(r"!\[([^\]]*)\]\([^)]*\)", r"\1", text)
    text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r"\1 (\2)", text)
    text = re.sub(r"`([^`]*)`", r"\1", text)
    text = re.sub(r"\*\*(.*?)\*\*", r"\1", text)
    text = re.sub(r"(?<!\*)\*([^*]+)\*", r"\1", text)
    return text.replace("\\|", "|").strip()


def split_table_row(line: str) -> list[str]:
    line = line.strip().strip("|")
    return [cell.strip() for cell in re.split(r"(?<!\\)\|", line)]


def mermaid_summary(lines: list[str]) -> str:
    labels = {m.group(1): plain(m.group(2)) for line in lines if (m := re.match(r"\s*(\w+)\[(.+?)\]\s*$", line))}
    edges = []
    for line in lines:
        edge = re.match(r"\s*(\w+)\s*-->\s*(\w+)\s*$", line)
        if edge:
            left, right = edge.groups()
            edges.append(f"{labels.get(left, left)} -> {labels.get(right, right)}")
    return "Architecture flow: " + "; ".join(edges) if edges else "Architecture diagram: see the surrounding text."


def render_with_python_docx(markdown: str) -> bool:
    try:
        from docx import Document
        from docx.enum.section import WD_SECTION
        from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT
        from docx.enum.text import WD_ALIGN_PARAGRAPH
        from docx.oxml import OxmlElement
        from docx.oxml.ns import qn
        from docx.shared import Inches, Pt, RGBColor
    except ImportError:
        return False

    doc = Document()
    sec = doc.sections[0]
    sec.top_margin = Inches(0.7)
    sec.bottom_margin = Inches(0.7)
    sec.left_margin = Inches(0.72)
    sec.right_margin = Inches(0.72)
    sec.header_distance = Inches(0.3)
    sec.footer_distance = Inches(0.3)

    styles = doc.styles
    styles["Normal"].font.name = "Aptos"
    styles["Normal"].font.size = Pt(9.5)
    styles["Normal"].paragraph_format.space_after = Pt(5)
    for name, size, color in (("Title", 24, "12344D"), ("Heading 1", 17, "12344D"), ("Heading 2", 13, "176B87"), ("Heading 3", 11, "176B87")):
        styles[name].font.name = "Aptos Display"
        styles[name].font.size = Pt(size)
        styles[name].font.color.rgb = RGBColor.from_string(color)
        styles[name].font.bold = True

    header = sec.header.paragraphs[0]
    header.text = "TWIN GUARD AI  |  PROJECT HANDBOOK"
    header.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    header.runs[0].font.size = Pt(8)
    header.runs[0].font.color.rgb = RGBColor(100, 110, 120)
    footer = sec.footer.paragraphs[0]
    footer.alignment = WD_ALIGN_PARAGRAPH.CENTER
    footer.add_run("TwinGuard AI  •  ")
    fld = OxmlElement("w:fldSimple")
    fld.set(qn("w:instr"), "PAGE")
    footer._p.append(fld)

    lines = markdown.splitlines()
    i = 0
    first_title = True
    while i < len(lines):
        line = lines[i]
        if line.strip() == "\\pagebreak":
            doc.add_page_break()
            i += 1
            continue
        if line.strip().startswith("```"):
            language = line.strip()[3:].strip().lower()
            block = []
            i += 1
            while i < len(lines) and not lines[i].strip().startswith("```"):
                block.append(lines[i])
                i += 1
            i += 1
            if language == "mermaid":
                doc.add_paragraph(mermaid_summary(block), style="Quote")
            else:
                for code_line in block:
                    p = doc.add_paragraph()
                    r = p.add_run(code_line)
                    r.font.name = "Consolas"
                    r.font.size = Pt(8)
            continue
        if line.startswith("|"):
            raw_rows = []
            while i < len(lines) and lines[i].startswith("|"):
                row = split_table_row(lines[i])
                if not all(re.fullmatch(r":?-{3,}:?", c.replace(" ", "")) for c in row):
                    raw_rows.append(row)
                i += 1
            if raw_rows:
                cols = max(len(row) for row in raw_rows)
                table = doc.add_table(rows=len(raw_rows), cols=cols)
                table.style = "Table Grid"
                table.autofit = True
                for ri, row in enumerate(raw_rows):
                    for ci in range(cols):
                        cell = table.cell(ri, ci)
                        cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
                        cell.text = plain(row[ci]) if ci < len(row) else ""
                        if ri == 0:
                            tcpr = cell._tc.get_or_add_tcPr()
                            shd = OxmlElement("w:shd")
                            shd.set(qn("w:fill"), "D9EAF0")
                            tcpr.append(shd)
                            for run in cell.paragraphs[0].runs:
                                run.bold = True
                        for p in cell.paragraphs:
                            for run in p.runs:
                                run.font.size = Pt(7.5)
                doc.add_paragraph()
            continue
        if not line.strip():
            i += 1
            continue
        heading = re.match(r"^(#{1,3})\s+(.*)$", line)
        if heading:
            level = len(heading.group(1))
            text = plain(heading.group(2))
            if first_title and level == 1:
                p = doc.add_paragraph(style="Title")
                p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                p.add_run(text)
                first_title = False
            else:
                doc.add_heading(text, level=level)
            i += 1
            continue
        if line.strip() == "---":
            i += 1
            continue
        if line.lstrip().startswith("> "):
            doc.add_paragraph(plain(line.lstrip()[2:]), style="Quote")
            i += 1
            continue
        bullet = re.match(r"^\s*[-*]\s+(.*)$", line)
        numbered = re.match(r"^\s*\d+[.)]\s+(.*)$", line)
        if bullet or numbered:
            item = (bullet or numbered).group(1)
            doc.add_paragraph(plain(item), style="List Bullet" if bullet else "List Number")
            i += 1
            continue
        doc.add_paragraph(plain(line))
        i += 1
    doc.core_properties.title = "TwinGuard AI Project Handbook"
    doc.core_properties.subject = "Research project handbook and current status"
    doc.core_properties.author = "TwinGuard AI project team"
    doc.save(OUTPUT)
    return True


def xml_text(text: str) -> str:
    return html.escape(text, quote=False)


def ooxml_run(text: str, *, bold: bool = False, italic: bool = False, mono: bool = False) -> str:
    props = []
    if bold:
        props.append("<w:b/>")
    if italic:
        props.append("<w:i/>")
    if mono:
        props.append('<w:rFonts w:ascii="Consolas" w:hAnsi="Consolas"/>')
        props.append('<w:sz w:val="16"/>')
    rpr = f"<w:rPr>{''.join(props)}</w:rPr>" if props else ""
    return f"<w:r>{rpr}<w:t xml:space=\"preserve\">{xml_text(text)}</w:t></w:r>"


def ooxml_para(text: str = "", style: str = "Normal", *, page_break: bool = False) -> str:
    if page_break:
        return '<w:p><w:r><w:br w:type="page"/></w:r></w:p>'
    ppr = f'<w:pPr><w:pStyle w:val="{style}"/></w:pPr>' if style else ""
    return f"<w:p>{ppr}{ooxml_run(plain(text))}</w:p>"


def ooxml_table(rows: list[list[str]]) -> str:
    if not rows:
        return ""
    ncols = max(len(row) for row in rows)
    width = max(900, 9000 // ncols)
    grid = "".join(f'<w:gridCol w:w="{width}"/>' for _ in range(ncols))
    out = [f'<w:tbl><w:tblPr><w:tblStyle w:val="TableGrid"/><w:tblW w:w="0" w:type="auto"/><w:tblBorders><w:top w:val="single" w:sz="4" w:color="AAB7C4"/><w:left w:val="single" w:sz="4" w:color="AAB7C4"/><w:bottom w:val="single" w:sz="4" w:color="AAB7C4"/><w:right w:val="single" w:sz="4" w:color="AAB7C4"/><w:insideH w:val="single" w:sz="4" w:color="D3DCE3"/><w:insideV w:val="single" w:sz="4" w:color="D3DCE3"/></w:tblBorders></w:tblPr><w:tblGrid>{grid}</w:tblGrid>']
    for ri, row in enumerate(rows):
        out.append("<w:tr>")
        if ri == 0:
            out.append('<w:trPr><w:tblHeader/></w:trPr>')
        for ci in range(ncols):
            text = plain(row[ci]) if ci < len(row) else ""
            shade = '<w:shd w:fill="D9EAF0"/>' if ri == 0 else ""
            run = ooxml_run(text, bold=(ri == 0))
            out.append(f'<w:tc><w:tcPr><w:tcW w:w="{width}" w:type="dxa"/>{shade}<w:vAlign w:val="center"/></w:tcPr><w:p><w:pPr><w:spacing w:after="60"/></w:pPr>{run}</w:p></w:tc>')
        out.append("</w:tr>")
    out.append("</w:tbl>")
    return "".join(out)


def render_fallback(markdown: str) -> None:
    """Create a standards-based DOCX using only Python's standard library."""
    lines = markdown.splitlines()
    body: list[str] = []
    i = 0
    first_title = True
    while i < len(lines):
        line = lines[i]
        if line.strip() == "\\pagebreak":
            body.append(ooxml_para(page_break=True))
            i += 1
            continue
        if line.strip().startswith("```"):
            language = line.strip()[3:].strip().lower()
            block = []
            i += 1
            while i < len(lines) and not lines[i].strip().startswith("```"):
                block.append(lines[i])
                i += 1
            i += 1
            if language == "mermaid":
                body.append(ooxml_para(mermaid_summary(block), "Quote"))
            else:
                for code_line in block:
                    body.append(f'<w:p><w:pPr><w:pStyle w:val="CodeBlock"/></w:pPr>{ooxml_run(code_line, mono=True)}</w:p>')
            continue
        if line.startswith("|"):
            rows = []
            while i < len(lines) and lines[i].startswith("|"):
                row = split_table_row(lines[i])
                if not all(re.fullmatch(r":?-{3,}:?", c.replace(" ", "")) for c in row):
                    rows.append(row)
                i += 1
            body.append(ooxml_table(rows))
            body.append(ooxml_para(""))
            continue
        if not line.strip() or line.strip() == "---":
            i += 1
            continue
        heading = re.match(r"^(#{1,3})\s+(.*)$", line)
        if heading:
            level = len(heading.group(1))
            text = plain(heading.group(2))
            if first_title and level == 1:
                body.append(ooxml_para(text, "Title"))
                first_title = False
            else:
                body.append(ooxml_para(text, f"Heading{level}"))
            i += 1
            continue
        if line.lstrip().startswith("> "):
            body.append(ooxml_para(line.lstrip()[2:], "Quote"))
            i += 1
            continue
        bullet = re.match(r"^\s*[-*]\s+(.*)$", line)
        numbered = re.match(r"^\s*\d+[.)]\s+(.*)$", line)
        if bullet or numbered:
            body.append(ooxml_para(("• " if bullet else "  ") + (bullet or numbered).group(1), "ListParagraph"))
            i += 1
            continue
        body.append(ooxml_para(line))
        i += 1

    body_xml = "".join(body)
    document_xml = f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"><w:body>{body_xml}<w:sectPr><w:headerReference w:type="default" r:id="rId2"/><w:footerReference w:type="default" r:id="rId3"/><w:pgSz w:w="12240" w:h="15840"/><w:pgMar w:top="1008" w:right="1037" w:bottom="1008" w:left="1037" w:header="432" w:footer="432" w:gutter="0"/></w:sectPr></w:body></w:document>'''
    styles_xml = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
<w:docDefaults><w:rPrDefault><w:rPr><w:rFonts w:ascii="Aptos" w:hAnsi="Aptos"/><w:sz w:val="19"/></w:rPr></w:rPrDefault><w:pPrDefault><w:pPr><w:spacing w:after="100" w:line="260"/></w:pPr></w:pPrDefault></w:docDefaults>
<w:style w:type="paragraph" w:default="1" w:styleId="Normal"><w:name w:val="Normal"/></w:style>
<w:style w:type="paragraph" w:styleId="Title"><w:name w:val="Title"/><w:pPr><w:jc w:val="center"/><w:spacing w:before="3000" w:after="240"/></w:pPr><w:rPr><w:rFonts w:ascii="Aptos Display" w:hAnsi="Aptos Display"/><w:b/><w:color w:val="12344D"/><w:sz w:val="48"/></w:rPr></w:style>
<w:style w:type="paragraph" w:styleId="Heading1"><w:name w:val="heading 1"/><w:basedOn w:val="Normal"/><w:pPr><w:keepNext/><w:spacing w:before="300" w:after="140"/></w:pPr><w:rPr><w:rFonts w:ascii="Aptos Display" w:hAnsi="Aptos Display"/><w:b/><w:color w:val="12344D"/><w:sz w:val="34"/></w:rPr></w:style>
<w:style w:type="paragraph" w:styleId="Heading2"><w:name w:val="heading 2"/><w:basedOn w:val="Normal"/><w:pPr><w:keepNext/><w:spacing w:before="220" w:after="100"/></w:pPr><w:rPr><w:b/><w:color w:val="176B87"/><w:sz w:val="27"/></w:rPr></w:style>
<w:style w:type="paragraph" w:styleId="Heading3"><w:name w:val="heading 3"/><w:basedOn w:val="Normal"/><w:pPr><w:keepNext/></w:pPr><w:rPr><w:b/><w:color w:val="176B87"/><w:sz w:val="23"/></w:rPr></w:style>
<w:style w:type="paragraph" w:styleId="Quote"><w:name w:val="Quote"/><w:basedOn w:val="Normal"/><w:pPr><w:ind w:left="360"/></w:pPr><w:rPr><w:i/></w:rPr></w:style>
<w:style w:type="paragraph" w:styleId="ListParagraph"><w:name w:val="List Paragraph"/><w:basedOn w:val="Normal"/></w:style>
<w:style w:type="paragraph" w:styleId="CodeBlock"><w:name w:val="Code Block"/><w:basedOn w:val="Normal"/><w:pPr><w:spacing w:after="0"/></w:pPr></w:style>
<w:style w:type="table" w:styleId="TableGrid"><w:name w:val="Table Grid"/></w:style></w:styles>'''
    header_xml = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:hdr xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:p><w:pPr><w:jc w:val="right"/></w:pPr><w:r><w:rPr><w:color w:val="64727F"/><w:sz w:val="16"/></w:rPr><w:t>TWIN GUARD AI  |  PROJECT HANDBOOK</w:t></w:r></w:p></w:hdr>'''
    footer_xml = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:ftr xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:p><w:pPr><w:jc w:val="center"/></w:pPr><w:r><w:t>TwinGuard AI  •  Page </w:t></w:r><w:fldSimple w:instr="PAGE"><w:r><w:t>1</w:t></w:r></w:fldSimple></w:p></w:ftr>'''
    rels_xml = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/><Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/header" Target="header1.xml"/><Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/footer" Target="footer1.xml"/></Relationships>'''
    root_rels = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/></Relationships>'''
    content_types = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/><Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/><Override PartName="/word/header1.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.header+xml"/><Override PartName="/word/footer1.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.footer+xml"/></Types>'''
    core = f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?><cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:dcterms="http://purl.org/dc/terms/" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"><dc:title>TwinGuard AI Project Handbook</dc:title><dc:subject>Research project handbook</dc:subject><dc:creator>TwinGuard AI project team</dc:creator><dcterms:created xsi:type="dcterms:W3CDTF">{date.today().isoformat()}T00:00:00Z</dcterms:created></cp:coreProperties>'''
    app = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties" xmlns:vt="http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes"><Application>TwinGuard Handbook Builder</Application></Properties>'''
    with zipfile.ZipFile(OUTPUT, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", content_types)
        zf.writestr("_rels/.rels", root_rels)
        zf.writestr("docProps/core.xml", core)
        zf.writestr("docProps/app.xml", app)
        zf.writestr("word/document.xml", document_xml)
        zf.writestr("word/styles.xml", styles_xml)
        zf.writestr("word/header1.xml", header_xml)
        zf.writestr("word/footer1.xml", footer_xml)
        zf.writestr("word/_rels/document.xml.rels", rels_xml)


def main() -> int:
    if not SOURCE.is_file():
        print(f"Missing handbook source: {SOURCE}", file=sys.stderr)
        return 2
    markdown = SOURCE.read_text(encoding="utf-8")
    if render_with_python_docx(markdown):
        print(f"Built with python-docx: {OUTPUT.relative_to(ROOT)}")
    else:
        render_fallback(markdown)
        print("python-docx is not installed; built DOCX with the standard-library OOXML fallback.")
        print(f"Built: {OUTPUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
