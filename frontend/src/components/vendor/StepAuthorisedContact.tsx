import React from 'react';
import type { Application, ApplicationDraftUpdate } from '../../types/application';
import { UserCheck } from 'lucide-react';

interface StepProps {
  application: Application;
  onChange: (updates: ApplicationDraftUpdate) => void;
}

export const StepAuthorisedContact: React.FC<StepProps> = ({ application, onChange }) => {
  return (
    <div className="space-y-6">
      <div>
        <h3 className="text-base font-bold text-slate-900 flex items-center gap-2">
          <UserCheck className="w-5 h-5 text-indigo-600" />
          Step 3: Contact Details
        </h3>
        <p className="text-xs text-slate-500 mt-1">
          Provide the name and contact details of the person we can reach regarding your onboarding,
          purchase orders, and payment queries.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div>
          <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1">
            Contact Person Name <span className="text-rose-500">*</span>
          </label>
          <input
            type="text"
            required
            value={application.contact_name || ''}
            onChange={(e) => onChange({ contact_name: e.target.value })}
            placeholder="e.g. Vikram Malhotra"
            className="w-full px-3 py-2 text-xs border border-slate-300 rounded-lg focus:ring-2 focus:ring-indigo-500 bg-white"
          />
          <p className="text-[11px] text-slate-400 mt-1">Primary contact for all onboarding communications</p>
        </div>

        <div>
          <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1">
            Designation / Job Title <span className="text-rose-500">*</span>
          </label>
          <input
            type="text"
            required
            value={application.contact_designation || ''}
            onChange={(e) => onChange({ contact_designation: e.target.value })}
            placeholder="e.g. Proprietor, Director, Partner, Manager"
            className="w-full px-3 py-2 text-xs border border-slate-300 rounded-lg focus:ring-2 focus:ring-indigo-500 bg-white"
          />
          <p className="text-[11px] text-slate-400 mt-1">Role of the contact person within your organization</p>
        </div>

        <div>
          <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1">
            Email Address <span className="text-rose-500">*</span>
          </label>
          <input
            type="email"
            required
            value={application.contact_email || ''}
            onChange={(e) => onChange({ contact_email: e.target.value })}
            placeholder="e.g. contact@company.in"
            className="w-full px-3 py-2 text-xs border border-slate-300 rounded-lg focus:ring-2 focus:ring-indigo-500 bg-white"
          />
          <p className="text-[11px] text-slate-400 mt-1">Official email where order and payment notices will be sent</p>
        </div>

        <div>
          <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1">
            Mobile Number (India) <span className="text-rose-500">*</span>
          </label>
          <input
            type="tel"
            required
            value={application.contact_mobile || ''}
            onChange={(e) => onChange({ contact_mobile: e.target.value })}
            placeholder="e.g. 98200 12345"
            className="w-full px-3 py-2 text-xs border border-slate-300 rounded-lg focus:ring-2 focus:ring-indigo-500 bg-white"
          />
          <p className="text-[11px] text-slate-400 mt-1">10-digit Indian mobile number for verification updates</p>
        </div>
      </div>

      {/* Authorised Signatory */}
      <div className="bg-slate-50 p-4 rounded-xl border border-slate-200 space-y-2">
        <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider">
          Authorised Signatory Name (if different)
        </label>
        <div className="max-w-md">
          <input
            type="text"
            value={application.authorised_signatory_name || ''}
            onChange={(e) => onChange({ authorised_signatory_name: e.target.value })}
            placeholder="Leave blank if the contact person above is the sole signatory"
            className="w-full px-3 py-2 text-xs border border-slate-300 rounded-lg focus:ring-2 focus:ring-indigo-500 bg-white"
          />
        </div>
        <p className="text-[11px] text-slate-500">
          If someone other than the contact person signs legal agreements and contracts on behalf of your
          business, enter their name here. For companies and LLPs, board resolution or authority evidence may
          be requested in the document checklist.
        </p>
      </div>
    </div>
  );
};
