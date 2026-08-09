"use client";

import dynamic from "next/dynamic";
import { useMemo } from "react";

import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";

/**
 * Load Monaco lazily on the client — it's ~1MB gzipped and never needed
 * anywhere else in the app right now, so keep it out of the main bundle.
 */
const MonacoEditor = dynamic(
  () => import("@monaco-editor/react").then((mod) => mod.default),
  {
    ssr: false,
    loading: () => (
      <Skeleton className="h-[360px] w-full rounded-md" />
    ),
  },
);

export const SUPPORTED_LANGUAGES = [
  { value: "python", label: "Python" },
  { value: "javascript", label: "JavaScript" },
  { value: "typescript", label: "TypeScript" },
  { value: "java", label: "Java" },
  { value: "cpp", label: "C++" },
  { value: "go", label: "Go" },
  { value: "sql", label: "SQL" },
] as const;

export type SupportedLanguage = (typeof SUPPORTED_LANGUAGES)[number]["value"];

interface CodingEditorProps {
  value: string;
  onValueChange: (next: string) => void;
  language: SupportedLanguage;
  onLanguageChange: (next: SupportedLanguage) => void;
  disabled?: boolean;
  className?: string;
}

export function CodingEditor({
  value,
  onValueChange,
  language,
  onLanguageChange,
  disabled,
  className,
}: CodingEditorProps) {
  const options = useMemo(
    () => ({
      minimap: { enabled: false },
      fontSize: 14,
      lineNumbers: "on" as const,
      scrollBeyondLastLine: false,
      automaticLayout: true,
      tabSize: 2,
      readOnly: disabled,
    }),
    [disabled],
  );

  return (
    <div className={cn("flex flex-col gap-2", className)}>
      <div className="flex items-center justify-between">
        <label className="text-sm font-medium text-foreground">
          Your solution
        </label>
        <label className="flex items-center gap-2 text-xs text-muted-foreground">
          Language
          <select
            className="rounded-md border border-input bg-background px-2 py-1 text-xs shadow-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50"
            value={language}
            disabled={disabled}
            onChange={(e) => onLanguageChange(e.target.value as SupportedLanguage)}
          >
            {SUPPORTED_LANGUAGES.map((lang) => (
              <option key={lang.value} value={lang.value}>
                {lang.label}
              </option>
            ))}
          </select>
        </label>
      </div>
      <div className="overflow-hidden rounded-md border border-input">
        <MonacoEditor
          height="360px"
          language={language}
          value={value}
          onChange={(v) => onValueChange(v ?? "")}
          theme="vs-dark"
          options={options}
        />
      </div>
      <p className="text-xs text-muted-foreground">
        Code is stored as-submitted; execution is not run in this MVP. Focus
        on clean, correct code — the evaluator reviews your solution as text.
      </p>
    </div>
  );
}
