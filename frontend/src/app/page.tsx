"use client";

import { useEffect, useMemo, useState } from "react";
import {
  AlertTriangle,
  CalendarDays,
  Check,
  ChevronRight,
  Clock3,
  FileText,
  Loader2,
  RefreshCw,
  Sparkles,
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

type Workspace = {
  courses: Course[];
  events: AcademicEvent[];
  changes: Change[];
  workload: WorkloadDay[];
};

type ExtractionResult = {
  results: Array<{
    title: string;
    action: string;
    message: string;
    event_id: string;
  }>;
};

type CanvasCourse = {
  id: number;
  course_code: string;
  name: string;
};

const seedAnnouncement = `Programming Assignment 2 has been extended.
It is now due Monday, September 21, 2026 at 11:59 PM in Canvas.`;

function formatDate(value: string | null) {
  if (!value) return "Needs review";

  return new Intl.DateTimeFormat("en-US", {
    weekday: "short",
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  }).format(new Date(value));
}

function statusStyle(status: AcademicEvent["status"]) {
  if (status === "updated") {
    return "bg-amber-100 text-amber-800 border-amber-200";
  }

  if (status === "needs_review") {
    return "bg-rose-100 text-rose-800 border-rose-200";
  }

  if (status === "verified") {
    return "bg-emerald-100 text-emerald-800 border-emerald-200";
  }

  return "bg-slate-100 text-slate-700 border-slate-200";
}

export default function Home() {
  const [workspace, setWorkspace] = useState<Workspace | null>(null);
  const [selectedEvent, setSelectedEvent] = useState<AcademicEvent | null>(null);
  const [sourceText, setSourceText] = useState(seedAnnouncement);
  const [sourceTitle, setSourceTitle] = useState("Programming Assignment 2 extension");
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

  const coursesById = useMemo(
    () =>
      Object.fromEntries(
        (workspace?.courses ?? []).map((course) => [course.id, course]),
      ),
    [workspace],
  );

  async function loadWorkspace() {
    setLoading(true);

    try {
      const response = await fetch(`${API_URL}/api/demo/workspace`, {
        cache: "no-store",
      });

      if (!response.ok) {
        throw new Error("Could not load DueScope demo workspace.");
      }

      const data = (await response.json()) as Workspace;
      setWorkspace(data);

      setSelectedEvent((current) => {
        if (!current) return null;

        return data.events.find((event) => event.id === current.id) ?? null;
      });
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "Could not reach the backend.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void loadWorkspace();
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
          `Loaded ${courses.length} Canvas course(s). Choose one to import official due dates.`,
        );
      } else {
        setNotice("No active Canvas courses were returned for this account.");
      }
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "Could not load Canvas courses.");
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

      setNotice(
        `Imported ${data.imported_count} upcoming Canvas deadline(s). ` +
          `${data.skipped_past_count} past deadline(s) skipped.`,
      );

      await loadWorkspace();
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "Could not import Canvas deadlines.");
    } finally {
      setCanvasImporting(false);
    }
  }

  async function scanSource() {
    setScanning(true);
    setNotice("");

    try {
      const response = await fetch(`${API_URL}/api/sources/extract-and-reconcile`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          course_id: courseId,
          source_type: sourceType,
          source_title: sourceTitle,
          source_received_at: new Date().toISOString(),
          timezone: "America/Chicago",
          source_text: sourceText,
        }),
      });

      const data = (await response.json()) as ExtractionResult | { detail?: string };

      if (!response.ok) {
        throw new Error("detail" in data ? data.detail : "Deadline scan failed.");
      }

      const result = data as ExtractionResult;

      setNotice(
        result.results.length > 0
          ? result.results
              .map((item) => `${item.title}: ${item.action}`)
              .join(" - ")
          : "No deadlines found in this source.",
      );

      await loadWorkspace();
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "Deadline scan failed.");
    } finally {
      setScanning(false);
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

      await loadWorkspace();

      setNotice(
        `${event.title} ${event.approved ? "removed from" : "approved for"} calendar export.`,
      );
    } catch (error) {
      setNotice(error instanceof Error ? error.message : "Could not update approval.");
    }
  }

  async function exportCalendar() {
    const eventIds = (workspace?.events ?? [])
      .filter(
        (event) =>
          event.approved &&
          ["verified", "updated"].includes(event.status),
      )
      .map((event) => event.id);

    if (eventIds.length === 0) {
      setNotice("Approve at least one verified or updated deadline before exporting.");
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
      setNotice(error instanceof Error ? error.message : "Calendar export failed.");
    } finally {
      setExporting(false);
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
              A source-backed academic calendar that detects deadline changes before
              they become missed work.
            </p>
          </div>

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
        </header>

        {notice && (
          <div className="mb-6 flex items-start gap-3 rounded-xl border border-cyan-400/30 bg-cyan-400/10 px-4 py-3 text-sm text-cyan-100">
            <Check size={18} className="mt-0.5 shrink-0" />
            <span>{notice}</span>
          </div>
        )}

        {highWorkload && (
          <section className="mb-7 rounded-2xl border border-amber-400/40 bg-amber-300/10 p-5">
            <div className="flex gap-3">
              <AlertTriangle className="mt-0.5 shrink-0 text-amber-300" />
              <div>
                <p className="font-bold text-amber-200">High workload detected</p>
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
            <div className="rounded-2xl border border-slate-800 bg-slate-900/70 p-5 shadow-2xl shadow-black/20">
              <div className="mb-5 flex items-center justify-between">
                <div>
                  <h2 className="text-xl font-bold">Upcoming deadlines</h2>
                  <p className="mt-1 text-sm text-slate-400">
                    Click an event to inspect evidence and date history.
                  </p>
                </div>

                <button
                  onClick={loadWorkspace}
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
                          style={{ backgroundColor: course?.color ?? "#64748b" }}
                        />

                        <div className="min-w-0 flex-1">
                          <div className="flex flex-wrap items-center gap-2">
                            <p className="truncate font-bold">{event.title}</p>

                            <span
                              className={`rounded-full border px-2 py-0.5 text-xs font-semibold ${statusStyle(
                                event.status,
                              )}`}
                            >
                              {event.status.replace("_", " ")}
                            </span>
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
                    No upcoming deadlines yet. Import Canvas dates or scan a course
                    update to begin.
                  </div>
                )}
              </div>
            </div>

            <div className="rounded-2xl border border-slate-800 bg-slate-900/70 p-5">
              <div className="mb-4 flex items-center gap-2">
                <CalendarDays className="text-cyan-300" size={20} />

                <div>
                  <h2 className="text-xl font-bold">Import from Canvas</h2>
                  <p className="text-sm text-slate-400">
                    Pull official assignment due dates directly from Canvas.
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
            </div>

            <div className="rounded-2xl border border-slate-800 bg-slate-900/70 p-5">
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
              />

              <textarea
                value={sourceText}
                onChange={(event) => setSourceText(event.target.value)}
                className="mt-3 min-h-36 w-full resize-y rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm leading-6 outline-none focus:border-cyan-400"
                placeholder="Paste a course announcement, email, or syllabus excerpt..."
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
                {scanning ? "Scanning with Gemini..." : "Scan for deadlines"}
              </button>
            </div>
          </section>

          <aside className="space-y-7">
            <div className="rounded-2xl border border-slate-800 bg-slate-900/70 p-5">
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
                      {change.kind.replace("_", " ")}
                    </p>

                    <p className="mt-1 text-slate-400">{change.message}</p>
                  </button>
                ))}

                {(workspace?.changes ?? []).length === 0 && (
                  <p className="rounded-xl border border-dashed border-slate-700 p-4 text-sm text-slate-500">
                    No deadline changes need review right now.
                  </p>
                )}
              </div>
            </div>

            <div className="rounded-2xl border border-slate-800 bg-slate-900/70 p-5">
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
                    onClick={() => toggleApproval(selectedEvent)}
                    disabled={
                      !["verified", "updated"].includes(selectedEvent.status)
                    }
                    className="inline-flex w-full items-center justify-center gap-2 rounded-lg border border-cyan-400/60 px-4 py-2.5 font-bold text-cyan-200 transition hover:bg-cyan-400 hover:text-slate-950 disabled:cursor-not-allowed disabled:border-slate-700 disabled:text-slate-600"
                  >
                    <Check size={17} />
                    {selectedEvent.approved
                      ? "Remove approval"
                      : "Approve for export"}
                  </button>
                </div>
              ) : (
                <div className="mt-4 rounded-xl border border-dashed border-slate-700 p-5 text-sm text-slate-500">
                  Select a deadline to inspect its evidence, date history, and export
                  approval.
                </div>
              )}
            </div>

            <div className="rounded-2xl border border-slate-800 bg-slate-900/70 p-5">
              <div className="flex items-center gap-2">
                <Clock3 size={20} className="text-cyan-300" />
                <h2 className="text-xl font-bold">How DueScope works</h2>
              </div>

              <ol className="mt-4 space-y-3 text-sm text-slate-400">
                <li>1. Scan course information from Canvas, email, or a syllabus.</li>
                <li>2. Gemini extracts only source-backed deadlines.</li>
                <li>3. DueScope reconciles updates and preserves history.</li>
                <li>4. Approve trusted events and export your calendar.</li>
              </ol>
            </div>
          </aside>
        </div>
      </div>
    </main>
  );
}