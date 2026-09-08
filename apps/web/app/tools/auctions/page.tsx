"use client";

import Link from "next/link";
import { useLanguage } from "@/components/LanguageProvider";
import { ServiceHeader } from "@/components/ui/ServiceHeader";

export default function AuctionsNotOfferedPage() {
  const { locale } = useLanguage();
  const ar = locale === "ar";
  return (
    <div className="min-h-screen bg-[#f5f7f6]">
      <ServiceHeader
        icon="🔨"
        title={ar ? "المزادات" : "Auctions"}
        subtitle={ar ? "هذه الخدمة ليست جزءاً من المنتج الحالي." : "This service is not part of the current product."}
        breadcrumb={[{ label: ar ? "الأدوات" : "Tools", href: "/tools" }]}
      />
      <div className="container-page max-w-2xl py-10">
        <div className="rounded-2xl border border-slate-200 bg-white p-8 shadow-card">
          <p className="text-sm leading-7 text-ink-700">
            {ar
              ? "أُزيلت المزادات من سعودي بزنس. لا توجد بيانات مزادات حية أو تجريبية تُعرض هنا، حتى لا يُفهم العرض على أنه سوق قائم."
              : "Auctions were removed from Saudi Business. No live or demo auction listings are shown here, so the product is not mistaken for an active marketplace."}
          </p>
          <Link href="/tools/opportunities" className="mt-6 inline-flex text-sm font-bold text-brand-700">
            {ar ? "استكشف الفرص الاستثمارية بدلاً من ذلك" : "Explore investment opportunities instead"}
          </Link>
        </div>
      </div>
    </div>
  );
}
