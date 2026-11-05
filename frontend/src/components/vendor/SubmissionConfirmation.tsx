import React from 'react';
import type { Application } from '../../types/application';
import { CheckCircle2, Clock, Lock, Copy, Check, XCircle, ShieldAlert } from 'lucide-react';
import { VendorExceptionsBanner } from './VendorExceptionsBanner';

interface Props {
  application: Application;
  token?: string;
  onRefresh?: () => void;
}

export const SubmissionConfirmation: React.FC<Props> = ({ application, token, onRefresh }) => {
  const [copied, setCopied] = React.useState(false);

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
    <div className="max-w-3xl mx-auto space-y-6 py-6">
      {/* Priority Vendor Exception Clarifications & Corrections */}
      <VendorExceptionsBanner
        token={token}
        applicationId={application.id}
        onCorrectionSubmitted={onRefresh || (() => {})}
      />

      <div className="bg-white rounded-2xl border border-slate-200 p-8 shadow-sm text-center space-y-4">
        {/* Status Icon */}
        {isApproved ? (
          <div className="w-16 h-16 rounded-2xl bg-emerald-100 text-emerald-600 flex items-center justify-center mx-auto shadow-inner">
            <CheckCircle2 className="w-10 h-10" />
          </div>
        ) : isRejected ? (
          <div className="w-16 h-16 rounded-2xl bg-rose-100 text-rose-600 flex items-center justify-center mx-auto shadow-inner">
            <XCircle className="w-10 h-10" />
          </div>
        ) : isActionRequired ? (
          <div className="w-16 h-16 rounded-2xl bg-amber-100 text-amber-600 flex items-center justify-center mx-auto shadow-inner">
            <ShieldAlert className="w-10 h-10" />
          </div>
        ) : (
          <div className="w-16 h-16 rounded-2xl bg-indigo-100 text-indigo-600 flex items-center justify-center mx-auto shadow-inner">
            <CheckCircle2 className="w-10 h-10" />
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

          <h2 className="text-2xl font-extrabold text-slate-900 mt-3">
            {isApproved
              ? 'Onboarding Application Approved!'
              : isRejected
              ? 'Onboarding Application Declined'
              : isActionRequired
              ? 'Action Required on Your Application'
              : 'Thank You! Application Submitted Successfully'}
          </h2>

          <p className="text-xs text-slate-500 max-w-lg mx-auto mt-1">
            {isApproved
              ? `Congratulations, ${application.legal_name}. Your vendor registration has passed all statutory checks and your vendor record is active.`
              : isRejected
              ? `Your application for ${application.legal_name} could not be approved at this time. Please review the reason below.`
              : isActionRequired
              ? 'Our compliance team has requested clarification or a replacement document. Please review the notice above.'
              : `Your onboarding application for ${application.legal_name} has been received. Our compliance team is reviewing your documents and statutory registrations.`}
          </p>
        </div>

        {/* If Rejected, display mandatory rejection reason */}
        {isRejected && application.rejection_reason && (
          <div className="bg-rose-50 border border-rose-200 rounded-xl p-4 max-w-lg mx-auto text-left space-y-1">
            <span className="text-[11px] font-bold text-rose-800 uppercase tracking-wider block">
              Official Reason for Decision
            </span>
            <p className="text-xs text-rose-900 leading-relaxed font-medium">
              {application.rejection_reason}
            </p>
            <p className="text-[11px] text-rose-600 pt-1">
              For questions or appeals, please contact your procurement representative.
            </p>
          </div>
        )}

        {/* Reference Number Card */}
        <div className="bg-slate-50 p-4 rounded-xl border border-slate-200 max-w-md mx-auto space-y-1">
          <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider">
            Official Application Reference
          </span>
          <div className="flex items-center justify-center gap-2">
            <span className="text-xl font-mono font-bold text-indigo-700">
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
            Onboarding Progress Tracker
          </h3>
          <p className="text-xs text-slate-500 mt-0.5">
            Track each stage of your vendor onboarding journey in real time.
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

          {/* Step 2: Information & Document Review */}
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
              <span className="font-bold text-slate-900 text-xs">2. Document Review</span>
            </div>
            <p className="text-[11px] text-slate-500 pl-8">
              {isApproved
                ? 'Statutory documents verified'
                : 'Checking PAN, GST, and bank proofs'}
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
                ? 'Action needed from you above'
                : isApproved
                ? 'No pending clarifications'
                : 'Only if additional details needed'}
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
                : 'Compliance approval & onboarding'}
            </p>
          </div>
        </div>

        {/* Helpful What Happens Next Callout */}
        <div className="p-4 rounded-xl bg-slate-50 border border-slate-200 space-y-2 text-xs">
          <span className="font-bold text-slate-800 block">What happens next?</span>
          <ul className="space-y-1 text-slate-600 text-[11px] list-disc list-inside">
            <li>Our compliance team reviews applications within 1–2 business days.</li>
            <li>If any replacement document or clarification is required, an action notice will appear right here on your dashboard.</li>
            <li>Once approved, your vendor account will be activated to receive purchase orders and payment disbursements.</li>
          </ul>
        </div>
      </div>
    </div>
  );
};
