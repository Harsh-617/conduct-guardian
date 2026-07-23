"use client";

import { useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { Loader2, ShieldCheck } from "lucide-react";
import { Button } from "@/components/ui/button";
import { SamplePanel } from "./sample-panel";
import { VerdictStamp } from "./verdict-stamp";
import { EvidenceLog } from "./evidence-log";
import { samples } from "./data";
import type { LogEntry, SampleMessage } from "./data";

type Status = "idle" | "loading" | "done";

function formatTimestamp() {
  return new Date().toLocaleTimeString("en-US", {
    hour: "numeric",
    minute: "2-digit",
    second: "2-digit",
  });
}

function TranscriptText({ sample }: { sample: SampleMessage }) {
  const highlight = sample.result.highlight;
  if (!highlight) {
    return <>{sample.text}</>;
  }
  return (
    <>
      {highlight.before}
      <mark className="rounded bg-soft-red px-1 font-medium not-italic text-stamp-red">
        {highlight.match}
      </mark>
      {highlight.after}
    </>
  );
}

export function ScreeningTool() {
  const [text, setText] = useState("");
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [status, setStatus] = useState<Status>("idle");
  const [reviewed, setReviewed] = useState<SampleMessage | null>(null);
  const [entries, setEntries] = useState<LogEntry[]>([]);

  function handleSelectSample(sample: SampleMessage) {
    setSelectedId(sample.id);
    setText(sample.text);
    setStatus("idle");
    setReviewed(null);
  }

  function handleTextChange(value: string) {
    setText(value);
    setSelectedId(null);
    setStatus("idle");
    setReviewed(null);
  }

  function handleRun() {
    if (!text.trim() || status === "loading") return;

    setStatus("loading");
    setReviewed(null);

    window.setTimeout(() => {
      const selectedSample = selectedId
        ? samples.find((sample) => sample.id === selectedId)
        : null;
      const outcome =
        selectedSample ??
        samples[Math.floor(Math.random() * samples.length)];

      setReviewed(outcome);
      setStatus("done");

      const snippet =
        outcome.result.highlight?.match ??
        (outcome.text.length > 70
          ? `${outcome.text.slice(0, 70)}…`
          : outcome.text);

      setEntries((prev) => [
        {
          id: `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
          timestamp: formatTimestamp(),
          snippet: snippet.replace(/\s+/g, " ").trim(),
          verdict: outcome.result.verdict,
          rule: outcome.result.rule,
        },
        ...prev,
      ]);
    }, 1500);
  }

  return (
    <div className="flex flex-col gap-6">
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-[280px_1fr]">
        <SamplePanel selectedId={selectedId} onSelect={handleSelectSample} />

        <div className="rounded border border-hairline bg-card-white px-6 py-5">
          <p className="font-mono text-[11px] uppercase tracking-[0.15em] text-navy-light">
            {selectedId
              ? samples.find((s) => s.id === selectedId)?.channel
              : "Custom Input"}
          </p>
          <h2 className="mt-1 font-serif text-xl font-semibold text-ink-navy">
            Message Preview
          </h2>

          <textarea
            value={text}
            onChange={(e) => handleTextChange(e.target.value)}
            placeholder="Select a sample message on the left, or paste / write a message here to screen it…"
            rows={6}
            className="mt-4 w-full resize-none rounded border border-hairline bg-paper px-4 py-3 font-mono text-sm leading-relaxed text-ink-navy placeholder:text-navy-light/70 focus:border-brass-accent focus:outline-none"
          />

          <div className="mt-4 flex flex-wrap items-center gap-4">
            <Button
              type="button"
              onClick={handleRun}
              disabled={!text.trim() || status === "loading"}
              className="gap-2"
            >
              <ShieldCheck className="h-4 w-4" />
              Run compliance review
            </Button>

            {status === "loading" && (
              <span className="flex items-center gap-2 font-mono text-xs uppercase tracking-wide text-navy-light">
                <Loader2 className="h-3.5 w-3.5 animate-spin" />
                Checking against conduct rules…
              </span>
            )}
          </div>

          <AnimatePresence mode="wait">
            {status === "done" && reviewed && (
              <motion.div
                key={reviewed.id + entries.length}
                initial={{ opacity: 0, y: 12 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.35 }}
                className="mt-6 flex flex-col gap-5 border-t border-hairline pt-6"
              >
                <div className="flex flex-wrap items-center gap-4">
                  <VerdictStamp verdict={reviewed.result.verdict} />
                  <div className="font-mono text-xs text-navy-light">
                    <p>
                      {reviewed.channel} · {reviewed.account}
                    </p>
                    <p>Reviewed at {formatTimestamp()}</p>
                  </div>
                </div>

                <div className="rounded border border-hairline bg-paper px-4 py-4">
                  <p className="font-mono text-[10px] uppercase tracking-wide text-navy-light">
                    Transcript
                  </p>
                  <p className="mt-2 whitespace-pre-line text-sm leading-relaxed text-ink-navy">
                    <TranscriptText sample={reviewed} />
                  </p>
                </div>

                {reviewed.result.verdict === "FLAGGED" ? (
                  <>
                    <div>
                      <span className="inline-flex items-center rounded-full bg-soft-brass px-3 py-1 font-mono text-[10px] uppercase tracking-wide text-brass-accent">
                        Rule Broken: {reviewed.result.rule}
                      </span>
                    </div>

                    <div className="rounded border border-stamp-green/25 bg-soft-green px-4 py-4">
                      <p className="font-mono text-[10px] uppercase tracking-wide text-stamp-green">
                        Suggested Compliant Rewrite
                      </p>
                      <p className="mt-2 text-sm leading-relaxed text-ink-navy">
                        {reviewed.result.rewrite}
                      </p>
                    </div>
                  </>
                ) : (
                  <div className="rounded border border-stamp-green/25 bg-soft-green px-4 py-4">
                    <p className="text-sm leading-relaxed text-ink-navy">
                      No violations detected — this message meets conduct
                      standards.
                    </p>
                  </div>
                )}
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </div>

      <EvidenceLog entries={entries} />
    </div>
  );
}
