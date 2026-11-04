import type { Invitation, InvitationCreateInput, InvitationPublicResponse } from '../types/invitation';

const API_BASE = import.meta.env.VITE_API_BASE_URL || '/api';

export async function apiListInvitations(token: string): Promise<Invitation[]> {
  const res = await fetch(`${API_BASE}/invitations`, {
    headers: {
      Authorization: `Bearer ${token}`,
      Accept: 'application/json',
    },
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || 'Failed to fetch organisation invitations');
  }

  return res.json();
}

export async function apiCreateInvitation(token: string, data: InvitationCreateInput): Promise<Invitation> {
  const res = await fetch(`${API_BASE}/invitations`, {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${token}`,
      'Content-Type': 'application/json',
      Accept: 'application/json',
    },
    body: JSON.stringify(data),
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || 'Failed to generate vendor invitation');
  }

  return res.json();
}

export async function apiRevokeInvitation(token: string, invitationId: string): Promise<Invitation> {
  const res = await fetch(`${API_BASE}/invitations/${invitationId}/revoke`, {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${token}`,
      Accept: 'application/json',
    },
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || 'Failed to revoke invitation');
  }

  return res.json();
}

export async function apiValidateInvitationToken(rawToken: string): Promise<InvitationPublicResponse> {
  const res = await fetch(`${API_BASE}/invitations/token/${encodeURIComponent(rawToken)}`, {
    headers: { Accept: 'application/json' },
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || 'Invalid or expired invitation link');
  }

  return res.json();
}
