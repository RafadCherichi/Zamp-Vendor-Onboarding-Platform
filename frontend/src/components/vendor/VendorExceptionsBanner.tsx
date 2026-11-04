import React, { useState, useEffect } from 'react';
import {
  AlertCircle,
  CheckCircle2,
  Clock,
  UploadCloud,
  Send,
  HelpCircle,
} from 'lucide-react';
import { exceptionsApi } from '../../api/exceptions';
import { apiUploadDocument } from '../../api/applications';
import type { OnboardingException } from '../../types/exception';

interface VendorExceptionsBannerProps {
  applicationId: string;
  onCorrectionSubmitted?: () => void;
}

export const VendorExceptionsBanner: React.FC<VendorExceptionsBannerProps> = ({
  applicationId,
  onCorrectionSubmitted,
}) => {
  const [exceptions, setExceptions] = useState<OnboardingException[]>([]);
  const [loading, setLoading] = useState<boolean>(true);

  // Form states per exception
  const [fieldValues, setFieldValues] = useState<Record<string, string>>({});
  const [explanations, setExplanations] = useState<Record<string, string>>({});
  const [selectedFiles, setSelectedFiles] = useState<Record<string, File>>({});
  const [submitting, setSubmitting] = useState<Record<string, boolean>>({});
  const [successMessages, setSuccessMessages] = useState<Record<string, string>>({});
  const [errorMessages, setErrorMessages] = useState<Record<string, string>>({});

  const fetchExceptions = async () => {
    try {
      setLoading(true);
      const data = await exceptionsApi.getExceptions({ application_id: applicationId });
      setExceptions(data);
    } catch (err) {
      console.error('Failed to fetch exceptions for vendor:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (applicationId) {
      fetchExceptions();
    }
  }, [applicationId]);

  const actionableExceptions = exceptions.filter(
    (e) => e.status === 'ACTION_REQUIRED_FROM_VENDOR'
  );

  const submittedExceptions = exceptions.filter(
    (e) => e.status === 'RESPONSE_SUBMITTED'
  );

  if (loading) {
    return null;
  }

  if (actionableExceptions.length === 0 && submittedExceptions.length === 0) {
    return null;
  }

  const handleFieldChange = (excId: string, val: string) => {
    setFieldValues((prev) => ({ ...prev, [excId]: val }));
  };

  const handleExplanationChange = (excId: string, val: string) => {
    setExplanations((prev) => ({ ...prev, [excId]: val }));
  };

  const handleFileChange = (excId: string, file: File | null) => {
    if (file) {
      setSelectedFiles((prev) => ({ ...prev, [excId]: file }));
    }
  };

  const handleSubmitCorrection = async (exc: OnboardingException) => {
    const excId = exc.id;
    const newVal = fieldValues[excId];
    const exp = explanations[excId];
    const file = selectedFiles[excId];

    if (!newVal && !exp && !file) {
      setErrorMessages((prev) => ({
        ...prev,
        [excId]: 'Please provide a corrected value, replacement document, or explanation.',
      }));
      return;
    }

    try {
      setSubmitting((prev) => ({ ...prev, [excId]: true }));
      setErrorMessages((prev) => ({ ...prev, [excId]: '' }));

      // If document replacement was provided
      if (file) {
        const token = localStorage.getItem('token') || '';
        let docType = 'PAN_PROOF';
        if (exc.category.includes('GST')) docType = 'GST_CERTIFICATE';
        else if (exc.category.includes('BANK')) docType = 'BANK_PROOF';
        else if (exc.category.includes('CIN') || exc.category.includes('LLPIN')) docType = 'COI';
        await apiUploadDocument(token, applicationId, docType, file);
      }

      // Submit field correction and clarification
      await exceptionsApi.submitVendorCorrection(excId, {
        field_name: exc.related_field_name,
        new_field_value: newVal ? newVal.trim().toUpperCase() : undefined,
        explanation: exp ? exp.trim() : (file ? 'Uploaded replacement document' : undefined),
      });

      setSuccessMessages((prev) => ({
        ...prev,
        [excId]: 'Response submitted successfully. Revalidation in progress.',
      }));

      // Refresh after short delay
      setTimeout(() => {
        fetchExceptions();
        if (onCorrectionSubmitted) onCorrectionSubmitted();
      }, 1500);
    } catch (err: any) {
      const msg = err.response?.data?.detail || 'Failed to submit response. Please try again.';
      setErrorMessages((prev) => ({ ...prev, [excId]: msg }));
    } finally {
      setSubmitting((prev) => ({ ...prev, [excId]: false }));
    }
  };

  return (
    <div className="mb-8 rounded-xl border border-amber-200 bg-amber-50/50 shadow-sm overflow-hidden">
      {/* Header Banner */}
      <div className="p-4 sm:p-5 bg-gradient-to-r from-amber-500 to-amber-600 text-white flex items-start sm:items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-lg bg-white/20 backdrop-blur-xs">
            <AlertCircle className="w-6 h-6 text-white" />
          </div>
          <div>
            <h3 className="font-bold text-base sm:text-lg leading-tight">
              Action Required from Vendor ({actionableExceptions.length})
            </h3>
            <p className="text-xs sm:text-sm text-amber-100 mt-0.5">
              The compliance review team has identified items requiring your clarification or correction.
            </p>
          </div>
        </div>
        <span className="hidden sm:inline-flex px-3 py-1 text-xs font-semibold rounded-full bg-white text-amber-800 shadow-xs">
          Priority Response Needed
        </span>
      </div>

      {/* Actionable Exceptions List */}
      <div className="p-4 sm:p-6 space-y-6">
        {actionableExceptions.map((exc) => {
          const isSubmittingThis = submitting[exc.id];
          const isSuccessThis = successMessages[exc.id];
          const errorThis = errorMessages[exc.id];

          return (
            <div
              key={exc.id}
              className="bg-white rounded-xl border border-amber-200/80 p-5 shadow-xs transition-all hover:border-amber-300"
            >
              <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-100 pb-3">
                <div className="flex items-center gap-2">
                  <span className="px-2.5 py-0.5 text-xs font-bold rounded-md bg-amber-100 text-amber-800 uppercase tracking-wide">
                    {exc.category.replace(/_/g, ' ')}
                  </span>
                  <span className="text-xs font-mono text-slate-400">
                    {exc.reference_number}
                  </span>
                </div>
                <div className="flex items-center gap-1.5 text-xs text-amber-700 font-medium">
                  <Clock className="w-3.5 h-3.5" />
                  <span>Awaiting Your Correction</span>
                </div>
              </div>

              {/* Title & Description */}
              <div className="mt-3">
                <h4 className="font-semibold text-slate-900 text-base">
                  {exc.title}
                </h4>
                <p className="text-xs text-slate-600 mt-1 leading-relaxed">
                  {exc.description}
                </p>
              </div>

              {/* Specific Reviewer / System Instruction */}
              {exc.vendor_action_instruction && (
                <div className="mt-3.5 p-3 rounded-lg bg-amber-50 border border-amber-200 text-amber-900 text-xs flex items-start gap-2.5">
                  <HelpCircle className="w-4 h-4 text-amber-600 flex-shrink-0 mt-0.5" />
                  <div>
                    <strong className="font-semibold block mb-0.5">Instructions for resolution:</strong>
                    <span>{exc.vendor_action_instruction}</span>
                  </div>
                </div>
              )}

              {/* Interactive Resolution Section */}
              <div className="mt-4 pt-4 border-t border-slate-100 space-y-4">
                {isSuccessThis ? (
                  <div className="p-3.5 rounded-lg bg-emerald-50 border border-emerald-200 text-emerald-800 text-xs flex items-center gap-2">
                    <CheckCircle2 className="w-5 h-5 text-emerald-600 flex-shrink-0" />
                    <span className="font-medium">{isSuccessThis}</span>
                  </div>
                ) : (
                  <>
                    {/* If this exception relates to an application field */}
                    {exc.related_field_name && (
                      <div>
                        <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1.5">
                          Correct Value for: <span className="text-indigo-600">{exc.related_field_name}</span>
                        </label>
                        <input
                          type="text"
                          value={fieldValues[exc.id] || ''}
                          onChange={(e) => handleFieldChange(exc.id, e.target.value)}
                          placeholder={`Enter corrected ${exc.related_field_name.replace(/_/g, ' ')}...`}
                          className="w-full px-3 py-2 text-sm border border-slate-300 rounded-lg focus:ring-2 focus:ring-amber-500 focus:border-amber-500 font-mono"
                          disabled={isSubmittingThis}
                        />
                      </div>
                    )}

                    {/* If this exception relates to a document */}
                    {exc.related_document_id && (
                      <div>
                        <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1.5">
                          Upload Replacement Document (New Version)
                        </label>
                        <div className="flex items-center gap-3">
                          <label className="cursor-pointer inline-flex items-center gap-2 px-3.5 py-2 text-xs font-medium text-slate-700 bg-slate-50 border border-slate-300 rounded-lg hover:bg-slate-100 transition-colors">
                            <UploadCloud className="w-4 h-4 text-slate-500" />
                            <span>{selectedFiles[exc.id] ? selectedFiles[exc.id].name : 'Choose File (PDF, PNG, JPG)'}</span>
                            <input
                              type="file"
                              accept=".pdf,.png,.jpg,.jpeg"
                              onChange={(e) => handleFileChange(exc.id, e.target.files?.[0] || null)}
                              className="hidden"
                              disabled={isSubmittingThis}
                            />
                          </label>
                          {selectedFiles[exc.id] && (
                            <span className="text-xs text-emerald-600 font-medium flex items-center gap-1">
                              <CheckCircle2 className="w-3.5 h-3.5" />
                              Ready to upload
                            </span>
                          )}
                        </div>
                        <p className="text-[11px] text-slate-400 mt-1">
                          Previous document versions remain permanently archived for historical compliance audit.
                        </p>
                      </div>
                    )}

                    {/* Explanation or Clarification Note */}
                    <div>
                      <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1.5">
                        Vendor Explanation / Clarification Note
                      </label>
                      <textarea
                        rows={2}
                        value={explanations[exc.id] || ''}
                        onChange={(e) => handleExplanationChange(exc.id, e.target.value)}
                        placeholder="Provide details or reasoning for the correction or clarify the discrepancy..."
                        className="w-full px-3 py-2 text-xs border border-slate-300 rounded-lg focus:ring-2 focus:ring-amber-500 focus:border-amber-500"
                        disabled={isSubmittingThis}
                      />
                    </div>

                    {errorThis && (
                      <div className="p-2.5 rounded-lg bg-rose-50 border border-rose-200 text-rose-700 text-xs">
                        {errorThis}
                      </div>
                    )}

                    {/* Submit Action */}
                    <div className="flex items-center justify-between pt-2">
                      <span className="text-[11px] text-slate-400 italic">
                        Submitting triggers selective revalidation and alerts the compliance reviewer.
                      </span>
                      <button
                        onClick={() => handleSubmitCorrection(exc)}
                        disabled={isSubmittingThis}
                        className="inline-flex items-center gap-2 px-4 py-2 text-xs font-semibold text-white bg-amber-600 hover:bg-amber-700 rounded-lg shadow-xs transition-colors disabled:opacity-50"
                      >
                        {isSubmittingThis ? (
                          <span>Submitting...</span>
                        ) : (
                          <>
                            <Send className="w-3.5 h-3.5" />
                            <span>Submit Correction</span>
                          </>
                        )}
                      </button>
                    </div>
                  </>
                )}
              </div>
            </div>
          );
        })}

        {/* Recently Submitted Responses under Review */}
        {submittedExceptions.length > 0 && (
          <div className="mt-4 pt-4 border-t border-amber-200/60">
            <h5 className="text-xs font-semibold text-slate-700 uppercase tracking-wider mb-2 flex items-center gap-1.5">
              <Clock className="w-3.5 h-3.5 text-blue-500" />
              <span>Responses Submitted &amp; Pending Review ({submittedExceptions.length})</span>
            </h5>
            <div className="space-y-2">
              {submittedExceptions.map((subExc) => (
                <div
                  key={subExc.id}
                  className="bg-white/80 rounded-lg border border-slate-200 p-3 text-xs flex items-center justify-between"
                >
                  <div>
                    <span className="font-medium text-slate-900">{subExc.title}</span>
                    <span className="text-slate-400 ml-2 font-mono">({subExc.reference_number})</span>
                  </div>
                  <span className="px-2 py-0.5 rounded-full bg-blue-50 text-blue-700 font-semibold text-[11px] border border-blue-200">
                    Under Compliance Review
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
