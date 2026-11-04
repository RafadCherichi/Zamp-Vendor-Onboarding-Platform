import type { Notification } from '../types/exception';

const API_BASE = import.meta.env.VITE_API_BASE_URL || '/api';

function getAuthHeaders(token?: string): HeadersInit {
  const t = token || localStorage.getItem('vop_auth_token') || localStorage.getItem('token') || '';
  return {
    Authorization: `Bearer ${t}`,
    'Content-Type': 'application/json',
    Accept: 'application/json',
  };
}

export const notificationsApi = {
  getMyNotifications: async (unreadOnly: boolean = false, token?: string): Promise<Notification[]> => {
    const url = new URL(`${window.location.origin}${API_BASE}/notifications/`);
    if (unreadOnly) url.searchParams.set('unread_only', 'true');

    const res = await fetch(url.toString(), {
      headers: getAuthHeaders(token),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'Failed to fetch notifications');
    }
    return res.json();
  },

  getUnreadCount: async (token?: string): Promise<number> => {
    const res = await fetch(`${API_BASE}/notifications/count`, {
      headers: getAuthHeaders(token),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'Failed to fetch unread count');
    }
    const data = await res.json();
    return data.unread_count;
  },

  markAsRead: async (notificationId: string, token?: string): Promise<Notification> => {
    const res = await fetch(`${API_BASE}/notifications/${notificationId}/read`, {
      method: 'POST',
      headers: getAuthHeaders(token),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'Failed to mark notification read');
    }
    return res.json();
  },

  markAllAsRead: async (token?: string): Promise<{ marked_read_count: number }> => {
    const res = await fetch(`${API_BASE}/notifications/read-all`, {
      method: 'POST',
      headers: getAuthHeaders(token),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'Failed to mark all notifications read');
    }
    return res.json();
  },

  dismissNotification: async (notificationId: string, token?: string): Promise<void> => {
    const res = await fetch(`${API_BASE}/notifications/${notificationId}`, {
      method: 'DELETE',
      headers: getAuthHeaders(token),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'Failed to dismiss notification');
    }
  },
};
