from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from docx import Document

async def convert_to_file(resume: str, format_file: str):
    if format_file == "pdf":
        return await convert_to_pdf(resume)
    elif format_file == "docx":
        return await convert_to_docx(resume)
    else:
        raise ValueError("Unsupported format")


async def convert_to_pdf(text: str) -> BytesIO:
    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)

    width, height = A4
    lines = text.split("\n")
    y = height - 40

    for line in lines:
        pdf.drawString(40, y, line)
        y -= 15
        if y < 40:
            pdf.showPage()
            y = height - 40

    pdf.save()
    buffer.seek(0)
    return buffer


async def convert_to_docx(text: str) -> BytesIO:
    doc = Document()
    for line in text.split("\n"):
        doc.add_paragraph(line)

    buffer = BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer