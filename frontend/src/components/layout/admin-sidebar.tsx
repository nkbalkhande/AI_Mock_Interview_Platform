"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  ClipboardCheck,
  LayoutDashboard,
  ListChecks,
  PlusCircle,
  User as UserIcon,
  Users,
  X,
  type LucideIcon,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import { useSidebarStore } from "@/hooks/use-sidebar";
import { APP_NAME, ROUTES } from "@/lib/constants";
import { cn } from "@/lib/utils";

interface NavItem {
  label: string;
  href: string;
  icon: LucideIcon;
}

interface NavSection {
  label: string;
  icon: LucideIcon;
  children: NavItem[];
}

type NavEntry =
  | { kind: "item"; item: NavItem }
  | { kind: "section"; section: NavSection };

const ADMIN_NAV: NavEntry[] = [
  {
    kind: "item",
    item: {
      label: "Dashboard",
      href: ROUTES.admin.dashboard,
      icon: LayoutDashboard,
    },
  },
  {
    kind: "item",
    item: {
      label: "Users",
      href: ROUTES.admin.users,
      icon: Users,
    },
  },
  {
    kind: "section",
    section: {
      label: "Interviews",
      icon: ListChecks,
      children: [
        {
          label: "All Interviews",
          href: ROUTES.admin.interviews,
          icon: ListChecks,
        },
        {
          label: "Assign Interview",
          href: ROUTES.admin.assign,
          icon: PlusCircle,
        },
      ],
    },
  },
  {
    kind: "item",
    item: {
      label: "Evaluations",
      href: ROUTES.admin.evaluations,
      icon: ClipboardCheck,
    },
  },
  {
    kind: "item",
    item: {
      label: "Profile",
      href: ROUTES.admin.profile,
      icon: UserIcon,
    },
  },
];

function NavLink({
  item,
  onNavigate,
}: {
  item: NavItem;
  onNavigate?: () => void;
}) {
  const pathname = usePathname();
  const hrefPath = item.href.split("?")[0] ?? item.href;
  const active =
    pathname === hrefPath || pathname.startsWith(`${hrefPath}/`);
  const Icon = item.icon;
  return (
    <Link
      href={item.href}
      onClick={onNavigate}
      className={cn(
        "group flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors",
        active
          ? "bg-primary/10 text-primary"
          : "text-muted-foreground hover:bg-accent hover:text-accent-foreground",
      )}
    >
      <Icon className="h-4 w-4" />
      <span>{item.label}</span>
    </Link>
  );
}

function NavSectionBlock({
  section,
  onNavigate,
}: {
  section: NavSection;
  onNavigate?: () => void;
}) {
  const Icon = section.icon;
  return (
    <div>
      <div className="mt-4 flex items-center gap-2 px-3 pb-1 text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
        <Icon className="h-3.5 w-3.5" />
        {section.label}
      </div>
      <div className="flex flex-col gap-0.5">
        {section.children.map((child) => (
          <NavLink
            key={child.href}
            item={child}
            onNavigate={onNavigate}
          />
        ))}
      </div>
    </div>
  );
}

function SidebarBody({
  entries,
  onNavigate,
}: {
  entries: NavEntry[];
  onNavigate?: () => void;
}) {
  return (
    <div className="flex h-full flex-col">
      <div className="flex h-14 items-center gap-2 px-4">
        <div
          aria-hidden="true"
          className="grid h-8 w-8 place-items-center rounded-md bg-primary text-primary-foreground font-semibold"
        >
          AI
        </div>
        <div className="flex flex-col leading-tight">
          <span className="text-sm font-semibold text-foreground">
            {APP_NAME}
          </span>
          <span className="text-[10px] text-muted-foreground">
            Admin workspace
          </span>
        </div>
      </div>
      <Separator />
      <nav className="flex-1 space-y-0.5 overflow-y-auto px-2 py-3">
        {entries.map((entry) =>
          entry.kind === "item" ? (
            <NavLink
              key={entry.item.href}
              item={entry.item}
              onNavigate={onNavigate}
            />
          ) : (
            <NavSectionBlock
              key={entry.section.label}
              section={entry.section}
              onNavigate={onNavigate}
            />
          ),
        )}
      </nav>
    </div>
  );
}

export function AdminSidebar() {
  const isOpen = useSidebarStore((s) => s.isOpen);
  const close = useSidebarStore((s) => s.close);

  return (
    <>
      {/* Desktop */}
      <aside className="hidden w-64 shrink-0 border-r bg-card lg:block">
        <SidebarBody entries={ADMIN_NAV} />
      </aside>

      {/* Mobile drawer */}
      {isOpen ? (
        <div className="fixed inset-0 z-50 lg:hidden">
          <button
            aria-label="Close navigation"
            className="absolute inset-0 bg-foreground/40 backdrop-blur-sm"
            onClick={close}
          />
          <div className="absolute inset-y-0 left-0 flex w-72 flex-col border-r bg-card shadow-xl">
            <div className="flex items-center justify-end p-2">
              <Button
                variant="ghost"
                size="icon"
                aria-label="Close navigation"
                onClick={close}
              >
                <X />
              </Button>
            </div>
            <SidebarBody entries={ADMIN_NAV} onNavigate={close} />
          </div>
        </div>
      ) : null}
    </>
  );
}
