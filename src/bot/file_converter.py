"""
The module allows to convert the client's text data into different file formats through a single interface.
At the moment, the two most popular resume formats are PDF and DOCX.
"""

from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from docx import Document


async def convert_to_file(resume: str, format_file: str):
    """
    Allows to convert client's text data into PDF or DOCX file formats through a single interface.

    Attributes:
        resume (str): client's resume text
        format_file (str): file format for creating resume

    Raises:
        ValueError: if unsupported format file
    """
    if format_file == "pdf":
        return await convert_to_pdf(resume)
    elif format_file == "docx":
        return await convert_to_docx(resume)
    else:
        raise ValueError("Unsupported format")


async def convert_to_pdf(text: str) -> BytesIO:
    """
    Allows to convert client's text data into PDF file

    Attributes:
        text (str): client's resume text

    Returns:
        buffer (BytesIO): PDF file stored in RAM
    """
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
    """
    Allows to convert client's text data into DOCX file

    Attributes:
        text (str): client's resume text

    Returns:
        buffer (BytesIO): DOCX file stored in RAM
    """
    doc = Document()
    for line in text.split("\n"):
        doc.add_paragraph(line)

    buffer = BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer