import React from 'react';
import type { Application, ApplicationDraftUpdate, Constitution } from '../../types/application';
import { Building, MapPin } from 'lucide-react';

interface StepProps {
  application: Application;
  onChange: (updates: ApplicationDraftUpdate) => void;
}

const CONSTITUTIONS: { value: Constitution; label: string; desc: string }[] = [
  {
    value: 'PROPRIETORSHIP',
    label: 'Sole Proprietorship',
    desc: 'Unincorporated business owned and run by one individual.',
  },
  {
    value: 'PARTNERSHIP',
    label: 'Partnership Firm',
    desc: 'Firm governed by the Indian Partnership Act, 1932.',
  },
  {
    value: 'LLP',
    label: 'Limited Liability Partnership (LLP)',
    desc: 'Corporate body registered under the LLP Act, 2008 with MCA.',
  },
  {
    value: 'PVT_LTD',
    label: 'Private Limited Company',
    desc: 'Privately held legal entity registered under the Companies Act with CIN.',
  },
  {
    value: 'PUB_LTD',
    label: 'Public Limited Company',
    desc: 'Public company incorporated with MCA under the Companies Act.',
  },
];

export const StepBusinessIdentity: React.FC<StepProps> = ({ application, onChange }) => {
  return (
    <div className="space-y-6">
      <div>
        <h3 className="text-base font-bold text-slate-900 flex items-center gap-2">
          <Building className="w-5 h-5 text-indigo-600" />
          Step 1: About Your Business
        </h3>
        <p className="text-xs text-slate-500 mt-1">
          Tell us about your business name, legal structure, and registered office address as shown on your official registration certificates.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div>
          <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1">
            Legal Business Name <span className="text-rose-500">*</span>
          </label>
          <input
            type="text"
            required
            value={application.legal_name || ''}
            onChange={(e) => onChange({ legal_name: e.target.value })}
            placeholder="Official legal name as registered"
            className="w-full px-3 py-2 text-xs border border-slate-300 rounded-lg focus:ring-2 focus:ring-indigo-500 bg-white"
          />
        </div>

        <div>
          <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1">
            Trade Name (if different)
          </label>
          <input
            type="text"
            value={application.trade_name || ''}
            onChange={(e) => onChange({ trade_name: e.target.value })}
            placeholder="Brand or trade operating name"
            className="w-full px-3 py-2 text-xs border border-slate-300 rounded-lg focus:ring-2 focus:ring-indigo-500 bg-white"
          />
        </div>
      </div>

      {/* Constitution Selector */}
      <div>
        <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-2">
          Legal Constitution <span className="text-rose-500">*</span>
        </label>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
          {CONSTITUTIONS.map((c) => (
            <label
              key={c.value}
              className={`p-3 rounded-xl border text-xs cursor-pointer transition-all flex flex-col justify-between ${
                application.constitution === c.value
                  ? 'border-indigo-600 bg-indigo-50/50 ring-2 ring-indigo-200'
                  : 'border-slate-200 hover:border-slate-300 bg-white'
              }`}
            >
              <div className="flex items-center justify-between mb-1">
                <span className="font-bold text-slate-900">{c.label}</span>
                <input
                  type="radio"
                  name="constitution"
                  value={c.value}
                  checked={application.constitution === c.value}
                  onChange={() => onChange({ constitution: c.value })}
                  className="text-indigo-600 focus:ring-indigo-500"
                />
              </div>
              <p className="text-[11px] text-slate-500 leading-tight">{c.desc}</p>
            </label>
          ))}
        </div>
      </div>

      {/* Establishment Date */}
      <div>
        <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1">
          Date of Establishment / Incorporation
        </label>
        <input
          type="date"
          value={application.date_of_establishment || ''}
          onChange={(e) => onChange({ date_of_establishment: e.target.value })}
          className="w-full md:w-64 px-3 py-2 text-xs border border-slate-300 rounded-lg focus:ring-2 focus:ring-indigo-500 bg-white"
        />
      </div>

      {/* Addresses */}
      <div className="pt-2 border-t border-slate-100 space-y-4">
        <h4 className="text-xs font-bold text-slate-900 flex items-center gap-1.5">
          <MapPin className="w-4 h-4 text-slate-400" />
          Location and Address Details
        </h4>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1">
              Registered Office Address <span className="text-rose-500">*</span>
            </label>
            <textarea
              rows={3}
              required
              value={application.registered_address || ''}
              onChange={(e) => onChange({ registered_address: e.target.value })}
              placeholder="Full registered address as per tax / statutory records"
              className="w-full px-3 py-2 text-xs border border-slate-300 rounded-lg focus:ring-2 focus:ring-indigo-500 bg-white"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1">
              Operating / Factory Address (if different)
            </label>
            <textarea
              rows={3}
              value={application.operating_address || ''}
              onChange={(e) => onChange({ operating_address: e.target.value })}
              placeholder="Leave blank if identical to registered office address"
              className="w-full px-3 py-2 text-xs border border-slate-300 rounded-lg focus:ring-2 focus:ring-indigo-500 bg-white"
            />
          </div>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <div>
            <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1">
              City <span className="text-rose-500">*</span>
            </label>
            <input
              type="text"
              required
              value={application.city || ''}
              onChange={(e) => onChange({ city: e.target.value })}
              placeholder="e.g. Mumbai, Bengaluru"
              className="w-full px-3 py-2 text-xs border border-slate-300 rounded-lg focus:ring-2 focus:ring-indigo-500 bg-white"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1">
              State / Union Territory <span className="text-rose-500">*</span>
            </label>
            <input
              type="text"
              required
              value={application.state || ''}
              onChange={(e) => onChange({ state: e.target.value })}
              placeholder="e.g. Maharashtra, Karnataka"
              className="w-full px-3 py-2 text-xs border border-slate-300 rounded-lg focus:ring-2 focus:ring-indigo-500 bg-white"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1">
              PIN Code <span className="text-rose-500">*</span>
            </label>
            <input
              type="text"
              maxLength={6}
              required
              value={application.pincode || ''}
              onChange={(e) => onChange({ pincode: e.target.value.replace(/\D/g, '') })}
              placeholder="6-digit postal code"
              className="w-full px-3 py-2 text-xs font-mono border border-slate-300 rounded-lg focus:ring-2 focus:ring-indigo-500 bg-white"
            />
          </div>
        </div>
      </div>
    </div>
  );
};
