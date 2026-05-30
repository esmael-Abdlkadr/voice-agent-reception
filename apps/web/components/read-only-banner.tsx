"use client";

import { Eye } from "lucide-react";
import { useAuth } from "@/components/auth-provider";

/**
 * Shown on workspace pages when the current user only has the `viewer` role.
 * Write controls are hidden for viewers (and the API enforces it server-side
 * regardless), so this explains why.
 */
export function ReadOnlyBanner() {
  const { canEdit, currentRole } = useAuth();
  if (canEdit) return null;
  return (
    <div className="mb-5 flex items-center gap-2 rounded-lg border border-amber-500/30 bg-amber-500/10 px-3 py-2 text-xs text-amber-300">
      <Eye className="h-3.5 w-3.5" />
      You have <span className="font-medium">{currentRole ?? "read-only"}</span> access to
      this workspace — viewing only. Ask an owner or admin to make changes.
    </div>
  );
}
