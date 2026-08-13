"use client";

import { useRef, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { Loader2, ShieldCheck } from "lucide-react";
import { Button } from "@/components/ui/button";
import { ErrorState } from "@/components/ui/data-state";
import { api, ApiError } from "@/lib/api/client";
import { formatTimestamp, ruleLabel } from "@/lib/api/adapters";
import type { ApiChannel, ScreenResponse } from "@/lib/api/types";
import { SamplePanel } from "./sample-panel";
import { VerdictStamp } from "./verdict-stamp";
import { EvidenceLog } from "./evidence-log";
import { samples } from "./data";
import type { Channel, Highlight, LogEntry, SampleMessage, Verdict } from "./data";

type Status = "idle" | "loading" | "done" | "error";

/** UI channel labels -> the lowercase wire values the API expects. */
const API_CHANNEL: Record<Channel, ApiChannel> = {
  Call: "call",
  WhatsApp: "whatsapp",
  SMS: "sms",
};

/**
 * What gets sent to /screen plus what the results panel needs to render
 * itself back — kept together so the panel never has to re-derive request
 * state from whatever is currently sitting in the textarea.
 */
type Submission = {
  text: string;
  channelLabel: string;
  accountLabel: string | null;
  apiChannel: ApiChannel | undefined;
  accountId: string | undefined;
};

type Reviewed = {
  submission: Submission;
  response: ScreenResponse;
};

function submissionFromSample(sample: SampleMessage): Submission {
  return {
    text: sample.text,
    channelLabel: sample.channel,
    accountLabel: sample.account,
    apiChannel: API_CHANNEL[sample.channel],
    // Samples display "Account #4521" — the backend wants the bare
    // external_id ("4521") and auto-creates the account if it's unseen.
    accountId: sample.account.match(/(\d+)/)?.[1],
  };
}

function submissionFromText(text: string): Submission {
  return {
    text,
    channelLabel: "Custom Input",
    accountLabel: null,
    // Left undefined rather than guessed: JSON.stringify drops undefined
    // keys, so the backend applies its own default (whatsapp / "4471")
    // instead of us fabricating a channel/account nobody chose.
    apiChannel: undefined,
    accountId: undefined,
  };
}

/** Verbatim per the API contract — locate it in the submitted text, or don't highlight. */
function buildHighlight(text: string, quotedPhrase: string | null): Highlight | null {
  if (!quotedPhrase) return null;
  const idx = text.indexOf(quotedPhrase);
  if (idx === -1) return null;
  return {
    before: text.slice(0, idx),
    match: quotedPhrase,
    after: text.slice(idx + quotedPhrase.length),
  };
}

function buildSnippet(text: string, quotedPhrase: string | null): string {
  const source = quotedPhrase && text.includes(quotedPhrase) ? quotedPhrase : text;
  const collapsed = source.replace(/\s+/g, " ").trim();
  return collapsed.length > 70 ? `${collapsed.slice(0, 70)}…` : collapsed;
}

function TranscriptText({ text, highlight }: { text: string; highlight: Highlight | null }) {
  if (!highlight) {
    return <>{text}</>;
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
  const [reviewed, setReviewed] = useState<Reviewed | null>(null);
  const [apiError, setApiError] = useState<ApiError | null>(null);
  const [lastSubmission, setLastSubmission] = useState<Submission | null>(null);
  const [entries, setEntries] = useState<LogEntry[]>([]);

  // Guards against a slow, superseded request clobbering the result of a
  // faster one that was started after it.
  const requestSeq = useRef(0);

  async function runScreen(submission: Submission) {
    const seq = ++requestSeq.current;
    setStatus("loading");
    setApiError(null);
    setLastSubmission(submission);

    try {
      const response = await api.screen({
        text: submission.text,
        channel: submission.apiChannel,
        account_id: submission.accountId,
      });
      if (seq !== requestSeq.current) return;

      setReviewed({ submission, response });
      setStatus("done");
      setEntries((prev) => [
        {
          id: `${response.screening_result_id}-${response.message_id}`,
          timestamp: formatTimestamp(new Date().toISOString()),
          snippet: buildSnippet(submission.text, response.verdict.quoted_phrase),
          verdict: response.verdict.violation ? "FLAGGED" : "CLEAR",
          rule: ruleLabel(response.verdict.rule),
        },
        ...prev,
      ]);
    } catch (err) {
      if (seq !== requestSeq.current) return;
      setApiError(
        err instanceof ApiError ? err : new ApiError("Something went wrong.", "unknown", true, 0),
      );
      setStatus("error");
    }
  }

  function handleSelectSample(sample: SampleMessage) {
    if (status === "loading") return;
    setSelectedId(sample.id);
    setText(sample.text);
    setReviewed(null);
    setApiError(null);
    // Presets are a convenience for filling the box — selecting one runs the
    // exact same real screen as typing the text in and pressing the button.
    void runScreen(submissionFromSample(sample));
  }

  function handleTextChange(value: string) {
    setText(value);
    setSelectedId(null);
    setStatus("idle");
    setReviewed(null);
    setApiError(null);
  }

  function handleRun() {
    if (!text.trim() || status === "loading") return;
    const selectedSample = selectedId ? samples.find((s) => s.id === selectedId) : null;
    void runScreen(selectedSample ? submissionFromSample(selectedSample) : submissionFromText(text.trim()));
  }

  function handleRetry() {
    if (lastSubmission) void runScreen(lastSubmission);
  }

  const viewModel = reviewed
    ? {
        verdict: (reviewed.response.verdict.violation ? "FLAGGED" : "CLEAR") as Verdict,
        rule: ruleLabel(reviewed.response.verdict.rule),
        highlight: buildHighlight(reviewed.submission.text, reviewed.response.verdict.quoted_phrase),
      }
    : null;

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
            {status === "error" && apiError && (
              <motion.div
                key="error"
                initial={{ opacity: 0, y: 12 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.35 }}
                className="mt-6 border-t border-hairline pt-6"
              >
                <ErrorState
                  message={apiError.message}
                  retryable={apiError.retryable}
                  onRetry={handleRetry}
                  waking={apiError.code === "network_error"}
                />
              </motion.div>
            )}

            {status === "done" && reviewed && viewModel && (
              <motion.div
                key={reviewed.response.screening_result_id}
                initial={{ opacity: 0, y: 12 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.35 }}
                className="mt-6 flex flex-col gap-5 border-t border-hairline pt-6"
              >
                <div className="flex flex-wrap items-center gap-4">
                  <VerdictStamp verdict={viewModel.verdict} />
                  <div className="font-mono text-xs text-navy-light">
                    <p>
                      {reviewed.submission.channelLabel}
                      {reviewed.submission.accountLabel ? ` · ${reviewed.submission.accountLabel}` : ""}
                    </p>
                    <p>Reviewed at {formatTimestamp(new Date().toISOString())}</p>
                    <p>
                      {reviewed.response.model} · {reviewed.response.latency_ms}ms
                    </p>
                  </div>
                </div>

                <div className="rounded border border-hairline bg-paper px-4 py-4">
                  <p className="font-mono text-[10px] uppercase tracking-wide text-navy-light">
                    Transcript
                  </p>
                  <p className="mt-2 whitespace-pre-line text-sm leading-relaxed text-ink-navy">
                    <TranscriptText text={reviewed.submission.text} highlight={viewModel.highlight} />
                  </p>
                </div>

                {viewModel.verdict === "FLAGGED" ? (
                  <>
                    {viewModel.rule && (
                      <div>
                        <span className="inline-flex items-center rounded-full bg-soft-brass px-3 py-1 font-mono text-[10px] uppercase tracking-wide text-brass-accent">
                          Rule Broken: {viewModel.rule}
                        </span>
                      </div>
                    )}

                    <div className="rounded border border-hairline bg-paper px-4 py-4">
                      <p className="font-mono text-[10px] uppercase tracking-wide text-navy-light">
                        Explanation
                      </p>
                      <p className="mt-2 text-sm leading-relaxed text-ink-navy">
                        {reviewed.response.verdict.explanation}
                      </p>
                    </div>

                    {reviewed.response.verdict.suggested_rewrite && (
                      <div className="rounded border border-stamp-green/25 bg-soft-green px-4 py-4">
                        <p className="font-mono text-[10px] uppercase tracking-wide text-stamp-green">
                          Suggested Compliant Rewrite
                        </p>
                        <p className="mt-2 text-sm leading-relaxed text-ink-navy">
                          {reviewed.response.verdict.suggested_rewrite}
                        </p>
                      </div>
                    )}
                  </>
                ) : (
                  <div className="rounded border border-stamp-green/25 bg-soft-green px-4 py-4">
                    <p className="text-sm leading-relaxed text-ink-navy">
                      {reviewed.response.verdict.explanation}
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
