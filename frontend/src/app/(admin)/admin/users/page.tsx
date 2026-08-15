"use client";

import { useState } from "react";
import Link from "next/link";
import { Eye, Search, ShieldCheck, ShieldOff } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { MobileField } from "@/components/admin/mobile-field";
import { useUpdateUserStatus, useUsers } from "@/features/admin/hooks";
import { ROUTES } from "@/lib/constants";
import { formatDate } from "@/lib/format";

export default function UsersPage() {
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");
  const [roleFilter, setRoleFilter] = useState<string>("");
  const [statusFilter, setStatusFilter] = useState<string>("");
  const pageSize = 20;

  const { data, isLoading } = useUsers({
    page,
    page_size: pageSize,
    search: search || undefined,
    role: roleFilter || undefined,
    is_active:
      statusFilter === "active"
        ? true
        : statusFilter === "inactive"
          ? false
          : undefined,
  });

  const updateStatus = useUpdateUserStatus();
  const totalPages = data ? Math.ceil(data.total / data.page_size) : 0;

  return (
    <div className="mx-auto flex w-full max-w-6xl flex-col gap-6">
      <header>
        <h1 className="text-2xl font-semibold tracking-tight text-foreground">
          Users
        </h1>
        <p className="text-sm text-muted-foreground">
          Manage all registered users.
        </p>
      </header>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">User List</CardTitle>
          <div className="flex flex-wrap items-center gap-3 pt-2">
            <div className="relative flex-1 min-w-[200px]">
              <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
              <Input
                placeholder="Search by name or email..."
                value={search}
                onChange={(e) => {
                  setSearch(e.target.value);
                  setPage(1);
                }}
                className="pl-9"
              />
            </div>
            <select
              value={roleFilter}
              onChange={(e) => {
                setRoleFilter(e.target.value);
                setPage(1);
              }}
              className="h-9 rounded-md border border-input bg-background px-3 text-sm"
            >
              <option value="">All Roles</option>
              <option value="CANDIDATE">Candidate</option>
              <option value="ADMIN">Admin</option>
              <option value="INTERVIEWER">Interviewer</option>
            </select>
            <select
              value={statusFilter}
              onChange={(e) => {
                setStatusFilter(e.target.value);
                setPage(1);
              }}
              className="h-9 rounded-md border border-input bg-background px-3 text-sm"
            >
              <option value="">All Status</option>
              <option value="active">Active</option>
              <option value="inactive">Inactive</option>
            </select>
          </div>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="flex flex-col gap-2">
              {Array.from({ length: 5 }).map((_, i) => (
                <Skeleton key={i} className="h-12 w-full" />
              ))}
            </div>
          ) : !data || data.items.length === 0 ? (
            <p className="py-10 text-center text-sm text-muted-foreground">
              No users found.
            </p>
          ) : (
            <>
              {/* Desktop table (md+) */}
              <div className="hidden overflow-x-auto md:block">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Name</TableHead>
                      <TableHead>Email</TableHead>
                      <TableHead>Role</TableHead>
                      <TableHead>Organization</TableHead>
                      <TableHead>Designation</TableHead>
                      <TableHead>Experience</TableHead>
                      <TableHead>Status</TableHead>
                      <TableHead>Joined</TableHead>
                      <TableHead className="text-right">Actions</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {data.items.map((user) => (
                      <TableRow key={user.id}>
                        <TableCell className="font-medium">
                          {user.full_name}
                        </TableCell>
                        <TableCell className="text-muted-foreground">
                          {user.email}
                        </TableCell>
                        <TableCell>
                          <div className="flex flex-wrap gap-1">
                            {user.roles.map((r) => (
                              <Badge key={r} variant="secondary" className="text-xs">
                                {r}
                              </Badge>
                            ))}
                          </div>
                        </TableCell>
                        <TableCell className="text-muted-foreground">
                          {user.current_organization ?? "—"}
                        </TableCell>
                        <TableCell className="text-muted-foreground">
                          {user.current_designation ?? "—"}
                        </TableCell>
                        <TableCell className="text-muted-foreground">
                          {user.years_of_experience
                            ? `${user.years_of_experience} yrs`
                            : "—"}
                        </TableCell>
                        <TableCell>
                          <Badge
                            variant={user.is_active ? "default" : "destructive"}
                            className="text-xs"
                          >
                            {user.is_active ? "Active" : "Inactive"}
                          </Badge>
                        </TableCell>
                        <TableCell className="text-muted-foreground">
                          {formatDate(user.created_at)}
                        </TableCell>
                        <TableCell className="text-right">
                          <div className="flex items-center justify-end gap-1">
                            <Button
                              variant="ghost"
                              size="icon"
                              asChild
                            >
                              <Link href={`${ROUTES.admin.users}/${user.id}`}>
                                <Eye className="h-4 w-4" />
                              </Link>
                            </Button>
                            <Button
                              variant="ghost"
                              size="icon"
                              onClick={() =>
                                updateStatus.mutate({
                                  userId: user.id,
                                  isActive: !user.is_active,
                                })
                              }
                              disabled={updateStatus.isPending}
                            >
                              {user.is_active ? (
                                <ShieldOff className="h-4 w-4 text-destructive" />
                              ) : (
                                <ShieldCheck className="h-4 w-4 text-emerald-600" />
                              )}
                            </Button>
                          </div>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>

              {/* Mobile card list (<md) */}
              <div className="flex flex-col gap-3 md:hidden">
                {data.items.map((user) => (
                  <div
                    key={user.id}
                    className="flex flex-col gap-3 rounded-lg border bg-card p-4"
                  >
                    <div className="flex flex-wrap items-start justify-between gap-2">
                      <div className="min-w-0">
                        <p className="truncate font-medium">{user.full_name}</p>
                        <p className="break-all text-xs text-muted-foreground">
                          {user.email}
                        </p>
                      </div>
                      <Badge
                        variant={user.is_active ? "default" : "destructive"}
                        className="text-xs"
                      >
                        {user.is_active ? "Active" : "Inactive"}
                      </Badge>
                    </div>

                    <div className="flex flex-wrap gap-1">
                      {user.roles.map((r) => (
                        <Badge key={r} variant="secondary" className="text-xs">
                          {r}
                        </Badge>
                      ))}
                    </div>

                    <div className="grid grid-cols-2 gap-x-3 gap-y-2 text-xs">
                      <MobileField
                        label="Organization"
                        value={user.current_organization ?? "—"}
                      />
                      <MobileField
                        label="Designation"
                        value={user.current_designation ?? "—"}
                      />
                      <MobileField
                        label="Experience"
                        value={
                          user.years_of_experience
                            ? `${user.years_of_experience} yrs`
                            : "—"
                        }
                      />
                      <MobileField
                        label="Joined"
                        value={formatDate(user.created_at)}
                      />
                    </div>

                    <div className="flex flex-wrap gap-2 pt-1">
                      <Button
                        variant="outline"
                        size="sm"
                        asChild
                        className="flex-1"
                      >
                        <Link href={`${ROUTES.admin.users}/${user.id}`}>
                          <Eye className="mr-1.5 h-4 w-4" />
                          View
                        </Link>
                      </Button>
                      <Button
                        variant="outline"
                        size="sm"
                        className="flex-1"
                        onClick={() =>
                          updateStatus.mutate({
                            userId: user.id,
                            isActive: !user.is_active,
                          })
                        }
                        disabled={updateStatus.isPending}
                      >
                        {user.is_active ? (
                          <>
                            <ShieldOff className="mr-1.5 h-4 w-4 text-destructive" />
                            Deactivate
                          </>
                        ) : (
                          <>
                            <ShieldCheck className="mr-1.5 h-4 w-4 text-emerald-600" />
                            Activate
                          </>
                        )}
                      </Button>
                    </div>
                  </div>
                ))}
              </div>

              <div className="mt-4 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                <p className="text-xs text-muted-foreground">
                  Showing {data.items.length} of {data.total} users
                </p>
                <div className="flex items-center justify-between gap-2 sm:justify-end">
                  <Button
                    variant="outline"
                    size="sm"
                    disabled={page <= 1}
                    onClick={() => setPage((p) => p - 1)}
                  >
                    Previous
                  </Button>
                  <span className="text-sm text-muted-foreground">
                    {page} / {totalPages || 1}
                  </span>
                  <Button
                    variant="outline"
                    size="sm"
                    disabled={page >= totalPages}
                    onClick={() => setPage((p) => p + 1)}
                  >
                    Next
                  </Button>
                </div>
              </div>
            </>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
