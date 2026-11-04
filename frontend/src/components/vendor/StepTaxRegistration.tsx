import React from 'react';
import type { Application, ApplicationDraftUpdate } from '../../types/application';
import { FileCheck2, Info } from 'lucide-react';

interface StepProps {
  application: Application;
  onChange: (updates: ApplicationDraftUpdate) => void;
}

export const StepTaxRegistration: React.FC<StepProps> = ({ application, onChange }) => {
  const isCorporateOrLLP = ['PVT_LTD', 'PUB_LTD', 'LLP'].includes(application.constitution);

  return (
    <div className="space-y-6">
      <div>
        <h3 className="text-base font-bold text-slate-900 flex items-center gap-2">
          <FileCheck2 className="w-5 h-5 text-indigo-600" />
          Section 2: Tax & Statutory Registration
        </h3>
        <p className="text-xs text-slate-500 mt-1">
          Provide your Indian tax identifiers. GST and MSME registrations are conditional based on
          your business eligibility.
        </p>
      </div>

      {/* PAN */}
      <div className="bg-white p-4 rounded-xl border border-slate-200 space-y-2">
        <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider">
          Permanent Account Number (PAN) <span className="text-rose-500">*</span>
        </label>
        <div className="max-w-md">
          <input
            type="text"
            maxLength={10}
            required
            value={application.pan || ''}
            onChange={(e) => onChange({ pan: e.target.value.toUpperCase().trim() })}
            placeholder="e.g. AAPFU0938L"
            className="w-full px-3 py-2 text-sm font-mono tracking-wider uppercase border border-slate-300 rounded-lg focus:ring-2 focus:ring-indigo-500 bg-white"
          />
        </div>
        <p className="text-[11px] text-slate-500 flex items-center gap-1 mt-1">
          <Info className="w-3.5 h-3.5 text-slate-400 shrink-0" />
          {application.constitution === 'PROPRIETORSHIP'
            ? "For sole proprietorship, provide the proprietor's individual 10-digit PAN."
            : `For ${application.constitution.replace('_', ' ')}, provide the entity's registered PAN.`}
        </p>
      </div>

      {/* GST Section */}
      <div className="bg-white p-4 rounded-xl border border-slate-200 space-y-3">
        <div className="flex items-start gap-3">
          <input
            type="checkbox"
            id="gst_toggle"
            checked={application.is_gst_registered}
            onChange={(e) =>
              onChange({
                is_gst_registered: e.target.checked,
                gstin: e.target.checked ? (application.gstin || '') : '',
              })
            }
            className="mt-1 h-4 w-4 text-indigo-600 rounded border-slate-300 focus:ring-indigo-500"
          />
          <div>
            <label htmlFor="gst_toggle" className="text-xs font-bold text-slate-900 cursor-pointer">
              Our business is registered under Goods & Services Tax (GST)
            </label>
            <p className="text-[11px] text-slate-500">
              Check this if you possess an active GSTIN. GST registration is not universally mandatory
              for vendors below the statutory turnover threshold.
            </p>
          </div>
        </div>

        {application.is_gst_registered && (
          <div className="pl-7 pt-2 border-t border-slate-100 max-w-md space-y-1">
            <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1">
              Goods and Services Tax Identification Number (GSTIN) <span className="text-rose-500">*</span>
            </label>
            <input
              type="text"
              maxLength={15}
              required={application.is_gst_registered}
              value={application.gstin || ''}
              onChange={(e) => onChange({ gstin: e.target.value.toUpperCase().trim() })}
              placeholder="e.g. 27AAPFU0938L1ZV"
              className="w-full px-3 py-2 text-sm font-mono tracking-wider uppercase border border-slate-300 rounded-lg focus:ring-2 focus:ring-indigo-500 bg-white"
            />
            <p className="text-[11px] text-slate-400">
              Standard 15-character format: 2 state digits + 10 PAN characters + 1 entity digit + 'Z' + checksum.
            </p>
          </div>
        )}
      </div>

      {/* Udyam MSME Section */}
      <div className="bg-white p-4 rounded-xl border border-slate-200 space-y-3">
        <div className="flex items-start gap-3">
          <input
            type="checkbox"
            id="udyam_toggle"
            checked={application.is_udyam_registered}
            onChange={(e) =>
              onChange({
                is_udyam_registered: e.target.checked,
                udyam_number: e.target.checked ? (application.udyam_number || '') : '',
              })
            }
            className="mt-1 h-4 w-4 text-indigo-600 rounded border-slate-300 focus:ring-indigo-500"
          />
          <div>
            <label htmlFor="udyam_toggle" className="text-xs font-bold text-slate-900 cursor-pointer">
              Registered as Micro, Small, or Medium Enterprise (Udyam MSME)
            </label>
            <p className="text-[11px] text-slate-500">
              Check this if your enterprise holds an active Udyam Registration. Registration is permanent
              and does not require periodic renewal.
            </p>
          </div>
        </div>

        {application.is_udyam_registered && (
          <div className="pl-7 pt-2 border-t border-slate-100 max-w-md space-y-1">
            <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1">
              Udyam Registration Number <span className="text-rose-500">*</span>
            </label>
            <input
              type="text"
              maxLength={25}
              required={application.is_udyam_registered}
              value={application.udyam_number || ''}
              onChange={(e) => onChange({ udyam_number: e.target.value.toUpperCase().trim() })}
              placeholder="e.g. UDYAM-MH-02-0012345"
              className="w-full px-3 py-2 text-xs font-mono uppercase border border-slate-300 rounded-lg focus:ring-2 focus:ring-indigo-500 bg-white"
            />
          </div>
        )}
      </div>

      {/* Corporate CIN / LLPIN */}
      {isCorporateOrLLP && (
        <div className="bg-white p-4 rounded-xl border border-slate-200 space-y-2">
          <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider">
            {application.constitution === 'LLP'
              ? 'LLP Identification Number (LLPIN)'
              : 'Corporate Identification Number (CIN)'}{' '}
            <span className="text-rose-500">*</span>
          </label>
          <div className="max-w-md">
            <input
              type="text"
              maxLength={25}
              required={isCorporateOrLLP}
              value={application.cin_llpin || ''}
              onChange={(e) => onChange({ cin_llpin: e.target.value.toUpperCase().trim() })}
              placeholder={application.constitution === 'LLP' ? 'e.g. AAA-1234' : 'e.g. U72200KA2020PTC123456'}
              className="w-full px-3 py-2 text-xs font-mono uppercase border border-slate-300 rounded-lg focus:ring-2 focus:ring-indigo-500 bg-white"
            />
          </div>
          <p className="text-[11px] text-slate-500">
            Mandatory MCA statutory registration number for corporate / LLP status verification.
          </p>
        </div>
      )}
    </div>
  );
};
