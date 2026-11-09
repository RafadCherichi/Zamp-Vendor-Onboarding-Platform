export interface DashboardMetrics {
  total_applications: number;
  in_progress_count: number;
  awaiting_vendor_count: number;
  processing_count: number;
  awaiting_review_count: number;
  ready_for_approval_count: number;
  approved_count: number;
  rejected_count: number;
  escalated_count: number;
  open_exceptions_count: number;
  high_severity_exceptions_count: number;
  stale_review_count: number;
  exception_breakdown_by_category: Record<string, number>;
  exception_breakdown_by_severity: Record<string, number>;
  recent_activity: Array<{
    id: string;
    event_type: string;
    actor_role: string;
    application_id?: string;
    details: Record<string, any>;
    created_at?: string;
  }>;
  recently_submitted: Array<{
    id: string;
    reference_number: string;
    legal_name: string;
    constitution: string;
    status: string;
    submitted_at?: string;
    open_exceptions_count: number;
  }>;
}

export interface QueueItem {
  id: string;
  reference_number: string;
  legal_name: string;
  trade_name?: string;
  constitution: string;
  status: string;
  submitted_at?: string;
  created_at?: string;
  updated_at?: string;
  assigned_reviewer_id?: string;
  assigned_reviewer_name?: string;
  decision_maker_name?: string;
  open_exceptions_count: number;
  critical_exceptions_count: number;
  ready_for_approval: boolean;
  blocking_reasons?: string[];
  vendor_replied?: boolean;
  next_action: string;
}

export interface QueueResponse {
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
  items: QueueItem[];
}

export interface ReviewerUser {
  id: string;
  full_name: string;
  email: string;
  role: string;
}

export interface ApplicationComprehensiveDetails {
  overview: {
    id: string;
    reference_number: string;
    legal_name: string;
    trade_name?: string;
    constitution: string;
    status: string;
    submitted_at?: string;
    created_at?: string;
    updated_at?: string;
    assigned_reviewer_id?: string;
    assigned_reviewer_name?: string;
    assigned_at?: string;
    reviewed_by_name?: string;
    reviewed_at?: string;
    decision_notes?: string;
    rejection_reason?: string;
    is_approval_eligible: boolean;
    blocking_reasons: string[];
  };
  business_details: {
    identity: {
      legal_name: string;
      trade_name?: string;
      constitution: string;
      date_of_establishment?: string;
      registered_address?: string;
      operating_address?: string;
      city?: string;
      state?: string;
      pincode?: string;
    };
    tax_and_registrations: {
      pan?: string;
      is_gst_registered: boolean;
      gstin?: string;
      is_udyam_registered: boolean;
      udyam_number?: string;
      cin_llpin?: string;
    };
    contact: {
      contact_name?: string;
      contact_designation?: string;
      contact_email?: string;
      contact_mobile?: string;
      authorised_signatory_name?: string;
    };
    banking: {
      bank_account_holder_name?: string;
      bank_account_number?: string;
      bank_ifsc?: string;
      bank_account_type?: string;
      bank_name?: string;
    };
    classification: {
      categories: string[];
      other_business_activity_description?: string;
    };
    declarations: {
      declaration_accurate_info: boolean;
      declaration_authorised_rep: boolean;
      declaration_verification_consent: boolean;
      declaration_timestamp?: string;
    };
  };
  documents: Array<{
    id: string;
    document_type: string;
    title: string;
    is_required: boolean;
    status: string;
    current_version_id?: string;
    versions: Array<{
      id: string;
      version_number: number;
      filename: string;
      file_size: number;
      content_type: string;
      created_at?: string;
      preview_url: string;
      extraction?: {
        status: string;
        detected_document_type?: string;
        classification_confidence?: number;
        is_type_match?: boolean;
        fields: Array<{
          field_name: string;
          extracted_value?: string;
          confidence_score?: number;
          evidence_text?: string;
        }>;
      } | null;
    }>;
  }>;
  validation?: {
    id: string;
    run_type: string;
    status: string;
    summary?: string;
    passed_count: number;
    failed_count: number;
    warning_count: number;
    unverified_count: number;
    unavailable_count: number;
    created_at?: string;
    layers: Record<
      string,
      Array<{
        id: string;
        check_id: string;
        layer: string;
        check_name: string;
        status: string;
        severity: string;
        source_document_id?: string | null;
        source_version_id?: string | null;
        submitted_value?: string;
        extracted_value?: string;
        external_value?: string;
        evidence?: string;
        explanation: string;
        recommended_action?: string;
        is_stale: boolean;
        stale_reason?: string;
      }>
    >;
  } | null;
  exceptions: Array<{
    id: string;
    reference_number: string;
    category: string;
    title: string;
    description: string;
    severity: string;
    status: string;
    assigned_role?: string;
    related_field_name?: string;
    related_document_id?: string;
    vendor_action_instruction?: string;
    resolution_type?: string;
    resolution_notes?: string;
    resolved_at?: string;
    created_at?: string;
    comments: Array<{
      id: string;
      author_role: string;
      is_internal: boolean;
      message: string;
      created_at?: string;
    }>;
    field_corrections: Array<{
      id: string;
      field_name: string;
      previous_value?: string;
      new_value?: string;
      vendor_explanation?: string;
      created_at?: string;
    }>;
    transitions: Array<{
      id: string;
      from_status: string;
      to_status: string;
      actor_role: string;
      reason?: string;
      notes?: string;
      created_at?: string;
    }>;
  }>;
  external_verifications: Array<{
    id: string;
    verification_type: string;
    provider_name: string;
    request_id: string;
    submitted_identifier: string;
    status: string;
    is_simulated: boolean;
    environment_label: string;
    returned_attributes: Record<string, any>;
    reason?: string;
    duration_ms: number;
    created_at?: string;
  }>;
  activity_trail: Array<{
    id: string;
    event_type: string;
    actor_role: string;
    details: Record<string, any>;
    created_at?: string;
  }>;
}
