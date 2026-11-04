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
} from 'lucide-react';

interface StepProps {
  token: string;
  application: Application;
  onGoToStep: (stepIndex: number) => void;
  onChange: (updates: ApplicationDraftUpdate) => void;
  onSubmitSuccess: (refNumber: string) => void;
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

  const mandatoryDocs = (application.documents || []).filter((d) => d.is_required);
  const missingDocs = mandatoryDocs.filter((d) => d.status !== 'UPLOADED');

  const missingFields: string[] = [];
  if (!application.legal_name) missingFields.push('Legal Business Name');
  if (!application.registered_address) missingFields.push('Registered Address');
  if (!application.city) missingFields.push('City');
  if (!application.state) missingFields.push('State');
  if (!application.pincode) missingFields.push('PIN Code');
  if (!application.pan) missingFields.push('PAN');
  if (application.is_gst_registered && !application.gstin) missingFields.push('GSTIN');
  if (application.is_udyam_registered && !application.udyam_number) missingFields.push('Udyam Number');
  if (!application.contact_name) missingFields.push('Contact Person Name');
  if (!application.contact_email) missingFields.push('Contact Email');
  if (!application.contact_mobile) missingFields.push('Contact Mobile');
  if (!application.bank_account_holder_name) missingFields.push('Bank Account Holder Name');
  if (!application.bank_account_number) missingFields.push('Bank Account Number');
  if (!application.bank_ifsc) missingFields.push('Bank IFSC');

  const hasMissing = missingFields.length > 0 || missingDocs.length > 0;
  const allDeclarationsChecked =
    application.declaration_accurate_info &&
    application.declaration_authorised_rep &&
    application.declaration_verification_consent;

  const handleSubmit = async () => {
    if (hasMissing) {
      setSubmitError('Please complete all mandatory information and document uploads before submitting.');
      return;
    }
    if (!allDeclarationsChecked) {
      setSubmitError('Please review and check all three declarations to proceed with submission.');
      return;
    }

    setIsSubmitting(true);
    setSubmitError(null);
    try {
      const res = await apiSubmitApplication(token, application.id);
      onSubmitSuccess(res.reference_number);
    } catch (err: any) {
      setSubmitError(err?.message || 'Failed to submit onboarding application.');
      setIsSubmitting(false);
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

      {submitError && (
        <div className="p-4 rounded-xl bg-rose-50 border border-rose-200 text-xs text-rose-800 flex items-start gap-2.5">
          <AlertTriangle className="w-4 h-4 text-rose-600 shrink-0 mt-0.5" />
          <div>
            <span className="font-bold">Submission Blocked:</span>
            <p className="mt-0.5">{submitError}</p>
          </div>
        </div>
      )}

      {/* Missing Requirements Callout */}
      {hasMissing && (
        <div className="p-4 rounded-xl bg-amber-50 border border-amber-200 text-xs text-amber-900 space-y-2">
          <div className="font-bold flex items-center gap-1.5">
            <AlertTriangle className="w-4 h-4 text-amber-600" />
            Mandatory Requirements Incomplete
          </div>
          {missingFields.length > 0 && (
            <div>
              <span className="font-semibold text-amber-950">Missing Form Fields:</span>{' '}
              {missingFields.join(', ')}
            </div>
          )}
          {missingDocs.length > 0 && (
            <div>
              <span className="font-semibold text-amber-950">Missing Required Documents:</span>{' '}
              {missingDocs.map((d) => d.title).join(', ')}
            </div>
          )}
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
                {application.constitution?.replace('_', ' ') || '—'}
              </span>
            </div>
            <div>
              <span className="text-slate-400">Establishment:</span>{' '}
              {application.date_of_establishment || '—'}
            </div>
            <div className="truncate">
              <span className="text-slate-400">Address:</span>{' '}
              {application.registered_address
                ? `${application.registered_address}, ${application.city}, ${application.state} ${application.pincode}`
                : '—'}
            </div>
          </div>
        </div>

        {/* Card 2: Tax & Registration */}
        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-2xs space-y-2 relative">
          <div className="flex items-center justify-between border-b border-slate-100 pb-2">
            <h4 className="text-xs font-bold text-slate-900 flex items-center gap-1.5">
              <FileCheck2 className="w-4 h-4 text-indigo-600" />
              2. Tax & Registration
            </h4>
            <button
              onClick={() => onGoToStep(1)}
              className="text-[11px] text-indigo-600 hover:text-indigo-800 font-semibold inline-flex items-center gap-1"
            >
              <Edit3 className="w-3 h-3" /> Edit
            </button>
          </div>
          <div className="text-xs text-slate-600 space-y-1 font-mono">
            <div>
              <span className="text-slate-400 font-sans">PAN:</span>{' '}
              <span className="font-semibold text-slate-900">{application.pan || '—'}</span>
            </div>
            <div>
              <span className="text-slate-400 font-sans">GSTIN:</span>{' '}
              {application.is_gst_registered ? application.gstin || '—' : 'Not Registered'}
            </div>
            <div>
              <span className="text-slate-400 font-sans">Udyam MSME:</span>{' '}
              {application.is_udyam_registered ? application.udyam_number || '—' : 'Not Registered'}
            </div>
            {application.cin_llpin && (
              <div>
                <span className="text-slate-400 font-sans">CIN/LLPIN:</span> {application.cin_llpin}
              </div>
            )}
          </div>
        </div>

        {/* Card 3: Contact */}
        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-2xs space-y-2 relative">
          <div className="flex items-center justify-between border-b border-slate-100 pb-2">
            <h4 className="text-xs font-bold text-slate-900 flex items-center gap-1.5">
              <UserCheck className="w-4 h-4 text-indigo-600" />
              3. Authorised Contact
            </h4>
            <button
              onClick={() => onGoToStep(2)}
              className="text-[11px] text-indigo-600 hover:text-indigo-800 font-semibold inline-flex items-center gap-1"
            >
              <Edit3 className="w-3 h-3" /> Edit
            </button>
          </div>
          <div className="text-xs text-slate-600 space-y-1">
            <div>
              <span className="text-slate-400">Representative:</span>{' '}
              <span className="font-semibold text-slate-900">{application.contact_name || '—'}</span>
            </div>
            <div>
              <span className="text-slate-400">Designation:</span> {application.contact_designation || '—'}
            </div>
            <div>
              <span className="text-slate-400">Email:</span>{' '}
              <span className="font-mono">{application.contact_email || '—'}</span>
            </div>
            <div>
              <span className="text-slate-400">Mobile:</span> {application.contact_mobile || '—'}
            </div>
          </div>
        </div>

        {/* Card 4: Banking */}
        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-2xs space-y-2 relative">
          <div className="flex items-center justify-between border-b border-slate-100 pb-2">
            <h4 className="text-xs font-bold text-slate-900 flex items-center gap-1.5">
              <Landmark className="w-4 h-4 text-indigo-600" />
              4. Banking Details
            </h4>
            <button
              onClick={() => onGoToStep(3)}
              className="text-[11px] text-indigo-600 hover:text-indigo-800 font-semibold inline-flex items-center gap-1"
            >
              <Edit3 className="w-3 h-3" /> Edit
            </button>
          </div>
          <div className="text-xs text-slate-600 space-y-1">
            <div>
              <span className="text-slate-400">Account Holder:</span>{' '}
              <span className="font-semibold text-slate-900">
                {application.bank_account_holder_name || '—'}
              </span>
            </div>
            <div>
              <span className="text-slate-400">Account Number:</span>{' '}
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

      {/* Document Uploads Summary */}
      <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-2xs space-y-3">
        <div className="flex items-center justify-between border-b border-slate-100 pb-2">
          <h4 className="text-xs font-bold text-slate-900 flex items-center gap-1.5">
            <FileText className="w-4 h-4 text-indigo-600" />
            Checklist Status ({mandatoryDocs.length - missingDocs.length} / {mandatoryDocs.length} Mandatory Uploaded)
          </h4>
          <button
            onClick={() => onGoToStep(5)}
            className="text-[11px] text-indigo-600 hover:text-indigo-800 font-semibold inline-flex items-center gap-1"
          >
            <Edit3 className="w-3 h-3" /> Manage Documents
          </button>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-xs">
          {(application.documents || []).map((doc) => (
            <div
              key={doc.id}
              className="flex items-center justify-between p-2 rounded-lg bg-slate-50 border border-slate-100"
            >
              <span className="font-medium text-slate-800 truncate mr-2">{doc.title}</span>
              {doc.status === 'UPLOADED' ? (
                <span className="text-[10px] font-semibold text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded border border-emerald-200 shrink-0">
                  Uploaded (v{doc.current_version?.version_number || 1})
                </span>
              ) : doc.is_required ? (
                <span className="text-[10px] font-semibold text-rose-700 bg-rose-50 px-2 py-0.5 rounded border border-rose-200 shrink-0">
                  Missing
                </span>
              ) : (
                <span className="text-[10px] font-medium text-slate-400 shrink-0">Optional</span>
              )}
            </div>
          ))}
        </div>
      </div>

      {/* Deterministic Validation & Consistency Results */}
      <ValidationFindingsCard token={token} applicationId={application.id} />

      {/* Section 6: Declarations & Consent */}
      <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-2xs space-y-4">
        <h4 className="text-xs font-bold text-slate-900 uppercase tracking-wider">
          Legal Declarations & Verification Consent <span className="text-rose-500">*</span>
        </h4>

        <div className="space-y-3 text-xs text-slate-700">
          <label className="flex items-start gap-3 cursor-pointer">
            <input
              type="checkbox"
              checked={application.declaration_accurate_info}
              onChange={(e) => onChange({ declaration_accurate_info: e.target.checked })}
              className="mt-0.5 h-4 w-4 text-indigo-600 rounded border-slate-300 focus:ring-indigo-500"
            />
            <span>
              <strong>Accuracy & Authenticity:</strong> I declare that all information provided in this
              onboarding application, including tax identifiers, banking credentials, and uploaded statutory
              documents, is true, complete, and accurate.
            </span>
          </label>

          <label className="flex items-start gap-3 cursor-pointer">
            <input
              type="checkbox"
              checked={application.declaration_authorised_rep}
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
              checked={application.declaration_verification_consent}
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
          className="flex items-center gap-2 px-6 py-3 rounded-xl text-sm font-bold text-white bg-indigo-600 hover:bg-indigo-700 shadow-md disabled:opacity-50 transition-all"
        >
          <Send className="w-4 h-4" />
          <span>{isSubmitting ? 'Submitting Application...' : 'Submit Application for Review'}</span>
        </button>
      </div>
    </div>
  );
};
