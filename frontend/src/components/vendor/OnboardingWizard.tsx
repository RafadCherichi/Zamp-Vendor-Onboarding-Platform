import React, { useState, useEffect, useRef } from 'react';
import type { Application, ApplicationDraftUpdate } from '../../types/application';
import { apiFetchChecklist, apiResetOwnDraft, apiUpdateApplicationDraft, apiUploadDocument } from '../../api/applications';
import { StepBusinessIdentity } from './StepBusinessIdentity';
import { StepTaxRegistration } from './StepTaxRegistration';
import { StepAuthorisedContact } from './StepAuthorisedContact';
import { StepBankingDetails } from './StepBankingDetails';
import { StepBusinessClassification } from './StepBusinessClassification';
import { StepDocumentChecklist } from './StepDocumentChecklist';
import { StepReviewSubmit } from './StepReviewSubmit';
import { hasWrongDocumentType } from '../../utils/documentSlots';
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
  AlertTriangle,
  LoaderCircle,
  FlaskConical,
  RotateCcw,
} from 'lucide-react';
import { getDemoAutofillProfilesForVendor } from './demoAutofill';

interface WizardProps {
  token: string;
  initialApplication: Application;
  onRefresh: (silent?: boolean) => void;
  onSubmitSuccess: (refNumber: string) => void;
}

export const STEPS = [
  { id: 0, label: 'Business', icon: Building, title: 'About Your Business' },
  { id: 1, label: 'Tax', icon: FileCheck2, title: 'Tax Details' },
  { id: 2, label: 'Contact', icon: UserCheck, title: 'Contact Details' },
  { id: 3, label: 'Banking', icon: Landmark, title: 'Bank Account Details' },
  { id: 4, label: 'Activity', icon: Tag, title: 'What Does Your Business Do?' },
  { id: 5, label: 'Documents', icon: FileText, title: 'Documents You Need to Provide' },
  { id: 6, label: 'Review', icon: ShieldCheck, title: 'Review and Submit' },
];

export function isStepValid(stepIdx: number, app: Application): { isValid: boolean; errors: string[] } {
  const errors: string[] = [];

  switch (stepIdx) {
    case 0: // About Your Business
      if (!app.legal_name || !app.legal_name.trim() || app.legal_name.trim().length < 2) {
        errors.push('Legal Business Name is required (minimum 2 characters).');
      }
      if (!app.constitution) {
        errors.push('Please select your business constitution.');
      }
      if (!app.registered_address || !app.registered_address.trim()) {
        errors.push('Registered office address is required.');
      }
      if (!app.city || !app.city.trim()) {
        errors.push('City is required.');
      }
      if (!app.state || !app.state.trim()) {
        errors.push('State or Union Territory is required.');
      }
      if (!app.pincode || !/^\d{6}$/.test(app.pincode.trim())) {
        errors.push('PIN code must be a 6-digit number.');
      }
      break;

    case 1: // Tax Details
      if (!app.pan || !/^[A-Z]{5}[0-9]{4}[A-Z]{1}$/.test(app.pan.trim().toUpperCase())) {
        errors.push('Please enter a valid 10-character PAN (e.g. ABCDE1234F).');
      }
      if (app.is_gst_registered) {
        const gstRegex = /^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$/;
        if (!app.gstin || !gstRegex.test(app.gstin.trim().toUpperCase())) {
          errors.push('Please enter a valid 15-character GSTIN matching your state code and PAN.');
        }
      }
      if (app.is_udyam_registered && (!app.udyam_number || !app.udyam_number.trim())) {
        errors.push('Please enter your Udyam Registration Number (e.g. UDYAM-MH-02-0012345).');
      }
      if (['PVT_LTD', 'PUB_LTD', 'LLP'].includes(app.constitution)) {
        if (!app.cin_llpin || !app.cin_llpin.trim()) {
          errors.push(`Please enter your ${app.constitution === 'LLP' ? 'LLPIN' : 'CIN'} from your Certificate of Incorporation.`);
        }
      }
      break;

    case 2: // Contact Details
      if (!app.contact_name || !app.contact_name.trim()) {
        errors.push('Contact person name is required.');
      }
      if (!app.contact_designation || !app.contact_designation.trim()) {
        errors.push('Designation or title is required.');
      }
      if (!app.contact_email || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(app.contact_email.trim())) {
        errors.push('Please enter a valid email address.');
      }
      if (!app.contact_mobile || !/^(?:\+91|0)?[6-9]\d{9}$/.test(app.contact_mobile.trim().replace(/[\s-]/g, ''))) {
        errors.push('Please enter a valid 10-digit Indian mobile number.');
      }
      break;

    case 3: // Bank Account Details
      if (!app.bank_account_holder_name || !app.bank_account_holder_name.trim()) {
        errors.push('Bank account holder name (as printed on cheque/passbook) is required.');
      }
      if (!app.bank_account_number || !app.bank_account_number.trim()) {
        errors.push('Bank account number is required.');
      }
      if (!app.bank_ifsc || !/^[A-Z]{4}0[A-Z0-9]{6}$/.test(app.bank_ifsc.trim().toUpperCase())) {
        errors.push('Please enter an 11-character RBI IFSC code (e.g. HDFC0000123).');
      }
      break;

    case 4: // What Does Your Business Do?
      if (!app.categories || app.categories.length === 0) {
        errors.push('Please select at least one activity that describes the products or services your business provides.');
      } else if (app.categories.includes('other')) {
        if (!app.other_business_activity_description || !app.other_business_activity_description.trim()) {
          errors.push('Please describe your business activity when "Other Business Activities" is selected.');
        }
      }
      break;

    case 5: // Documents You Need to Provide
      const mandatoryDocs = (app.documents || []).filter((d) => d.is_required);
      const missingDocs = mandatoryDocs.filter((d) => d.status !== 'UPLOADED');
      if (missingDocs.length > 0) {
        missingDocs.forEach((d) => errors.push(`Please upload: ${d.title}.`));
      }
      mandatoryDocs.filter((d) => hasWrongDocumentType(d, app.constitution)).forEach((d) => {
        errors.push(`Replace ${d.title}: the current file appears to be a different document.`);
      });
      break;

    case 6: // Review and Submit
      // Check prior steps
      for (let i = 0; i < 6; i++) {
        const prior = isStepValid(i, app);
        if (!prior.isValid) {
          errors.push(`Complete all mandatory fields in Step ${i + 1} (${STEPS[i].label}).`);
        }
      }
      if (!app.declaration_accurate_info) {
        errors.push('Please confirm the accuracy declaration.');
      }
      if (!app.declaration_authorised_rep) {
        errors.push('Please confirm the authorized representation declaration.');
      }
      if (!app.declaration_verification_consent) {
        errors.push('Please confirm the verification and processing consent declaration.');
      }
      break;
  }

  return { isValid: errors.length === 0, errors };
}

export const OnboardingWizard: React.FC<WizardProps> = ({
  token,
  initialApplication,
  onRefresh,
  onSubmitSuccess,
}) => {
  const [currentStep, setCurrentStep] = useState<number>(() => {
    try {
      const saved = sessionStorage.getItem(`vop_step_${initialApplication.id}`);
      if (saved !== null) {
        const val = parseInt(saved, 10);
        if (!isNaN(val) && val >= 0 && val < STEPS.length) return val;
      }
    } catch {}
    return 0;
  });

  const [application, setApplication] = useState<Application>(initialApplication);
  const unsavedDraftRef = useRef<ApplicationDraftUpdate>({});
  const [isSaving, setIsSaving] = useState(false);
  const [isResetting, setIsResetting] = useState(false);
  const [saveSuccessMsg, setSaveSuccessMsg] = useState<string | null>(null);
  const [stepErrors, setStepErrors] = useState<{ stepId: number; errors: string[] } | null>(null);
  const [autofillProfile, setAutofillProfile] = useState<string | null>(null);
  const [autofillMessage, setAutofillMessage] = useState<string | null>(null);
  const [autofillError, setAutofillError] = useState<string | null>(null);

  useEffect(() => {
    setApplication((current) => {
      if (current.id !== initialApplication.id) {
        unsavedDraftRef.current = {};
        return initialApplication;
      }
      return { ...initialApplication, ...unsavedDraftRef.current } as Application;
    });
  }, [initialApplication]);

  const updateStep = (newStep: number) => {
    setCurrentStep(newStep);
    try {
      sessionStorage.setItem(`vop_step_${application.id}`, String(newStep));
    } catch {}
  };

  const handleFieldChange = async (updates: ApplicationDraftUpdate) => {
    unsavedDraftRef.current = { ...unsavedDraftRef.current, ...updates };
    setStepErrors(null);
    setApplication((prev) => ({
      ...prev,
      ...updates,
      constitution: (updates.constitution as any) || prev.constitution,
      categories: updates.categories !== undefined ? updates.categories : prev.categories,
    }));

    try {
      // Responses can arrive out of order while someone fills successive fields.
      // Keep the newer local draft; the full save before advancing reconciles it.
      await apiUpdateApplicationDraft(token, application.id, updates);
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
        gstin: application.is_gst_registered ? (application.gstin || undefined) : undefined,
        is_udyam_registered: application.is_udyam_registered,
        udyam_number: application.is_udyam_registered ? (application.udyam_number || undefined) : undefined,
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
      const changesMadeWhileSaving = unsavedDraftRef.current;
      for (const [key, value] of Object.entries(changesMadeWhileSaving)) {
        if (value === (application as any)[key]) {
          delete (changesMadeWhileSaving as any)[key];
        }
      }
      unsavedDraftRef.current = changesMadeWhileSaving;
      setApplication({ ...updated, ...changesMadeWhileSaving } as Application);
      setSaveSuccessMsg(`Progress saved at ${new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}`);
      setTimeout(() => setSaveSuccessMsg(null), 3000);
      onRefresh(true);
    } catch (err: any) {
      alert(err?.message || 'Failed to save draft progress.');
    } finally {
      setIsSaving(false);
    }
  };

  const handleStepClick = (targetStep: number) => {
    if (targetStep <= currentStep) {
      // Backward navigation to review or edit previous steps is always permitted
      setStepErrors(null);
      updateStep(targetStep);
      window.scrollTo({ top: 0, behavior: 'smooth' });
      return;
    }

    // Forward navigation: verify all prior steps are completed
    for (let i = 0; i < targetStep; i++) {
      const check = isStepValid(i, application);
      if (!check.isValid) {
        setStepErrors({
          stepId: i,
          errors: check.errors,
        });
        updateStep(i);
        window.scrollTo({ top: 0, behavior: 'smooth' });
        return;
      }
    }

    setStepErrors(null);
    updateStep(targetStep);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const handleNext = async () => {
    // Validate current step before advancing
    const check = isStepValid(currentStep, application);
    if (!check.isValid) {
      setStepErrors({
        stepId: currentStep,
        errors: check.errors,
      });
      window.scrollTo({ top: 0, behavior: 'smooth' });
      return;
    }

    setStepErrors(null);
    await handleExplicitSave();
    if (currentStep < STEPS.length - 1) {
      updateStep(currentStep + 1);
      window.scrollTo({ top: 0, behavior: 'smooth' });
    }
  };

  const handlePrev = () => {
    setStepErrors(null);
    if (currentStep > 0) {
      updateStep(currentStep - 1);
      window.scrollTo({ top: 0, behavior: 'smooth' });
    }
  };

  const handleDemoAutofill = async (profileId: string) => {
    const profile = getDemoAutofillProfilesForVendor(application.legal_name).find((item) => item.id === profileId);
    if (!profile || autofillProfile) return;

    setAutofillProfile(profile.id);
    setAutofillMessage('Adding fictional vendor details…');
    setAutofillError(null);
    setStepErrors(null);
    unsavedDraftRef.current = {};
    try {
      const updated = await apiUpdateApplicationDraft(token, application.id, {
        ...profile.draft,
        declaration_accurate_info: false,
        declaration_authorised_rep: false,
        declaration_verification_consent: false,
      });
      setApplication(updated);

      const checklist = await apiFetchChecklist(token, application.id);
      const requiredSlots = checklist.filter((slot) => slot.is_required);
      const missingExample = requiredSlots.find((slot) => !profile.documents[slot.document_type]);
      if (missingExample) {
        throw new Error(`The ${profile.name} example is missing a sample for ${missingExample.title}.`);
      }

      for (let index = 0; index < requiredSlots.length; index += 1) {
        const slot = requiredSlots[index];
        const filename = profile.documents[slot.document_type];
        setAutofillMessage(`Adding sample documents… ${index + 1} of ${requiredSlots.length}`);
        const response = await fetch(`/demo-documents/${filename}`);
        if (!response.ok) throw new Error(`Could not load the sample file for ${slot.title}.`);
        const file = new File([await response.blob()], filename, { type: 'application/pdf' });
        await apiUploadDocument(token, application.id, slot.document_type, file);
      }

      const refreshed = await apiUpdateApplicationDraft(token, application.id, {});
      setApplication(refreshed);
      setAutofillMessage(`${profile.name} details and ${requiredSlots.length} required sample documents are ready to review.`);
      onRefresh(true);
    } catch (error: any) {
      setAutofillError(error?.message || 'Demo details could not be added. Please retry or continue manually.');
      setAutofillMessage(null);
    } finally {
      setAutofillProfile(null);
    }
  };

  const handleResetDraft = async () => {
    if (!window.confirm('Start this draft again? Your entered details and uploaded documents will be cleared. Your company account and the other demo cases will stay as they are.')) return;
    setIsResetting(true);
    try {
      const reset = await apiResetOwnDraft(token, application.id);
      unsavedDraftRef.current = {};
      setApplication(reset);
      setStepErrors(null);
      setAutofillMessage(null);
      setAutofillError(null);
      updateStep(0);
      onRefresh(true);
      window.scrollTo({ top: 0, behavior: 'smooth' });
    } catch (error: any) {
      alert(error?.message || 'Could not start this draft again.');
    } finally {
      setIsResetting(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Priority Vendor Exception Clarifications & Corrections */}
      <VendorExceptionsBanner
        token={token}
        applicationId={application.id}
        documentSlots={application.documents}
        onCorrectionSubmitted={() => onRefresh(true)}
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
              onClick={handleResetDraft}
              disabled={isResetting || isSaving || Boolean(autofillProfile)}
              className="inline-flex items-center gap-1.5 rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 transition-colors hover:bg-slate-50 disabled:opacity-50"
            >
              <RotateCcw className="h-3.5 w-3.5" />
              {isResetting ? 'Starting again…' : 'Start again'}
            </button>
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
            const isCompleted = isStepValid(step.id, application).isValid;

            return (
              <button
                key={step.id}
                type="button"
                onClick={() => handleStepClick(step.id)}
                className={`flex flex-col sm:flex-row items-center sm:items-start gap-1.5 p-2 rounded-xl text-center sm:text-left transition-all ${
                  isCurrent
                    ? 'bg-indigo-600 text-white shadow-xs'
                    : isCompleted
                    ? 'text-slate-800 hover:bg-emerald-50/50 bg-emerald-50/20'
                    : 'text-slate-400 hover:bg-slate-50'
                }`}
              >
                {isCompleted && !isCurrent ? (
                  <CheckCircle2 className="w-4 h-4 shrink-0 text-emerald-600" />
                ) : (
                  <Icon className={`w-4 h-4 shrink-0 ${isCurrent ? 'text-white' : 'text-slate-400'}`} />
                )}
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

      {/* Section Validation Error Banner */}
      {stepErrors && stepErrors.stepId === currentStep && (
        <div className="p-4 rounded-xl bg-rose-50 border border-rose-200 text-xs text-rose-800 flex items-start gap-3 shadow-2xs">
          <AlertTriangle className="w-4 h-4 text-rose-600 shrink-0 mt-0.5" />
          <div className="space-y-1">
            <span className="font-bold block">
              Please complete all mandatory information in Step {currentStep + 1} ({STEPS[currentStep].title}) to continue:
            </span>
            <ul className="list-disc list-inside space-y-0.5 text-rose-700">
              {stepErrors.errors.map((err, idx) => (
                <li key={idx}>{err}</li>
              ))}
            </ul>
          </div>
        </div>
      )}

      {/* Active Step Container */}
      <div className="bg-white rounded-2xl border border-slate-200 p-6 sm:p-8 shadow-2xs">
        {currentStep === 0 && (
          <section aria-labelledby="demo-autofill-heading" className="mb-7 rounded-2xl border border-amber-200 bg-[#fbf7ed] p-4 sm:p-5">
            <div className="flex items-start gap-3">
              <span className="mt-0.5 rounded-xl bg-white p-2 text-amber-800 border border-amber-200"><FlaskConical className="h-4 w-4" /></span>
              <div className="min-w-0 flex-1">
                <h3 id="demo-autofill-heading" className="text-sm font-semibold text-slate-900">Need to see the flow first?</h3>
                <p className="mt-1 max-w-3xl text-xs leading-relaxed text-slate-600">Load a fictional vendor example with its sample documents. Check every detail, edit it if you like, and make your own declarations before submitting.</p>
                <div className="mt-4 grid grid-cols-1 gap-2 md:grid-cols-3">
                  {getDemoAutofillProfilesForVendor(application.legal_name).map((profile) => (
                    <div key={profile.id} className="rounded-xl border border-amber-100 bg-white/80 p-3">
                      <p className="text-xs font-semibold text-slate-800">{profile.name}</p>
                      <p className="mt-1 min-h-8 text-[11px] leading-snug text-slate-500">{profile.description}</p>
                      <button
                        type="button"
                        aria-label={`Fill with demo data: ${profile.name}`}
                        disabled={autofillProfile !== null}
                        onClick={() => void handleDemoAutofill(profile.id)}
                        className="mt-3 inline-flex min-h-9 w-full items-center justify-center gap-2 rounded-lg border border-slate-300 bg-white px-3 py-2 text-xs font-semibold text-slate-800 transition-colors hover:border-slate-400 hover:bg-slate-50 disabled:cursor-wait disabled:opacity-60"
                      >
                        {autofillProfile === profile.id ? <LoaderCircle className="h-3.5 w-3.5 animate-spin" /> : null}
                        {autofillProfile === profile.id ? 'Loading example…' : 'Use this example'}
                      </button>
                    </div>
                  ))}
                </div>
                {autofillMessage && <p role="status" className="mt-3 text-xs font-medium text-emerald-800">{autofillMessage}</p>}
                {autofillError && <p role="alert" className="mt-3 text-xs font-medium text-rose-700">{autofillError}</p>}
              </div>
            </div>
          </section>
        )}
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
            onGoToStep={(stepIdx) => handleStepClick(stepIdx)}
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
