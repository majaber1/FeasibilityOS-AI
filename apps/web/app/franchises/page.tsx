"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

export default function FranchisesPage() {
  const router = useRouter();

  useEffect(() => {
    // Redirect to the unified Opportunities Center
    router.replace("/opportunities");
  }, [router]);

  return (
    <div className="flex min-h-[50vh] items-center justify-center p-8 text-center text-sm text-slate-500">
      جارٍ الانتقال إلى مركز الفرص والامتياز التجاري المعتمد...
    </div>
  );
}
