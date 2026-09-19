"use client";


import { API_BASE_URL } from "@/lib/api";
import { useEffect, useMemo, useState } from "react";
import {
  AlertTriangle,
  BriefcaseBusiness,
  CalendarCheck2,
  CalendarDays,
  Check,
  ChevronRight,
  Clock3,
  ExternalLink,
  FileText,
  Loader2,
  Pencil,
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

type JobStatus =
  | "application_received"
  | "online_assessment"
  | "recruiter_screen"
  | "phone_screen"
  | "technical_interview"
  | "onsite_interview"
  | "final_interview"
  | "offer"
  | "rejected"
  | "unknown";

type JobHistoryItem = {
  status: JobStatus;
  message_id: string;
  received_at: string;
  reason: string;
};

type JobApplication = {
  id: string;
  company: string;
  role: string;
  status: JobStatus;
  next_action: string;
  received_at: string;
  requires_review: boolean;
  source_subject: string;
  source_sender: string;
  source_message_id: string;
  source_thread_id?: string;
  gmail_url: string;
  source_excerpt: string;
  updated_at: string;
  history?: JobHistoryItem[];
};

type JobScanResult = {
  query: string;
  matched_count: number;
  created: JobApplication[];
  updated: JobApplication[];
  skipped: Array<{ message_id: string; reason: string }>;
  errors: Array<{ message_id: string; reason: string }>;
  calendar_proposals?: JobCalendarProposal[];
  safety_note: string;
};

type JobProposalKind =
  | "online_assessment_deadline"
  | "interview_scheduling_deadline"
  | "confirmed_interview";

type JobProposalStatus = "pending" | "approved" | "dismissed";

type JobCalendarProposal = {
  id: string;
  job_id: string;
  company: string;
  role: string;
  kind: JobProposalKind;
  title: string;
  starts_at: string;
  ends_at: string;
  source_message_id: string;
  source_excerpt: string;
  gmail_url: string;
  status: JobProposalStatus;
  created_at: string;
  resolved_at: string | null;
  google_calendar_event_id: string | null;
  google_calendar_url: string | null;
  calendar_synced_at: string | null;
};

type JobProposalApprovalResponse = {
  proposal: JobCalendarProposal;
  calendar: {
    action: "created" | "updated";
    google_calendar_event_id: string;
    calendar_url: string;
  };
};

type DeadlineFilter = "7" | "14" | "30" | "all";

const DEADLINE_FILTERS: Array<{ value: DeadlineFilter; label: string }> = [
  { value: "7", label: "Next 7 days" },
  { value: "14", label: "Next 14 days" },
  { value: "30", label: "Next 30 days" },
  { value: "all", label: "All semester" },
];

const JOB_STATUSES: JobStatus[] = [
  "application_received",
  "online_assessment",
  "recruiter_screen",
  "phone_screen",
  "technical_interview",
  "onsite_interview",
  "final_interview",
  "offer",
  "rejected",
  "unknown",
];

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

function jobStatusStyle(status: JobStatus) {
  if (status === "rejected") {
    return "border-rose-400/40 bg-rose-400/10 text-rose-200";
  }

  if (status === "offer") {
    return "border-emerald-400/40 bg-emerald-400/10 text-emerald-200";
  }

  if (
    [
      "online_assessment",
      "recruiter_screen",
      "phone_screen",
      "technical_interview",
      "onsite_interview",
      "final_interview",
    ].includes(status)
  ) {
    return "border-cyan-400/40 bg-cyan-400/10 text-cyan-200";
  }

  if (status === "application_received") {
    return "border-violet-400/40 bg-violet-400/10 text-violet-200";
  }

  return "border-slate-600 bg-slate-800 text-slate-300";
}

function jobProposalStyle(kind: JobProposalKind) {
  if (kind === "confirmed_interview") {
    return "border-cyan-400/40 bg-cyan-400/10 text-cyan-200";
  }

  if (kind === "online_assessment_deadline") {
    return "border-violet-400/40 bg-violet-400/10 text-violet-200";
  }

  return "border-amber-400/40 bg-amber-400/10 text-amber-200";
}

function actionLabel(action: string) {
  return action.replaceAll("_", " ");
}

function syncItemSummary(items: GoogleSyncItem[]) {
  return items.map((item) => item.title).join(", ");
}

function uniqueJobs(jobs: JobApplication[]) {
  return Array.from(new Map(jobs.map((job) => [job.id, job])).values());
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
  const [canvasFocusCourseId, setCanvasFocusCourseId] = useState<string | null>(
    null,
  );
  const [deadlineFilter, setDeadlineFilter] = useState<DeadlineFilter>("14");
  const [canvasLoading, setCanvasLoading] = useState(false);
  const [canvasImporting, setCanvasImporting] = useState(false);
  const [resolvingProposalId, setResolvingProposalId] = useState("");
  const [googleConnected, setGoogleConnected] = useState(false);
  const [googleStatusLoading, setGoogleStatusLoading] = useState(true);
  const [syncingGoogle, setSyncingGoogle] = useState(false);
  const [syncResult, setSyncResult] = useState<GoogleSyncResult | null>(null);
  const [jobs, setJobs] = useState<JobApplication[]>([]);
  const [jobsLoading, setJobsLoading] = useState(true);
  const [scanningJobs, setScanningJobs] = useState(false);
  const [jobScanResult, setJobScanResult] = useState<JobScanResult | null>(null);
  const [editingJobId, setEditingJobId] = useState("");
  const [jobDraft, setJobDraft] = useState<Partial<JobApplication>>({});
  const [savingJobId, setSavingJobId] = useState("");
  const [jobCalendarProposals, setJobCalendarProposals] = useState<
    JobCalendarProposal[]
  >([]);
  const [jobProposalsLoading, setJobProposalsLoading] = useState(true);
  const [resolvingJobProposalId, setResolvingJobProposalId] = useState("");

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

  const pendingJobCalendarProposals = useMemo(
    () =>
      jobCalendarProposals.filter((proposal) => proposal.status === "pending"),
    [jobCalendarProposals],
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

  async function loadJobs(showLoading = true) {
    if (showLoading) {
      setJobsLoading(true);
    }

    try {
      const response = await fetch(`${API_URL}/api/jobs`, {
        cache: "no-store",
      });

      if (!response.ok) {
        throw new Error("Could not load job applications.");
      }

      setJobs((await response.json()) as JobApplication[]);
    } catch (error) {
      if (showLoading) {
        setNotice(
          error instanceof Error
            ? error.message
            : "Could not load job applications.",
        );
      }
    } finally {
      if (showLoading) {
        setJobsLoading(false);
      }
    }
  }

  async function loadJobCalendarProposals(showLoading = true) {
    if (showLoading) {
      setJobProposalsLoading(true);
    }

    try {
      const response = await fetch(`${API_URL}/api/jobs/proposals`, {
        cache: "no-store",
      });

      if (!response.ok) {
        throw new Error("Could not load job reminder proposals.");
      }

      setJobCalendarProposals((await response.json()) as JobCalendarProposal[]);
    } catch (error) {
      if (showLoading) {
        setNotice(
          error instanceof Error
            ? error.message
            : "Could not load job reminder proposals.",
        );
      }
    } finally {
      if (showLoading) {
        setJobProposalsLoading(false);
      }
    }
  }

  useEffect(() => {
    void loadWorkspace();
    void loadGoogleStatus();
    void loadJobs();
    void loadJobCalendarProposals();
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
      const importMessage = data.message
        ? `${data.message} `
        : `Processed ${data.imported_count} upcoming Canvas deadline(s). `;
      const pastMessage = data.skipped_past_count
        ? `${data.skipped_past_count} past deadline(s) skipped. `
        : "";
      const proposalMessage = proposalCount
        ? `${proposalCount} change proposal(s) need review.`
        : "";

      setCanvasFocusCourseId(`canvas-${canvasCourseId}`);
      setNotice(`${importMessage}${pastMessage}${proposalMessage}`.trim());
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

      setNotice(
        action === "accept"
          ? `${proposal.candidate.title} updated to ${formatDate(
              proposal.candidate.due_at,
            )}. Calendar approval was reset because the deadline changed.`
          : `Kept the saved deadline for ${proposal.candidate.title}.`,
      );
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

  async function syncSelectedEventToGoogle(event: AcademicEvent) {
    if (!googleConnected) {
      setNotice("Connect Google Calendar before syncing deadlines.");
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
          body: JSON.stringify({ event_ids: [event.id] }),
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

      if (result.created.length > 0) {
        setNotice(`${event.title} was added to Google Calendar.`);
      } else if (result.updated.length > 0) {
        setNotice(`${event.title} was updated in Google Calendar.`);
      } else if (result.skipped.length > 0) {
        setNotice(
          result.skipped[0].reason ?? "This deadline could not be synced.",
        );
      } else if (result.failed.length > 0) {
        setNotice(result.failed[0].reason ?? "Google Calendar sync failed.");
      }
    } catch (error) {
      setNotice(
        error instanceof Error ? error.message : "Google Calendar sync failed.",
      );
    } finally {
      setSyncingGoogle(false);
    }
  }

  async function scanJobEmails() {
    setScanningJobs(true);
    setNotice("");
    setJobScanResult(null);

    try {
      const response = await fetch(`${API_URL}/api/jobs/scan`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ max_results: 25 }),
      });
      const data = (await response.json()) as JobScanResult | { detail?: string };

      if (!response.ok) {
        throw new Error(
          "detail" in data ? data.detail : "Could not scan job emails.",
        );
      }

      const result = data as JobScanResult;
      setJobScanResult(result);
      await Promise.all([loadJobs(false), loadJobCalendarProposals(false)]);

      const totalChanges = result.created.length + result.updated.length;
      const proposalCount = result.calendar_proposals?.length ?? 0;
      setNotice(
        totalChanges > 0
          ? `Job email scan complete: ${result.created.length} record(s) created, ${result.updated.length} record(s) updated, and ${proposalCount} reminder proposal(s) found.`
          : `Job email scan complete: ${result.skipped.length} message(s) skipped and ${proposalCount} new reminder proposal(s) found.`,
      );
    } catch (error) {
      setNotice(
        error instanceof Error ? error.message : "Could not scan job emails.",
      );
    } finally {
      setScanningJobs(false);
    }
  }

  function beginEditJob(job: JobApplication) {
    setEditingJobId(job.id);
    setJobDraft({
      company: job.company,
      role: job.role,
      status: job.status,
      next_action: job.next_action,
      requires_review: false,
    });
  }

  function cancelEditJob() {
    setEditingJobId("");
    setJobDraft({});
  }

  async function saveJob(job: JobApplication) {
    setSavingJobId(job.id);
    setNotice("");

    try {
      const response = await fetch(`${API_URL}/api/jobs/${job.id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          company: jobDraft.company?.trim() || job.company,
          role: jobDraft.role?.trim() || job.role,
          status: jobDraft.status || job.status,
          next_action: jobDraft.next_action?.trim() || job.next_action,
          requires_review: false,
        }),
      });
      const data = (await response.json()) as JobApplication | { detail?: string };

      if (!response.ok) {
        throw new Error(
          "detail" in data ? data.detail : "Could not save job application.",
        );
      }

      setJobs((current) =>
        current.map((item) =>
          item.id === job.id ? (data as JobApplication) : item,
        ),
      );
      setEditingJobId("");
      setJobDraft({});
      setNotice(`${job.company} application details were saved.`);
    } catch (error) {
      setNotice(
        error instanceof Error
          ? error.message
          : "Could not save job application.",
      );
    } finally {
      setSavingJobId("");
    }
  }

  async function approveJobCalendarProposal(proposal: JobCalendarProposal) {
    if (!googleConnected) {
      setNotice("Connect Google Calendar before approving a job reminder.");
      return;
    }

    setResolvingJobProposalId(proposal.id);
    setNotice("");

    try {
      const response = await fetch(
        `${API_URL}/api/jobs/proposals/${proposal.id}/approve`,
        { method: "POST" },
      );
      const data = (await response.json()) as
        | JobProposalApprovalResponse
        | { detail?: string };

      if (!response.ok) {
        throw new Error(
          "detail" in data
            ? data.detail
            : "Could not approve the job reminder.",
        );
      }

      const result = data as JobProposalApprovalResponse;
      setJobCalendarProposals((current) =>
        current.map((item) =>
          item.id === proposal.id ? result.proposal : item,
        ),
      );
      setNotice(
        `${proposal.title} was ${result.calendar.action} in Google Calendar.`,
      );
    } catch (error) {
      setNotice(
        error instanceof Error
          ? error.message
          : "Could not approve the job reminder.",
      );
    } finally {
      setResolvingJobProposalId("");
    }
  }

  async function dismissJobCalendarProposal(proposal: JobCalendarProposal) {
    setResolvingJobProposalId(proposal.id);
    setNotice("");

    try {
      const response = await fetch(
        `${API_URL}/api/jobs/proposals/${proposal.id}/dismiss`,
        { method: "POST" },
      );
      const data = (await response.json()) as JobCalendarProposal | { detail?: string };

      if (!response.ok) {
        throw new Error(
          "detail" in data
            ? data.detail
            : "Could not dismiss the job reminder.",
        );
      }

      const dismissed = data as JobCalendarProposal;
      setJobCalendarProposals((current) =>
        current.map((item) => (item.id === proposal.id ? dismissed : item)),
      );
      setNotice(`${proposal.title} was dismissed. Google Calendar was not changed.`);
    } catch (error) {
      setNotice(
        error instanceof Error
          ? error.message
          : "Could not dismiss the job reminder.",
      );
    } finally {
      setResolvingJobProposalId("");
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

  const allEvents = workspace?.events ?? [];
  const events = allEvents.filter(
    (event) =>
      canvasFocusCourseId === null || event.course_id === canvasFocusCourseId,
  );
  const selectedFilter =
    DEADLINE_FILTERS.find((filter) => filter.value === deadlineFilter) ??
    DEADLINE_FILTERS[1];
  const displayedEvents = events.filter((event) => {
    if (!event.due_at) return false;

    const dueAt = new Date(event.due_at);
    if (Number.isNaN(dueAt.getTime())) return false;
    if (deadlineFilter === "all") return true;

    const now = new Date();
    const end = new Date(now);
    end.setDate(end.getDate() + Number(deadlineFilter));

    return dueAt >= now && dueAt <= end;
  });
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
                <p className="font-bold text-amber-200">High workload detected</p>
                <p className="mt-1 text-sm text-amber-100/80">
                  {highWorkload.date}: {highWorkload.minutes} estimated minutes. {highWorkload.reason}
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
                    {selectedFilter.label} - {displayedEvents.length} displayed deadline{displayedEvents.length === 1 ? "" : "s"}
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

              <div className="mb-5 flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
                <label htmlFor="deadline-filter" className="text-sm font-semibold text-slate-300">
                  Show deadlines
                </label>
                <select
                  id="deadline-filter"
                  value={deadlineFilter}
                  onChange={(event) => setDeadlineFilter(event.target.value as DeadlineFilter)}
                  className="rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-slate-200 outline-none focus:border-cyan-400"
                >
                  {DEADLINE_FILTERS.map((filter) => (
                    <option key={filter.value} value={filter.value}>
                      {filter.label}
                    </option>
                  ))}
                </select>
              </div>

              {canvasFocusCourseId && (
                <div className="mb-5 flex flex-wrap items-center justify-between gap-3 rounded-xl border border-cyan-400/30 bg-cyan-400/10 px-3 py-2 text-sm text-cyan-100">
                  <span>Showing deadlines imported from the selected Canvas course.</span>
                  <button
                    onClick={() => setCanvasFocusCourseId(null)}
                    className="rounded-lg border border-cyan-300/40 px-2 py-1 text-xs font-semibold transition hover:bg-cyan-300 hover:text-slate-950"
                  >
                    Show all courses
                  </button>
                </div>
              )}

              <div className="space-y-3">
                {displayedEvents
                  .slice()
                  .sort((a, b) => (a.due_at ?? "9999").localeCompare(b.due_at ?? "9999"))
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
                            <span className={`rounded-full border px-2 py-0.5 text-xs font-semibold ${statusStyle(event.status)}`}>
                              {actionLabel(event.status)}
                            </span>
                            {event.approved && (
                              <span className="rounded-full border border-cyan-400/40 bg-cyan-400/10 px-2 py-0.5 text-xs font-semibold text-cyan-200">
                                Approved
                              </span>
                            )}
                          </div>
                          <p className="mt-1 text-sm text-slate-400">
                            {course?.code ?? event.course_id} - {formatDate(event.due_at)}
                          </p>
                        </div>
                        <ChevronRight className="shrink-0 text-slate-500" size={20} />
                      </button>
                    );
                  })}

                {displayedEvents.length === 0 && (
                  <div className="rounded-xl border border-dashed border-slate-700 p-5 text-sm text-slate-500">
                    No deadlines due {deadlineFilter === "all" ? "in this semester" : `in the next ${deadlineFilter} days`}.
                  </div>
                )}
              </div>
            </section>

            <section className="rounded-2xl border border-slate-800 bg-slate-900/70 p-5">
              <div className="mb-4 flex items-center gap-2">
                <CalendarDays className="text-cyan-300" size={20} />
                <div>
                  <h2 className="text-xl font-bold">Import from Canvas</h2>
                  <p className="text-sm text-slate-400">Pull official upcoming assignment due dates from Canvas.</p>
                </div>
              </div>

              {canvasCourses.length === 0 ? (
                <button
                  onClick={() => void loadCanvasCourses()}
                  disabled={canvasLoading}
                  className="inline-flex items-center gap-2 rounded-lg bg-cyan-400 px-4 py-2.5 font-bold text-slate-950 transition hover:bg-cyan-300 disabled:cursor-not-allowed disabled:opacity-60"
                >
                  {canvasLoading ? <Loader2 size={18} className="animate-spin" /> : <RefreshCw size={18} />}
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
                        {course.course_code ? `${course.course_code} - ${course.name}` : course.name}
                      </option>
                    ))}
                  </select>
                  <button
                    onClick={() => void importCanvasCourse()}
                    disabled={canvasImporting}
                    className="inline-flex items-center justify-center gap-2 rounded-lg border border-cyan-400/60 px-4 py-2.5 font-bold text-cyan-200 transition hover:bg-cyan-400 hover:text-slate-950 disabled:cursor-not-allowed disabled:opacity-60"
                  >
                    {canvasImporting ? <Loader2 size={18} className="animate-spin" /> : <CalendarDays size={18} />}
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
                  <p className="text-sm text-slate-400">Paste an announcement, email, or syllabus excerpt.</p>
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
                  <option value="instructor_announcement">Canvas announcement</option>
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
                onClick={() => void scanSource()}
                disabled={scanning || !sourceText.trim()}
                className="mt-3 inline-flex items-center gap-2 rounded-lg bg-cyan-400 px-4 py-2.5 font-bold text-slate-950 transition hover:bg-cyan-300 disabled:cursor-not-allowed disabled:opacity-60"
              >
                {scanning ? <Loader2 size={18} className="animate-spin" /> : <Sparkles size={18} />}
                {scanning ? "Scanning course update..." : "Scan for deadlines"}
              </button>
            </section>

            <section className="rounded-2xl border border-violet-400/30 bg-violet-400/5 p-5">
              <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
                <div className="flex gap-3">
                  <BriefcaseBusiness className="mt-0.5 shrink-0 text-violet-300" size={21} />
                  <div>
                    <h2 className="text-xl font-bold">Job applications</h2>
                    <p className="mt-1 max-w-2xl text-sm text-slate-400">
                      Scan Gmail read-only for recruiting-system emails. DueScope keeps the original source email and marks inferred statuses for review.
                    </p>
                  </div>
                </div>

                <div className="flex shrink-0 gap-2">
                  <button
                    onClick={() => void loadJobs(true)}
                    disabled={jobsLoading || scanningJobs}
                    className="rounded-lg border border-slate-700 p-2 text-slate-300 transition hover:border-violet-400 hover:text-violet-200 disabled:cursor-not-allowed disabled:opacity-60"
                    title="Refresh job applications"
                    aria-label="Refresh job applications"
                  >
                    <RefreshCw size={17} className={jobsLoading ? "animate-spin" : ""} />
                  </button>
                  <button
                    onClick={() => void scanJobEmails()}
                    disabled={scanningJobs}
                    className="inline-flex items-center justify-center gap-2 rounded-lg bg-violet-400 px-4 py-2.5 font-bold text-slate-950 transition hover:bg-violet-300 disabled:cursor-not-allowed disabled:opacity-60"
                  >
                    {scanningJobs ? <Loader2 size={18} className="animate-spin" /> : <BriefcaseBusiness size={18} />}
                    {scanningJobs ? "Scanning Gmail..." : "Scan for new job updates"}
                  </button>
                </div>
              </div>

              {jobScanResult && (
                <div className="mt-4 rounded-xl border border-violet-400/30 bg-slate-950/70 p-4 text-sm">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <p className="font-semibold text-violet-200">
                      Latest scan: {jobScanResult.matched_count} matching email{jobScanResult.matched_count === 1 ? "" : "s"}
                    </p>
                    <p className="text-xs text-slate-500">
                      {jobScanResult.created.length} created · {jobScanResult.updated.length} updated · {jobScanResult.calendar_proposals?.length ?? 0} reminders · {jobScanResult.skipped.length} skipped · {jobScanResult.errors.length} errors
                    </p>
                  </div>
                  <p className="mt-2 text-xs leading-5 text-slate-400">{jobScanResult.safety_note}</p>
                </div>
              )}

              <div className="mt-5 space-y-3">
                {jobsLoading ? (
                  <div className="flex items-center gap-2 rounded-xl border border-dashed border-slate-700 p-4 text-sm text-slate-400">
                    <Loader2 size={16} className="animate-spin" />
                    Loading job applications...
                  </div>
                ) : jobs.length === 0 ? (
                  <div className="rounded-xl border border-dashed border-slate-700 p-4 text-sm text-slate-500">
                    No job applications are tracked yet. Scan job emails to find messages from supported recruiting systems.
                  </div>
                ) : (
                  uniqueJobs(jobs).map((job) => {
                    const editing = editingJobId === job.id;
                    const saving = savingJobId === job.id;

                    return (
                      <article key={job.id} className="rounded-xl border border-slate-700 bg-slate-950/70 p-4">
                        {editing ? (
                          <div className="space-y-3">
                            <div className="grid gap-3 sm:grid-cols-2">
                              <label className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                                Company
                                <input
                                  value={jobDraft.company ?? ""}
                                  onChange={(event) => setJobDraft((current) => ({ ...current, company: event.target.value }))}
                                  className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-sm normal-case tracking-normal text-slate-100 outline-none focus:border-violet-400"
                                />
                              </label>
                              <label className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                                Role
                                <input
                                  value={jobDraft.role ?? ""}
                                  onChange={(event) => setJobDraft((current) => ({ ...current, role: event.target.value }))}
                                  className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-sm normal-case tracking-normal text-slate-100 outline-none focus:border-violet-400"
                                />
                              </label>
                            </div>
                            <label className="block text-xs font-semibold uppercase tracking-wide text-slate-500">
                              Status
                              <select
                                value={jobDraft.status ?? job.status}
                                onChange={(event) => setJobDraft((current) => ({ ...current, status: event.target.value as JobStatus }))}
                                className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-sm normal-case tracking-normal text-slate-100 outline-none focus:border-violet-400"
                              >
                                {JOB_STATUSES.map((status) => (
                                  <option key={status} value={status}>{actionLabel(status)}</option>
                                ))}
                              </select>
                            </label>
                            <label className="block text-xs font-semibold uppercase tracking-wide text-slate-500">
                              Next action
                              <input
                                value={jobDraft.next_action ?? ""}
                                onChange={(event) => setJobDraft((current) => ({ ...current, next_action: event.target.value }))}
                                className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-sm normal-case tracking-normal text-slate-100 outline-none focus:border-violet-400"
                              />
                            </label>
                            <div className="grid gap-2 sm:grid-cols-2">
                              <button
                                onClick={() => void saveJob(job)}
                                disabled={saving}
                                className="inline-flex items-center justify-center gap-2 rounded-lg bg-violet-400 px-3 py-2.5 text-sm font-bold text-slate-950 transition hover:bg-violet-300 disabled:cursor-not-allowed disabled:opacity-60"
                              >
                                {saving ? <Loader2 size={16} className="animate-spin" /> : <Check size={16} />}
                                Save review
                              </button>
                              <button
                                onClick={cancelEditJob}
                                disabled={saving}
                                className="inline-flex items-center justify-center gap-2 rounded-lg border border-slate-600 px-3 py-2.5 text-sm font-bold text-slate-200 transition hover:border-slate-400 hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-60"
                              >
                                <X size={16} />
                                Cancel
                              </button>
                            </div>
                          </div>
                        ) : (
                          <>
                            <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                              <div className="min-w-0">
                                <div className="flex flex-wrap items-center gap-2">
                                  <h3 className="font-bold text-slate-100">{job.company}</h3>
                                  <span className={`rounded-full border px-2 py-0.5 text-xs font-semibold ${jobStatusStyle(job.status)}`}>
                                    {actionLabel(job.status)}
                                  </span>
                                  {job.requires_review && (
                                    <span className="rounded-full border border-amber-400/40 bg-amber-400/10 px-2 py-0.5 text-xs font-semibold text-amber-200">
                                      Review needed
                                    </span>
                                  )}
                                </div>
                                <p className="mt-1 text-sm text-violet-200">{job.role}</p>
                              </div>
                              <button
                                onClick={() => beginEditJob(job)}
                                className="inline-flex items-center justify-center gap-2 rounded-lg border border-violet-400/50 px-3 py-2 text-sm font-bold text-violet-200 transition hover:bg-violet-400 hover:text-slate-950"
                              >
                                <Pencil size={15} />
                                Review
                              </button>
                            </div>
                            <div className="mt-3 rounded-lg border border-slate-800 bg-slate-900/70 p-3">
                              <p className="text-xs font-bold uppercase tracking-wider text-slate-500">Next action</p>
                              <p className="mt-1 text-sm text-slate-300">{job.next_action}</p>
                            </div>
                            <p className="mt-3 text-xs text-slate-500">Latest source: {formatDate(job.received_at)} · {job.source_sender}</p>
                            <p className="mt-1 text-sm text-slate-400">{job.source_subject}</p>
                            <p className="mt-3 line-clamp-3 text-sm leading-6 text-slate-500">{job.source_excerpt}</p>
                            <div className="mt-4 flex flex-wrap items-center gap-3">
                              <a
                                href={job.gmail_url}
                                target="_blank"
                                rel="noreferrer"
                                className="inline-flex items-center gap-2 text-sm font-semibold text-violet-200 transition hover:text-violet-100"
                              >
                                Open source email
                                <ExternalLink size={15} />
                              </a>
                              <span className="text-xs text-slate-600">Updated {formatDate(job.updated_at)}</span>
                            </div>
                          </>
                        )}
                      </article>
                    );
                  })
                )}
              </div>
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
                      <p className="mt-1 text-sm text-slate-400">Sync only deadlines you explicitly approve.</p>
                    </div>
                    <button
                      onClick={() => void loadGoogleStatus(true)}
                      disabled={googleStatusLoading}
                      className="rounded-lg border border-slate-700 p-2 text-slate-300 transition hover:border-emerald-400 hover:text-emerald-300 disabled:cursor-not-allowed disabled:opacity-60"
                      title="Refresh Google Calendar status"
                      aria-label="Refresh Google Calendar status"
                    >
                      <RefreshCw size={16} className={googleStatusLoading ? "animate-spin" : ""} />
                    </button>
                  </div>
                  <div className="mt-4 rounded-xl border border-slate-700 bg-slate-950/70 p-3">
                    <p className="text-xs font-bold uppercase tracking-wider text-slate-500">Connection status</p>
                    <p className={`mt-1 text-sm font-semibold ${googleConnected ? "text-emerald-300" : "text-amber-300"}`}>
                      {googleStatusLoading ? "Checking connection..." : googleConnected ? "Connected to Google Calendar" : "Not connected"}
                    </p>
                  </div>
                  {googleConnected ? (
                    <button
                      onClick={() => void syncApprovedToGoogle()}
                      disabled={syncingGoogle || approvedSyncableEvents.length === 0}
                      className="mt-3 inline-flex w-full items-center justify-center gap-2 rounded-lg bg-emerald-400 px-4 py-2.5 font-bold text-slate-950 transition hover:bg-emerald-300 disabled:cursor-not-allowed disabled:opacity-60"
                    >
                      {syncingGoogle ? <Loader2 size={18} className="animate-spin" /> : <CalendarCheck2 size={18} />}
                      {syncingGoogle ? "Syncing approved deadlines..." : `Sync ${approvedSyncableEvents.length} approved deadline${approvedSyncableEvents.length === 1 ? "" : "s"}`}
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
                    <p className="mt-3 text-sm text-slate-500">Approve a verified or updated deadline to enable sync.</p>
                  )}
                  {syncResult && (
                    <div className="mt-4 space-y-3">
                      {syncResult.created.length > 0 && (
                        <div className="rounded-xl border border-emerald-400/30 bg-emerald-400/10 p-3 text-sm text-emerald-100">
                          <p className="font-bold">Created: {syncItemSummary(syncResult.created)}</p>
                          {syncResult.created.map((item) => item.calendar_url ? (
                            <a key={item.event_id} href={item.calendar_url} target="_blank" rel="noreferrer" className="mt-1 block text-xs text-emerald-200 underline underline-offset-2">
                              Open {item.title} in Google Calendar
                            </a>
                          ) : null)}
                        </div>
                      )}
                      {syncResult.updated.length > 0 && (
                        <div className="rounded-xl border border-cyan-400/30 bg-cyan-400/10 p-3 text-sm text-cyan-100">
                          <p className="font-bold">Updated: {syncItemSummary(syncResult.updated)}</p>
                          {syncResult.updated.map((item) => item.calendar_url ? (
                            <a key={item.event_id} href={item.calendar_url} target="_blank" rel="noreferrer" className="mt-1 block text-xs text-cyan-200 underline underline-offset-2">
                              Open {item.title} in Google Calendar
                            </a>
                          ) : null)}
                        </div>
                      )}
                      {syncResult.skipped.length > 0 && (
                        <div className="rounded-xl border border-amber-400/30 bg-amber-400/10 p-3 text-sm text-amber-100">
                          <p className="font-bold">Skipped deadlines</p>
                          {syncResult.skipped.map((item) => <p key={item.event_id} className="mt-1 text-xs">{item.title}: {item.reason ?? "Not eligible for sync."}</p>)}
                        </div>
                      )}
                      {syncResult.failed.length > 0 && (
                        <div className="rounded-xl border border-rose-400/30 bg-rose-400/10 p-3 text-sm text-rose-100">
                          <p className="font-bold">Sync errors</p>
                          {syncResult.failed.map((item) => <p key={item.event_id} className="mt-1 text-xs">{item.title}: {item.reason ?? "Unknown sync error."}</p>)}
                        </div>
                      )}
                    </div>
                  )}
                </div>
              </div>
            </section>

            <section className="rounded-2xl border border-violet-400/30 bg-violet-400/5 p-5">
              <div className="flex items-start justify-between gap-3">
                <div className="flex gap-3">
                  <BriefcaseBusiness className="mt-0.5 shrink-0 text-violet-300" size={20} />
                  <div>
                    <h2 className="text-xl font-bold">Job reminders to review</h2>
                    <p className="mt-1 text-sm text-slate-400">
                      Gmail creates reminders only from explicit dates. Approving a proposal is the only action that changes Google Calendar.
                    </p>
                  </div>
                </div>
                <button
                  onClick={() => void loadJobCalendarProposals(true)}
                  disabled={jobProposalsLoading || Boolean(resolvingJobProposalId)}
                  className="rounded-lg border border-slate-700 p-2 text-slate-300 transition hover:border-violet-400 hover:text-violet-200 disabled:cursor-not-allowed disabled:opacity-60"
                  title="Refresh job reminder proposals"
                  aria-label="Refresh job reminder proposals"
                >
                  <RefreshCw size={16} className={jobProposalsLoading ? "animate-spin" : ""} />
                </button>
              </div>

              <div className="mt-4 space-y-4">
                {jobProposalsLoading ? (
                  <div className="flex items-center gap-2 rounded-xl border border-dashed border-slate-700 p-4 text-sm text-slate-400">
                    <Loader2 size={16} className="animate-spin" />
                    Loading job reminders...
                  </div>
                ) : pendingJobCalendarProposals.length === 0 ? (
                  <div className="rounded-xl border border-dashed border-slate-700 p-4 text-sm text-slate-500">
                    No pending job reminders. Scan job emails to detect explicit assessment deadlines or interview scheduling deadlines.
                  </div>
                ) : (
                  pendingJobCalendarProposals.map((proposal) => {
                    const resolving = resolvingJobProposalId === proposal.id;
                    return (
                      <article key={proposal.id} className="rounded-xl border border-violet-400/30 bg-slate-950/70 p-4">
                        <div className="flex flex-wrap items-start justify-between gap-3">
                          <div>
                            <p className="font-semibold text-violet-100">{proposal.title}</p>
                            <p className="mt-1 text-sm text-violet-200">{proposal.company} · {proposal.role}</p>
                          </div>
                          <span className={`rounded-full border px-2 py-0.5 text-xs font-semibold ${jobProposalStyle(proposal.kind)}`}>
                            {actionLabel(proposal.kind)}
                          </span>
                        </div>
                        <div className="mt-3 grid gap-2 text-sm sm:grid-cols-2">
                          <div className="rounded-lg border border-slate-800 bg-slate-900/70 p-3">
                            <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Starts</p>
                            <p className="mt-1 text-slate-200">{formatDate(proposal.starts_at)}</p>
                          </div>
                          <div className="rounded-lg border border-violet-400/30 bg-violet-400/10 p-3">
                            <p className="text-xs font-semibold uppercase tracking-wide text-violet-300">Deadline or event end</p>
                            <p className="mt-1 text-violet-100">{formatDate(proposal.ends_at)}</p>
                          </div>
                        </div>
                        <div className="mt-3 rounded-lg border border-slate-700 bg-slate-950 p-3">
                          <p className="text-xs font-bold uppercase tracking-wider text-slate-500">Source evidence</p>
                          <p className="mt-1 text-sm leading-6 text-slate-300">&quot;{proposal.source_excerpt}&quot;</p>
                        </div>
                        <a href={proposal.gmail_url} target="_blank" rel="noreferrer" className="mt-3 inline-flex items-center gap-2 text-sm font-semibold text-violet-200 transition hover:text-violet-100">
                          Open source email
                          <ExternalLink size={15} />
                        </a>
                        <div className="mt-4 grid gap-2 sm:grid-cols-2">
                          <button
                            onClick={() => void approveJobCalendarProposal(proposal)}
                            disabled={resolving || !googleConnected}
                            className="inline-flex items-center justify-center gap-2 rounded-lg bg-violet-400 px-3 py-2.5 text-sm font-bold text-slate-950 transition hover:bg-violet-300 disabled:cursor-not-allowed disabled:opacity-60"
                            title={googleConnected ? "Approve and add this reminder to Google Calendar" : "Connect Google Calendar before approving a reminder"}
                          >
                            {resolving ? <Loader2 size={16} className="animate-spin" /> : <CalendarCheck2 size={16} />}
                            Approve and add to Google Calendar
                          </button>
                          <button
                            onClick={() => void dismissJobCalendarProposal(proposal)}
                            disabled={resolving}
                            className="inline-flex items-center justify-center gap-2 rounded-lg border border-slate-600 px-3 py-2.5 text-sm font-bold text-slate-200 transition hover:border-slate-400 hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-60"
                          >
                            <X size={16} />
                            Dismiss
                          </button>
                        </div>
                        {!googleConnected && (
                          <button onClick={connectGoogleCalendar} className="mt-3 inline-flex w-full items-center justify-center gap-2 rounded-lg border border-emerald-400/60 px-3 py-2.5 text-sm font-bold text-emerald-200 transition hover:bg-emerald-400 hover:text-slate-950">
                            <Unplug size={16} />
                            Connect Google to approve reminders
                          </button>
                        )}
                      </article>
                    );
                  })
                )}
              </div>

              {!jobProposalsLoading && jobCalendarProposals.some((proposal) => proposal.status === "approved") && (
                <div className="mt-4 rounded-xl border border-emerald-400/30 bg-emerald-400/10 p-3 text-sm text-emerald-100">
                  <p className="font-semibold">Approved job reminders</p>
                  {jobCalendarProposals.filter((proposal) => proposal.status === "approved").map((proposal) => (
                    <div key={proposal.id} className="mt-2 flex flex-wrap items-center justify-between gap-2">
                      <span>{proposal.title}</span>
                      {proposal.google_calendar_url && (
                        <a href={proposal.google_calendar_url} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1 text-xs font-semibold text-emerald-200 underline underline-offset-2">
                          Open in Calendar
                          <ExternalLink size={13} />
                        </a>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </section>

            <section className="rounded-2xl border border-amber-400/30 bg-amber-300/5 p-5">
              <div className="flex items-start gap-2">
                <ShieldCheck className="mt-0.5 shrink-0 text-amber-300" size={20} />
                <div>
                  <h2 className="text-xl font-bold">Deadline proposals</h2>
                  <p className="mt-1 text-sm text-slate-400">A changed date never overwrites your saved deadline automatically.</p>
                </div>
              </div>
              <div className="mt-4 space-y-4">
                {proposals.map((proposal) => {
                  const savedEvent = allEvents.find((event) => event.id === proposal.event_id);
                  const course = savedEvent ? coursesById[savedEvent.course_id] : undefined;
                  const resolving = resolvingProposalId === proposal.id;
                  return (
                    <article key={proposal.id} className="rounded-xl border border-amber-400/30 bg-slate-950/70 p-4">
                      <p className="font-semibold text-amber-100">{proposal.candidate.title}</p>
                      <p className="mt-1 text-xs text-slate-400">{course?.code ?? savedEvent?.course_id ?? "Course"} - review required</p>
                      <div className="mt-3 grid gap-2 text-sm sm:grid-cols-2">
                        <div className="rounded-lg border border-slate-800 p-3">
                          <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Saved deadline</p>
                          <p className="mt-1 text-slate-200">{formatDate(savedEvent?.due_at)}</p>
                        </div>
                        <div className="rounded-lg border border-amber-400/30 bg-amber-300/10 p-3">
                          <p className="text-xs font-semibold uppercase tracking-wide text-amber-300">Proposed deadline</p>
                          <p className="mt-1 text-amber-100">{formatDate(proposal.candidate.due_at)}</p>
                        </div>
                      </div>
                      <p className="mt-3 text-sm leading-6 text-slate-400">{proposal.message}</p>
                      <div className="mt-3 rounded-lg border border-slate-700 bg-slate-950 p-3">
                        <p className="text-xs font-bold uppercase tracking-wider text-slate-500">Proposed evidence</p>
                        <p className="mt-1 text-sm leading-6 text-slate-300">&quot;{proposal.candidate.source_excerpt}&quot;</p>
                      </div>
                      {proposal.candidate.needs_review_reason && (
                        <div className="mt-3 rounded-lg border border-rose-400/30 bg-rose-400/10 p-3 text-sm text-rose-100">{proposal.candidate.needs_review_reason}</div>
                      )}
                      <div className="mt-4 grid gap-2 sm:grid-cols-2">
                        <button onClick={() => void resolveProposal(proposal, "accept")} disabled={resolving} className="inline-flex items-center justify-center gap-2 rounded-lg bg-amber-300 px-3 py-2.5 text-sm font-bold text-slate-950 transition hover:bg-amber-200 disabled:cursor-not-allowed disabled:opacity-60">
                          {resolving ? <Loader2 size={16} className="animate-spin" /> : <Check size={16} />}
                          Accept change
                        </button>
                        <button onClick={() => void resolveProposal(proposal, "reject")} disabled={resolving} className="inline-flex items-center justify-center gap-2 rounded-lg border border-slate-600 px-3 py-2.5 text-sm font-bold text-slate-200 transition hover:border-slate-400 hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-60">
                          <X size={16} />
                          Keep saved date
                        </button>
                      </div>
                    </article>
                  );
                })}
                {proposals.length === 0 && (
                  <div className="rounded-xl border border-dashed border-slate-700 p-4 text-sm text-slate-500">No proposed deadline changes are waiting for review.</div>
                )}
              </div>
            </section>

            <section className="rounded-2xl border border-slate-800 bg-slate-900/70 p-5">
              <h2 className="text-xl font-bold">Changes to review</h2>
              <div className="mt-4 space-y-3">
                {(workspace?.changes ?? []).map((change) => (
                  <button key={`${change.event_id}-${change.kind}`} onClick={() => {
                    const event = allEvents.find((item) => item.id === change.event_id);
                    if (event) setSelectedEvent(event);
                  }} className="w-full rounded-xl border border-slate-800 bg-slate-950/70 p-3 text-left text-sm transition hover:border-cyan-400/60">
                    <p className="font-semibold capitalize text-cyan-200">{actionLabel(change.kind)}</p>
                    <p className="mt-1 text-slate-400">{change.message}</p>
                  </button>
                ))}
                {(workspace?.changes ?? []).length === 0 && (
                  <div className="rounded-xl border border-dashed border-slate-700 p-4 text-sm text-slate-500">No changes need review right now.</div>
                )}
              </div>
            </section>

            <section className="rounded-2xl border border-slate-800 bg-slate-900/70 p-5">
              <h2 className="text-xl font-bold">Evidence panel</h2>
              {selectedEvent ? (
                <div className="mt-4 space-y-4">
                  <div>
                    <p className="text-sm font-bold">{selectedEvent.title}</p>
                    <p className="mt-1 text-sm text-slate-400">{coursesById[selectedEvent.course_id]?.code ?? selectedEvent.course_id} - {formatDate(selectedEvent.due_at)}</p>
                  </div>
                  <div className="rounded-xl border border-slate-700 bg-slate-950 p-3">
                    <p className="mb-2 text-xs font-bold uppercase tracking-wider text-slate-500">Source evidence</p>
                    <p className="text-sm leading-6 text-slate-300">&quot;{selectedEvent.source_excerpt}&quot;</p>
                  </div>
                  {selectedEvent.history.length > 0 && (
                    <div>
                      <p className="mb-2 text-xs font-bold uppercase tracking-wider text-slate-500">Deadline history</p>
                      <div className="space-y-2">
                        {selectedEvent.history.map((version, index) => (
                          <div key={`${version.source_id}-${index}`} className="rounded-lg border border-slate-800 bg-slate-950/70 p-3 text-sm">
                            <div className="flex items-center justify-between gap-3">
                              <span className="font-medium">{formatDate(version.due_at)}</span>
                              <span className={version.is_current ? "text-emerald-300" : "text-slate-500"}>{version.is_current ? "Current" : "Previous"}</span>
                            </div>
                            <p className="mt-1 text-xs text-slate-500">{version.reason}</p>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                  {selectedEvent.needs_review_reason && (
                    <div className="rounded-xl border border-rose-400/30 bg-rose-400/10 p-3 text-sm text-rose-100">{selectedEvent.needs_review_reason}</div>
                  )}
                  <button onClick={() => void toggleApproval(selectedEvent)} disabled={! ["verified", "updated"].includes(selectedEvent.status)} className="inline-flex w-full items-center justify-center gap-2 rounded-lg border border-cyan-400/60 px-4 py-2.5 font-bold text-cyan-200 transition hover:bg-cyan-400 hover:text-slate-950 disabled:cursor-not-allowed disabled:border-slate-700 disabled:text-slate-600">
                    <Check size={17} />
                    {selectedEvent.approved ? "Remove approval" : "Approve for export and sync"}
                  </button>
                  {selectedEvent.approved && googleConnected && (
                    <button onClick={() => void syncSelectedEventToGoogle(selectedEvent)} disabled={syncingGoogle} className="inline-flex w-full items-center justify-center gap-2 rounded-lg border border-emerald-400/60 px-4 py-2.5 font-bold text-emerald-200 transition hover:bg-emerald-400 hover:text-slate-950 disabled:cursor-not-allowed disabled:opacity-60">
                      {syncingGoogle ? <Loader2 size={17} className="animate-spin" /> : <CalendarCheck2 size={17} />}
                      Sync this deadline to Google
                    </button>
                  )}
                  {selectedEvent.approved && !googleConnected && (
                    <button onClick={connectGoogleCalendar} className="inline-flex w-full items-center justify-center gap-2 rounded-lg border border-emerald-400/60 px-4 py-2.5 font-bold text-emerald-200 transition hover:bg-emerald-400 hover:text-slate-950">
                      <Unplug size={17} />
                      Connect Google to sync
                    </button>
                  )}
                </div>
              ) : (
                <div className="mt-4 rounded-xl border border-dashed border-slate-700 p-5 text-sm text-slate-500">Select a deadline to inspect its evidence, history, and export approval.</div>
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
