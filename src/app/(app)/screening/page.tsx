import { ScreeningTool } from "@/components/screening/screening-tool";

export default function ScreeningPage() {
  return (
    <div className="flex flex-col gap-8">
      <div>
        <p className="font-mono text-[11px] uppercase tracking-[0.2em] text-navy-light">
          Conduct Compliance
        </p>
        <h1 className="mt-1 font-serif text-3xl font-semibold text-ink-navy">
          Live Screening
        </h1>
        <p className="mt-2 max-w-2xl text-sm leading-relaxed text-navy-light">
          Screen a call transcript, SMS, or WhatsApp message against conduct
          rules. Load a sample scenario or paste your own message, then run
          a review.
        </p>
      </div>

      <ScreeningTool />
    </div>
  );
}
