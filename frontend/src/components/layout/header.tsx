"use client";

import { Menu } from "lucide-react";

import { NotificationBell } from "@/components/layout/notification-bell";
import { ProfileMenu } from "@/components/layout/profile-menu";
import { Button } from "@/components/ui/button";
import { useSidebarStore } from "@/hooks/use-sidebar";

interface HeaderProps {
  /** Optional URL for the user's uploaded profile photo (avatar). */
  photoUrl?: string | null;
}

/**
 * Top application header: mobile hamburger (left), notification bell + profile
 * dropdown (right). Sits above the main content and stays visible on scroll.
 */
export function Header({ photoUrl }: HeaderProps) {
  const openSidebar = useSidebarStore((s) => s.open);

  return (
    <header className="sticky top-0 z-30 flex h-14 shrink-0 items-center gap-2 border-b bg-background/80 px-3 backdrop-blur-md sm:px-4">
      <div className="flex items-center gap-2 lg:hidden">
        <Button
          variant="ghost"
          size="icon"
          aria-label="Open navigation"
          onClick={openSidebar}
        >
          <Menu />
        </Button>
      </div>

      <div className="ml-auto flex items-center gap-1 sm:gap-2">
        <NotificationBell />
        <ProfileMenu photoUrl={photoUrl} />
      </div>
    </header>
  );
}
