import { focusCaseQueue } from '../../utils/focusCaseQueue';
import React, { useEffect, useState } from 'react';
import { useAuth } from '../../context/AuthContext';
import { apiResetDemo } from '../../api/client';
import { apiGetDashboardMetrics } from '../../api/queue';
import type { DashboardMetrics } from '../../types/queue';
import { ApplicationQueue } from '../queue/ApplicationQueue';
import { ApplicationDetailsWorkspace } from '../review/ApplicationDetailsWorkspace';
import {
  ShieldCheck,
  RotateCcw,
  CheckCircle2,
  AlertTriangle,
} from 'lucide-react';

export const AdminDashboard: React.FC = () => {
  const { user, token } = useAuth();
  const [selectedApplicationId, setSelectedApplicationId] = useState<string | null>(null);
  const [selectedApplicationTab, setSelectedApplicationTab] = useState<'OVERVIEW' | 'EXCEPTIONS'>('OVERVIEW');
  const [isResetting, setIsResetting] = useState<boolean>(false);
  const [resetResult, setResetResult] = useState<any | null>(null);
  const [resetError, setResetError] = useState<string | null>(null);
  const [metrics, setMetrics] = useState<DashboardMetrics | null>(null);
  const [queueStatusFilter, setQueueStatusFilter] = useState<string>('ALL');
  const [queueRevision, setQueueRevision] = useState(0);
  const [queueSeverityFilter, setQueueSeverityFilter] = useState<string>('ALL');

  useEffect(() => {
    if (!token) return;
    apiGetDashboardMetrics(token).then(setMetrics).catch((err) => console.error('Failed to load administrator overview', err));
  }, [token]);

  useEffect(() => {
    const openApplication = (event: Event) => {
      const { applicationId, initialTab } = (event as CustomEvent<{ applicationId?: string; initialTab?: 'OVERVIEW' | 'EXCEPTIONS'; restore?: boolean }>).detail || {};
      if (!applicationId && (event as CustomEvent).detail?.restore) setSelectedApplicationId(null);
      if (applicationId) {
        setSelectedApplicationTab(initialTab || 'OVERVIEW');
        setSelectedApplicationId(applicationId);
      }
    };
    window.addEventListener('vop:open-application', openApplication);
    return () => window.removeEventListener('vop:open-application', openApplication);
  }, []);

  const handleResetDemo = async () => {
    if (!token) return;
    if (!window.confirm('Reset demo environment? This will re-seed pristine demo accounts, 3 standard test cases, and synthetic documents.')) {
      return;
    }
    setIsResetting(true);
    setResetError(null);
    try {
      const res = await apiResetDemo(token);
      setResetResult(res);
    } catch (err: any) {
      setResetError(err?.message || 'Failed to reset demo environment.');
    } finally {
      setIsResetting(false);
    }
  };

  if (selectedApplicationId) {
    return (
      <ApplicationDetailsWorkspace
        applicationId={selectedApplicationId}
        initialTab={selectedApplicationTab}
        onBack={() => { window.history.replaceState({}, '', window.location.pathname); setSelectedApplicationId(null); setSelectedApplicationTab('OVERVIEW'); }}
        onActionComplete={() => { setSelectedApplicationId(null); setQueueRevision(value => value + 1); if (token) apiGetDashboardMetrics(token).then(setMetrics); }}
        isReviewer={true}
      />
    );
  }

  return (
    <div className="space-y-6">
      {/* Banner */}
      <div className="relative overflow-hidden rounded-3xl border border-[#315240] bg-[#19382b] p-6 text-[#f7f5ec] shadow-lg sm:p-7">
        <div aria-hidden="true" className="pointer-events-none absolute -right-12 -top-24 h-64 w-64 rounded-full border border-white/10" />
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-white/10 text-[#e7c978] border border-white/15 flex items-center justify-center">
              <ShieldCheck className="w-6 h-6" />
            </div>
            <div>
              <p className="mb-1 text-[10px] font-bold uppercase tracking-[0.2em] text-[#d9bd72]">Organisation oversight</p>
              <h2 className="font-serif text-2xl font-medium tracking-tight text-white sm:text-3xl">Keep every case accountable.</h2>
              <p className="mt-1 text-sm text-[#d5e0d7]">
                Review ownership, support escalations and maintain a clear decision trail for <span className="font-semibold text-white">{user?.organisation.name}</span>.
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            {import.meta.env.DEV && <button
              onClick={handleResetDemo}
              disabled={isResetting}
              className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-lg text-xs font-semibold text-white bg-purple-600 hover:bg-purple-700 shadow-xs transition disabled:opacity-50"
            >
              <RotateCcw className={`w-3.5 h-3.5 ${isResetting ? 'animate-spin' : ''}`} />
              <span>{isResetting ? 'Resetting Demo...' : 'Reset & Re-Seed Demo'}</span>
            </button>}
            <div className="rounded-full border border-white/20 bg-white/10 px-3 py-1.5 text-xs font-semibold text-[#f3e6bc]">
              Administrator
            </div>
          </div>
        </div>
      </div>

      {resetError && (
        <div className="p-3 bg-rose-50 border border-rose-200 text-rose-800 text-xs rounded-xl flex items-center gap-2">
          <AlertTriangle className="w-4 h-4 text-rose-600 shrink-0" />
          <span>{resetError}</span>
        </div>
      )}

      {resetResult && (
        <div className="bg-emerald-50 border border-emerald-200 rounded-xl p-5 text-xs text-emerald-900 space-y-3">
          <div className="flex items-center justify-between">
            <div className="font-bold flex items-center gap-1.5 text-emerald-800">
              <CheckCircle2 className="w-4 h-4 text-emerald-600" />
              <span>Demo Environment Reset &amp; Seeded Successfully!</span>
            </div>
            <button
              onClick={() => setResetResult(null)}
              className="text-emerald-700 hover:text-emerald-900 font-bold"
            >
              &times;
            </button>
          </div>
          <p className="text-emerald-700">
            3 repeatable demonstration cases have been restored with synthetic compliance documents, OCR findings, and verification records:
          </p>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3 pt-1">
            <div className="bg-white p-3 rounded-lg border border-emerald-200 space-y-1">
              <span className="font-bold text-slate-900 block">Case 1: Clean Application</span>
              <span className="font-mono text-[11px] text-indigo-700 font-semibold block">APP-2026-CLEAN-001</span>
              <span className="text-[11px] text-slate-500 block">Tata Industrial Supplies Pvt Ltd</span>
              <span className="px-2 py-0.5 rounded bg-emerald-100 text-emerald-800 font-bold text-[10px] inline-block mt-1">
                Policy Gate: PASS
              </span>
            </div>
            <div className="bg-white p-3 rounded-lg border border-emerald-200 space-y-1">
              <span className="font-bold text-slate-900 block">Case 2: Correction Mismatch</span>
              <span className="font-mono text-[11px] text-indigo-700 font-semibold block">APP-2026-MISM-002</span>
              <span className="text-[11px] text-slate-500 block">Sharma Engineering Works</span>
              <span className="px-2 py-0.5 rounded bg-amber-100 text-amber-800 font-bold text-[10px] inline-block mt-1">
                Bank Mismatch Exception
              </span>
            </div>
            <div className="bg-white p-3 rounded-lg border border-emerald-200 space-y-1">
              <span className="font-bold text-slate-900 block">Case 3: Unresolved Verification</span>
              <span className="font-mono text-[11px] text-indigo-700 font-semibold block">APP-2026-WARN-003</span>
              <span className="text-[11px] text-slate-500 block">Apex Logistics &amp; Cargo LLP</span>
              <span className="px-2 py-0.5 rounded bg-rose-100 text-rose-800 font-bold text-[10px] inline-block mt-1">
                Provider Timeout &amp; Duplicate Flag
              </span>
            </div>
          </div>
        </div>
      )}

      {metrics && (
        <section className="relative overflow-hidden rounded-3xl border border-[#dcd8ca] bg-[#f3f0e6] p-5 sm:p-7" aria-label="Organisation workload">
          <div aria-hidden="true" className="pointer-events-none absolute -right-10 -top-24 h-64 w-64 rounded-full border border-[#315240]/10" />
          <div className="relative flex flex-wrap items-end justify-between gap-4">
            <div>
              <p className="text-[10px] font-bold uppercase tracking-[0.22em] text-[#65766a]">Organisation overview</p>
              <h3 className="mt-1 font-serif text-2xl text-[#243b2f] sm:text-3xl">Where attention is needed</h3>
              <p className="mt-1 text-sm text-slate-600">Open a group to review its cases and confirm ownership.</p>
            </div>
            <span className="rounded-full border border-[#c9c2af] bg-white/70 px-3 py-1.5 text-xs text-[#4b5b4e]">{metrics.total_applications} applications in this organisation</span>
          </div>
          <div className="relative mt-6 grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-4">
            <div aria-hidden="true" className="absolute left-[8%] right-[8%] top-6 hidden border-t border-dashed border-[#8f967f] xl:block" />
            {[
              { label: 'Awaiting review', note: 'Cases still need assessment', count: metrics.awaiting_review_count, action: () => { setQueueStatusFilter('AWAITING_REVIEW'); setQueueSeverityFilter('ALL'); }, tone: 'border-[#788c78]/35 bg-white/75' },
              { label: 'Escalated', note: 'Policy or authority question', count: metrics.escalated_count, action: () => { setQueueStatusFilter('ESCALATED'); setQueueSeverityFilter('ALL'); }, tone: 'border-[#c7ae73]/45 bg-[#fbf5e5]' },
              { label: 'Waiting over 3 days', note: 'Check the next owner', count: metrics.stale_review_count, action: () => { setQueueStatusFilter('OVERDUE_REVIEW'); setQueueSeverityFilter('ALL'); }, tone: 'border-[#d79d89]/40 bg-[#fbefeb]' },
              { label: 'High priority issues', note: 'Review potential blockers', count: metrics.high_severity_exceptions_count, action: () => { setQueueStatusFilter('ALL'); setQueueSeverityFilter('HIGH'); }, tone: 'border-[#d79d89]/50 bg-white/80' },
            ].map((stage, index) => (
              <button key={stage.label} onClick={() => { stage.action(); focusCaseQueue(); }} style={{ animationDelay: `${index * 70}ms` }} className={`group relative min-h-28 animate-[stage-arrive_420ms_cubic-bezier(0.2,0.7,0.2,1)_both] rounded-2xl border p-4 text-left transition duration-200 hover:-translate-y-1 hover:shadow-md focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#315240] motion-reduce:animate-none motion-reduce:transform-none motion-reduce:transition-none ${stage.tone}`}>
                <span className="flex items-center justify-between">
                  <span className="text-xs font-semibold text-[#34483a]">{stage.label}</span>
                </span>
                <span className="mt-3 flex items-end justify-between gap-2">
                  <span className="font-serif text-4xl leading-none tabular-nums text-[#243b2f]">{stage.count}</span>
                  <span className="text-right text-[10px] text-slate-600">{stage.note}</span>
                </span>
              </button>
            ))}
          </div>
        </section>
      )}

      {/* Organisation Applications Queue for Administrative Oversight */}
      <div className="space-y-3">
        <div className="flex items-center justify-between border-b border-slate-200 pb-2">
          <div>
            <h3 className="text-base font-bold text-slate-900">All supplier applications</h3>
            <p className="text-xs text-slate-500">
              Complete view of organisational applications including escalated files, pending reviews, and reviewer assignments.
            </p>
          </div>
        </div>

        <ApplicationQueue
          key={`${queueRevision}-${queueStatusFilter}-${queueSeverityFilter}`}
          initialStatus={queueStatusFilter}
          initialSeverity={queueSeverityFilter}
          onSelectApplication={(appId) => {
            setSelectedApplicationTab('OVERVIEW');
            setSelectedApplicationId(appId);
          }}
        />
      </div>
    </div>
  );
};
