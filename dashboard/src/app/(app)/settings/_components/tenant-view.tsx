import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Building2, Briefcase, FolderKanban } from "lucide-react";
import type {
  TenantHierarchyResponse,
  UserMembership,
} from "@/lib/types";

export function TenantView({
  membership,
  hierarchy,
}: {
  membership: UserMembership;
  hierarchy: TenantHierarchyResponse | null;
}) {
  return (
    <div className="flex flex-col gap-4">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            Your tenant membership
            <Badge variant="secondary" className="capitalize">
              {membership.role.replace(/_/g, " ")}
            </Badge>
          </CardTitle>
          <CardDescription>
            Multi-tenant Phase C scaffolding. The hierarchy is in place
            but query-scoping is single-tenant in v1 — every endpoint
            currently returns the full tree regardless of role.
          </CardDescription>
        </CardHeader>
        <CardContent className="grid gap-3 text-sm md:grid-cols-2">
          <div>
            <div className="text-xs uppercase text-muted-foreground">Partner</div>
            <div className="text-sm font-semibold">
              {membership.partner?.name ?? "—"}
            </div>
            <div className="text-xs text-muted-foreground">
              {membership.partner ? `id: ${membership.partner.id}` : ""}
            </div>
          </div>
          <div>
            <div className="text-xs uppercase text-muted-foreground">
              Advertiser scope
            </div>
            <div className="text-sm font-semibold">
              {membership.advertiser?.name ?? "all advertisers (superadmin)"}
            </div>
            <div className="text-xs text-muted-foreground">
              {membership.advertiser ? `id: ${membership.advertiser.id}` : ""}
            </div>
          </div>
        </CardContent>
      </Card>

      {membership.role === "superadmin" && hierarchy && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Building2 className="size-4" />
              Tenant hierarchy
            </CardTitle>
            <CardDescription>
              {hierarchy.total_partners} partner
              {hierarchy.total_partners === 1 ? "" : "s"} ·{" "}
              {hierarchy.total_advertisers} advertiser
              {hierarchy.total_advertisers === 1 ? "" : "s"} ·{" "}
              {hierarchy.total_workspaces} workspace
              {hierarchy.total_workspaces === 1 ? "" : "s"}
            </CardDescription>
          </CardHeader>
          <CardContent className="flex flex-col gap-4">
            {hierarchy.partners.map((p) => (
              <div
                key={p.id}
                className="flex flex-col gap-3 rounded-lg border p-3"
              >
                <div className="flex items-center justify-between gap-2">
                  <div className="flex items-center gap-2">
                    <Building2 className="size-4 text-primary" />
                    <span className="text-sm font-semibold">{p.name}</span>
                    <Badge variant="outline" className="text-[10px] capitalize">
                      {p.kind.replace(/_/g, " ")}
                    </Badge>
                  </div>
                  <StatusBadge status={p.status} />
                </div>
                {p.advertisers.length === 0 ? (
                  <div className="pl-6 text-xs italic text-muted-foreground">
                    No advertisers under this partner.
                  </div>
                ) : (
                  <div className="flex flex-col gap-2 pl-6">
                    {p.advertisers.map((a) => (
                      <div
                        key={a.id}
                        className="flex flex-col gap-2 border-l border-border pl-3"
                      >
                        <div className="flex items-center justify-between gap-2">
                          <div className="flex items-center gap-2">
                            <Briefcase className="size-3.5 text-muted-foreground" />
                            <span className="text-sm">{a.name}</span>
                            {a.category && (
                              <Badge variant="outline" className="text-[10px]">
                                {a.category.replace(/_/g, " ")}
                              </Badge>
                            )}
                          </div>
                          <StatusBadge status={a.status} />
                        </div>
                        {a.workspaces.map((w) => (
                          <div
                            key={w.id}
                            className="flex items-center gap-2 pl-4 text-xs text-muted-foreground"
                          >
                            <FolderKanban className="size-3" />
                            <span className="text-foreground">{w.name}</span>
                            {w.purpose && (
                              <span>— {w.purpose}</span>
                            )}
                          </div>
                        ))}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            ))}
            <Alert>
              <AlertTitle>Scaffolding in place</AlertTitle>
              <AlertDescription>
                Partner creation, white-labeling, seat management, and
                per-tenant query scoping are Phase C work. The schema
                (migration 022) is already in place so the expansion is
                additive, not a rewrite.
              </AlertDescription>
            </Alert>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

function StatusBadge({ status }: { status: string }) {
  const variant: "default" | "secondary" | "destructive" | "outline" =
    status === "active"
      ? "default"
      : status === "paused"
        ? "secondary"
        : status === "suspended"
          ? "destructive"
          : "outline";
  return (
    <Badge variant={variant} className="text-[10px]">
      {status}
    </Badge>
  );
}
