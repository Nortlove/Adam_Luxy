/**
 * Client surface layout — Front-end A.
 *
 * Intentionally distinct from the internal (app) layout: no sidebar, no
 * Dialogue Ledger, no Learning or Analytics nav. Clients receive a
 * report surface; they do not operate the cognitive instrument.
 *
 * Discipline (per orientation A10 + Chris directive 2026-04-22):
 *   - Do not give the client a management-UI feel. This is a report,
 *     not a console. Clean header, plenty of whitespace, content
 *     centered in a readable column.
 *   - Do not leak internal nav. The internal nav (Campaigns /
 *     Recommendations / Learning / Dialogue Ledger / etc.) is for
 *     operators, not clients. If the client needs to reach another
 *     client surface in the future, add to this layout's header only
 *     what they need — not a replica of the internal sidebar.
 *   - Route groups are URL-transparent. This file wraps everything
 *     under dashboard/src/app/(client)/ ; the existing (app) layout is
 *     unchanged and continues to wrap all internal routes.
 */

import Link from "next/link";
import { getCurrentUser } from "@/lib/auth";

export default function ClientLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const user = getCurrentUser();

  return (
    <div className="flex min-h-full flex-col">
      <header className="border-b bg-background">
        <div className="mx-auto flex h-14 w-full max-w-5xl items-center justify-between px-6">
          <div className="flex items-center gap-3">
            <div className="flex size-7 items-center justify-center rounded-md bg-primary text-[10px] font-bold text-primary-foreground">
              IN
            </div>
            <div className="flex flex-col leading-tight">
              <span className="text-sm font-semibold">INFORMATIV</span>
              <span className="text-[10px] uppercase tracking-wider text-muted-foreground">
                Client Report
              </span>
            </div>
          </div>
          <div className="flex items-center gap-4 text-xs text-muted-foreground">
            {user.role === "superadmin" && (
              <Link
                href="/campaigns"
                className="text-xs font-medium text-muted-foreground underline-offset-4 hover:underline"
                title="Switch to internal (superadmin) surface"
              >
                ← Internal
              </Link>
            )}
            <span>{user.email}</span>
          </div>
        </div>
      </header>
      <main className="flex-1 overflow-auto bg-muted/30">{children}</main>
      <footer className="border-t bg-background">
        <div className="mx-auto flex w-full max-w-5xl items-center justify-between px-6 py-3 text-[10px] text-muted-foreground">
          <span>Reported by INFORMATIV · ADAM</span>
          <span>Analysis updated from live learning</span>
        </div>
      </footer>
    </div>
  );
}
