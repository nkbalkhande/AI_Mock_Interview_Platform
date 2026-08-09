import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

/** Merge conditional class names and resolve Tailwind conflicts. */
export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

/**
 * Derive up to two uppercase initials from a full name.
 *
 * Falls back to "?" when nothing is parseable, so the avatar always has
 * *something* to render. Handles hyphenated names and extra whitespace.
 *
 * Examples:
 *   "Nilesh Balkhande" -> "NB"
 *   "ada" -> "A"
 *   "  " -> "?"
 */
export function getInitials(fullName: string | null | undefined): string {
  if (!fullName) return "?";
  const parts = fullName
    .split(/\s+/)
    .map((p) => p.trim())
    .filter(Boolean);
  if (parts.length === 0) return "?";
  const first = parts[0]?.[0] ?? "";
  const last = parts.length > 1 ? (parts[parts.length - 1]?.[0] ?? "") : "";
  const initials = `${first}${last}`.toUpperCase();
  return initials || "?";
}
