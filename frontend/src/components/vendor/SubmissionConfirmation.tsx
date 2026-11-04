import React from 'react';
import type { Application } from '../../types/application';
import { CheckCircle2, Clock, Lock, Copy, Check, XCircle, ShieldAlert } from 'lucide-react';
import { VendorExceptionsBanner } from './VendorExceptionsBanner';

interface Props {
  application: Application;
}

export const SubmissionConfirmation: React.FC<Props> = ({ application }) => {
  const [copied, setCopied] = React.useState(false);

  const handleCopy = () => {
    navigator.clipboard.writeText(application.reference_number);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const isApproved = application.status === 'APPROVED';
  const isRejected = application.status === 'REJECTED';
  const isActionRequired = application.status === 'ACTION_REQUIRED';

  return (
    <div className="max-w-3xl mx-auto space-y-6 py-6">
      {/* Priority Vendor Exception Clarifications & Corrections */}
      <VendorExceptionsBanner
        applicationId={application.id}
        onCorrectionSubmitted={() => {}}
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
            Application Status: {application.status.replace(/_/g, ' ')}
          </span>

          <h2 className="text-2xl font-extrabold text-slate-900 mt-3">
            {isApproved
              ? 'Onboarding Application Officially Approved!'
              : isRejected
              ? 'Onboarding Application Declined'
              : isActionRequired
              ? 'Action Required on Application'
              : 'Onboarding Application Under Evaluation'}
          </h2>

          <p className="text-xs text-slate-500 max-w-lg mx-auto mt-1">
            {isApproved
              ? `Congratulations, ${application.legal_name}. Your vendor registration has passed all statutory checks and your vendor master record is active.`
              : isRejected
              ? `Your application for ${application.legal_name} could not be approved at this time. Please review the reason below.`
              : isActionRequired
              ? 'A reviewer has requested clarification or a replacement document. Please review the notice above.'
              : `Thank you, ${application.legal_name}. Your onboarding application has been submitted and is actively being processed.`}
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
                ? 'Field edits are restricted to items highlighted in the clarification request.'
                : 'This application is locked for formal procurement verification.'}
            </span>
          </div>
        )}
      </div>

      {/* What Happens Next Card (only if still in progress) */}
      {!isApproved && !isRejected && (
        <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-2xs space-y-4">
          <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2">
            <Clock className="w-4 h-4 text-indigo-600" />
            Evaluation Pipeline Status
          </h3>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-3 text-xs">
            <div className="p-4 rounded-xl bg-slate-50 border border-slate-200 space-y-1">
              <div className="font-bold text-slate-900 flex items-center gap-1.5">
                <span className="w-5 h-5 rounded-full bg-indigo-100 text-indigo-700 flex items-center justify-center text-[10px]">
                  1
                </span>
                Extraction &amp; Rules
              </div>
              <p className="text-[11px] text-slate-500 leading-relaxed">
                Automated document classification and optical extraction verify syntax and cross-document consistency.
              </p>
            </div>

            <div className="p-4 rounded-xl bg-slate-50 border border-slate-200 space-y-1">
              <div className="font-bold text-slate-900 flex items-center gap-1.5">
                <span className="w-5 h-5 rounded-full bg-indigo-100 text-indigo-700 flex items-center justify-center text-[10px]">
                  2
                </span>
                External Checks
              </div>
              <p className="text-[11px] text-slate-500 leading-relaxed">
                Simulated verification checks PAN active status, GSTIN filing consistency, and bank beneficiary name matching.
              </p>
            </div>

            <div className="p-4 rounded-xl bg-slate-50 border border-slate-200 space-y-1">
              <div className="font-bold text-slate-900 flex items-center gap-1.5">
                <span className="w-5 h-5 rounded-full bg-indigo-100 text-indigo-700 flex items-center justify-center text-[10px]">
                  3
                </span>
                Reviewer Sign-Off
              </div>
              <p className="text-[11px] text-slate-500 leading-relaxed">
                If any evidence is ambiguous, clear correction instructions are routed to you. Otherwise, reviewers record final approval.
              </p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
