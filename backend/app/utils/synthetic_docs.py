import os
from pathlib import Path
from reportlab.lib.pagesizes import letter, A4
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from PIL import Image, ImageDraw, ImageFilter


def generate_synthetic_pan_pdf(dest_path: str) -> str:
    """Generates synthetic Indian PAN Card PDF with digital text."""
    Path(dest_path).parent.mkdir(parents=True, exist_ok=True)
    c = canvas.Canvas(dest_path, pagesize=(350, 220))

    # Background card border
    c.setStrokeColor(colors.HexColor("#1A365D"))
    c.setLineWidth(2)
    c.rect(10, 10, 330, 200, fill=0)

    # Header
    c.setFillColor(colors.HexColor("#0F172A"))
    c.setFont("Helvetica-Bold", 10)
    c.drawCentredString(175, 195, "INCOME TAX DEPARTMENT")
    c.setFont("Helvetica-Bold", 9)
    c.drawCentredString(175, 182, "GOVT. OF INDIA")

    # Photo & Signature placeholders
    c.setStrokeColor(colors.HexColor("#CBD5E1"))
    c.rect(20, 95, 60, 75, fill=0)
    c.setFont("Helvetica", 7)
    c.drawCentredString(50, 130, "[PHOTO]")

    # Details
    c.setFont("Helvetica", 7)
    c.drawString(95, 160, "Permanent Account Number Card")

    c.setFont("Helvetica-Bold", 8)
    c.drawString(95, 142, "Name")
    c.setFont("Helvetica", 8)
    c.drawString(95, 132, "VIKRAM MALHOTRA")

    c.setFont("Helvetica-Bold", 8)
    c.drawString(95, 118, "Father's Name")
    c.setFont("Helvetica", 8)
    c.drawString(95, 108, "RAJESH MALHOTRA")

    c.setFont("Helvetica-Bold", 8)
    c.drawString(95, 94, "Date of Birth")
    c.setFont("Helvetica", 8)
    c.drawString(95, 84, "12/04/1985")

    # PAN Number prominently
    c.setFont("Helvetica-Bold", 12)
    c.setFillColor(colors.HexColor("#1E3A8A"))
    c.drawString(95, 60, "PAN: AAPFU0938L")

    c.save()
    return dest_path


def generate_synthetic_pan_image(dest_path: str) -> str:
    """Generates synthetic Indian PAN Card PNG image for image OCR testing."""
    Path(dest_path).parent.mkdir(parents=True, exist_ok=True)
    img = Image.new("RGB", (700, 440), color=(248, 250, 252))
    draw = ImageDraw.Draw(img)

    # Border
    draw.rectangle([10, 10, 690, 430], outline=(30, 58, 138), width=3)

    # Headers
    draw.text((230, 25), "INCOME TAX DEPARTMENT", fill=(15, 23, 42))
    draw.text((280, 50), "GOVT. OF INDIA", fill=(15, 23, 42))
    draw.text((200, 80), "Permanent Account Number Card", fill=(71, 85, 105))

    # Details
    draw.text((200, 130), "Name:", fill=(15, 23, 42))
    draw.text((200, 155), "VIKRAM MALHOTRA", fill=(15, 23, 42))

    draw.text((200, 195), "Father's Name:", fill=(15, 23, 42))
    draw.text((200, 220), "RAJESH MALHOTRA", fill=(15, 23, 42))

    draw.text((200, 260), "Date of Birth: 12/04/1985", fill=(15, 23, 42))

    draw.text((200, 320), "PAN: AAPFU0938L", fill=(30, 58, 138))

    img.save(dest_path, "PNG")
    return dest_path


def generate_synthetic_gst_pdf(dest_path: str) -> str:
    """Generates synthetic Form GST REG-06 Registration Certificate."""
    Path(dest_path).parent.mkdir(parents=True, exist_ok=True)
    c = canvas.Canvas(dest_path, pagesize=A4)
    width, height = A4

    c.setFont("Helvetica-Bold", 14)
    c.drawCentredString(width / 2, height - 60, "Government of India")
    c.setFont("Helvetica-Bold", 12)
    c.drawCentredString(width / 2, height - 80, "Form GST REG-06")
    c.setFont("Helvetica", 10)
    c.drawCentredString(width / 2, height - 95, "[See Rule 10(1)]")
    c.setFont("Helvetica-Bold", 12)
    c.drawCentredString(width / 2, height - 115, "Registration Certificate")

    c.setLineWidth(1)
    c.line(50, height - 125, width - 50, height - 125)

    y = height - 160
    rows = [
        ("Registration Number (GSTIN):", "27AAPFU0938L1ZV"),
        ("Legal Name:", "Apex Components & Fasteners"),
        ("Trade Name:", "Apex Fasteners"),
        ("Constitution of Business:", "Sole Proprietorship"),
        ("Address of Principal Place of Business:", "Plot 42, Wagle Industrial Estate, Road No. 16, Thane, Maharashtra, 400604"),
        ("Date of Liability:", "01/07/2017"),
        ("Period of Validity:", "From 01/07/2017 To Regular"),
        ("Type of Registration:", "Regular"),
    ]

    for label, val in rows:
        c.setFont("Helvetica-Bold", 9)
        c.drawString(60, y, label)
        c.setFont("Helvetica", 9)
        c.drawString(240, y, val)
        y -= 30

    c.setFont("Helvetica-Oblique", 8)
    c.drawString(60, y - 40, "This is a computer generated certificate under Central Goods and Services Tax Act, 2017.")
    c.save()
    return dest_path


def generate_synthetic_bank_cheque_image(dest_path: str) -> str:
    """Generates synthetic cancelled cheque image for bank proof extraction."""
    Path(dest_path).parent.mkdir(parents=True, exist_ok=True)
    img = Image.new("RGB", (800, 380), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)

    # Cheque border & header
    draw.rectangle([10, 10, 790, 370], outline=(100, 116, 139), width=2)
    draw.text((30, 25), "HDFC BANK LTD", fill=(15, 23, 42))
    draw.text((30, 45), "Wagle Estate Branch, Thane (West) - 400604", fill=(71, 85, 105))
    draw.text((500, 25), "IFSC: HDFC0000123", fill=(15, 23, 42))

    # Pay line & details
    draw.text((40, 110), "PAY TO:", fill=(71, 85, 105))
    draw.text((120, 110), "Apex Components & Fasteners", fill=(15, 23, 42))

    draw.text((40, 160), "A/C NO:", fill=(71, 85, 105))
    draw.text((120, 160), "9876543210123", fill=(15, 23, 42))

    draw.text((520, 240), "For Apex Components & Fasteners", fill=(15, 23, 42))
    draw.text((560, 300), "Authorised Signatory", fill=(71, 85, 105))

    # Bold CANCELLED across the cheque face
    draw.line([(150, 320), (650, 60)], fill=(220, 38, 38), width=4)
    draw.line([(170, 340), (670, 80)], fill=(220, 38, 38), width=4)
    draw.text((320, 180), "CANCELLED", fill=(220, 38, 38))

    img.save(dest_path, "PNG")
    return dest_path


def generate_synthetic_udyam_pdf(dest_path: str) -> str:
    """Generates synthetic Udyam MSME Registration Certificate."""
    Path(dest_path).parent.mkdir(parents=True, exist_ok=True)
    c = canvas.Canvas(dest_path, pagesize=A4)
    width, height = A4

    c.setFont("Helvetica-Bold", 13)
    c.drawCentredString(width / 2, height - 60, "Ministry of Micro, Small and Medium Enterprises")
    c.setFont("Helvetica-Bold", 12)
    c.drawCentredString(width / 2, height - 80, "UDYAM REGISTRATION CERTIFICATE")

    c.setLineWidth(1)
    c.line(50, height - 95, width - 50, height - 95)

    y = height - 130
    items = [
        ("UDYAM REGISTRATION NUMBER:", "UDYAM-MH-02-0012345"),
        ("NAME OF ENTERPRISE:", "Apex Components & Fasteners"),
        ("ORGANISATION TYPE:", "Proprietary"),
        ("MAJOR ACTIVITY:", "MANUFACTURING"),
        ("ENTERPRISE TYPE:", "MICRO"),
        ("DATE OF INCORPORATION:", "12/04/2018"),
        ("NATIONAL INDUSTRY CLASSIFICATION (NIC):", "25991 - Manufacture of fasteners and fasteners products"),
    ]

    for label, val in items:
        c.setFont("Helvetica-Bold", 9)
        c.drawString(60, y, label)
        c.setFont("Helvetica", 9)
        c.drawString(250, y, val)
        y -= 32

    c.save()
    return dest_path


def generate_synthetic_coi_pdf(dest_path: str) -> str:
    """Generates synthetic MCA Certificate of Incorporation for Company."""
    Path(dest_path).parent.mkdir(parents=True, exist_ok=True)
    c = canvas.Canvas(dest_path, pagesize=A4)
    width, height = A4

    c.setFont("Helvetica-Bold", 12)
    c.drawCentredString(width / 2, height - 60, "GOVERNMENT OF INDIA")
    c.drawCentredString(width / 2, height - 76, "MINISTRY OF CORPORATE AFFAIRS")
    c.setFont("Helvetica", 10)
    c.drawCentredString(width / 2, height - 92, "Registrar of Companies, Karnataka")
    c.setFont("Helvetica-Bold", 13)
    c.drawCentredString(width / 2, height - 120, "Certificate of Incorporation")

    c.setFont("Helvetica-Oblique", 8)
    c.drawCentredString(width / 2, height - 135, "[Pursuant to sub-section (2) of section 7 of the Companies Act, 2013]")

    c.setFont("Helvetica-Bold", 10)
    c.drawString(60, height - 170, "Corporate Identity Number (CIN): U72200KA2020PTC123456")

    body_text = (
        "I hereby certify that Zenith Cloud Systems Private Limited is incorporated on this "
        "Fifteenth day of September Two Thousand Twenty under the Companies Act, 2013 (18 of 2013) "
        "and that the company is limited by shares. Constitution: Private Limited Company."
    )
    c.setFont("Helvetica", 10)
    c.drawString(60, height - 210, body_text[:80])
    c.drawString(60, height - 225, body_text[80:160])
    c.drawString(60, height - 240, body_text[160:])

    c.save()
    return dest_path


def generate_synthetic_unreadable_image(dest_path: str) -> str:
    """Generates an illegible noisy blurred image to test NEEDS_REVIEW / FAILED state."""
    Path(dest_path).parent.mkdir(parents=True, exist_ok=True)
    import random
    img = Image.new("RGB", (400, 300), color=(200, 200, 200))
    pixels = img.load()
    for x in range(400):
        for y in range(300):
            val = random.randint(180, 220)
            pixels[x, y] = (val, val, val)

    # Blur heavily so zero text is recognizable
    img = img.filter(ImageFilter.GaussianBlur(radius=8))
    img.save(dest_path, "PNG")
    return dest_path


def generate_all_demo_documents(target_dir: str = "./demo_documents") -> dict:
    """Generates all 6 synthetic demo compliance documents."""
    out_dir = Path(target_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    paths = {
        "pan_pdf": generate_synthetic_pan_pdf(str(out_dir / "synthetic_pan_card.pdf")),
        "pan_png": generate_synthetic_pan_image(str(out_dir / "synthetic_pan_card.png")),
        "gst_pdf": generate_synthetic_gst_pdf(str(out_dir / "synthetic_gst_certificate.pdf")),
        "bank_png": generate_synthetic_bank_cheque_image(str(out_dir / "synthetic_cancelled_cheque.png")),
        "udyam_pdf": generate_synthetic_udyam_pdf(str(out_dir / "synthetic_udyam_certificate.pdf")),
        "coi_pdf": generate_synthetic_coi_pdf(str(out_dir / "synthetic_coi_certificate.pdf")),
        "unreadable_png": generate_synthetic_unreadable_image(str(out_dir / "synthetic_unreadable_noise.png")),
    }
    return paths
