import { AgencyTable } from "@/components/agencies/agency-table";

export default function AgenciesPage() {
  return (
    <div className="flex flex-col gap-8">
      <div>
        <p className="font-mono text-[11px] uppercase tracking-[0.2em] text-navy-light">
          Juris Collect · Agency Management
        </p>
        <h1 className="mt-1 font-serif text-3xl font-semibold text-ink-navy">
          Agency Oversight
        </h1>
        <p className="mt-2 max-w-2xl text-sm leading-relaxed text-navy-light">
          A bank&rsquo;s view across every collection agency it has
          appointed — the oversight layer Agency Management doesn&rsquo;t
          have yet.
        </p>
      </div>

      <AgencyTable />
    </div>
  );
}
