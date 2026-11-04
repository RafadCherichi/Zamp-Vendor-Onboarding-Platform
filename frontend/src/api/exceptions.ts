import type {
  OnboardingException,
  ExceptionComment,
  VendorCorrectionSubmitPayload,
  TransitionPayload,
  AssignPayload,
} from '../types/exception';

const API_BASE = import.meta.env.VITE_API_BASE_URL || '/api';

function getAuthHeaders(token?: string): HeadersInit {
  const t = token || localStorage.getItem('vop_auth_token') || localStorage.getItem('token') || '';
  return {
    Authorization: `Bearer ${t}`,
    'Content-Type': 'application/json',
    Accept: 'application/json',
  };
}

export const exceptionsApi = {
  getExceptions: async (
    params?: {
      application_id?: string;
      status?: string;
      category?: string;
      severity?: string;
    },
    token?: string
  ): Promise<OnboardingException[]> => {
    const url = new URL(`${window.location.origin}${API_BASE}/exceptions/`);
    if (params?.application_id) url.searchParams.set('application_id', params.application_id);
    if (params?.status) url.searchParams.set('status', params.status);
    if (params?.category) url.searchParams.set('category', params.category);
    if (params?.severity) url.searchParams.set('severity', params.severity);

    const res = await fetch(url.toString(), {
      headers: getAuthHeaders(token),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'Failed to fetch exceptions');
    }
    return res.json();
  },

  getExceptionById: async (id: string, token?: string): Promise<OnboardingException> => {
    const res = await fetch(`${API_BASE}/exceptions/${id}`, {
      headers: getAuthHeaders(token),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'Failed to fetch exception');
    }
    return res.json();
  },

  syncExceptions: async (applicationId: string, token?: string): Promise<OnboardingException[]> => {
    const res = await fetch(`${API_BASE}/exceptions/sync/${applicationId}`, {
      method: 'POST',
      headers: getAuthHeaders(token),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'Failed to sync exceptions');
    }
    return res.json();
  },

  transitionException: async (
    id: string,
    payload: TransitionPayload,
    token?: string
  ): Promise<OnboardingException> => {
    const res = await fetch(`${API_BASE}/exceptions/${id}/transition`, {
      method: 'POST',
      headers: getAuthHeaders(token),
      body: JSON.stringify(payload),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'Failed to transition exception');
    }
    return res.json();
  },

  assignException: async (
    id: string,
    payload: AssignPayload,
    token?: string
  ): Promise<OnboardingException> => {
    const res = await fetch(`${API_BASE}/exceptions/${id}/assign`, {
      method: 'POST',
      headers: getAuthHeaders(token),
      body: JSON.stringify(payload),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'Failed to assign exception');
    }
    return res.json();
  },

  submitVendorCorrection: async (
    id: string,
    payload: VendorCorrectionSubmitPayload,
    token?: string
  ): Promise<OnboardingException> => {
    const res = await fetch(`${API_BASE}/exceptions/${id}/correct`, {
      method: 'POST',
      headers: getAuthHeaders(token),
      body: JSON.stringify(payload),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'Failed to submit correction');
    }
    return res.json();
  },

  addComment: async (
    id: string,
    payload: { message: string; is_internal?: boolean },
    token?: string
  ): Promise<ExceptionComment> => {
    const res = await fetch(`${API_BASE}/exceptions/${id}/comments`, {
      method: 'POST',
      headers: getAuthHeaders(token),
      body: JSON.stringify(payload),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'Failed to add comment');
    }
    return res.json();
  },

  resolveException: async (
    id: string,
    payload: {
      resolution_type: string;
      resolution_notes?: string;
    },
    token?: string
  ): Promise<OnboardingException> => {
    const res = await fetch(`${API_BASE}/exceptions/${id}/resolve`, {
      method: 'POST',
      headers: getAuthHeaders(token),
      body: JSON.stringify(payload),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'Failed to resolve exception');
    }
    return res.json();
  },
};
