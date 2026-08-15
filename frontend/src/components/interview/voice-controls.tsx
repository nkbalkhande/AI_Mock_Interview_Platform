"use client";

import { Loader2, Mic, MicOff, Volume2, VolumeOff, VolumeX } from "lucide-react";

import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

// ---------------------------------------------------------------------------
// InterviewerVoice — replay button shown near the question card.
// TTS auto-plays on new questions; this lets the candidate replay.
// ---------------------------------------------------------------------------

interface InterviewerVoiceProps {
  isTtsPlaying: boolean;
  hasError: boolean;
  /** Browser blocked speech before the user's first interaction. */
  isBlocked?: boolean;
  onReplay: () => void;
  onStop: () => void;
  disabled?: boolean;
}

export function InterviewerVoice({
  isTtsPlaying,
  hasError,
  isBlocked,
  onReplay,
  onStop,
  disabled,
}: InterviewerVoiceProps) {
  return (
    <div className="flex flex-col gap-2 sm:flex-row sm:items-center">
      <Button
        type="button"
        variant={isTtsPlaying ? "destructive" : "outline"}
        size="sm"
        onClick={isTtsPlaying ? onStop : onReplay}
        disabled={disabled}
        className="w-full sm:w-auto"
      >
        {isTtsPlaying ? (
          <>
            <VolumeX className="mr-1.5 h-4 w-4" />
            Stop
          </>
        ) : (
          <>
            <Volume2 className="mr-1.5 h-4 w-4" />
            Replay Question
          </>
        )}
      </Button>

      {isBlocked && !isTtsPlaying ? (
        <span className="flex items-start gap-1.5 text-xs text-muted-foreground sm:items-center">
          <Volume2 className="mt-0.5 h-4 w-4 shrink-0 sm:mt-0" />
          <span>
            Click Replay Question (or anywhere on the page) to hear it — the
            browser blocks audio until your first interaction
          </span>
        </span>
      ) : hasError && !isTtsPlaying ? (
        <span className="flex items-start gap-1.5 text-xs text-destructive sm:items-center">
          <VolumeOff className="mt-0.5 h-4 w-4 shrink-0 sm:mt-0" />
          <span>Voice is not working — please read the question above</span>
        </span>
      ) : null}
    </div>
  );
}

// ---------------------------------------------------------------------------
// MicInput — optional mic button shown near the answer box.
// Candidate can record their answer or just type.
// ---------------------------------------------------------------------------

interface MicInputProps {
  isRecording: boolean;
  isTranscribing: boolean;
  onStartRecording: () => void;
  onStopRecording: () => void;
  error?: string | null;
  disabled?: boolean;
}

export function MicInput({
  isRecording,
  isTranscribing,
  onStartRecording,
  onStopRecording,
  error,
  disabled,
}: MicInputProps) {
  return (
    <div className="flex flex-col gap-2 sm:flex-row sm:items-center">
      <Button
        type="button"
        variant={isRecording ? "destructive" : "secondary"}
        size="sm"
        onClick={isRecording ? onStopRecording : onStartRecording}
        disabled={disabled || isTranscribing}
        className={cn("w-full sm:w-auto", isRecording && "animate-pulse")}
      >
        {isTranscribing ? (
          <>
            <Loader2 className="mr-1.5 h-4 w-4 animate-spin" />
            Transcribing…
          </>
        ) : isRecording ? (
          <>
            <MicOff className="mr-1.5 h-4 w-4" />
            Stop Recording
          </>
        ) : (
          <>
            <Mic className="mr-1.5 h-4 w-4" />
            Speak Answer
          </>
        )}
      </Button>

      {!isRecording && !isTranscribing && !error ? (
        <span className="text-xs text-muted-foreground">
          or type your answer below
        </span>
      ) : null}

      {error ? (
        <p className="text-xs text-destructive">{error}</p>
      ) : null}
    </div>
  );
}
