import React, { useState } from 'react';
import type { Application, ApplicationDraftUpdate } from '../../types/application';
import { apiSubmitApplication } from '../../api/applications';
import { ValidationFindingsCard } from './ValidationFindingsCard';
import {
  AlertTriangle,
  Send,
  Building,
  FileCheck2,
  UserCheck,
  Landmark,
  FileText,
  ShieldCheck,
  Edit3,
  ArrowRight,
  RefreshCw,
} from 'lucide-react';

interface StepProps {
  token: string;
  application: Application;
  onGoToStep: (stepIndex: number) => void;
  onChange: (updates: ApplicationDraftUpdate) => void;
  onSubmitSuccess: (refNumber: string) => void;
}

interface MissingItem {
  message: string;
  stepIdx: number;
  stepLabel: string;
}

export const StepReviewSubmit: React.FC<StepProps> = ({
  token,
  application,
  onGoToStep,
  onChange,
  onSubmitSuccess,
}) => {
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [structuredErrors, setStructuredErrors] = useState<MissingItem[]>([]);

  const mandatoryDocs = (application.documents || []).filter((d) => d.is_required);
  const missingDocs = mandatoryDocs.filter((d) => d.status !== 'UPLOADED');

  // Compute missing requirements aligned 100% with backend submission rules
  const missingItems: MissingItem[] = [];

  // Step 1: Business Identity
  if (!application.legal_name || !application.legal_name.trim()) {
    missingItems.push({ message: 'Legal Business Name is required', stepIdx: 0, stepLabel: 'Step 1: Business Identity' });
  }
  if (!application.constitution) {
    missingItems.push({ message: 'Legal Constitution must be selected', stepIdx: 0, stepLabel: 'Step 1: Business Identity' });
  }
  if (!application.registered_address || !application.registered_address.trim()) {
    missingItems.push({ message: 'Registered Address is required', stepIdx: 0, stepLabel: 'Step 1: Business Identity' });
  }
  if (!application.city || !application.city.trim()) {
    missingItems.push({ message: 'City is required', stepIdx: 0, stepLabel: 'Step 1: Business Identity' });
  }
  if (!application.state || !application.state.trim()) {
    missingItems.push({ message: 'State / Union Territory is required', stepIdx: 0, stepLabel: 'Step 1: Business Identity' });
  }
  if (!application.pincode || !/^\d{6}$/.test(application.pincode.trim())) {
    missingItems.push({ message: 'PIN Code must be a 6-digit number', stepIdx: 0, stepLabel: 'Step 1: Business Identity' });
  }

  // Step 2: Tax & Registration
  if (!application.pan || !/^[A-Z]{5}[0-9]{4}[A-Z]{1}$/.test(application.pan.trim().toUpperCase())) {
    missingItems.push({ message: 'Valid 10-character statutory PAN is required', stepIdx: 1, stepLabel: 'Step 2: Tax & Registration' });
  }
  if (application.is_gst_registered) {
    const gstRegex = /^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$/;
    if (!application.gstin || !gstRegex.test(application.gstin.trim().toUpperCase())) {
      missingItems.push({ message: 'Valid 15-character statutory GSTIN is required when declared GST registered', stepIdx: 1, stepLabel: 'Step 2: Tax & Registration' });
    }
  }
  if (application.is_udyam_registered && (!application.udyam_number || !application.udyam_number.trim())) {
    missingItems.push({ message: 'Udyam Registration Number is required when MSME registered', stepIdx: 1, stepLabel: 'Step 2: Tax & Registration' });
  }
  if (['PVT_LTD', 'PUB_LTD', 'LLP'].includes(application.constitution)) {
    if (!application.cin_llpin || !application.cin_llpin.trim()) {
      missingItems.push({
        message: `${application.constitution === 'LLP' ? 'LLPIN' : 'CIN'} is required for ${application.constitution.replace(/_/g, ' ')}`,
        stepIdx: 1,
        stepLabel: 'Step 2: Tax & Registration',
      });
    }
  }

  // Step 3: Authorised Contact
  if (!application.contact_name || !application.contact_name.trim()) {
    missingItems.push({ message: 'Contact Person Name is required', stepIdx: 2, stepLabel: 'Step 3: Authorised Contact' });
  }
  if (!application.contact_email || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(application.contact_email.trim())) {
    missingItems.push({ message: 'Valid Contact Email is required', stepIdx: 2, stepLabel: 'Step 3: Authorised Contact' });
  }
  if (!application.contact_mobile || !/^(?:\+91|0)?[6-9]\d{9}$/.test(application.contact_mobile.trim().replace(/[\s-]/g, ''))) {
    missingItems.push({ message: 'Valid 10-digit Indian Mobile Number is required', stepIdx: 2, stepLabel: 'Step 3: Authorised Contact' });
  }

  // Step 4: Banking Details
  if (!application.bank_account_holder_name || !application.bank_account_holder_name.trim()) {
    missingItems.push({ message: 'Bank Account Holder Name is required', stepIdx: 3, stepLabel: 'Step 4: Banking Details' });
  }
  if (!application.bank_account_number || !application.bank_account_number.trim()) {
    missingItems.push({ message: 'Bank Account Number is required', stepIdx: 3, stepLabel: 'Step 4: Banking Details' });
  }
  if (!application.bank_ifsc || !/^[A-Z]{4}0[A-Z0-9]{6}$/.test(application.bank_ifsc.trim().toUpperCase())) {
    missingItems.push({ message: 'Valid 11-character RBI IFSC Code is required', stepIdx: 3, stepLabel: 'Step 4: Banking Details' });
  }

  // Step 5: Business Classification
  if (!application.categories || application.categories.length === 0) {
    missingItems.push({ message: 'Select at least one business classification activity', stepIdx: 4, stepLabel: 'Step 5: Business Classification' });
  }

  // Step 6: Mandatory Documents
  missingDocs.forEach((doc) => {
    missingItems.push({ message: `Mandatory document required: ${doc.title}`, stepIdx: 5, stepLabel: 'Step 6: Document Checklist' });
  });

  const hasMissing = missingItems.length > 0;
  const allDeclarationsChecked =
    Boolean(application.declaration_accurate_info) &&
    Boolean(application.declaration_authorised_rep) &&
    Boolean(application.declaration_verification_consent);

  const mapBackendErrorToStep = (errStr: string): MissingItem => {
    const lower = errStr.toLowerCase();
    let stepIdx = 0;
    let stepLabel = 'Step 1: Business Identity';

    if (lower.includes('step 2') || lower.includes('section 2') || lower.includes('pan') || lower.includes('gstin') || lower.includes('udyam') || lower.includes('cin') || lower.includes('llpin')) {
      stepIdx = 1;
      stepLabel = 'Step 2: Tax & Registration';
    } else if (lower.includes('step 3') || lower.includes('section 3') || lower.includes('contact') || lower.includes('email') || lower.includes('mobile')) {
      stepIdx = 2;
      stepLabel = 'Step 3: Authorised Contact';
    } else if (lower.includes('step 4') || lower.includes('section 4') || lower.includes('bank') || lower.includes('ifsc') || lower.includes('account')) {
      stepIdx = 3;
      stepLabel = 'Step 4: Banking Details';
    } else if (lower.includes('step 5') || lower.includes('section 5') || lower.includes('classification') || lower.includes('activity')) {
      stepIdx = 4;
      stepLabel = 'Step 5: Business Classification';
    } else if (lower.includes('step 6') || lower.includes('document') || lower.includes('checklist')) {
      stepIdx = 5;
      stepLabel = 'Step 6: Document Checklist';
    } else if (lower.includes('step 7') || lower.includes('declaration')) {
      stepIdx = 6;
      stepLabel = 'Step 7: Declarations';
    }

    return { message: errStr, stepIdx, stepLabel };
  };

  const handleSubmit = async () => {
    if (isSubmitting) return;

    if (hasMissing) {
      setStructuredErrors(missingItems);
      setSubmitError('Please complete all mandatory information and document uploads before submitting.');
      return;
    }
    if (!allDeclarationsChecked) {
      setSubmitError('Please review and confirm all three statutory declarations below to proceed.');
      return;
    }

    setIsSubmitting(true);
    setSubmitError(null);
    setStructuredErrors([]);

    try {
      const res = await apiSubmitApplication(token, application.id);
      onSubmitSuccess(res.reference_number);
    } catch (err: any) {
      setIsSubmitting(false);
      const rawErrors = err?.errors || [];
      if (Array.isArray(rawErrors) && rawErrors.length > 0) {
        setStructuredErrors(rawErrors.map(mapBackendErrorToStep));
        setSubmitError(err?.message || 'Submission blocked by compliance requirements.');
      } else {
        setSubmitError(err?.message || 'Failed to submit onboarding application.');
      }
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h3 className="text-base font-bold text-slate-900 flex items-center gap-2">
          <ShieldCheck className="w-5 h-5 text-indigo-600" />
          Section 7: Review Application & Final Declarations
        </h3>
        <p className="text-xs text-slate-500 mt-1">
          Review all submitted details and uploaded statutory evidence before final submission. Once
          submitted, the application is locked for buyer verification.
        </p>
      </div>

      {/* Submission Blocked Alert with Actionable Deep-links */}
      {(submitError || structuredErrors.length > 0) && (
        <div className="p-4 rounded-xl bg-rose-50 border border-rose-200 text-xs text-rose-800 space-y-2.5 shadow-2xs">
          <div className="flex items-start gap-2.5">
            <AlertTriangle className="w-4 h-4 text-rose-600 shrink-0 mt-0.5" />
            <div>
              <span className="font-bold">Submission Blocked:</span>
              <p className="mt-0.5">{submitError || 'Requirements missing before submission.'}</p>
            </div>
          </div>

          {structuredErrors.length > 0 && (
            <div className="pt-2 border-t border-rose-200/60 space-y-1.5 pl-6">
              <span className="font-semibold text-rose-900 block text-[11px] uppercase tracking-wider">
                Actionable Items Requiring Completion:
              </span>
              <div className="space-y-1">
                {structuredErrors.map((item, idx) => (
                  <div
                    key={idx}
                    className="flex flex-col sm:flex-row sm:items-center justify-between gap-1.5 p-2 rounded-lg bg-white/80 border border-rose-200"
                  >
                    <span className="text-slate-800 font-medium">{item.message}</span>
                    <button
                      type="button"
                      onClick={() => onGoToStep(item.stepIdx)}
                      className="inline-flex items-center gap-1 text-[11px] font-bold text-indigo-600 hover:text-indigo-800 shrink-0 self-start sm:self-auto px-2 py-0.5 rounded bg-indigo-50 border border-indigo-200"
                    >
                      <span>Fix in {item.stepLabel}</span>
                      <ArrowRight className="w-3 h-3" />
                    </button>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Missing Requirements Pre-flight Callout */}
      {!submitError && hasMissing && (
        <div className="p-4 rounded-xl bg-amber-50 border border-amber-200 text-xs text-amber-900 space-y-2.5 shadow-2xs">
          <div className="font-bold flex items-center gap-1.5">
            <AlertTriangle className="w-4 h-4 text-amber-600" />
            <span>Mandatory Requirements Incomplete ({missingItems.length})</span>
          </div>
          <div className="space-y-1">
            {missingItems.map((item, idx) => (
              <div
                key={idx}
                className="flex flex-col sm:flex-row sm:items-center justify-between gap-1 p-2 rounded-lg bg-white/70 border border-amber-200/80"
              >
                <span className="text-slate-800 font-medium">{item.message}</span>
                <button
                  type="button"
                  onClick={() => onGoToStep(item.stepIdx)}
                  className="inline-flex items-center gap-1 text-[11px] font-bold text-amber-800 hover:text-amber-950 shrink-0 self-start sm:self-auto px-2 py-0.5 rounded bg-amber-100 border border-amber-300"
                >
                  <span>Go to {item.stepLabel}</span>
                  <ArrowRight className="w-3 h-3" />
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Review Summary Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Card 1: Business Identity */}
        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-2xs space-y-2 relative">
          <div className="flex items-center justify-between border-b border-slate-100 pb-2">
            <h4 className="text-xs font-bold text-slate-900 flex items-center gap-1.5">
              <Building className="w-4 h-4 text-indigo-600" />
              1. Business Identity
            </h4>
            <button
              type="button"
              onClick={() => onGoToStep(0)}
              className="text-[11px] text-indigo-600 hover:text-indigo-800 font-semibold inline-flex items-center gap-1"
            >
              <Edit3 className="w-3 h-3" /> Edit
            </button>
          </div>
          <div className="text-xs text-slate-600 space-y-1">
            <div>
              <span className="text-slate-400">Legal Name:</span>{' '}
              <span className="font-semibold text-slate-900">{application.legal_name || '—'}</span>
            </div>
            <div>
              <span className="text-slate-400">Trade Name:</span> {application.trade_name || '—'}
            </div>
            <div>
              <span className="text-slate-400">Constitution:</span>{' '}
              <span className="font-medium text-slate-800">
                {application.constitution?.replace(/_/g, ' ') || '—'}
              </span>
            </div>
            <div>
              <span className="text-slate-400">Establishment:</span>{' '}
              {application.date_of_establishment || '—'}
            </div>
            <div className="truncate">
              <span className="text-slate-400">Address:</span> {application.registered_address || '—'}
            </div>
            <div>
              <span className="text-slate-400">City / State:</span>{' '}
              {application.city && application.state
                ? `${application.city}, ${application.state} - ${application.pincode || ''}`
                : '—'}
            </div>
          </div>
        </div>

        {/* Card 2: Tax & Statutory Registration */}
        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-2xs space-y-2 relative">
          <div className="flex items-center justify-between border-b border-slate-100 pb-2">
            <h4 className="text-xs font-bold text-slate-900 flex items-center gap-1.5">
              <FileCheck2 className="w-4 h-4 text-indigo-600" />
              2. Tax & Statutory Registration
            </h4>
            <button
              type="button"
              onClick={() => onGoToStep(1)}
              className="text-[11px] text-indigo-600 hover:text-indigo-800 font-semibold inline-flex items-center gap-1"
            >
              <Edit3 className="w-3 h-3" /> Edit
            </button>
          </div>
          <div className="text-xs text-slate-600 space-y-1">
            <div>
              <span className="text-slate-400">PAN:</span>{' '}
              <span className="font-mono font-semibold text-slate-900">{application.pan || '—'}</span>
            </div>
            <div>
              <span className="text-slate-400">GST Registration:</span>{' '}
              <span className="font-semibold">
                {application.is_gst_registered ? (
                  <span className="text-indigo-700">Registered</span>
                ) : (
                  <span className="text-slate-500">Not Registered / Below Threshold</span>
                )}
              </span>
            </div>
            {application.is_gst_registered && (
              <div>
                <span className="text-slate-400">GSTIN:</span>{' '}
                <span className="font-mono">{application.gstin || '—'}</span>
              </div>
            )}
            <div>
              <span className="text-slate-400">MSME / Udyam:</span>{' '}
              {application.is_udyam_registered ? application.udyam_number || 'Registered' : 'Not Claimed'}
            </div>
            {['PVT_LTD', 'PUB_LTD', 'LLP'].includes(application.constitution) && (
              <div>
                <span className="text-slate-400">{application.constitution === 'LLP' ? 'LLPIN:' : 'CIN:'}</span>{' '}
                <span className="font-mono">{application.cin_llpin || '—'}</span>
              </div>
            )}
          </div>
        </div>

        {/* Card 3: Authorised Contact */}
        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-2xs space-y-2 relative">
          <div className="flex items-center justify-between border-b border-slate-100 pb-2">
            <h4 className="text-xs font-bold text-slate-900 flex items-center gap-1.5">
              <UserCheck className="w-4 h-4 text-indigo-600" />
              3. Authorised Contact
            </h4>
            <button
              type="button"
              onClick={() => onGoToStep(2)}
              className="text-[11px] text-indigo-600 hover:text-indigo-800 font-semibold inline-flex items-center gap-1"
            >
              <Edit3 className="w-3 h-3" /> Edit
            </button>
          </div>
          <div className="text-xs text-slate-600 space-y-1">
            <div>
              <span className="text-slate-400">Name:</span>{' '}
              <span className="font-semibold text-slate-900">{application.contact_name || '—'}</span>
            </div>
            <div>
              <span className="text-slate-400">Designation:</span>{' '}
              {application.contact_designation || '—'}
            </div>
            <div>
              <span className="text-slate-400">Email:</span> {application.contact_email || '—'}
            </div>
            <div>
              <span className="text-slate-400">Mobile:</span> {application.contact_mobile || '—'}
            </div>
            <div>
              <span className="text-slate-400">Signatory:</span>{' '}
              {application.authorised_signatory_name || application.contact_name || '—'}
            </div>
          </div>
        </div>

        {/* Card 4: Banking Details */}
        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-2xs space-y-2 relative">
          <div className="flex items-center justify-between border-b border-slate-100 pb-2">
            <h4 className="text-xs font-bold text-slate-900 flex items-center gap-1.5">
              <Landmark className="w-4 h-4 text-indigo-600" />
              4. Banking Details
            </h4>
            <button
              type="button"
              onClick={() => onGoToStep(3)}
              className="text-[11px] text-indigo-600 hover:text-indigo-800 font-semibold inline-flex items-center gap-1"
            >
              <Edit3 className="w-3 h-3" /> Edit
            </button>
          </div>
          <div className="text-xs text-slate-600 space-y-1">
            <div>
              <span className="text-slate-400">Holder Name:</span>{' '}
              <span className="font-semibold text-slate-900">
                {application.bank_account_holder_name || '—'}
              </span>
            </div>
            <div>
              <span className="text-slate-400">Account No:</span>{' '}
              <span className="font-mono">{application.bank_account_number || '—'}</span>
            </div>
            <div>
              <span className="text-slate-400">IFSC:</span>{' '}
              <span className="font-mono">{application.bank_ifsc || '—'}</span>
            </div>
            <div>
              <span className="text-slate-400">Account Type:</span> {application.bank_account_type || 'CURRENT'}
            </div>
          </div>
        </div>
      </div>

      {/* Document Uploads Summary with Clear Semantic Statuses */}
      <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-2xs space-y-3">
        <div className="flex items-center justify-between border-b border-slate-100 pb-2">
          <h4 className="text-xs font-bold text-slate-900 flex items-center gap-1.5">
            <FileText className="w-4 h-4 text-indigo-600" />
            Checklist Status ({mandatoryDocs.length - missingDocs.length} / {mandatoryDocs.length} Mandatory Uploaded)
          </h4>
          <button
            type="button"
            onClick={() => onGoToStep(5)}
            className="text-[11px] text-indigo-600 hover:text-indigo-800 font-semibold inline-flex items-center gap-1"
          >
            <Edit3 className="w-3 h-3" /> Manage Documents
          </button>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-xs">
          {(application.documents || []).map((doc) => {
            const isUploaded = doc.status === 'UPLOADED';
            const isMismatch = doc.is_type_match === false || doc.processing_status === 'NEEDS_REVIEW';
            const isProcessing = doc.processing_status === 'PROCESSING' || doc.processing_status === 'QUEUED';

            return (
              <div
                key={doc.id}
                className="flex items-center justify-between p-2 rounded-lg bg-slate-50 border border-slate-100"
              >
                <span className="font-medium text-slate-800 truncate mr-2">{doc.title}</span>
                {isUploaded ? (
                  isMismatch ? (
                    <span className="text-[10px] font-semibold text-amber-800 bg-amber-50 px-2 py-0.5 rounded border border-amber-300 shrink-0">
                      Needs Attention (v{doc.current_version?.version_number || 1})
                    </span>
                  ) : isProcessing ? (
                    <span className="text-[10px] font-semibold text-blue-700 bg-blue-50 px-2 py-0.5 rounded border border-blue-200 shrink-0">
                      Processing OCR...
                    </span>
                  ) : (
                    <span className="text-[10px] font-semibold text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded border border-emerald-200 shrink-0">
                      Uploaded &amp; Parsed (v{doc.current_version?.version_number || 1})
                    </span>
                  )
                ) : doc.is_required ? (
                  <span className="text-[10px] font-semibold text-rose-700 bg-rose-50 px-2 py-0.5 rounded border border-rose-200 shrink-0">
                    Missing (Required)
                  </span>
                ) : (
                  <span className="text-[10px] font-medium text-slate-400 shrink-0">Optional / Not Applicable</span>
                )}
              </div>
            );
          })}
        </div>
      </div>

      {/* Deterministic Validation & Consistency Results */}
      <ValidationFindingsCard token={token} applicationId={application.id} />

      {/* Mandatory Statutory Declarations */}
      <div className="bg-slate-50 border border-slate-200 rounded-xl p-5 space-y-3">
        <h4 className="text-xs font-bold text-slate-900 uppercase tracking-wider">
          Statutory Declarations &amp; Vendor Consent <span className="text-rose-500">*</span>
        </h4>

        <div className="space-y-3 text-xs text-slate-700">
          <label className="flex items-start gap-3 cursor-pointer">
            <input
              type="checkbox"
              checked={Boolean(application.declaration_accurate_info)}
              onChange={(e) => onChange({ declaration_accurate_info: e.target.checked })}
              className="mt-0.5 h-4 w-4 text-indigo-600 rounded border-slate-300 focus:ring-indigo-500"
            />
            <span>
              <strong>Accuracy Declaration:</strong> I certify that all information submitted in this
              onboarding application, including statutory PAN, GST, MSME, and bank account numbers, is
              true, complete, and accurate to the best of my knowledge.
            </span>
          </label>

          <label className="flex items-start gap-3 cursor-pointer">
            <input
              type="checkbox"
              checked={Boolean(application.declaration_authorised_rep)}
              onChange={(e) => onChange({ declaration_authorised_rep: e.target.checked })}
              className="mt-0.5 h-4 w-4 text-indigo-600 rounded border-slate-300 focus:ring-indigo-500"
            />
            <span>
              <strong>Authorised Representation:</strong> I confirm that I am duly authorised to represent
              and submit this onboarding application on behalf of the commercial entity named herein.
            </span>
          </label>

          <label className="flex items-start gap-3 cursor-pointer">
            <input
              type="checkbox"
              checked={Boolean(application.declaration_verification_consent)}
              onChange={(e) => onChange({ declaration_verification_consent: e.target.checked })}
              className="mt-0.5 h-4 w-4 text-indigo-600 rounded border-slate-300 focus:ring-indigo-500"
            />
            <span>
              <strong>Verification Consent:</strong> I acknowledge the buyer&rsquo;s vendor due-diligence
              process and consent to the lawful external verification of submitted PAN, GSTIN, MSME, and
              beneficiary bank account details for vendor panel onboarding.
            </span>
          </label>
        </div>
      </div>

      {/* Submit Button */}
      <div className="pt-2 flex justify-end">
        <button
          type="button"
          disabled={isSubmitting || hasMissing || !allDeclarationsChecked}
          onClick={handleSubmit}
          className="flex items-center gap-2 px-6 py-3 rounded-xl text-sm font-bold text-white bg-indigo-600 hover:bg-indigo-700 shadow-md disabled:opacity-40 disabled:pointer-events-none transition-all"
        >
          {isSubmitting ? (
            <>
              <RefreshCw className="w-4 h-4 animate-spin" />
              <span>Submitting Application...</span>
            </>
          ) : (
            <>
              <Send className="w-4 h-4" />
              <span>Submit Application for Review</span>
            </>
          )}
        </button>
      </div>
    </div>
  );
};
