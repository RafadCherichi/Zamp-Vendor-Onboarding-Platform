import React, { useState } from 'react';
import type { Application, DocumentSlot, DocumentExtractionDetail } from '../../types/application';
import {
  apiUploadDocument,
  getDocumentPreviewUrl,
  apiFetchDocumentExtraction,
  apiReprocessDocument,
} from '../../api/applications';
import {
  FileText,
  Upload,
  CheckCircle2,
  Eye,
  EyeOff,
  RefreshCw,
  AlertTriangle,
  X,
  FileCheck,
  Sparkles,
  Info,
  AlertCircle,
  Search,
} from 'lucide-react';

interface StepProps {
  token: string;
  application: Application;
  onRefresh: () => void;
}

export const StepDocumentChecklist: React.FC<StepProps> = ({ token, application, onRefresh }) => {
  const [uploadingType, setUploadingType] = useState<string | null>(null);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [previewDoc, setPreviewDoc] = useState<DocumentSlot | null>(null);
  const [inspectingDoc, setInspectingDoc] = useState<DocumentSlot | null>(null);
  const [extractionDetail, setExtractionDetail] = useState<DocumentExtractionDetail | null>(null);
  const [loadingExtraction, setLoadingExtraction] = useState(false);
  const [reprocessing, setReprocessing] = useState(false);
  const [revealedFields, setRevealedFields] = useState<Record<string, boolean>>({});

  const handleFileUpload = async (documentType: string, file: File) => {
    setUploadingType(documentType);
    setUploadError(null);
    try {
      await apiUploadDocument(token, application.id, documentType, file);
      onRefresh();
    } catch (err: any) {
      setUploadError(err?.message || `Failed to upload ${documentType}`);
    } finally {
      setUploadingType(null);
    }
  };

  const handleOpenInspection = async (slot: DocumentSlot) => {
    setInspectingDoc(slot);
    setLoadingExtraction(true);
    setExtractionDetail(null);
    try {
      const data = await apiFetchDocumentExtraction(token, application.id, slot.id);
      setExtractionDetail(data);
    } catch (err: any) {
      setUploadError(err?.message || 'Failed to load extraction details');
    } finally {
      setLoadingExtraction(false);
    }
  };

  const handleReprocess = async () => {
    if (!inspectingDoc) return;
    setReprocessing(true);
    try {
      const updated = await apiReprocessDocument(token, application.id, inspectingDoc.id);
      setExtractionDetail(updated);
      onRefresh();
    } catch (err: any) {
      setUploadError(err?.message || 'Failed to reprocess document');
    } finally {
      setReprocessing(false);
    }
  };

  const toggleFieldReveal = (fieldId: string) => {
    setRevealedFields((prev) => ({ ...prev, [fieldId]: !prev[fieldId] }));
  };

  const documents = application.documents || [];
  const mandatoryDocs = documents.filter((d) => d.is_required);
  const uploadedMandatory = mandatoryDocs.filter((d) => d.status === 'UPLOADED');
  const allMandatoryUploaded = mandatoryDocs.length > 0 && uploadedMandatory.length === mandatoryDocs.length;

  return (
    <div className="space-y-6">
      <div>
        <h3 className="text-base font-bold text-slate-900 flex items-center gap-2">
          <FileText className="w-5 h-5 text-indigo-600" />
          Section 6: Dynamic Document Verification Checklist
        </h3>
        <p className="text-xs text-slate-500 mt-1">
          Upload statutory evidence required based on your legal constitution (
          <span className="font-semibold text-slate-700">{application.constitution.replace('_', ' ')}</span>
          ), tax registration, and business operations. Each document is parsed via our automated OCR pipeline to extract compliance fields.
        </p>
      </div>

      {uploadError && (
        <div className="p-3.5 rounded-xl bg-rose-50 border border-rose-200 text-xs text-rose-700 flex items-start gap-2.5">
          <AlertTriangle className="w-4 h-4 text-rose-600 shrink-0 mt-0.5" />
          <div>
            <span className="font-bold">Error:</span> {uploadError}
          </div>
        </div>
      )}

      {/* Progress pill */}
      <div className="p-4 rounded-xl bg-white border border-slate-200 shadow-2xs flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <span className="text-xs font-bold text-slate-900">
            Mandatory Documents Uploaded: {uploadedMandatory.length} of {mandatoryDocs.length}
          </span>
          <p className="text-[11px] text-slate-500">
            {allMandatoryUploaded
              ? 'All required documents have been uploaded.'
              : 'Please upload all mandatory documents to proceed to final submission.'}
          </p>
        </div>
        <div className="w-full sm:w-48 bg-slate-100 rounded-full h-2.5 overflow-hidden">
          <div
            className={`h-2.5 rounded-full transition-all ${
              allMandatoryUploaded ? 'bg-emerald-500' : 'bg-indigo-600'
            }`}
            style={{
              width: `${mandatoryDocs.length ? (uploadedMandatory.length / mandatoryDocs.length) * 100 : 0}%`,
            }}
          />
        </div>
      </div>

      {/* Document Slots */}
      <div className="space-y-4">
        {documents.map((slot) => {
          const isUploaded = slot.status === 'UPLOADED';
          const isBusy = uploadingType === slot.document_type;
          const procStatus = slot.processing_status;
          const hasFlags = slot.review_flags && slot.review_flags.length > 0;
          const hasTypeMismatch = slot.is_type_match === false;

          return (
            <div
              key={slot.id}
              className={`p-5 rounded-xl border transition-all ${
                hasTypeMismatch
                  ? 'bg-amber-50/30 border-amber-300'
                  : isUploaded
                  ? 'bg-emerald-50/20 border-emerald-200'
                  : slot.is_required
                  ? 'bg-white border-slate-200 hover:border-indigo-300'
                  : 'bg-slate-50/60 border-slate-200 opacity-80'
              }`}
            >
              <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-3">
                <div className="space-y-1.5 flex-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="font-bold text-slate-900 text-sm">{slot.title}</span>
                    {slot.is_required ? (
                      <span className="text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded bg-rose-50 text-rose-700 border border-rose-200">
                        Mandatory
                      </span>
                    ) : (
                      <span className="text-[10px] font-medium px-2 py-0.5 rounded bg-slate-100 text-slate-600 border border-slate-200">
                        Conditional / Optional
                      </span>
                    )}

                    {isUploaded && slot.current_version && (
                      <span className="text-[10px] font-semibold px-2 py-0.5 rounded-full bg-emerald-100 text-emerald-800 border border-emerald-300 flex items-center gap-1">
                        <CheckCircle2 className="w-3 h-3 text-emerald-600" />
                        Uploaded (v{slot.current_version.version_number})
                      </span>
                    )}

                    {/* Processing Status Badge */}
                    {isUploaded && procStatus && (
                      <span
                        className={`text-[10px] font-semibold px-2 py-0.5 rounded-full border flex items-center gap-1 ${
                          procStatus === 'EXTRACTED'
                            ? 'bg-indigo-50 text-indigo-700 border-indigo-200'
                            : procStatus === 'NEEDS_REVIEW'
                            ? 'bg-amber-50 text-amber-700 border-amber-300'
                            : procStatus === 'PROCESSING' || procStatus === 'QUEUED'
                            ? 'bg-blue-50 text-blue-700 border-blue-200'
                            : 'bg-rose-50 text-rose-700 border-rose-200'
                        }`}
                      >
                        {procStatus === 'EXTRACTED' && <Sparkles className="w-3 h-3 text-indigo-600" />}
                        {procStatus === 'NEEDS_REVIEW' && <AlertTriangle className="w-3 h-3 text-amber-600" />}
                        {(procStatus === 'PROCESSING' || procStatus === 'QUEUED') && (
                          <RefreshCw className="w-3 h-3 text-blue-600 animate-spin" />
                        )}
                        {procStatus === 'FAILED' && <AlertCircle className="w-3 h-3 text-rose-600" />}
                        <span>{procStatus.replace('_', ' ')}</span>
                      </span>
                    )}
                  </div>

                  {slot.requirement_reason && (
                    <p className="text-xs text-slate-600 leading-relaxed">
                      <span className="font-semibold text-slate-700">Requirement Rule:</span>{' '}
                      {slot.requirement_reason}
                    </p>
                  )}

                  <div className="text-[11px] text-slate-400">
                    Accepted formats: {slot.accepted_extensions.join(', ').toUpperCase()} &bull; Max{' '}
                    {slot.max_size_mb}MB
                  </div>

                  {/* Uploaded File Info */}
                  {isUploaded && slot.current_version && (
                    <div className="flex flex-wrap items-center gap-2 pt-1">
                      <div className="text-xs font-mono text-emerald-800 bg-white/80 px-2.5 py-1.5 rounded-lg border border-emerald-200 inline-flex items-center gap-2">
                        <FileCheck className="w-3.5 h-3.5 text-emerald-600" />
                        <span>{slot.current_version.original_filename}</span>
                        <span className="text-[10px] text-slate-400">
                          ({Math.round(slot.current_version.file_size_bytes / 1024)} KB)
                        </span>
                      </div>

                      {slot.detected_document_type && (
                        <div className="text-[11px] px-2 py-1 rounded-md bg-slate-100 text-slate-700 border border-slate-200">
                          Detected:{' '}
                          <span className="font-bold text-slate-900">
                            {slot.detected_document_type.replace('_', ' ')}
                          </span>
                        </div>
                      )}
                    </div>
                  )}

                  {/* Warning / Mismatch Banner */}
                  {hasTypeMismatch && (
                    <div className="mt-2 p-2.5 rounded-lg bg-amber-50 border border-amber-300 text-xs text-amber-800 flex items-start gap-2">
                      <AlertTriangle className="w-4 h-4 text-amber-600 shrink-0 mt-0.5" />
                      <div>
                        <span className="font-bold">Document Type Mismatch Warning:</span> This document resembles a{' '}
                        <span className="font-bold underline">{slot.detected_document_type?.replace('_', ' ')}</span>{' '}
                        rather than the requested <span className="font-bold">{slot.title}</span>. Please verify and
                        replace if incorrect.
                      </div>
                    </div>
                  )}

                  {/* Extracted Fields Summary Pills */}
                  {isUploaded && slot.extracted_fields_summary && Object.keys(slot.extracted_fields_summary).length > 0 && (
                    <div className="mt-2.5 p-3 rounded-lg bg-white/90 border border-slate-200 space-y-1.5">
                      <div className="text-[11px] font-bold text-slate-700 flex items-center justify-between">
                        <span className="flex items-center gap-1.5">
                          <Sparkles className="w-3.5 h-3.5 text-indigo-600" />
                          Extracted Compliance Fields (OCR / Layout)
                        </span>
                        <button
                          type="button"
                          onClick={() => handleOpenInspection(slot)}
                          className="text-[11px] text-indigo-600 hover:text-indigo-800 font-semibold underline flex items-center gap-1"
                        >
                          <Search className="w-3 h-3" /> View Evidence & Confidence
                        </button>
                      </div>
                      <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-2 pt-1">
                        {Object.entries(slot.extracted_fields_summary).map(([key, val]) => (
                          <div
                            key={key}
                            className="px-2 py-1.5 rounded bg-slate-50 border border-slate-200 text-xs flex flex-col"
                          >
                            <span className="text-[10px] text-slate-400 uppercase tracking-wider font-semibold">
                              {key.replace(/_/g, ' ')}
                            </span>
                            <span className="font-mono font-medium text-slate-900 truncate" title={val}>
                              {val}
                            </span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Review Flags */}
                  {hasFlags && (
                    <div className="mt-2 space-y-1">
                      {slot.review_flags!.map((flag, idx) => (
                        <div
                          key={idx}
                          className="text-[11px] text-amber-800 bg-amber-50/80 px-2 py-1 rounded border border-amber-200 flex items-center gap-1.5"
                        >
                          <Info className="w-3 h-3 text-amber-600 shrink-0" />
                          <span>{flag}</span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>

                {/* Upload / Action Buttons */}
                <div className="flex items-center gap-2 shrink-0 self-start">
                  {isUploaded && (
                    <>
                      <button
                        type="button"
                        onClick={() => setPreviewDoc(slot)}
                        className="inline-flex items-center gap-1 px-3 py-1.5 rounded-lg text-xs font-medium text-slate-700 bg-white hover:bg-slate-50 border border-slate-200 shadow-2xs transition-colors"
                      >
                        <Eye className="w-3.5 h-3.5 text-indigo-600" />
                        Preview
                      </button>

                      <button
                        type="button"
                        onClick={() => handleOpenInspection(slot)}
                        className="inline-flex items-center gap-1 px-3 py-1.5 rounded-lg text-xs font-medium text-indigo-700 bg-indigo-50 hover:bg-indigo-100 border border-indigo-200 shadow-2xs transition-colors"
                      >
                        <Search className="w-3.5 h-3.5 text-indigo-600" />
                        Inspect OCR
                      </button>
                    </>
                  )}

                  <label className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold text-white bg-indigo-600 hover:bg-indigo-700 shadow-2xs cursor-pointer transition-colors disabled:opacity-50">
                    {isBusy ? (
                      <>
                        <RefreshCw className="w-3.5 h-3.5 animate-spin" /> Uploading...
                      </>
                    ) : isUploaded ? (
                      <>
                        <Upload className="w-3.5 h-3.5" /> Replace (v{slot.versions_count + 1})
                      </>
                    ) : (
                      <>
                        <Upload className="w-3.5 h-3.5" /> Upload File
                      </>
                    )}
                    <input
                      type="file"
                      disabled={isBusy}
                      accept=".pdf,.jpg,.jpeg,.png"
                      onChange={(e) => {
                        const file = e.target.files?.[0];
                        if (file) {
                          handleFileUpload(slot.document_type, file);
                          e.target.value = '';
                        }
                      }}
                      className="hidden"
                    />
                  </label>
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {/* Safe Document Preview Modal */}
      {previewDoc && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 backdrop-blur-2xs p-4">
          <div className="bg-white rounded-2xl max-w-4xl w-full h-[85vh] flex flex-col shadow-2xl border border-slate-200 overflow-hidden">
            <div className="px-6 py-4 border-b border-slate-200 flex items-center justify-between bg-slate-50">
              <div>
                <h4 className="text-sm font-bold text-slate-900">{previewDoc.title}</h4>
                <p className="text-xs text-slate-500 font-mono">
                  {previewDoc.current_version?.original_filename} (Version {previewDoc.current_version?.version_number})
                </p>
              </div>
              <button
                onClick={() => setPreviewDoc(null)}
                className="p-1 rounded-lg text-slate-400 hover:text-slate-600 hover:bg-slate-100"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="flex-1 bg-slate-100 p-2 overflow-auto flex items-center justify-center">
              {previewDoc.current_version?.content_type === 'application/pdf' ? (
                <iframe
                  src={getDocumentPreviewUrl(application.id, previewDoc.id)}
                  title="Document Preview"
                  className="w-full h-full rounded-lg border border-slate-300 bg-white"
                />
              ) : (
                <img
                  src={getDocumentPreviewUrl(application.id, previewDoc.id)}
                  alt="Document Preview"
                  className="max-h-full max-w-full object-contain rounded-lg shadow-sm"
                />
              )}
            </div>

            <div className="px-6 py-3 border-t border-slate-200 bg-white flex justify-between items-center text-xs text-slate-500">
              <span>Private Object Storage &bull; In-line Streaming</span>
              <button
                onClick={() => setPreviewDoc(null)}
                className="px-4 py-1.5 rounded-lg bg-slate-900 text-white font-semibold hover:bg-slate-800"
              >
                Close Preview
              </button>
            </div>
          </div>
        </div>
      )}

      {/* OCR Inspection & Evidence Modal */}
      {inspectingDoc && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 backdrop-blur-2xs p-4">
          <div className="bg-white rounded-2xl max-w-5xl w-full h-[88vh] flex flex-col shadow-2xl border border-slate-200 overflow-hidden">
            <div className="px-6 py-4 border-b border-slate-200 flex items-center justify-between bg-slate-50">
              <div className="flex items-center gap-2">
                <Sparkles className="w-5 h-5 text-indigo-600" />
                <div>
                  <h4 className="text-sm font-bold text-slate-900">
                    OCR & Compliance Extraction Evidence — {inspectingDoc.title}
                  </h4>
                  <p className="text-xs text-slate-500 font-mono">
                    {inspectingDoc.current_version?.original_filename} (Version{' '}
                    {inspectingDoc.current_version?.version_number})
                  </p>
                </div>
              </div>
              <button
                onClick={() => setInspectingDoc(null)}
                className="p-1 rounded-lg text-slate-400 hover:text-slate-600 hover:bg-slate-100"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="flex-1 overflow-hidden grid grid-cols-1 lg:grid-cols-2 divide-y lg:divide-y-0 lg:divide-x divide-slate-200">
              {/* Left Column: Visual File Preview */}
              <div className="h-full bg-slate-100 p-3 overflow-auto flex flex-col">
                <span className="text-[11px] font-bold text-slate-600 mb-2">Original Document Preview</span>
                <div className="flex-1 bg-white rounded-xl border border-slate-300 overflow-hidden flex items-center justify-center">
                  {inspectingDoc.current_version?.content_type === 'application/pdf' ? (
                    <iframe
                      src={getDocumentPreviewUrl(application.id, inspectingDoc.id)}
                      title="Document Preview"
                      className="w-full h-full"
                    />
                  ) : (
                    <img
                      src={getDocumentPreviewUrl(application.id, inspectingDoc.id)}
                      alt="Document Preview"
                      className="max-h-full max-w-full object-contain p-2"
                    />
                  )}
                </div>
              </div>

              {/* Right Column: Structured Extraction & Provenance */}
              <div className="h-full overflow-y-auto p-5 space-y-5">
                {loadingExtraction ? (
                  <div className="h-full flex flex-col items-center justify-center py-16 text-slate-500 space-y-2">
                    <RefreshCw className="w-6 h-6 animate-spin text-indigo-600" />
                    <span className="text-xs">Loading document extraction data...</span>
                  </div>
                ) : extractionDetail ? (
                  <>
                    {/* Classification Decision */}
                    <div className="p-4 rounded-xl bg-slate-50 border border-slate-200 space-y-2">
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-bold text-slate-800">Classification Result</span>
                        <span
                          className={`text-xs px-2.5 py-0.5 rounded-full font-semibold border ${
                            extractionDetail.is_type_match
                              ? 'bg-emerald-50 text-emerald-800 border-emerald-200'
                              : 'bg-amber-50 text-amber-800 border-amber-300'
                          }`}
                        >
                          {extractionDetail.detected_document_type?.replace('_', ' ')} (
                          {Math.round((extractionDetail.classification_confidence || 0) * 100)}% match)
                        </span>
                      </div>
                      <p className="text-xs text-slate-600">{extractionDetail.classification_reason}</p>
                      <div className="text-[11px] text-slate-400 font-mono">
                        Pipeline Provider: {extractionDetail.provider_used} &bull; Pages: {extractionDetail.page_count}
                      </div>
                    </div>

                    {/* Extracted Fields Table */}
                    <div>
                      <div className="flex items-center justify-between mb-2">
                        <span className="text-xs font-bold text-slate-900">
                          Extracted Structured Fields ({extractionDetail.fields.length})
                        </span>
                        <span className="text-[11px] text-slate-400">Field-level Confidence & Evidence</span>
                      </div>

                      {extractionDetail.fields.length === 0 ? (
                        <div className="p-4 rounded-xl border border-dashed border-slate-200 text-center text-xs text-slate-400">
                          No structured compliance identifiers recognized in document text.
                        </div>
                      ) : (
                        <div className="space-y-2.5">
                          {extractionDetail.fields.map((f) => (
                            <div key={f.id} className="p-3 rounded-xl border border-slate-200 bg-white space-y-1.5">
                              <div className="flex items-center justify-between">
                                <span className="text-xs font-bold text-slate-800 uppercase tracking-wider font-mono">
                                  {f.field_name.replace(/_/g, ' ')}
                                </span>
                                <span
                                  className={`text-[10px] px-2 py-0.5 rounded font-bold ${
                                    f.confidence_score >= 0.90
                                      ? 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                                      : f.confidence_score >= 0.75
                                      ? 'bg-blue-50 text-blue-700 border border-blue-200'
                                      : 'bg-amber-50 text-amber-700 border border-amber-200'
                                  }`}
                                >
                                  {Math.round(f.confidence_score * 100)}% Confidence
                                </span>
                              </div>

                              <div className="text-sm font-semibold font-mono text-indigo-950 flex items-center justify-between">
                                <div className="flex items-center gap-2">
                                  <span>
                                    {revealedFields[f.id] ? f.extracted_value : f.normalized_value || f.extracted_value}
                                  </span>
                                  {(f.field_name.includes('pan') || f.field_name.includes('account')) && (
                                    <button
                                      type="button"
                                      onClick={() => toggleFieldReveal(f.id)}
                                      title={revealedFields[f.id] ? 'Mask value' : 'Show unmasked value'}
                                      className="text-slate-400 hover:text-slate-600 p-0.5"
                                    >
                                      {revealedFields[f.id] ? <EyeOff className="w-3.5 h-3.5" /> : <Eye className="w-3.5 h-3.5" />}
                                    </button>
                                  )}
                                </div>
                                <span className="text-[10px] text-slate-400 font-normal">Page {f.page_number}</span>
                              </div>

                              {f.evidence_text && (
                                <div className="p-2 rounded bg-slate-50 border border-slate-100 text-[11px] text-slate-600 font-mono">
                                  <span className="text-[10px] font-bold text-slate-400 block mb-0.5">
                                    Evidence Context:
                                  </span>
                                  "{f.evidence_text}"
                                </div>
                              )}
                              <div className="text-[10px] text-slate-400">
                                Method: <span className="font-semibold">{f.extraction_method}</span>
                              </div>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  </>
                ) : (
                  <div className="p-4 text-xs text-slate-400">No extraction information found.</div>
                )}
              </div>
            </div>

            <div className="px-6 py-3 border-t border-slate-200 bg-white flex justify-between items-center text-xs text-slate-500">
              <button
                type="button"
                onClick={handleReprocess}
                disabled={reprocessing}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-slate-200 hover:bg-slate-50 font-semibold text-slate-700 disabled:opacity-50"
              >
                <RefreshCw className={`w-3.5 h-3.5 text-indigo-600 ${reprocessing ? 'animate-spin' : ''}`} />
                {reprocessing ? 'Reprocessing OCR...' : 'Reprocess Document'}
              </button>

              <button
                onClick={() => setInspectingDoc(null)}
                className="px-4 py-1.5 rounded-lg bg-slate-900 text-white font-semibold hover:bg-slate-800"
              >
                Done
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
