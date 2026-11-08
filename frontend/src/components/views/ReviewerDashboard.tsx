import React, { useState, useEffect } from 'react';
import { useAuth } from '../../context/AuthContext';
import { apiGetDashboardMetrics } from '../../api/queue';
import type { DashboardMetrics } from '../../types/queue';
import { ApplicationQueue } from '../queue/ApplicationQueue';
import { ApplicationDetailsWorkspace } from '../review/ApplicationDetailsWorkspace';
import {
  CheckCircle2,
  AlertTriangle,
  Clock,
  ShieldAlert,
  RefreshCw,
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
      <div className="border-b border-slate-200 pb-5 pt-2">
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div>
              <p className="text-xs uppercase tracking-[0.16em] font-semibold text-indigo-700 mb-1">Review desk</p>
              <h2 className="text-2xl font-semibold text-slate-900">Application decisions</h2>
              <p className="text-sm text-slate-600 mt-1">
                Compare submitted details with documents and record a decision for {user?.organisation.name}
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
              <span>Refresh</span>
            </button>
          </div>
        </div>
      </div>

      {/* Reviewer Priority Metric Cards */}
      {metrics && (
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-px bg-slate-200 border border-slate-200 rounded-lg overflow-hidden">
          {/* Card 1: Ready for Approval */}
          <div
            onClick={() => handleFilterClick('ALL', 'ALL', true, false)}
            className="bg-white p-4 hover:bg-slate-50 cursor-pointer transition group"
          >
            <div className="flex items-center justify-between">
              <span className="text-xs font-medium text-slate-600 flex items-center gap-1">
                <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
                Ready to Approve
              </span>
            </div>
            <div className="text-2xl font-semibold text-slate-900 mt-1.5">
              {metrics.ready_for_approval_count}
            </div>
            <span className="text-xs text-slate-500 mt-0.5 block">Open ready cases &rarr;</span>
          </div>

          {/* Card 2: Awaiting Review / Under Evaluation */}
          <div
            onClick={() => handleFilterClick('UNDER_REVIEW', 'ALL', false, false)}
            className="bg-white p-4 hover:bg-slate-50 cursor-pointer transition group"
          >
            <div className="flex items-center justify-between">
              <span className="text-xs font-medium text-slate-600 flex items-center gap-1">
                <Clock className="w-3.5 h-3.5 text-indigo-600" />
                Under Review
              </span>
            </div>
            <div className="text-2xl font-semibold text-slate-900 mt-1.5">
              {metrics.awaiting_review_count}
            </div>
            <span className="text-xs text-slate-500 mt-0.5 block">Waiting for review &rarr;</span>
          </div>

          {/* Card 3: Critical / High Severity Issues */}
          <div
            onClick={() => handleFilterClick('ALL', 'HIGH', false, false)}
            className="bg-white p-4 hover:bg-slate-50 cursor-pointer transition group"
          >
            <div className="flex items-center justify-between">
              <span className="text-xs font-medium text-slate-600 flex items-center gap-1">
                <AlertTriangle className="w-3.5 h-3.5 text-rose-600" />
                High Severity Issues
              </span>
            </div>
            <div className="text-2xl font-semibold text-slate-900 mt-1.5">
              {metrics.high_severity_exceptions_count}
            </div>
            <span className="text-xs text-slate-500 mt-0.5 block">Needs investigation &rarr;</span>
          </div>

          {/* Card 4: Action Required (Awaiting Vendor) */}
          <div
            onClick={() => handleFilterClick('ACTION_REQUIRED', 'ALL', false, false)}
            className="bg-white p-4 hover:bg-slate-50 cursor-pointer transition group"
          >
            <div className="flex items-center justify-between">
              <span className="text-xs font-medium text-slate-600 flex items-center gap-1">
                <Clock className="w-3.5 h-3.5 text-amber-600" />
                Clarification Pending
              </span>
            </div>
            <div className="text-2xl font-semibold text-slate-900 mt-1.5">
              {metrics.awaiting_vendor_count}
            </div>
            <span className="text-xs text-slate-500 mt-0.5 block">Waiting on vendors &rarr;</span>
          </div>

          {/* Card 5: Escalated to Admin */}
          <div
            onClick={() => handleFilterClick('ESCALATED', 'ALL', false, false)}
            className="bg-white p-4 hover:bg-slate-50 cursor-pointer transition group"
          >
            <div className="flex items-center justify-between">
              <span className="text-xs font-medium text-slate-600 flex items-center gap-1">
                <ShieldAlert className="w-3.5 h-3.5 text-purple-600" />
                Escalated to Admin
              </span>
            </div>
            <div className="text-2xl font-semibold text-slate-900 mt-1.5">
              {metrics.escalated_count}
            </div>
            <span className="text-xs text-slate-500 mt-0.5 block">Policy review &rarr;</span>
          </div>
        </div>
      )}

      {/* Primary Application Queue */}
      <div className="space-y-4">
        <div className="flex items-center justify-between border-b border-slate-200 pb-2">
          <div>
            <h3 className="text-lg font-semibold text-slate-900">Applications</h3>
            <p className="text-sm text-slate-600">
              Open a case to compare evidence, see exceptions, and record the next decision.
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
