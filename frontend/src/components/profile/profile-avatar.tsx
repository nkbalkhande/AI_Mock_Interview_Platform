"use client";

import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { cn, getInitials } from "@/lib/utils";

interface ProfileAvatarProps {
  fullName: string | null | undefined;
  photoUrl?: string | null;
  className?: string;
}

/**
 * Photo-with-initials-fallback avatar. Renders the uploaded photo if any,
 * otherwise the user's initials (e.g. "Nilesh Balkhande" → "NB").
 */
export function ProfileAvatar({
  fullName,
  photoUrl,
  className,
}: ProfileAvatarProps) {
  const initials = getInitials(fullName);
  return (
    <Avatar className={cn(className)}>
      {photoUrl ? (
        <AvatarImage
          src={photoUrl}
          alt={fullName ?? "Profile photo"}
        />
      ) : null}
      <AvatarFallback>{initials}</AvatarFallback>
    </Avatar>
  );
}
