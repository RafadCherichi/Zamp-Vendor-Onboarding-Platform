import React, { useState, useEffect, useCallback } from 'react';
import { useAuth } from '../../context/AuthContext';
import { apiListInvitations, apiCreateInvitation, apiRevokeInvitation } from '../../api/invitations';
import { exceptionsApi } from '../../api/exceptions';
import type { Invitation, InvitationStatus } from '../../types/invitation';
import type { OnboardingException } from '../../types/exception';
import {
  Send,
  Plus,
  RefreshCw,
  Copy,
  Check,
  XCircle,
  Clock,
  CheckCircle2,
  AlertTriangle,
  ExternalLink,
  ShieldAlert,
} from 'lucide-react';

export const ProcurementDashboard: React.FC = () => {
  const { token, user } = useAuth();
  const [invitations, setInvitations] = useState<Invitation[]>([]);
  const [orgExceptions, setOrgExceptions] = useState<OnboardingException[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // New invitation modal state
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [vendorName, setVendorName] = useState('');
  const [vendorEmail, setVendorEmail] = useState('');
  const [daysValid, setDaysValid] = useState(7);
  const [customMessage, setCustomMessage] = useState('');
  const [isCreating, setIsCreating] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);
  const [createdInvite, setCreatedInvite] = useState<Invitation | null>(null);
  const [copiedToken, setCopiedToken] = useState<string | null>(null);

  const fetchInvites = useCallback(async () => {
    if (!token) return;
    setLoading(true);
    setError(null);
    try {
      const [invData, excData] = await Promise.all([
        apiListInvitations(token),
        exceptionsApi.getExceptions().catch(() => []),
      ]);
      setInvitations(invData);
      setOrgExceptions(excData);
    } catch (err: any) {
      setError(err?.message || 'Failed to load invitations.');
    } finally {
      setLoading(false);
    }
  }, [token]);

  useEffect(() => {
    fetchInvites();
  }, [fetchInvites]);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!token || !vendorName || !vendorEmail) return;

    setIsCreating(true);
    setFormError(null);
    try {
      const res = await apiCreateInvitation(token, {
        vendor_name: vendorName,
        vendor_email: vendorEmail,
        days_valid: Number(daysValid),
        custom_message: customMessage || undefined,
      });
      setCreatedInvite(res);
      setVendorName('');
      setVendorEmail('');
      setCustomMessage('');
      fetchInvites();
    } catch (err: any) {
      setFormError(err?.message || 'Failed to dispatch vendor invitation.');
    } finally {
      setIsCreating(false);
    }
  };

  const handleRevoke = async (id: string) => {
    if (!token) return;
    if (!window.confirm('Are you sure you want to revoke this vendor invitation?')) return;

    try {
      await apiRevokeInvitation(token, id);
      fetchInvites();
    } catch (err: any) {
      alert(err?.message || 'Failed to revoke invitation.');
    }
  };

  const copyToClipboard = (text: string, id: string) => {
    navigator.clipboard.writeText(text);
    setCopiedToken(id);
    setTimeout(() => setCopiedToken(null), 2500);
  };

  const getStatusBadge = (status: InvitationStatus) => {
    switch (status) {
      case 'PENDING':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-amber-50 text-amber-700 border border-amber-200">
            <Clock className="w-3 h-3 text-amber-600" />
            Pending Submission
          </span>
        );
      case 'ACCEPTED':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">
            <CheckCircle2 className="w-3 h-3 text-emerald-600" />
            Accepted
          </span>
        );
      case 'EXPIRED':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-slate-100 text-slate-600 border border-slate-200">
            <AlertTriangle className="w-3 h-3 text-slate-500" />
            Expired
          </span>
        );
      case 'REVOKED':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-rose-50 text-rose-700 border border-rose-200">
            <XCircle className="w-3 h-3 text-rose-600" />
            Revoked
          </span>
        );
      default:
        return <span>{status}</span>;
    }
  };

  const pendingCount = invitations.filter((i) => i.status === 'PENDING').length;
  const acceptedCount = invitations.filter((i) => i.status === 'ACCEPTED').length;
  const expiredCount = invitations.filter((i) => i.status === 'EXPIRED').length;

  return (
    <div className="space-y-6">
      {/* Top Banner / Metrics */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 bg-white p-6 rounded-xl border border-slate-200 shadow-2xs">
        <div>
          <h2 className="text-xl font-bold text-slate-900">Procurement Officer Workspace</h2>
          <p className="text-xs text-slate-500 mt-1">
            Manage vendor onboarding invitations, track response status, and control issuing authority for{' '}
            <span className="font-semibold text-slate-700">{user?.organisation.name}</span>.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={fetchInvites}
            disabled={loading}
            className="inline-flex items-center gap-1.5 px-3 py-2 rounded-lg text-xs font-medium text-slate-700 bg-slate-100 hover:bg-slate-200 border border-slate-200 transition-colors"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
            Refresh
          </button>
          <button
            onClick={() => {
              setCreatedInvite(null);
              setFormError(null);
              setIsModalOpen(true);
            }}
            className="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg text-xs font-semibold text-white bg-indigo-600 hover:bg-indigo-700 shadow-xs transition-colors"
          >
            <Plus className="w-4 h-4" />
            Create Vendor Invitation
          </button>
        </div>
      </div>

      {/* Metric Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-4 gap-4">
        <div className="bg-white p-4 rounded-xl border border-slate-200">
          <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
            Total Dispatched
          </span>
          <div className="text-2xl font-bold text-slate-900 mt-1">{invitations.length}</div>
          <div className="text-[11px] text-slate-400 mt-1">Scoped to this organisation</div>
        </div>
        <div className="bg-white p-4 rounded-xl border border-amber-200 bg-amber-50/20">
          <span className="text-xs font-semibold text-amber-700 uppercase tracking-wider">
            Pending Vendor Action
          </span>
          <div className="text-2xl font-bold text-amber-900 mt-1">{pendingCount}</div>
          <div className="text-[11px] text-amber-600 mt-1">Awaiting vendor form submission</div>
        </div>
        <div className="bg-white p-4 rounded-xl border border-emerald-200 bg-emerald-50/20">
          <span className="text-xs font-semibold text-emerald-700 uppercase tracking-wider">
            Accepted / Onboarded
          </span>
          <div className="text-2xl font-bold text-emerald-900 mt-1">{acceptedCount}</div>
          <div className="text-[11px] text-emerald-600 mt-1">Submitted applications</div>
        </div>
        <div className="bg-white p-4 rounded-xl border border-slate-200">
          <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
            Expired or Inactive
          </span>
          <div className="text-2xl font-bold text-slate-700 mt-1">{expiredCount}</div>
          <div className="text-[11px] text-slate-400 mt-1">Require re-invitation</div>
        </div>
      </div>

      {/* Operational Exception Counter Overview */}
      <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-2xs space-y-3">
        <div className="flex items-center justify-between border-b border-slate-100 pb-2">
          <h3 className="text-xs font-bold text-slate-900 uppercase tracking-wider flex items-center gap-1.5">
            <AlertTriangle className="w-4 h-4 text-amber-500" />
            Operational Exceptions &amp; Remediation Status
          </h3>
          <span className="text-xs text-slate-500">
            {orgExceptions.length} total exception{orgExceptions.length === 1 ? '' : 's'} across organisation
          </span>
        </div>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
          <div className="p-3 rounded-lg bg-amber-50 border border-amber-200">
            <span className="text-[11px] font-semibold text-amber-800 uppercase">Awaiting Vendor Action</span>
            <div className="text-xl font-bold text-amber-900 mt-0.5">
              {orgExceptions.filter((e) => e.status === 'ACTION_REQUIRED_FROM_VENDOR').length}
            </div>
            <span className="text-[10px] text-amber-700">Clarification or re-upload requested</span>
          </div>

          <div className="p-3 rounded-lg bg-blue-50 border border-blue-200">
            <span className="text-[11px] font-semibold text-blue-800 uppercase">Vendor Responded</span>
            <div className="text-xl font-bold text-blue-900 mt-0.5">
              {orgExceptions.filter((e) => e.status === 'RESPONSE_SUBMITTED').length}
            </div>
            <span className="text-[10px] text-blue-700">Ready for reviewer evaluation</span>
          </div>

          <div className="p-3 rounded-lg bg-rose-50 border border-rose-200">
            <span className="text-[11px] font-semibold text-rose-800 uppercase">Critical / High Severity</span>
            <div className="text-xl font-bold text-rose-900 mt-0.5">
              {orgExceptions.filter((e) => (e.severity === 'CRITICAL' || e.severity === 'HIGH') && e.status !== 'RESOLVED' && e.status !== 'CLOSED').length}
            </div>
            <span className="text-[10px] text-rose-700">Statutory / PAN / GST discrepancies</span>
          </div>

          <div className="p-3 rounded-lg bg-emerald-50 border border-emerald-200">
            <span className="text-[11px] font-semibold text-emerald-800 uppercase">Resolved &amp; Verified</span>
            <div className="text-xl font-bold text-emerald-900 mt-0.5">
              {orgExceptions.filter((e) => e.status === 'RESOLVED' || e.status === 'CLOSED').length}
            </div>
            <span className="text-[10px] text-emerald-700">Remediated or overridden with note</span>
          </div>
        </div>
      </div>

      {/* Invitations Table */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-2xs overflow-hidden">
        <div className="px-6 py-4 border-b border-slate-100 flex items-center justify-between">
          <h3 className="text-sm font-bold text-slate-900">Vendor Invitation Register</h3>
          <span className="text-xs text-slate-500">
            {invitations.length} invitation{invitations.length === 1 ? '' : 's'} recorded
          </span>
        </div>

        {error && (
          <div className="p-4 bg-rose-50 border-b border-rose-200 flex items-center gap-2 text-xs text-rose-700">
            <ShieldAlert className="w-4 h-4 text-rose-600 shrink-0" />
            {error}
          </div>
        )}

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-50 text-slate-500 border-b border-slate-200 font-semibold uppercase tracking-wider">
              <tr>
                <th className="px-6 py-3">Vendor / Entity</th>
                <th className="px-6 py-3">Contact Email</th>
                <th className="px-6 py-3">Status</th>
                <th className="px-6 py-3">Expiry Date</th>
                <th className="px-6 py-3 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 text-slate-700">
              {loading && invitations.length === 0 ? (
                <tr>
                  <td colSpan={5} className="px-6 py-8 text-center text-slate-400">
                    Loading organisation invitations...
                  </td>
                </tr>
              ) : invitations.length === 0 ? (
                <tr>
                  <td colSpan={5} className="px-6 py-8 text-center text-slate-400">
                    No vendor invitations created yet. Click &ldquo;Create Vendor Invitation&rdquo; to begin.
                  </td>
                </tr>
              ) : (
                invitations.map((inv) => (
                  <tr key={inv.id} className="hover:bg-slate-50/60 transition-colors">
                    <td className="px-6 py-4">
                      <div className="font-semibold text-slate-900">{inv.vendor_name}</div>
                      {inv.custom_message && (
                        <div className="text-[11px] text-slate-400 line-clamp-1 mt-0.5">
                          Note: {inv.custom_message}
                        </div>
                      )}
                    </td>
                    <td className="px-6 py-4 font-mono text-slate-600">{inv.vendor_email}</td>
                    <td className="px-6 py-4">{getStatusBadge(inv.status)}</td>
                    <td className="px-6 py-4 text-slate-500">
                      {new Date(inv.expires_at).toLocaleDateString(undefined, {
                        year: 'numeric',
                        month: 'short',
                        day: 'numeric',
                        hour: '2-digit',
                        minute: '2-digit',
                      })}
                    </td>
                    <td className="px-6 py-4 text-right space-x-2">
                      {inv.status === 'PENDING' && (
                        <button
                          onClick={() => handleRevoke(inv.id)}
                          className="px-2.5 py-1 rounded text-xs font-medium text-rose-600 hover:text-rose-800 hover:bg-rose-50 border border-rose-200 transition-colors"
                        >
                          Revoke
                        </button>
                      )}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Create Invitation Modal */}
      {isModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 backdrop-blur-2xs p-4">
          <div className="bg-white rounded-2xl max-w-lg w-full p-6 shadow-xl border border-slate-200">
            <div className="flex items-center justify-between pb-4 border-b border-slate-100">
              <div>
                <h3 className="text-base font-bold text-slate-900">Issue Vendor Invitation</h3>
                <p className="text-xs text-slate-500 mt-0.5">
                  Generate a cryptographically random, expiring link for vendor onboarding
                </p>
              </div>
              <button
                onClick={() => setIsModalOpen(false)}
                className="text-slate-400 hover:text-slate-600 text-sm font-semibold"
              >
                &times;
              </button>
            </div>

            {createdInvite ? (
              <div className="py-6 space-y-4">
                <div className="p-4 rounded-xl bg-emerald-50 border border-emerald-200 text-xs text-emerald-800 space-y-2">
                  <div className="flex items-center gap-2 font-bold text-emerald-900">
                    <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                    Vendor Invitation Successfully Generated!
                  </div>
                  <p>
                    A high-entropy token was generated. Only its SHA-256 hash has been stored in
                    the database.
                  </p>
                </div>

                <div className="p-4 rounded-xl bg-slate-50 border border-slate-200 space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-[11px] font-bold text-indigo-700 uppercase tracking-wider bg-indigo-50 px-2 py-0.5 rounded border border-indigo-200">
                      Simulated Demo Direct Link
                    </span>
                    <span className="text-[10px] text-slate-400">Valid for {createdInvite.expires_at}</span>
                  </div>
                  <p className="text-xs text-slate-600">
                    In production, this link is dispatched securely via email. For local evaluation,
                    use the simulated link below:
                  </p>
                  <div className="flex items-center gap-2 pt-1">
                    <input
                      type="text"
                      readOnly
                      value={`${window.location.origin}${createdInvite.demo_invitation_url}`}
                      className="w-full text-xs font-mono bg-white border border-slate-300 rounded px-2.5 py-1.5 select-all"
                    />
                    <button
                      onClick={() =>
                        copyToClipboard(
                          `${window.location.origin}${createdInvite.demo_invitation_url}`,
                          createdInvite.id
                        )
                      }
                      className="px-3 py-1.5 rounded bg-indigo-600 text-white text-xs font-semibold hover:bg-indigo-700 shrink-0 inline-flex items-center gap-1"
                    >
                      {copiedToken === createdInvite.id ? (
                        <>
                          <Check className="w-3.5 h-3.5" /> Copied!
                        </>
                      ) : (
                        <>
                          <Copy className="w-3.5 h-3.5" /> Copy Link
                        </>
                      )}
                    </button>
                  </div>
                </div>

                <div className="flex justify-end gap-2 pt-2">
                  <button
                    onClick={() => {
                      if (createdInvite.demo_invitation_url) {
                        window.open(createdInvite.demo_invitation_url, '_blank');
                      }
                    }}
                    className="px-3 py-2 rounded-lg border border-slate-200 text-xs font-semibold text-slate-700 hover:bg-slate-50 inline-flex items-center gap-1.5"
                  >
                    <ExternalLink className="w-3.5 h-3.5" />
                    Open as Vendor in New Tab
                  </button>
                  <button
                    onClick={() => setIsModalOpen(false)}
                    className="px-4 py-2 rounded-lg bg-slate-900 text-white text-xs font-semibold hover:bg-slate-800"
                  >
                    Done
                  </button>
                </div>
              </div>
            ) : (
              <form onSubmit={handleCreate} className="space-y-4 pt-4">
                {formError && (
                  <div className="p-3 bg-rose-50 border border-rose-200 rounded-lg text-xs text-rose-700">
                    {formError}
                  </div>
                )}

                <div>
                  <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1">
                    Vendor Business / Trade Name
                  </label>
                  <input
                    type="text"
                    required
                    value={vendorName}
                    onChange={(e) => setVendorName(e.target.value)}
                    placeholder="e.g. Apex Industrial Supplies Pvt Ltd"
                    className="w-full px-3 py-2 text-xs border border-slate-300 rounded-lg focus:outline-hidden focus:ring-2 focus:ring-indigo-500"
                  />
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1">
                    Vendor Contact Business Email
                  </label>
                  <input
                    type="email"
                    required
                    value={vendorEmail}
                    onChange={(e) => setVendorEmail(e.target.value)}
                    placeholder="e.g. contact@apexindustrial.in"
                    className="w-full px-3 py-2 text-xs border border-slate-300 rounded-lg focus:outline-hidden focus:ring-2 focus:ring-indigo-500"
                  />
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1">
                    Invitation Validity Period (Days)
                  </label>
                  <select
                    value={daysValid}
                    onChange={(e) => setDaysValid(Number(e.target.value))}
                    className="w-full px-3 py-2 text-xs border border-slate-300 rounded-lg focus:outline-hidden focus:ring-2 focus:ring-indigo-500 bg-white"
                  >
                    <option value={3}>3 Days (Expedited)</option>
                    <option value={7}>7 Days (Standard)</option>
                    <option value={14}>14 Days (Extended)</option>
                    <option value={30}>30 Days (Maximum)</option>
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1">
                    Custom Message to Vendor (Optional)
                  </label>
                  <textarea
                    rows={3}
                    value={customMessage}
                    onChange={(e) => setCustomMessage(e.target.value)}
                    placeholder="e.g. Please provide your GSTIN, entity PAN, and cancelled cheque for vendor registration."
                    className="w-full px-3 py-2 text-xs border border-slate-300 rounded-lg focus:outline-hidden focus:ring-2 focus:ring-indigo-500"
                  />
                </div>

                <div className="flex justify-end gap-2 pt-3 border-t border-slate-100">
                  <button
                    type="button"
                    onClick={() => setIsModalOpen(false)}
                    className="px-4 py-2 rounded-lg text-xs font-medium text-slate-600 hover:bg-slate-100 border border-slate-200"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={isCreating}
                    className="px-4 py-2 rounded-lg text-xs font-semibold text-white bg-indigo-600 hover:bg-indigo-700 shadow-xs disabled:opacity-50 inline-flex items-center gap-1.5"
                  >
                    <Send className="w-3.5 h-3.5" />
                    {isCreating ? 'Generating Token...' : 'Issue Invitation'}
                  </button>
                </div>
              </form>
            )}
          </div>
        </div>
      )}
    </div>
  );
};
