# -*- coding: utf-8 -*-
"""
BỘ CÔNG CỤ XUẤT BÁO CÁO NGHIÊN CỨU CHUYÊN SÂU SPEC2RTL & PROMPT2SILICON
Định dạng kép: Markdown (.md) và PDF (.pdf) chuẩn công nghiệp & học thuật
Sử dụng ReportLab 4.4.4 Platypus và Windows TrueType Arial/Consolas Unicode Fonts
"""

import os
import sys
import html
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import StyleSheet1, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, KeepTogether, HRFlowable, Preformatted
)
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase.pdfmetrics import registerFontFamily

# -----------------------------------------------------------------------------
# 1. ĐĂNG KÝ HỆ THỐNG PHÔNG CHỮ UNICODE TIẾNG VIỆT
# -----------------------------------------------------------------------------
_FONTS_REGISTERED = False

def register_system_fonts():
    global _FONTS_REGISTERED
    if _FONTS_REGISTERED:
        return
    
    font_dir = r"C:\Windows\Fonts"
    arial_path = os.path.join(font_dir, "arial.ttf")
    arialbd_path = os.path.join(font_dir, "arialbd.ttf")
    ariali_path = os.path.join(font_dir, "ariali.ttf")
    consola_path = os.path.join(font_dir, "consola.ttf")
    consolab_path = os.path.join(font_dir, "consolab.ttf")

    if os.path.exists(arial_path):
        pdfmetrics.registerFont(TTFont("Arial", arial_path))
    if os.path.exists(arialbd_path):
        pdfmetrics.registerFont(TTFont("Arial-Bold", arialbd_path))
    if os.path.exists(ariali_path):
        pdfmetrics.registerFont(TTFont("Arial-Italic", ariali_path))
    
    registerFontFamily("Arial", normal="Arial", bold="Arial-Bold", italic="Arial-Italic")

    if os.path.exists(consola_path):
        pdfmetrics.registerFont(TTFont("Consolas", consola_path))
    if os.path.exists(consolab_path):
        pdfmetrics.registerFont(TTFont("Consolas-Bold", consolab_path))
        registerFontFamily("Consolas", normal="Consolas", bold="Consolas-Bold")
    else:
        registerFontFamily("Consolas", normal="Consolas", bold="Consolas")

    _FONTS_REGISTERED = True


# -----------------------------------------------------------------------------
# 2. TWO-PASS NUMBERED CANVAS (ĐÁNH SỐ TRANG "TRANG X / Y" & RUNNING HEADER)
# -----------------------------------------------------------------------------
class NumberedCanvas(canvas.Canvas):
    report_short_title = "Hệ Thống Thiết Kế Vi Mạch Spec2RTL & Prompt2Silicon"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []
        self.report_short_title = NumberedCanvas.report_short_title

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_page_decorations(self, total_pages):
        self.saveState()
        
        # Kích thước trang A4: 595.27 x 841.89 pt
        # Lề trái: 40 pt, Lề phải: 555 pt (chiều rộng in: 515 pt)
        left = 40
        right = 555
        
        # Running Header (Chỉ vẽ từ trang 2 trở đi)
        if self._pageNumber > 1:
            self.setFont("Arial", 8)
            self.setFillColor(colors.HexColor("#64748B"))
            # Trích đoạn tiêu đề ngắn ở góc trái
            short_title = getattr(self, "report_short_title", "Báo Cáo Nghiên Cứu Spec2RTL")
            if len(short_title) > 75:
                short_title = short_title[:72] + "..."
            self.drawString(left, 808, short_title)
            self.drawRightString(right, 808, "QUY TRÌNH THIẾT KẾ VI MẠCH TỰ ĐỘNG")
            
            # Đường kẻ mảnh phân cách Header
            self.setStrokeColor(colors.HexColor("#CBD5E1"))
            self.setLineWidth(0.6)
            self.line(left, 802, right, 802)

        # Running Footer (Tất cả các trang)
        self.setStrokeColor(colors.HexColor("#CBD5E1"))
        self.setLineWidth(0.6)
        self.line(left, 42, right, 42)
        
        self.setFont("Arial", 8)
        self.setFillColor(colors.HexColor("#64748B"))
        self.drawString(left, 30, "Khoa Điện Tử — Phòng Thí Nghiệm Thiết Kế Vi Mạch & Hệ Thống Nhúng")
        
        page_str = f"Trang {self._pageNumber} / {total_pages}"
        self.drawRightString(right, 30, page_str)
        
        self.restoreState()


# -----------------------------------------------------------------------------
# 3. ĐỊNH NGHĨA KIỂU DÁNG VĂN BẢN (TYPOGRAPHY & STYLESHEET)
# -----------------------------------------------------------------------------
def get_report_stylesheet():
    register_system_fonts()
    styles = StyleSheet1()

    # Màu sắc chủ đạo (Deep Navy Palette)
    NAVY = colors.HexColor("#1E3A8A")
    CYAN = colors.HexColor("#0284C7")
    TEXT_MAIN = colors.HexColor("#0F172A")
    TEXT_MUTED = colors.HexColor("#475569")

    custom_styles = {
        "DocTrack": ParagraphStyle(
            "DocTrack",
            fontName="Arial-Bold",
            fontSize=10,
            leading=13,
            textColor=CYAN,
            spaceAfter=4,
            textTransform="uppercase"
        ),
        "DocTitle": ParagraphStyle(
            "DocTitle",
            fontName="Arial-Bold",
            fontSize=18,
            leading=23,
            textColor=NAVY,
            spaceAfter=6
        ),
        "DocSubtitle": ParagraphStyle(
            "DocSubtitle",
            fontName="Arial-Italic",
            fontSize=10.5,
            leading=15,
            textColor=TEXT_MUTED,
            spaceAfter=12
        ),
        "SectionH1": ParagraphStyle(
            "SectionH1",
            fontName="Arial-Bold",
            fontSize=13.5,
            leading=18,
            textColor=NAVY,
            spaceBefore=14,
            spaceAfter=6,
            keepWithNext=True
        ),
        "SectionH2": ParagraphStyle(
            "SectionH2",
            fontName="Arial-Bold",
            fontSize=11,
            leading=15,
            textColor=CYAN,
            spaceBefore=10,
            spaceAfter=4,
            keepWithNext=True
        ),
        "SectionH3": ParagraphStyle(
            "SectionH3",
            fontName="Arial-Bold",
            fontSize=9.5,
            leading=13,
            textColor=colors.HexColor("#334155"),
            spaceBefore=7,
            spaceAfter=3,
            keepWithNext=True
        ),
        "Body": ParagraphStyle(
            "Body",
            fontName="Arial",
            fontSize=9,
            leading=13.5,
            textColor=TEXT_MAIN,
            spaceAfter=5
        ),
        "Bullet": ParagraphStyle(
            "Bullet",
            fontName="Arial",
            fontSize=9,
            leading=13,
            textColor=TEXT_MAIN,
            leftIndent=14,
            firstLineIndent=-8,
            spaceAfter=3
        ),
        "ExecBoxTitle": ParagraphStyle(
            "ExecBoxTitle",
            fontName="Arial-Bold",
            fontSize=10,
            leading=13,
            textColor=NAVY,
            spaceAfter=4
        ),
        "ExecBoxText": ParagraphStyle(
            "ExecBoxText",
            fontName="Arial",
            fontSize=8.5,
            leading=12.5,
            textColor=colors.HexColor("#1E293B")
        ),
        "CalloutTitle": ParagraphStyle(
            "CalloutTitle",
            fontName="Arial-Bold",
            fontSize=9,
            leading=12,
            textColor=NAVY,
            spaceAfter=2
        ),
        "CalloutBody": ParagraphStyle(
            "CalloutBody",
            fontName="Arial",
            fontSize=8.5,
            leading=12,
            textColor=colors.HexColor("#334155")
        ),
        "MetaLabel": ParagraphStyle(
            "MetaLabel",
            fontName="Arial-Bold",
            fontSize=8,
            leading=11,
            textColor=colors.HexColor("#475569")
        ),
        "MetaValue": ParagraphStyle(
            "MetaValue",
            fontName="Arial",
            fontSize=8,
            leading=11,
            textColor=TEXT_MAIN
        ),
        "TableHeader": ParagraphStyle(
            "TableHeader",
            fontName="Arial-Bold",
            fontSize=8,
            leading=11,
            textColor=colors.white,
            alignment=1  # Căn giữa
        ),
        "TableCell": ParagraphStyle(
            "TableCell",
            fontName="Arial",
            fontSize=7.5,
            leading=10.5,
            textColor=TEXT_MAIN
        ),
        "TableCellBold": ParagraphStyle(
            "TableCellBold",
            fontName="Arial-Bold",
            fontSize=7.5,
            leading=10.5,
            textColor=TEXT_MAIN
        ),
        "TableCellCenter": ParagraphStyle(
            "TableCellCenter",
            fontName="Arial",
            fontSize=7.5,
            leading=10.5,
            textColor=TEXT_MAIN,
            alignment=1
        ),
        "CodeText": ParagraphStyle(
            "CodeText",
            fontName="Consolas",
            fontSize=7.2,
            leading=9.2,
            textColor=colors.HexColor("#0F172A")
        ),
        "FormulaBox": ParagraphStyle(
            "FormulaBox",
            fontName="Arial-Bold",
            fontSize=9,
            leading=13,
            textColor=NAVY,
            alignment=1,
            spaceBefore=3,
            spaceAfter=3
        )
    }

    for name, s in custom_styles.items():
        styles.add(s)

    return styles


# -----------------------------------------------------------------------------
# 4. LỚP ĐỐI TƯỢNG BÁO CÁO TOÀN NĂNG (REPORT DOCUMENT MODEL)
# -----------------------------------------------------------------------------
class ReportDocument:
    def __init__(self, report_id, filename_base, track_tag, title, subtitle, metadata=None):
        self.report_id = report_id
        self.filename_base = filename_base
        self.track_tag = track_tag
        self.title = title
        self.subtitle = subtitle
        self.metadata = metadata or {}
        self.executive_summary = ""
        self.sections = []

    def set_executive_summary(self, text):
        self.executive_summary = text

    def add_section(self, title):
        sec = {"title": title, "elements": []}
        self.sections.append(sec)
        return sec

    def add_p(self, text):
        if not self.sections:
            self.add_section("Tổng Quan")
        self.sections[-1]["elements"].append(("p", text))

    def add_h2(self, text):
        if not self.sections:
            self.add_section("Tổng Quan")
        self.sections[-1]["elements"].append(("h2", text))

    def add_h3(self, text):
        if not self.sections:
            self.add_section("Tổng Quan")
        self.sections[-1]["elements"].append(("h3", text))

    def add_bullet(self, text):
        if not self.sections:
            self.add_section("Tổng Quan")
        self.sections[-1]["elements"].append(("bullet", text))

    def add_callout(self, title, text, ctype="info"):
        if not self.sections:
            self.add_section("Tổng Quan")
        self.sections[-1]["elements"].append(("callout", (title, text, ctype)))

    def add_formula(self, formula_text, label=""):
        if not self.sections:
            self.add_section("Tổng Quan")
        self.sections[-1]["elements"].append(("formula", (formula_text, label)))

    def add_table(self, headers, rows, col_widths=None):
        if not self.sections:
            self.add_section("Tổng Quan")
        self.sections[-1]["elements"].append(("table", (headers, rows, col_widths)))

    def add_code(self, code_text, lang="verilog"):
        if not self.sections:
            self.add_section("Tổng Quan")
        self.sections[-1]["elements"].append(("code", (code_text, lang)))

    # -------------------------------------------------------------------------
    # 5. XUẤT RA TỆP MARKDOWN (.md)
    # -------------------------------------------------------------------------
    def export_markdown(self, filepath):
        lines = []
        lines.append(f"# {self.track_tag}")
        lines.append(f"# {self.title}")
        lines.append(f"*{self.subtitle}*")
        lines.append("")
        
        # Metadata
        lines.append("---")
        lines.append("### Thông Tin Tài Liệu")
        for k, v in self.metadata.items():
            lines.append(f"- **{k}**: {v}")
        lines.append("---")
        lines.append("")

        # Executive Summary
        if self.executive_summary:
            lines.append("## Tóm Tắt Điều Hành (Executive Summary)")
            lines.append(f"> {self.executive_summary.strip()}")
            lines.append("")
            lines.append("---")
            lines.append("")

        # Sections
        for sec in self.sections:
            lines.append(f"## {sec['title']}")
            lines.append("")
            for etype, data in sec["elements"]:
                if etype == "p":
                    lines.append(data)
                    lines.append("")
                elif etype == "h2":
                    lines.append(f"### {data}")
                    lines.append("")
                elif etype == "h3":
                    lines.append(f"#### {data}")
                    lines.append("")
                elif etype == "bullet":
                    lines.append(f"- {data}")
                elif etype == "callout":
                    title, text, _ = data
                    lines.append(f"> **{title}**  ")
                    lines.append(f"> {text}")
                    lines.append("")
                elif etype == "formula":
                    ftext, label = data
                    if label:
                        lines.append(f"$$\n{ftext} \\tag{{{label}}}\n$$")
                    else:
                        lines.append(f"$$\n{ftext}\n$$")
                    lines.append("")
                elif etype == "table":
                    headers, rows, _ = data
                    header_line = "| " + " | ".join(headers) + " |"
                    sep_line = "| " + " | ".join(["---"] * len(headers)) + " |"
                    lines.append(header_line)
                    lines.append(sep_line)
                    for row in rows:
                        row_line = "| " + " | ".join([str(c).replace("\n", " ") for c in row]) + " |"
                        lines.append(row_line)
                    lines.append("")
                elif etype == "code":
                    code_text, lang = data
                    lines.append(f"```{lang}")
                    lines.append(code_text.strip())
                    lines.append("```")
                    lines.append("")
            lines.append("")

        os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
        return filepath

    # -------------------------------------------------------------------------
    # 6. XUẤT RA TỆP PDF (.pdf) QUA REPORTLAB PLATYPUS
    # -------------------------------------------------------------------------
    def export_pdf(self, filepath):
        styles = get_report_stylesheet()
        story = []

        # Header Banner / Title Table
        # Width khả dụng: 515 pt
        meta_rows = []
        meta_items = list(self.metadata.items())
        for i in range(0, len(meta_items), 2):
            left_item = meta_items[i]
            right_item = meta_items[i+1] if i+1 < len(meta_items) else ("", "")
            meta_rows.append([
                Paragraph(f"<b>{left_item[0]}:</b>", styles["MetaLabel"]),
                Paragraph(str(left_item[1]), styles["MetaValue"]),
                Paragraph(f"<b>{right_item[0]}:</b>", styles["MetaLabel"]),
                Paragraph(str(right_item[1]), styles["MetaValue"]),
            ])

        meta_table = Table(meta_rows, colWidths=[80, 175, 80, 180])
        meta_table.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("TOPPADDING", (0, 0), (-1, -1), 2),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ("RIGHTPADDING", (0, 0), (-1, -1), 4),
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F8FAFC")),
            ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
        ]))

        story.append(Paragraph(self.track_tag, styles["DocTrack"]))
        story.append(Paragraph(self.title, styles["DocTitle"]))
        story.append(Paragraph(self.subtitle, styles["DocSubtitle"]))
        story.append(meta_table)
        story.append(Spacer(1, 10))

        # Executive Summary Callout Box
        if self.executive_summary:
            exec_content = [
                Paragraph("TÓM TẮT ĐIỀU HÀNH & KẾT QUẢ ĐỘT PHÁ (EXECUTIVE SUMMARY)", styles["ExecBoxTitle"]),
                Spacer(1, 3),
                Paragraph(self.executive_summary, styles["ExecBoxText"])
            ]
            exec_table = Table([[exec_content]], colWidths=[515])
            exec_table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#EFF6FF")),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                ("BOX", (0, 0), (-1, -1), 0.8, colors.HexColor("#BFDBFE")),
                ("LINEBEFORE", (0, 0), (0, -1), 3.5, colors.HexColor("#1E3A8A")),
            ]))
            story.append(exec_table)
            story.append(Spacer(1, 12))

        # Build Sections
        for sec in self.sections:
            story.append(Paragraph(sec["title"], styles["SectionH1"]))
            story.append(HRFlowable(width="100%", thickness=0.8, color=colors.HexColor("#CBD5E1"), spaceAfter=8, spaceBefore=2))

            for etype, data in sec["elements"]:
                if etype == "p":
                    story.append(Paragraph(data, styles["Body"]))
                elif etype == "h2":
                    story.append(Paragraph(data, styles["SectionH2"]))
                elif etype == "h3":
                    story.append(Paragraph(data, styles["SectionH3"]))
                elif etype == "bullet":
                    story.append(Paragraph(f"&bull;&nbsp;&nbsp;{data}", styles["Bullet"]))
                elif etype == "callout":
                    ctitle, ctext, ctype = data
                    bg_col = colors.HexColor("#EFF6FF")
                    bar_col = colors.HexColor("#1E3A8A")
                    box_col = colors.HexColor("#BFDBFE")
                    if ctype == "warning":
                        bg_col = colors.HexColor("#FEF2F2")
                        bar_col = colors.HexColor("#DC2626")
                        box_col = colors.HexColor("#FECACA")
                    elif ctype == "success":
                        bg_col = colors.HexColor("#F0FDF4")
                        bar_col = colors.HexColor("#16A34A")
                        box_col = colors.HexColor("#BBF7D0")

                    callout_cell = [
                        Paragraph(ctitle, styles["CalloutTitle"]),
                        Spacer(1, 2),
                        Paragraph(ctext, styles["CalloutBody"])
                    ]
                    c_table = Table([[callout_cell]], colWidths=[515])
                    c_table.setStyle(TableStyle([
                        ("BACKGROUND", (0, 0), (-1, -1), bg_col),
                        ("BOX", (0, 0), (-1, -1), 0.5, box_col),
                        ("LINEBEFORE", (0, 0), (0, -1), 3, bar_col),
                        ("LEFTPADDING", (0, 0), (-1, -1), 8),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                        ("TOPPADDING", (0, 0), (-1, -1), 5),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                    ]))
                    story.append(Spacer(1, 3))
                    story.append(c_table)
                    story.append(Spacer(1, 5))
                elif etype == "formula":
                    ftext, label = data
                    lbl_str = f"&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<b>({label})</b>" if label else ""
                    f_content = Paragraph(f"<i>{html.escape(ftext)}</i>{lbl_str}", styles["FormulaBox"])
                    f_table = Table([[f_content]], colWidths=[515])
                    f_table.setStyle(TableStyle([
                        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F8FAFC")),
                        ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
                        ("TOPPADDING", (0, 0), (-1, -1), 4),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                    ]))
                    story.append(Spacer(1, 3))
                    story.append(f_table)
                    story.append(Spacer(1, 5))
                elif etype == "table":
                    headers, rows, col_widths = data
                    # Chuyển đổi thành Paragraph cell
                    table_data = []
                    header_cells = [Paragraph(h, styles["TableHeader"]) for h in headers]
                    table_data.append(header_cells)
                    for r_idx, row in enumerate(rows):
                        row_cells = []
                        for c_idx, cell in enumerate(row):
                            style_use = styles["TableCellBold"] if c_idx == 0 else styles["TableCell"]
                            row_cells.append(Paragraph(str(cell), style_use))
                        table_data.append(row_cells)

                    # Phân bổ chiều rộng nếu None
                    if not col_widths:
                        num_cols = len(headers)
                        w = 515.0 / num_cols
                        col_widths = [w] * num_cols

                    t = Table(table_data, colWidths=col_widths, repeatRows=1)
                    t_style = [
                        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1E3A8A")),
                        ("ALIGN", (0, 0), (-1, 0), "CENTER"),
                        ("VALIGN", (0, 0), (-1, -1), "TOP"),
                        ("TOPPADDING", (0, 0), (-1, -1), 3),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                        ("LEFTPADDING", (0, 0), (-1, -1), 4),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
                    ]
                    # Màu xen kẽ
                    for r_idx in range(1, len(table_data)):
                        bg = colors.HexColor("#FFFFFF") if r_idx % 2 == 1 else colors.HexColor("#F8FAFC")
                        t_style.append(("BACKGROUND", (0, r_idx), (-1, r_idx), bg))

                    t.setStyle(TableStyle(t_style))
                    story.append(Spacer(1, 4))
                    story.append(t)
                    story.append(Spacer(1, 6))
                elif etype == "code":
                    code_text, lang = data
                    # Bao bọc trong bảng màu xám
                    p_code = Preformatted(code_text.strip(), styles["CodeText"])
                    code_table = Table([[p_code]], colWidths=[515])
                    code_table.setStyle(TableStyle([
                        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F8FAFC")),
                        ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
                        ("TOPPADDING", (0, 0), (-1, -1), 4),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                        ("LEFTPADDING", (0, 0), (-1, -1), 6),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                    ]))
                    story.append(Spacer(1, 3))
                    story.append(code_table)
                    story.append(Spacer(1, 5))

        # Build Document
        os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)
        doc = SimpleDocTemplate(
            filepath,
            pagesize=A4,
            leftMargin=40,
            rightMargin=40,
            topMargin=46,
            bottomMargin=48
        )
        
        # Set short title on Canvas
        NumberedCanvas.report_short_title = f"{self.report_id}: {self.title[:65]}"
        doc.build(story, canvasmaker=NumberedCanvas)
        return filepath
