export type ExceptionCategory =
  | 'MISSING_MANDATORY_DOCUMENT'
  | 'DOCUMENT_CLASSIFICATION_MISMATCH'
  | 'POOR_QUALITY_UNREADABLE'
  | 'PAN_MISMATCH'
  | 'GST_MISMATCH'
  | 'LEGAL_NAME_MISMATCH'
  | 'INVALID_IDENTIFIER_FORMAT'
  | 'BANK_DETAIL_MISMATCH'
  | 'EXTERNAL_VERIFICATION_FAILURE'
  | 'EXTERNAL_VERIFICATION_UNAVAILABLE'
  | 'POTENTIAL_DUPLICATE_VENDOR'
  | 'EXPIRED_LICENCE'
  | 'CONFLICTING_EVIDENCE'
  | 'HIGH_RISK_CHANGE';

export type ExceptionSeverity = 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW';

export type ExceptionStatus =
  | 'OPEN'
  | 'ASSIGNED'
  | 'ACTION_REQUIRED_FROM_VENDOR'
  | 'RESPONSE_SUBMITTED'
  | 'UNDER_REVIEW'
  | 'RESOLVED'
  | 'REJECTED'
  | 'ESCALATED'
  | 'CLOSED';

export type ResolutionType =
  | 'CORRECTED_BY_VENDOR'
  | 'VERIFIED_MANUALLY'
  | 'DOCUMENT_ACCEPTED_WITH_NOTE'
  | 'EXCEPTION_OVERRIDDEN'
  | 'CANCELLED_OBSOLETE';

export interface ExceptionTransition {
  id: string;
  exception_id: string;
  from_status: string;
  to_status: string;
  actor_user_id?: string;
  actor_role: string;
  reason?: string;
  notes?: string;
  created_at: string;
}

export interface ExceptionComment {
  id: string;
  exception_id: string;
  author_user_id?: string;
  author_role: string;
  is_internal: boolean;
  message: string;
  created_at: string;
}

export interface FieldCorrection {
  id: string;
  exception_id: string;
  application_id: string;
  field_name: string;
  previous_value?: string;
  new_value?: string;
  changed_by_user_id?: string;
  changed_by_role: string;
  vendor_explanation?: string;
  created_at: string;
}

export interface OnboardingException {
  id: string;
  reference_number: string;
  application_id: string;
  organisation_id: string;
  vendor_id: string;
  category: ExceptionCategory;
  title: string;
  description: string;
  severity: ExceptionSeverity;
  source_check_ids?: string[];
  source_finding_id?: string;
  related_document_id?: string;
  related_version_id?: string;
  related_field_name?: string;
  assigned_user_id?: string;
  assigned_role?: string;
  status: ExceptionStatus;
  vendor_action_instruction?: string;
  resolution_type?: ResolutionType;
  resolution_notes?: string;
  created_by_role: string;
  resolved_at?: string;
  created_at: string;
  updated_at: string;
  transitions: ExceptionTransition[];
  comments: ExceptionComment[];
  field_corrections: FieldCorrection[];
}

export interface Notification {
  id: string;
  organisation_id: string;
  recipient_user_id: string;
  title: string;
  message: string;
  notification_type: string;
  entity_type?: string;
  entity_id?: string;
  is_read: boolean;
  created_at: string;
}

export interface VendorCorrectionSubmitPayload {
  field_name?: string;
  new_field_value?: string;
  explanation?: string;
}

export interface TransitionPayload {
  target_status: ExceptionStatus;
  reason?: string;
  notes?: string;
  resolution_type?: ResolutionType;
  resolution_notes?: string;
  vendor_action_instruction?: string;
}

export interface AssignPayload {
  assigned_user_id?: string;
  assigned_role?: string;
  reason?: string;
}
