"use client";

import Link from "next/link";
import { LogOut, User as UserIcon } from "lucide-react";

import { ProfileAvatar } from "@/components/profile/profile-avatar";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { useLogout } from "@/features/auth/hooks";
import { useAuth } from "@/hooks/use-auth";
import { ROUTES } from "@/lib/constants";
import { isAdmin } from "@/lib/auth";

interface ProfileMenuProps {
  photoUrl?: string | null;
}

/** Header profile dropdown: shows the avatar; opens to Profile + Logout. */
export function ProfileMenu({ photoUrl }: ProfileMenuProps) {
  const { user } = useAuth();
  const logoutMutation = useLogout();

  const profileHref = isAdmin(user)
    ? ROUTES.admin.profile
    : ROUTES.candidate.profile;

  return (
    <DropdownMenu>
      <DropdownMenuTrigger
        aria-label="Account menu"
        className="rounded-full outline-none ring-offset-background focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
      >
        <ProfileAvatar
          fullName={user?.fullName}
          photoUrl={photoUrl}
          className="h-9 w-9"
        />
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-56">
        <DropdownMenuLabel>
          <div className="flex flex-col">
            <span className="text-sm font-medium text-foreground">
              {user?.fullName ?? "Signed in"}
            </span>
            {user?.email ? (
              <span className="text-xs text-muted-foreground">
                {user.email}
              </span>
            ) : null}
          </div>
        </DropdownMenuLabel>
        <DropdownMenuSeparator />
        <DropdownMenuItem asChild>
          <Link href={profileHref} className="cursor-pointer">
            <UserIcon />
            Profile
          </Link>
        </DropdownMenuItem>
        <DropdownMenuSeparator />
        <DropdownMenuItem
          onSelect={(event) => {
            event.preventDefault();
            logoutMutation.mutate();
          }}
          disabled={logoutMutation.isPending}
          className="cursor-pointer text-destructive focus:text-destructive"
        >
          <LogOut />
          {logoutMutation.isPending ? "Signing out…" : "Logout"}
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
