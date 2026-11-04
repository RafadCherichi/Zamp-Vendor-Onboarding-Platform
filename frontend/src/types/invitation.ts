export type InvitationStatus = 'PENDING' | 'ACCEPTED' | 'EXPIRED' | 'REVOKED';

export interface Invitation {
  id: string;
  organisation_id: string;
  vendor_name: string;
  vendor_email: string;
  status: InvitationStatus;
  expires_at: string;
  created_at: string;
  accepted_at?: string | null;
  revoked_at?: string | null;
  custom_message?: string | null;
  demo_invitation_url?: string | null;
}

export interface InvitationCreateInput {
  vendor_name: string;
  vendor_email: string;
  days_valid: number;
  custom_message?: string;
}

export interface InvitationPublicResponse {
  is_valid: boolean;
  status: InvitationStatus;
  vendor_name: string;
  vendor_email: string;
  buyer_organisation_name: string;
  expires_at: string;
  message?: string | null;
}
