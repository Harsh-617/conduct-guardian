"use client";

import { useRef, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { Loader2, Mail, MessageCircle, MessageSquare, Phone, ShieldCheck } from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { Button } from "@/components/ui/button";
import { ErrorState } from "@/components/ui/data-state";
import { api, ApiError } from "@/lib/api/client";
import { formatTimestamp, ruleLabel } from "@/lib/api/adapters";
import { useApi } from "@/lib/api/use-api";
import type { AccountSummary, ApiChannel, ScreenResponse } from "@/lib/api/types";
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

/** Channel choices offered for custom/free-text submissions. */
const CHANNEL_OPTIONS: { value: ApiChannel; label: string; icon: LucideIcon }[] = [
  { value: "whatsapp", label: "WhatsApp", icon: MessageCircle },
  { value: "sms", label: "SMS", icon: MessageSquare },
  { value: "call", label: "Call", icon: Phone },
  { value: "email", label: "Email", icon: Mail },
];

const CHANNEL_LABEL: Record<ApiChannel, string> = {
  whatsapp: "WhatsApp",
  sms: "SMS",
  call: "Call",
  email: "Email",
};

// Chips are a convenience picker, not a directory — cap the row so it can't
// grow into a wall of buttons as the account list grows. Matches the cap
// used by the Case Timeline's account switcher.
const MAX_ACCOUNT_CHIPS = 12;

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

/**
 * Real /screen latency is 6-7s typical, up to 11-14s at p95 (see
 * docs/JUDGE-ONEPAGER.md) — a static spinner that long reads as "broken."
 * Staged messages tell the user the wait is expected and moving.
 */
const LOADING_STAGES = [
  "Checking against conduct rules…",
  "Cross-referencing Act 873 and BNM guidance…",
  "Almost there…",
] as const;
const LOADING_STAGE_DELAYS_MS = [3500, 8000];

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

function submissionFromText(text: string, accountId: string, apiChannel: ApiChannel): Submission {
  return {
    text,
    channelLabel: CHANNEL_LABEL[apiChannel],
    accountLabel: `Account #${accountId}`,
    apiChannel,
    accountId,
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

/** Account chip + free-text picker for custom submissions. Same visual pattern as the Case Timeline's account switcher. */
function AccountPicker({
  accounts,
  value,
  onChange,
  disabled,
}: {
  accounts: AccountSummary[];
  value: string;
  onChange: (id: string) => void;
  disabled: boolean;
}) {
  return (
    <div className={disabled ? "pointer-events-none opacity-50" : ""}>
      <label
        htmlFor="screen-account-id"
        className="font-mono text-[11px] uppercase tracking-[0.2em] text-navy-light"
      >
        Account
      </label>
      <input
        id="screen-account-id"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        disabled={disabled}
        placeholder="Select an account or type a new ID"
        className="mt-2 w-full max-w-xs rounded border border-hairline bg-paper px-4 py-2 font-mono text-sm text-ink-navy placeholder:text-navy-light/70 focus:border-brass-accent focus:outline-none"
      />
      {accounts.length > 0 && (
        <div className="mt-2 flex flex-wrap items-center gap-2">
          {accounts.slice(0, MAX_ACCOUNT_CHIPS).map((account) => {
            const active = account.external_id === value;
            return (
              <button
                key={account.id}
                type="button"
                onClick={() => onChange(account.external_id)}
                className={`rounded-full border px-3 py-1 font-mono text-xs transition-colors ${
                  active
                    ? "border-brass-accent bg-soft-brass text-brass-accent"
                    : "border-hairline bg-paper text-navy-light hover:border-brass-accent/50 hover:bg-soft-brass/40"
                }`}
              >
                #{account.external_id}
              </button>
            );
          })}
          {accounts.length > MAX_ACCOUNT_CHIPS && (
            <span className="font-mono text-xs text-navy-light">
              +{accounts.length - MAX_ACCOUNT_CHIPS} more — type the ID above
            </span>
          )}
        </div>
      )}
    </div>
  );
}

/** Channel button group for custom submissions. Same rounded-pill styling as ChannelBadge. */
function ChannelPicker({
  value,
  onChange,
  disabled,
}: {
  value: ApiChannel;
  onChange: (channel: ApiChannel) => void;
  disabled: boolean;
}) {
  return (
    <div className={disabled ? "pointer-events-none opacity-50" : ""}>
      <p className="font-mono text-[11px] uppercase tracking-[0.2em] text-navy-light">
        Channel
      </p>
      <div className="mt-2 flex flex-wrap items-center gap-2">
        {CHANNEL_OPTIONS.map(({ value: optionValue, label, icon: Icon }) => {
          const active = optionValue === value;
          return (
            <button
              key={optionValue}
              type="button"
              onClick={() => onChange(optionValue)}
              disabled={disabled}
              className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 font-mono text-[11px] uppercase tracking-wide transition-colors ${
                active
                  ? "border-brass-accent bg-soft-brass text-brass-accent"
                  : "border-hairline bg-paper text-navy-light hover:border-brass-accent/50 hover:bg-soft-brass/40"
              }`}
            >
              <Icon className="h-3 w-3" />
              {label}
            </button>
          );
        })}
      </div>
    </div>
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
  const [loadingStage, setLoadingStage] = useState(0);
  const [customAccountId, setCustomAccountId] = useState("");
  const [customChannel, setCustomChannel] = useState<ApiChannel>("whatsapp");

  const { data: accountsData } = useApi(() => api.accounts(), []);

  // Guards against a slow, superseded request clobbering the result of a
  // faster one that was started after it.
  const requestSeq = useRef(0);
  const loadingTimers = useRef<ReturnType<typeof setTimeout>[]>([]);

  function clearLoadingTimers() {
    loadingTimers.current.forEach(clearTimeout);
    loadingTimers.current = [];
  }

  async function runScreen(submission: Submission) {
    const seq = ++requestSeq.current;
    clearLoadingTimers();
    setStatus("loading");
    setLoadingStage(0);
    setApiError(null);
    setLastSubmission(submission);

    LOADING_STAGE_DELAYS_MS.forEach((delay, i) => {
      loadingTimers.current.push(
        setTimeout(() => {
          if (seq === requestSeq.current) setLoadingStage(i + 1);
        }, delay),
      );
    });

    try {
      const response = await api.screen({
        text: submission.text,
        channel: submission.apiChannel,
        account_id: submission.accountId,
      });
      if (seq !== requestSeq.current) return;
      clearLoadingTimers();

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
      clearLoadingTimers();
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
    if (selectedSample) {
      void runScreen(submissionFromSample(selectedSample));
      return;
    }
    const accountId = customAccountId.trim();
    if (!accountId) return;
    void runScreen(submissionFromText(text.trim(), accountId, customChannel));
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

          <div className="mt-4 flex flex-wrap gap-6">
            <AccountPicker
              accounts={accountsData?.accounts ?? []}
              value={customAccountId}
              onChange={setCustomAccountId}
              disabled={selectedId !== null}
            />
            <ChannelPicker
              value={customChannel}
              onChange={setCustomChannel}
              disabled={selectedId !== null}
            />
          </div>
          {selectedId && (
            <p className="mt-2 font-mono text-xs text-navy-light">
              Using the sample&apos;s own account and channel — clear the text to pick your own.
            </p>
          )}

          <div className="mt-4 flex flex-wrap items-center gap-4">
            <Button
              type="button"
              onClick={handleRun}
              disabled={
                !text.trim() || status === "loading" || (!selectedId && !customAccountId.trim())
              }
              className="gap-2"
            >
              <ShieldCheck className="h-4 w-4" />
              Run compliance review
            </Button>

            {status === "loading" && (
              <span className="flex items-center gap-2 font-mono text-xs uppercase tracking-wide text-navy-light">
                <Loader2 className="h-3.5 w-3.5 animate-spin" />
                <AnimatePresence mode="wait">
                  <motion.span
                    key={loadingStage}
                    initial={{ opacity: 0, y: 4 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: -4 }}
                    transition={{ duration: 0.25 }}
                  >
                    {LOADING_STAGES[loadingStage]}
                  </motion.span>
                </AnimatePresence>
              </span>
            )}
          </div>

          {!selectedId && text.trim() && !customAccountId.trim() && (
            <p className="mt-2 font-mono text-xs text-stamp-red">
              Select or enter an account before running a custom message.
            </p>
          )}

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
