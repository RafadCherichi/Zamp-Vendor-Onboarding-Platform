import React, { useState, useEffect, useCallback } from 'react';
import { useAuth } from '../../context/AuthContext';
import { apiListInvitations, apiCreateInvitation, apiRevokeInvitation } from '../../api/invitations';
import { apiGetDashboardMetrics } from '../../api/queue';
import type { Invitation } from '../../types/invitation';
import type { DashboardMetrics } from '../../types/queue';
import { ApplicationQueue } from '../queue/ApplicationQueue';
import { ApplicationDetailsWorkspace } from '../review/ApplicationDetailsWorkspace';
import { ProcessRunHistory } from '../runs/ProcessRunHistory';
import {
  Plus,
  RefreshCw,
  Copy,
  Check,
  Inbox,
  Layers,
  Activity,
} from 'lucide-react';

export const ProcurementDashboard: React.FC = () => {
  const { token, user } = useAuth();
  const [activeView, setActiveView] = useState<'QUEUE' | 'RUNS' | 'INVITATIONS'>('QUEUE');
  const [selectedApplicationId, setSelectedApplicationId] = useState<string | null>(null);

  // Queue initial filters triggered by dashboard metric clicks
  const [queueStatusFilter, setQueueStatusFilter] = useState<string>('ALL');
  const [queueSeverityFilter, setQueueSeverityFilter] = useState<string>('ALL');
  const [queueReadyFilter, setQueueReadyFilter] = useState<boolean>(false);

  // Data states
  const [metrics, setMetrics] = useState<DashboardMetrics | null>(null);
  const [invitations, setInvitations] = useState<Invitation[]>([]);
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

  const fetchDashboardData = useCallback(async () => {
    if (!token) return;
    setLoading(true);
    setError(null);
    try {
      const [metricsData, invData] = await Promise.all([
        apiGetDashboardMetrics(token).catch(() => null),
        apiListInvitations(token).catch(() => []),
      ]);
      setMetrics(metricsData);
      setInvitations(invData);
    } catch (err: any) {
      setError(err?.message || 'Failed to load dashboard data.');
    } finally {
      setLoading(false);
    }
  }, [token]);

  useEffect(() => {
    fetchDashboardData();
  }, [fetchDashboardData]);

  const handleCreateInvitation = async (e: React.FormEvent) => {
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
      fetchDashboardData();
    } catch (err: any) {
      setFormError(err?.message || 'Failed to dispatch vendor invitation.');
    } finally {
      setIsCreating(false);
    }
  };

  const handleRevokeInvitation = async (id: string) => {
    if (!token) return;
    if (!window.confirm('Are you sure you want to revoke this vendor invitation?')) return;

    try {
      await apiRevokeInvitation(token, id);
      fetchDashboardData();
    } catch (err: any) {
      alert(err?.message || 'Failed to revoke invitation.');
    }
  };

  const copyToClipboard = (text: string, id: string) => {
    navigator.clipboard.writeText(text);
    setCopiedToken(id);
    setTimeout(() => setCopiedToken(null), 2500);
  };

  const navigateToQueueFilter = (status: string, severity: string = 'ALL', readyOnly: boolean = false) => {
    setQueueStatusFilter(status);
    setQueueSeverityFilter(severity);
    setQueueReadyFilter(readyOnly);
    setActiveView('QUEUE');
    setSelectedApplicationId(null);
  };

  if (selectedApplicationId) {
    return (
      <ApplicationDetailsWorkspace
        applicationId={selectedApplicationId}
        onBack={() => setSelectedApplicationId(null)}
        onActionComplete={fetchDashboardData}
        isReviewer={true}
      />
    );
  }

  return (
    <div className="space-y-6">
      {/* Top Banner */}
      <div className="relative flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 overflow-hidden bg-[#1d382b] p-6 sm:p-7 rounded-2xl border border-[#294a37] shadow-sm text-[#f8f7f0]">
        <div aria-hidden="true" className="pointer-events-none absolute -right-12 -top-24 h-64 w-64 rounded-full border border-[#ffffff18]" />
        <div>
          <p className="mb-2 text-[10px] font-bold uppercase tracking-[0.2em] text-[#c5d8c7]">Zamp · Vendor operations</p>
          <div className="flex flex-wrap items-center gap-2">
            <h2 className="font-serif text-2xl sm:text-3xl font-medium tracking-tight text-white">Good partnerships start here.</h2>
            <span className="text-[10px] uppercase font-bold tracking-wider px-2.5 py-1 rounded-full bg-[#ffffff14] text-[#e5ecdf] border border-[#ffffff2a]">
              Operations
            </span>
          </div>
          <p className="text-sm text-[#d3ded3] mt-2 max-w-2xl">
            Review each submission, see what the checks found, and help good vendors get moving. <span className="font-semibold text-white">{user?.organisation.name}</span>
          </p>
        </div>

        <div className="relative flex items-center gap-2">
          <button
            onClick={fetchDashboardData}
            disabled={loading}
            className="inline-flex h-10 items-center gap-1.5 px-3 rounded-lg text-xs font-semibold text-white bg-[#ffffff12] hover:bg-[#ffffff22] border border-[#ffffff30] transition"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
            <span>Refresh</span>
          </button>
          <button
            onClick={() => {
              setCreatedInvite(null);
              setFormError(null);
              setIsModalOpen(true);
            }}
            className="inline-flex h-10 items-center gap-1.5 px-4 rounded-lg text-xs font-semibold text-[#1d382b] bg-[#d8b76b] hover:bg-[#e5c984] shadow-xs transition"
          >
            <Plus className="w-4 h-4" />
            <span>Dispatch Invitation</span>
          </button>
        </div>
      </div>

      {error && (
        <div className="p-3 bg-rose-50 border border-rose-200 text-rose-800 text-xs rounded-xl">
          {error}
        </div>
      )}

      {/* Interactive Metric Cards (Click to Filter Queue) */}
      {metrics && activeView === 'QUEUE' && (
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
          {/* Total Applications */}
          <div
            onClick={() => navigateToQueueFilter('ALL')}
            className="bg-white p-4 rounded-xl border border-slate-200 hover:border-indigo-400 cursor-pointer transition shadow-2xs group"
          >
            <span className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider block">
              Total Applications
            </span>
            <div className="text-2xl font-bold text-slate-900 mt-1 group-hover:text-indigo-600 transition">
              {metrics.total_applications}
            </div>
            <span className="text-[10px] text-slate-400 mt-0.5 block">View complete queue &rarr;</span>
          </div>

          {/* Awaiting Review */}
          <div
            onClick={() => navigateToQueueFilter('UNDER_REVIEW')}
            className="bg-white p-4 rounded-xl border border-purple-200 bg-purple-50/20 hover:border-purple-400 cursor-pointer transition shadow-2xs group"
          >
            <span className="text-[11px] font-semibold text-purple-700 uppercase tracking-wider block">
              Awaiting Review
            </span>
            <div className="text-2xl font-bold text-purple-900 mt-1 group-hover:text-purple-600 transition">
              {metrics.awaiting_review_count}
            </div>
            <span className="text-[10px] text-purple-600 mt-0.5 block">Queued for evaluation &rarr;</span>
          </div>

          {/* Pending Vendor Action */}
          <div
            onClick={() => navigateToQueueFilter('ACTION_REQUIRED')}
            className="bg-white p-4 rounded-xl border border-amber-200 bg-amber-50/20 hover:border-amber-400 cursor-pointer transition shadow-2xs group"
          >
            <span className="text-[11px] font-semibold text-amber-700 uppercase tracking-wider block">
              Awaiting Vendor
            </span>
            <div className="text-2xl font-bold text-amber-900 mt-1 group-hover:text-amber-600 transition">
              {metrics.awaiting_vendor_count}
            </div>
            <span className="text-[10px] text-amber-600 mt-0.5 block">Clarifications requested &rarr;</span>
          </div>

          {/* Ready for Approval */}
          <div
            onClick={() => navigateToQueueFilter('SUBMITTED', 'ALL', true)}
            className="bg-white p-4 rounded-xl border border-emerald-200 bg-emerald-50/20 hover:border-emerald-400 cursor-pointer transition shadow-2xs group"
          >
            <span className="text-[11px] font-semibold text-emerald-700 uppercase tracking-wider block">
              Ready for Approval
            </span>
            <div className="text-2xl font-bold text-emerald-900 mt-1 group-hover:text-emerald-600 transition">
              {metrics.ready_for_approval_count}
            </div>
            <span className="text-[10px] text-emerald-600 mt-0.5 block">0 open exceptions &rarr;</span>
          </div>

          {/* Critical / High Exceptions */}
          <div
            onClick={() => navigateToQueueFilter('ALL', 'HIGH')}
            className="bg-white p-4 rounded-xl border border-rose-200 bg-rose-50/20 hover:border-rose-400 cursor-pointer transition shadow-2xs group"
          >
            <span className="text-[11px] font-semibold text-rose-700 uppercase tracking-wider block">
              High Severity Issues
            </span>
            <div className="text-2xl font-bold text-rose-900 mt-1 group-hover:text-rose-600 transition">
              {metrics.high_severity_exceptions_count}
            </div>
            <span className="text-[10px] text-rose-600 mt-0.5 block">Statutory blocks &rarr;</span>
          </div>

          {/* Approved */}
          <div
            onClick={() => navigateToQueueFilter('APPROVED')}
            className="bg-white p-4 rounded-xl border border-slate-200 hover:border-slate-300 cursor-pointer transition shadow-2xs group"
          >
            <span className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider block">
              Approved Vendors
            </span>
            <div className="text-2xl font-bold text-slate-700 mt-1 group-hover:text-slate-900 transition">
              {metrics.approved_count}
            </div>
            <span className="text-[10px] text-slate-400 mt-0.5 block">Master records &rarr;</span>
          </div>
        </div>
      )}

      {/* Operational Widgets Row */}
      {metrics && activeView === 'QUEUE' && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Widget 1: Recent Application Activity */}
          <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-2xs space-y-3">
            <h4 className="text-xs font-bold text-slate-900 uppercase tracking-wider flex items-center gap-1.5 border-b border-slate-100 pb-2">
              <Activity className="w-3.5 h-3.5 text-indigo-600" />
              Recent Application Activity
            </h4>
            <div className="space-y-2 max-h-52 overflow-y-auto divide-y divide-slate-100 text-xs">
              {metrics.recent_activity.length === 0 ? (
                <div className="py-4 text-center text-slate-400 text-xs">No recent activity.</div>
              ) : (
                metrics.recent_activity.map((act) => (
                  <div key={act.id} className="pt-2 pb-1">
                    <div className="flex items-center justify-between">
                      <span className="font-semibold text-slate-900">{act.event_type.replace(/_/g, ' ')}</span>
                      <span className="text-[10px] text-slate-400">
                        {act.created_at ? new Date(act.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : ''}
                      </span>
                    </div>
                    <span className="text-[11px] text-slate-500 block">by {act.actor_role}</span>
                  </div>
                ))
              )}
            </div>
          </div>

          {/* Widget 2: Recently Submitted Applications */}
          <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-2xs space-y-3">
            <h4 className="text-xs font-bold text-slate-900 uppercase tracking-wider flex items-center gap-1.5 border-b border-slate-100 pb-2">
              <Inbox className="w-3.5 h-3.5 text-indigo-600" />
              Recently Submitted
            </h4>
            <div className="space-y-2 max-h-52 overflow-y-auto divide-y divide-slate-100 text-xs">
              {metrics.recently_submitted.length === 0 ? (
                <div className="py-4 text-center text-slate-400 text-xs">No submitted applications yet.</div>
              ) : (
                metrics.recently_submitted.map((sub) => (
                  <div
                    key={sub.id}
                    onClick={() => setSelectedApplicationId(sub.id)}
                    className="pt-2 pb-1 cursor-pointer hover:bg-slate-50 transition rounded p-1"
                  >
                    <div className="flex items-center justify-between">
                      <span className="font-bold text-slate-900 truncate">{sub.legal_name}</span>
                      <span className="text-[10px] font-mono font-semibold text-indigo-600">{sub.reference_number}</span>
                    </div>
                    <div className="flex items-center justify-between text-[11px] text-slate-500 mt-0.5">
                      <span>{sub.constitution.replace(/_/g, ' ')}</span>
                      {sub.open_exceptions_count > 0 ? (
                        <span className="text-amber-600 font-semibold">{sub.open_exceptions_count} open issue(s)</span>
                      ) : (
                        <span className="text-emerald-600 font-semibold">Ready</span>
                      )}
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>

          {/* Widget 3: Exception Categories Breakdown */}
          <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-2xs space-y-3">
            <h4 className="text-xs font-bold text-slate-900 uppercase tracking-wider flex items-center gap-1.5 border-b border-slate-100 pb-2">
              <Layers className="w-3.5 h-3.5 text-indigo-600" />
              Open Issues by Category
            </h4>
            <div className="space-y-1.5 max-h-52 overflow-y-auto text-xs">
              {Object.keys(metrics.exception_breakdown_by_category).length === 0 ? (
                <div className="py-4 text-center text-slate-400 text-xs">No open exceptions.</div>
              ) : (
                Object.entries(metrics.exception_breakdown_by_category).map(([cat, count]) => (
                  <div key={cat} className="flex items-center justify-between p-1.5 bg-slate-50 rounded">
                    <span className="font-medium text-slate-700 truncate">{cat.replace(/_/g, ' ')}</span>
                    <span className="px-2 py-0.5 bg-amber-100 text-amber-800 rounded font-bold text-[11px]">
                      {count}
                    </span>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>
      )}

      {/* Main Workspace Navigation */}
      <div className="flex items-center justify-between border-b border-slate-200 pt-2">
        <div className="flex gap-4 text-sm font-bold">
          <button
            onClick={() => setActiveView('QUEUE')}
            className={`pb-2.5 border-b-2 transition ${
              activeView === 'QUEUE'
                ? 'border-indigo-600 text-indigo-700'
                : 'border-transparent text-slate-500 hover:text-slate-800'
            }`}
          >
            Vendor Application Queue
          </button>
          <button
            onClick={() => setActiveView('RUNS')}
            className={`pb-2.5 border-b-2 transition ${activeView === 'RUNS' ? 'border-indigo-600 text-indigo-700' : 'border-transparent text-slate-500 hover:text-slate-800'}`}
          >
            Processing Runs
          </button>
          <button
            onClick={() => setActiveView('INVITATIONS')}
            className={`pb-2.5 border-b-2 transition ${
              activeView === 'INVITATIONS'
                ? 'border-indigo-600 text-indigo-700'
                : 'border-transparent text-slate-500 hover:text-slate-800'
            }`}
          >
            Invitation Register ({invitations.length})
          </button>
        </div>
      </div>

      {/* View 1: Application Queue */}
      {activeView === 'QUEUE' && (
        <ApplicationQueue
          initialStatus={queueStatusFilter}
          initialSeverity={queueSeverityFilter}
          initialReadyForApproval={queueReadyFilter}
          onSelectApplication={(appId) => setSelectedApplicationId(appId)}
        />
      )}

      {activeView === 'RUNS' && token && (
        <ProcessRunHistory token={token} onOpenApplication={(id) => setSelectedApplicationId(id)} />
      )}

      {/* View 2: Invitations Register */}
      {activeView === 'INVITATIONS' && (
        <div className="bg-white rounded-xl border border-slate-200 shadow-2xs overflow-hidden">
          <div className="px-6 py-4 border-b border-slate-100 flex items-center justify-between">
            <h3 className="text-sm font-bold text-slate-900">Vendor Invitation Register</h3>
            <span className="text-xs text-slate-500">{invitations.length} invitation(s) recorded</span>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-50 text-slate-500 border-b border-slate-200 font-semibold uppercase tracking-wider">
                <tr>
                  <th className="px-6 py-3">Vendor / Entity</th>
                  <th className="px-6 py-3">Recipient Email</th>
                  <th className="px-6 py-3">Status</th>
                  <th className="px-6 py-3">Issued Date</th>
                  <th className="px-6 py-3">Expiry Date</th>
                  <th className="px-6 py-3">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {invitations.length === 0 ? (
                  <tr>
                    <td colSpan={6} className="text-center py-8 text-slate-400">
                      No vendor invitations created yet.
                    </td>
                  </tr>
                ) : (
                  invitations.map((inv) => (
                    <tr key={inv.id} className="hover:bg-slate-50/80 transition">
                      <td className="px-6 py-3.5 font-bold text-slate-900">{inv.vendor_name}</td>
                      <td className="px-6 py-3.5 text-slate-600">{inv.vendor_email}</td>
                      <td className="px-6 py-3.5">
                        <span className="font-semibold">{inv.status}</span>
                      </td>
                      <td className="px-6 py-3.5 text-slate-500">{new Date(inv.created_at).toLocaleDateString()}</td>
                      <td className="px-6 py-3.5 text-slate-500">{new Date(inv.expires_at).toLocaleDateString()}</td>
                      <td className="px-6 py-3.5">
                        {inv.status === 'PENDING' && (
                          <button
                            onClick={() => handleRevokeInvitation(inv.id)}
                            className="text-xs font-semibold text-rose-600 hover:text-rose-800"
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
      )}

      {/* Create Invitation Modal */}
      {isModalOpen && (
        <div className="fixed inset-0 bg-slate-900/50 backdrop-blur-2xs z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl max-w-lg w-full p-6 shadow-xl border border-slate-200 space-y-4">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <h3 className="font-bold text-slate-900 text-sm">Dispatch Vendor Onboarding Invitation</h3>
              <button onClick={() => setIsModalOpen(false)} className="text-slate-400 hover:text-slate-600">
                &times;
              </button>
            </div>

            {formError && (
              <div className="p-2.5 bg-rose-50 border border-rose-200 text-rose-800 text-xs rounded-lg">
                {formError}
              </div>
            )}

            {createdInvite ? (
              <div className="space-y-3 text-xs">
                <div className="p-3 bg-emerald-50 border border-emerald-200 text-emerald-800 rounded-lg">
                  Invitation created successfully! Provide the onboarding link below to the vendor:
                </div>
                <div className="flex items-center justify-between gap-2 p-2.5 bg-slate-100 border border-slate-200 rounded-lg font-mono text-[11px] break-all">
                  <span>{createdInvite.demo_invitation_url || `${window.location.origin}/invite?token=${createdInvite.id}`}</span>
                  <button
                    type="button"
                    onClick={() =>
                      copyToClipboard(
                        createdInvite.demo_invitation_url || `${window.location.origin}/invite?token=${createdInvite.id}`,
                        createdInvite.id
                      )
                    }
                    className="shrink-0 p-1.5 bg-white border border-slate-200 rounded text-slate-600 hover:text-slate-900 transition"
                    title="Copy Link"
                  >
                    {copiedToken === createdInvite.id ? <Check className="w-3.5 h-3.5 text-emerald-600" /> : <Copy className="w-3.5 h-3.5" />}
                  </button>
                </div>
                <button
                  type="button"
                  onClick={() => setIsModalOpen(false)}
                  className="w-full py-2 bg-indigo-600 text-white rounded-lg font-semibold"
                >
                  Done
                </button>
              </div>
            ) : (
              <form onSubmit={handleCreateInvitation} className="space-y-3 text-xs">
                <div>
                  <label className="block font-semibold text-slate-700 uppercase mb-1">Vendor Legal Name *</label>
                  <input
                    type="text"
                    required
                    value={vendorName}
                    onChange={(e) => setVendorName(e.target.value)}
                    placeholder="e.g. Acme Supplies Private Limited"
                    className="w-full p-2 border border-slate-300 rounded-lg focus:outline-none"
                  />
                </div>
                <div>
                  <label className="block font-semibold text-slate-700 uppercase mb-1">Vendor Contact Email *</label>
                  <input
                    type="email"
                    required
                    value={vendorEmail}
                    onChange={(e) => setVendorEmail(e.target.value)}
                    placeholder="e.g. compliance@acmesupplies.in"
                    className="w-full p-2 border border-slate-300 rounded-lg focus:outline-none"
                  />
                </div>
                <div>
                  <label className="block font-semibold text-slate-700 uppercase mb-1">Validity (Days)</label>
                  <input
                    type="number"
                    min={1}
                    max={30}
                    value={daysValid}
                    onChange={(e) => setDaysValid(Number(e.target.value))}
                    className="w-full p-2 border border-slate-300 rounded-lg focus:outline-none"
                  />
                </div>
                <div>
                  <label className="block font-semibold text-slate-700 uppercase mb-1">Custom Message (Optional)</label>
                  <textarea
                    rows={2}
                    value={customMessage}
                    onChange={(e) => setCustomMessage(e.target.value)}
                    placeholder="Optional message..."
                    className="w-full p-2 border border-slate-300 rounded-lg focus:outline-none"
                  />
                </div>

                <div className="flex justify-end gap-2 pt-2 border-t border-slate-100">
                  <button
                    type="button"
                    onClick={() => setIsModalOpen(false)}
                    className="px-3 py-1.5 border border-slate-200 rounded-lg text-slate-600"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={isCreating}
                    className="px-4 py-1.5 bg-indigo-600 text-white rounded-lg font-semibold disabled:opacity-50"
                  >
                    {isCreating ? 'Dispatching...' : 'Dispatch Invitation'}
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
