import type {
  DashboardMetrics,
  QueueResponse,
  ReviewerUser,
  ApplicationComprehensiveDetails,
} from '../types/queue';

const API_BASE = import.meta.env.VITE_API_BASE_URL || '/api';

function getAuthHeaders(token?: string): HeadersInit {
  const t = token || localStorage.getItem('vop_auth_token') || localStorage.getItem('token') || '';
  return {
    Authorization: `Bearer ${t}`,
    'Content-Type': 'application/json',
    Accept: 'application/json',
  };
}

export async function apiGetDashboardMetrics(token?: string): Promise<DashboardMetrics> {
  const res = await fetch(`${API_BASE}/applications/dashboard/metrics`, {
    headers: getAuthHeaders(token),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Failed to fetch dashboard metrics');
  }
  return res.json();
}

export async function apiQueryApplicationQueue(
  params?: {
    search?: string;
    status?: string;
    exception_severity?: string;
    exception_category?: string;
    assigned_reviewer_id?: string;
    unassigned_only?: boolean;
    ready_for_approval_only?: boolean;
    page?: number;
    page_size?: number;
    sort_by?: string;
    sort_order?: string;
  },
  token?: string
): Promise<QueueResponse> {
  const url = new URL(`${window.location.origin}${API_BASE}/applications/queue`);
  if (params?.search) url.searchParams.set('search', params.search);
  if (params?.status) url.searchParams.set('status', params.status);
  if (params?.exception_severity) url.searchParams.set('exception_severity', params.exception_severity);
  if (params?.exception_category) url.searchParams.set('exception_category', params.exception_category);
  if (params?.assigned_reviewer_id) url.searchParams.set('assigned_reviewer_id', params.assigned_reviewer_id);
  if (params?.unassigned_only) url.searchParams.set('unassigned_only', 'true');
  if (params?.ready_for_approval_only) url.searchParams.set('ready_for_approval_only', 'true');
  if (params?.page) url.searchParams.set('page', String(params.page));
  if (params?.page_size) url.searchParams.set('page_size', String(params.page_size));
  if (params?.sort_by) url.searchParams.set('sort_by', params.sort_by);
  if (params?.sort_order) url.searchParams.set('sort_order', params.sort_order);

  const res = await fetch(url.toString(), {
    headers: getAuthHeaders(token),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Failed to query application queue');
  }
  return res.json();
}

export async function apiGetOrganisationReviewers(token?: string): Promise<ReviewerUser[]> {
  const res = await fetch(`${API_BASE}/applications/reviewers`, {
    headers: getAuthHeaders(token),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Failed to fetch organisation reviewers');
  }
  return res.json();
}

export async function apiGetApplicationComprehensiveDetails(
  applicationId: string,
  token?: string
): Promise<ApplicationComprehensiveDetails> {
  const res = await fetch(`${API_BASE}/applications/${applicationId}/details`, {
    headers: getAuthHeaders(token),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Failed to fetch application details');
  }
  return res.json();
}

export async function apiAssignReviewer(
  applicationId: string,
  reviewerUserId: string | null,
  reason?: string,
  token?: string
): Promise<void> {
  const res = await fetch(`${API_BASE}/applications/${applicationId}/assign`, {
    method: 'POST',
    headers: getAuthHeaders(token),
    body: JSON.stringify({ reviewer_user_id: reviewerUserId, reason }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Failed to assign reviewer');
  }
}

export async function apiApproveApplication(
  applicationId: string,
  notes?: string,
  token?: string
): Promise<void> {
  const res = await fetch(`${API_BASE}/applications/${applicationId}/approve`, {
    method: 'POST',
    headers: getAuthHeaders(token),
    body: JSON.stringify({ notes }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    const message = err.detail?.message || err.detail || 'Failed to approve application';
    const reasons = err.detail?.reasons ? `: ${err.detail.reasons.join(', ')}` : '';
    throw new Error(`${message}${reasons}`);
  }
}

export async function apiRejectApplication(
  applicationId: string,
  reason: string,
  notes?: string,
  token?: string
): Promise<void> {
  const res = await fetch(`${API_BASE}/applications/${applicationId}/reject`, {
    method: 'POST',
    headers: getAuthHeaders(token),
    body: JSON.stringify({ reason, notes }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Failed to reject application');
  }
}

export async function apiClarifyApplication(
  applicationId: string,
  instructions: string,
  relatedExceptionId?: string,
  relatedField?: string,
  relatedDocumentId?: string,
  token?: string
): Promise<void> {
  const res = await fetch(`${API_BASE}/applications/${applicationId}/request-clarification`, {
    method: 'POST',
    headers: getAuthHeaders(token),
    body: JSON.stringify({
      instructions,
      related_exception_id: relatedExceptionId,
      related_field: relatedField,
      related_document_id: relatedDocumentId,
    }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Failed to request clarification');
  }
}

export async function apiEscalateApplication(
  applicationId: string,
  reason: string,
  targetRole: string = 'ADMIN',
  token?: string
): Promise<void> {
  const res = await fetch(`${API_BASE}/applications/${applicationId}/escalate`, {
    method: 'POST',
    headers: getAuthHeaders(token),
    body: JSON.stringify({ reason, target_role: targetRole }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Failed to escalate application');
  }
}
