"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutGrid,
  Compass,
  LineChart,
  MessagesSquare,
  Settings,
  Activity,
  Lightbulb,
  BrainCircuit,
} from "lucide-react";

import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
} from "@/components/ui/sidebar";

const NAV_ITEMS: Array<{
  href: string;
  label: string;
  icon: React.ComponentType<{ className?: string }>;
}> = [
  { href: "/campaigns", label: "Campaigns", icon: LayoutGrid },
  { href: "/recommendations", label: "Recommendations", icon: Lightbulb },
  { href: "/learning", label: "Learning", icon: BrainCircuit },
  { href: "/discovery", label: "Discovery", icon: Compass },
  { href: "/analytics", label: "Analytics", icon: LineChart },
  { href: "/ledger", label: "Dialogue Ledger", icon: MessagesSquare },
  { href: "/settings", label: "Settings", icon: Settings },
];

export function AppSidebar({
  userName,
  userEmail,
}: {
  userName: string;
  userEmail: string;
}) {
  const pathname = usePathname();

  return (
    <Sidebar collapsible="icon">
      <SidebarHeader>
        <div className="flex items-center gap-2 px-2 py-2">
          <div className="flex size-8 items-center justify-center rounded-md bg-primary text-primary-foreground">
            <Activity className="size-4" />
          </div>
          <div className="flex flex-col leading-tight group-data-[collapsible=icon]:hidden">
            <span className="text-sm font-semibold">INFORMATIV</span>
            <span className="text-xs text-muted-foreground">ADAM · pilot</span>
          </div>
        </div>
      </SidebarHeader>
      <SidebarContent>
        <SidebarGroup>
          <SidebarGroupLabel>Workspace</SidebarGroupLabel>
          <SidebarGroupContent>
            <SidebarMenu>
              {NAV_ITEMS.map((item) => {
                const Icon = item.icon;
                const isActive =
                  pathname === item.href || pathname.startsWith(`${item.href}/`);
                return (
                  <SidebarMenuItem key={item.href}>
                    <SidebarMenuButton
                      isActive={isActive}
                      render={<Link href={item.href} />}
                    >
                      <Icon className="size-4" />
                      <span>{item.label}</span>
                    </SidebarMenuButton>
                  </SidebarMenuItem>
                );
              })}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>
      </SidebarContent>
      <SidebarFooter>
        <div className="flex items-center gap-2 rounded-md px-2 py-2 text-sm group-data-[collapsible=icon]:hidden">
          <div className="flex size-8 items-center justify-center rounded-full bg-muted font-medium">
            {userName.charAt(0).toUpperCase()}
          </div>
          <div className="flex flex-col leading-tight">
            <span className="text-sm font-medium">{userName}</span>
            <span className="text-xs text-muted-foreground">{userEmail}</span>
          </div>
        </div>
      </SidebarFooter>
    </Sidebar>
  );
}
