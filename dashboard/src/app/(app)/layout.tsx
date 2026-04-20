import {
  SidebarInset,
  SidebarProvider,
  SidebarTrigger,
} from "@/components/ui/sidebar";
import { AppSidebar } from "@/components/app-sidebar";
import { getCurrentUser } from "@/lib/auth";

export default function AppLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const user = getCurrentUser();

  return (
    <SidebarProvider>
      <AppSidebar userName={user.name} userEmail={user.email} />
      <SidebarInset>
        <header className="flex h-14 shrink-0 items-center gap-2 border-b px-4">
          <SidebarTrigger />
          <div className="flex-1" />
          <div className="text-xs text-muted-foreground">
            pilot · single-tenant
          </div>
        </header>
        <main className="flex-1 overflow-auto">{children}</main>
      </SidebarInset>
    </SidebarProvider>
  );
}
