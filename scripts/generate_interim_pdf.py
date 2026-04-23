from __future__ import annotations

from pathlib import Path

from reportlab.lib.pagesizes import LETTER
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas


def write_pdf(source_md: Path, target_pdf: Path) -> None:
    text = source_md.read_text(encoding="utf-8")
    lines = text.splitlines()

    c = canvas.Canvas(str(target_pdf), pagesize=LETTER)
    _, height = LETTER
    margin = 0.75 * inch
    y = height - margin

    c.setFont("Helvetica", 10)
    for raw in lines:
        line = raw if raw else " "
        if y < margin:
            c.showPage()
            c.setFont("Helvetica", 10)
            y = height - margin

        while len(line) > 110:
            chunk = line[:110]
            c.drawString(margin, y, chunk)
            y -= 14
            line = line[110:]
            if y < margin:
                c.showPage()
                c.setFont("Helvetica", 10)
                y = height - margin

        c.drawString(margin, y, line)
        y -= 14

    c.save()


if __name__ == "__main__":
    src = Path("docs/interim_report.md")
    dst = Path("deliverables/interim_report.pdf")
    write_pdf(src, dst)
    print(f"Wrote {dst}")
