import React from 'react';
import type { Application, ApplicationDraftUpdate } from '../../types/application';
import { Tag, AlertCircle } from 'lucide-react';

interface StepProps {
  application: Application;
  onChange: (updates: ApplicationDraftUpdate) => void;
}

const CATEGORIES: { id: string; label: string; desc: string; licenceHint?: string }[] = [
  {
    id: 'goods_supplier',
    label: 'Goods Supplier / Trader',
    desc: 'Supply of finished goods, raw materials, wholesale, or distribution.',
  },
  {
    id: 'manufacturer',
    label: 'Manufacturer',
    desc: 'Production, assembly, fabrication, or industrial processing of physical items.',
  },
  {
    id: 'professional_services',
    label: 'Professional Services',
    desc: 'Consulting, legal, accounting, marketing, or human resource services.',
  },
  {
    id: 'it_services',
    label: 'IT & Software Services',
    desc: 'Software development, cloud hosting, SaaS, IT infrastructure, or digital solutions.',
  },
  {
    id: 'logistics',
    label: 'Logistics & Transport',
    desc: 'Freight transport, warehousing, courier, fleet carriage, or supply-chain logistics.',
    licenceHint: 'Requires Transport / Fleet Carrier Permit in Document Checklist.',
  },
  {
    id: 'construction',
    label: 'Construction & Contracting',
    desc: 'Civil contracting, infrastructure, electrical/mechanical works, or labour supply.',
  },
  {
    id: 'food_catering',
    label: 'Food, Beverages & Catering',
    desc: 'Canteen management, food supply, cafeteria catering, or packaged consumables.',
    licenceHint: 'Requires FSSAI Food Safety Licence in Document Checklist.',
  },
  {
    id: 'other',
    label: 'Other Business Activities',
    desc: 'General commercial services and vendor capabilities not listed above.',
  },
];

export const StepBusinessClassification: React.FC<StepProps> = ({ application, onChange }) => {
  const selectedCategories = application.categories || [];

  const handleToggle = (categoryId: string) => {
    let updated: string[];
    if (selectedCategories.includes(categoryId)) {
      updated = selectedCategories.filter((c) => c !== categoryId);
    } else {
      updated = [...selectedCategories, categoryId];
    }
    onChange({ categories: updated });
  };

  return (
    <div className="space-y-6">
      <div>
        <h3 className="text-base font-bold text-slate-900 flex items-center gap-2">
          <Tag className="w-5 h-5 text-indigo-600" />
          Section 5: Business Activity & Classification
        </h3>
        <p className="text-xs text-slate-500 mt-1">
          Select all applicable business operations your organization provides to the buyer. This
          determines applicable industry licences and compliance requirements.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        {CATEGORIES.map((cat) => {
          const isSelected = selectedCategories.includes(cat.id);
          return (
            <label
              key={cat.id}
              className={`p-4 rounded-xl border text-xs cursor-pointer transition-all flex items-start gap-3 ${
                isSelected
                  ? 'border-indigo-600 bg-indigo-50/40 ring-1 ring-indigo-300'
                  : 'border-slate-200 hover:border-slate-300 bg-white'
              }`}
            >
              <input
                type="checkbox"
                checked={isSelected}
                onChange={() => handleToggle(cat.id)}
                className="mt-0.5 h-4 w-4 text-indigo-600 rounded border-slate-300 focus:ring-indigo-500"
              />
              <div className="space-y-1">
                <span className="font-bold text-slate-900 block">{cat.label}</span>
                <p className="text-[11px] text-slate-500 leading-tight">{cat.desc}</p>
                {cat.licenceHint && isSelected && (
                  <span className="inline-flex items-center gap-1 text-[10px] font-semibold text-amber-700 bg-amber-50 px-2 py-0.5 rounded border border-amber-200 mt-1">
                    <AlertCircle className="w-3 h-3 text-amber-600 shrink-0" />
                    {cat.licenceHint}
                  </span>
                )}
              </div>
            </label>
          );
        })}
      </div>

      <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-200 text-xs text-slate-600">
        <span className="font-semibold text-slate-900">Dynamic Checklist Impact:</span> The Document
        Checklist in Step 6 automatically recalculates when categories change. For example, selecting{' '}
        <span className="font-semibold">Food, Beverages & Catering</span> activates mandatory FSSAI
        verification.
      </div>
    </div>
  );
};
