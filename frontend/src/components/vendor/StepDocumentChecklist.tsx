import React, { useState } from 'react';
import type { Application, DocumentSlot } from '../../types/application';
import { apiUploadDocument, getDocumentPreviewUrl } from '../../api/applications';
import {
  FileText,
  Upload,
  CheckCircle2,
  Eye,
  RefreshCw,
  AlertTriangle,
  X,
  FileCheck,
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
          ), tax registration, and business operations.
        </p>
      </div>

      {uploadError && (
        <div className="p-3.5 rounded-xl bg-rose-50 border border-rose-200 text-xs text-rose-700 flex items-start gap-2.5">
          <AlertTriangle className="w-4 h-4 text-rose-600 shrink-0 mt-0.5" />
          <div>
            <span className="font-bold">Upload Error:</span> {uploadError}
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
      <div className="space-y-3">
        {documents.map((slot) => {
          const isUploaded = slot.status === 'UPLOADED';
          const isBusy = uploadingType === slot.document_type;

          return (
            <div
              key={slot.id}
              className={`p-5 rounded-xl border transition-all ${
                isUploaded
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

                  {isUploaded && slot.current_version && (
                    <div className="text-xs font-mono text-emerald-800 bg-white/80 px-2.5 py-1.5 rounded-lg border border-emerald-200 inline-flex items-center gap-2 mt-1">
                      <FileCheck className="w-3.5 h-3.5 text-emerald-600" />
                      <span>{slot.current_version.original_filename}</span>
                      <span className="text-[10px] text-slate-400">
                        ({Math.round(slot.current_version.file_size_bytes / 1024)} KB &bull;{' '}
                        {new Date(slot.current_version.created_at).toLocaleTimeString()})
                      </span>
                    </div>
                  )}
                </div>

                {/* Upload / Action Buttons */}
                <div className="flex items-center gap-2 shrink-0 self-start">
                  {isUploaded && (
                    <button
                      type="button"
                      onClick={() => setPreviewDoc(slot)}
                      className="inline-flex items-center gap-1 px-3 py-1.5 rounded-lg text-xs font-medium text-slate-700 bg-white hover:bg-slate-50 border border-slate-200 shadow-2xs transition-colors"
                    >
                      <Eye className="w-3.5 h-3.5 text-indigo-600" />
                      Preview
                    </button>
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
    </div>
  );
};
