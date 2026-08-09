import Link from "next/link";
import { ArrowRight, FileEdit, Sparkles } from "lucide-react";

import { Card } from "@/components/ui/card";
import { ROUTES } from "@/lib/constants";

/**
 * Two primary CTAs to launch a practice interview.
 *
 * The dashboard task explicitly scopes this to *navigating* to the JD- or
 * Role-based practice flows; the flows themselves (JD paste, role picker,
 * interview engine) land in follow-up work.
 */
export function QuickActionsSection() {
  return (
    <div className="grid gap-4 md:grid-cols-2">
      <Link
        href={ROUTES.candidate.interviewsJdBased}
        className="group focus:outline-none"
      >
        <Card className="relative overflow-hidden border-primary/30 bg-gradient-to-br from-primary/10 via-transparent to-transparent p-5 transition-shadow group-hover:shadow-md group-focus-visible:ring-2 group-focus-visible:ring-ring">
          <div className="flex items-start gap-4">
            <div className="grid h-11 w-11 shrink-0 place-items-center rounded-lg bg-primary text-primary-foreground">
              <FileEdit className="h-5 w-5" />
            </div>
            <div className="min-w-0 flex-1">
              <h3 className="text-base font-semibold text-foreground">
                Start JD Based Interview
              </h3>
              <p className="mt-1 text-sm text-muted-foreground">
                Paste a job description and get an AI interview tailored to
                the role + your resume.
              </p>
            </div>
            <ArrowRight className="h-5 w-5 shrink-0 text-primary transition-transform group-hover:translate-x-0.5" />
          </div>
        </Card>
      </Link>

      <Link
        href={ROUTES.candidate.interviewsRoleBased}
        className="group focus:outline-none"
      >
        <Card className="relative overflow-hidden border-primary/30 bg-gradient-to-br from-primary/10 via-transparent to-transparent p-5 transition-shadow group-hover:shadow-md group-focus-visible:ring-2 group-focus-visible:ring-ring">
          <div className="flex items-start gap-4">
            <div className="grid h-11 w-11 shrink-0 place-items-center rounded-lg bg-primary text-primary-foreground">
              <Sparkles className="h-5 w-5" />
            </div>
            <div className="min-w-0 flex-1">
              <h3 className="text-base font-semibold text-foreground">
                Start Role Based Interview
              </h3>
              <p className="mt-1 text-sm text-muted-foreground">
                Pick a target role — AI Engineer, Backend, Data Scientist…
                — and start a practice round.
              </p>
            </div>
            <ArrowRight className="h-5 w-5 shrink-0 text-primary transition-transform group-hover:translate-x-0.5" />
          </div>
        </Card>
      </Link>
    </div>
  );
}
