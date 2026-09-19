import Link from "next/link";
import { ArrowLeft, CheckCircle2, LockKeyhole, MailCheck, ShieldCheck } from "lucide-react";

const safeguards = [
  {
    icon: ShieldCheck,
    title: "Review before changes",
    description:
      "DueScope treats extracted dates as suggestions. A conflicting academic deadline becomes a proposal for you to accept or reject.",
  },
  {
    icon: MailCheck,
    title: "Read-only Gmail handling",
    description:
      "The job workflow is designed to read relevant messages for status and scheduling information. It does not send, archive, label, modify, or delete Gmail messages.",
  },
  {
    icon: LockKeyhole,
    title: "Explicit Calendar approval",
    description:
      "DueScope does not create or update Google Calendar events until you approve the specific proposed action.",
  },
];

export default function PrivacyPage() {
  return (
    <main className="min-h-screen bg-slate-950 text-slate-100">
      <div className="mx-auto max-w-3xl px-6 py-10 sm:px-10">
        <Link
          href="/"
          className="inline-flex items-center gap-2 text-sm font-medium text-cyan-300 transition hover:text-cyan-200"
        >
          <ArrowLeft className="h-4 w-4" />
          Back to DueScope
        </Link>

        <h1 className="mt-10 text-4xl font-bold tracking-tight text-white">
          Privacy and safety in the DueScope beta
        </h1>

        <p className="mt-5 text-lg leading-8 text-slate-300">
          DueScope is built around a simple rule: automation may identify useful
          information, but the student remains in control of saved deadlines and
          Calendar changes.
        </p>

        <section className="mt-10 space-y-5">
          {safeguards.map((item) => {
            const Icon = item.icon;

            return (
              <article
                key={item.title}
                className="rounded-xl border border-slate-800 bg-slate-900/50 p-6"
              >
                <Icon className="h-6 w-6 text-cyan-300" />
                <h2 className="mt-4 text-lg font-semibold text-white">
                  {item.title}
                </h2>
                <p className="mt-2 leading-7 text-slate-300">{item.description}</p>
              </article>
            );
          })}
        </section>

        <section className="mt-10 rounded-xl border border-amber-400/30 bg-amber-400/10 p-6">
          <h2 className="flex items-center gap-2 font-semibold text-amber-100">
            <CheckCircle2 className="h-5 w-5" />
            Current beta scope
          </h2>
          <p className="mt-3 leading-7 text-amber-50/90">
            The public site provides a seeded demonstration workspace. Real
            third-party account connections are being prepared for an invite-only
            beta and should not be treated as open public account functionality
            yet.
          </p>
        </section>

        <p className="mt-10 text-sm leading-6 text-slate-400">
          Do not enter sensitive personal, academic, employment, or credential
          information into a shared demonstration environment.
        </p>
      </div>
    </main>
  );
}
