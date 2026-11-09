import React, { useState, useEffect } from 'react';
import { useAuth } from '../../context/AuthContext';
import { apiGetDashboardMetrics } from '../../api/queue';
import type { DashboardMetrics } from '../../types/queue';
import { ApplicationQueue } from '../queue/ApplicationQueue';
import { ApplicationDetailsWorkspace } from '../review/ApplicationDetailsWorkspace';
import {
  AlertTriangle,
  RefreshCw,
} from 'lucide-react';

export const ReviewerDashboard: React.FC = () => {
  const { user, token } = useAuth();
  const [selectedApplicationId, setSelectedApplicationId] = useState<string | null>(null);
  const [selectedApplicationTab, setSelectedApplicationTab] = useState<'OVERVIEW' | 'EXCEPTIONS'>('OVERVIEW');

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

  useEffect(() => {
    const openApplication = (event: Event) => {
      const { applicationId, initialTab } = (event as CustomEvent<{ applicationId?: string; initialTab?: 'OVERVIEW' | 'EXCEPTIONS' }>).detail || {};
      if (applicationId) {
        setSelectedApplicationTab(initialTab || 'OVERVIEW');
        setSelectedApplicationId(applicationId);
      }
    };
    window.addEventListener('vop:open-application', openApplication);
    return () => window.removeEventListener('vop:open-application', openApplication);
  }, []);

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
        initialTab={selectedApplicationTab}
        onBack={() => {
          setSelectedApplicationId(null);
          setSelectedApplicationTab('OVERVIEW');
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

      {/* Visual, state-backed review flow */}
      {metrics && (
        <section className="relative overflow-hidden rounded-3xl border border-[#315240] bg-[#19382b] p-5 text-[#f7f5ec] shadow-lg sm:p-7">
          <div aria-hidden="true" className="pointer-events-none absolute -right-10 -top-28 h-72 w-72 rounded-full border border-white/10" />
          <div aria-hidden="true" className="pointer-events-none absolute -right-2 -top-20 h-56 w-56 rounded-full border border-white/10" />
          <div className="relative flex flex-wrap items-end justify-between gap-4">
            <div>
              <p className="text-[10px] font-bold uppercase tracking-[0.22em] text-[#d9bd72]">Your review flow</p>
              <h3 className="mt-1 font-serif text-2xl font-medium sm:text-3xl">Move the work forward</h3>
              <p className="mt-1 max-w-xl text-sm text-[#d5e0d7]">Choose a stage to see the cases that need your attention.</p>
            </div>
            <div className="rounded-full border border-[#e9ca7b]/40 bg-[#e9ca7b]/10 px-3 py-1.5 text-xs text-[#f1dfae]">
              <span className="font-semibold">{metrics.high_severity_exceptions_count}</span> high priority items
            </div>
          </div>
          <div className="relative mt-7 grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-4">
            <div aria-hidden="true" className="absolute left-[9%] right-[9%] top-6 hidden border-t border-dashed border-[#e9ca7b]/50 xl:block" />
            {[
              { label: 'Awaiting review', note: 'Assess submitted evidence', count: metrics.awaiting_review_count, onClick: () => handleFilterClick('AWAITING_REVIEW'), tone: 'border-white/15 bg-white/[0.06]' },
              { label: 'Vendor response', note: 'Clarification requested', count: metrics.awaiting_vendor_count, onClick: () => handleFilterClick('ACTION_REQUIRED'), tone: 'border-[#e9ca7b]/35 bg-[#e9ca7b]/[0.09]' },
              { label: 'Ready to decide', note: 'No open blocking issues', count: metrics.ready_for_approval_count, onClick: () => handleFilterClick('ALL', 'ALL', true), tone: 'border-[#a8d3b4]/35 bg-[#a8d3b4]/[0.09]' },
              { label: 'Escalated', note: 'Needs policy oversight', count: metrics.escalated_count, onClick: () => handleFilterClick('ESCALATED'), tone: 'border-[#c4b5fd]/35 bg-[#c4b5fd]/[0.09]' },
            ].map((stage, index) => (
              <button
                key={stage.label}
                onClick={stage.onClick}
                style={{ animationDelay: `${index * 70}ms` }}
                className={`group relative min-h-28 animate-[stage-arrive_420ms_cubic-bezier(0.2,0.7,0.2,1)_both] rounded-2xl border p-4 text-left transition duration-200 hover:-translate-y-1 hover:bg-white/[0.12] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#f0cf78] motion-reduce:animate-none motion-reduce:transform-none motion-reduce:transition-none ${stage.tone}`}
              >
                <span className="flex items-center justify-between">
                  <span className="text-xs font-semibold text-[#edf1e9]">{stage.label}</span>
                  <span className="grid h-7 w-7 place-items-center rounded-full border border-[#f0cf78]/50 bg-[#19382b] text-[11px] font-bold text-[#f0cf78] transition-transform duration-300 group-hover:rotate-12 motion-reduce:transform-none motion-reduce:transition-none">{index + 1}</span>
                </span>
                <span className="mt-3 flex items-end justify-between gap-2">
                  <span className="font-serif text-4xl leading-none tabular-nums">{stage.count}</span>
                  <span className="text-right text-[10px] text-[#c5d5ca]">{stage.note}</span>
                </span>
              </button>
            ))}
          </div>
          <button
            onClick={() => handleFilterClick('ALL', 'HIGH')}
            className="relative mt-3 inline-flex items-center gap-2 rounded-full border border-[#ef9d8a]/35 bg-[#ef9d8a]/10 px-3 py-2 text-xs text-[#ffd0c4] transition hover:bg-[#ef9d8a]/20 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#f0cf78]"
          >
            <AlertTriangle className="h-3.5 w-3.5" />
            View {metrics.high_severity_exceptions_count} high severity findings
          </button>
        </section>
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
          onSelectApplication={(appId) => {
            setSelectedApplicationTab('OVERVIEW');
            setSelectedApplicationId(appId);
          }}
        />
      </div>
    </div>
  );
};
