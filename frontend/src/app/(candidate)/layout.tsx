import type { ReactNode } from "react";

import { Header } from "@/components/layout/header";
import { SessionBootstrap } from "@/components/layout/session-bootstrap";
import { Sidebar } from "@/components/layout/sidebar";

/**
 * Authenticated candidate app shell.
 *
 * ``SessionBootstrap`` rehydrates the client auth store from the httpOnly
 * cookie on refresh (frontend's ``useAuthStore`` is otherwise empty until
 * a login mutation) and redirects admins to their own dashboard so they
 * don't accidentally see candidate-only screens.
 */
export default function CandidateLayout({ children }: { children: ReactNode }) {
  return (
    <SessionBootstrap requireRole="candidate">
      <div className="flex min-h-screen w-full bg-background">
        <Sidebar />
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
