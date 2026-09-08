"use client";

import { useEffect } from "react";
import { useParams, useRouter } from "next/navigation";
import { getStudy, getToken } from "@/lib/api";

export default function FeasibilityStudyRedirectPage() {
  const params = useParams();
  const router = useRouter();
  const id = Number(params.id);

  useEffect(() => {
    const token = getToken();
    if (!token || !Number.isInteger(id)) {
      router.replace("/tools/feasibility");
      return;
    }
    getStudy(token, id)
      .then((study) => router.replace(`/projects/${study.project_id}/studies/${study.id}`))
      .catch(() => router.replace("/tools/feasibility"));
  }, [id, router]);

  return <div className="container-page py-20 text-center text-sm text-ink-500">…</div>;
}
