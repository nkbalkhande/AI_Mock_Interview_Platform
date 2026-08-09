"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { CheckCircle2, Clock, RefreshCw } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import {
  usePracticeResult,
  useSubmitInterview,
} from "@/features/interviews/hooks";
import { ROUTES } from "@/lib/constants";

export default function PracticeResultPage() {
  const params = useParams<{ sessionId: string }>();
  const result = usePracticeResult(params.sessionId);
  const retryEvaluation = useSubmitInterview(params.sessionId);

  if (result.isError) {
    return (
      <StateCard
        icon={<RefreshCw className="h-7 w-7" />}
        title="Report unavailable"
        message={result.error?.message || "We could not load this result."}
        action={<Button onClick={() => result.refetch()}>Try again</Button>}
      />
    );
  }

  if (result.isLoading || result.data?.status === "pending") {
    return (
      <StateCard
        icon={<Clock className="h-7 w-7 animate-pulse" />}
        title="Preparing your practice report"
        message="The AI evaluation is still running. This page updates automatically."
      />
    );
  }

  if (result.data?.status === "retryable") {
    return (
      <StateCard
        icon={<RefreshCw className="h-7 w-7" />}
        title="Evaluation needs another attempt"
        message={
          retryEvaluation.error?.message ||
          "The previous evaluation did not finish. Your interview is saved and can be evaluated again."
        }
        action={
          <Button
            disabled={retryEvaluation.isPending}
            onClick={() => retryEvaluation.mutate()}
          >
            <RefreshCw
              className={`mr-2 h-4 w-4 ${
                retryEvaluation.isPending ? "animate-spin" : ""
              }`}
            />
            {retryEvaluation.isPending
              ? "Retrying evaluation..."
              : "Retry evaluation"}
          </Button>
        }
      />
    );
  }

  if (!result.data) {
    return null;
  }

  const report = result.data;
  return (
    <div className="mx-auto flex w-full max-w-5xl flex-col gap-6">
      <header className="flex flex-col gap-3 rounded-xl border bg-card p-6 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <p className="text-sm text-muted-foreground">
            {report.practice_type === "ROLE_BASED"
              ? report.role_name || "Custom role"
              : "JD-based practice"}
          </p>
          <h1 className="text-2xl font-semibold">Practice Interview Report</h1>
          <p className="mt-1 text-sm text-muted-foreground">{report.summary}</p>
        </div>
        <div className="text-left sm:text-right">
          <p className="text-4xl font-bold text-primary">
            {formatScore(report.overall_score)}
          </p>
          <p className="text-xs text-muted-foreground">Overall score / 10</p>
        </div>
      </header>

      <section className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <ScoreCard label="Technical" value={report.technical_score} />
        <ScoreCard label="Problem solving" value={report.reasoning_score} />
        <ScoreCard label="Communication" value={report.communication_score} />
        <ScoreCard
          label="Project knowledge"
          value={report.project_knowledge_score}
        />
      </section>

      <section className="grid gap-4 lg:grid-cols-3">
        <FeedbackCard title="Strengths" items={report.strengths} />
        <FeedbackCard title="Weak areas" items={report.weaknesses} />
        <FeedbackCard
          title="Areas to improve"
          items={report.improvement_areas}
        />
      </section>

      <Card>
        <CardHeader>
          <h2 className="font-semibold">Skill breakdown</h2>
        </CardHeader>
        <CardContent>
          {report.skill_scores.length ? (
            <div className="grid gap-3 sm:grid-cols-2">
              {report.skill_scores.map((skill) => (
                <div key={skill.skill_name} className="rounded-lg border p-4">
                  <div className="flex items-center justify-between gap-3">
                    <h3 className="font-medium">{skill.skill_name}</h3>
                    <span className="font-semibold">
                      {skill.score}/{skill.max_score}
                    </span>
                  </div>
                  {skill.strength ? (
                    <p className="mt-2 text-sm text-muted-foreground">
                      {skill.strength}
                    </p>
                  ) : null}
                  {skill.improvement_area ? (
                    <p className="mt-1 text-sm text-amber-700 dark:text-amber-300">
                      Improve: {skill.improvement_area}
                    </p>
                  ) : null}
                  {skill.evidence.length ? (
                    <div className="mt-3">
                      <p className="text-xs font-medium">Evidence</p>
                      <ul className="mt-1 list-disc space-y-1 pl-5 text-xs text-muted-foreground">
                        {skill.evidence.map((item) => (
                          <li key={item}>{item}</li>
                        ))}
                      </ul>
                    </div>
                  ) : null}
                </div>
              ))}
            </div>
          ) : (
            <p className="text-sm text-muted-foreground">
              No individual skill scores were produced for this session.
            </p>
          )}
        </CardContent>
      </Card>

      <div className="flex justify-end">
        <Button asChild>
          <Link href={ROUTES.candidate.dashboard}>
            <CheckCircle2 className="mr-2 h-4 w-4" /> Back to dashboard
          </Link>
        </Button>
      </div>
    </div>
  );
}

function ScoreCard({ label, value }: { label: string; value: number | null }) {
  return (
    <Card>
      <CardContent className="pt-6">
        <p className="text-sm text-muted-foreground">{label}</p>
        <p className="mt-1 text-2xl font-semibold">{formatScore(value)}</p>
      </CardContent>
    </Card>
  );
}

function FeedbackCard({ title, items }: { title: string; items: string[] }) {
  return (
    <Card>
      <CardHeader><h2 className="font-semibold">{title}</h2></CardHeader>
      <CardContent>
        {items.length ? (
          <ul className="list-disc space-y-2 pl-5 text-sm text-muted-foreground">
            {items.map((item) => <li key={item}>{item}</li>)}
          </ul>
        ) : (
          <p className="text-sm text-muted-foreground">No items reported.</p>
        )}
      </CardContent>
    </Card>
  );
}

function StateCard({
  icon,
  title,
  message,
  action,
}: {
  icon: React.ReactNode;
  title: string;
  message: string;
  action?: React.ReactNode;
}) {
  return (
    <div className="mx-auto grid min-h-[50vh] max-w-lg place-items-center">
      <Card className="w-full">
        <CardContent className="flex flex-col items-center gap-3 py-12 text-center">
          <span className="text-primary">{icon}</span>
          <h1 className="text-xl font-semibold">{title}</h1>
          <p className="text-sm text-muted-foreground">{message}</p>
          {action}
        </CardContent>
      </Card>
    </div>
  );
}

function formatScore(value: number | null) {
  return value == null ? "—" : value.toFixed(1);
}