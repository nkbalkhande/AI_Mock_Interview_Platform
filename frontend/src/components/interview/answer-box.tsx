"use client";

import * as React from "react";

import { cn } from "@/lib/utils";

interface AnswerBoxProps
  extends Omit<React.TextareaHTMLAttributes<HTMLTextAreaElement>, "value"> {
  value: string;
  onValueChange: (next: string) => void;
  label?: string;
  helperText?: string;
  maxLength?: number;
}

/**
 * Textarea with a floating character counter and a11y label.
 *
 * Kept as a controlled component so the parent page can restore the
 * previously-submitted answer on refresh (via ``existing_answer``) and
 * clear it after a successful submission.
 */
export function AnswerBox({
  value,
  onValueChange,
  label = "Your answer",
  helperText,
  maxLength = 20000,
  className,
  disabled,
  ...rest
}: AnswerBoxProps) {
  return (
    <div className="flex flex-col gap-1.5">
      <div className="flex items-baseline justify-between">
        <label className="text-sm font-medium text-foreground" htmlFor="answer-box">
          {label}
        </label>
        <span
          className={cn(
            "text-xs tabular-nums text-muted-foreground",
            value.length > maxLength * 0.9 && "text-amber-600",
          )}
        >
          {value.length.toLocaleString()} / {maxLength.toLocaleString()}
        </span>
      </div>
      <textarea
        id="answer-box"
        className={cn(
          "min-h-[180px] w-full resize-y rounded-md border border-input bg-transparent p-3 text-sm leading-relaxed shadow-sm transition-colors placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50",
          className,
        )}
        value={value}
        onChange={(e) => onValueChange(e.target.value.slice(0, maxLength))}
        placeholder="Type your answer here — walk through your reasoning step by step."
        maxLength={maxLength}
        disabled={disabled}
        {...rest}
      />
      {helperText ? (
        <p className="text-xs text-muted-foreground">{helperText}</p>
      ) : null}
    </div>
  );
}
