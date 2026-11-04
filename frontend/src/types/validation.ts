export type ValidationStatus =
  | 'PASSED'
  | 'FAILED'
  | 'WARNING'
  | 'UNVERIFIED'
  | 'UNAVAILABLE'
  | 'NOT_APPLICABLE';

export type ValidationSeverity = 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW';

export type ValidationLayer =
  | 'LAYER_A_INPUT'
  | 'LAYER_B_CONSISTENCY'
  | 'LAYER_C_EXTERNAL'
  | 'LAYER_D_DUPLICATE';

export interface ValidationFinding {
  id: string;
  check_id: string;
  layer: string;
  check_name: string;
  status: ValidationStatus;
  severity: ValidationSeverity;
  source_document_id?: string | null;
  source_version_id?: string | null;
  submitted_value?: string | null;
  extracted_value?: string | null;
  external_value?: string | null;
  evidence?: string | null;
  explanation: string;
  recommended_action?: string | null;
  is_stale: boolean;
  stale_reason?: string | null;
  created_at: string;
}

export interface ValidationRun {
  id: string;
  application_id: string;
  organisation_id: string;
  run_type: string;
  status: string;
  summary?: string | null;
  passed_count: number;
  failed_count: number;
  warning_count: number;
  unverified_count: number;
  unavailable_count: number;
  is_current: boolean;
  trigger_reason?: string | null;
  created_at: string;
  findings: ValidationFinding[];
}

export interface ExternalVerificationRecord {
  id: string;
  verification_type: string;
  provider_name: string;
  request_id: string;
  submitted_identifier: string;
  status: 'VERIFIED' | 'FAILED' | 'UNVERIFIED' | 'UNAVAILABLE';
  is_simulated: boolean;
  returned_attributes?: Record<string, any>;
  reason?: string | null;
  duration_ms: number;
  created_at: string;
}

export interface DuplicateSignal {
  id: string;
  application_id: string;
  candidate_application_id: string;
  candidate_vendor_id: string;
  match_strength: 'STRONG' | 'MODERATE' | 'WEAK';
  matching_attributes: string[];
  explanation: string;
  recommended_action: string;
  is_dismissed: boolean;
  created_at: string;
}

export interface AuditEvent {
  id: string;
  event_type: string;
  entity_type: string;
  entity_id?: string | null;
  actor_role?: string | null;
  details?: Record<string, any>;
  created_at: string;
}
