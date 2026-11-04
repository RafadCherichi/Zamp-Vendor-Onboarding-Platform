import React, { useState, useEffect, useCallback } from 'react';
import {
  Search,
  Filter,
  RotateCcw,
  ChevronLeft,
  ChevronRight,
  AlertTriangle,
  CheckCircle2,
  Eye,
  X,
  UserCheck,
} from 'lucide-react';
import { useAuth } from '../../context/AuthContext';
import {
  apiQueryApplicationQueue,
  apiGetOrganisationReviewers,
  apiAssignReviewer,
} from '../../api/queue';
import type { QueueItem, ReviewerUser } from '../../types/queue';

interface Props {
  initialStatus?: string;
  initialSeverity?: string;
  initialReadyForApproval?: boolean;
  initialAssignedToMe?: boolean;
  onSelectApplication: (applicationId: string) => void;
}

export const ApplicationQueue: React.FC<Props> = ({
  initialStatus,
  initialSeverity,
  initialReadyForApproval = false,
  initialAssignedToMe = false,
  onSelectApplication,
}) => {
  const { user } = useAuth();
  const [items, setItems] = useState<QueueItem[]>([]);
  const [total, setTotal] = useState<number>(0);
  const [page, setPage] = useState<number>(1);
  const [pageSize, setPageSize] = useState<number>(10);
  const [totalPages, setTotalPages] = useState<number>(1);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // Filters
  const [search, setSearch] = useState<string>('');
  const [status, setStatus] = useState<string>(initialStatus || 'ALL');
  const [severity, setSeverity] = useState<string>(initialSeverity || 'ALL');
  const [assignedReviewerId, setAssignedReviewerId] = useState<string>(
    initialAssignedToMe && user?.id ? user.id : 'ALL'
  );
  const [readyForApprovalOnly, setReadyForApprovalOnly] = useState<boolean>(initialReadyForApproval);
  const [reviewers, setReviewers] = useState<ReviewerUser[]>([]);

  // Sync props changes from parent dashboard
  useEffect(() => {
    if (initialStatus) setStatus(initialStatus);
  }, [initialStatus]);

  useEffect(() => {
    if (initialSeverity) setSeverity(initialSeverity);
  }, [initialSeverity]);

  useEffect(() => {
    setReadyForApprovalOnly(initialReadyForApproval);
  }, [initialReadyForApproval]);

  useEffect(() => {
    if (initialAssignedToMe && user?.id) {
      setAssignedReviewerId(user.id);
    }
  }, [initialAssignedToMe, user?.id]);

  const fetchReviewers = async () => {
    try {
      const data = await apiGetOrganisationReviewers();
      setReviewers(data);
    } catch {
      // Ignore
    }
  };

  const fetchQueue = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const res = await apiQueryApplicationQueue({
        search: search.trim() || undefined,
        status: status !== 'ALL' ? status : undefined,
        exception_severity: severity !== 'ALL' ? severity : undefined,
        assigned_reviewer_id: assignedReviewerId !== 'ALL' ? assignedReviewerId : undefined,
        ready_for_approval_only: readyForApprovalOnly || undefined,
        page,
        page_size: pageSize,
      });
      setItems(res.items);
      setTotal(res.total);
      setTotalPages(res.total_pages);
    } catch (err: any) {
      setError(err?.message || 'Failed to fetch application queue.');
    } finally {
      setLoading(false);
    }
  }, [search, status, severity, assignedReviewerId, readyForApprovalOnly, page, pageSize]);

  useEffect(() => {
    fetchReviewers();
  }, []);

  useEffect(() => {
    fetchQueue();
  }, [fetchQueue]);

  const handleClearFilters = () => {
    setSearch('');
    setStatus('ALL');
    setSeverity('ALL');
    setAssignedReviewerId('ALL');
    setReadyForApprovalOnly(false);
    setPage(1);
  };

  const handleQuickAssign = async (appId: string, revId: string) => {
    try {
      await apiAssignReviewer(appId, revId || null);
      fetchQueue();
    } catch (err: any) {
      alert(err?.message || 'Failed to reassign application.');
    }
  };

  const getStatusBadge = (st: string) => {
    switch (st) {
      case 'APPROVED':
        return 'bg-emerald-100 text-emerald-800 border-emerald-300';
      case 'REJECTED':
        return 'bg-rose-100 text-rose-800 border-rose-300';
      case 'ACTION_REQUIRED':
        return 'bg-amber-100 text-amber-800 border-amber-300';
      case 'UNDER_REVIEW':
        return 'bg-purple-100 text-purple-800 border-purple-300';
      case 'SUBMITTED':
        return 'bg-blue-100 text-blue-800 border-blue-300';
      case 'ESCALATED':
        return 'bg-orange-100 text-orange-800 border-orange-300';
      default:
        return 'bg-slate-100 text-slate-700 border-slate-200';
    }
  };

  const hasActiveFilters =
    search !== '' ||
    status !== 'ALL' ||
    severity !== 'ALL' ||
    assignedReviewerId !== 'ALL' ||
    readyForApprovalOnly;

  return (
    <div className="bg-white rounded-2xl border border-slate-200 shadow-2xs overflow-hidden space-y-4 p-5">
      {/* Header and Search Bar */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-3 border-b border-slate-100 pb-4">
        <div>
          <h3 className="text-base font-bold text-slate-900">Application Management Queue</h3>
          <p className="text-xs text-slate-500 mt-0.5">
            Real-time queue scoped to your organisation with multi-filter search and evidence inspection.
          </p>
        </div>

        {/* Search Input */}
        <div className="relative w-full md:w-80">
          <Search className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
          <input
            type="text"
            value={search}
            onChange={(e) => {
              setSearch(e.target.value);
              setPage(1);
            }}
            placeholder="Search vendor name, ref, or email..."
            className="w-full pl-9 pr-3 py-1.5 text-xs border border-slate-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:outline-none"
          />
        </div>
      </div>

      {/* Filter Chips Bar */}
      <div className="flex flex-wrap items-center gap-2.5 text-xs text-slate-600">
        <span className="font-semibold text-slate-700 flex items-center gap-1">
          <Filter className="w-3.5 h-3.5 text-indigo-600" />
          Filters:
        </span>

        {/* Status Dropdown */}
        <select
          value={status}
          onChange={(e) => {
            setStatus(e.target.value);
            setPage(1);
          }}
          className="px-2.5 py-1 rounded-lg border border-slate-200 bg-slate-50 text-xs font-medium focus:outline-none"
        >
          <option value="ALL">All Statuses</option>
          <option value="SUBMITTED">Submitted</option>
          <option value="UNDER_REVIEW">Under Review</option>
          <option value="ACTION_REQUIRED">Action Required</option>
          <option value="APPROVED">Approved</option>
          <option value="REJECTED">Rejected</option>
          <option value="ESCALATED">Escalated</option>
        </select>

        {/* Severity Dropdown */}
        <select
          value={severity}
          onChange={(e) => {
            setSeverity(e.target.value);
            setPage(1);
          }}
          className="px-2.5 py-1 rounded-lg border border-slate-200 bg-slate-50 text-xs font-medium focus:outline-none"
        >
          <option value="ALL">All Severities</option>
          <option value="CRITICAL">Critical Exceptions</option>
          <option value="HIGH">High Severity</option>
          <option value="MEDIUM">Medium Severity</option>
          <option value="LOW">Low Severity</option>
        </select>

        {/* Assigned Reviewer Dropdown */}
        <select
          value={assignedReviewerId}
          onChange={(e) => {
            setAssignedReviewerId(e.target.value);
            setPage(1);
          }}
          className="px-2.5 py-1 rounded-lg border border-slate-200 bg-slate-50 text-xs font-medium focus:outline-none"
        >
          <option value="ALL">All Reviewers</option>
          {reviewers.map((r) => (
            <option key={r.id} value={r.id}>
              {r.full_name}
            </option>
          ))}
        </select>

        {/* Assigned to Me Toggle Chip */}
        {user?.id && (
          <button
            onClick={() => {
              if (assignedReviewerId === user.id) {
                setAssignedReviewerId('ALL');
              } else {
                setAssignedReviewerId(user.id);
              }
              setPage(1);
            }}
            className={`px-3 py-1 rounded-lg border text-xs font-semibold transition flex items-center gap-1 ${
              assignedReviewerId === user.id
                ? 'bg-indigo-600 text-white border-indigo-600 shadow-xs'
                : 'bg-slate-50 hover:bg-slate-100 text-slate-700 border-slate-200'
            }`}
          >
            <UserCheck className="w-3.5 h-3.5" />
            <span>Assigned to Me</span>
          </button>
        )}

        {/* Ready for Approval Toggle Chip */}
        <button
          onClick={() => {
            setReadyForApprovalOnly(!readyForApprovalOnly);
            setPage(1);
          }}
          className={`px-3 py-1 rounded-lg border text-xs font-semibold transition flex items-center gap-1 ${
            readyForApprovalOnly
              ? 'bg-emerald-600 text-white border-emerald-600 shadow-xs'
              : 'bg-slate-50 hover:bg-slate-100 text-slate-700 border-slate-200'
          }`}
        >
          <CheckCircle2 className="w-3.5 h-3.5" />
          <span>Ready for Approval</span>
        </button>

        {hasActiveFilters && (
          <button
            onClick={handleClearFilters}
            className="px-2.5 py-1 rounded-lg text-xs font-semibold text-rose-600 hover:bg-rose-50 border border-rose-200 transition flex items-center gap-1"
          >
            <X className="w-3.5 h-3.5" />
            <span>Clear Filters</span>
          </button>
        )}
      </div>

      {error && (
        <div className="p-3 bg-rose-50 border border-rose-200 text-rose-700 rounded-lg text-xs">
          {error}
        </div>
      )}

      {/* Applications Queue Table */}
      <div className="overflow-x-auto border border-slate-200 rounded-xl">
        <table className="w-full text-left text-xs">
          <thead className="bg-slate-50 text-slate-500 border-b border-slate-200 font-semibold uppercase tracking-wider">
            <tr>
              <th className="px-4 py-3">Vendor / Reference</th>
              <th className="px-4 py-3">Constitution</th>
              <th className="px-4 py-3">Submitted</th>
              <th className="px-4 py-3">Status</th>
              <th className="px-4 py-3">Active Exceptions</th>
              <th className="px-4 py-3">Assigned Reviewer</th>
              <th className="px-4 py-3 text-right">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {loading ? (
              <tr>
                <td colSpan={7} className="text-center py-8 text-slate-400">
                  <RotateCcw className="w-5 h-5 animate-spin mx-auto text-indigo-600 mb-1" />
                  Loading application queue...
                </td>
              </tr>
            ) : items.length === 0 ? (
              <tr>
                <td colSpan={7} className="text-center py-8 text-slate-400">
                  No applications matched the selected filters.
                </td>
              </tr>
            ) : (
              items.map((item) => (
                <tr key={item.id} className="hover:bg-slate-50/80 transition">
                  <td className="px-4 py-3">
                    <span className="font-mono text-[11px] font-bold text-indigo-700 block">
                      {item.reference_number}
                    </span>
                    <span className="font-bold text-slate-900 text-sm line-clamp-1">
                      {item.legal_name}
                    </span>
                    {item.trade_name && item.trade_name !== item.legal_name && (
                      <span className="text-[11px] text-slate-500 block">
                        T/A: {item.trade_name}
                      </span>
                    )}
                  </td>
                  <td className="px-4 py-3 text-slate-600 font-medium">
                    {item.constitution.replace(/_/g, ' ')}
                  </td>
                  <td className="px-4 py-3 text-slate-500">
                    {item.submitted_at ? new Date(item.submitted_at).toLocaleDateString() : 'Draft'}
                  </td>
                  <td className="px-4 py-3">
                    <span className={`px-2 py-0.5 rounded-full text-[11px] font-bold border ${getStatusBadge(item.status)}`}>
                      {item.status.replace(/_/g, ' ')}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    {item.open_exceptions_count > 0 ? (
                      <span
                        className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-bold border ${
                          item.critical_exceptions_count > 0
                            ? 'bg-rose-50 text-rose-800 border-rose-300'
                            : 'bg-amber-50 text-amber-800 border-amber-300'
                        }`}
                      >
                        <AlertTriangle className="w-3 h-3" />
                        {item.open_exceptions_count} Open ({item.critical_exceptions_count} Crit)
                      </span>
                    ) : item.ready_for_approval ? (
                      <span className="inline-flex items-center gap-1 text-[11px] font-semibold text-emerald-700">
                        <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
                        Clean / Ready
                      </span>
                    ) : (
                      <span className="text-slate-400">0 Exceptions</span>
                    )}
                  </td>
                  <td className="px-4 py-3">
                    <select
                      value={item.assigned_reviewer_id || ''}
                      onChange={(e) => handleQuickAssign(item.id, e.target.value)}
                      className="bg-slate-50 hover:bg-white text-xs border border-slate-200 rounded p-1 font-medium text-slate-700 focus:outline-none"
                    >
                      <option value="">Unassigned</option>
                      {reviewers.map((r) => (
                        <option key={r.id} value={r.id}>
                          {r.full_name}
                        </option>
                      ))}
                    </select>
                  </td>
                  <td className="px-4 py-3 text-right">
                    <button
                      onClick={() => onSelectApplication(item.id)}
                      className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg font-semibold text-xs text-white bg-indigo-600 hover:bg-indigo-700 shadow-xs transition"
                    >
                      <Eye className="w-3.5 h-3.5" />
                      <span>Inspect</span>
                    </button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Pagination Bar */}
      <div className="flex flex-col sm:flex-row items-center justify-between gap-3 pt-2 text-xs text-slate-500">
        <div>
          Showing <span className="font-semibold text-slate-900">{items.length}</span> of{' '}
          <span className="font-semibold text-slate-900">{total}</span> applications
        </div>

        <div className="flex items-center gap-3">
          <div className="flex items-center gap-1">
            <span>Per page:</span>
            <select
              value={pageSize}
              onChange={(e) => {
                setPageSize(Number(e.target.value));
                setPage(1);
              }}
              className="border border-slate-200 rounded px-1.5 py-0.5 bg-slate-50 text-xs focus:outline-none"
            >
              <option value={10}>10</option>
              <option value={25}>25</option>
              <option value={50}>50</option>
            </select>
          </div>

          <div className="flex items-center gap-1">
            <button
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={page <= 1}
              className="p-1 rounded border border-slate-200 hover:bg-slate-50 disabled:opacity-40"
            >
              <ChevronLeft className="w-4 h-4" />
            </button>
            <span className="px-2 font-medium text-slate-700">
              Page {page} of {totalPages || 1}
            </span>
            <button
              onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
              disabled={page >= totalPages}
              className="p-1 rounded border border-slate-200 hover:bg-slate-50 disabled:opacity-40"
            >
              <ChevronRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
