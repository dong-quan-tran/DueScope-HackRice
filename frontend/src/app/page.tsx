"use client";

import { useEffect, useMemo, useState } from "react";
import {
  AlertTriangle,
  CalendarCheck2,
  CalendarDays,
  Check,
  ChevronRight,
  Clock3,
  FileText,
  Loader2,
  RefreshCw,
  ShieldCheck,
  Sparkles,
  Unplug,
  X,
} from "lucide-react";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8001";

type Course = {
  id: string;
  code: string;
  name: string;
  color: string;
};

type EventVersion = {
  due_at: string | null;
  source_id: string;
  reason: string;
  is_current: boolean;
};

type AcademicEvent = {
  id: string;
  course_id: string;
  type: string;
  title: string;
  starts_at: string | null;
  due_at: string | null;
  location?: string | null;
  status: "verified" | "updated" | "needs_review" | "canceled";
  approved: boolean;
  workload_minutes: number;
  source_id: string;
  source_excerpt: string;
  needs_review_reason?: string | null;
  history: EventVersion[];
};

type Change = {
  event_id: string;
  kind: string;
  message: string;
};

type WorkloadDay = {
  date: string;
  minutes: number;
  level: string;
  reason: string;
};

type DeadlineProposal = {
  id: string;
  event_id: string;
  candidate: {
    course_id: string;
    type: string;
    title: string;
    starts_at: string | null;
    due_at: string | null;
    source_id: string;
    source_excerpt: string;
    change_type: string;
    confidence: string;
    needs_review_reason?: string | null;
  };
  message: string;
  created_at: string;
  resolved: boolean;
  resolution?: "accepted" | "rejected" | null;
};

type Workspace = {
  courses: Course[];
  events: AcademicEvent[];
  changes: Change[];
  workload: WorkloadDay[];
  proposals?: DeadlineProposal[];
};

type ExtractionResult = {
  extraction: {
    provider?: string;
    used_demo_fallback?: boolean;
  };
  results: Array<{
    title: string;
    action: string;
    message: string;
    event_id: string;
    proposal_id?: string | null;
  }>;
};

type CanvasCourse = {
  id: number;
  course_code: string;
  name: string;
};

type GoogleAuthStatus = {
  connected: boolean;
};

type GoogleSyncItem = {
  event_id: string;
  title: string;
  google_event_id?: string;
  calendar_url?: string;
  reason?: string;
};

type GoogleSyncResult = {
  created: GoogleSyncItem[];
  updated: GoogleSyncItem[];
  skipped: GoogleSyncItem[];
  failed: GoogleSyncItem[];
};

const seedAnnouncement = `Programming Assignment 2 has been extended.
It is now due Monday, September 21, 2026 at 11:59 PM in Canvas.`;

function formatDate(value: string | null | undefined) {
  if (!value) return "Needs review";

  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    return "Needs review";
  }

  return new Intl.DateTimeFormat("en-US", {
    weekday: "short",
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  }).format(date);
}

function statusStyle(status: AcademicEvent["status"]) {
  if (status === "updated") {
    return "border-amber-200 bg-amber-100 text-amber-800";
  }

  if (status === "needs_review") {
    return "border-rose-200 bg-rose-100 text-rose-800";
  }

  if (status === "verified") {
    return "border-emerald-200 bg-emerald-100 text-emerald-800";
  }

  return "border-slate-200 bg-slate-100 text-slate-700";
}

function actionLabel(action: string) {
  return action.replaceAll("_", " ");
}

function syncItemSummary(items: GoogleSyncItem[]) {
  return items.map((item) => item.title).join(", ");
}

export default function Home() {
  const [workspace, setWorkspace] = useState<Workspace | null>(null);
  const [selectedEvent, setSelectedEvent] = useState<AcademicEvent | null>(null);
  const [sourceText, setSourceText] = useState(seedAnnouncement);
  const [sourceTitle, setSourceTitle] = useState(
    "Programming Assignment 2 extension",
  );
  const [courseId, setCourseId] = useState("cse-3310");
  const [sourceType, setSourceType] = useState("instructor_announcement");
  const [loading, setLoading] = useState(true);
  const [scanning, setScanning] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [notice, setNotice] = useState("");
  const [canvasCourses, setCanvasCourses] = useState<CanvasCourse[]>([]);
  const [canvasCourseId, setCanvasCourseId] = useState("");
  const [canvasLoading, setCanvasLoading] = useState(false);
  const [canvasImporting, setCanvasImporting] = useState(false);
  const [resolvingProposalId, setResolvingProposalId] = useState("");
  const [googleConnected, setGoogleConnected] = useState(false);
  const [googleStatusLoading, setGoogleStatusLoading] = useState(true);
  const [syncingGoogle, setSyncingGoogle] = useState(false);
  const [syncResult, setSyncResult] = useState<GoogleSyncResult | null>(null);

  const coursesById = useMemo(
    () =>
      Object.fromEntries(
        (workspace?.courses ?? []).map((course) => [course.id, course]),
      ),
    [workspace],
  );

  const approvedSyncableEvents = useMemo(
    () =>
      (workspace?.events ?? []).filter(
        (event) =>
          event.approved && ["verified", "updated"].includes(event.status),
      ),
    [workspace],
  );

  async function loadWorkspace(showLoading = true) {
    if (showLoading) {
      setLoading(true);
    }

    try {
      const response = await fetch(`${API_URL}/api/demo/workspace`, {
        cache: "no-store",
      });

      if (!response.ok) {
        throw new Error("Could not load DueScope workspace.");
      }

      const data = (await response.json()) as Workspace;
      setWorkspace(data);

      setSelectedEvent((current) => {
        if (!current) return null;

        return data.events.find((event) => event.id === current.id) ?? null;
      });
    } catch (error) {
      setNotice(
        error instanceof Error ? error.message : "Could not reach the backend.",
      );
    } finally {
      if (showLoading) {
        setLoading(false);
      }
    }
  }

  async function loadGoogleStatus(showError = false) {
    setGoogleStatusLoading(true);

    try {
      const response = await fetch(`${API_URL}/api/google/auth/status`, {
        cache: "no-store",
      });

      if (!response.ok) {
        throw new Error("Could not check Google Calendar connection.");
      }

      const data = (await response.json()) as GoogleAuthStatus;
      setGoogleConnected(data.connected);
    } catch (error) {
      setGoogleConnected(false);

      if (showError) {
        setNotice(
          error instanceof Error
            ? error.message
            : "Could not check Google Calendar connection.",
        );
      }
    } finally {
      setGoogleStatusLoading(false);
    }
  }

  useEffect(() => {
    void loadWorkspace();
    void loadGoogleStatus();
  }, []);

  async function loadCanvasCourses() {
    setCanvasLoading(true);
    setNotice("");

    try {
      const response = await fetch(`${API_URL}/api/canvas/courses`);
      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail ?? "Could not load Canvas courses.");
      }

      const courses = data as CanvasCourse[];
      setCanvasCourses(courses);

      if (courses.length > 0) {
        setCanvasCourseId(String(courses[0].id));
        setNotice(
          `Loaded ${courses.length} Canvas course(s). Select one to import official due dates.`,
        );
      } else {
        setNotice("No active Canvas courses were returned for this account.");
      }
    } catch (error) {
      setNotice(
        error instanceof Error
          ? error.message
          : "Could not load Canvas courses.",
      );
    } finally {
      setCanvasLoading(false);
    }
  }

  async function importCanvasCourse() {
    if (!canvasCourseId) {
      setNotice("Load and select a Canvas course first.");
      return;
    }

    setCanvasImporting(true);
    setNotice("");

    try {
      const response = await fetch(
        `${API_URL}/api/canvas/import-course/${canvasCourseId}`,
        { method: "POST" },
      );
      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail ?? "Could not import Canvas deadlines.");
      }

      const proposalCount = Array.isArray(data.items)
        ? data.items.filter(
            (item: { proposal_id?: string | null }) => item.proposal_id,
          ).length
        : 0;

      setNotice(
        `Processed ${data.imported_count} upcoming Canvas deadline(s). ` +
          `${data.skipped_past_count} past deadline(s) skipped.` +
          (proposalCount
            ? ` ${proposalCount} change proposal(s) need review.`
            : ""),
      );

      await loadWorkspace(false);
    } catch (error) {
      setNotice(
        error instanceof Error
          ? error.message
          : "Could not import Canvas deadlines.",
      );
    } finally {
      setCanvasImporting(false);
    }
  }

  async function scanSource() {
    if (!sourceText.trim()) {
      setNotice("Paste a course update before scanning.");
      return;
    }

    setScanning(true);
    setNotice("");

    try {
      const response = await fetch(
        `${API_URL}/api/sources/extract-and-reconcile`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            course_id: courseId,
            source_type: sourceType,
            source_title: sourceTitle.trim() || "Untitled course update",
            source_received_at: new Date().toISOString(),
            timezone: "America/Chicago",
            source_text: sourceText,
          }),
        },
      );

      const data = (await response.json()) as ExtractionResult | { detail?: string };

      if (!response.ok) {
        throw new Error("detail" in data ? data.detail : "Deadline scan failed.");
      }

      const result = data as ExtractionResult;
      const provider = result.extraction.provider
        ? ` via ${result.extraction.provider}`
        : "";

      setNotice(
        result.results.length > 0
          ? `${result.results
              .map((item) => `${item.title}: ${actionLabel(item.action)}`)
              .join(" - ")}${provider}`
          : `No deadlines found in this source${provider}.`,
      );

      await loadWorkspace(false);
    } catch (error) {
      setNotice(
        error instanceof Error ? error.message : "Deadline scan failed.",
      );
    } finally {
      setScanning(false);
    }
  }

  async function resolveProposal(
    proposal: DeadlineProposal,
    action: "accept" | "reject",
  ) {
    setResolvingProposalId(proposal.id);
    setNotice("");

    try {
      const response = await fetch(
        `${API_URL}/api/events/proposals/${proposal.id}/${action}`,
        { method: "POST" },
      );
      const data = await response.json();

      if (!response.ok) {
        throw new Error(
          data.detail ??
            `Could not ${action === "accept" ? "accept" : "reject"} proposal.`,
        );
      }

      if (action === "accept") {
        setNotice(
          `${proposal.candidate.title} updated to ${formatDate(
            proposal.candidate.due_at,
          )}. Calendar approval was reset because the deadline changed.`,
        );
      } else {
        setNotice(
          `Kept the saved deadline for ${proposal.candidate.title}.`,
        );
      }

      await loadWorkspace(false);
    } catch (error) {
      setNotice(
        error instanceof Error
          ? error.message
          : `Could not ${action} proposal.`,
      );
    } finally {
      setResolvingProposalId("");
    }
  }

  async function toggleApproval(event: AcademicEvent) {
    try {
      const response = await fetch(`${API_URL}/api/events/${event.id}/approval`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ approved: !event.approved }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail ?? "Could not update approval.");
      }

      await loadWorkspace(false);

      setNotice(
        `${event.title} ${
          event.approved ? "removed from" : "approved for"
        } calendar export and Google Calendar sync.`,
      );
    } catch (error) {
      setNotice(
        error instanceof Error ? error.message : "Could not update approval.",
      );
    }
  }

  async function exportCalendar() {
    const eventIds = approvedSyncableEvents.map((event) => event.id);

    if (eventIds.length === 0) {
      setNotice(
        "Approve at least one verified or updated deadline before exporting.",
      );
      return;
    }

    setExporting(true);
    setNotice("");

    try {
      const response = await fetch(`${API_URL}/api/calendar/export`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ event_ids: eventIds }),
      });

      if (!response.ok) {
        const data = await response.json();
        throw new Error(data.detail ?? "Calendar export failed.");
      }

      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement("a");

      anchor.href = url;
      anchor.download = "duescope-calendar.ics";
      document.body.appendChild(anchor);
      anchor.click();
      anchor.remove();
      URL.revokeObjectURL(url);

      setNotice(
        `Exported ${eventIds.length} approved deadline(s) to an ICS calendar file.`,
      );
    } catch (error) {
      setNotice(
        error instanceof Error ? error.message : "Calendar export failed.",
      );
    } finally {
      setExporting(false);
    }
  }

  function connectGoogleCalendar() {
    window.location.assign(`${API_URL}/api/google/auth/start`);
  }

  async function syncApprovedToGoogle() {
    if (!googleConnected) {
      setNotice("Connect Google Calendar before syncing deadlines.");
      return;
    }

    if (approvedSyncableEvents.length === 0) {
      setNotice(
        "Approve at least one verified or updated deadline before syncing to Google Calendar.",
      );
      return;
    }

    setSyncingGoogle(true);
    setNotice("");
    setSyncResult(null);

    try {
      const response = await fetch(
        `${API_URL}/api/google/calendar/sync-approved`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            event_ids: approvedSyncableEvents.map((event) => event.id),
          }),
        },
      );

      const data = (await response.json()) as GoogleSyncResult | { detail?: string };

      if (!response.ok) {
        throw new Error(
          "detail" in data ? data.detail : "Google Calendar sync failed.",
        );
      }

      const result = data as GoogleSyncResult;
      setSyncResult(result);

      const resultMessage = [
        result.created.length ? `${result.created.length} created` : "",
        result.updated.length ? `${result.updated.length} updated` : "",
        result.skipped.length ? `${result.skipped.length} skipped` : "",
        result.failed.length ? `${result.failed.length} failed` : "",
      ]
        .filter(Boolean)
        .join(", ");

      setNotice(
        resultMessage
          ? `Google Calendar sync complete: ${resultMessage}.`
          : "Google Calendar sync finished with no eligible events.",
      );
    } catch (error) {
      setNotice(
        error instanceof Error ? error.message : "Google Calendar sync failed.",
      );
    } finally {
      setSyncingGoogle(false);
    }
  }

  if (loading) {
    return (
      <main className="grid min-h-screen place-items-center bg-slate-950 text-white">
        <div className="flex items-center gap-3 text-lg">
          <Loader2 className="animate-spin" />
          Loading DueScope...
        </div>
      </main>
    );
  }

  const events = workspace?.events ?? [];
  const proposals = (workspace?.proposals ?? []).filter(
    (proposal) => !proposal.resolved,
  );
  const highWorkload = workspace?.workload.find((day) => day.level === "high");

  return (
    <main className="min-h-screen bg-slate-950 text-slate-100">
      <div className="mx-auto max-w-7xl px-5 py-8 sm:px-8">
        <header className="mb-8 flex flex-col gap-5 border-b border-slate-800 pb-7 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <div className="mb-3 flex items-center gap-2 text-sm font-semibold uppercase tracking-[0.22em] text-cyan-300">
              <Sparkles size={16} />
              HackRice 16 - Work &amp; Productivity
            </div>

            <h1 className="text-4xl font-black tracking-tight sm:text-5xl">
              DueScope
            </h1>

            <p className="mt-3 max-w-2xl text-slate-400">
              A source-backed academic calendar that detects deadline changes
              before they become missed work.
            </p>
          </div>

          <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
            <button
              onClick={() => void syncApprovedToGoogle()}
              disabled={syncingGoogle || googleStatusLoading || !googleConnected}
              className="inline-flex items-center justify-center gap-2 rounded-xl border border-emerald-400/70 px-4 py-3 font-bold text-emerald-200 transition hover:bg-emerald-400 hover:text-slate-950 disabled:cursor-not-allowed disabled:opacity-60"
              title={
                googleConnected
                  ? "Sync approved trusted deadlines to Google Calendar"
                  : "Connect Google Calendar before syncing"
              }
            >
              {syncingGoogle ? (
                <Loader2 size={18} className="animate-spin" />
              ) : (
                <CalendarCheck2 size={18} />
              )}
              {syncingGoogle
                ? "Syncing Google..."
                : `Sync Google (${approvedSyncableEvents.length})`}
            </button>

            <button
              onClick={exportCalendar}
              disabled={exporting}
              className="inline-flex items-center justify-center gap-2 rounded-xl bg-cyan-400 px-4 py-3 font-bold text-slate-950 transition hover:bg-cyan-300 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {exporting ? (
                <Loader2 size={18} className="animate-spin" />
              ) : (
                <CalendarDays size={18} />
              )}
              Export approved calendar
            </button>
          </div>
        </header>

        {notice && (
          <div
            className="mb-6 flex items-start gap-3 rounded-xl border border-cyan-400/30 bg-cyan-400/10 px-4 py-3 text-sm text-cyan-100"
            role="status"
          >
            <Check size={18} className="mt-0.5 shrink-0" />
            <span>{notice}</span>
          </div>
        )}

        {highWorkload && (
          <section className="mb-7 rounded-2xl border border-amber-400/40 bg-amber-300/10 p-5">
            <div className="flex gap-3">
              <AlertTriangle className="mt-0.5 shrink-0 text-amber-300" />
              <div>
                <p className="font-bold text-amber-200">
                  High workload detected
                </p>
                <p className="mt-1 text-sm text-amber-100/80">
                  {highWorkload.date}: {highWorkload.minutes} estimated minutes.{" "}
                  {highWorkload.reason}
                </p>
              </div>
            </div>
          </section>
        )}

        <div className="grid gap-7 lg:grid-cols-[1.45fr_0.85fr]">
          <section className="space-y-7">
            <section className="rounded-2xl border border-slate-800 bg-slate-900/70 p-5 shadow-2xl shadow-black/20">
              <div className="mb-5 flex items-center justify-between">
                <div>
                  <h2 className="text-xl font-bold">Upcoming deadlines</h2>
                  <p className="mt-1 text-sm text-slate-400">
                    Click an event to inspect its evidence, history, and export
                    approval.
                  </p>
                </div>

                <button
                  onClick={() => void loadWorkspace(false)}
                  className="rounded-lg border border-slate-700 p-2 text-slate-300 transition hover:border-cyan-400 hover:text-cyan-300"
                  title="Refresh events"
                  aria-label="Refresh events"
                >
                  <RefreshCw size={17} />
                </button>
              </div>

              <div className="space-y-3">
                {events
                  .slice()
                  .sort((a, b) =>
                    (a.due_at ?? "9999").localeCompare(b.due_at ?? "9999"),
                  )
                  .map((event) => {
                    const course = coursesById[event.course_id];

                    return (
                      <button
                        key={event.id}
                        onClick={() => setSelectedEvent(event)}
                        className="flex w-full items-center gap-4 rounded-xl border border-slate-800 bg-slate-950/70 p-4 text-left transition hover:border-cyan-400/60 hover:bg-slate-800"
                      >
                        <span
                          className="h-11 w-1.5 rounded-full"
                          style={{
                            backgroundColor: course?.color ?? "#64748b",
                          }}
                        />

                        <div className="min-w-0 flex-1">
                          <div className="flex flex-wrap items-center gap-2">
                            <p className="truncate font-bold">{event.title}</p>
                            <span
                              className={`rounded-full border px-2 py-0.5 text-xs font-semibold ${statusStyle(
                                event.status,
                              )}`}
                            >
                              {actionLabel(event.status)}
                            </span>
                            {event.approved && (
                              <span className="rounded-full border border-cyan-400/40 bg-cyan-400/10 px-2 py-0.5 text-xs font-semibold text-cyan-200">
                                Approved
                              </span>
                            )}
                          </div>

                          <p className="mt-1 text-sm text-slate-400">
                            {course?.code ?? event.course_id} -{" "}
                            {formatDate(event.due_at)}
                          </p>
                        </div>

                        <ChevronRight
                          className="shrink-0 text-slate-500"
                          size={20}
                        />
                      </button>
                    );
                  })}

                {events.length === 0 && (
                  <div className="rounded-xl border border-dashed border-slate-700 p-5 text-sm text-slate-500">
                    No deadlines yet. Import Canvas assignments or scan a course
                    update to get started.
                  </div>
                )}
              </div>
            </section>

            <section className="rounded-2xl border border-slate-800 bg-slate-900/70 p-5">
              <div className="mb-4 flex items-center gap-2">
                <CalendarDays className="text-cyan-300" size={20} />
                <div>
                  <h2 className="text-xl font-bold">Import from Canvas</h2>
                  <p className="text-sm text-slate-400">
                    Pull official upcoming assignment due dates from Canvas.
                  </p>
                </div>
              </div>

              {canvasCourses.length === 0 ? (
                <button
                  onClick={loadCanvasCourses}
                  disabled={canvasLoading}
                  className="inline-flex items-center gap-2 rounded-lg bg-cyan-400 px-4 py-2.5 font-bold text-slate-950 transition hover:bg-cyan-300 disabled:cursor-not-allowed disabled:opacity-60"
                >
                  {canvasLoading ? (
                    <Loader2 size={18} className="animate-spin" />
                  ) : (
                    <RefreshCw size={18} />
                  )}
                  {canvasLoading ? "Loading Canvas..." : "Load Canvas courses"}
                </button>
              ) : (
                <div className="flex flex-col gap-3 sm:flex-row">
                  <select
                    value={canvasCourseId}
                    onChange={(event) => setCanvasCourseId(event.target.value)}
                    className="min-w-0 flex-1 rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm outline-none focus:border-cyan-400"
                    aria-label="Canvas course"
                  >
                    {canvasCourses.map((course) => (
                      <option key={course.id} value={course.id}>
                        {course.course_code
                          ? `${course.course_code} - ${course.name}`
                          : course.name}
                      </option>
                    ))}
                  </select>

                  <button
                    onClick={importCanvasCourse}
                    disabled={canvasImporting}
                    className="inline-flex items-center justify-center gap-2 rounded-lg border border-cyan-400/60 px-4 py-2.5 font-bold text-cyan-200 transition hover:bg-cyan-400 hover:text-slate-950 disabled:cursor-not-allowed disabled:opacity-60"
                  >
                    {canvasImporting ? (
                      <Loader2 size={18} className="animate-spin" />
                    ) : (
                      <CalendarDays size={18} />
                    )}
                    {canvasImporting ? "Importing..." : "Import deadlines"}
                  </button>
                </div>
              )}
            </section>

            <section className="rounded-2xl border border-slate-800 bg-slate-900/70 p-5">
              <div className="mb-4 flex items-center gap-2">
                <FileText className="text-cyan-300" size={20} />
                <div>
                  <h2 className="text-xl font-bold">Scan a course update</h2>
                  <p className="text-sm text-slate-400">
                    Paste an announcement, email, or syllabus excerpt.
                  </p>
                </div>
              </div>

              <div className="grid gap-3 sm:grid-cols-2">
                <select
                  value={courseId}
                  onChange={(event) => setCourseId(event.target.value)}
                  className="rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm outline-none focus:border-cyan-400"
                  aria-label="DueScope course"
                >
                  {(workspace?.courses ?? []).map((course) => (
                    <option key={course.id} value={course.id}>
                      {course.code} - {course.name}
                    </option>
                  ))}
                </select>

                <select
                  value={sourceType}
                  onChange={(event) => setSourceType(event.target.value)}
                  className="rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm outline-none focus:border-cyan-400"
                  aria-label="Source type"
                >
                  <option value="instructor_announcement">
                    Canvas announcement
                  </option>
                  <option value="instructor_email">Instructor email</option>
                  <option value="syllabus">Syllabus</option>
                  <option value="other">Other course source</option>
                </select>
              </div>

              <input
                value={sourceTitle}
                onChange={(event) => setSourceTitle(event.target.value)}
                className="mt-3 w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm outline-none focus:border-cyan-400"
                placeholder="Source title"
                aria-label="Source title"
              />

              <textarea
                value={sourceText}
                onChange={(event) => setSourceText(event.target.value)}
                className="mt-3 min-h-36 w-full resize-y rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm leading-6 outline-none focus:border-cyan-400"
                placeholder="Paste a course announcement, email, or syllabus excerpt..."
                aria-label="Course source text"
              />

              <button
                onClick={scanSource}
                disabled={scanning || !sourceText.trim()}
                className="mt-3 inline-flex items-center gap-2 rounded-lg bg-cyan-400 px-4 py-2.5 font-bold text-slate-950 transition hover:bg-cyan-300 disabled:cursor-not-allowed disabled:opacity-60"
              >
                {scanning ? (
                  <Loader2 size={18} className="animate-spin" />
                ) : (
                  <Sparkles size={18} />
                )}
                {scanning ? "Scanning course update..." : "Scan for deadlines"}
              </button>
            </section>
          </section>

          <aside className="space-y-7">
            <section className="rounded-2xl border border-emerald-400/30 bg-emerald-300/5 p-5">
              <div className="flex items-start gap-3">
                <CalendarCheck2 className="mt-0.5 shrink-0 text-emerald-300" size={20} />
                <div className="min-w-0 flex-1">
                  <div className="flex flex-wrap items-center justify-between gap-3">
                    <div>
                      <h2 className="text-xl font-bold">Google Calendar</h2>
                      <p className="mt-1 text-sm text-slate-400">
                        Sync only deadlines you explicitly approve.
                      </p>
                    </div>
                    <button
                      onClick={() => void loadGoogleStatus(true)}
                      disabled={googleStatusLoading}
                      className="rounded-lg border border-slate-700 p-2 text-slate-300 transition hover:border-emerald-400 hover:text-emerald-300 disabled:cursor-not-allowed disabled:opacity-60"
                      title="Refresh Google Calendar status"
                      aria-label="Refresh Google Calendar status"
                    >
                      <RefreshCw
                        size={16}
                        className={googleStatusLoading ? "animate-spin" : ""}
                      />
                    </button>
                  </div>

                  <div className="mt-4 rounded-xl border border-slate-700 bg-slate-950/70 p-3">
                    <p className="text-xs font-bold uppercase tracking-wider text-slate-500">
                      Connection status
                    </p>
                    <p
                      className={`mt-1 text-sm font-semibold ${
                        googleConnected ? "text-emerald-300" : "text-amber-300"
                      }`}
                    >
                      {googleStatusLoading
                        ? "Checking connection..."
                        : googleConnected
                          ? "Connected to Google Calendar"
                          : "Not connected"}
                    </p>
                  </div>

                  {googleConnected ? (
                    <button
                      onClick={() => void syncApprovedToGoogle()}
                      disabled={syncingGoogle || approvedSyncableEvents.length === 0}
                      className="mt-3 inline-flex w-full items-center justify-center gap-2 rounded-lg bg-emerald-400 px-4 py-2.5 font-bold text-slate-950 transition hover:bg-emerald-300 disabled:cursor-not-allowed disabled:opacity-60"
                    >
                      {syncingGoogle ? (
                        <Loader2 size={18} className="animate-spin" />
                      ) : (
                        <CalendarCheck2 size={18} />
                      )}
                      {syncingGoogle
                        ? "Syncing approved deadlines..."
                        : `Sync ${approvedSyncableEvents.length} approved deadline${
                            approvedSyncableEvents.length === 1 ? "" : "s"
                          }`}
                    </button>
                  ) : (
                    <button
                      onClick={connectGoogleCalendar}
                      className="mt-3 inline-flex w-full items-center justify-center gap-2 rounded-lg bg-emerald-400 px-4 py-2.5 font-bold text-slate-950 transition hover:bg-emerald-300"
                    >
                      <CalendarCheck2 size={18} />
                      Connect Google Calendar
                    </button>
                  )}

                  {googleConnected && approvedSyncableEvents.length === 0 && (
                    <p className="mt-3 text-sm text-slate-500">
                      Approve a verified or updated deadline to enable sync.
                    </p>
                  )}

                  {syncResult && (
                    <div className="mt-4 space-y-3">
                      {syncResult.created.length > 0 && (
                        <div className="rounded-xl border border-emerald-400/30 bg-emerald-400/10 p-3 text-sm text-emerald-100">
                          <p className="font-bold">
                            Created: {syncItemSummary(syncResult.created)}
                          </p>
                          {syncResult.created.map((item) =>
                            item.calendar_url ? (
                              <a
                                key={item.event_id}
                                href={item.calendar_url}
                                target="_blank"
                                rel="noreferrer"
                                className="mt-1 block text-xs text-emerald-200 underline underline-offset-2"
                              >
                                Open {item.title} in Google Calendar
                              </a>
                            ) : null,
                          )}
                        </div>
                      )}

                      {syncResult.updated.length > 0 && (
                        <div className="rounded-xl border border-cyan-400/30 bg-cyan-400/10 p-3 text-sm text-cyan-100">
                          <p className="font-bold">
                            Updated: {syncItemSummary(syncResult.updated)}
                          </p>
                          {syncResult.updated.map((item) =>
                            item.calendar_url ? (
                              <a
                                key={item.event_id}
                                href={item.calendar_url}
                                target="_blank"
                                rel="noreferrer"
                                className="mt-1 block text-xs text-cyan-200 underline underline-offset-2"
                              >
                                Open {item.title} in Google Calendar
                              </a>
                            ) : null,
                          )}
                        </div>
                      )}

                      {syncResult.skipped.length > 0 && (
                        <div className="rounded-xl border border-amber-400/30 bg-amber-400/10 p-3 text-sm text-amber-100">
                          <p className="font-bold">Skipped deadlines</p>
                          {syncResult.skipped.map((item) => (
                            <p key={item.event_id} className="mt-1 text-xs">
                              {item.title}: {item.reason ?? "Not eligible for sync."}
                            </p>
                          ))}
                        </div>
                      )}

                      {syncResult.failed.length > 0 && (
                        <div className="rounded-xl border border-rose-400/30 bg-rose-400/10 p-3 text-sm text-rose-100">
                          <p className="font-bold">Sync errors</p>
                          {syncResult.failed.map((item) => (
                            <p key={item.event_id} className="mt-1 text-xs">
                              {item.title}: {item.reason ?? "Unknown sync error."}
                            </p>
                          ))}
                        </div>
                      )}
                    </div>
                  )}
                </div>
              </div>
            </section>

            <section className="rounded-2xl border border-amber-400/30 bg-amber-300/5 p-5">
              <div className="flex items-start gap-2">
                <ShieldCheck className="mt-0.5 shrink-0 text-amber-300" size={20} />
                <div>
                  <h2 className="text-xl font-bold">Deadline proposals</h2>
                  <p className="mt-1 text-sm text-slate-400">
                    A changed date never overwrites your saved deadline
                    automatically.
                  </p>
                </div>
              </div>

              <div className="mt-4 space-y-4">
                {proposals.map((proposal) => {
                  const savedEvent = events.find(
                    (event) => event.id === proposal.event_id,
                  );
                  const course = savedEvent
                    ? coursesById[savedEvent.course_id]
                    : undefined;
                  const resolving = resolvingProposalId === proposal.id;

                  return (
                    <article
                      key={proposal.id}
                      className="rounded-xl border border-amber-400/30 bg-slate-950/70 p-4"
                    >
                      <p className="font-semibold text-amber-100">
                        {proposal.candidate.title}
                      </p>

                      <p className="mt-1 text-xs text-slate-400">
                        {course?.code ?? savedEvent?.course_id ?? "Course"} -
                        review required
                      </p>

                      <div className="mt-3 grid gap-2 text-sm sm:grid-cols-2">
                        <div className="rounded-lg border border-slate-800 p-3">
                          <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                            Saved deadline
                          </p>
                          <p className="mt-1 text-slate-200">
                            {formatDate(savedEvent?.due_at)}
                          </p>
                        </div>

                        <div className="rounded-lg border border-amber-400/30 bg-amber-300/10 p-3">
                          <p className="text-xs font-semibold uppercase tracking-wide text-amber-300">
                            Proposed deadline
                          </p>
                          <p className="mt-1 text-amber-100">
                            {formatDate(proposal.candidate.due_at)}
                          </p>
                        </div>
                      </div>

                      <p className="mt-3 text-sm leading-6 text-slate-400">
                        {proposal.message}
                      </p>

                      <div className="mt-3 rounded-lg border border-slate-700 bg-slate-950 p-3">
                        <p className="text-xs font-bold uppercase tracking-wider text-slate-500">
                          Proposed evidence
                        </p>
                        <p className="mt-1 text-sm leading-6 text-slate-300">
                          &quot;{proposal.candidate.source_excerpt}&quot;
                        </p>
                      </div>

                      {proposal.candidate.needs_review_reason && (
                        <div className="mt-3 rounded-lg border border-rose-400/30 bg-rose-400/10 p-3 text-sm text-rose-100">
                          {proposal.candidate.needs_review_reason}
                        </div>
                      )}

                      <div className="mt-4 grid gap-2 sm:grid-cols-2">
                        <button
                          onClick={() => void resolveProposal(proposal, "accept")}
                          disabled={resolving}
                          className="inline-flex items-center justify-center gap-2 rounded-lg bg-amber-300 px-3 py-2.5 text-sm font-bold text-slate-950 transition hover:bg-amber-200 disabled:cursor-not-allowed disabled:opacity-60"
                        >
                          {resolving ? (
                            <Loader2 size={16} className="animate-spin" />
                          ) : (
                            <Check size={16} />
                          )}
                          Accept change
                        </button>

                        <button
                          onClick={() => void resolveProposal(proposal, "reject")}
                          disabled={resolving}
                          className="inline-flex items-center justify-center gap-2 rounded-lg border border-slate-600 px-3 py-2.5 text-sm font-bold text-slate-200 transition hover:border-slate-400 hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-60"
                        >
                          <X size={16} />
                          Keep saved date
                        </button>
                      </div>
                    </article>
                  );
                })}

                {proposals.length === 0 && (
                  <div className="rounded-xl border border-dashed border-slate-700 p-4 text-sm text-slate-500">
                    No proposed deadline changes are waiting for review.
                  </div>
                )}
              </div>
            </section>

            <section className="rounded-2xl border border-slate-800 bg-slate-900/70 p-5">
              <h2 className="text-xl font-bold">Changes to review</h2>

              <div className="mt-4 space-y-3">
                {(workspace?.changes ?? []).map((change) => (
                  <button
                    key={`${change.event_id}-${change.kind}`}
                    onClick={() => {
                      const event = events.find(
                        (item) => item.id === change.event_id,
                      );

                      if (event) {
                        setSelectedEvent(event);
                      }
                    }}
                    className="w-full rounded-xl border border-slate-800 bg-slate-950/70 p-3 text-left text-sm transition hover:border-cyan-400/60"
                  >
                    <p className="font-semibold capitalize text-cyan-200">
                      {actionLabel(change.kind)}
                    </p>
                    <p className="mt-1 text-slate-400">{change.message}</p>
                  </button>
                ))}

                {(workspace?.changes ?? []).length === 0 && (
                  <div className="rounded-xl border border-dashed border-slate-700 p-4 text-sm text-slate-500">
                    No changes need review right now.
                  </div>
                )}
              </div>
            </section>

            <section className="rounded-2xl border border-slate-800 bg-slate-900/70 p-5">
              <h2 className="text-xl font-bold">Evidence panel</h2>

              {selectedEvent ? (
                <div className="mt-4 space-y-4">
                  <div>
                    <p className="text-sm font-bold">{selectedEvent.title}</p>
                    <p className="mt-1 text-sm text-slate-400">
                      {coursesById[selectedEvent.course_id]?.code ??
                        selectedEvent.course_id}{" "}
                      - {formatDate(selectedEvent.due_at)}
                    </p>
                  </div>

                  <div className="rounded-xl border border-slate-700 bg-slate-950 p-3">
                    <p className="mb-2 text-xs font-bold uppercase tracking-wider text-slate-500">
                      Source evidence
                    </p>
                    <p className="text-sm leading-6 text-slate-300">
                      &quot;{selectedEvent.source_excerpt}&quot;
                    </p>
                  </div>

                  {selectedEvent.history.length > 0 && (
                    <div>
                      <p className="mb-2 text-xs font-bold uppercase tracking-wider text-slate-500">
                        Deadline history
                      </p>

                      <div className="space-y-2">
                        {selectedEvent.history.map((version, index) => (
                          <div
                            key={`${version.source_id}-${index}`}
                            className="rounded-lg border border-slate-800 bg-slate-950/70 p-3 text-sm"
                          >
                            <div className="flex items-center justify-between gap-3">
                              <span className="font-medium">
                                {formatDate(version.due_at)}
                              </span>
                              <span
                                className={
                                  version.is_current
                                    ? "text-emerald-300"
                                    : "text-slate-500"
                                }
                              >
                                {version.is_current ? "Current" : "Previous"}
                              </span>
                            </div>
                            <p className="mt-1 text-xs text-slate-500">
                              {version.reason}
                            </p>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {selectedEvent.needs_review_reason && (
                    <div className="rounded-xl border border-rose-400/30 bg-rose-400/10 p-3 text-sm text-rose-100">
                      {selectedEvent.needs_review_reason}
                    </div>
                  )}

                  <button
                    onClick={() => void toggleApproval(selectedEvent)}
                    disabled={
                      !["verified", "updated"].includes(selectedEvent.status)
                    }
                    className="inline-flex w-full items-center justify-center gap-2 rounded-lg border border-cyan-400/60 px-4 py-2.5 font-bold text-cyan-200 transition hover:bg-cyan-400 hover:text-slate-950 disabled:cursor-not-allowed disabled:border-slate-700 disabled:text-slate-600"
                  >
                    <Check size={17} />
                    {selectedEvent.approved
                      ? "Remove approval"
                      : "Approve for export and sync"}
                  </button>

                  {selectedEvent.approved && googleConnected && (
                    <button
                      onClick={async () => {
                        setSyncingGoogle(true);
                        setNotice("");
                        setSyncResult(null);

                        try {
                          const response = await fetch(
                            `${API_URL}/api/google/calendar/sync-approved`,
                            {
                              method: "POST",
                              headers: { "Content-Type": "application/json" },
                              body: JSON.stringify({
                                event_ids: [selectedEvent.id],
                              }),
                            },
                          );
                          const data = (await response.json()) as
                            | GoogleSyncResult
                            | { detail?: string };

                          if (!response.ok) {
                            throw new Error(
                              "detail" in data
                                ? data.detail
                                : "Google Calendar sync failed.",
                            );
                          }

                          const result = data as GoogleSyncResult;
                          setSyncResult(result);

                          if (result.created.length > 0) {
                            setNotice(
                              `${selectedEvent.title} was added to Google Calendar.`,
                            );
                          } else if (result.updated.length > 0) {
                            setNotice(
                              `${selectedEvent.title} was updated in Google Calendar.`,
                            );
                          } else if (result.skipped.length > 0) {
                            setNotice(
                              result.skipped[0].reason ??
                                "This deadline could not be synced.",
                            );
                          } else if (result.failed.length > 0) {
                            setNotice(
                              result.failed[0].reason ??
                                "Google Calendar sync failed.",
                            );
                          }
                        } catch (error) {
                          setNotice(
                            error instanceof Error
                              ? error.message
                              : "Google Calendar sync failed.",
                          );
                        } finally {
                          setSyncingGoogle(false);
                        }
                      }}
                      disabled={syncingGoogle}
                      className="inline-flex w-full items-center justify-center gap-2 rounded-lg border border-emerald-400/60 px-4 py-2.5 font-bold text-emerald-200 transition hover:bg-emerald-400 hover:text-slate-950 disabled:cursor-not-allowed disabled:opacity-60"
                    >
                      {syncingGoogle ? (
                        <Loader2 size={17} className="animate-spin" />
                      ) : (
                        <CalendarCheck2 size={17} />
                      )}
                      Sync this deadline to Google
                    </button>
                  )}

                  {selectedEvent.approved && !googleConnected && (
                    <button
                      onClick={connectGoogleCalendar}
                      className="inline-flex w-full items-center justify-center gap-2 rounded-lg border border-emerald-400/60 px-4 py-2.5 font-bold text-emerald-200 transition hover:bg-emerald-400 hover:text-slate-950"
                    >
                      <Unplug size={17} />
                      Connect Google to sync
                    </button>
                  )}
                </div>
              ) : (
                <div className="mt-4 rounded-xl border border-dashed border-slate-700 p-5 text-sm text-slate-500">
                  Select a deadline to inspect its evidence, history, and export
                  approval.
                </div>
              )}
            </section>

            <section className="rounded-2xl border border-slate-800 bg-slate-900/70 p-5">
              <div className="flex items-center gap-2">
                <Clock3 size={20} className="text-cyan-300" />
                <h2 className="text-xl font-bold">How DueScope works</h2>
              </div>

              <ol className="mt-4 space-y-3 text-sm text-slate-400">
                <li>1. Import Canvas work or scan course information.</li>
                <li>2. AI extracts source-backed deadline candidates.</li>
                <li>3. DueScope validates evidence and proposes date conflicts.</li>
                <li>4. Accept trusted changes, approve events, then export or sync them.</li>
              </ol>
            </section>
          </aside>
        </div>
      </div>
    </main>
  );
}
