import React, { useState, useEffect } from 'react';
import { useAuth } from '../../context/AuthContext';
import type { Application } from '../../types/application';
import type { ExternalVerificationRecord, DuplicateSignal, AuditEvent } from '../../types/validation';
import { apiListApplications } from '../../api/applications';
import {
  apiFetchVerifications,
  apiFetchDuplicateSignals,
  apiDismissDuplicateSignal,
  apiFetchAuditTrail,
} from '../../api/validation';
import { ValidationFindingsCard } from '../vendor/ValidationFindingsCard';
import { ExceptionManagerCard } from '../reviewer/ExceptionManagerCard';
import {
  UserCheck,
  AlertTriangle,
  CheckCircle2,
  Clock,
  ShieldCheck,
  ChevronRight,
  History,
  AlertOctagon,
} from 'lucide-react';

export const ReviewerDashboard: React.FC = () => {
  const { user, token } = useAuth();
  const [applications, setApplications] = useState<Application[]>([]);
  const [selectedApp, setSelectedApp] = useState<Application | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Inspection Drawer tabs: EXCEPTIONS, VALIDATION, REGISTRIES, DUPLICATES, AUDIT
  const [activeTab, setActiveTab] = useState<'EXCEPTIONS' | 'VALIDATION' | 'REGISTRIES' | 'DUPLICATES' | 'AUDIT'>('EXCEPTIONS');
  const [verifications, setVerifications] = useState<ExternalVerificationRecord[]>([]);
  const [duplicateSignals, setDuplicateSignals] = useState<DuplicateSignal[]>([]);
  const [auditEvents, setAuditEvents] = useState<AuditEvent[]>([]);

  const loadApplications = async () => {
    if (!token) return;
    try {
      setLoading(true);
      setError(null);
      const data = await apiListApplications(token);
      setApplications(data);
      if (data.length > 0 && !selectedApp) {
        setSelectedApp(data[0]);
      }
    } catch (err: any) {
      setError(err.message || 'Failed to load applications');
    } finally {
      setLoading(false);
    }
  };

  const loadInspectionDetails = async (appId: string) => {
    if (!token) return;
    try {
      const [vData, dData, aData] = await Promise.all([
        apiFetchVerifications(token, appId).catch(() => []),
        apiFetchDuplicateSignals(token, appId).catch(() => []),
        apiFetchAuditTrail(token, appId).catch(() => []),
      ]);
      setVerifications(vData);
      setDuplicateSignals(dData);
      setAuditEvents(aData);
    } catch (err: any) {
      console.error('Failed to load inspection details', err);
    }
  };

  const handleDismissDuplicate = async (signalId: string) => {
    if (!token || !selectedApp) return;
    try {
      await apiDismissDuplicateSignal(token, selectedApp.id, signalId);
      loadInspectionDetails(selectedApp.id);
    } catch (err: any) {
      alert(`Error dismissing signal: ${err.message}`);
    }
  };

  useEffect(() => {
    loadApplications();
  }, [token]);

  useEffect(() => {
    if (selectedApp) {
      loadInspectionDetails(selectedApp.id);
    }
  }, [selectedApp, token]);

  const submittedCount = applications.filter((a) => a.status === 'SUBMITTED').length;
  const inProgressCount = applications.filter((a) => a.status === 'IN_PROGRESS' || a.status === 'DRAFT').length;

  return (
    <div className="space-y-6">
      {/* Header Banner */}
      <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-2xs">
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-amber-50 text-amber-800 border border-amber-200 flex items-center justify-center">
              <UserCheck className="w-6 h-6" />
            </div>
            <div>
              <h2 className="text-xl font-bold text-slate-900">Reviewer & Approver Workspace</h2>
              <p className="text-xs text-slate-500">
                Evaluation queue for <span className="font-semibold text-slate-700">{user?.organisation.name}</span> &bull;{' '}
                Deterministic validation inspection & simulated registries
              </p>
            </div>
          </div>
          <div className="px-3 py-1.5 rounded-lg bg-amber-50 border border-amber-200 text-xs font-semibold text-amber-900">
            Audit Authority Active
          </div>
        </div>
      </div>

      {error && (
        <div className="p-4 bg-rose-50 border border-rose-200 rounded-xl text-rose-800 text-xs font-medium">
          {error}
        </div>
      )}

      {/* Metric Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div className="bg-white p-5 rounded-xl border border-slate-200">
          <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider flex items-center gap-1.5">
            <Clock className="w-3.5 h-3.5 text-amber-500" />
            Pending Verification Inspection
          </span>
          <div className="text-2xl font-bold text-slate-900 mt-2">{submittedCount}</div>
          <div className="text-[11px] text-slate-400 mt-1">Submitted vendor applications</div>
        </div>

        <div className="bg-white p-5 rounded-xl border border-slate-200">
          <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider flex items-center gap-1.5">
            <AlertTriangle className="w-3.5 h-3.5 text-rose-500" />
            Drafts In Progress
          </span>
          <div className="text-2xl font-bold text-slate-900 mt-2">{inProgressCount}</div>
          <div className="text-[11px] text-slate-400 mt-1">Vendors completing checklist</div>
        </div>

        <div className="bg-white p-5 rounded-xl border border-slate-200">
          <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider flex items-center gap-1.5">
            <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500" />
            Total Onboarding Queue
          </span>
          <div className="text-2xl font-bold text-slate-900 mt-2">{applications.length}</div>
          <div className="text-[11px] text-slate-400 mt-1">Organisational applications</div>
        </div>
      </div>

      {/* Main Reviewer Workspace Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column: Applications List */}
        <div className="bg-white rounded-xl border border-slate-200 shadow-2xs overflow-hidden flex flex-col">
          <div className="p-4 border-b border-slate-100 flex items-center justify-between">
            <h3 className="text-sm font-bold text-slate-900">Application Queue</h3>
            <span className="text-xs font-medium text-slate-500">{applications.length} entities</span>
          </div>

          {loading ? (
            <div className="p-8 text-center text-xs text-slate-500">Loading queue...</div>
          ) : applications.length === 0 ? (
            <div className="p-8 text-center text-xs text-slate-400">No applications registered.</div>
          ) : (
            <div className="divide-y divide-slate-100 overflow-y-auto max-h-[600px]">
              {applications.map((app) => (
                <button
                  key={app.id}
                  onClick={() => setSelectedApp(app)}
                  className={`w-full text-left p-4 hover:bg-slate-50 transition flex items-center justify-between ${
                    selectedApp?.id === app.id ? 'bg-indigo-50/70 border-l-4 border-indigo-600' : ''
                  }`}
                >
                  <div>
                    <span className="text-xs font-mono font-bold text-indigo-700">{app.reference_number}</span>
                    <h4 className="text-sm font-bold text-slate-900 line-clamp-1">{app.legal_name || 'Untitled Vendor'}</h4>
                    <div className="flex items-center gap-2 mt-1 text-[11px] text-slate-500">
                      <span>{app.constitution.replace('_', ' ')}</span>
                      <span>&bull;</span>
                      <span className={`font-semibold ${app.status === 'SUBMITTED' ? 'text-amber-700' : 'text-slate-600'}`}>
                        {app.status}
                      </span>
                    </div>
                  </div>
                  <ChevronRight className="w-4 h-4 text-slate-400 shrink-0" />
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Right Column: Selected Application Inspection Workspace */}
        <div className="lg:col-span-2 space-y-4">
          {selectedApp ? (
            <div className="space-y-4">
              {/* Selected Entity Card */}
              <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-2xs">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-slate-100 pb-3">
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-mono font-bold px-2 py-0.5 bg-indigo-50 text-indigo-700 rounded border border-indigo-200">
                        {selectedApp.reference_number}
                      </span>
                      <span className="text-xs font-semibold px-2 py-0.5 bg-slate-100 text-slate-700 rounded">
                        {selectedApp.status}
                      </span>
                    </div>
                    <h3 className="text-base font-bold text-slate-900 mt-1">{selectedApp.legal_name}</h3>
                  </div>
                  <div className="text-xs text-slate-500 font-mono">
                    PAN: <span className="font-bold text-slate-800">{selectedApp.pan || '—'}</span> &bull; GSTIN:{' '}
                    <span className="font-bold text-slate-800">{selectedApp.gstin || '—'}</span>
                  </div>
                </div>

                {/* Sub-Navigation Tabs */}
                <div className="flex gap-2 pt-3 text-xs font-semibold border-b border-slate-100 overflow-x-auto">
                  <button
                    onClick={() => setActiveTab('EXCEPTIONS')}
                    className={`pb-2 px-2 border-b-2 transition whitespace-nowrap ${
                      activeTab === 'EXCEPTIONS'
                        ? 'border-indigo-600 text-indigo-700'
                        : 'border-transparent text-slate-500 hover:text-slate-800'
                    }`}
                  >
                    Exceptions &amp; Clarifications
                  </button>
                  <button
                    onClick={() => setActiveTab('VALIDATION')}
                    className={`pb-2 px-2 border-b-2 transition whitespace-nowrap ${
                      activeTab === 'VALIDATION'
                        ? 'border-indigo-600 text-indigo-700'
                        : 'border-transparent text-slate-500 hover:text-slate-800'
                    }`}
                  >
                    4-Layer Validation Findings
                  </button>
                  <button
                    onClick={() => setActiveTab('REGISTRIES')}
                    className={`pb-2 px-2 border-b-2 transition ${
                      activeTab === 'REGISTRIES'
                        ? 'border-indigo-600 text-indigo-700'
                        : 'border-transparent text-slate-500 hover:text-slate-800'
                    }`}
                  >
                    Simulated Registries ({verifications.length})
                  </button>
                  <button
                    onClick={() => setActiveTab('DUPLICATES')}
                    className={`pb-2 px-2 border-b-2 transition ${
                      activeTab === 'DUPLICATES'
                        ? 'border-indigo-600 text-indigo-700'
                        : 'border-transparent text-slate-500 hover:text-slate-800'
                    }`}
                  >
                    Duplicate Signals ({duplicateSignals.length})
                  </button>
                  <button
                    onClick={() => setActiveTab('AUDIT')}
                    className={`pb-2 px-2 border-b-2 transition ${
                      activeTab === 'AUDIT'
                        ? 'border-indigo-600 text-indigo-700'
                        : 'border-transparent text-slate-500 hover:text-slate-800'
                    }`}
                  >
                    Audit Trail ({auditEvents.length})
                  </button>
                </div>
              </div>

              {/* Tab 0: Exception Management & Clarifications */}
              {activeTab === 'EXCEPTIONS' && (
                <ExceptionManagerCard applicationId={selectedApp.id} isReviewer={true} />
              )}

              {/* Tab 1: Validation Engine Findings Card */}
              {activeTab === 'VALIDATION' && token && (
                <ValidationFindingsCard token={token} applicationId={selectedApp.id} isReviewerView={true} />
              )}

              {/* Tab 2: Simulated External Registries */}
              {activeTab === 'REGISTRIES' && (
                <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-2xs space-y-4">
                  <div className="flex items-center justify-between border-b border-slate-100 pb-3">
                    <div>
                      <h4 className="text-sm font-bold text-slate-900 flex items-center gap-1.5">
                        <ShieldCheck className="w-4 h-4 text-indigo-600" />
                        External Registry Authoritative Verifications
                      </h4>
                      <p className="text-xs text-slate-500 mt-0.5">
                        Authoritative third-party query records executed in deterministic sandbox environment.
                      </p>
                    </div>
                    <span className="text-[11px] font-bold px-2 py-0.5 bg-amber-100 text-amber-800 rounded border border-amber-200">
                      SIMULATED SANDBOX
                    </span>
                  </div>

                  {verifications.length === 0 ? (
                    <div className="text-center py-8 text-xs text-slate-400">
                      No external registry queries recorded yet. Trigger validation to run authoritative queries.
                    </div>
                  ) : (
                    <div className="space-y-3">
                      {verifications.map((v) => (
                        <div key={v.id} className="p-3.5 rounded-lg border border-slate-200 bg-slate-50/60 text-xs space-y-2">
                          <div className="flex items-center justify-between">
                            <div className="flex items-center space-x-2">
                              <span className="font-bold text-slate-900 uppercase">{v.verification_type}</span>
                              <span
                                className={`px-2 py-0.5 rounded font-semibold text-[10px] ${
                                  v.status === 'VERIFIED'
                                    ? 'bg-emerald-100 text-emerald-800 border border-emerald-200'
                                    : v.status === 'FAILED'
                                    ? 'bg-rose-100 text-rose-800 border border-rose-200'
                                    : 'bg-sky-100 text-sky-800 border border-sky-200'
                                }`}
                              >
                                {v.status}
                              </span>
                              <span className="text-slate-400 font-mono text-[10px]">{v.request_id}</span>
                            </div>
                            <span className="text-slate-500 font-mono text-[11px]">{v.duration_ms} ms</span>
                          </div>
                          <div className="text-slate-600">
                            <strong>Provider:</strong> {v.provider_name}
                          </div>
                          <div className="text-slate-600">
                            <strong>Target Identifier:</strong> <span className="font-mono">{v.submitted_identifier}</span>
                          </div>
                          {v.reason && (
                            <div className="text-slate-500 italic">
                              <strong>Outcome:</strong> {v.reason}
                            </div>
                          )}
                          {v.returned_attributes && Object.keys(v.returned_attributes).length > 0 && (
                            <pre className="p-2 bg-slate-900 text-slate-100 rounded text-[11px] overflow-x-auto font-mono mt-1">
                              {JSON.stringify(v.returned_attributes, null, 2)}
                            </pre>
                          )}
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}

              {/* Tab 3: Duplicate Candidate Signals */}
              {activeTab === 'DUPLICATES' && (
                <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-2xs space-y-4">
                  <div className="flex items-center justify-between border-b border-slate-100 pb-3">
                    <div>
                      <h4 className="text-sm font-bold text-slate-900 flex items-center gap-1.5">
                        <AlertOctagon className="w-4 h-4 text-orange-600" />
                        Organisation Duplicate Candidate Signals
                      </h4>
                      <p className="text-xs text-slate-500 mt-0.5">
                        Detects matching PAN, GSTIN, CIN, bank account, or entity name strictly within this organisation.
                      </p>
                    </div>
                  </div>

                  {duplicateSignals.length === 0 ? (
                    <div className="text-center py-8 text-xs text-slate-400">
                      No duplicate vendor candidates detected for this application.
                    </div>
                  ) : (
                    <div className="space-y-3">
                      {duplicateSignals.map((sig) => (
                        <div
                          key={sig.id}
                          className={`p-4 rounded-xl border text-xs space-y-2 ${
                            sig.is_dismissed
                              ? 'bg-slate-50 border-slate-200 opacity-60'
                              : sig.match_strength === 'STRONG'
                              ? 'bg-rose-50 border-rose-200'
                              : 'bg-amber-50 border-amber-200'
                          }`}
                        >
                          <div className="flex items-center justify-between">
                            <div className="flex items-center space-x-2">
                              <span
                                className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                                  sig.match_strength === 'STRONG'
                                    ? 'bg-rose-600 text-white'
                                    : 'bg-amber-600 text-white'
                                }`}
                              >
                                {sig.match_strength} DUPLICATE MATCH
                              </span>
                              {sig.is_dismissed && (
                                <span className="px-2 py-0.5 bg-slate-200 text-slate-700 font-bold text-[10px] rounded">
                                  DISMISSED BY REVIEWER
                                </span>
                              )}
                            </div>
                            {!sig.is_dismissed && (
                              <button
                                onClick={() => handleDismissDuplicate(sig.id)}
                                className="px-2.5 py-1 bg-white hover:bg-slate-100 text-slate-700 rounded border border-slate-300 font-semibold text-[11px] transition"
                              >
                                Dismiss Flag
                              </button>
                            )}
                          </div>

                          <p className="text-slate-800 font-medium">{sig.explanation}</p>
                          <div className="text-slate-600">
                            <strong>Recommended Action:</strong> {sig.recommended_action}
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}

              {/* Tab 4: Immutable Audit Trail */}
              {activeTab === 'AUDIT' && (
                <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-2xs space-y-4">
                  <div className="flex items-center justify-between border-b border-slate-100 pb-3">
                    <div>
                      <h4 className="text-sm font-bold text-slate-900 flex items-center gap-1.5">
                        <History className="w-4 h-4 text-indigo-600" />
                        Application Audit Trail
                      </h4>
                      <p className="text-xs text-slate-500 mt-0.5">
                        Immutable event log recording validation runs, external verifications, and user actions.
                      </p>
                    </div>
                  </div>

                  {auditEvents.length === 0 ? (
                    <div className="text-center py-8 text-xs text-slate-400">No audit events recorded yet.</div>
                  ) : (
                    <div className="divide-y divide-slate-100">
                      {auditEvents.map((evt) => (
                        <div key={evt.id} className="py-2.5 flex items-start justify-between text-xs">
                          <div>
                            <span className="font-mono font-bold text-slate-900">{evt.event_type}</span>
                            <span className="text-slate-400 text-[11px] ml-2">by {evt.actor_role || 'SYSTEM'}</span>
                            {evt.details && (
                              <pre className="mt-1 text-[10px] text-slate-600 font-mono bg-slate-50 p-1.5 rounded">
                                {JSON.stringify(evt.details)}
                              </pre>
                            )}
                          </div>
                          <span className="text-[11px] text-slate-400 font-mono shrink-0">
                            {new Date(evt.created_at).toLocaleString()}
                          </span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </div>
          ) : (
            <div className="p-12 text-center bg-white rounded-xl border border-slate-200 text-slate-400 text-xs">
              Select an application from the queue to inspect validation findings.
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
