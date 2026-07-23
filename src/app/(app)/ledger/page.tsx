import { LedgerTable } from "@/components/ledger/ledger-table";

export default function LedgerPage() {
  return (
    <div className="flex flex-col gap-8">
      <div>
        <p className="font-mono text-[11px] uppercase tracking-[0.2em] text-navy-light">
          Audit Trail
        </p>
        <h1 className="mt-1 font-serif text-3xl font-semibold text-ink-navy">
          Evidence Ledger
        </h1>
        <p className="mt-2 max-w-2xl text-sm leading-relaxed text-navy-light">
          Every reviewed message, chained so nothing can be quietly altered
          after the fact.
        </p>
      </div>

      <LedgerTable />
    </div>
  );
}
