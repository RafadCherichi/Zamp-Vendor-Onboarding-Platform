import React, { useState, useEffect } from 'react';
import {
  AlertTriangle,
  MessageSquare,
  Lock,
  RefreshCw,
  UserPlus,
  Filter,
  X,
  RotateCcw,
} from 'lucide-react';
import { exceptionsApi } from '../../api/exceptions';
import type {
  OnboardingException,
  ExceptionStatus,
  ExceptionSeverity,
  ResolutionType,
} from '../../types/exception';

interface ExceptionManagerCardProps {
  applicationId: string;
  isReviewer?: boolean;
}

export const ExceptionManagerCard: React.FC<ExceptionManagerCardProps> = ({
  applicationId,
  isReviewer = true,
}) => {
  const [exceptions, setExceptions] = useState<OnboardingException[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [syncing, setSyncing] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  // Filters
  const [statusFilter, setStatusFilter] = useState<string>('ALL');
  const [severityFilter, setSeverityFilter] = useState<string>('ALL');

  // Modals / active actions
  const [activeExcId, setActiveExcId] = useState<string | null>(null);
  const [actionType, setActionType] = useState<
    'REQUEST_CORRECTION' | 'RESOLVE' | 'REOPEN' | 'REASSIGN' | 'COMMENT' | null
  >(null);

  // Form states
  const [vendorInstruction, setVendorInstruction] = useState<string>('');
  const [resolutionType, setResolutionType] = useState<ResolutionType>('CORRECTED_BY_VENDOR');
  const [resolutionNotes, setResolutionNotes] = useState<string>('');
  const [reopenReason, setReopenReason] = useState<string>('');
  const [reassignRole, setReassignRole] = useState<string>('REVIEWER');
  const [commentMessage, setCommentMessage] = useState<string>('');
  const [isInternalComment, setIsInternalComment] = useState<boolean>(true);
  const [submittingAction, setSubmittingAction] = useState<boolean>(false);

  const fetchExceptions = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await exceptionsApi.getExceptions({ application_id: applicationId });
      setExceptions(data);
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Failed to load exceptions.');
    } finally {
      setLoading(false);
    }
  };

  const handleSyncExceptions = async () => {
    try {
      setSyncing(true);
      setError(null);
      const synced = await exceptionsApi.syncExceptions(applicationId);
      setExceptions(synced);
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Failed to sync exceptions from validation run.');
    } finally {
      setSyncing(false);
    }
  };

  useEffect(() => {
    if (applicationId) {
      fetchExceptions();
    }
  }, [applicationId]);

  const filteredExceptions = exceptions.filter((e) => {
    if (statusFilter !== 'ALL' && e.status !== statusFilter) return false;
    if (severityFilter !== 'ALL' && e.severity !== severityFilter) return false;
    return true;
  });

  const openActionModal = (
    exc: OnboardingException,
    type: 'REQUEST_CORRECTION' | 'RESOLVE' | 'REOPEN' | 'REASSIGN' | 'COMMENT'
  ) => {
    setActiveExcId(exc.id);
    setActionType(type);
    setError(null);
    setVendorInstruction(exc.vendor_action_instruction || '');
    setResolutionNotes('');
    setReopenReason('');
    setCommentMessage('');
    setIsInternalComment(true);
  };

  const closeActionModal = () => {
    setActiveExcId(null);
    setActionType(null);
    setError(null);
  };

  const executeAction = async () => {
    if (!activeExcId) return;
    try {
      setSubmittingAction(true);
      setError(null);

      if (actionType === 'REQUEST_CORRECTION') {
        if (!vendorInstruction.trim()) {
          setError('Please specify clear action instructions for the vendor.');
          return;
        }
        await exceptionsApi.transitionException(activeExcId, {
          target_status: 'ACTION_REQUIRED_FROM_VENDOR',
          vendor_action_instruction: vendorInstruction.trim(),
          notes: 'Clarification requested by compliance reviewer.',
        });
      } else if (actionType === 'RESOLVE') {
        await exceptionsApi.resolveException(activeExcId, {
          resolution_type: resolutionType,
          resolution_notes: resolutionNotes.trim() || undefined,
        });
      } else if (actionType === 'REOPEN') {
        if (!reopenReason.trim()) {
          setError('Mandatory justification is required to reopen an exception.');
          return;
        }
        await exceptionsApi.transitionException(activeExcId, {
          target_status: 'OPEN',
          reason: reopenReason.trim(),
          notes: 'Exception reopened for follow-up audit.',
        });
      } else if (actionType === 'REASSIGN') {
        await exceptionsApi.assignException(activeExcId, {
          assigned_role: reassignRole,
          reason: `Reassigned to ${reassignRole}`,
        });
      } else if (actionType === 'COMMENT') {
        if (!commentMessage.trim()) return;
        await exceptionsApi.addComment(activeExcId, {
          message: commentMessage.trim(),
          is_internal: isInternalComment,
        });
      }

      closeActionModal();
      fetchExceptions();
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Action failed.');
    } finally {
      setSubmittingAction(false);
    }
  };

  const getStatusColor = (status: ExceptionStatus) => {
    switch (status) {
      case 'ACTION_REQUIRED_FROM_VENDOR':
        return 'bg-amber-100 text-amber-800 border-amber-300';
      case 'RESPONSE_SUBMITTED':
        return 'bg-blue-100 text-blue-800 border-blue-300';
      case 'UNDER_REVIEW':
        return 'bg-purple-100 text-purple-800 border-purple-300';
      case 'RESOLVED':
        return 'bg-emerald-100 text-emerald-800 border-emerald-300';
      case 'CLOSED':
        return 'bg-slate-100 text-slate-700 border-slate-300';
      case 'ESCALATED':
        return 'bg-rose-100 text-rose-800 border-rose-300';
      default:
        return 'bg-slate-100 text-slate-800 border-slate-200';
    }
  };

  const getSeverityBadge = (sev: ExceptionSeverity) => {
    switch (sev) {
      case 'CRITICAL':
        return 'bg-rose-600 text-white';
      case 'HIGH':
        return 'bg-orange-500 text-white';
      case 'MEDIUM':
        return 'bg-amber-500 text-white';
      case 'LOW':
        return 'bg-slate-500 text-white';
    }
  };

  return (
    <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-2xs space-y-4">
      {/* Header Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-100 pb-3">
        <div>
          <h4 className="text-sm font-bold text-slate-900 flex items-center gap-1.5">
            <AlertTriangle className="w-4 h-4 text-amber-600" />
            Exception Management &amp; Vendor Clarifications ({exceptions.length})
          </h4>
          <p className="text-xs text-slate-500 mt-0.5">
            Traceable exception workflows, vendor correction requests, and selective revalidation.
          </p>
        </div>
        <button
          onClick={handleSyncExceptions}
          disabled={syncing}
          className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-slate-300 bg-slate-50 hover:bg-slate-100 text-xs font-semibold text-slate-700 transition disabled:opacity-50"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${syncing ? 'animate-spin' : ''}`} />
          <span>{syncing ? 'Syncing Findings...' : 'Sync Validation Findings'}</span>
        </button>
      </div>

      {error && (
        <div className="p-3 bg-rose-50 border border-rose-200 text-rose-800 rounded-lg text-xs font-medium">
          {error}
        </div>
      )}

      {/* Filter Controls */}
      <div className="flex flex-wrap items-center gap-3 pt-1 pb-2 text-xs">
        <div className="flex items-center gap-1.5 text-slate-600 font-medium">
          <Filter className="w-3.5 h-3.5" />
          <span>Status:</span>
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="px-2 py-1 rounded border border-slate-200 bg-slate-50 text-xs font-semibold focus:outline-none"
          >
            <option value="ALL">All Statuses ({exceptions.length})</option>
            <option value="OPEN">Open</option>
            <option value="ACTION_REQUIRED_FROM_VENDOR">Action Required from Vendor</option>
            <option value="RESPONSE_SUBMITTED">Response Submitted</option>
            <option value="UNDER_REVIEW">Under Review</option>
            <option value="RESOLVED">Resolved</option>
            <option value="CLOSED">Closed</option>
          </select>
        </div>

        <div className="flex items-center gap-1.5 text-slate-600 font-medium">
          <span>Severity:</span>
          <select
            value={severityFilter}
            onChange={(e) => setSeverityFilter(e.target.value)}
            className="px-2 py-1 rounded border border-slate-200 bg-slate-50 text-xs font-semibold focus:outline-none"
          >
            <option value="ALL">All Severities</option>
            <option value="CRITICAL">Critical</option>
            <option value="HIGH">High</option>
            <option value="MEDIUM">Medium</option>
            <option value="LOW">Low</option>
          </select>
        </div>
      </div>

      {/* Exceptions List */}
      {loading ? (
        <div className="text-center py-8 text-xs text-slate-400">Loading exceptions...</div>
      ) : filteredExceptions.length === 0 ? (
        <div className="text-center py-8 text-xs text-slate-400">
          No exceptions match the selected filter.
        </div>
      ) : (
        <div className="space-y-4">
          {filteredExceptions.map((exc) => (
            <div
              key={exc.id}
              className="p-4 rounded-xl border border-slate-200 bg-slate-50/40 text-xs space-y-3 transition hover:border-slate-300"
            >
              {/* Card Header */}
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div className="flex items-center gap-2">
                  <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${getSeverityBadge(exc.severity)}`}>
                    {exc.severity}
                  </span>
                  <span className={`px-2 py-0.5 rounded-full text-[11px] font-bold border ${getStatusColor(exc.status)}`}>
                    {exc.status.replace(/_/g, ' ')}
                  </span>
                  <span className="font-mono text-slate-400 text-[11px]">{exc.reference_number}</span>
                </div>
                <div className="text-[11px] text-slate-500">
                  Assigned: <span className="font-semibold text-slate-700">{exc.assigned_role || 'Unassigned'}</span>
                </div>
              </div>

              {/* Title & Description */}
              <div>
                <h5 className="font-bold text-slate-900 text-sm">{exc.title}</h5>
                <p className="text-slate-600 mt-0.5 leading-relaxed">{exc.description}</p>
              </div>

              {/* Specific Vendor Instruction if set */}
              {exc.vendor_action_instruction && (
                <div className="p-2.5 rounded bg-amber-50 border border-amber-200 text-amber-900 text-xs">
                  <strong>Vendor Instruction:</strong> {exc.vendor_action_instruction}
                </div>
              )}

              {/* Resolution details if resolved */}
              {exc.resolved_at && (
                <div className="p-2.5 rounded bg-emerald-50 border border-emerald-200 text-emerald-900 text-xs flex items-center justify-between">
                  <div>
                    <strong>Resolved ({exc.resolution_type}):</strong> {exc.resolution_notes || 'Resolved by reviewer'}
                  </div>
                  <span className="text-[10px] text-emerald-700 font-mono">
                    {new Date(exc.resolved_at).toLocaleString()}
                  </span>
                </div>
              )}

              {/* Field Corrections Diff History */}
              {exc.field_corrections && exc.field_corrections.length > 0 && (
                <div className="p-2.5 rounded bg-blue-50/80 border border-blue-200 text-xs space-y-1">
                  <div className="font-semibold text-blue-900 flex items-center gap-1">
                    <RotateCcw className="w-3.5 h-3.5" />
                    <span>Vendor Correction History</span>
                  </div>
                  {exc.field_corrections.map((corr) => (
                    <div key={corr.id} className="text-[11px] text-blue-800">
                      Field <strong>{corr.field_name}</strong>: changed from{' '}
                      <span className="font-mono bg-white px-1 rounded border border-blue-200">
                        {corr.previous_value || 'None'}
                      </span>{' '}
                      to{' '}
                      <span className="font-mono font-bold bg-white px-1 rounded border border-blue-200">
                        {corr.new_value}
                      </span>
                      {corr.vendor_explanation && (
                        <div className="italic text-slate-600 mt-0.5 ml-2">
                          Reason: &ldquo;{corr.vendor_explanation}&rdquo;
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}

              {/* Action Buttons */}
              {isReviewer && (
                <div className="flex flex-wrap items-center gap-2 pt-2 border-t border-slate-100">
                  {exc.status !== 'RESOLVED' && exc.status !== 'CLOSED' && (
                    <>
                      <button
                        onClick={() => openActionModal(exc, 'REQUEST_CORRECTION')}
                        className="px-2.5 py-1 text-xs font-semibold bg-amber-600 hover:bg-amber-700 text-white rounded transition shadow-2xs"
                      >
                        Request Vendor Correction
                      </button>
                      <button
                        onClick={() => openActionModal(exc, 'RESOLVE')}
                        className="px-2.5 py-1 text-xs font-semibold bg-emerald-600 hover:bg-emerald-700 text-white rounded transition shadow-2xs"
                      >
                        Resolve Exception
                      </button>
                    </>
                  )}

                  {(exc.status === 'RESOLVED' || exc.status === 'CLOSED') && (
                    <button
                      onClick={() => openActionModal(exc, 'REOPEN')}
                      className="px-2.5 py-1 text-xs font-semibold bg-slate-700 hover:bg-slate-800 text-white rounded transition shadow-2xs flex items-center gap-1"
                    >
                      <RotateCcw className="w-3 h-3" />
                      <span>Reopen Exception</span>
                    </button>
                  )}

                  <button
                    onClick={() => openActionModal(exc, 'REASSIGN')}
                    className="px-2.5 py-1 text-xs font-medium bg-white hover:bg-slate-100 text-slate-700 border border-slate-300 rounded transition flex items-center gap-1"
                  >
                    <UserPlus className="w-3 h-3" />
                    <span>Reassign</span>
                  </button>

                  <button
                    onClick={() => openActionModal(exc, 'COMMENT')}
                    className="px-2.5 py-1 text-xs font-medium bg-white hover:bg-slate-100 text-slate-700 border border-slate-300 rounded transition flex items-center gap-1"
                  >
                    <MessageSquare className="w-3 h-3" />
                    <span>Comments ({exc.comments?.length || 0})</span>
                  </button>
                </div>
              )}

              {/* Comments Thread Summary */}
              {exc.comments && exc.comments.length > 0 && (
                <div className="pt-2 border-t border-slate-100 space-y-1.5">
                  {exc.comments.slice(-2).map((c) => (
                    <div
                      key={c.id}
                      className={`p-2 rounded text-[11px] flex items-start gap-2 ${
                        c.is_internal
                          ? 'bg-amber-50/80 border border-amber-200 text-amber-900'
                          : 'bg-white border border-slate-200 text-slate-700'
                      }`}
                    >
                      {c.is_internal && <Lock className="w-3 h-3 text-amber-600 shrink-0 mt-0.5" />}
                      <div className="flex-1">
                        <div className="flex items-center justify-between">
                          <span className="font-semibold text-slate-900">
                            {c.author_role} {c.is_internal ? '(Internal Note)' : '(Vendor Clarification)'}
                          </span>
                          <span className="text-[10px] text-slate-400">
                            {new Date(c.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                          </span>
                        </div>
                        <p className="mt-0.5">{c.message}</p>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Action Modal */}
      {actionType && (
        <div className="fixed inset-0 bg-slate-900/50 backdrop-blur-2xs z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl max-w-lg w-full p-6 shadow-xl border border-slate-200 space-y-4 animate-in fade-in zoom-in-95 duration-100">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <h4 className="font-bold text-slate-900 text-sm">
                {actionType === 'REQUEST_CORRECTION' && 'Request Action / Correction from Vendor'}
                {actionType === 'RESOLVE' && 'Resolve Exception'}
                {actionType === 'REOPEN' && 'Reopen Exception (Mandatory Justification)'}
                {actionType === 'REASSIGN' && 'Reassign Exception'}
                {actionType === 'COMMENT' && 'Add Note or Clarification'}
              </h4>
              <button onClick={closeActionModal} className="text-slate-400 hover:text-slate-600">
                <X className="w-4 h-4" />
              </button>
            </div>

            {error && (
              <div className="p-2.5 bg-rose-50 border border-rose-200 text-rose-800 text-xs rounded-lg">
                {error}
              </div>
            )}

            {/* Request Vendor Correction Form */}
            {actionType === 'REQUEST_CORRECTION' && (
              <div className="space-y-3">
                <p className="text-xs text-slate-600">
                  This will transition the exception to <strong>ACTION_REQUIRED_FROM_VENDOR</strong>,
                  send an in-app alert to the vendor, and enable them to upload replacement documents or correct profile fields.
                </p>
                <div>
                  <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1">
                    Clear Action Instructions for Vendor *
                  </label>
                  <textarea
                    rows={3}
                    value={vendorInstruction}
                    onChange={(e) => setVendorInstruction(e.target.value)}
                    placeholder="E.g.: The PAN entered in your profile differs from the PAN card proof. Please correct the application PAN or upload an updated document."
                    className="w-full p-2.5 text-xs border border-slate-300 rounded-lg focus:ring-2 focus:ring-amber-500 focus:outline-none"
                  />
                </div>
              </div>
            )}

            {/* Resolve Form */}
            {actionType === 'RESOLVE' && (
              <div className="space-y-3">
                <div>
                  <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1">
                    Resolution Type *
                  </label>
                  <select
                    value={resolutionType}
                    onChange={(e) => setResolutionType(e.target.value as ResolutionType)}
                    className="w-full p-2 text-xs border border-slate-300 rounded-lg focus:outline-none"
                  >
                    <option value="CORRECTED_BY_VENDOR">Corrected by Vendor</option>
                    <option value="VERIFIED_MANUALLY">Verified Manually</option>
                    <option value="DOCUMENT_ACCEPTED_WITH_NOTE">Document Accepted with Note</option>
                    <option value="EXCEPTION_OVERRIDDEN">Exception Overridden</option>
                    <option value="CANCELLED_OBSOLETE">Cancelled / Obsolete</option>
                  </select>
                </div>
                <div>
                  <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1">
                    Reviewer Notes / Evidence Rationale
                  </label>
                  <textarea
                    rows={2}
                    value={resolutionNotes}
                    onChange={(e) => setResolutionNotes(e.target.value)}
                    placeholder="Document why this resolution was approved..."
                    className="w-full p-2.5 text-xs border border-slate-300 rounded-lg focus:outline-none"
                  />
                </div>
              </div>
            )}

            {/* Reopen Form */}
            {actionType === 'REOPEN' && (
              <div className="space-y-3">
                <p className="text-xs text-slate-600">
                  Reopening an exception requires a mandatory justification for audit compliance.
                </p>
                <div>
                  <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1">
                    Mandatory Reason for Reopening *
                  </label>
                  <textarea
                    rows={3}
                    value={reopenReason}
                    onChange={(e) => setReopenReason(e.target.value)}
                    placeholder="Explain why this previously resolved exception is being reopened..."
                    className="w-full p-2.5 text-xs border border-slate-300 rounded-lg focus:ring-2 focus:ring-slate-700 focus:outline-none"
                  />
                </div>
              </div>
            )}

            {/* Reassign Form */}
            {actionType === 'REASSIGN' && (
              <div className="space-y-3">
                <div>
                  <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1">
                    Assign Role
                  </label>
                  <select
                    value={reassignRole}
                    onChange={(e) => setReassignRole(e.target.value)}
                    className="w-full p-2 text-xs border border-slate-300 rounded-lg focus:outline-none"
                  >
                    <option value="REVIEWER">Reviewer / Approver</option>
                    <option value="PROCUREMENT_OFFICER">Procurement Officer</option>
                    <option value="VENDOR">Vendor</option>
                    <option value="ADMIN">Administrator</option>
                  </select>
                </div>
              </div>
            )}

            {/* Comment Form */}
            {actionType === 'COMMENT' && (
              <div className="space-y-3">
                <div className="flex items-center gap-3">
                  <label className="flex items-center gap-1.5 text-xs font-semibold text-slate-700 cursor-pointer">
                    <input
                      type="radio"
                      name="comment_type"
                      checked={isInternalComment}
                      onChange={() => setIsInternalComment(true)}
                    />
                    <Lock className="w-3.5 h-3.5 text-amber-600" />
                    <span>Internal Note (Hidden from Vendor)</span>
                  </label>
                  <label className="flex items-center gap-1.5 text-xs font-semibold text-slate-700 cursor-pointer">
                    <input
                      type="radio"
                      name="comment_type"
                      checked={!isInternalComment}
                      onChange={() => setIsInternalComment(false)}
                    />
                    <span>Vendor-Visible Clarification</span>
                  </label>
                </div>
                <textarea
                  rows={3}
                  value={commentMessage}
                  onChange={(e) => setCommentMessage(e.target.value)}
                  placeholder="Type note or question..."
                  className="w-full p-2.5 text-xs border border-slate-300 rounded-lg focus:outline-none"
                />
              </div>
            )}

            {/* Modal Actions */}
            <div className="flex items-center justify-end gap-2 pt-2 border-t border-slate-100">
              <button
                onClick={closeActionModal}
                disabled={submittingAction}
                className="px-3 py-1.5 text-xs font-medium text-slate-600 hover:text-slate-800 rounded-lg border border-slate-200"
              >
                Cancel
              </button>
              <button
                onClick={executeAction}
                disabled={submittingAction}
                className="px-4 py-1.5 text-xs font-semibold text-white bg-indigo-600 hover:bg-indigo-700 rounded-lg transition disabled:opacity-50"
              >
                {submittingAction ? 'Processing...' : 'Confirm Action'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
