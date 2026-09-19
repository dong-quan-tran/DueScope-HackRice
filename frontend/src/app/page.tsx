import Link from "next/link";
import {
  ArrowRight,
  CalendarCheck,
  FileSearch,
  MailCheck,
  ShieldCheck,
} from "lucide-react";

const workflow = [
  {
    icon: FileSearch,
    title: "Collect evidence",
    description:
      "Bring together deadlines from Canvas, course updates, and job-related emails with the original source attached.",
  },
  {
    icon: ShieldCheck,
    title: "Review changes",
    description:
      "A changed date becomes a review proposal. DueScope never silently replaces a saved deadline.",
  },
  {
    icon: CalendarCheck,
    title: "Approve calendar actions",
    description:
      "Google Calendar changes happen only after you explicitly approve an eligible reminder or deadline.",
  },
];

export default function HomePage() {
  return (
    <main className="min-h-screen bg-slate-950 text-slate-100">
      <section className="mx-auto flex min-h-screen max-w-6xl flex-col px-6 py-8 sm:px-10">
        <nav className="flex items-center justify-between">
          <Link href="/" className="text-xl font-bold tracking-tight text-white">
            Due<span className="text-cyan-400">Scope</span>
          </Link>
          <div className="flex items-center gap-4 text-sm">
            <Link
              href="/privacy"
              className="text-slate-300 transition hover:text-white"
            >
              Privacy
            </Link>
            <Link
              href="/demo"
              className="rounded-lg bg-cyan-400 px-4 py-2 font-semibold text-slate-950 transition hover:bg-cyan-300"
            >
              Try the demo
            </Link>
          </div>
        </nav>

        <div className="grid flex-1 items-center gap-12 py-20 lg:grid-cols-[1.1fr_0.9fr]">
          <div>
            <p className="mb-5 inline-flex items-center gap-2 rounded-full border border-cyan-400/30 bg-cyan-400/10 px-3 py-1 text-sm font-medium text-cyan-200">
              <ShieldCheck className="h-4 w-4" />
              Evidence-backed student productivity
            </p>

            <h1 className="max-w-3xl text-4xl font-bold tracking-tight text-white sm:text-6xl">
              Keep up with deadlines without giving automation control.
            </h1>

            <p className="mt-6 max-w-2xl text-lg leading-8 text-slate-300">
              DueScope helps students track academic deadlines and job opportunities
              from Canvas, course updates, and Gmail—while keeping source evidence
              visible and calendar actions under user control.
            </p>

            <div className="mt-8 flex flex-wrap gap-4">
              <Link
                href="/demo"
                className="inline-flex items-center gap-2 rounded-lg bg-cyan-400 px-5 py-3 font-semibold text-slate-950 transition hover:bg-cyan-300"
              >
                Explore the interactive demo
                <ArrowRight className="h-4 w-4" />
              </Link>
              <Link
                href="/privacy"
                className="inline-flex items-center gap-2 rounded-lg border border-slate-700 px-5 py-3 font-semibold text-slate-100 transition hover:border-slate-500 hover:bg-slate-900"
              >
                How your data stays controlled
              </Link>
            </div>

            <p className="mt-5 text-sm text-slate-400">
              Public beta demo: no Canvas, Gmail, or Google account is required to explore the workflow.
            </p>
          </div>

          <div className="rounded-2xl border border-slate-700 bg-slate-900/70 p-6 shadow-2xl shadow-cyan-950/20">
            <div className="flex items-center gap-3 border-b border-slate-800 pb-5">
              <div className="rounded-lg bg-cyan-400/15 p-2 text-cyan-300">
                <CalendarCheck className="h-5 w-5" />
              </div>
              <div>
                <p className="font-semibold text-white">Review-first workflow</p>
                <p className="text-sm text-slate-400">No silent deadline or calendar changes</p>
              </div>
            </div>

            <div className="space-y-4 py-5">
              <div className="rounded-xl border border-slate-700 bg-slate-950/60 p-4">
                <div className="flex items-center gap-2 text-sm font-medium text-cyan-200">
                  <FileSearch className="h-4 w-4" />
                  New course update found
                </div>
                <p className="mt-2 text-sm text-slate-300">
                  “GC-MS Lab Report deadline is extended to Monday at 5:00 PM.”
                </p>
              </div>

              <div className="rounded-xl border border-amber-400/30 bg-amber-400/10 p-4">
                <p className="text-sm font-semibold text-amber-200">
                  Review required: deadline changed
                </p>
                <p className="mt-1 text-sm text-slate-300">
                  Your existing deadline is preserved until you accept or reject the proposal.
                </p>
              </div>

              <div className="rounded-xl border border-emerald-400/30 bg-emerald-400/10 p-4">
                <div className="flex items-center gap-2 text-sm font-semibold text-emerald-200">
                  <MailCheck className="h-4 w-4" />
                  Gmail stays read-only
                </div>
                <p className="mt-1 text-sm text-slate-300">
                  Scheduling deadlines can be proposed, but no Calendar event is created without approval.
                </p>
              </div>
            </div>
          </div>
        </div>

        <section className="grid gap-4 pb-8 md:grid-cols-3">
          {workflow.map((item) => {
            const Icon = item.icon;

            return (
              <article
                key={item.title}
                className="rounded-xl border border-slate-800 bg-slate-900/40 p-5"
              >
                <Icon className="mb-4 h-5 w-5 text-cyan-300" />
                <h2 className="font-semibold text-white">{item.title}</h2>
                <p className="mt-2 text-sm leading-6 text-slate-400">
                  {item.description}
                </p>
              </article>
            );
          })}
        </section>
      </section>
    </main>
  );
}
