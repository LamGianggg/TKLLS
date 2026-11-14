# -*- coding: utf-8 -*-
r"""
CHƯƠNG TRÌNH ĐIỀU PHỐI XUẤT TOÀN BỘ 7 BÁO CÁO NGHIÊN CỨU CHUYÊN SÂU SPEC2RTL
Định dạng kép: 7 tệp Markdown (.md) và 7 tệp PDF (.pdf) chuẩn công nghiệp & học thuật
Thư mục xuất: D:\altera\13.0sp1\BTVN\Do_An_3\reports
"""

import os
import sys
import time

# Thiết lập đường dẫn môi trường
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(CURRENT_DIR)
sys.path.insert(0, CURRENT_DIR)

from report_builder import register_system_fonts
from reports_data_01_03 import build_report_01, build_report_02, build_report_03
from reports_data_04_06 import build_report_04, build_report_05, build_report_06
from reports_data_07 import build_report_07
from reports_data_master import build_report_master

try:
    import fitz  # PyMuPDF
except ImportError:
    fitz = None


def generate_all_reports(output_dir=None):
    if output_dir is None:
        output_dir = os.path.join(PROJECT_ROOT, "reports")
    os.makedirs(output_dir, exist_ok=True)

    print("=" * 80)
    print("KHỞI ĐỘNG TIẾN TRÌNH XUẤT 8 BÁO CÁO NGHIÊN CỨU SPEC2RTL & PROMPT2SILICON")
    print(f"Thư mục xuất báo cáo: {output_dir}")
    print("=" * 80)

    start_time = time.time()
    register_system_fonts()

    builders = [
        ("01", build_report_01),
        ("02", build_report_02),
        ("03", build_report_03),
        ("04", build_report_04),
        ("05", build_report_05),
        ("06", build_report_06),
        ("07", build_report_07),
        ("00", build_report_master)
    ]

    results = []

    for idx, (code, builder_fn) in enumerate(builders, 1):
        print(f"\n[{idx}/8] Đang xử lý báo cáo mã: {code} ...")
        t0 = time.time()
        doc = builder_fn()

        md_filename = f"{doc.filename_base}.md"
        pdf_filename = f"{doc.filename_base}.pdf"
        md_path = os.path.join(output_dir, md_filename)
        pdf_path = os.path.join(output_dir, pdf_filename)

        # Xuất Markdown
        doc.export_markdown(md_path)
        with open(md_path, "r", encoding="utf-8") as f:
            md_lines = len(f.readlines())
        md_size_kb = os.path.getsize(md_path) / 1024

        # Xuất PDF
        doc.export_pdf(pdf_path)
        pdf_size_kb = os.path.getsize(pdf_path) / 1024

        # Kiểm định bằng PyMuPDF nếu có
        pdf_pages = 0
        text_sample = ""
        if fitz:
            pdf_doc = fitz.open(pdf_path)
            pdf_pages = len(pdf_doc)
            if pdf_pages > 0:
                text_sample = pdf_doc[0].get_text()[:80].replace("\n", " ")
            pdf_doc.close()

        elapsed = time.time() - t0
        print(f"  -> Hoàn thành trong {elapsed:.2f}s | MD: {md_lines} dòng ({md_size_kb:.1f} KB) | PDF: {pdf_pages} trang ({pdf_size_kb:.1f} KB)")

        results.append({
            "code": code,
            "title": doc.title,
            "md_path": md_path,
            "pdf_path": pdf_path,
            "md_lines": md_lines,
            "pdf_pages": pdf_pages,
            "pdf_size_kb": pdf_size_kb,
            "sample": text_sample
        })

    total_time = time.time() - start_time
    print("\n" + "=" * 80)
    print("BẢNG TỔNG HỢP KIỂM ĐỊNH CHẤT LƯỢNG 16 TỆP BÁO CÁO (8 MD + 8 PDF)")
    print("=" * 80)
    print(f"{'Mã':<4} | {'Số Dòng MD':<10} | {'Số Trang PDF':<12} | {'Dung Lượng PDF':<14} | {'Trạng Thái':<10}")
    print("-" * 65)

    all_passed = True
    for r in results:
        passed = (r["md_lines"] >= 100) and (r["pdf_pages"] >= 2) and (r["pdf_size_kb"] > 10.0)
        status_str = "PASS [OK]" if passed else "FAIL"
        if not passed:
            all_passed = False
        print(f"{r['code']:<4} | {r['md_lines']:<10} | {r['pdf_pages']:<12} | {r['pdf_size_kb']:.1f} KB{'':<7} | {status_str:<10}")

    print("=" * 80)
    print(f"Tổng thời gian sinh 16 tệp: {total_time:.2f} giây.")
    print(f"Kết luận kiểm định toàn bộ: {'THÀNH CÔNG 100% [ALL 16 FILES PASSED]' if all_passed else 'CẦN KIỂM TRA LẠI'}")
    print("=" * 80)
    return results


if __name__ == "__main__":
    generate_all_reports()
