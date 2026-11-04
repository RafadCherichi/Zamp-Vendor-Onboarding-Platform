import os
import random
from pathlib import Path
from reportlab.lib.pagesizes import letter, A4
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from PIL import Image, ImageDraw, ImageFilter


def generate_synthetic_pan_pdf(
    dest_path: str,
    pan: str = "AAPFU0938L",
    name: str = "VIKRAM MALHOTRA",
    father_name: str = "RAJESH MALHOTRA",
    dob: str = "12/04/1985",
) -> str:
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
    c.drawString(95, 132, name.upper())

    c.setFont("Helvetica-Bold", 8)
    c.drawString(95, 118, "Father's Name")
    c.setFont("Helvetica", 8)
    c.drawString(95, 108, father_name.upper())

    c.setFont("Helvetica-Bold", 8)
    c.drawString(95, 94, "Date of Birth / Incorporation")
    c.setFont("Helvetica", 8)
    c.drawString(95, 84, dob)

    # PAN Number prominently
    c.setFont("Helvetica-Bold", 12)
    c.setFillColor(colors.HexColor("#1E3A8A"))
    c.drawString(95, 60, f"PAN: {pan.upper()}")

    c.save()
    return dest_path


def generate_synthetic_pan_image(
    dest_path: str,
    pan: str = "AAPFU0938L",
    name: str = "VIKRAM MALHOTRA",
    dob: str = "12/04/1985",
) -> str:
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
    draw.text((200, 155), name.upper(), fill=(15, 23, 42))

    draw.text((200, 220), f"Date of Birth: {dob}", fill=(15, 23, 42))
    draw.text((200, 280), f"PAN: {pan.upper()}", fill=(30, 58, 138))

    img.save(dest_path, "PNG")
    return dest_path


def generate_synthetic_gst_pdf(
    dest_path: str,
    gstin: str = "27AAPFU0938L1ZV",
    legal_name: str = "Apex Components & Fasteners",
    trade_name: str = "Apex Fasteners",
    constitution: str = "Sole Proprietorship",
    address: str = "Plot 42, Wagle Industrial Estate, Road No. 16, Thane, Maharashtra, 400604",
) -> str:
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
        ("Registration Number (GSTIN):", gstin),
        ("Legal Name:", legal_name),
        ("Trade Name:", trade_name),
        ("Constitution of Business:", constitution),
        ("Address of Principal Place of Business:", address[:75]),
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


def generate_synthetic_bank_cheque_pdf(
    dest_path: str,
    bank_name: str = "ICICI BANK",
    account_number: str = "50200012345678",
    ifsc: str = "ICIC0000002",
    holder_name: str = "Tata Industrial Supplies Private Limited",
) -> str:
    """Generates synthetic cancelled cheque PDF with digital text for robust OCR extraction."""
    Path(dest_path).parent.mkdir(parents=True, exist_ok=True)
    c = canvas.Canvas(dest_path, pagesize=(600, 300))

    # Border
    c.setStrokeColor(colors.HexColor("#475569"))
    c.setLineWidth(1.5)
    c.rect(15, 15, 570, 270, fill=0)

    # Header
    c.setFont("Helvetica-Bold", 12)
    c.setFillColor(colors.HexColor("#0F172A"))
    c.drawString(30, 260, bank_name.upper())

    c.setFont("Helvetica", 8)
    c.drawString(30, 245, "Industrial Area Branch")
    c.setFont("Helvetica-Bold", 10)
    c.drawString(420, 260, f"IFSC: {ifsc.upper()}")

    # Details
    c.setFont("Helvetica", 9)
    c.drawString(40, 200, "PAY TO:")
    c.setFont("Helvetica-Bold", 10)
    c.drawString(100, 200, holder_name)

    c.setFont("Helvetica", 9)
    c.drawString(40, 160, "A/C NO:")
    c.setFont("Helvetica-Bold", 11)
    c.drawString(100, 160, account_number)

    c.setFont("Helvetica", 8)
    c.drawString(400, 80, f"For {holder_name}")
    c.drawString(420, 50, "Authorised Signatory")

    # CANCELLED watermark
    c.setFont("Helvetica-Bold", 24)
    c.setFillColor(colors.HexColor("#DC2626"))
    c.drawString(220, 140, "*** CANCELLED ***")

    c.save()
    return dest_path


def generate_synthetic_bank_cheque_image(
    dest_path: str,
    bank_name: str = "HDFC BANK LTD",
    account_number: str = "9876543210123",
    ifsc: str = "HDFC0000123",
    holder_name: str = "Apex Components & Fasteners",
) -> str:
    """Generates synthetic cancelled cheque image for bank proof extraction."""
    Path(dest_path).parent.mkdir(parents=True, exist_ok=True)
    img = Image.new("RGB", (800, 380), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)

    # Cheque border & header
    draw.rectangle([10, 10, 790, 370], outline=(100, 116, 139), width=2)
    draw.text((30, 25), bank_name.upper(), fill=(15, 23, 42))
    draw.text((30, 45), "Industrial Area Branch", fill=(71, 85, 105))
    draw.text((500, 25), f"IFSC: {ifsc.upper()}", fill=(15, 23, 42))

    # Pay line & details
    draw.text((40, 110), "PAY TO:", fill=(71, 85, 105))
    draw.text((120, 110), holder_name, fill=(15, 23, 42))

    draw.text((40, 160), "A/C NO:", fill=(71, 85, 105))
    draw.text((120, 160), account_number, fill=(15, 23, 42))

    draw.text((480, 240), f"For {holder_name}", fill=(15, 23, 42))
    draw.text((560, 300), "Authorised Signatory", fill=(71, 85, 105))

    # Bold CANCELLED across the cheque face
    draw.line([(150, 320), (650, 60)], fill=(220, 38, 38), width=4)
    draw.line([(170, 340), (670, 80)], fill=(220, 38, 38), width=4)
    draw.text((320, 180), "CANCELLED", fill=(220, 38, 38))

    img.save(dest_path, "PNG")
    return dest_path


def generate_synthetic_udyam_pdf(
    dest_path: str,
    udyam_number: str = "UDYAM-MH-02-0012345",
    name: str = "Apex Components & Fasteners",
    enterprise_type: str = "MICRO",
) -> str:
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
        ("UDYAM REGISTRATION NUMBER:", udyam_number),
        ("NAME OF ENTERPRISE:", name),
        ("ORGANISATION TYPE:", "Proprietary"),
        ("MAJOR ACTIVITY:", "MANUFACTURING"),
        ("ENTERPRISE TYPE:", enterprise_type),
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


def generate_synthetic_coi_pdf(
    dest_path: str,
    company_name: str = "Zenith Cloud Systems Private Limited",
    cin: str = "U72200KA2020PTC123456",
    state: str = "Karnataka",
) -> str:
    """Generates synthetic MCA Certificate of Incorporation for Company."""
    Path(dest_path).parent.mkdir(parents=True, exist_ok=True)
    c = canvas.Canvas(dest_path, pagesize=A4)
    width, height = A4

    c.setFont("Helvetica-Bold", 12)
    c.drawCentredString(width / 2, height - 60, "GOVERNMENT OF INDIA")
    c.drawCentredString(width / 2, height - 76, "MINISTRY OF CORPORATE AFFAIRS")
    c.setFont("Helvetica", 10)
    c.drawCentredString(width / 2, height - 92, f"Registrar of Companies, {state}")
    c.setFont("Helvetica-Bold", 13)
    c.drawCentredString(width / 2, height - 120, "Certificate of Incorporation")

    c.setFont("Helvetica-Oblique", 8)
    c.drawCentredString(width / 2, height - 135, "[Pursuant to sub-section (2) of section 7 of the Companies Act, 2013]")

    c.setFont("Helvetica-Bold", 10)
    c.drawString(60, height - 170, f"Corporate Identity Number (CIN): {cin}")

    body_text = (
        f"I hereby certify that {company_name} is incorporated on this "
        "Fifteenth day of September Two Thousand Twenty under the Companies Act, 2013 (18 of 2013) "
        "and that the company is limited by shares. Constitution: Private Limited Company."
    )
    c.setFont("Helvetica", 10)
    c.drawString(60, height - 210, body_text[:80])
    c.drawString(60, height - 225, body_text[80:160])
    c.drawString(60, height - 240, body_text[160:])

    c.save()
    return dest_path


def generate_synthetic_board_resolution_pdf(
    dest_path: str,
    company_name: str = "Tata Industrial Supplies Private Limited",
    signatory_name: str = "Ratan Verma",
) -> str:
    """Generates synthetic certified extract of Board Resolution authorizing signatory."""
    Path(dest_path).parent.mkdir(parents=True, exist_ok=True)
    c = canvas.Canvas(dest_path, pagesize=A4)
    width, height = A4

    c.setFont("Helvetica-Bold", 13)
    c.drawCentredString(width / 2, height - 60, company_name.upper())
    c.setFont("Helvetica", 9)
    c.drawCentredString(width / 2, height - 76, "Registered Office: Bengaluru, Karnataka")
    c.setFont("Helvetica-Bold", 11)
    c.drawCentredString(width / 2, height - 105, "CERTIFIED TRUE EXTRACT OF THE BOARD RESOLUTION")

    c.setLineWidth(1)
    c.line(50, height - 115, width - 50, height - 115)

    c.setFont("Helvetica", 10)
    p1 = f"RESOLVED THAT {signatory_name}, Director of the Company, be and is hereby authorized to sign, execute, and submit all vendor onboarding contracts, compliance declarations, and statutory documents on behalf of the Company."
    c.drawString(60, height - 150, p1[:85])
    c.drawString(60, height - 165, p1[85:])

    c.setFont("Helvetica-Bold", 10)
    c.drawString(60, height - 230, f"For {company_name}")
    c.setFont("Helvetica", 9)
    c.drawString(60, height - 270, "Authorised Director")
    c.drawString(60, height - 285, "Date: 15/09/2020")
    c.save()
    return dest_path


def generate_synthetic_unreadable_image(dest_path: str) -> str:
    """Generates an illegible noisy blurred image to test NEEDS_REVIEW / FAILED state."""
    Path(dest_path).parent.mkdir(parents=True, exist_ok=True)
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
    """Generates all synthetic demo compliance documents."""
    out_dir = Path(target_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    paths = {
        # Case 1 (Tata Industrial Supplies Private Limited)
        "pan_tata_pdf": generate_synthetic_pan_pdf(
            str(out_dir / "pan_tata.pdf"),
            pan="AAACZ1234K",
            name="Tata Industrial Supplies Private Limited",
            father_name="RATAN VERMA",
            dob="15/09/2020",
        ),
        "gst_tata_pdf": generate_synthetic_gst_pdf(
            str(out_dir / "gst_tata.pdf"),
            gstin="29AAACZ1234K1Z5",
            legal_name="Tata Industrial Supplies Private Limited",
            trade_name="Tata Supplies",
            constitution="Private Limited Company",
            address="Plot 10, Industrial Hub, Electronic City Phase 1, Bengaluru, Karnataka, 560100",
        ),
        "bank_tata_png": generate_synthetic_bank_cheque_image(
            str(out_dir / "bank_tata.png"),
            bank_name="ICICI BANK",
            account_number="50200012345678",
            ifsc="ICIC0000002",
            holder_name="Tata Industrial Supplies Private Limited",
        ),
        "bank_tata_pdf": generate_synthetic_bank_cheque_pdf(
            str(out_dir / "bank_tata.pdf"),
            bank_name="ICICI BANK",
            account_number="50200012345678",
            ifsc="ICIC0000002",
            holder_name="Tata Industrial Supplies Private Limited",
        ),
        "coi_tata_pdf": generate_synthetic_coi_pdf(
            str(out_dir / "coi_tata.pdf"),
            company_name="Tata Industrial Supplies Private Limited",
            cin="U72200KA2020PTC123456",
            state="Karnataka",
        ),
        "board_res_tata_pdf": generate_synthetic_board_resolution_pdf(
            str(out_dir / "board_resolution_tata.pdf"),
            company_name="Tata Industrial Supplies Private Limited",
            signatory_name="Ratan Verma",
        ),

        # Case 2 (Sharma Engineering Works)
        "pan_sharma_pdf": generate_synthetic_pan_pdf(
            str(out_dir / "pan_sharma.pdf"),
            pan="AAPFU0938L",
            name="RAMESH SHARMA",
            father_name="OM PRAKASH SHARMA",
            dob="12/04/1985",
        ),
        "gst_sharma_pdf": generate_synthetic_gst_pdf(
            str(out_dir / "gst_sharma.pdf"),
            gstin="27AAPFU0938L1ZV",
            legal_name="Sharma Engineering Works",
            trade_name="Sharma Engineering",
            constitution="Sole Proprietorship",
            address="Plot 42, Wagle Industrial Estate, Road No. 16, Thane, Maharashtra, 400604",
        ),
        "bank_sharma_png": generate_synthetic_bank_cheque_image(
            str(out_dir / "bank_sharma.png"),
            bank_name="HDFC BANK LTD",
            # Intended mismatch: Cheque shows 50200012345678, while form declares 9876543210123
            account_number="50200012345678",
            ifsc="HDFC0000123",
            holder_name="Sharma Engineering Works",
        ),
        "bank_sharma_pdf": generate_synthetic_bank_cheque_pdf(
            str(out_dir / "bank_sharma.pdf"),
            bank_name="HDFC BANK LTD",
            # Intended mismatch: Cheque shows 50200012345678, while form declares 9876543210123
            account_number="50200012345678",
            ifsc="HDFC0000123",
            holder_name="Sharma Engineering Works",
        ),
        "udyam_sharma_pdf": generate_synthetic_udyam_pdf(
            str(out_dir / "udyam_sharma.pdf"),
            udyam_number="UDYAM-MH-02-0012345",
            name="Sharma Engineering Works",
            enterprise_type="MICRO",
        ),

        # Default fallbacks
        "pan_pdf": generate_synthetic_pan_pdf(str(out_dir / "synthetic_pan_card.pdf")),
        "pan_png": generate_synthetic_pan_image(str(out_dir / "synthetic_pan_card.png")),
        "gst_pdf": generate_synthetic_gst_pdf(str(out_dir / "synthetic_gst_certificate.pdf")),
        "bank_pdf": generate_synthetic_bank_cheque_pdf(
            str(out_dir / "synthetic_cancelled_cheque.pdf"),
            bank_name="HDFC BANK LTD",
            account_number="9876543210123",
            ifsc="HDFC0000123",
            holder_name="Apex Components & Fasteners",
        ),
        "bank_png": generate_synthetic_bank_cheque_image(str(out_dir / "synthetic_cancelled_cheque.png")),
        "udyam_pdf": generate_synthetic_udyam_pdf(str(out_dir / "synthetic_udyam_certificate.pdf")),
        "coi_pdf": generate_synthetic_coi_pdf(str(out_dir / "synthetic_coi_certificate.pdf")),
        "unreadable_png": generate_synthetic_unreadable_image(str(out_dir / "synthetic_unreadable_noise.png")),
    }
    return paths
