import React, { useCallback, useEffect, useState } from 'react';
import { ArrowUpRight, Check, Clock3, LoaderCircle, RefreshCw, ShieldCheck, X } from 'lucide-react';
import { apiFetchValidationRun, apiFetchValidationRunHistory } from '../../api/validation';
import type { ValidationRun, ValidationRunHistoryItem } from '../../types/validation';

interface Props {
  token: string;
  onOpenApplication: (id: string) => void;
}

const outcomeText = (outcome: ValidationRunHistoryItem['outcome']) => ({
  APPROVED: 'Ready to approve',
  REJECTED: 'Rejected',
  PENDING: 'Pending review',
}[outcome]);

const plainReason = (reason: string) => {
  const value = reason.replace(/^\[SIMULATED\]\s*/i, '');
  if (/does not match declared holder|beneficiary name.*does not match/i.test(value)) {
    return 'The bank account holder name does not match the vendor’s legal name. Review the bank proof before approval.';
  }
  if (/account number.*(?:mismatch|does not match|differ)|discrepancy in bank account number/i.test(value)) {
    return 'The bank details on the document do not match the form. Check the account information before approval.';
  }
  if (/bank holder name comparison.*(?:mismatch|does not align)|significant mismatch/i.test(value)) {
    return 'The name on the bank proof does not align with the submitted business name. A reviewer should check the evidence.';
  }
  if (/unreadable|field was missing/i.test(value)) {
    return 'We could not read all the details in this document. Ask the vendor for a clearer copy or review it manually.';
  }
  if (/simulated mca registry verification failed|cin\/llpin not found/i.test(value)) {
    return 'The company registration number was not found in the sample registry. Check the number and supporting document before deciding.';
  }
  if (/unavailable|could not reach|timed out/i.test(value)) {
    return 'The sample verification service could not respond. The reviewer can retry later; the vendor does not need to resubmit this information.';
  }
  return value;
};

const outcomeStyle = (outcome: ValidationRunHistoryItem['outcome']) => ({
  APPROVED: 'bg-[#e7f1e8] text-[#245b3b] border-[#c9dfce]',
  REJECTED: 'bg-[#f7e8e3] text-[#8b3f2e] border-[#e9c9bf]',
  PENDING: 'bg-[#f1f0e9] text-[#526358] border-[#d9d8ce]',
}[outcome]);

export const ProcessRunHistory: React.FC<Props> = ({ token, onOpenApplication }) => {
  const [runs, setRuns] = useState<ValidationRunHistoryItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedRun, setSelectedRun] = useState<ValidationRunHistoryItem | null>(null);
  const [runDetail, setRunDetail] = useState<ValidationRun | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [detailError, setDetailError] = useState<string | null>(null);

  const loadRuns = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setRuns(await apiFetchValidationRunHistory(token));
    } catch (err: any) {
      setError(err?.message || 'Recent checks could not be loaded.');
    } finally {
      setLoading(false);
    }
  }, [token]);

  useEffect(() => { loadRuns(); }, [loadRuns]);

  const openRun = async (item: ValidationRunHistoryItem) => {
    setSelectedRun(item);
    setRunDetail(null);
    setDetailError(null);
    setDetailLoading(true);
    try {
      setRunDetail(await apiFetchValidationRun(token, item.id));
    } catch (err: any) {
      setDetailError(err?.message || 'This run could not be opened.');
    } finally {
      setDetailLoading(false);
    }
  };

  const closeRun = () => { setSelectedRun(null); setRunDetail(null); setDetailError(null); };

  const summaryCounts = runs.reduce((counts, run) => {
    counts[run.outcome] += 1;
    return counts;
  }, { APPROVED: 0, REJECTED: 0, PENDING: 0 });

  return (
    <>
    <section className="overflow-hidden rounded-2xl border border-[#d9d8ce] bg-white shadow-sm">
      <div className="flex flex-col gap-5 border-b border-[#e8e6dc] bg-[#fcfbf7] px-6 py-5 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="mb-1 text-[11px] font-bold uppercase tracking-[0.17em] text-[#8b6840]">The audit trail</p>
          <h3 className="font-serif text-2xl tracking-tight text-[#1c3328]">Processing runs</h3>
          <p className="mt-1 text-sm text-[#68756c]">Every completed check, its outcome, and the reason behind it.</p>
        </div>
        <div className="flex flex-wrap items-center gap-2 text-xs">
          <span className="rounded-full border border-[#c9dfce] bg-[#e7f1e8] px-3 py-1.5 font-semibold text-[#245b3b]">{summaryCounts.APPROVED} ready</span>
          <span className="rounded-full border border-[#d9d8ce] bg-white px-3 py-1.5 font-semibold text-[#526358]">{summaryCounts.PENDING} pending review</span>
          <span className="rounded-full border border-[#e9c9bf] bg-[#f7e8e3] px-3 py-1.5 font-semibold text-[#8b3f2e]">{summaryCounts.REJECTED} rejected</span>
          <button onClick={loadRuns} disabled={loading} aria-label="Refresh processing runs" className="ml-1 inline-flex h-9 w-9 items-center justify-center rounded-lg border border-[#d9d8ce] bg-white text-[#526358] transition hover:bg-[#f2f1e9] disabled:opacity-50">
            <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      {error && <div role="alert" className="m-5 rounded-lg border border-[#e7c1b7] bg-[#fbefeb] px-4 py-3 text-sm text-[#873e2c]">{error}</div>}
      {loading && runs.length === 0 ? (
        <div className="flex items-center justify-center gap-2 px-6 py-16 text-sm text-[#68756c]"><LoaderCircle className="h-4 w-4 animate-spin" />Loading completed checks…</div>
      ) : runs.length === 0 ? (
        <div className="px-6 py-16 text-center">
          <ShieldCheck className="mx-auto mb-3 h-8 w-8 text-[#718878]" />
          <h4 className="font-semibold text-[#26382d]">No processing runs yet</h4>
          <p className="mt-1 text-sm text-[#68756c]">A run will appear here after a vendor submission is checked.</p>
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full min-w-[760px] text-left text-sm">
            <thead className="bg-[#f4f3ed] text-[10px] font-bold uppercase tracking-[0.13em] text-[#6d786e]">
              <tr><th className="px-6 py-3.5">Vendor and reference</th><th className="px-4 py-3.5">Current outcome</th><th className="px-4 py-3.5">Checks</th><th className="px-4 py-3.5">What happened</th><th className="px-6 py-3.5">Run time</th><th className="px-4 py-3.5" /></tr>
            </thead>
            <tbody className="divide-y divide-[#eeece4]">
              {runs.map((run) => {
                const findings = run.passed_count + run.failed_count + run.warning_count + run.unverified_count + run.unavailable_count;
                return <tr key={run.id} className="group align-top transition hover:bg-[#fbfaf6]">
                  <td className="px-6 py-4">
                    <div className="font-semibold text-[#26382d]">{run.vendor_name}</div>
                    <div className="mt-1 font-mono text-xs text-[#7b857b]">{run.application_reference}{run.is_current && <span className="ml-2 rounded bg-[#e7f1e8] px-1.5 py-0.5 font-sans text-[10px] font-semibold text-[#245b3b]">Latest</span>}</div>
                  </td>
                  <td className="px-4 py-4"><span className={`inline-flex rounded-full border px-2.5 py-1 text-xs font-semibold ${outcomeStyle(run.outcome)}`}>{run.outcome === 'APPROVED' ? <Check className="mr-1 h-3.5 w-3.5" /> : run.outcome === 'PENDING' ? <Clock3 className="mr-1 h-3.5 w-3.5" /> : null}{outcomeText(run.outcome)}</span></td>
                  <td className="px-4 py-4 text-xs text-[#526358]">{findings} checks <span className="text-[#a0a59b]">·</span> {run.passed_count} clear</td>
                  <td className="max-w-sm px-4 py-4 text-xs leading-5 text-[#53645a]">{plainReason(run.reason || run.summary || 'Checks completed.')}</td>
                  <td className="whitespace-nowrap px-6 py-4 text-xs text-[#748076]"><span className="inline-flex items-center gap-1.5"><Clock3 className="h-3.5 w-3.5" />{new Date(run.created_at).toLocaleString([], { dateStyle: 'medium', timeStyle: 'short' })}</span></td>
                  <td className="px-4 py-4"><button onClick={() => void openRun(run)} className="inline-flex h-9 items-center gap-1.5 rounded-lg border border-[#d9d8ce] bg-white px-3 text-xs font-semibold text-[#315844] transition hover:border-[#8fa995] hover:bg-[#f4f7f2]">Inspect run<ArrowUpRight className="h-3.5 w-3.5" /></button></td>
                </tr>;
              })}
            </tbody>
          </table>
        </div>
      )}
      <div className="flex flex-col gap-1.5 border-t border-[#e8e6dc] bg-[#fcfbf7] px-6 py-3 text-[11px] text-[#7b857b] sm:flex-row sm:items-center sm:justify-between"><span>Showing the latest {runs.length} real validation run{runs.length === 1 ? '' : 's'} for this organisation.</span><span className="font-medium text-[#5d6d61]">Demo environment: tax, bank and registry responses are simulated · Human review stays in control</span></div>
    </section>
    {selectedRun && (
      <div className="fixed inset-0 z-50 flex items-center justify-center bg-[#102319a8] p-3 sm:p-6" onMouseDown={(event) => { if (event.target === event.currentTarget) closeRun(); }}>
        <section role="dialog" aria-modal="true" aria-labelledby="run-detail-heading" className="flex max-h-[92vh] w-full max-w-4xl flex-col overflow-hidden rounded-2xl border border-[#d9d8ce] bg-[#fcfbf7] shadow-2xl">
          <header className="flex items-start justify-between gap-4 border-b border-[#e8e6dc] bg-white px-5 py-4 sm:px-7">
            <div>
              <p className="text-[10px] font-bold uppercase tracking-[0.17em] text-[#8b6840]">Saved process output · {selectedRun.application_reference}</p>
              <h2 id="run-detail-heading" className="mt-1 font-serif text-2xl text-[#1c3328]">{selectedRun.vendor_name}</h2>
              <p className="mt-1 text-xs text-[#748076]">{selectedRun.run_type.replace(/_/g, ' ').toLowerCase()} · {new Date(selectedRun.created_at).toLocaleString()}</p>
            </div>
            <button onClick={closeRun} aria-label="Close run details" className="inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-lg border border-[#deded5] bg-white text-[#526358] hover:bg-[#f2f1e9]"><X className="h-4 w-4" /></button>
          </header>
          <div className="overflow-y-auto px-5 py-5 sm:px-7">
            {detailLoading ? <div className="flex items-center justify-center gap-2 py-16 text-sm text-[#68756c]"><LoaderCircle className="h-4 w-4 animate-spin" />Opening the saved checks…</div>
              : detailError ? <div role="alert" className="rounded-lg border border-[#e7c1b7] bg-[#fbefeb] px-4 py-3 text-sm text-[#873e2c]">{detailError}</div>
              : runDetail && <>
                <div className="grid gap-3 sm:grid-cols-3">
                  <div className="rounded-xl border border-[#d9d8ce] bg-white p-4"><p className="text-[10px] font-bold uppercase tracking-wider text-[#7b857b]">Process outcome</p><p className="mt-1 text-sm font-semibold text-[#26382d]">{outcomeText(selectedRun.outcome)}</p></div>
                  <div className="rounded-xl border border-[#d9d8ce] bg-white p-4"><p className="text-[10px] font-bold uppercase tracking-wider text-[#7b857b]">Findings recorded</p><p className="mt-1 text-sm font-semibold text-[#26382d]">{runDetail.findings.length} total</p></div>
                  <div className="rounded-xl border border-[#d9d8ce] bg-white p-4"><p className="text-[10px] font-bold uppercase tracking-wider text-[#7b857b]">Current case status</p><p className="mt-1 text-sm font-semibold text-[#26382d]">{selectedRun.application_status.replace(/_/g, ' ')}</p></div>
                </div>
                <div className="mt-4 rounded-xl border border-[#d9d8ce] bg-white p-4 sm:p-5">
                  <h3 className="text-sm font-semibold text-[#26382d]">What the checks found</h3>
                  <p className="mt-1 text-xs leading-5 text-[#68756c]">{plainReason(selectedRun.reason || runDetail.summary || 'Checks completed.')}</p>
                  <p className="mt-1 text-[11px] text-[#7b857b]">{runDetail.findings.filter((finding) => finding.status === 'PASSED').length} passed · {runDetail.findings.filter((finding) => finding.status === 'NOT_APPLICABLE').length} not applicable · {runDetail.findings.length} findings recorded</p>
                  <div className="mt-4 divide-y divide-[#eeece4]">
                    {runDetail.findings.map((finding) => {
                      const clear = finding.status === 'PASSED' || finding.status === 'NOT_APPLICABLE';
                      const color = clear ? 'bg-[#e7f1e8] text-[#245b3b] border-[#c9dfce]' : finding.status === 'FAILED' ? 'bg-[#f7e8e3] text-[#8b3f2e] border-[#e9c9bf]' : 'bg-[#f8efd9] text-[#805a18] border-[#ead8a8]';
                      return <article key={finding.id} className="flex flex-col gap-2 py-3 sm:flex-row sm:items-start sm:justify-between">
                        <div className="min-w-0"><div className="flex flex-wrap items-center gap-2"><h4 className="text-xs font-semibold text-[#34483a]">{finding.check_name}</h4><span className="rounded border border-[#deded5] px-1.5 py-0.5 text-[9px] font-semibold uppercase tracking-wide text-[#7b857b]">{finding.layer.replace(/^LAYER_[A-D]_/, '')}</span></div><p className="mt-1 text-xs leading-5 text-[#68756c]">{finding.explanation.replace(/^\[SIMULATED\]\s*/i, '')}</p>{finding.recommended_action && <p className="mt-1 text-xs leading-5 text-[#526358]"><span className="font-semibold">Next step: </span>{finding.recommended_action}</p>}</div>
                        <span className={`inline-flex w-fit shrink-0 rounded-full border px-2.5 py-1 text-[10px] font-bold uppercase tracking-wide ${color}`}>{finding.status.replace(/_/g, ' ')}</span>
                      </article>;
                    })}
                  </div>
                </div>
                <div className="mt-3 rounded-lg border border-[#e3d2a7] bg-[#fbf5e5] px-4 py-3 text-xs leading-5 text-[#70591f]">Demo notice: external tax, bank, and registry results shown here use simulated records. A reviewer makes the final decision.</div>
              </>}
          </div>
          <footer className="flex flex-col gap-2 border-t border-[#e8e6dc] bg-white px-5 py-3 sm:flex-row sm:items-center sm:justify-between sm:px-7">
            <span className="text-[11px] text-[#7b857b]">Run history is read-only; this view does not change the vendor’s decision.</span>
            <div className="flex justify-end gap-2"><button onClick={closeRun} className="inline-flex h-9 items-center rounded-lg border border-[#deded5] px-3 text-xs font-semibold text-[#526358] hover:bg-[#f2f1e9]">Close</button><button onClick={() => { closeRun(); onOpenApplication(selectedRun.application_id); }} className="inline-flex h-9 items-center gap-1.5 rounded-lg bg-[#286344] px-3 text-xs font-semibold text-white hover:bg-[#204e36]">Open case<ArrowUpRight className="h-3.5 w-3.5" /></button></div>
          </footer>
        </section>
      </div>
    )}
    </>
  );
};
