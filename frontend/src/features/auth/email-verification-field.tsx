"use client";

import {
  useEffect,
  useRef,
  useState,
  type ChangeEvent,
  type KeyboardEvent,
} from "react";
import { CheckCircle2, Loader2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

import type { UseFormRegisterReturn } from "react-hook-form";

import { useSendEmailOtp, useVerifyEmailOtp } from "./hooks";
import type { ApiError } from "./types";

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
const OTP_LENGTH = 6;

function isValidEmail(value: string): boolean {
  return EMAIL_RE.test(value.trim());
}

function retryAfterSeconds(error: ApiError | undefined): number | null {
  const details = error?.details;
  if (
    details &&
    typeof details === "object" &&
    "retry_after_seconds" in details &&
    typeof (details as { retry_after_seconds: unknown }).retry_after_seconds ===
      "number"
  ) {
    return (details as { retry_after_seconds: number }).retry_after_seconds;
  }
  const match = error?.message?.match(/(\d+)\s+seconds/i);
  return match ? Number(match[1]) : null;
}

type EmailVerificationFieldProps = {
  email: string;
  emailError?: string;
  registerEmail: UseFormRegisterReturn;
  verified: boolean;
  onVerifiedChange: (verified: boolean) => void;
};

export function EmailVerificationField({
  email,
  emailError,
  registerEmail,
  verified,
  onVerifiedChange,
}: EmailVerificationFieldProps) {
  const sendOtp = useSendEmailOtp();
  const verifyOtp = useVerifyEmailOtp();
  const [otpSentTo, setOtpSentTo] = useState<string | null>(null);
  const [otpDigits, setOtpDigits] = useState<string[]>(
    Array.from({ length: OTP_LENGTH }, () => ""),
  );
  const [otpError, setOtpError] = useState<string | null>(null);
  const [cooldown, setCooldown] = useState(0);
  const inputsRef = useRef<Array<HTMLInputElement | null>>([]);

  const normalized = email.trim().toLowerCase();
  const canVerifyEmail = isValidEmail(normalized) && !verified;
  const showOtp = Boolean(otpSentTo) && otpSentTo === normalized && !verified;

  useEffect(() => {
    if (verified && otpSentTo && otpSentTo !== normalized) {
      onVerifiedChange(false);
      setOtpSentTo(null);
      setOtpDigits(Array.from({ length: OTP_LENGTH }, () => ""));
      setOtpError(null);
    }
    if (otpSentTo && otpSentTo !== normalized) {
      setOtpSentTo(null);
      setOtpDigits(Array.from({ length: OTP_LENGTH }, () => ""));
      setOtpError(null);
      onVerifiedChange(false);
    }
  }, [normalized, otpSentTo, verified, onVerifiedChange]);

  useEffect(() => {
    if (cooldown <= 0) return;
    const id = window.setInterval(() => {
      setCooldown((value) => (value <= 1 ? 0 : value - 1));
    }, 1000);
    return () => window.clearInterval(id);
  }, [cooldown]);

  const startCooldown = (seconds: number) => {
    setCooldown(Math.max(0, Math.floor(seconds)));
  };

  const handleSend = () => {
    if (!canVerifyEmail) return;
    setOtpError(null);
    sendOtp.mutate(normalized, {
      onSuccess: (data) => {
        setOtpSentTo(normalized);
        setOtpDigits(Array.from({ length: OTP_LENGTH }, () => ""));
        startCooldown(data.cooldown_seconds ?? 60);
        window.setTimeout(() => inputsRef.current[0]?.focus(), 0);
      },
      onError: (error: ApiError) => {
        const wait = retryAfterSeconds(error);
        if (wait) startCooldown(wait);
        setOtpError(error.message ?? "Could not send the verification code.");
      },
    });
  };

  const handleDigit = (index: number, raw: string) => {
    const digit = raw.replace(/\D/g, "").slice(-1);
    const next = [...otpDigits];
    next[index] = digit;
    setOtpDigits(next);
    if (digit && index < OTP_LENGTH - 1) {
      inputsRef.current[index + 1]?.focus();
    }
  };

  const handleKeyDown = (index: number, event: KeyboardEvent<HTMLInputElement>) => {
    if (event.key === "Backspace" && !otpDigits[index] && index > 0) {
      inputsRef.current[index - 1]?.focus();
    }
  };

  const handlePaste = (event: React.ClipboardEvent<HTMLInputElement>) => {
    const pasted = event.clipboardData.getData("text").replace(/\D/g, "").slice(0, OTP_LENGTH);
    if (!pasted) return;
    event.preventDefault();
    const next = Array.from({ length: OTP_LENGTH }, (_, i) => pasted[i] ?? "");
    setOtpDigits(next);
    inputsRef.current[Math.min(pasted.length, OTP_LENGTH) - 1]?.focus();
  };

  const otpValue = otpDigits.join("");

  const handleVerifyOtp = () => {
    if (otpValue.length !== OTP_LENGTH) {
      setOtpError("Enter the 6-digit verification code.");
      return;
    }
    setOtpError(null);
    verifyOtp.mutate(
      { email: normalized, otp: otpValue },
      {
        onSuccess: () => {
          onVerifiedChange(true);
          setOtpError(null);
        },
        onError: (error: ApiError) => {
          setOtpError(
            error.message ?? "Invalid verification code. Please enter the correct OTP.",
          );
        },
      },
    );
  };

  return (
    <div className="space-y-3 sm:col-span-2">
      <div className="space-y-2">
        <Label htmlFor="email">Email</Label>
        <div className="flex flex-col gap-2 sm:flex-row">
          <Input
            id="email"
            type="email"
            autoComplete="email"
            placeholder="you@example.com"
            aria-invalid={!!emailError}
            className="sm:flex-1"
            {...registerEmail}
          />
          {!verified && !showOtp ? (
            <Button
              type="button"
              variant="secondary"
              className="shrink-0"
              disabled={!canVerifyEmail || sendOtp.isPending}
              onClick={handleSend}
            >
              {sendOtp.isPending ? (
                <>
                  <Loader2 className="animate-spin" />
                  Sending…
                </>
              ) : (
                "Verify Email"
              )}
            </Button>
          ) : null}
        </div>
        {emailError ? (
          <p className="text-xs text-destructive">{emailError}</p>
        ) : null}
      </div>

      {verified ? (
        <p className="flex items-center gap-2 text-sm font-medium text-emerald-600">
          <CheckCircle2 className="size-4" />
          Email Verified
        </p>
      ) : otpSentTo !== normalized && isValidEmail(normalized) ? (
        <p className="text-xs text-amber-600">Email not verified</p>
      ) : null}

      {showOtp ? (
        <div className="space-y-3 rounded-lg border border-border bg-muted/40 p-4">
          <p className="text-sm text-muted-foreground">
            We&apos;ve sent a verification code to{" "}
            <span className="font-medium text-foreground">{otpSentTo}</span>
          </p>
          <div className="space-y-2">
            <Label htmlFor="otp-0">Enter OTP</Label>
            <div className="flex gap-2">
              {otpDigits.map((digit, index) => (
                <Input
                  key={index}
                  id={index === 0 ? "otp-0" : undefined}
                  ref={(node) => {
                    inputsRef.current[index] = node;
                  }}
                  inputMode="numeric"
                  autoComplete={index === 0 ? "one-time-code" : "off"}
                  maxLength={1}
                  value={digit}
                  onChange={(event: ChangeEvent<HTMLInputElement>) =>
                    handleDigit(index, event.target.value)
                  }
                  onKeyDown={(event) => handleKeyDown(index, event)}
                  onPaste={index === 0 ? handlePaste : undefined}
                  className="h-11 w-10 px-0 text-center text-lg font-semibold tracking-normal"
                  aria-label={`Digit ${index + 1}`}
                />
              ))}
            </div>
          </div>
          {otpError ? (
            <p className="text-xs text-destructive" role="alert">
              {otpError}
            </p>
          ) : null}
          <Button
            type="button"
            onClick={handleVerifyOtp}
            disabled={verifyOtp.isPending || otpValue.length !== OTP_LENGTH}
          >
            {verifyOtp.isPending ? (
              <>
                <Loader2 className="animate-spin" />
                Verifying…
              </>
            ) : (
              "Verify OTP"
            )}
          </Button>
          <p className="text-xs text-muted-foreground">
            Didn&apos;t receive the code?{" "}
            {cooldown > 0 ? (
              <span>Resend OTP in {cooldown} seconds</span>
            ) : (
              <button
                type="button"
                className="font-medium text-foreground underline-offset-4 hover:underline disabled:opacity-50"
                disabled={sendOtp.isPending}
                onClick={handleSend}
              >
                Resend OTP
              </button>
            )}
          </p>
        </div>
      ) : null}
    </div>
  );
}
