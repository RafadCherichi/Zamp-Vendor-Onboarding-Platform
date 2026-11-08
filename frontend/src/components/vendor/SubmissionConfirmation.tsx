import React from 'react';
import type { Application } from '../../types/application';
import { CheckCircle2, Clock, Lock, Copy, Check, XCircle, ShieldAlert } from 'lucide-react';
import { VendorExceptionsBanner } from './VendorExceptionsBanner';
import { apiFetchValidation } from '../../api/validation';
import type { ValidationRun } from '../../types/validation';

interface Props {
  application: Application;
  token?: string;
  onRefresh?: () => void;
}

export const SubmissionConfirmation: React.FC<Props> = ({ application, token, onRefresh }) => {
  const [copied, setCopied] = React.useState(false);
  const [providerUnavailable, setProviderUnavailable] = React.useState(false);
  const [validationRun, setValidationRun] = React.useState<ValidationRun | null>(null);

  React.useEffect(() => {
    if (!token) {
      return;
    }
    let active = true;
    apiFetchValidation(token, application.id)
      .then((run) => {
        if (active) {
          setValidationRun(run);
          setProviderUnavailable(run.findings.some((finding) =>
            finding.check_id.startsWith('C_') && finding.status === 'UNAVAILABLE'
          ));
        }
      })
      .catch(() => { if (active) { setProviderUnavailable(false); setValidationRun(null); } });
    return () => { active = false; };
  }, [token, application.id, application.status, application.updated_at]);

  const handleCopy = () => {
    navigator.clipboard.writeText(application.reference_number);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const isApproved = application.status === 'APPROVED';
  const isRejected = application.status === 'REJECTED';
  const isActionRequired = application.status === 'ACTION_REQUIRED';
  const isInReview = application.status === 'SUBMITTED' || application.status === 'UNDER_REVIEW';

  const getFriendlyStatusText = () => {
    if (isApproved) return 'Approved';
    if (isRejected) return 'Not Approved';
    if (isActionRequired) return 'Action Needed';
    return 'Under Review';
  };

  return (
    <div className="max-w-3xl mx-auto space-y-6 py-4">
      {/* Priority Vendor Exception Clarifications & Corrections */}
      {!isRejected && !isApproved && (
        <VendorExceptionsBanner
          token={token}
          applicationId={application.id}
          onCorrectionSubmitted={onRefresh || (() => {})}
        />
      )}

      <div className="bg-white rounded-2xl border border-slate-200 p-6 sm:p-8 text-left space-y-4">
        {/* Status Icon */}
        {isApproved ? (
          <div className="w-10 h-10 rounded-lg bg-emerald-100 text-emerald-600 flex items-center justify-center">
            <CheckCircle2 className="w-6 h-6" />
          </div>
        ) : isRejected ? (
          <div className="w-10 h-10 rounded-lg bg-rose-100 text-rose-600 flex items-center justify-center">
            <XCircle className="w-6 h-6" />
          </div>
        ) : isActionRequired ? (
          <div className="w-10 h-10 rounded-lg bg-amber-100 text-amber-600 flex items-center justify-center">
            <ShieldAlert className="w-6 h-6" />
          </div>
        ) : (
          <div className="w-10 h-10 rounded-lg bg-indigo-100 text-indigo-600 flex items-center justify-center">
            <CheckCircle2 className="w-6 h-6" />
          </div>
        )}

        <div>
          <span
            className={`text-xs font-bold uppercase tracking-wider px-3 py-1 rounded-full border ${
              isApproved
                ? 'text-emerald-700 bg-emerald-50 border-emerald-200'
                : isRejected
                ? 'text-rose-700 bg-rose-50 border-rose-200'
                : isActionRequired
                ? 'text-amber-700 bg-amber-50 border-amber-200'
                : 'text-indigo-700 bg-indigo-50 border-indigo-200'
            }`}
          >
            Application Status: {getFriendlyStatusText()}
          </span>

          <h2 className="text-2xl font-semibold text-slate-900 mt-3">
            {isApproved
              ? 'Onboarding Application Approved!'
              : isRejected
              ? 'Onboarding Application Declined'
              : isActionRequired
              ? 'Action Required on Your Application'
              : 'Thank You! Application Submitted Successfully'}
          </h2>

          <p className="text-sm text-slate-600 max-w-lg mt-2 leading-relaxed">
            {isApproved
              ? `The review team has approved the application for ${application.legal_name}. Keep this reference for your records.`
              : isRejected
              ? `Your application for ${application.legal_name} could not be approved at this time. Please review the reason below.`
              : isActionRequired
              ? 'We need one more detail before review can continue. Follow the request above and send your response.'
              : `Your application for ${application.legal_name} has been received. The review team is checking your details and documents.`}
          </p>
        </div>

        {providerUnavailable && !isApproved && !isRejected && (
          <div className="max-w-lg p-4 border border-slate-200 bg-slate-50 rounded-lg text-left">
            <p className="text-sm font-semibold text-slate-900">A verification service is temporarily unavailable</p>
            <p className="text-sm text-slate-600 mt-1 leading-relaxed">
              Our team will retry the check. You do not need to upload the same document again.
            </p>
          </div>
        )}

        {/* If Rejected, display mandatory rejection reason */}
        {isRejected && application.rejection_reason && (
          <div className="bg-rose-50 border border-rose-200 rounded-xl p-4 max-w-lg text-left space-y-1">
            <span className="text-[11px] font-bold text-rose-800 uppercase tracking-wider block">
              Official Reason for Decision
            </span>
            <p className="text-sm text-rose-900 leading-relaxed font-medium">
              {application.rejection_reason}
            </p>
            <p className="text-[11px] text-rose-600 pt-1">
              For questions or appeals, please contact your procurement representative.
            </p>
          </div>
        )}

        {/* Reference Number Card */}
        <div className="bg-slate-50 p-4 rounded-xl border border-slate-200 max-w-md space-y-1">
          <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider">
            Official Application Reference
          </span>
          <div className="flex items-center justify-center gap-2">
            <span className="text-lg font-mono font-semibold text-indigo-700">
              {application.reference_number}
            </span>
            <button
              onClick={handleCopy}
              className="p-1 rounded text-slate-400 hover:text-slate-600 hover:bg-slate-200 transition"
              title="Copy Reference Number"
            >
              {copied ? <Check className="w-4 h-4 text-emerald-600" /> : <Copy className="w-4 h-4" />}
            </button>
          </div>
          <div className="text-[11px] text-slate-400">
            {isApproved && application.reviewed_at ? (
              <span>Approved at: {new Date(application.reviewed_at).toLocaleString()}</span>
            ) : application.submitted_at ? (
              <span>Submitted at: {new Date(application.submitted_at).toLocaleString()}</span>
            ) : (
              <span>Registered in system</span>
            )}
          </div>
        </div>

        {/* Locked Notice */}
        {!isApproved && !isRejected && (
          <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-200 text-xs text-slate-600 max-w-lg mx-auto flex items-center justify-center gap-2">
            <Lock className="w-4 h-4 text-slate-400 shrink-0" />
            <span>
              {isActionRequired
                ? 'Field edits are restricted to items highlighted in the clarification notice above.'
                : 'This application is locked while our compliance team reviews your information.'}
            </span>
          </div>
        )}
      </div>

      {/* State-Aware 4-Step Onboarding Progress Tracker */}
      <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-2xs space-y-5">
        <div>
            <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2">
            <Clock className="w-4 h-4 text-indigo-600" />
            Application status
          </h3>
          <p className="text-xs text-slate-500 mt-0.5">
            See what has happened so far. The checks run on your submitted details; a person makes the final decision.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
          {/* Step 1: Application Received */}
          <div className="p-3.5 rounded-xl bg-emerald-50/50 border border-emerald-200 space-y-1.5 relative">
            <div className="flex items-center gap-2">
              <span className="w-6 h-6 rounded-full bg-emerald-600 text-white flex items-center justify-center text-xs font-bold shrink-0">
                ✓
              </span>
              <span className="font-bold text-slate-900 text-xs">1. Application Received</span>
            </div>
            <p className="text-[11px] text-slate-500 pl-8">
              {application.submitted_at
                ? `Submitted on ${new Date(application.submitted_at).toLocaleDateString()}`
                : 'Successfully received'}
            </p>
          </div>

          {/* Step 2: Automated document and data checks */}
          <div
            className={`p-3.5 rounded-xl border space-y-1.5 relative ${
              isApproved
                ? 'bg-emerald-50/50 border-emerald-200'
                : isRejected
                ? 'bg-slate-50 border-slate-200'
                : isInReview || isActionRequired
                ? 'bg-indigo-50/40 border-indigo-200 ring-1 ring-indigo-300'
                : 'bg-slate-50 border-slate-200'
            }`}
          >
            <div className="flex items-center gap-2">
              <span
                className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold shrink-0 ${
                  isApproved
                    ? 'bg-emerald-600 text-white'
                    : isInReview || isActionRequired
                    ? 'bg-indigo-600 text-white'
                    : 'bg-slate-200 text-slate-600'
                }`}
              >
                {isApproved ? '✓' : '2'}
              </span>
              <span className="font-bold text-slate-900 text-xs">2. Automated checks</span>
            </div>
            <p className="text-[11px] text-slate-500 pl-8">
              {isApproved
                ? 'Checks completed before approval'
                : validationRun
                ? validationRun.failed_count + validationRun.unverified_count + validationRun.unavailable_count + validationRun.warning_count === 0
                  ? `All ${validationRun.passed_count} checks passed`
                  : `${validationRun.passed_count} passed · ${validationRun.failed_count + validationRun.unverified_count + validationRun.unavailable_count + validationRun.warning_count} need review`
                : 'Your submitted documents and details are being checked'}
            </p>
          </div>

          {/* Step 3: Clarifications (if any) */}
          <div
            className={`p-3.5 rounded-xl border space-y-1.5 relative ${
              isActionRequired
                ? 'bg-amber-50 border-amber-300 ring-1 ring-amber-400'
                : isApproved
                ? 'bg-emerald-50/50 border-emerald-200'
                : 'bg-slate-50 border-slate-200 opacity-80'
            }`}
          >
            <div className="flex items-center gap-2">
              <span
                className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold shrink-0 ${
                  isActionRequired
                    ? 'bg-amber-600 text-white animate-pulse'
                    : isApproved
                    ? 'bg-emerald-600 text-white'
                    : 'bg-slate-200 text-slate-600'
                }`}
              >
                {isApproved ? '✓' : isActionRequired ? '!' : '3'}
              </span>
              <span className="font-bold text-slate-900 text-xs">3. Clarifications</span>
            </div>
            <p className="text-[11px] text-slate-500 pl-8">
              {isActionRequired
                ? 'We have asked you for more information'
                : isApproved
                ? 'No vendor follow-up is outstanding'
                : isRejected
                ? 'No further information is needed for this decision'
                : 'We will contact you here if anything is missing'}
            </p>
          </div>

          {/* Step 4: Final Decision */}
          <div
            className={`p-3.5 rounded-xl border space-y-1.5 relative ${
              isApproved
                ? 'bg-emerald-50/50 border-emerald-200'
                : isRejected
                ? 'bg-rose-50 border-rose-200'
                : 'bg-slate-50 border-slate-200 opacity-80'
            }`}
          >
            <div className="flex items-center gap-2">
              <span
                className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold shrink-0 ${
                  isApproved
                    ? 'bg-emerald-600 text-white'
                    : isRejected
                    ? 'bg-rose-600 text-white'
                    : 'bg-slate-200 text-slate-600'
                }`}
              >
                {isApproved ? '✓' : isRejected ? '✕' : '4'}
              </span>
              <span className="font-bold text-slate-900 text-xs">4. Final Decision</span>
            </div>
            <p className="text-[11px] text-slate-500 pl-8">
              {isApproved
                ? 'Approved & active on vendor panel'
                : isRejected
                ? 'Application not approved'
                : 'A reviewer will record the final decision'}
            </p>
          </div>
        </div>

        <div className="p-4 rounded-xl bg-slate-50 border border-slate-200 space-y-2 text-sm">
          <span className="font-semibold text-slate-800 block">What happens next?</span>
          <p className="text-slate-600 leading-relaxed">
            {isRejected
              ? 'This decision is final in this application. Contact your procurement representative if you need the reason explained or want the decision reviewed.'
              : isApproved
              ? 'Keep your application reference. Your procurement representative will contact you about the next business step.'
              : isActionRequired
              ? 'Send the corrected detail or document above. The review team will check your response and update this page.'
              : 'The review team is checking your details. If we need anything else, a request will appear here.'}
          </p>
        </div>
      </div>
    </div>
  );
};
