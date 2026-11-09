import { useProtectedDocument } from '../../utils/useProtectedDocument';
import React, { useState } from 'react';
import type { Application, DocumentSlot, DocumentExtractionDetail, ProcessingProgress } from '../../types/application';
import { hasWrongDocumentType, isAcceptedAlternative } from '../../utils/documentSlots';
import {
  apiUploadDocument,
  getDocumentPreviewUrl,
  apiFetchDocumentExtraction,
  apiReprocessDocument,
  apiFetchProcessingProgress,
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
  Search,
} from 'lucide-react';

interface StepProps {
  token: string;
  application: Application;
  onRefresh: () => void;
}

const PROCESS_STEPS = [
  { stage: 'SENDING_FILE', label: 'Send file' },
  { stage: 'READING_TEXT', label: 'Read text' },
  { stage: 'CLASSIFYING', label: 'Identify proof' },
  { stage: 'EXTRACTING_FIELDS', label: 'Read details' },
  { stage: 'CHECKING_RESULT', label: 'Check result' },
] as const;

export const StepDocumentChecklist: React.FC<StepProps> = ({ token, application, onRefresh }) => {
  const [uploadingType, setUploadingType] = useState<string | null>(null);
  const [liveProgress, setLiveProgress] = useState<ProcessingProgress | null>(null);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [previewDoc, setPreviewDoc] = useState<DocumentSlot | null>(null);
  const [previewError, setPreviewError] = useState<boolean>(false);
  const [inspectingDoc, setInspectingDoc] = useState<DocumentSlot | null>(null);
  const protectedPreview = useProtectedDocument(previewDoc ? getDocumentPreviewUrl(application.id, previewDoc.id) : null, token);
  const protectedInspection = useProtectedDocument(inspectingDoc ? getDocumentPreviewUrl(application.id, inspectingDoc.id) : null, token);
  const [extractionDetail, setExtractionDetail] = useState<DocumentExtractionDetail | null>(null);
  const [loadingExtraction, setLoadingExtraction] = useState(false);
  const [reprocessing, setReprocessing] = useState(false);
  const [revealedFields, setRevealedFields] = useState<Record<string, boolean>>({});

  const handleFileUpload = async (documentType: string, file: File, afterVersion: number) => {
    setUploadingType(documentType);
    setLiveProgress({ status: 'WAITING_FOR_UPLOAD', stage: 'SENDING_FILE', message: 'Sending your document', version_number: afterVersion });
    setUploadError(null);
    let active = true;
    const readProgress = async () => {
      try {
        const current = await apiFetchProcessingProgress(token, application.id, documentType, afterVersion);
        if (active) setLiveProgress(current);
      } catch {
        // The upload request remains authoritative; a missed status poll must not interrupt it.
      }
    };
    const poll = window.setInterval(readProgress, 400);
    void readProgress();
    try {
      await apiUploadDocument(token, application.id, documentType, file);
      onRefresh();
    } catch (err: any) {
      setUploadError(err?.message || `Failed to upload ${documentType}`);
    } finally {
      active = false;
      window.clearInterval(poll);
      setUploadingType(null);
      setLiveProgress(null);
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
  const uploadedDocs = documents.filter((d) => d.status === 'UPLOADED');
  const uploadedMandatory = mandatoryDocs.filter((d) => d.status === 'UPLOADED');
  const allMandatoryUploaded = mandatoryDocs.length > 0 && uploadedMandatory.length === mandatoryDocs.length;

  const needsAttentionDocs = documents.filter(
    (d) =>
      d.status === 'UPLOADED' &&
      (hasWrongDocumentType(d, application.constitution) ||
        (d.is_type_match === false && d.detected_document_type === 'UNKNOWN') ||
        (d.processing_status === 'NEEDS_REVIEW' && !(isAcceptedAlternative(d, application.constitution) && (d.review_flags || []).every((flag) => flag.startsWith('Document type mismatch')))) ||
        d.processing_status === 'FAILED')
  );

  const acceptedDocs = documents.filter(
    (d) =>
      d.status === 'UPLOADED' &&
      (d.is_type_match !== false || isAcceptedAlternative(d, application.constitution)) &&
      (d.processing_status !== 'NEEDS_REVIEW' || (isAcceptedAlternative(d, application.constitution) && (d.review_flags || []).every((flag) => flag.startsWith('Document type mismatch')))) &&
      d.processing_status !== 'FAILED'
  );

  return (
    <div className="space-y-6">
      <div>
        <h3 className="text-base font-bold text-slate-900 flex items-center gap-2">
          <FileText className="w-5 h-5 text-indigo-600" />
          Step 6: Documents You Need to Provide
        </h3>
        <p className="text-xs text-slate-500 mt-1">
          Upload the evidence required for your business entity (
          <span className="font-semibold text-slate-700">{application.constitution.replace(/_/g, ' ')}</span>
          ). We compare what you enter with the documents you provide. Registry results in this demo are simulated and labelled.
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

      {uploadingType && liveProgress && (
        <div role="status" aria-live="polite" className="border-l-4 border-slate-900 bg-white px-4 py-3 text-sm text-slate-800">
          <p className="font-semibold">Checking your document</p>
          <p className="mt-1 text-slate-600">{liveProgress.message}</p>
          <ol className="mt-3 grid grid-cols-2 gap-2 sm:grid-cols-5" aria-label="Document check stages">
            {PROCESS_STEPS.map((step, index) => {
              const activeIndex = PROCESS_STEPS.findIndex((item) => item.stage === liveProgress.stage);
              const done = activeIndex > index || liveProgress.stage === 'COMPLETE';
              const current = activeIndex === index || (liveProgress.stage === 'QUEUED' && index === 0);
              return (
                <li key={step.stage} aria-current={current ? 'step' : undefined} className={`border-t-2 pt-1 text-xs ${done ? 'border-emerald-600 text-slate-700' : current ? 'border-slate-900 font-semibold text-slate-900' : 'border-slate-200 text-slate-400'}`}>
                  {done ? '✓ ' : ''}{step.label}
                </li>
              );
            })}
          </ol>
        </div>
      )}

      {/* Progress and Semantic Health Card */}
      <div className="p-4 rounded-xl bg-white border border-slate-200 shadow-2xs space-y-3">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div>
            <span className="text-xs font-bold text-slate-900 block mb-1">
              Document Checklist Progress
            </span>
            <p className="text-[11px] text-slate-500">
              {allMandatoryUploaded && needsAttentionDocs.length === 0
                ? 'All mandatory statutory documents uploaded and successfully processed.'
                : needsAttentionDocs.length > 0
                ? `${needsAttentionDocs.length} uploaded document(s) have potential issues detected by automated verification. You may replace them before final submission.`
                : 'Please upload all required statutory documents to unlock submission.'}
            </p>
          </div>
          <div className="w-full sm:w-48 bg-slate-100 rounded-full h-2.5 overflow-hidden">
            <div
              className={`h-2.5 rounded-full transition-all ${
                allMandatoryUploaded
                  ? needsAttentionDocs.length > 0
                    ? 'bg-amber-500'
                    : 'bg-emerald-500'
                  : 'bg-indigo-600'
              }`}
              style={{
                width: `${mandatoryDocs.length ? (uploadedMandatory.length / mandatoryDocs.length) * 100 : 0}%`,
              }}
            />
          </div>
        </div>

        {/* 4 Distinct Counters */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5 pt-2 border-t border-slate-100 text-xs">
          <div className="p-2 rounded-lg bg-slate-50 border border-slate-200 flex items-center justify-between">
            <span className="text-slate-600 font-medium">Required:</span>
            <span className="font-bold text-slate-900">{mandatoryDocs.length}</span>
          </div>
          <div className="p-2 rounded-lg bg-indigo-50/60 border border-indigo-200 flex items-center justify-between">
            <span className="text-indigo-800 font-medium">Uploaded:</span>
            <span className="font-bold text-indigo-700">{uploadedDocs.length}</span>
          </div>
          <div className="p-2 rounded-lg bg-amber-50 border border-amber-200 flex items-center justify-between">
            <span className="text-amber-800 font-medium">Need Attention:</span>
            <span className="font-bold text-amber-700">{needsAttentionDocs.length}</span>
          </div>
          <div className="p-2 rounded-lg bg-emerald-50 border border-emerald-200 flex items-center justify-between">
            <span className="text-emerald-800 font-medium">Accepted:</span>
            <span className="font-bold text-emerald-700">{acceptedDocs.length}</span>
          </div>
        </div>
      </div>

      {/* Document Slots */}
      <div className="space-y-4">
        {documents.map((slot) => {
          const isUploaded = slot.status === 'UPLOADED';
          const isBusy = uploadingType === slot.document_type;
          const procStatus = slot.processing_status;
          const hasTypeMismatch = hasWrongDocumentType(slot, application.constitution);

          // Determine distinct semantic status
          const acceptedAlternative = isAcceptedAlternative(slot, application.constitution);
          const visibleFlags = (slot.review_flags || []).filter((flag) => !(acceptedAlternative && flag.startsWith('Document type mismatch')));
          const hasFlags = visibleFlags.length > 0;
          const isNeedsAttention = isUploaded && (hasTypeMismatch || (slot.is_type_match === false && slot.detected_document_type === 'UNKNOWN') || (procStatus === 'NEEDS_REVIEW' && !(acceptedAlternative && (slot.review_flags || []).every((flag) => flag.startsWith('Document type mismatch')))) || procStatus === 'FAILED');
          const isProcessing = isUploaded && (procStatus === 'PROCESSING' || procStatus === 'QUEUED');
          const isVerifiedExtracted = isUploaded && !isNeedsAttention && !isProcessing;

          return (
            <div
              key={slot.id}
              className={`p-5 rounded-xl border transition-all ${
                isNeedsAttention
                  ? 'bg-amber-50/40 border-amber-300'
                  : isVerifiedExtracted
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

                    {/* Requirement Tier */}
                    {slot.is_required ? (
                      <span className="text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded bg-rose-50 text-rose-700 border border-rose-200">
                        Mandatory
                      </span>
                    ) : (
                      <span className="text-[10px] font-medium px-2 py-0.5 rounded bg-slate-100 text-slate-600 border border-slate-200">
                        Conditional / Optional
                      </span>
                    )}

                    {/* Semantic Status Badge */}
                    {!isUploaded ? (
                      <span className="text-[10px] font-semibold px-2 py-0.5 rounded bg-slate-100 text-slate-500 border border-slate-200">
                        Not uploaded
                      </span>
                    ) : isNeedsAttention ? (
                      <span className="text-[10px] font-semibold px-2.5 py-0.5 rounded-full bg-amber-100 text-amber-900 border border-amber-300 flex items-center gap-1">
                        <AlertTriangle className="w-3 h-3 text-amber-600" />
                        Needs your attention (v{slot.current_version?.version_number || 1})
                      </span>
                    ) : isProcessing ? (
                      <span className="text-[10px] font-semibold px-2.5 py-0.5 rounded-full bg-blue-50 text-blue-700 border border-blue-200 flex items-center gap-1">
                        <RefreshCw className="w-3 h-3 text-blue-600 animate-spin" />
                        Being checked... (v{slot.current_version?.version_number || 1})
                      </span>
                    ) : (
                      <span className="text-[10px] font-semibold px-2.5 py-0.5 rounded-full bg-emerald-100 text-emerald-800 border border-emerald-300 flex items-center gap-1">
                        <CheckCircle2 className="w-3 h-3 text-emerald-600" />
                        Read and checked (v{slot.current_version?.version_number || 1})
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
                            {slot.detected_document_type.replace(/_/g, ' ')}
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
                        <span className="font-bold">Document Type Check:</span> The uploaded file appears to be a{' '}
                        <span className="font-bold underline">{slot.detected_document_type?.replace(/_/g, ' ')}</span>{' '}
                        instead of your <span className="font-bold">{slot.title}</span>. Please verify and upload the correct document if needed.
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
                          <Search className="w-3 h-3" /> View Evidence &amp; Confidence
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
                      {visibleFlags.map((flag, idx) => (
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
                        onClick={() => {
                          setPreviewError(false);
                          setPreviewDoc(slot);
                        }}
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
                        <RefreshCw className="w-3.5 h-3.5 animate-spin" /> Checking...
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
                      disabled={uploadingType !== null}
                      accept=".pdf,.jpg,.jpeg,.png"
                      onChange={(e) => {
                        const file = e.target.files?.[0];
                        if (file) {
                          handleFileUpload(slot.document_type, file, slot.versions_count);
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
              <div className="flex items-center gap-3">
                <a
                  href={protectedPreview.url || undefined}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="px-3 py-1.5 text-xs font-semibold text-indigo-700 bg-white hover:bg-indigo-50 border border-indigo-200 rounded-lg shadow-2xs transition inline-flex items-center gap-1.5"
                >
                  <Eye className="w-3.5 h-3.5" />
                  Open in New Tab
                </a>
                <button
                  type="button"
                  onClick={() => setPreviewDoc(null)}
                  className="p-1 rounded-lg text-slate-400 hover:text-slate-600 hover:bg-slate-100"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>
            </div>

            <div className="flex-1 bg-slate-100 p-2 overflow-auto flex items-center justify-center">
              {(() => {
                const previewUrl = protectedPreview.url;
                if (!previewUrl) return <p role="status" className="p-6 text-sm">{protectedPreview.error || 'Opening document…'}</p>;
                const filename = previewDoc.current_version?.original_filename || '';
                const contentType = previewDoc.current_version?.content_type || '';
                const isPdf = contentType === 'application/pdf' || filename.toLowerCase().endsWith('.pdf');
                const isImage = contentType.startsWith('image/') || /\.(png|jpe?g)$/i.test(filename);

                if (previewError) {
                  return (
                    <div className="p-8 text-center space-y-2 bg-white rounded-xl border border-slate-200 max-w-md shadow-2xs">
                      <FileText className="w-10 h-10 text-slate-400 mx-auto" />
                      <p className="text-xs font-bold text-slate-800">Preview rendering not available inline</p>
                      <p className="text-[11px] text-slate-500">
                        The document file is securely stored. You can open it directly in a new tab.
                      </p>
                      <div className="pt-2">
                        <a
                          href={previewUrl}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="px-3.5 py-1.5 bg-indigo-600 text-white rounded-lg text-xs font-semibold inline-flex items-center gap-1.5"
                        >
                          <Eye className="w-3.5 h-3.5" /> Open Document in New Tab
                        </a>
                      </div>
                    </div>
                  );
                }

                if (isPdf) {
                  return (
                    <iframe
                      src={previewUrl}
                      title="Document Preview"
                      className="w-full h-full rounded-lg border border-slate-300 bg-white"
                    />
                  );
                }

                if (isImage) {
                  return (
                    <img
                      src={previewUrl}
                      alt="Document Preview"
                      className="max-h-full max-w-full object-contain rounded-lg shadow-sm"
                      onError={() => setPreviewError(true)}
                    />
                  );
                }

                return (
                  <div className="p-8 text-center space-y-2 bg-white rounded-xl border border-slate-200 max-w-md shadow-2xs">
                    <FileText className="w-10 h-10 text-slate-400 mx-auto" />
                    <p className="text-xs font-bold text-slate-800">Unsupported format for direct browser preview</p>
                    <p className="text-[11px] text-slate-500">
                      Standard inline rendering is supported for PDF, PNG, and JPEG files.
                    </p>
                    <div className="pt-2">
                      <a
                        href={previewUrl}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="px-3.5 py-1.5 bg-indigo-600 text-white rounded-lg text-xs font-semibold inline-flex items-center gap-1.5"
                      >
                        <Eye className="w-3.5 h-3.5" /> Open in New Tab
                      </a>
                    </div>
                  </div>
                );
              })()}
            </div>

            <div className="px-6 py-3 border-t border-slate-200 bg-white flex justify-between items-center text-xs text-slate-500">
              <span>Secure Document Storage &bull; Private Inline Streaming</span>
              <div className="flex items-center gap-2">
                <a
                  href={protectedPreview.url || undefined}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="px-3 py-1.5 rounded-lg border border-slate-200 hover:bg-slate-50 text-slate-700 font-semibold inline-flex items-center gap-1"
                >
                  <Eye className="w-3.5 h-3.5" />
                  Open in New Tab
                </a>
                <button
                  type="button"
                  onClick={() => setPreviewDoc(null)}
                  className="px-4 py-1.5 rounded-lg bg-slate-900 text-white font-semibold hover:bg-slate-800"
                >
                  Close Preview
                </button>
              </div>
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
                    OCR &amp; Compliance Extraction Evidence — {inspectingDoc.title}
                  </h4>
                  <p className="text-xs text-slate-500 font-mono">
                    {inspectingDoc.current_version?.original_filename} (Version{' '}
                    {inspectingDoc.current_version?.version_number})
                  </p>
                </div>
              </div>
              <button
                type="button"
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
                  {(() => {
                    const previewUrl = protectedInspection.url;
                    if (!previewUrl) return <p role="status" className="p-6 text-sm">{protectedInspection.error || 'Opening document…'}</p>;
                    const filename = inspectingDoc.current_version?.original_filename || '';
                    const contentType = inspectingDoc.current_version?.content_type || '';
                    const isPdf = contentType === 'application/pdf' || filename.toLowerCase().endsWith('.pdf');

                    if (isPdf) {
                      return (
                        <iframe
                          src={previewUrl}
                          title="Document Preview"
                          className="w-full h-full"
                        />
                      );
                    }
                    return (
                      <img
                        src={previewUrl}
                        alt="Document Preview"
                        className="max-h-full max-w-full object-contain p-2"
                      />
                    );
                  })()}
                </div>
              </div>

              {/* Right Column: Structured Extraction & Provenance */}
              <div className="h-full bg-white overflow-auto p-4 space-y-4">
                {loadingExtraction ? (
                  <div className="py-16 text-center text-xs text-slate-400 flex flex-col items-center gap-2">
                    <RefreshCw className="w-5 h-5 animate-spin text-indigo-600" />
                    Loading OCR extraction fields &amp; layout coordinates...
                  </div>
                ) : extractionDetail ? (
                  <>
                    <div className="p-3 bg-slate-50 rounded-xl border border-slate-200 space-y-1 text-xs">
                      <div className="flex justify-between items-center">
                        <span className="font-semibold text-slate-700">Classification:</span>
                        <span className="font-mono font-bold text-indigo-900">
                          {extractionDetail.detected_document_type || 'UNKNOWN'}
                        </span>
                      </div>
                      <div className="flex justify-between items-center">
                        <span className="font-semibold text-slate-700">Classification Confidence:</span>
                        <span className="font-mono font-bold text-slate-900">
                          {Math.round((extractionDetail.classification_confidence || 0) * 100)}%
                        </span>
                      </div>
                      <div className="flex justify-between items-center">
                        <span className="font-semibold text-slate-700">Provider &amp; Pages:</span>
                        <span>
                          {extractionDetail.provider_used} &bull; {extractionDetail.page_count} page(s)
                        </span>
                      </div>
                    </div>

                    <div className="space-y-2">
                      <span className="text-xs font-bold text-slate-900 block">
                        Extracted Statutory Fields ({extractionDetail.fields.length})
                      </span>

                      {extractionDetail.fields.length === 0 ? (
                        <div className="p-4 text-xs text-slate-400 text-center border border-dashed rounded-xl">
                          No specific fields extracted from this document.
                        </div>
                      ) : (
                        <div className="space-y-2">
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
                type="button"
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
