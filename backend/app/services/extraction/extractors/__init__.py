from app.models.document import DocumentTypeEnum
from app.services.extraction.extractors.pan import extract_pan_fields
from app.services.extraction.extractors.gst import extract_gst_fields
from app.services.extraction.extractors.bank import extract_bank_fields
from app.services.extraction.extractors.udyam import extract_udyam_fields
from app.services.extraction.extractors.constitution import extract_constitution_fields
from app.services.extraction.extractors.signatory import extract_signatory_fields
from app.services.extraction.extractors.licence import extract_licence_fields

EXTRACTOR_REGISTRY = {
    DocumentTypeEnum.PAN_PROOF.value: extract_pan_fields,
    DocumentTypeEnum.GST_CERTIFICATE.value: extract_gst_fields,
    DocumentTypeEnum.BANK_PROOF.value: extract_bank_fields,
    DocumentTypeEnum.UDYAM_CERTIFICATE.value: extract_udyam_fields,
    DocumentTypeEnum.CONSTITUTION_PROOF.value: extract_constitution_fields,
    DocumentTypeEnum.SIGNATORY_PROOF.value: extract_signatory_fields,
    DocumentTypeEnum.INDUSTRY_LICENCE.value: extract_licence_fields,
}

__all__ = [
    "EXTRACTOR_REGISTRY",
    "extract_pan_fields",
    "extract_gst_fields",
    "extract_bank_fields",
    "extract_udyam_fields",
    "extract_constitution_fields",
    "extract_signatory_fields",
    "extract_licence_fields",
]
