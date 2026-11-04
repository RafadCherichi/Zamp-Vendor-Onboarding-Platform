import io
import logging
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
import pypdf
from PIL import Image, ImageOps
import numpy as np

logger = logging.getLogger(__name__)

# Singleton RapidOCR engine for in-process OCR tasks
_ocr_engine = None


def get_ocr_engine():
    global _ocr_engine
    if _ocr_engine is None:
        try:
            from rapidocr_onnxruntime import RapidOCR
            # Initialize with default English/Latin model
            _ocr_engine = RapidOCR()
            logger.info("RapidOCR engine initialized successfully.")
        except Exception as e:
            logger.error(f"Failed to initialize RapidOCR: {e}")
            _ocr_engine = None
    return _ocr_engine


@dataclass
class OcrLine:
    text: str
    confidence: float
    box: Optional[List[List[float]]] = None


@dataclass
class PageOcrResult:
    page_number: int
    text: str
    lines: List[OcrLine] = field(default_factory=list)
    has_selectable_text: bool = False
    confidence: float = 1.0


@dataclass
class OcrResult:
    full_text: str
    pages: List[PageOcrResult]
    page_count: int
    primary_method: str  # "PDF_TEXT" or "OCR_VISION"
    average_confidence: float
    is_unreadable: bool
    error_message: Optional[str] = None


def run_rapidocr_on_image(image: Image.Image, page_num: int = 1) -> PageOcrResult:
    """Runs RapidOCR on a PIL image and returns structured PageOcrResult."""
    # Ensure standard RGB and auto-orient based on EXIF tag
    try:
        image = ImageOps.exif_transpose(image)
    except Exception:
        pass

    if image.mode != "RGB":
        image = image.convert("RGB")

    img_np = np.array(image)
    engine = get_ocr_engine()
    if engine is None:
        return PageOcrResult(
            page_number=page_num,
            text="",
            lines=[],
            has_selectable_text=False,
            confidence=0.0,
        )

    try:
        ocr_result, elapse_list = engine(img_np)
    except Exception as e:
        logger.error(f"RapidOCR execution failed on page {page_num}: {e}")
        return PageOcrResult(
            page_number=page_num,
            text="",
            lines=[],
            has_selectable_text=False,
            confidence=0.0,
        )

    lines: List[OcrLine] = []
    text_chunks: List[str] = []
    conf_scores: List[float] = []

    if ocr_result:
        for item in ocr_result:
            # item structure: [box_points, text, confidence]
            box = item[0]
            txt = str(item[1]).strip()
            conf = float(item[2])
            if txt:
                lines.append(OcrLine(text=txt, confidence=conf, box=box))
                text_chunks.append(txt)
                conf_scores.append(conf)

    full_page_text = "\n".join(text_chunks)
    avg_conf = sum(conf_scores) / len(conf_scores) if conf_scores else 0.0

    return PageOcrResult(
        page_number=page_num,
        text=full_page_text,
        lines=lines,
        has_selectable_text=False,
        confidence=round(avg_conf, 3),
    )


def extract_document_text(file_bytes: bytes, mime_type: str) -> OcrResult:
    """
    Extracts text and layout information from PDF or image documents.
    Uses selectable text for digital PDFs; uses RapidOCR for scans and images.
    """
    if not file_bytes:
        return OcrResult(
            full_text="",
            pages=[],
            page_count=0,
            primary_method="NONE",
            average_confidence=0.0,
            is_unreadable=True,
            error_message="File is empty.",
        )

    # 1. Image Document Processing (JPEG, PNG)
    if mime_type in ["image/jpeg", "image/png"]:
        try:
            image = Image.open(io.BytesIO(file_bytes))
        except Exception as e:
            return OcrResult(
                full_text="",
                pages=[],
                page_count=0,
                primary_method="OCR_VISION",
                average_confidence=0.0,
                is_unreadable=True,
                error_message=f"Corrupt or invalid image file: {str(e)}",
            )

        page_res = run_rapidocr_on_image(image, page_num=1)
        is_blank = len(page_res.text.strip()) < 5

        return OcrResult(
            full_text=page_res.text,
            pages=[page_res],
            page_count=1,
            primary_method="OCR_VISION",
            average_confidence=page_res.confidence,
            is_unreadable=is_blank,
            error_message="No readable text recognized in image" if is_blank else None,
        )

    # 2. PDF Document Processing
    if mime_type == "application/pdf":
        try:
            reader = pypdf.PdfReader(io.BytesIO(file_bytes))
        except Exception as e:
            return OcrResult(
                full_text="",
                pages=[],
                page_count=0,
                primary_method="PDF_TEXT",
                average_confidence=0.0,
                is_unreadable=True,
                error_message=f"Corrupt or unreadable PDF: {str(e)}",
            )

        page_count = len(reader.pages)
        if page_count == 0:
            return OcrResult(
                full_text="",
                pages=[],
                page_count=0,
                primary_method="PDF_TEXT",
                average_confidence=0.0,
                is_unreadable=True,
                error_message="PDF contains no pages.",
            )

        pages: List[PageOcrResult] = []
        has_any_selectable = False
        all_confidences: List[float] = []

        for idx, page in enumerate(reader.pages):
            page_num = idx + 1
            try:
                extracted = (page.extract_text() or "").strip()
            except Exception as e:
                logger.warning(f"Failed to extract digital text on PDF page {page_num}: {e}")
                extracted = ""

            # If page has substantial digital text (> 20 alphanumeric characters), use it
            clean_alnum = "".join(ch for ch in extracted if ch.isalnum())
            if len(clean_alnum) >= 20:
                has_any_selectable = True
                lines = [OcrLine(text=line.strip(), confidence=1.0) for line in extracted.split("\n") if line.strip()]
                pages.append(PageOcrResult(
                    page_number=page_num,
                    text=extracted,
                    lines=lines,
                    has_selectable_text=True,
                    confidence=1.0,
                ))
                all_confidences.append(1.0)
            else:
                # Scanned or image-only page: extract page images if available and run OCR
                page_ocr_run = False
                if hasattr(page, "images") and len(page.images) > 0:
                    for img_file in page.images:
                        try:
                            pil_img = Image.open(io.BytesIO(img_file.data))
                            img_res = run_rapidocr_on_image(pil_img, page_num=page_num)
                            if len(img_res.text.strip()) > len(extracted):
                                extracted = img_res.text
                                pages.append(img_res)
                                all_confidences.append(img_res.confidence)
                                page_ocr_run = True
                                break
                        except Exception as e:
                            logger.warning(f"Error reading embedded image on page {page_num}: {e}")

                if not page_ocr_run:
                    # Still keep what little text was extracted
                    lines = [OcrLine(text=line.strip(), confidence=0.8) for line in extracted.split("\n") if line.strip()]
                    pages.append(PageOcrResult(
                        page_number=page_num,
                        text=extracted,
                        lines=lines,
                        has_selectable_text=False,
                        confidence=0.5 if extracted else 0.0,
                    ))
                    all_confidences.append(0.5 if extracted else 0.0)

        full_text = "\n\n--- Page Break ---\n\n".join(p.text for p in pages if p.text.strip())
        avg_conf = sum(all_confidences) / len(all_confidences) if all_confidences else 0.0
        is_unreadable = len(full_text.strip()) < 5

        return OcrResult(
            full_text=full_text,
            pages=pages,
            page_count=page_count,
            primary_method="PDF_TEXT" if has_any_selectable else "OCR_VISION",
            average_confidence=round(avg_conf, 3),
            is_unreadable=is_unreadable,
            error_message="No legible text extracted from document" if is_unreadable else None,
        )

    return OcrResult(
        full_text="",
        pages=[],
        page_count=0,
        primary_method="NONE",
        average_confidence=0.0,
        is_unreadable=True,
        error_message=f"Unsupported mime type: {mime_type}",
    )
