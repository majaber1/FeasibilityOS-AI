"use client";

import { useEffect, useState } from "react";
import { getProject, getToken, type Project } from "@/lib/api";

export function useProjectContext() {
  const [project, setProject] = useState<Project | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    const token = getToken();
    if (!token) return;
    const params = new URLSearchParams(window.location.search);
    const rawId = params.get("project_id") || params.get("business");
    const projectId = rawId ? Number(rawId) : NaN;
    if (!Number.isInteger(projectId) || projectId <= 0) return;

    setLoading(true);
    getProject(token, projectId)
      .then(setProject)
      .catch((reason) => setError(reason instanceof Error ? reason.message : String(reason)))
      .finally(() => setLoading(false));
  }, []);

  return { project, loading, error };
}
