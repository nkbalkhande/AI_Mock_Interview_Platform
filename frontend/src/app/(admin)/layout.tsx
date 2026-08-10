import type { ReactNode } from "react";

import { AdminSidebar } from "@/components/layout/admin-sidebar";
import { Header } from "@/components/layout/header";
import { SessionBootstrap } from "@/components/layout/session-bootstrap";

export default function AdminLayout({ children }: { children: ReactNode }) {
  return (
    <SessionBootstrap requireRole="admin">
      <div className="flex min-h-screen w-full bg-background">
        <AdminSidebar />
        <div className="flex min-w-0 flex-1 flex-col">
          <Header />
          <main className="min-w-0 flex-1 px-4 py-6 sm:px-6 lg:px-8">
            {children}
          </main>
        </div>
      </div>
    </SessionBootstrap>
  );
}
