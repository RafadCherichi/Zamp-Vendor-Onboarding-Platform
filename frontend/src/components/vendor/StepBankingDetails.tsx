import React, { useState } from 'react';
import type { Application, ApplicationDraftUpdate } from '../../types/application';
import { Landmark, ShieldAlert, CheckCircle2, RotateCcw } from 'lucide-react';

interface StepProps {
  application: Application;
  onChange: (updates: ApplicationDraftUpdate) => void;
}

export const StepBankingDetails: React.FC<StepProps> = ({ application, onChange }) => {
  const isMaskedInitial = Boolean(
    application.bank_account_number &&
      (application.bank_account_number.includes('•') || application.bank_account_number.includes('*'))
  );

  const [isEditingAccount, setIsEditingAccount] = useState(!isMaskedInitial);
  const [accountNumber, setAccountNumber] = useState(isMaskedInitial ? '' : application.bank_account_number || '');
  const [confirmAccount, setConfirmAccount] = useState(isMaskedInitial ? '' : application.bank_account_number || '');

  const handleAccountChange = (val: string) => {
    const clean = val.replace(/\D/g, '');
    setAccountNumber(clean);
    if (confirmAccount && clean === confirmAccount) {
      onChange({ bank_account_number: clean });
    }
  };

  const handleConfirmChange = (val: string) => {
    const clean = val.replace(/\D/g, '');
    setConfirmAccount(clean);
    if (clean === accountNumber) {
      onChange({ bank_account_number: clean });
    }
  };

  const isMismatch = isEditingAccount && confirmAccount.length > 0 && accountNumber !== confirmAccount;
  const isMatch = isEditingAccount && confirmAccount.length > 0 && accountNumber === confirmAccount;

  return (
    <div className="space-y-6">
      <div>
        <h3 className="text-base font-bold text-slate-900 flex items-center gap-2">
          <Landmark className="w-5 h-5 text-indigo-600" />
          Section 4: Banking &amp; Disbursement Details
        </h3>
        <p className="text-xs text-slate-500 mt-1">
          Provide your commercial bank account details for invoice disbursement. Details must match
          the cancelled cheque or bank proof uploaded in the document checklist.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div>
          <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1">
            Beneficiary / Account Holder Name <span className="text-rose-500">*</span>
          </label>
          <input
            type="text"
            required
            value={application.bank_account_holder_name || ''}
            onChange={(e) => onChange({ bank_account_holder_name: e.target.value })}
            placeholder="Name exactly as printed on bank records"
            className="w-full px-3 py-2 text-xs border border-slate-300 rounded-lg focus:ring-2 focus:ring-indigo-500 bg-white"
          />
        </div>

        <div>
          <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1">
            Bank Name
          </label>
          <input
            type="text"
            value={application.bank_name || ''}
            onChange={(e) => onChange({ bank_name: e.target.value })}
            placeholder="e.g. HDFC Bank, State Bank of India, ICICI Bank"
            className="w-full px-3 py-2 text-xs border border-slate-300 rounded-lg focus:ring-2 focus:ring-indigo-500 bg-white"
          />
        </div>

        {/* Bank Account Number handling (with saved-mask preservation) */}
        {!isEditingAccount ? (
          <div className="col-span-1 md:col-span-2 p-3.5 rounded-xl bg-slate-50 border border-slate-200 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div>
              <span className="text-[11px] font-bold text-slate-500 uppercase tracking-wider block">
                Saved Bank Account Number
              </span>
              <span className="font-mono text-sm font-bold text-slate-900 tracking-wider">
                {application.bank_account_number}
              </span>
              <span className="text-[11px] text-emerald-600 block mt-0.5 font-medium flex items-center gap-1">
                <CheckCircle2 className="w-3.5 h-3.5" />
                Account number saved securely in draft (masked for privacy)
              </span>
            </div>
            <button
              type="button"
              onClick={() => {
                setIsEditingAccount(true);
                setAccountNumber('');
                setConfirmAccount('');
              }}
              className="px-3.5 py-1.5 text-xs font-bold text-indigo-700 bg-white hover:bg-indigo-50 rounded-lg border border-indigo-200 shadow-2xs transition-colors self-start sm:self-auto"
            >
              Change Account Number
            </button>
          </div>
        ) : (
          <>
            <div>
              <div className="flex items-center justify-between mb-1">
                <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider">
                  Bank Account Number <span className="text-rose-500">*</span>
                </label>
                {isMaskedInitial && (
                  <button
                    type="button"
                    onClick={() => {
                      setIsEditingAccount(false);
                      setAccountNumber('');
                      setConfirmAccount('');
                    }}
                    className="text-[11px] text-slate-500 hover:text-slate-700 inline-flex items-center gap-1"
                  >
                    <RotateCcw className="w-3 h-3" />
                    Keep Saved Account
                  </button>
                )}
              </div>
              <input
                type="password"
                required
                value={accountNumber}
                onChange={(e) => handleAccountChange(e.target.value)}
                placeholder="Enter account number"
                className="w-full px-3 py-2 text-xs font-mono border border-slate-300 rounded-lg focus:ring-2 focus:ring-indigo-500 bg-white"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1">
                Confirm Bank Account Number <span className="text-rose-500">*</span>
              </label>
              <input
                type="text"
                required
                value={confirmAccount}
                onChange={(e) => handleConfirmChange(e.target.value)}
                placeholder="Re-type account number"
                className="w-full px-3 py-2 text-xs font-mono border border-slate-300 rounded-lg focus:ring-2 focus:ring-indigo-500 bg-white"
              />
              {isMismatch && (
                <p className="text-[11px] text-rose-600 flex items-center gap-1 mt-1 font-medium">
                  <ShieldAlert className="w-3.5 h-3.5 shrink-0" />
                  Account numbers do not match.
                </p>
              )}
              {isMatch && (
                <p className="text-[11px] text-emerald-600 flex items-center gap-1 mt-1 font-medium">
                  <CheckCircle2 className="w-3.5 h-3.5 shrink-0" />
                  Account numbers confirmed.
                </p>
              )}
            </div>
          </>
        )}

        <div>
          <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1">
            IFSC Code (11 alphanumeric characters) <span className="text-rose-500">*</span>
          </label>
          <input
            type="text"
            maxLength={11}
            required
            value={application.bank_ifsc || ''}
            onChange={(e) => onChange({ bank_ifsc: e.target.value.toUpperCase().trim() })}
            placeholder="e.g. HDFC0000123"
            className="w-full px-3 py-2 text-xs font-mono uppercase tracking-wider border border-slate-300 rounded-lg focus:ring-2 focus:ring-indigo-500 bg-white"
          />
        </div>

        <div>
          <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1">
            Account Type <span className="text-rose-500">*</span>
          </label>
          <select
            value={application.bank_account_type || 'CURRENT'}
            onChange={(e) => onChange({ bank_account_type: e.target.value })}
            className="w-full px-3 py-2 text-xs border border-slate-300 rounded-lg focus:ring-2 focus:ring-indigo-500 bg-white"
          >
            <option value="CURRENT">Current Account (Commercial)</option>
            <option value="SAVINGS">Savings Account (Individual / Proprietor)</option>
            <option value="OD_CC">Overdraft / Cash Credit Account</option>
          </select>
        </div>
      </div>

      <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-200 text-xs text-slate-500">
        <span className="font-semibold text-slate-700">Security Safeguard:</span> Full bank account
        numbers are never exposed in public logs or non-privileged screens. A cancelled cheque will
        be required in the document checklist to verify account printed details.
      </div>
    </div>
  );
};
