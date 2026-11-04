import React from 'react';
import { CheckCircle2, Clock, Layers } from 'lucide-react';

export const FoundationRoadmap: React.FC = () => {
  const increments = [
    {
      id: 0,
      name: 'Increment 0: Foundation',
      desc: 'Workspace inspection, FastAPI backend, React Vite frontend, Alembic migration, private storage adapter, and health verification.',
      status: 'completed',
    },
    {
      id: 1,
      name: 'Increment 1: App Shell & Identity',
      desc: 'Organisation-scoped authentication, RBAC (Vendor, Procurement, Reviewer, Admin), and expiring invitation tokens.',
      status: 'pending',
    },
    {
      id: 2,
      name: 'Increment 2: Vendor Onboarding',
      desc: 'Mobile-first dynamic 6-section form, activity/constitution-based conditional checklist, draft save/resume, and submission.',
      status: 'pending',
    },
    {
      id: 3,
      name: 'Increment 3: Document Processing',
      desc: 'Private object storage with checksums, async queue/worker, OCR/vision extraction with confidence & provenance.',
      status: 'pending',
    },
    {
      id: 4,
      name: 'Increment 4: Validation & Verification',
      desc: 'Deterministic rules, PAN/GST cross-checking, duplicate candidate detection, and mock verification adapters.',
      status: 'pending',
    },
    {
      id: 5,
      name: 'Increment 5: Exception Lifecycle',
      desc: 'Explainable vendor correction flow, versioned document replacement, and dependency-aware selective revalidation.',
      status: 'pending',
    },
    {
      id: 6,
      name: 'Increment 6: Internal Workspace',
      desc: 'Reviewer desktop workspace, side-by-side evidence inspection, decision recording with reasons, and procurement queue.',
      status: 'pending',
    },
    {
      id: 7,
      name: 'Increment 7: Hardening & Demo Data',
      desc: 'Append-only audit timeline, file security/quarantine, acceptance test suite, and synthetic vendor demo journeys.',
      status: 'pending',
    },
  ];

  return (
    <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
      <div className="px-6 py-4 border-b border-slate-100 flex items-center justify-between">
        <div>
          <h2 className="text-base font-semibold text-slate-900 flex items-center gap-2">
            <Layers className="w-5 h-5 text-indigo-600" />
            Product Architecture & Build Roadmap
          </h2>
          <p className="text-xs text-slate-500 mt-0.5">
            Structured delivery roadmap based on Section 16 of the Consolidated Product Specification
          </p>
        </div>
        <span className="text-xs font-semibold px-2.5 py-1 rounded-full bg-indigo-50 text-indigo-700 border border-indigo-200">
          Increment 0 Active
        </span>
      </div>

      <div className="p-6">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {increments.map((inc) => (
            <div
              key={inc.id}
              className={`p-4 rounded-lg border transition-all ${
                inc.status === 'completed'
                  ? 'bg-emerald-50/50 border-emerald-200'
                  : 'bg-slate-50/50 border-slate-200 opacity-80'
              }`}
            >
              <div className="flex items-start justify-between">
                <div className="flex items-center gap-2">
                  {inc.status === 'completed' ? (
                    <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
                  ) : (
                    <Clock className="w-4 h-4 text-slate-400 shrink-0" />
                  )}
                  <h3
                    className={`text-sm font-semibold ${
                      inc.status === 'completed' ? 'text-emerald-900' : 'text-slate-700'
                    }`}
                  >
                    {inc.name}
                  </h3>
                </div>
                <span
                  className={`text-[10px] font-semibold uppercase px-2 py-0.5 rounded ${
                    inc.status === 'completed'
                      ? 'bg-emerald-100 text-emerald-800'
                      : 'bg-slate-200 text-slate-600'
                  }`}
                >
                  {inc.status === 'completed' ? 'Current Foundation' : 'Upcoming'}
                </span>
              </div>
              <p className="text-xs text-slate-600 mt-2 pl-6 leading-relaxed">{inc.desc}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
