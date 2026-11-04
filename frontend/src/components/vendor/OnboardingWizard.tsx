import React, { useState } from 'react';
import type { Application, ApplicationDraftUpdate } from '../../types/application';
import { apiUpdateApplicationDraft } from '../../api/applications';
import { StepBusinessIdentity } from './StepBusinessIdentity';
import { StepTaxRegistration } from './StepTaxRegistration';
import { StepAuthorisedContact } from './StepAuthorisedContact';
import { StepBankingDetails } from './StepBankingDetails';
import { StepBusinessClassification } from './StepBusinessClassification';
import { StepDocumentChecklist } from './StepDocumentChecklist';
import { StepReviewSubmit } from './StepReviewSubmit';
import { VendorExceptionsBanner } from './VendorExceptionsBanner';
import {
  Building,
  FileCheck2,
  UserCheck,
  Landmark,
  Tag,
  FileText,
  ShieldCheck,
  ArrowRight,
  ArrowLeft,
  Save,
  CheckCircle2,
} from 'lucide-react';

interface WizardProps {
  token: string;
  initialApplication: Application;
  onRefresh: () => void;
  onSubmitSuccess: (refNumber: string) => void;
}

const STEPS = [
  { id: 0, label: 'Identity', icon: Building, title: 'Business Identity' },
  { id: 1, label: 'Tax & Reg', icon: FileCheck2, title: 'Tax & Registration' },
  { id: 2, label: 'Contact', icon: UserCheck, title: 'Authorised Contact' },
  { id: 3, label: 'Banking', icon: Landmark, title: 'Banking Details' },
  { id: 4, label: 'Activity', icon: Tag, title: 'Business Classification' },
  { id: 5, label: 'Checklist', icon: FileText, title: 'Document Checklist' },
  { id: 6, label: 'Review', icon: ShieldCheck, title: 'Review & Submit' },
];

export const OnboardingWizard: React.FC<WizardProps> = ({
  token,
  initialApplication,
  onRefresh,
  onSubmitSuccess,
}) => {
  const [currentStep, setCurrentStep] = useState(0);
  const [application, setApplication] = useState<Application>(initialApplication);
  const [isSaving, setIsSaving] = useState(false);
  const [saveSuccessMsg, setSaveSuccessMsg] = useState<string | null>(null);

  const handleFieldChange = async (updates: ApplicationDraftUpdate) => {
    // Optimistic local state update
    setApplication((prev) => ({
      ...prev,
      ...updates,
      constitution: (updates.constitution as any) || prev.constitution,
      categories: updates.categories !== undefined ? updates.categories : prev.categories,
    }));

    // Auto-save debounced or explicit
    try {
      const updated = await apiUpdateApplicationDraft(token, application.id, updates);
      setApplication(updated);
    } catch {
      // Local changes remain for explicit save
    }
  };

  const handleExplicitSave = async () => {
    setIsSaving(true);
    setSaveSuccessMsg(null);
    try {
      const updated = await apiUpdateApplicationDraft(token, application.id, {
        legal_name: application.legal_name,
        trade_name: application.trade_name || undefined,
        constitution: application.constitution,
        date_of_establishment: application.date_of_establishment || undefined,
        registered_address: application.registered_address || undefined,
        operating_address: application.operating_address || undefined,
        city: application.city || undefined,
        state: application.state || undefined,
        pincode: application.pincode || undefined,
        pan: application.pan || undefined,
        is_gst_registered: application.is_gst_registered,
        gstin: application.gstin || undefined,
        is_udyam_registered: application.is_udyam_registered,
        udyam_number: application.udyam_number || undefined,
        cin_llpin: application.cin_llpin || undefined,
        contact_name: application.contact_name || undefined,
        contact_designation: application.contact_designation || undefined,
        contact_email: application.contact_email || undefined,
        contact_mobile: application.contact_mobile || undefined,
        authorised_signatory_name: application.authorised_signatory_name || undefined,
        bank_account_holder_name: application.bank_account_holder_name || undefined,
        bank_account_number: application.bank_account_number || undefined,
        bank_ifsc: application.bank_ifsc || undefined,
        bank_account_type: application.bank_account_type || undefined,
        bank_name: application.bank_name || undefined,
        categories: application.categories,
        declaration_accurate_info: application.declaration_accurate_info,
        declaration_authorised_rep: application.declaration_authorised_rep,
        declaration_verification_consent: application.declaration_verification_consent,
      });
      setApplication(updated);
      setSaveSuccessMsg(`Progress saved at ${new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}`);
      setTimeout(() => setSaveSuccessMsg(null), 3000);
      onRefresh();
    } catch (err: any) {
      alert(err?.message || 'Failed to save draft progress.');
    } finally {
      setIsSaving(false);
    }
  };

  const handleNext = async () => {
    await handleExplicitSave();
    if (currentStep < STEPS.length - 1) {
      setCurrentStep((prev) => prev + 1);
      window.scrollTo({ top: 0, behavior: 'smooth' });
    }
  };

  const handlePrev = () => {
    if (currentStep > 0) {
      setCurrentStep((prev) => prev - 1);
      window.scrollTo({ top: 0, behavior: 'smooth' });
    }
  };

  return (
    <div className="space-y-6">
      {/* Priority Vendor Exception Clarifications & Corrections */}
      <VendorExceptionsBanner
        applicationId={application.id}
        onCorrectionSubmitted={onRefresh}
      />

      {/* Top Wizard Navigation Card */}
      <div className="bg-white rounded-2xl border border-slate-200 p-4 sm:p-6 shadow-2xs">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-4 border-b border-slate-100">
          <div>
            <span className="text-[10px] font-bold uppercase tracking-wider text-indigo-700 bg-indigo-50 px-2.5 py-0.5 rounded-full border border-indigo-200">
              Draft In Progress &bull; Ref: {application.reference_number}
            </span>
            <h2 className="text-lg font-bold text-slate-900 mt-1">
              Vendor Onboarding & Compliance Submission
            </h2>
          </div>
          <div className="flex items-center gap-2 self-start sm:self-auto">
            {saveSuccessMsg && (
              <span className="text-xs text-emerald-600 flex items-center gap-1 font-medium animate-fade-in">
                <CheckCircle2 className="w-3.5 h-3.5" />
                {saveSuccessMsg}
              </span>
            )}
            <button
              type="button"
              onClick={handleExplicitSave}
              disabled={isSaving}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold text-slate-700 bg-slate-100 hover:bg-slate-200 border border-slate-200 transition-colors"
            >
              <Save className="w-3.5 h-3.5 text-slate-500" />
              {isSaving ? 'Saving...' : 'Save Progress'}
            </button>
          </div>
        </div>

        {/* Step Tabs */}
        <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-7 gap-1 pt-3">
          {STEPS.map((step) => {
            const Icon = step.icon;
            const isCurrent = currentStep === step.id;
            const isCompleted = currentStep > step.id;

            return (
              <button
                key={step.id}
                type="button"
                onClick={() => setCurrentStep(step.id)}
                className={`flex flex-col sm:flex-row items-center sm:items-start gap-1.5 p-2 rounded-xl text-center sm:text-left transition-all ${
                  isCurrent
                    ? 'bg-indigo-600 text-white shadow-xs'
                    : isCompleted
                    ? 'text-slate-700 hover:bg-slate-100'
                    : 'text-slate-400 hover:bg-slate-50'
                }`}
              >
                <Icon className={`w-4 h-4 shrink-0 ${isCurrent ? 'text-white' : isCompleted ? 'text-emerald-600' : 'text-slate-400'}`} />
                <div className="truncate">
                  <div className="text-[10px] uppercase font-bold tracking-wider leading-none">
                    Step {step.id + 1}
                  </div>
                  <div className="text-xs font-semibold truncate leading-tight mt-0.5">
                    {step.label}
                  </div>
                </div>
              </button>
            );
          })}
        </div>
      </div>

      {/* Active Step Container */}
      <div className="bg-white rounded-2xl border border-slate-200 p-6 sm:p-8 shadow-2xs">
        {currentStep === 0 && (
          <StepBusinessIdentity application={application} onChange={handleFieldChange} />
        )}
        {currentStep === 1 && (
          <StepTaxRegistration application={application} onChange={handleFieldChange} />
        )}
        {currentStep === 2 && (
          <StepAuthorisedContact application={application} onChange={handleFieldChange} />
        )}
        {currentStep === 3 && (
          <StepBankingDetails application={application} onChange={handleFieldChange} />
        )}
        {currentStep === 4 && (
          <StepBusinessClassification application={application} onChange={handleFieldChange} />
        )}
        {currentStep === 5 && (
          <StepDocumentChecklist
            token={token}
            application={application}
            onRefresh={async () => {
              const updated = await apiUpdateApplicationDraft(token, application.id, {});
              setApplication(updated);
            }}
          />
        )}
        {currentStep === 6 && (
          <StepReviewSubmit
            token={token}
            application={application}
            onGoToStep={(stepIdx) => setCurrentStep(stepIdx)}
            onChange={handleFieldChange}
            onSubmitSuccess={onSubmitSuccess}
          />
        )}

        {/* Step Bottom Navigation Bar */}
        <div className="flex items-center justify-between pt-8 border-t border-slate-100 mt-8">
          <button
            type="button"
            disabled={currentStep === 0}
            onClick={handlePrev}
            className="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg text-xs font-semibold text-slate-700 bg-slate-100 hover:bg-slate-200 border border-slate-200 disabled:opacity-30 disabled:pointer-events-none transition-colors"
          >
            <ArrowLeft className="w-3.5 h-3.5" />
            Previous
          </button>

          <div className="flex items-center gap-2">
            {currentStep < STEPS.length - 1 ? (
              <button
                type="button"
                onClick={handleNext}
                className="inline-flex items-center gap-1.5 px-5 py-2.5 rounded-lg text-xs font-bold text-white bg-indigo-600 hover:bg-indigo-700 shadow-xs transition-colors"
              >
                <span>Save & Continue</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </button>
            ) : null}
          </div>
        </div>
      </div>
    </div>
  );
};
