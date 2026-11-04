import React from 'react';
import type { Application } from '../../types/application';
import { CheckCircle2, Clock, Lock, Copy, Check } from 'lucide-react';
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

  return (
    <div className="max-w-3xl mx-auto space-y-6 py-6">
      {/* Priority Vendor Exception Clarifications & Corrections */}
      <VendorExceptionsBanner
        applicationId={application.id}
        onCorrectionSubmitted={() => {}}
      />

      <div className="bg-white rounded-2xl border border-slate-200 p-8 shadow-sm text-center space-y-4">
        <div className="w-16 h-16 rounded-2xl bg-emerald-100 text-emerald-600 flex items-center justify-center mx-auto shadow-inner">
          <CheckCircle2 className="w-10 h-10" />
        </div>

        <div>
          <span className="text-xs font-bold uppercase tracking-wider text-emerald-700 bg-emerald-50 px-3 py-1 rounded-full border border-emerald-200">
            Application Status: SUBMITTED
          </span>
          <h2 className="text-2xl font-extrabold text-slate-900 mt-3">
            Onboarding Application Successfully Submitted!
          </h2>
          <p className="text-xs text-slate-500 max-w-lg mx-auto mt-1">
            Thank you, <span className="font-semibold text-slate-700">{application.legal_name}</span>.
            Your onboarding application has been registered with buyer organisation{' '}
            <span className="font-semibold text-slate-700">Apex Enterprises Ltd</span>.
          </p>
        </div>

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
              className="p-1 rounded text-slate-400 hover:text-slate-600 hover:bg-slate-200"
              title="Copy Reference Number"
            >
              {copied ? <Check className="w-4 h-4 text-emerald-600" /> : <Copy className="w-4 h-4" />}
            </button>
          </div>
          <div className="text-[11px] text-slate-400">
            Submitted at:{' '}
            {application.submitted_at
              ? new Date(application.submitted_at).toLocaleString()
              : 'Just now'}
          </div>
        </div>

        {/* Locked Notice */}
        <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-200 text-xs text-slate-600 max-w-lg mx-auto flex items-center justify-center gap-2">
          <Lock className="w-4 h-4 text-slate-400 shrink-0" />
          <span>This application is now locked for formal procurement verification.</span>
        </div>
      </div>

      {/* What Happens Next Card */}
      <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-2xs space-y-4">
        <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2">
          <Clock className="w-4 h-4 text-indigo-600" />
          What Happens Next in the Review Process
        </h3>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-3 text-xs">
          <div className="p-4 rounded-xl bg-slate-50 border border-slate-200 space-y-1">
            <div className="font-bold text-slate-900 flex items-center gap-1.5">
              <span className="w-5 h-5 rounded-full bg-indigo-100 text-indigo-700 flex items-center justify-center text-[10px]">
                1
              </span>
              Extraction & Rules
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
    </div>
  );
};
