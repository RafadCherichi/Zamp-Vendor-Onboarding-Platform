export type Constitution = 'PROPRIETORSHIP' | 'PARTNERSHIP' | 'LLP' | 'PVT_LTD' | 'PUB_LTD' | 'OTHER';

export type ApplicationStatus =
  | 'DRAFT'
  | 'IN_PROGRESS'
  | 'SUBMITTED'
  | 'UNDER_REVIEW'
  | 'ACTION_REQUIRED'
  | 'APPROVED'
  | 'REJECTED'
  | 'ESCALATED';

export type ProcessingStatus = 'QUEUED' | 'PROCESSING' | 'EXTRACTED' | 'NEEDS_REVIEW' | 'FAILED';

export interface ProcessingProgress {
  status: ProcessingStatus | 'WAITING_FOR_UPLOAD';
  stage: 'SENDING_FILE' | 'QUEUED' | 'READING_TEXT' | 'CLASSIFYING' | 'EXTRACTING_FIELDS' | 'CHECKING_RESULT' | 'COMPLETE' | 'NEEDS_REVIEW' | 'FAILED';
  message: string;
  version_number: number;
}

export interface ExtractedFieldDetail {
  id: string;
  field_name: string;
  extracted_value: string;
  normalized_value?: string | null;
  confidence_score: number;
  page_number: number;
  evidence_text?: string | null;
  extraction_method: string;
  vendor_corrected_value?: string | null;
  vendor_correction_reason?: string | null;
  vendor_corrected_by_name?: string | null;
  vendor_corrected_at?: string | null;
}

export interface DocumentExtractionDetail {
  id: string;
  document_id: string;
  document_version_id: string;
  status: ProcessingStatus;
  detected_document_type?: string | null;
  classification_confidence?: number | null;
  classification_reason?: string | null;
  is_type_match: boolean;
  page_count: number;
  provider_used: string;
  review_flags: string[];
  fields: ExtractedFieldDetail[];
  created_at: string;
}

export interface DocumentVersion {
  id: string;
  version_number: number;
  original_filename: string;
  file_size_bytes: number;
  content_type: string;
  created_at: string;
}

export interface DocumentSlot {
  id: string;
  document_type: string;
  title: string;
  is_required: boolean;
  requirement_reason?: string | null;
  status: 'PENDING' | 'UPLOADED';
  current_version?: DocumentVersion | null;
  versions_count: number;
  accepted_extensions: string[];
  max_size_mb: number;
  // Extraction & OCR Insights
  processing_status?: ProcessingStatus | null;
  detected_document_type?: string | null;
  is_type_match?: boolean | null;
  review_flags?: string[];
  extracted_fields_summary?: Record<string, string>;
}

export interface Application {
  demo_profile_id?: string | null;
  id: string;
  reference_number: string;
  organisation_id: string;
  vendor_id: string;
  status: ApplicationStatus;
  submitted_at?: string | null;
  reviewed_at?: string | null;
  rejection_reason?: string | null;
  decision_notes?: string | null;
  created_at: string;
  updated_at: string;

  // Section 1: Business Identity
  legal_name: string;
  trade_name?: string | null;
  constitution: Constitution;
  date_of_establishment?: string | null;
  registered_address?: string | null;
  operating_address?: string | null;
  city?: string | null;
  state?: string | null;
  pincode?: string | null;

  // Section 2: Tax & Registration
  pan?: string | null;
  is_gst_registered: boolean;
  gstin?: string | null;
  is_udyam_registered: boolean;
  udyam_number?: string | null;
  cin_llpin?: string | null;

  // Section 3: Authorised Contact
  contact_name?: string | null;
  contact_designation?: string | null;
  contact_email?: string | null;
  contact_mobile?: string | null;
  authorised_signatory_name?: string | null;

  // Section 4: Banking Details
  bank_account_holder_name?: string | null;
  bank_account_number?: string | null;
  bank_ifsc?: string | null;
  bank_account_type?: string | null;
  bank_name?: string | null;

  // Section 5: Business Classification
  categories: string[];
  other_business_activity_description?: string | null;

  // Section 6: Declarations & Consent
  declaration_accurate_info: boolean;
  declaration_authorised_rep: boolean;
  declaration_verification_consent: boolean;
  declaration_timestamp?: string | null;

  documents: DocumentSlot[];
}

export interface ApplicationDraftUpdate {
  legal_name?: string;
  trade_name?: string;
  constitution?: string;
  date_of_establishment?: string;
  registered_address?: string;
  operating_address?: string;
  city?: string;
  state?: string;
  pincode?: string;
  pan?: string;
  is_gst_registered?: boolean;
  gstin?: string;
  is_udyam_registered?: boolean;
  udyam_number?: string;
  cin_llpin?: string;
  contact_name?: string;
  contact_designation?: string;
  contact_email?: string;
  contact_mobile?: string;
  authorised_signatory_name?: string;
  bank_account_holder_name?: string;
  bank_account_number?: string;
  bank_ifsc?: string;
  bank_account_type?: string;
  bank_name?: string;
  categories?: string[];
  other_business_activity_description?: string;
  declaration_accurate_info?: boolean;
  declaration_authorised_rep?: boolean;
  declaration_verification_consent?: boolean;
}

export interface ApplicationSubmitResponse {
  success: boolean;
  reference_number: string;
  status: string;
  submitted_at: string;
  message: string;
}
