import type { CurrentQuestion } from "@/features/interviews/types";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { cn } from "@/lib/utils";

const TYPE_LABELS: Record<string, string> = {
  TECHNICAL: "Technical",
  PROJECT: "Project",
  BEHAVIORAL: "Behavioral",
  CODING: "Coding",
  SYSTEM_DESIGN: "System design",
  FOLLOW_UP: "Follow-up",
};

const TYPE_VARIANTS: Record<
  string,
  "default" | "secondary" | "success" | "warning" | "outline"
> = {
  TECHNICAL: "default",
  PROJECT: "secondary",
  BEHAVIORAL: "secondary",
  CODING: "warning",
  SYSTEM_DESIGN: "default",
  FOLLOW_UP: "outline",
};

interface QuestionCardProps {
  question: CurrentQuestion;
  className?: string;
}

export function QuestionCard({ question, className }: QuestionCardProps) {
  return (
    <Card className={cn("border-border", className)}>
      <CardHeader className="flex flex-col gap-2 pb-3">
        <div className="flex flex-wrap items-center gap-2">
          <Badge variant={TYPE_VARIANTS[question.question_type] ?? "default"}>
            {TYPE_LABELS[question.question_type] ?? question.question_type}
          </Badge>
          {question.difficulty ? (
            <Badge variant="outline">{question.difficulty.toLowerCase()}</Badge>
          ) : null}
          {question.topic ? (
            <span className="text-xs text-muted-foreground">
              Topic: <span className="text-foreground">{question.topic}</span>
            </span>
          ) : null}
        </div>
      </CardHeader>
      <CardContent className="pt-0">
        <p className="whitespace-pre-line text-base leading-relaxed text-foreground">
          {question.question_text}
        </p>
      </CardContent>
    </Card>
  );
}
