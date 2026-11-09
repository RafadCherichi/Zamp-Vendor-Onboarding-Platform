import React, { useState, useEffect } from 'react';
import {
  AlertCircle,
  CheckCircle2,
  Clock,
  Send,
  HelpCircle,
} from 'lucide-react';
import { exceptionsApi } from '../../api/exceptions';
import { apiUploadDocument } from '../../api/applications';
import type { OnboardingException } from '../../types/exception';
import type { DocumentSlot } from '../../types/application';

interface VendorExceptionsBannerProps {
  applicationId: string;
  token?: string;
  documentSlots: DocumentSlot[];
  onCorrectionSubmitted?: () => void;
}

const readableField = (field: string) =>
  field.replace(/_/g, ' ').replace(/\b\w/g, (letter) => letter.toUpperCase());

export const VendorExceptionsBanner: React.FC<VendorExceptionsBannerProps> = ({
  applicationId,
  token,
  documentSlots,
  onCorrectionSubmitted,
}) => {
  const [exceptions, setExceptions] = useState<OnboardingException[]>([]);
  useEffect(() => {
    const focusRequest = () => {
      const id = new URLSearchParams(window.location.search).get('request');
      if (!id) return;
      const element = document.getElementById(`request-${id}`);
      element?.scrollIntoView({ block: 'center', behavior: 'instant' });
      element?.focus({ preventScroll: true });
    };
    focusRequest();
    window.addEventListener('vop:open-application', focusRequest);
    return () => window.removeEventListener('vop:open-application', focusRequest);
  }, [exceptions]);

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
      const data = await exceptionsApi.getExceptions({ application_id: applicationId }, token);
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
  }, [applicationId, token]);

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

  if (actionableExceptions.length === 0 && submittedExceptions.length > 0) {
    return (
      <div className="mb-6 rounded-xl border border-slate-200 bg-white overflow-hidden">
        <div className="p-4 sm:p-5 border-b border-slate-200 flex items-start sm:items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-indigo-50">
              <Clock className="w-5 h-5 text-indigo-700" />
            </div>
            <div>
              <h3 className="font-bold text-base leading-tight">
                Responses Submitted — Awaiting Review ({submittedExceptions.length})
              </h3>
              <p className="text-sm text-slate-600 mt-0.5">
                We have your response. The review team will check it; you do not need to send it again.
              </p>
            </div>
          </div>
          <span className="hidden sm:inline-flex px-3 py-1 text-xs font-semibold text-indigo-800">
            Responses Under Review
          </span>
        </div>
        <div className="p-4 sm:p-5 space-y-3">
          {submittedExceptions.map((subExc) => (
            <div
              key={subExc.id}
              className="bg-white rounded-lg border border-slate-200 p-3.5 text-xs flex flex-col sm:flex-row sm:items-center justify-between gap-2 shadow-2xs"
            >
              <div>
                <div className="flex items-center gap-2">
                  <span className="font-bold text-slate-900">{subExc.title}</span>
                </div>
                {subExc.description && (
                  <p className="text-slate-500 text-[11px] mt-0.5 line-clamp-1">{subExc.description}</p>
                )}
              </div>
              <span className="px-2.5 py-1 rounded-full bg-sky-50 text-sky-700 font-semibold text-[11px] border border-sky-200 self-start sm:self-auto shrink-0 flex items-center gap-1">
                <Clock className="w-3 h-3 text-sky-600" />
                Under Compliance Review
              </span>
            </div>
          ))}
        </div>
      </div>
    );
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

    if (exc.related_document_id && !file && !(exc.related_field_name && newVal?.trim())) {
      setErrorMessages((prev) => ({ ...prev, [excId]: 'Upload the replacement document requested by the reviewer.' }));
      return;
    }

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
      const authToken = token || localStorage.getItem('token') || localStorage.getItem('vop_auth_token') || '';
      if (file) {
        const requestedSlot = documentSlots.find((slot) => slot.id === exc.related_document_id);
        if (!requestedSlot) {
          throw new Error('The requested document slot is no longer available. Contact your procurement representative before uploading.');
        }
        await apiUploadDocument(authToken, applicationId, requestedSlot.document_type, file, {
          exceptionId: excId,
          explanation: exp?.trim(),
          newFieldValue: newVal?.trim() ? newVal.trim().toUpperCase() : undefined,
        });
      }

      // Submit field correction and clarification
      if (!file) await exceptionsApi.submitVendorCorrection(
        excId,
        {
          field_name: exc.related_field_name,
          new_field_value: newVal ? newVal.trim().toUpperCase() : undefined,
          explanation: exp ? exp.trim() : (file ? 'Uploaded replacement document' : undefined),
        },
        authToken
      );

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
    <div className="mb-8 rounded-xl border border-amber-300 bg-white overflow-hidden">
      {/* Header Banner */}
      <div className="p-4 sm:p-5 border-b border-amber-200 bg-amber-50 flex items-start sm:items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-lg bg-white border border-amber-200">
            <AlertCircle className="w-5 h-5 text-amber-800" />
          </div>
          <div>
            <h3 className="font-semibold text-base sm:text-lg leading-tight text-slate-900">
              {actionableExceptions.length} {actionableExceptions.length === 1 ? 'item needs' : 'items need'} your attention
            </h3>
            <p className="text-sm text-slate-700 mt-0.5">
              Review the request below and send the corrected detail or document.
            </p>
          </div>
        </div>
        <span className="hidden sm:inline-flex px-3 py-1 text-xs font-semibold text-amber-800">
          Your next step
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
              id={`request-${exc.id}`}
              tabIndex={-1}
              className="bg-white rounded-xl border border-amber-200/80 p-5 shadow-xs transition-all hover:border-amber-300"
            >
              <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-100 pb-3">
                <div className="flex items-center gap-2">
                  <span className="px-2.5 py-0.5 text-xs font-bold rounded-md bg-amber-100 text-amber-800 uppercase tracking-wide">
                    {exc.category.replace(/_/g, ' ')}
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
                <p className="text-sm text-slate-600 mt-1 leading-relaxed">
                  {exc.description}
                </p>
              </div>

              {/* Specific Reviewer / System Instruction */}
              {exc.vendor_action_instruction && (
                <div className="mt-3.5 p-3 rounded-lg bg-amber-50 border border-amber-200 text-amber-900 text-sm flex items-start gap-2.5">
                  <HelpCircle className="w-4 h-4 text-amber-600 flex-shrink-0 mt-0.5" />
                  <div>
                    <strong className="font-semibold block mb-0.5">What to do</strong>
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
                        <div className="flex flex-wrap items-center justify-between gap-1 mb-1.5">
                          <label htmlFor={`correction-${exc.id}`} className="block text-sm font-semibold text-slate-700">
                            Correct {readableField(exc.related_field_name)}
                          </label>
                          {exc.field_corrections && exc.field_corrections.length > 0 && exc.field_corrections[0].previous_value && (
                            <span className="text-[11px] text-slate-500 font-mono">
                              Originally submitted: <span className="font-semibold text-rose-700 line-through">{exc.field_corrections[0].previous_value}</span>
                            </span>
                          )}
                        </div>
                        <input
                          id={`correction-${exc.id}`}
                          type="text"
                          value={fieldValues[exc.id] || ''}
                          onChange={(e) => handleFieldChange(exc.id, e.target.value)}
                          placeholder={`Enter ${readableField(exc.related_field_name).toLowerCase()}`}
                          className="w-full px-3 py-2 text-sm border border-slate-300 rounded-lg focus:ring-2 focus:ring-amber-500 focus:border-amber-500 font-mono"
                          disabled={isSubmittingThis}
                        />
                      </div>
                    )}

                    {/* If this exception relates to a document */}
                    {exc.related_document_id && (
                      <div>
                        <label htmlFor={`replacement-${exc.id}`} className="block text-sm font-semibold text-slate-700 mb-1.5">
                          Upload a replacement {documentSlots.find((slot) => slot.id === exc.related_document_id)?.title || 'document'}
                        </label>
                        <div className="flex flex-wrap items-center gap-3">
                          <input
                            id={`replacement-${exc.id}`}
                            type="file"
                            accept=".pdf,.png,.jpg,.jpeg"
                            onChange={(e) => handleFileChange(exc.id, e.target.files?.[0] || null)}
                            className="block w-full text-sm text-slate-700 file:mr-3 file:rounded file:border file:border-slate-300 file:bg-slate-50 file:px-3 file:py-2 file:text-sm file:font-medium file:text-slate-700 hover:file:bg-slate-100"
                            disabled={isSubmittingThis}
                          />
                          {selectedFiles[exc.id] && (
                            <span className="text-xs text-emerald-600 font-medium flex items-center gap-1">
                              <CheckCircle2 className="w-3.5 h-3.5" />
                              Ready to upload
                            </span>
                          )}
                        </div>
                        <p className="text-xs text-slate-500 mt-1">
                          PDF, PNG, or JPG. Your previous upload stays on record.
                        </p>
                      </div>
                    )}

                    {/* Explanation or Clarification Note */}
                    <div>
                      <label htmlFor={`explanation-${exc.id}`} className="block text-sm font-semibold text-slate-700 mb-1.5">
                        Add a note (optional)
                      </label>
                      <textarea
                        id={`explanation-${exc.id}`}
                        rows={2}
                        value={explanations[exc.id] || ''}
                        onChange={(e) => handleExplanationChange(exc.id, e.target.value)}
                        placeholder="Tell the reviewer what you changed"
                        className="w-full px-3 py-2 text-sm border border-slate-300 rounded-lg focus:ring-2 focus:ring-amber-500 focus:border-amber-500"
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
                      <span className="text-xs text-slate-600">
                        The review team will check your response.
                      </span>
                      <button
                        onClick={() => handleSubmitCorrection(exc)}
                        disabled={isSubmittingThis}
                        className="inline-flex items-center gap-2 px-4 py-2 text-sm font-semibold text-white bg-indigo-600 hover:bg-indigo-700 rounded-lg transition-colors disabled:opacity-50"
                      >
                        {isSubmittingThis ? (
                          <span>Submitting...</span>
                        ) : (
                          <>
                            <Send className="w-3.5 h-3.5" />
                            <span>Send response</span>
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
