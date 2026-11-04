import time
import secrets
from typing import Dict, Any, Optional
from app.services.verification.base import (
    BaseVerificationAdapter,
    VerificationResult,
    VerificationStatus,
)


def mask_id(val: str) -> str:
    if not val:
        return ""
    clean = val.strip()
    if len(clean) <= 4:
        return "****"
    if len(clean) == 10:  # PAN
        return clean[:2] + "*****" + clean[-2:]
    if len(clean) == 15:  # GSTIN
        return clean[:2] + "******" + clean[-4:]
    return ("*" * (len(clean) - 4)) + clean[-4:]


class SimulatedPanAdapter(BaseVerificationAdapter):
    @property
    def verification_type(self) -> str:
        return "PAN"

    @property
    def provider_name(self) -> str:
        return "Income Tax Department (NSDL/ITD Simulated Sandbox)"

    def verify(self, identifier: str, context: Optional[Dict[str, Any]] = None) -> VerificationResult:
        start = time.time()
        clean_pan = (identifier or "").strip().upper()
        req_id = f"REQ-PAN-{secrets.token_hex(4).upper()}"

        # Test case: Service Unavailable
        if "TIMEOUT" in clean_pan or "UNAVAILABLE" in clean_pan:
            return VerificationResult(
                verification_type=self.verification_type,
                provider_name=self.provider_name,
                request_id=req_id,
                submitted_identifier=mask_id(clean_pan),
                status=VerificationStatus.UNAVAILABLE,
                is_simulated=True,
                returned_attributes={},
                reason="Simulated provider connection timeout (HTTP 504 Gateway Timeout). External registry unreachable.",
                duration_ms=int((time.time() - start) * 1000) + 120,
            )

        # Test case: Failed / Inactive
        if "FAIL" in clean_pan:
            return VerificationResult(
                verification_type=self.verification_type,
                provider_name=self.provider_name,
                request_id=req_id,
                submitted_identifier=mask_id(clean_pan),
                status=VerificationStatus.FAILED,
                is_simulated=True,
                returned_attributes={"pan_status": "INOPERATIVE_OR_DELETED"},
                reason="PAN not found in Income Tax Department master database or marked inoperative.",
                duration_ms=int((time.time() - start) * 1000) + 45,
            )

        # Seeded PAN records
        known_records = {
            "AAPFU0938L": {
                "registered_name": "VIKRAM MALHOTRA",
                "pan_type": "Individual / Proprietor",
                "status": "VALID_AND_ACTIVE",
                "aadhaar_seeding_status": "LINKED",
            },
            "AAACZ1234K": {
                "registered_name": "ZENITH CLOUD SYSTEMS PRIVATE LIMITED",
                "pan_type": "Company",
                "status": "VALID_AND_ACTIVE",
                "aadhaar_seeding_status": "NOT_APPLICABLE",
            },
        }

        rec = known_records.get(clean_pan)
        if rec:
            return VerificationResult(
                verification_type=self.verification_type,
                provider_name=self.provider_name,
                request_id=req_id,
                submitted_identifier=mask_id(clean_pan),
                status=VerificationStatus.VERIFIED,
                is_simulated=True,
                returned_attributes=rec,
                reason="PAN confirmed active in Income Tax Department master registry.",
                duration_ms=int((time.time() - start) * 1000) + 35,
            )

        # Generic valid PAN format fallback for synthetic testing
        if len(clean_pan) == 10 and clean_pan[3] in "PCHFATBLJG":
            reg_name = "REGISTERED ENTITY"
            if context:
                reg_name = context.get("legal_name") or context.get("declared_name") or "REGISTERED ENTITY"
            return VerificationResult(
                verification_type=self.verification_type,
                provider_name=self.provider_name,
                request_id=req_id,
                submitted_identifier=mask_id(clean_pan),
                status=VerificationStatus.VERIFIED,
                is_simulated=True,
                returned_attributes={
                    "taxpayer_name": str(reg_name).upper(),
                    "registered_name": str(reg_name).upper(),
                    "status": "VALID_AND_ACTIVE",
                },
                reason="Synthetic PAN record verified against test registry.",
                duration_ms=int((time.time() - start) * 1000) + 40,
            )

        return VerificationResult(
            verification_type=self.verification_type,
            provider_name=self.provider_name,
            request_id=req_id,
            submitted_identifier=mask_id(clean_pan),
            status=VerificationStatus.UNVERIFIED,
            is_simulated=True,
            returned_attributes={},
            reason="Unable to verify: Malformed or unverified PAN identifier.",
            duration_ms=int((time.time() - start) * 1000) + 20,
        )


class SimulatedGstAdapter(BaseVerificationAdapter):
    @property
    def verification_type(self) -> str:
        return "GST"

    @property
    def provider_name(self) -> str:
        return "GSTN Common Portal (e-Way/GSP Direct API Sandbox)"

    def verify(self, identifier: str, context: Optional[Dict[str, Any]] = None) -> VerificationResult:
        start = time.time()
        clean_gst = (identifier or "").strip().upper()
        req_id = f"REQ-GST-{secrets.token_hex(4).upper()}"

        if "TIMEOUT" in clean_gst or "UNAVAILABLE" in clean_gst:
            return VerificationResult(
                verification_type=self.verification_type,
                provider_name=self.provider_name,
                request_id=req_id,
                submitted_identifier=mask_id(clean_gst),
                status=VerificationStatus.UNAVAILABLE,
                is_simulated=True,
                returned_attributes={},
                reason="Simulated GSTN GSP API endpoint timed out. External GST service unavailable.",
                duration_ms=int((time.time() - start) * 1000) + 150,
            )

        if "FAIL" in clean_gst:
            return VerificationResult(
                verification_type=self.verification_type,
                provider_name=self.provider_name,
                request_id=req_id,
                submitted_identifier=mask_id(clean_gst),
                status=VerificationStatus.FAILED,
                is_simulated=True,
                returned_attributes={"gstin_status": "CANCELLED_OR_INACTIVE"},
                reason="GSTIN registration has been cancelled or revoked by tax authority.",
                duration_ms=int((time.time() - start) * 1000) + 40,
            )

        known_gstins = {
            "27AAPFU0938L1ZV": {
                "legal_name": "Apex Components & Fasteners",
                "trade_name": "Apex Fasteners",
                "gstin_status": "Active",
                "constitution": "Sole Proprietorship",
                "date_of_registration": "01/07/2017",
                "principal_address": "Plot 42, Wagle Industrial Estate, Road No. 16, Thane 400604",
            },
            "29AAACZ1234K1Z5": {
                "legal_name": "Zenith Cloud Systems Private Limited",
                "trade_name": "Zenith Cloud",
                "gstin_status": "Active",
                "constitution": "Private Limited Company",
                "date_of_registration": "15/09/2020",
                "principal_address": "Level 4, Tech Park Boulevard, Whitefield, Bengaluru 560066",
            },
        }

        rec = known_gstins.get(clean_gst)
        if rec:
            return VerificationResult(
                verification_type=self.verification_type,
                provider_name=self.provider_name,
                request_id=req_id,
                submitted_identifier=mask_id(clean_gst),
                status=VerificationStatus.VERIFIED,
                is_simulated=True,
                returned_attributes=rec,
                reason="GSTIN verified active on GSTN portal with matching registration details.",
                duration_ms=int((time.time() - start) * 1000) + 50,
            )

        if len(clean_gst) == 15 and clean_gst[:2].isdigit():
            gst_name = "REGISTERED TAXPAYER"
            if context:
                gst_name = context.get("legal_name") or context.get("declared_name") or "REGISTERED TAXPAYER"
            return VerificationResult(
                verification_type=self.verification_type,
                provider_name=self.provider_name,
                request_id=req_id,
                submitted_identifier=mask_id(clean_gst),
                status=VerificationStatus.VERIFIED,
                is_simulated=True,
                returned_attributes={
                    "legal_name": str(gst_name),
                    "trade_name": str(gst_name),
                    "gst_status": "Active",
                    "gstin_status": "Active",
                },
                reason="Synthetic GSTIN confirmed active on sandbox gateway.",
                duration_ms=int((time.time() - start) * 1000) + 45,
            )

        return VerificationResult(
            verification_type=self.verification_type,
            provider_name=self.provider_name,
            request_id=req_id,
            submitted_identifier=mask_id(clean_gst),
            status=VerificationStatus.UNVERIFIED,
            is_simulated=True,
            returned_attributes={},
            reason="Unable to verify: GSTIN not found in GSTN database.",
            duration_ms=int((time.time() - start) * 1000) + 30,
        )


class SimulatedMcaAdapter(BaseVerificationAdapter):
    @property
    def verification_type(self) -> str:
        return "MCA"

    @property
    def provider_name(self) -> str:
        return "Ministry of Corporate Affairs (MCA21 V3 Sandbox)"

    def verify(self, identifier: str, context: Optional[Dict[str, Any]] = None) -> VerificationResult:
        start = time.time()
        clean_id = (identifier or "").strip().upper()
        req_id = f"REQ-MCA-{secrets.token_hex(4).upper()}"

        if "TIMEOUT" in clean_id or "UNAVAILABLE" in clean_id:
            return VerificationResult(
                verification_type=self.verification_type,
                provider_name=self.provider_name,
                request_id=req_id,
                submitted_identifier=mask_id(clean_id),
                status=VerificationStatus.UNAVAILABLE,
                is_simulated=True,
                returned_attributes={},
                reason="MCA21 database API connection timed out.",
                duration_ms=int((time.time() - start) * 1000) + 120,
            )

        if clean_id == "U72200KA2020PTC123456":
            return VerificationResult(
                verification_type=self.verification_type,
                provider_name=self.provider_name,
                request_id=req_id,
                submitted_identifier=mask_id(clean_id),
                status=VerificationStatus.VERIFIED,
                is_simulated=True,
                returned_attributes={
                    "company_name": "Zenith Cloud Systems Private Limited",
                    "company_status": "Active",
                    "roc": "RoC-Bangalore",
                    "class_of_company": "Private",
                    "date_of_incorporation": "15/09/2020",
                },
                reason="CIN found in RoC registry with Active status.",
                duration_ms=int((time.time() - start) * 1000) + 60,
            )

        if len(clean_id) == 21 and (clean_id.startswith("U") or clean_id.startswith("L")):
            comp_name = "REGISTERED CORPORATE ENTITY"
            if context:
                comp_name = context.get("legal_name") or context.get("declared_name") or "REGISTERED CORPORATE ENTITY"
            return VerificationResult(
                verification_type=self.verification_type,
                provider_name=self.provider_name,
                request_id=req_id,
                submitted_identifier=mask_id(clean_id),
                status=VerificationStatus.VERIFIED,
                is_simulated=True,
                returned_attributes={
                    "company_name": str(comp_name),
                    "company_status": "Active",
                    "roc": "RoC",
                    "class_of_company": "Private",
                    "date_of_incorporation": "01/01/2020",
                },
                reason="CIN found in RoC registry with Active status.",
                duration_ms=int((time.time() - start) * 1000) + 50,
            )

        return VerificationResult(
            verification_type=self.verification_type,
            provider_name=self.provider_name,
            request_id=req_id,
            submitted_identifier=mask_id(clean_id),
            status=VerificationStatus.UNVERIFIED,
            is_simulated=True,
            returned_attributes={},
            reason="CIN/LLPIN not found in MCA company master database.",
            duration_ms=int((time.time() - start) * 1000) + 40,
        )


class SimulatedUdyamAdapter(BaseVerificationAdapter):
    @property
    def verification_type(self) -> str:
        return "UDYAM"

    @property
    def provider_name(self) -> str:
        return "Ministry of MSME (Udyam Portal Verification Sandbox)"

    def verify(self, identifier: str, context: Optional[Dict[str, Any]] = None) -> VerificationResult:
        start = time.time()
        clean_udyam = (identifier or "").strip().upper()
        req_id = f"REQ-UDYAM-{secrets.token_hex(4).upper()}"

        if "TIMEOUT" in clean_udyam or "UNAVAILABLE" in clean_udyam:
            return VerificationResult(
                verification_type=self.verification_type,
                provider_name=self.provider_name,
                request_id=req_id,
                submitted_identifier=clean_udyam,
                status=VerificationStatus.UNAVAILABLE,
                is_simulated=True,
                returned_attributes={},
                reason="MSME Udyam verification service temporarily unreachable.",
                duration_ms=int((time.time() - start) * 1000) + 110,
            )

        if clean_udyam == "UDYAM-MH-02-0012345":
            return VerificationResult(
                verification_type=self.verification_type,
                provider_name=self.provider_name,
                request_id=req_id,
                submitted_identifier=clean_udyam,
                status=VerificationStatus.VERIFIED,
                is_simulated=True,
                returned_attributes={
                    "enterprise_name": "Apex Components & Fasteners",
                    "enterprise_type": "MICRO",
                    "major_activity": "MANUFACTURING",
                    "status": "ACTIVE",
                },
                reason="Udyam registration confirmed valid on Ministry of MSME portal.",
                duration_ms=int((time.time() - start) * 1000) + 45,
            )

        return VerificationResult(
            verification_type=self.verification_type,
            provider_name=self.provider_name,
            request_id=req_id,
            submitted_identifier=clean_udyam,
            status=VerificationStatus.UNVERIFIED,
            is_simulated=True,
            returned_attributes={},
            reason="Udyam registration not found on MSME portal.",
            duration_ms=int((time.time() - start) * 1000) + 30,
        )


class SimulatedBankAccountAdapter(BaseVerificationAdapter):
    @property
    def verification_type(self) -> str:
        return "BANK_ACCOUNT"

    @property
    def provider_name(self) -> str:
        return "NPCI / IMPS Penny-Drop Verification Sandbox"

    def verify(self, identifier: str, context: Optional[Dict[str, Any]] = None) -> VerificationResult:
        start = time.time()
        clean_acc = (identifier or "").strip()
        ifsc = (context.get("bank_ifsc") or "").strip().upper() if context else ""
        req_id = f"REQ-BANK-{secrets.token_hex(4).upper()}"

        if "TIMEOUT" in clean_acc or "UNAVAILABLE" in clean_acc:
            return VerificationResult(
                verification_type=self.verification_type,
                provider_name=self.provider_name,
                request_id=req_id,
                submitted_identifier=mask_id(clean_acc),
                status=VerificationStatus.UNAVAILABLE,
                is_simulated=True,
                returned_attributes={},
                reason="Banking switch / IMPS penny drop gateway timed out.",
                duration_ms=int((time.time() - start) * 1000) + 160,
            )

        if "FAIL" in clean_acc:
            return VerificationResult(
                verification_type=self.verification_type,
                provider_name=self.provider_name,
                request_id=req_id,
                submitted_identifier=mask_id(clean_acc),
                status=VerificationStatus.FAILED,
                is_simulated=True,
                returned_attributes={"imps_response_code": "R03", "reason": "Account Does Not Exist"},
                reason="Beneficiary bank rejected penny drop: Account does not exist or is blocked.",
                duration_ms=int((time.time() - start) * 1000) + 55,
            )

        known_accounts = {
            "9876543210123": {
                "registered_name": "Apex Components & Fasteners",
                "bank_name": "HDFC Bank Ltd",
                "account_status": "ACTIVE",
                "imps_response_code": "00_TRANSACTION_SUCCESSFUL",
            },
            "50200012345678": {
                "registered_name": "Zenith Cloud Systems Private Limited",
                "bank_name": "ICICI Bank",
                "account_status": "ACTIVE",
                "imps_response_code": "00_TRANSACTION_SUCCESSFUL",
            },
        }

        rec = known_accounts.get(clean_acc)
        if rec:
            return VerificationResult(
                verification_type=self.verification_type,
                provider_name=self.provider_name,
                request_id=req_id,
                submitted_identifier=mask_id(clean_acc),
                status=VerificationStatus.VERIFIED,
                is_simulated=True,
                returned_attributes=rec,
                reason="Penny drop verification successful: Account active and confirmed by beneficiary bank.",
                duration_ms=int((time.time() - start) * 1000) + 65,
            )

        # Fallback for synthetic accounts
        if len(clean_acc) >= 9 and len(clean_acc) <= 18 and clean_acc.isdigit():
            holder = "VERIFIED VENDOR"
            if context:
                holder = (
                    context.get("account_holder_name")
                    or context.get("bank_account_holder_name")
                    or context.get("legal_name")
                    or "VERIFIED VENDOR"
                )
            return VerificationResult(
                verification_type=self.verification_type,
                provider_name=self.provider_name,
                request_id=req_id,
                submitted_identifier=mask_id(clean_acc),
                status=VerificationStatus.VERIFIED,
                is_simulated=True,
                returned_attributes={
                    "registered_name": str(holder),
                    "account_status": "ACTIVE",
                    "imps_response_code": "00_TRANSACTION_SUCCESSFUL",
                },
                reason="Penny drop completed successfully on sandbox gateway.",
                duration_ms=int((time.time() - start) * 1000) + 70,
            )

        return VerificationResult(
            verification_type=self.verification_type,
            provider_name=self.provider_name,
            request_id=req_id,
            submitted_identifier=mask_id(clean_acc),
            status=VerificationStatus.UNVERIFIED,
            is_simulated=True,
            returned_attributes={},
            reason="Unable to verify bank account on IMPS network.",
            duration_ms=int((time.time() - start) * 1000) + 40,
        )
