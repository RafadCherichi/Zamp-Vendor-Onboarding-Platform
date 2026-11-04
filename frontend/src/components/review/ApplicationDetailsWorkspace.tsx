import React, { useState, useEffect } from 'react';
import {
  ArrowLeft,
  CheckCircle2,
  AlertTriangle,
  ShieldCheck,
  User,
  Building2,
  Lock,
  RotateCcw,
  XCircle,
  HelpCircle,
  Check,
  X,
  Eye,
  AlertOctagon,
} from 'lucide-react';
import {
  apiGetApplicationComprehensiveDetails,
  apiApproveApplication,
  apiRejectApplication,
  apiClarifyApplication,
  apiEscalateApplication,
  apiAssignReviewer,
  apiGetOrganisationReviewers,
} from '../../api/queue';
import type {
  ApplicationComprehensiveDetails,
  ReviewerUser,
} from '../../types/queue';
import { ExceptionManagerCard } from '../reviewer/ExceptionManagerCard';

interface Props {
  applicationId: string;
  onBack?: () => void;
  onActionComplete?: () => void;
  isReviewer?: boolean;
}

export const ApplicationDetailsWorkspace: React.FC<Props> = ({
  applicationId,
  onBack,
  onActionComplete,
  isReviewer = true,
}) => {
  const [details, setDetails] = useState<ApplicationComprehensiveDetails | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [reviewers, setReviewers] = useState<ReviewerUser[]>([]);

  // Navigation tab
  const [activeTab, setActiveTab] = useState<
    'OVERVIEW' | 'BUSINESS' | 'DOCUMENTS' | 'VALIDATION' | 'EXCEPTIONS' | 'REGISTRIES' | 'AUDIT'
  >('OVERVIEW');

  // Preview modal
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [previewTitle, setPreviewTitle] = useState<string>('');

  // Modals for Decision Actions
  const [activeModal, setActiveModal] = useState<
    'APPROVE' | 'REJECT' | 'CLARIFY' | 'ESCALATE' | 'ASSIGN' | null
  >(null);
  const [approveNotes, setApproveNotes] = useState<string>('');
  const [rejectReason, setRejectReason] = useState<string>('');
  const [rejectNotes, setRejectNotes] = useState<string>('');
  const [clarifyInstructions, setClarifyInstructions] = useState<string>('');
  const [escalateReason, setEscalateReason] = useState<string>('');
  const [escalateTargetRole, setEscalateTargetRole] = useState<string>('ADMIN');
  const [selectedReviewerId, setSelectedReviewerId] = useState<string>('');
  const [actionSubmitting, setActionSubmitting] = useState<boolean>(false);
  const [actionError, setActionError] = useState<string | null>(null);

  const fetchDetails = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await apiGetApplicationComprehensiveDetails(applicationId);
      setDetails(data);
      if (data.overview.assigned_reviewer_id) {
        setSelectedReviewerId(data.overview.assigned_reviewer_id);
      }
    } catch (err: any) {
      setError(err?.message || 'Failed to load application workspace details.');
    } finally {
      setLoading(false);
    }
  };

  const fetchReviewers = async () => {
    try {
      const data = await apiGetOrganisationReviewers();
      setReviewers(data);
    } catch {
      // Ignore
    }
  };

  useEffect(() => {
    if (applicationId) {
      fetchDetails();
      fetchReviewers();
    }
  }, [applicationId]);

  const handleApprove = async () => {
    try {
      setActionSubmitting(true);
      setActionError(null);
      await apiApproveApplication(applicationId, approveNotes.trim() || undefined);
      setActiveModal(null);
      fetchDetails();
      if (onActionComplete) onActionComplete();
    } catch (err: any) {
      setActionError(err?.message || 'Failed to approve application.');
    } finally {
      setActionSubmitting(false);
    }
  };

  const handleReject = async () => {
    if (!rejectReason.trim()) {
      setActionError('A clear rejection reason is mandatory.');
      return;
    }
    try {
      setActionSubmitting(true);
      setActionError(null);
      await apiRejectApplication(applicationId, rejectReason.trim(), rejectNotes.trim() || undefined);
      setActiveModal(null);
      fetchDetails();
      if (onActionComplete) onActionComplete();
    } catch (err: any) {
      setActionError(err?.message || 'Failed to reject application.');
    } finally {
      setActionSubmitting(false);
    }
  };

  const handleClarify = async () => {
    if (!clarifyInstructions.trim()) {
      setActionError('Clarification instructions for the vendor are mandatory.');
      return;
    }
    try {
      setActionSubmitting(true);
      setActionError(null);
      await apiClarifyApplication(applicationId, clarifyInstructions.trim());
      setActiveModal(null);
      fetchDetails();
      if (onActionComplete) onActionComplete();
    } catch (err: any) {
      setActionError(err?.message || 'Failed to dispatch clarification request.');
    } finally {
      setActionSubmitting(false);
    }
  };

  const handleEscalate = async () => {
    if (!escalateReason.trim()) {
      setActionError('An escalation reason is mandatory.');
      return;
    }
    try {
      setActionSubmitting(true);
      setActionError(null);
      await apiEscalateApplication(applicationId, escalateReason.trim(), escalateTargetRole);
      setActiveModal(null);
      fetchDetails();
      if (onActionComplete) onActionComplete();
    } catch (err: any) {
      setActionError(err?.message || 'Failed to escalate application.');
    } finally {
      setActionSubmitting(false);
    }
  };

  const handleAssign = async (revId: string) => {
    try {
      setActionSubmitting(true);
      await apiAssignReviewer(applicationId, revId || null);
      setSelectedReviewerId(revId);
      setActiveModal(null);
      fetchDetails();
      if (onActionComplete) onActionComplete();
    } catch (err: any) {
      alert(err?.message || 'Failed to assign reviewer.');
    } finally {
      setActionSubmitting(false);
    }
  };

  if (loading) {
    return (
      <div className="bg-white rounded-2xl border border-slate-200 p-12 text-center text-xs text-slate-500 space-y-3">
        <RotateCcw className="w-6 h-6 animate-spin text-indigo-600 mx-auto" />
        <p>Loading complete evidence and decision workspace...</p>
      </div>
    );
  }

  if (error || !details) {
    return (
      <div className="bg-white rounded-2xl border border-slate-200 p-8 text-center text-xs space-y-4">
        <div className="p-3 bg-rose-50 border border-rose-200 text-rose-700 rounded-lg max-w-md mx-auto">
          {error || 'Unable to load application workspace.'}
        </div>
        {onBack && (
          <button
            onClick={onBack}
            className="px-4 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-lg font-semibold inline-flex items-center gap-1.5"
          >
            <ArrowLeft className="w-4 h-4" />
            <span>Back to Queue</span>
          </button>
        )}
      </div>
    );
  }

  const { overview, business_details, documents, validation, exceptions, external_verifications, activity_trail } = details;

  const getStatusBadge = (status: string) => {
    switch (status) {
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

  return (
    <div className="space-y-6">
      {/* Top Banner & Action Bar */}
      <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-2xs space-y-4">
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
          <div className="flex items-start gap-3">
            {onBack && (
              <button
                onClick={onBack}
                className="p-2 rounded-lg border border-slate-200 hover:bg-slate-50 text-slate-600 transition"
                title="Back to Application Queue"
              >
                <ArrowLeft className="w-5 h-5" />
              </button>
            )}
            <div>
              <div className="flex flex-wrap items-center gap-2">
                <span className="font-mono text-xs font-bold px-2.5 py-0.5 rounded bg-indigo-50 text-indigo-700 border border-indigo-200">
                  {overview.reference_number}
                </span>
                <span className={`text-xs font-bold px-2.5 py-0.5 rounded-full border ${getStatusBadge(overview.status)}`}>
                  {overview.status.replace(/_/g, ' ')}
                </span>
                {overview.is_approval_eligible ? (
                  <span className="inline-flex items-center gap-1 text-[11px] font-bold px-2 py-0.5 rounded bg-emerald-50 text-emerald-700 border border-emerald-200">
                    <CheckCircle2 className="w-3 h-3 text-emerald-600" />
                    Ready for Approval
                  </span>
                ) : (
                  <span className="inline-flex items-center gap-1 text-[11px] font-bold px-2 py-0.5 rounded bg-amber-50 text-amber-700 border border-amber-200">
                    <AlertTriangle className="w-3 h-3 text-amber-600" />
                    {overview.blocking_reasons.length} Pending Requirement(s)
                  </span>
                )}
              </div>
              <h2 className="text-xl font-extrabold text-slate-900 mt-1">{overview.legal_name}</h2>
              <div className="flex flex-wrap items-center gap-3 text-xs text-slate-500 mt-0.5">
                <span>{overview.constitution.replace(/_/g, ' ')}</span>
                <span>&bull;</span>
                <span>Submitted: {overview.submitted_at ? new Date(overview.submitted_at).toLocaleDateString() : 'Draft'}</span>
                <span>&bull;</span>
                <span>Reviewer: <strong>{overview.assigned_reviewer_name || 'Unassigned'}</strong></span>
              </div>
            </div>
          </div>

          {/* Action Toolbar */}
          {isReviewer && overview.status !== 'APPROVED' && overview.status !== 'REJECTED' && (
            <div className="flex flex-wrap items-center gap-2">
              {/* Quick Assign Dropdown */}
              <div className="flex items-center gap-1 bg-slate-50 border border-slate-200 rounded-lg p-1 text-xs">
                <User className="w-3.5 h-3.5 text-slate-500 ml-1" />
                <select
                  value={selectedReviewerId}
                  onChange={(e) => handleAssign(e.target.value)}
                  className="bg-transparent text-xs font-medium text-slate-700 focus:outline-none pr-1 cursor-pointer"
                >
                  <option value="">Unassigned</option>
                  {reviewers.map((r) => (
                    <option key={r.id} value={r.id}>
                      {r.full_name} ({r.role})
                    </option>
                  ))}
                </select>
              </div>

              {/* Request Clarification */}
              <button
                onClick={() => {
                  setActionError(null);
                  setActiveModal('CLARIFY');
                }}
                className="px-3 py-1.5 rounded-lg text-xs font-semibold bg-amber-50 hover:bg-amber-100 text-amber-800 border border-amber-300 transition flex items-center gap-1"
              >
                <HelpCircle className="w-3.5 h-3.5" />
                <span>Request Clarification</span>
              </button>

              {/* Escalate */}
              <button
                onClick={() => {
                  setActionError(null);
                  setActiveModal('ESCALATE');
                }}
                className="px-3 py-1.5 rounded-lg text-xs font-semibold bg-slate-100 hover:bg-slate-200 text-slate-700 border border-slate-300 transition flex items-center gap-1"
              >
                <AlertOctagon className="w-3.5 h-3.5" />
                <span>Escalate</span>
              </button>

              {/* Reject */}
              <button
                onClick={() => {
                  setActionError(null);
                  setActiveModal('REJECT');
                }}
                className="px-3 py-1.5 rounded-lg text-xs font-semibold bg-rose-50 hover:bg-rose-100 text-rose-800 border border-rose-300 transition flex items-center gap-1"
              >
                <XCircle className="w-3.5 h-3.5" />
                <span>Reject</span>
              </button>

              {/* Approve */}
              <button
                onClick={() => {
                  setActionError(null);
                  setActiveModal('APPROVE');
                }}
                className={`px-4 py-1.5 rounded-lg text-xs font-semibold text-white transition flex items-center gap-1.5 shadow-xs ${
                  overview.is_approval_eligible
                    ? 'bg-emerald-600 hover:bg-emerald-700'
                    : 'bg-slate-400 hover:bg-slate-500 cursor-not-allowed opacity-90'
                }`}
              >
                <Check className="w-3.5 h-3.5" />
                <span>Approve Vendor</span>
              </button>
            </div>
          )}
        </div>

        {/* 7 Section Navigation Tabs */}
        <div className="flex gap-2 pt-2 border-t border-slate-100 text-xs font-semibold overflow-x-auto">
          {[
            { id: 'OVERVIEW', label: 'A. Overview & Gates' },
            { id: 'BUSINESS', label: 'B. Business Details' },
            { id: 'DOCUMENTS', label: `C. Documents (${documents.length})` },
            { id: 'VALIDATION', label: 'D. 4-Layer Validation' },
            { id: 'EXCEPTIONS', label: `E. Exceptions (${exceptions.length})` },
            { id: 'REGISTRIES', label: `F. Registries (${external_verifications.length})` },
            { id: 'AUDIT', label: `G. Activity Trail (${activity_trail.length})` },
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as any)}
              className={`pb-2 px-3 border-b-2 transition whitespace-nowrap ${
                activeTab === tab.id
                  ? 'border-indigo-600 text-indigo-700'
                  : 'border-transparent text-slate-500 hover:text-slate-800'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>
      </div>

      {/* Tab A: Overview & Policy Checklist */}
      {activeTab === 'OVERVIEW' && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2 space-y-4">
            {/* Approval Readiness Checklist */}
            <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-2xs space-y-3">
              <h3 className="text-sm font-bold text-slate-900 flex items-center gap-1.5">
                <ShieldCheck className="w-4 h-4 text-indigo-600" />
                Statutory Compliance &amp; Policy Checklist
              </h3>
              <p className="text-xs text-slate-500">
                All statutory requirements and evidence checks must be satisfied before final vendor onboarding approval.
              </p>

              <div className="space-y-2 pt-2">
                {overview.blocking_reasons.length === 0 ? (
                  <div className="p-3 rounded-lg bg-emerald-50 border border-emerald-200 text-emerald-800 text-xs flex items-center gap-2">
                    <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
                    <span className="font-semibold">
                      All approval criteria verified: mandatory documents present, no unresolved blocking exceptions, validation engine passed.
                    </span>
                  </div>
                ) : (
                  overview.blocking_reasons.map((reason, idx) => (
                    <div
                      key={idx}
                      className="p-2.5 rounded-lg bg-amber-50 border border-amber-200 text-amber-900 text-xs flex items-start gap-2"
                    >
                      <AlertTriangle className="w-4 h-4 text-amber-600 shrink-0 mt-0.5" />
                      <span>{reason}</span>
                    </div>
                  ))
                )}
              </div>
            </div>

            {/* Decision Log if resolved */}
            {(overview.status === 'APPROVED' || overview.status === 'REJECTED') && (
              <div
                className={`p-5 rounded-xl border text-xs space-y-2 ${
                  overview.status === 'APPROVED' ? 'bg-emerald-50/70 border-emerald-200' : 'bg-rose-50/70 border-rose-200'
                }`}
              >
                <h4 className="font-bold text-sm">
                  {overview.status === 'APPROVED' ? 'Formal Approval Recorded' : 'Application Rejection Recorded'}
                </h4>
                <div className="text-slate-700">
                  Reviewed by: <strong>{overview.reviewed_by_name || 'Compliance Reviewer'}</strong> &bull; Date:{' '}
                  <strong>{overview.reviewed_at ? new Date(overview.reviewed_at).toLocaleString() : '—'}</strong>
                </div>
                {overview.rejection_reason && (
                  <div className="p-2.5 rounded bg-white/80 border border-rose-200 text-rose-900">
                    <strong>Rejection Reason:</strong> {overview.rejection_reason}
                  </div>
                )}
                {overview.decision_notes && (
                  <div className="text-slate-600">
                    <strong>Reviewer Notes:</strong> {overview.decision_notes}
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Right Column: Metadata Summary */}
          <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-2xs space-y-4 text-xs">
            <h4 className="font-bold text-slate-900 border-b border-slate-100 pb-2">Application Metadata</h4>
            <div className="space-y-2.5 text-slate-600">
              <div className="flex justify-between">
                <span>Application ID:</span>
                <span className="font-mono text-slate-800">{overview.id.slice(0, 8)}...</span>
              </div>
              <div className="flex justify-between">
                <span>Reference:</span>
                <span className="font-mono font-bold text-slate-900">{overview.reference_number}</span>
              </div>
              <div className="flex justify-between">
                <span>Submitted At:</span>
                <span>{overview.submitted_at ? new Date(overview.submitted_at).toLocaleString() : 'Draft'}</span>
              </div>
              <div className="flex justify-between">
                <span>Assigned Reviewer:</span>
                <span className="font-semibold text-slate-800">{overview.assigned_reviewer_name || 'Unassigned'}</span>
              </div>
              <div className="flex justify-between">
                <span>Active Exceptions:</span>
                <span className="font-bold text-amber-700">{exceptions.filter((e) => e.status !== 'RESOLVED' && e.status !== 'CLOSED').length}</span>
              </div>
              <div className="flex justify-between">
                <span>Total Documents:</span>
                <span>{documents.length} slots</span>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Tab B: Business Details */}
      {activeTab === 'BUSINESS' && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Section 1: Business Identity */}
          <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-2xs text-xs space-y-3">
            <h4 className="font-bold text-slate-900 flex items-center gap-1.5 border-b border-slate-100 pb-2">
              <Building2 className="w-4 h-4 text-indigo-600" />
              1. Business Identity &amp; Operating Address
            </h4>
            <div className="space-y-2 text-slate-600">
              <div>
                <span className="text-[11px] text-slate-400 block">Legal Business Name</span>
                <span className="font-semibold text-slate-900">{business_details.identity.legal_name}</span>
              </div>
              <div>
                <span className="text-[11px] text-slate-400 block">Trade Name</span>
                <span>{business_details.identity.trade_name || 'Same as Legal Name'}</span>
              </div>
              <div>
                <span className="text-[11px] text-slate-400 block">Constitution of Business</span>
                <span className="font-medium text-slate-800">{business_details.identity.constitution.replace(/_/g, ' ')}</span>
              </div>
              <div>
                <span className="text-[11px] text-slate-400 block">Registered Address</span>
                <span>{business_details.identity.registered_address || '—'}</span>
              </div>
              <div className="grid grid-cols-3 gap-2">
                <div>
                  <span className="text-[11px] text-slate-400 block">City</span>
                  <span>{business_details.identity.city || '—'}</span>
                </div>
                <div>
                  <span className="text-[11px] text-slate-400 block">State</span>
                  <span>{business_details.identity.state || '—'}</span>
                </div>
                <div>
                  <span className="text-[11px] text-slate-400 block">PIN Code</span>
                  <span className="font-mono">{business_details.identity.pincode || '—'}</span>
                </div>
              </div>
            </div>
          </div>

          {/* Section 2: Tax & Registration */}
          <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-2xs text-xs space-y-3">
            <h4 className="font-bold text-slate-900 flex items-center gap-1.5 border-b border-slate-100 pb-2">
              <ShieldCheck className="w-4 h-4 text-indigo-600" />
              2. Statutory &amp; Tax Registrations (Masked)
            </h4>
            <div className="space-y-2 text-slate-600">
              <div>
                <span className="text-[11px] text-slate-400 block">Permanent Account Number (PAN)</span>
                <span className="font-mono font-bold text-slate-900">{business_details.tax_and_registrations.pan || '—'}</span>
              </div>
              <div>
                <span className="text-[11px] text-slate-400 block">Goods &amp; Services Tax Identification (GSTIN)</span>
                <span className="font-mono font-bold text-slate-900">{business_details.tax_and_registrations.gstin || 'Not GST Registered'}</span>
              </div>
              <div>
                <span className="text-[11px] text-slate-400 block">MCA Registration (CIN / LLPIN)</span>
                <span className="font-mono">{business_details.tax_and_registrations.cin_llpin || 'Not Applicable'}</span>
              </div>
              <div>
                <span className="text-[11px] text-slate-400 block">MSME / Udyam Registration</span>
                <span className="font-mono">{business_details.tax_and_registrations.udyam_number || 'Not Registered'}</span>
              </div>
            </div>
          </div>

          {/* Section 3: Authorised Contact */}
          <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-2xs text-xs space-y-3">
            <h4 className="font-bold text-slate-900 flex items-center gap-1.5 border-b border-slate-100 pb-2">
              <User className="w-4 h-4 text-indigo-600" />
              3. Authorised Signatory &amp; Primary Contact
            </h4>
            <div className="space-y-2 text-slate-600">
              <div>
                <span className="text-[11px] text-slate-400 block">Contact Person</span>
                <span className="font-semibold text-slate-900">{business_details.contact.contact_name || '—'}</span>
                <span className="text-slate-400 text-[11px] ml-1">({business_details.contact.contact_designation || 'Representative'})</span>
              </div>
              <div>
                <span className="text-[11px] text-slate-400 block">Official Email</span>
                <span>{business_details.contact.contact_email || '—'}</span>
              </div>
              <div>
                <span className="text-[11px] text-slate-400 block">Mobile Number</span>
                <span className="font-mono">{business_details.contact.contact_mobile || '—'}</span>
              </div>
              <div>
                <span className="text-[11px] text-slate-400 block">Authorised Signatory</span>
                <span>{business_details.contact.authorised_signatory_name || business_details.contact.contact_name || '—'}</span>
              </div>
            </div>
          </div>

          {/* Section 4: Banking */}
          <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-2xs text-xs space-y-3">
            <h4 className="font-bold text-slate-900 flex items-center gap-1.5 border-b border-slate-100 pb-2">
              <Lock className="w-4 h-4 text-indigo-600" />
              4. Banking &amp; Disbursement Profile (Masked)
            </h4>
            <div className="space-y-2 text-slate-600">
              <div>
                <span className="text-[11px] text-slate-400 block">Account Holder Name</span>
                <span className="font-semibold text-slate-900">{business_details.banking.bank_account_holder_name || '—'}</span>
              </div>
              <div>
                <span className="text-[11px] text-slate-400 block">Bank Account Number (Protected)</span>
                <span className="font-mono font-bold text-slate-900">{business_details.banking.bank_account_number || '—'}</span>
              </div>
              <div className="grid grid-cols-2 gap-2">
                <div>
                  <span className="text-[11px] text-slate-400 block">IFSC Code</span>
                  <span className="font-mono font-bold">{business_details.banking.bank_ifsc || '—'}</span>
                </div>
                <div>
                  <span className="text-[11px] text-slate-400 block">Account Type</span>
                  <span>{business_details.banking.bank_account_type || 'CURRENT'}</span>
                </div>
              </div>
              <div>
                <span className="text-[11px] text-slate-400 block">Bank Name</span>
                <span>{business_details.banking.bank_name || 'Designated Bank Branch'}</span>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Tab C: Documents & Version History */}
      {activeTab === 'DOCUMENTS' && (
        <div className="space-y-4">
          <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-2xs">
            <h4 className="text-sm font-bold text-slate-900 mb-1">Document Evidence &amp; OCR Extraction Logs</h4>
            <p className="text-xs text-slate-500 mb-4">
              All statutory documents submitted by the vendor, with full version history and optical character extraction results.
            </p>

            <div className="space-y-4">
              {documents.map((doc) => (
                <div key={doc.id} className="p-4 rounded-xl border border-slate-200 bg-slate-50/50 space-y-3 text-xs">
                  <div className="flex items-center justify-between">
                    <div>
                      <span className="font-bold text-slate-900 text-sm">{doc.title}</span>
                      <span className="text-[11px] text-slate-400 ml-2 font-mono">({doc.document_type})</span>
                    </div>
                    <span
                      className={`px-2.5 py-0.5 rounded-full font-semibold text-[11px] border ${
                        doc.status === 'UPLOADED'
                          ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
                          : 'bg-amber-50 text-amber-700 border-amber-200'
                      }`}
                    >
                      {doc.status}
                    </span>
                  </div>

                  {/* Versions List */}
                  <div className="space-y-2">
                    {doc.versions.map((ver) => (
                      <div
                        key={ver.id}
                        className="bg-white rounded-lg border border-slate-200 p-3 flex flex-col md:flex-row md:items-center justify-between gap-3"
                      >
                        <div>
                          <div className="flex items-center gap-2">
                            <span className="font-bold text-slate-800">Version {ver.version_number}</span>
                            <span className="text-slate-400">&bull;</span>
                            <span className="text-slate-600 font-mono text-[11px]">{ver.filename}</span>
                            <span className="text-slate-400">&bull;</span>
                            <span className="text-slate-500 text-[11px]">{Math.round(ver.file_size / 1024)} KB</span>
                          </div>
                          {ver.extraction && (
                            <div className="mt-1 flex items-center gap-3 text-[11px] text-slate-500">
                              <span>OCR: <strong>{ver.extraction.status}</strong></span>
                              <span>Type Match: <strong>{ver.extraction.is_type_match ? 'Yes' : 'Needs Review'}</strong></span>
                              <span>Confidence: <strong>{Math.round((ver.extraction.classification_confidence || 0) * 100)}%</strong></span>
                            </div>
                          )}
                        </div>

                        <button
                          onClick={() => {
                            setPreviewUrl(ver.preview_url);
                            setPreviewTitle(`${doc.title} (v${ver.version_number})`);
                          }}
                          className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-slate-300 bg-slate-50 hover:bg-slate-100 text-slate-700 font-medium text-xs transition self-start md:self-auto"
                        >
                          <Eye className="w-3.5 h-3.5 text-indigo-600" />
                          <span>Inspect Document</span>
                        </button>
                      </div>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Tab D: 4-Layer Validation Findings */}
      {activeTab === 'VALIDATION' && validation && (
        <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-2xs space-y-4 text-xs">
          <div className="border-b border-slate-100 pb-3 flex items-center justify-between">
            <div>
              <h4 className="text-sm font-bold text-slate-900">4-Layer Deterministic Validation Results</h4>
              <p className="text-slate-500 mt-0.5">{validation.summary}</p>
            </div>
            <div className="flex gap-2">
              <span className="px-2 py-0.5 bg-emerald-100 text-emerald-800 rounded font-bold text-[11px]">
                {validation.passed_count} Passed
              </span>
              <span className="px-2 py-0.5 bg-rose-100 text-rose-800 rounded font-bold text-[11px]">
                {validation.failed_count} Failed
              </span>
              <span className="px-2 py-0.5 bg-amber-100 text-amber-800 rounded font-bold text-[11px]">
                {validation.warning_count} Warnings
              </span>
            </div>
          </div>

          {/* Grouped Layers */}
          {Object.entries(validation.layers).map(([layerName, findings]) => (
            <div key={layerName} className="space-y-2">
              <h5 className="font-bold text-slate-800 uppercase tracking-wider text-[11px] text-indigo-700">
                {layerName.replace(/_/g, ' ')} ({findings.length} checks)
              </h5>
              <div className="space-y-2">
                {findings.map((f) => (
                  <div
                    key={f.id}
                    className={`p-3 rounded-lg border flex flex-col md:flex-row md:items-center justify-between gap-3 ${
                      f.status === 'PASSED'
                        ? 'bg-emerald-50/40 border-emerald-200'
                        : f.status === 'FAILED'
                        ? 'bg-rose-50/50 border-rose-200'
                        : 'bg-amber-50/50 border-amber-200'
                    }`}
                  >
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="font-bold text-slate-900">{f.check_name}</span>
                        <span
                          className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                            f.status === 'PASSED'
                              ? 'bg-emerald-600 text-white'
                              : f.status === 'FAILED'
                              ? 'bg-rose-600 text-white'
                              : 'bg-amber-500 text-white'
                          }`}
                        >
                          {f.status}
                        </span>
                      </div>
                      <p className="text-slate-600 mt-0.5">{f.explanation}</p>
                      {f.evidence && <div className="text-[11px] text-slate-500 font-mono mt-1">{f.evidence}</div>}
                    </div>
                    {f.recommended_action && (
                      <span className="text-[11px] text-slate-500 italic shrink-0">
                        {f.recommended_action}
                      </span>
                    )}
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Tab E: Exceptions & Clarifications */}
      {activeTab === 'EXCEPTIONS' && (
        <ExceptionManagerCard applicationId={applicationId} isReviewer={isReviewer} />
      )}

      {/* Tab F: External Registries (Simulated) */}
      {activeTab === 'REGISTRIES' && (
        <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-2xs space-y-4 text-xs">
          <div className="flex items-center justify-between border-b border-slate-100 pb-3">
            <div>
              <h4 className="text-sm font-bold text-slate-900">External Registry Authoritative Verifications</h4>
              <p className="text-slate-500 mt-0.5">
                Authoritative queries against statutory PAN, GSTIN, MCA, and Bank penny-drop gateways.
              </p>
            </div>
            <span className="px-2.5 py-1 bg-amber-100 text-amber-800 rounded font-bold text-[10px] border border-amber-300">
              SIMULATED SANDBOX
            </span>
          </div>

          <div className="space-y-3">
            {external_verifications.length === 0 ? (
              <div className="text-center py-6 text-slate-400">No registry checks executed yet.</div>
            ) : (
              external_verifications.map((v) => (
                <div key={v.id} className="p-3.5 rounded-lg border border-slate-200 bg-slate-50/60 space-y-2">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <span className="font-bold text-slate-900">{v.verification_type} VERIFICATION</span>
                      <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${v.status === 'VERIFIED' ? 'bg-emerald-100 text-emerald-800' : 'bg-rose-100 text-rose-800'}`}>
                        {v.status}
                      </span>
                      <span className="font-mono text-slate-400 text-[10px]">{v.request_id}</span>
                    </div>
                    <span className="text-slate-500 font-mono text-[11px]">{v.duration_ms} ms</span>
                  </div>
                  <div className="text-slate-600">
                    <strong>Provider Adapter:</strong> {v.provider_name}
                  </div>
                  <div className="text-slate-600">
                    <strong>Target:</strong> <span className="font-mono">{v.submitted_identifier}</span>
                  </div>
                  {v.reason && <div className="text-slate-500 italic"><strong>Outcome:</strong> {v.reason}</div>}
                  {v.returned_attributes && Object.keys(v.returned_attributes).length > 0 && (
                    <pre className="p-2 bg-slate-900 text-slate-100 rounded text-[11px] font-mono overflow-x-auto mt-1">
                      {JSON.stringify(v.returned_attributes, null, 2)}
                    </pre>
                  )}
                </div>
              ))
            )}
          </div>
        </div>
      )}

      {/* Tab G: Activity & Audit Trail */}
      {activeTab === 'AUDIT' && (
        <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-2xs space-y-4 text-xs">
          <div className="border-b border-slate-100 pb-2">
            <h4 className="text-sm font-bold text-slate-900">Application Chronological Activity Trail</h4>
            <p className="text-slate-500 mt-0.5">Immutable audit events recorded across application lifecycle.</p>
          </div>
          <div className="divide-y divide-slate-100">
            {activity_trail.length === 0 ? (
              <div className="text-center py-6 text-slate-400">No activity logged yet.</div>
            ) : (
              activity_trail.map((evt) => (
                <div key={evt.id} className="py-2.5 flex items-start justify-between">
                  <div>
                    <span className="font-mono font-bold text-slate-900">{evt.event_type}</span>
                    <span className="text-slate-400 text-[11px] ml-2">by {evt.actor_role}</span>
                    {evt.details && (
                      <pre className="mt-1 text-[10px] text-slate-600 font-mono bg-slate-50 p-1.5 rounded">
                        {JSON.stringify(evt.details)}
                      </pre>
                    )}
                  </div>
                  <span className="text-[11px] text-slate-400 font-mono shrink-0">
                    {evt.created_at ? new Date(evt.created_at).toLocaleString() : ''}
                  </span>
                </div>
              ))
            )}
          </div>
        </div>
      )}

      {/* Decision Action Modals */}
      {activeModal && (
        <div className="fixed inset-0 bg-slate-900/50 backdrop-blur-2xs z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl max-w-lg w-full p-6 shadow-xl border border-slate-200 space-y-4">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <h4 className="font-bold text-slate-900 text-sm">
                {activeModal === 'APPROVE' && 'Approve Vendor Application'}
                {activeModal === 'REJECT' && 'Reject Vendor Application'}
                {activeModal === 'CLARIFY' && 'Request Clarification from Vendor'}
                {activeModal === 'ESCALATE' && 'Escalate Application'}
              </h4>
              <button onClick={() => setActiveModal(null)} className="text-slate-400 hover:text-slate-600">
                <X className="w-4 h-4" />
              </button>
            </div>

            {actionError && (
              <div className="p-2.5 bg-rose-50 border border-rose-200 text-rose-800 text-xs rounded-lg">
                {actionError}
              </div>
            )}

            {/* Approve Modal Content */}
            {activeModal === 'APPROVE' && (
              <div className="space-y-3 text-xs">
                {!overview.is_approval_eligible ? (
                  <div className="p-3 bg-amber-50 border border-amber-200 text-amber-900 rounded-lg space-y-2">
                    <strong className="block font-semibold">Cannot Approve — Pending Requirements:</strong>
                    <ul className="list-disc list-inside space-y-1">
                      {overview.blocking_reasons.map((r, i) => (
                        <li key={i}>{r}</li>
                      ))}
                    </ul>
                  </div>
                ) : (
                  <>
                    <p className="text-slate-600">
                      All statutory documents and evidence checks have succeeded. Approving will transition the vendor to
                      <strong> APPROVED</strong> status and record your formal sign-off.
                    </p>
                    <div>
                      <label className="block font-semibold text-slate-700 uppercase tracking-wider mb-1">
                        Approval Notes / Master File Reference
                      </label>
                      <textarea
                        rows={2}
                        value={approveNotes}
                        onChange={(e) => setApproveNotes(e.target.value)}
                        placeholder="Optional approval notes or internal reference..."
                        className="w-full p-2 border border-slate-300 rounded-lg focus:outline-none"
                      />
                    </div>
                  </>
                )}
              </div>
            )}

            {/* Reject Modal Content */}
            {activeModal === 'REJECT' && (
              <div className="space-y-3 text-xs">
                <p className="text-slate-600">
                  Rejecting will officially decline this vendor onboarding application. A clear explanation is mandatory.
                </p>
                <div>
                  <label className="block font-semibold text-slate-700 uppercase tracking-wider mb-1">
                    Mandatory Rejection Reason *
                  </label>
                  <textarea
                    rows={3}
                    value={rejectReason}
                    onChange={(e) => setRejectReason(e.target.value)}
                    placeholder="Provide specific justification (e.g. failed statutory cross-verification, blacklisted PAN)..."
                    className="w-full p-2.5 border border-slate-300 rounded-lg focus:ring-2 focus:ring-rose-500 focus:outline-none"
                  />
                </div>
                <div>
                  <label className="block font-semibold text-slate-700 uppercase tracking-wider mb-1">
                    Internal Rejection Notes (Optional)
                  </label>
                  <textarea
                    rows={2}
                    value={rejectNotes}
                    onChange={(e) => setRejectNotes(e.target.value)}
                    placeholder="Optional internal justification or notes..."
                    className="w-full p-2 border border-slate-300 rounded-lg focus:outline-none"
                  />
                </div>
              </div>
            )}

            {/* Clarify Modal Content */}
            {activeModal === 'CLARIFY' && (
              <div className="space-y-3 text-xs">
                <p className="text-slate-600">
                  This will transition the application to <strong>ACTION REQUIRED</strong>, dispatch an in-app alert,
                  and allow the vendor to correct specific fields or upload replacement documents.
                </p>
                <div>
                  <label className="block font-semibold text-slate-700 uppercase tracking-wider mb-1">
                    Clarification Instructions for Vendor *
                  </label>
                  <textarea
                    rows={3}
                    value={clarifyInstructions}
                    onChange={(e) => setClarifyInstructions(e.target.value)}
                    placeholder="Specify the exact document or field correction needed..."
                    className="w-full p-2.5 border border-slate-300 rounded-lg focus:ring-2 focus:ring-amber-500 focus:outline-none"
                  />
                </div>
              </div>
            )}

            {/* Escalate Modal Content */}
            {activeModal === 'ESCALATE' && (
              <div className="space-y-3 text-xs">
                <div>
                  <label className="block font-semibold text-slate-700 uppercase tracking-wider mb-1">
                    Target Role
                  </label>
                  <select
                    value={escalateTargetRole}
                    onChange={(e) => setEscalateTargetRole(e.target.value)}
                    className="w-full p-2 border border-slate-300 rounded-lg focus:outline-none"
                  >
                    <option value="ADMIN">Organisation Administrator</option>
                    <option value="PROCUREMENT_OFFICER">Head of Procurement</option>
                  </select>
                </div>
                <div>
                  <label className="block font-semibold text-slate-700 uppercase tracking-wider mb-1">
                    Escalation Reason *
                  </label>
                  <textarea
                    rows={3}
                    value={escalateReason}
                    onChange={(e) => setEscalateReason(e.target.value)}
                    placeholder="Explain why this application requires higher authority sign-off..."
                    className="w-full p-2.5 border border-slate-300 rounded-lg focus:outline-none"
                  />
                </div>
              </div>
            )}

            {/* Modal Actions */}
            <div className="flex items-center justify-end gap-2 pt-2 border-t border-slate-100 text-xs">
              <button
                onClick={() => setActiveModal(null)}
                disabled={actionSubmitting}
                className="px-3 py-1.5 rounded-lg border border-slate-200 text-slate-600 hover:bg-slate-50"
              >
                Cancel
              </button>
              {activeModal === 'APPROVE' && overview.is_approval_eligible && (
                <button
                  onClick={handleApprove}
                  disabled={actionSubmitting}
                  className="px-4 py-1.5 rounded-lg font-semibold text-white bg-emerald-600 hover:bg-emerald-700 disabled:opacity-50"
                >
                  {actionSubmitting ? 'Approving...' : 'Confirm Approval'}
                </button>
              )}
              {activeModal === 'REJECT' && (
                <button
                  onClick={handleReject}
                  disabled={actionSubmitting}
                  className="px-4 py-1.5 rounded-lg font-semibold text-white bg-rose-600 hover:bg-rose-700 disabled:opacity-50"
                >
                  {actionSubmitting ? 'Rejecting...' : 'Confirm Rejection'}
                </button>
              )}
              {activeModal === 'CLARIFY' && (
                <button
                  onClick={handleClarify}
                  disabled={actionSubmitting}
                  className="px-4 py-1.5 rounded-lg font-semibold text-white bg-amber-600 hover:bg-amber-700 disabled:opacity-50"
                >
                  {actionSubmitting ? 'Sending...' : 'Send Clarification Request'}
                </button>
              )}
              {activeModal === 'ESCALATE' && (
                <button
                  onClick={handleEscalate}
                  disabled={actionSubmitting}
                  className="px-4 py-1.5 rounded-lg font-semibold text-white bg-slate-800 hover:bg-slate-900 disabled:opacity-50"
                >
                  {actionSubmitting ? 'Escalating...' : 'Confirm Escalation'}
                </button>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Safe Document Preview Drawer / Modal */}
      {previewUrl && (
        <div className="fixed inset-0 bg-slate-900/60 backdrop-blur-2xs z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl w-full max-w-4xl h-[85vh] flex flex-col shadow-2xl border border-slate-200 overflow-hidden">
            <div className="p-4 bg-slate-50 border-b border-slate-200 flex items-center justify-between">
              <span className="font-bold text-slate-900 text-sm">{previewTitle}</span>
              <button onClick={() => setPreviewUrl(null)} className="p-1 rounded text-slate-400 hover:text-slate-700">
                <X className="w-5 h-5" />
              </button>
            </div>
            <div className="flex-1 bg-slate-100 p-2">
              <iframe src={previewUrl} className="w-full h-full rounded border border-slate-200 bg-white" title={previewTitle} />
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
