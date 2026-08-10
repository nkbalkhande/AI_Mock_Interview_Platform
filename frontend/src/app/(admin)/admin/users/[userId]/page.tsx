"use client";

import { use } from "react";
import Link from "next/link";
import { ArrowLeft, Mail, Phone, Building2, Briefcase } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { useUpdateUserStatus, useUserDetail } from "@/features/admin/hooks";
import { ROUTES } from "@/lib/constants";
import { formatDate, formatDateTime } from "@/lib/format";

function statusVariant(status: string) {
  const map: Record<string, "default" | "secondary" | "destructive" | "outline"> = {
    COMPLETED: "default",
    IN_PROGRESS: "secondary",
    CANCELLED: "destructive",
    ASSIGNED: "outline",
    SCHEDULED: "outline",
    AVAILABLE: "secondary",
  };
  return map[status] ?? "outline";
}

export default function UserDetailPage({
  params,
}: {
  params: Promise<{ userId: string }>;
}) {
  const { userId } = use(params);
  const { data: user, isLoading } = useUserDetail(userId);
  const updateStatus = useUpdateUserStatus();

  if (isLoading) {
    return (
      <div className="mx-auto flex w-full max-w-4xl flex-col gap-6">
        <Skeleton className="h-8 w-48" />
        <Skeleton className="h-64 w-full" />
      </div>
    );
  }

  if (!user) {
    return (
      <div className="mx-auto flex w-full max-w-4xl flex-col items-center gap-4 py-20">
        <p className="text-muted-foreground">User not found.</p>
        <Button variant="outline" asChild>
          <Link href={ROUTES.admin.users}>Back to Users</Link>
        </Button>
      </div>
    );
  }

  return (
    <div className="mx-auto flex w-full max-w-4xl flex-col gap-6">
      <div className="flex items-center gap-3">
        <Button variant="ghost" size="icon" asChild>
          <Link href={ROUTES.admin.users}>
            <ArrowLeft className="h-4 w-4" />
          </Link>
        </Button>
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">
            {user.full_name}
          </h1>
          <p className="text-sm text-muted-foreground">{user.email}</p>
        </div>
      </div>

      <div className="grid gap-6 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Profile Information</CardTitle>
          </CardHeader>
          <CardContent className="flex flex-col gap-3">
            <div className="flex items-center gap-2 text-sm">
              <Mail className="h-4 w-4 text-muted-foreground" />
              <span>{user.email}</span>
              {user.email_verified ? (
                <Badge variant="default" className="text-xs">Verified</Badge>
              ) : (
                <Badge variant="secondary" className="text-xs">Unverified</Badge>
              )}
            </div>
            {user.phone_number ? (
              <div className="flex items-center gap-2 text-sm">
                <Phone className="h-4 w-4 text-muted-foreground" />
                <span>{user.phone_number}</span>
              </div>
            ) : null}
            {user.current_organization ? (
              <div className="flex items-center gap-2 text-sm">
                <Building2 className="h-4 w-4 text-muted-foreground" />
                <span>{user.current_organization}</span>
              </div>
            ) : null}
            {user.current_designation ? (
              <div className="flex items-center gap-2 text-sm">
                <Briefcase className="h-4 w-4 text-muted-foreground" />
                <span>{user.current_designation}</span>
              </div>
            ) : null}
            {user.years_of_experience ? (
              <p className="text-sm text-muted-foreground">
                {user.years_of_experience} years of experience
              </p>
            ) : null}
            {user.bio ? (
              <p className="text-sm text-muted-foreground">{user.bio}</p>
            ) : null}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-base">Account</CardTitle>
          </CardHeader>
          <CardContent className="flex flex-col gap-3">
            <div className="flex flex-wrap gap-1">
              {user.roles.map((r) => (
                <Badge key={r} variant="secondary">
                  {r}
                </Badge>
              ))}
            </div>
            <div className="flex items-center gap-2">
              <span className="text-sm">Status:</span>
              <Badge variant={user.is_active ? "default" : "destructive"}>
                {user.is_active ? "Active" : "Inactive"}
              </Badge>
            </div>
            <p className="text-sm text-muted-foreground">
              Joined {formatDate(user.created_at)}
            </p>
            {user.last_login_at ? (
              <p className="text-sm text-muted-foreground">
                Last login {formatDateTime(user.last_login_at)}
              </p>
            ) : null}
            <Button
              variant={user.is_active ? "destructive" : "default"}
              size="sm"
              className="mt-2 w-fit"
              onClick={() =>
                updateStatus.mutate({
                  userId: user.id,
                  isActive: !user.is_active,
                })
              }
              disabled={updateStatus.isPending}
            >
              {user.is_active ? "Deactivate Account" : "Activate Account"}
            </Button>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">
            Interview History ({user.total_interviews})
          </CardTitle>
        </CardHeader>
        <CardContent>
          {user.interviews.length === 0 ? (
            <p className="py-6 text-center text-sm text-muted-foreground">
              No interviews yet.
            </p>
          ) : (
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Type</TableHead>
                    <TableHead>Role</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead>Scheduled</TableHead>
                    <TableHead>Created</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {user.interviews.map((iv) => (
                    <TableRow key={iv.interview_id}>
                      <TableCell>
                        <Badge variant="outline" className="text-xs">
                          {iv.interview_type}
                        </Badge>
                      </TableCell>
                      <TableCell>{iv.role ?? "—"}</TableCell>
                      <TableCell>
                        <Badge
                          variant={statusVariant(iv.status)}
                          className="text-xs"
                        >
                          {iv.status}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-muted-foreground">
                        {formatDateTime(iv.scheduled_at)}
                      </TableCell>
                      <TableCell className="text-muted-foreground">
                        {formatDate(iv.created_at)}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
