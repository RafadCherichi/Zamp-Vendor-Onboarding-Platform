import type {
  ValidationRun,
  ExternalVerificationRecord,
  DuplicateSignal,
  AuditEvent,
} from '../types/validation';

const API_BASE = import.meta.env.VITE_API_BASE_URL || '/api';

export async function apiFetchValidation(token: string, applicationId: string): Promise<ValidationRun> {
  const res = await fetch(`${API_BASE}/applications/${applicationId}/validation`, {
    headers: {
      Authorization: `Bearer ${token}`,
      Accept: 'application/json',
    },
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Failed to fetch application validation findings');
  }

  return res.json();
}

export async function apiTriggerValidation(
  token: string,
  applicationId: string,
  runType: string = 'FULL',
  triggerReason: string = 'User triggered validation'
): Promise<ValidationRun> {
  const res = await fetch(`${API_BASE}/applications/${applicationId}/validate`, {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${token}`,
      'Content-Type': 'application/json',
      Accept: 'application/json',
    },
    body: JSON.stringify({
      run_type: runType,
      trigger_reason: triggerReason,
    }),
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Failed to run validation');
  }

  return res.json();
}

export async function apiFetchVerifications(
  token: string,
  applicationId: string
): Promise<ExternalVerificationRecord[]> {
  const res = await fetch(`${API_BASE}/applications/${applicationId}/verifications`, {
    headers: {
      Authorization: `Bearer ${token}`,
      Accept: 'application/json',
    },
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Failed to fetch external verifications');
  }

  return res.json();
}

export async function apiFetchDuplicateSignals(
  token: string,
  applicationId: string
): Promise<DuplicateSignal[]> {
  const res = await fetch(`${API_BASE}/applications/${applicationId}/duplicates`, {
    headers: {
      Authorization: `Bearer ${token}`,
      Accept: 'application/json',
    },
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Failed to fetch duplicate signals');
  }

  return res.json();
}

export async function apiDismissDuplicateSignal(
  token: string,
  applicationId: string,
  signalId: string
): Promise<DuplicateSignal> {
  const res = await fetch(`${API_BASE}/applications/${applicationId}/duplicates/${signalId}/dismiss`, {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${token}`,
      Accept: 'application/json',
    },
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Failed to dismiss duplicate signal');
  }

  return res.json();
}

export async function apiFetchAuditTrail(
  token: string,
  applicationId: string
): Promise<AuditEvent[]> {
  const res = await fetch(`${API_BASE}/applications/${applicationId}/audit-trail`, {
    headers: {
      Authorization: `Bearer ${token}`,
      Accept: 'application/json',
    },
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Failed to fetch audit trail');
  }

  return res.json();
}
