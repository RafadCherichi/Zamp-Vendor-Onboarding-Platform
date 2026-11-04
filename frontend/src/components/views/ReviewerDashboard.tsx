import React, { useState, useEffect } from 'react';
import { useAuth } from '../../context/AuthContext';
import { apiGetDashboardMetrics } from '../../api/queue';
import type { DashboardMetrics } from '../../types/queue';
import { ApplicationQueue } from '../queue/ApplicationQueue';
import { ApplicationDetailsWorkspace } from '../review/ApplicationDetailsWorkspace';
import {
  UserCheck,
  CheckCircle2,
  AlertTriangle,
  Clock,
  ShieldAlert,
  RefreshCw,
  FileCheck2,
} from 'lucide-react';

export const ReviewerDashboard: React.FC = () => {
  const { user, token } = useAuth();
  const [selectedApplicationId, setSelectedApplicationId] = useState<string | null>(null);

  // Quick filters for queue
  const [queueStatusFilter, setQueueStatusFilter] = useState<string>('ALL');
  const [queueSeverityFilter, setQueueSeverityFilter] = useState<string>('ALL');
  const [queueReadyFilter, setQueueReadyFilter] = useState<boolean>(false);
  const [assignedToMeOnly, setAssignedToMeOnly] = useState<boolean>(false);

  const [metrics, setMetrics] = useState<DashboardMetrics | null>(null);
  const [loadingMetrics, setLoadingMetrics] = useState<boolean>(true);

  const loadMetrics = async () => {
    if (!token) return;
    try {
      setLoadingMetrics(true);
      const data = await apiGetDashboardMetrics(token);
      setMetrics(data);
    } catch (err) {
      console.error('Failed to load reviewer dashboard metrics', err);
    } finally {
      setLoadingMetrics(false);
    }
  };

  useEffect(() => {
    loadMetrics();
  }, [token]);

  const handleFilterClick = (status: string, severity: string = 'ALL', ready: boolean = false, me: boolean = false) => {
    setQueueStatusFilter(status);
    setQueueSeverityFilter(severity);
    setQueueReadyFilter(ready);
    setAssignedToMeOnly(me);
    setSelectedApplicationId(null);
  };

  // If an application is selected for comprehensive review, display the Reviewer Workspace
  if (selectedApplicationId) {
    return (
      <ApplicationDetailsWorkspace
        applicationId={selectedApplicationId}
        onBack={() => {
          setSelectedApplicationId(null);
          loadMetrics();
        }}
        onActionComplete={() => {
          loadMetrics();
        }}
        isReviewer={true}
      />
    );
  }

  return (
    <div className="space-y-6">
      {/* Header Banner */}
      <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-2xs">
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-indigo-50 text-indigo-700 border border-indigo-200 flex items-center justify-center">
              <UserCheck className="w-6 h-6" />
            </div>
            <div>
              <h2 className="text-xl font-bold text-slate-900">Reviewer &amp; Approver Workspace</h2>
              <p className="text-xs text-slate-500">
                Evaluation, statutory verification, and decision terminal for{' '}
                <span className="font-semibold text-slate-700">{user?.organisation.name}</span>
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={loadMetrics}
              disabled={loadingMetrics}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold text-slate-700 bg-slate-100 hover:bg-slate-200 border border-slate-200 transition"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${loadingMetrics ? 'animate-spin' : ''}`} />
              <span>Refresh Metrics</span>
            </button>
            <div className="px-3 py-1.5 rounded-lg bg-emerald-50 border border-emerald-200 text-xs font-bold text-emerald-800 flex items-center gap-1">
              <FileCheck2 className="w-3.5 h-3.5" />
              <span>Statutory Decision Authority</span>
            </div>
          </div>
        </div>
      </div>

      {/* Reviewer Priority Metric Cards */}
      {metrics && (
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-3">
          {/* Card 1: Ready for Approval */}
          <div
            onClick={() => handleFilterClick('ALL', 'ALL', true, false)}
            className="bg-white p-4 rounded-xl border border-emerald-200 bg-emerald-50/15 hover:border-emerald-400 cursor-pointer transition shadow-2xs group"
          >
            <div className="flex items-center justify-between">
              <span className="text-[11px] font-bold text-emerald-800 uppercase tracking-wider flex items-center gap-1">
                <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
                Ready to Approve
              </span>
            </div>
            <div className="text-2xl font-bold text-emerald-950 mt-1.5 group-hover:text-emerald-700 transition">
              {metrics.ready_for_approval_count}
            </div>
            <span className="text-[10px] text-emerald-600 mt-0.5 block">0 blocking exceptions &rarr;</span>
          </div>

          {/* Card 2: Awaiting Review / Under Evaluation */}
          <div
            onClick={() => handleFilterClick('UNDER_REVIEW', 'ALL', false, false)}
            className="bg-white p-4 rounded-xl border border-indigo-200 bg-indigo-50/15 hover:border-indigo-400 cursor-pointer transition shadow-2xs group"
          >
            <div className="flex items-center justify-between">
              <span className="text-[11px] font-bold text-indigo-800 uppercase tracking-wider flex items-center gap-1">
                <Clock className="w-3.5 h-3.5 text-indigo-600" />
                Under Review
              </span>
            </div>
            <div className="text-2xl font-bold text-indigo-950 mt-1.5 group-hover:text-indigo-700 transition">
              {metrics.awaiting_review_count}
            </div>
            <span className="text-[10px] text-indigo-600 mt-0.5 block">Active review queue &rarr;</span>
          </div>

          {/* Card 3: Critical / High Severity Issues */}
          <div
            onClick={() => handleFilterClick('ALL', 'HIGH', false, false)}
            className="bg-white p-4 rounded-xl border border-rose-200 bg-rose-50/15 hover:border-rose-400 cursor-pointer transition shadow-2xs group"
          >
            <div className="flex items-center justify-between">
              <span className="text-[11px] font-bold text-rose-800 uppercase tracking-wider flex items-center gap-1">
                <AlertTriangle className="w-3.5 h-3.5 text-rose-600" />
                High Severity Issues
              </span>
            </div>
            <div className="text-2xl font-bold text-rose-950 mt-1.5 group-hover:text-rose-700 transition">
              {metrics.high_severity_exceptions_count}
            </div>
            <span className="text-[10px] text-rose-600 mt-0.5 block">Statutory blocks &rarr;</span>
          </div>

          {/* Card 4: Action Required (Awaiting Vendor) */}
          <div
            onClick={() => handleFilterClick('ACTION_REQUIRED', 'ALL', false, false)}
            className="bg-white p-4 rounded-xl border border-amber-200 bg-amber-50/15 hover:border-amber-400 cursor-pointer transition shadow-2xs group"
          >
            <div className="flex items-center justify-between">
              <span className="text-[11px] font-bold text-amber-800 uppercase tracking-wider flex items-center gap-1">
                <Clock className="w-3.5 h-3.5 text-amber-600" />
                Clarification Pending
              </span>
            </div>
            <div className="text-2xl font-bold text-amber-950 mt-1.5 group-hover:text-amber-700 transition">
              {metrics.awaiting_vendor_count}
            </div>
            <span className="text-[10px] text-amber-600 mt-0.5 block">Vendor action required &rarr;</span>
          </div>

          {/* Card 5: Escalated to Admin */}
          <div
            onClick={() => handleFilterClick('ESCALATED', 'ALL', false, false)}
            className="bg-white p-4 rounded-xl border border-purple-200 bg-purple-50/15 hover:border-purple-400 cursor-pointer transition shadow-2xs group"
          >
            <div className="flex items-center justify-between">
              <span className="text-[11px] font-bold text-purple-800 uppercase tracking-wider flex items-center gap-1">
                <ShieldAlert className="w-3.5 h-3.5 text-purple-600" />
                Escalated to Admin
              </span>
            </div>
            <div className="text-2xl font-bold text-purple-950 mt-1.5 group-hover:text-purple-700 transition">
              {metrics.escalated_count}
            </div>
            <span className="text-[10px] text-purple-600 mt-0.5 block">Policy referrals &rarr;</span>
          </div>
        </div>
      )}

      {/* Primary Application Queue */}
      <div className="space-y-4">
        <div className="flex items-center justify-between border-b border-slate-200 pb-2">
          <div>
            <h3 className="text-base font-bold text-slate-900">Application Evaluation Queue</h3>
            <p className="text-xs text-slate-500">
              Select an entity to inspect statutory documents, 4-layer validation findings, sandbox registries, and execute decisions.
            </p>
          </div>
        </div>

        <ApplicationQueue
          initialStatus={queueStatusFilter}
          initialSeverity={queueSeverityFilter}
          initialReadyForApproval={queueReadyFilter}
          initialAssignedToMe={assignedToMeOnly}
          onSelectApplication={(appId) => setSelectedApplicationId(appId)}
        />
      </div>
    </div>
  );
};
