import type {
  Application,
  ApplicationDraftUpdate,
  ApplicationSubmitResponse,
  DocumentSlot,
  DocumentExtractionDetail,
  ProcessingProgress,
} from '../types/application';

const API_BASE = import.meta.env.VITE_API_BASE_URL || '/api';

export async function apiFetchCurrentApplication(token: string): Promise<Application> {
  const res = await fetch(`${API_BASE}/applications/current`, {
    headers: {
      Authorization: `Bearer ${token}`,
      Accept: 'application/json',
    },
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || 'Failed to fetch current application');
  }

  return res.json();
}

export async function apiResetOwnDraft(token: string, applicationId: string): Promise<Application> {
  const res = await fetch(`${API_BASE}/applications/${applicationId}/reset-draft`, {
    method: 'POST',
    headers: { Authorization: `Bearer ${token}`, Accept: 'application/json' },
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || 'Could not start this draft again.');
  }
  return res.json();
}

export async function apiUpdateApplicationDraft(
  token: string,
  applicationId: string,
  data: ApplicationDraftUpdate
): Promise<Application> {
  const res = await fetch(`${API_BASE}/applications/${applicationId}`, {
    method: 'PATCH',
    headers: {
      Authorization: `Bearer ${token}`,
      'Content-Type': 'application/json',
      Accept: 'application/json',
    },
    body: JSON.stringify(data),
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || 'Failed to save application draft');
  }

  return res.json();
}

export async function apiFetchChecklist(token: string, applicationId: string): Promise<DocumentSlot[]> {
  const res = await fetch(`${API_BASE}/applications/${applicationId}/checklist`, {
    headers: {
      Authorization: `Bearer ${token}`,
      Accept: 'application/json',
    },
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || 'Failed to load document checklist');
  }

  return res.json();
}

export async function apiUploadDocument(
  token: string,
  applicationId: string,
  documentType: string,
  file: File
): Promise<DocumentSlot> {
  const formData = new FormData();
  formData.append('file', file);

  const res = await fetch(`${API_BASE}/applications/${applicationId}/documents/${documentType}/upload`, {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${token}`,
      Accept: 'application/json',
    },
    body: formData,
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || 'Failed to upload document file');
  }

  return res.json();
}

export async function apiFetchProcessingProgress(
  token: string,
  applicationId: string,
  documentType: string,
  afterVersion: number
): Promise<ProcessingProgress> {
  const query = new URLSearchParams({ after_version: String(afterVersion) });
  const res = await fetch(
    `${API_BASE}/applications/${applicationId}/documents/${documentType}/processing?${query}`,
    { headers: { Authorization: `Bearer ${token}`, Accept: 'application/json' } }
  );
  if (!res.ok) throw new Error('Could not read document progress');
  return res.json();
}

export function getDocumentPreviewUrl(
  applicationId: string,
  documentId: string,
  token?: string
): string {
  const base = `${API_BASE}/applications/${applicationId}/documents/${documentId}/preview`;
  return token ? `${base}?token=${encodeURIComponent(token)}` : base;
}

export async function apiFetchDocumentExtraction(
  token: string,
  applicationId: string,
  documentId: string
): Promise<DocumentExtractionDetail> {
  const res = await fetch(`${API_BASE}/applications/${applicationId}/documents/${documentId}/extraction`, {
    headers: {
      Authorization: `Bearer ${token}`,
      Accept: 'application/json',
    },
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || 'Failed to fetch document extraction details');
  }

  return res.json();
}

export async function apiReprocessDocument(
  token: string,
  applicationId: string,
  documentId: string
): Promise<DocumentExtractionDetail> {
  const res = await fetch(`${API_BASE}/applications/${applicationId}/documents/${documentId}/reprocess`, {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${token}`,
      Accept: 'application/json',
    },
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || 'Failed to reprocess document');
  }

  return res.json();
}

export async function apiSubmitApplication(
  token: string,
  applicationId: string
): Promise<ApplicationSubmitResponse> {
  const res = await fetch(`${API_BASE}/applications/${applicationId}/submit`, {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${token}`,
      Accept: 'application/json',
    },
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    if (errorData.detail && typeof errorData.detail === 'object') {
      const msg = errorData.detail.message || 'Submission failed';
      const errors = Array.isArray(errorData.detail.errors)
        ? errorData.detail.errors
        : [];
      const err = new Error(msg) as any;
      err.errors = errors;
      throw err;
    }
    throw new Error(errorData.detail || 'Failed to submit application');
  }

  return res.json();
}

export async function apiListApplications(token: string): Promise<Application[]> {
  const res = await fetch(`${API_BASE}/applications`, {
    headers: {
      Authorization: `Bearer ${token}`,
      Accept: 'application/json',
    },
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || 'Failed to list applications');
  }

  return res.json();
}

export async function apiAcceptInvitation(
  rawToken: string,
  password: string,
  fullName?: string
): Promise<any> {
  const res = await fetch(`${API_BASE}/invitations/token/${encodeURIComponent(rawToken)}/accept`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Accept: 'application/json',
    },
    body: JSON.stringify({ password, full_name: fullName }),
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || 'Failed to accept invitation');
  }

  return res.json();
}
