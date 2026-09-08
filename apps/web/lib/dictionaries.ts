export type Locale = "ar" | "en";

export const LOCALES: Locale[] = ["ar", "en"];
export const DEFAULT_LOCALE: Locale = "ar";

export const dir = (locale: Locale): "rtl" | "ltr" => (locale === "ar" ? "rtl" : "ltr");

type Dict = {
  brand: string;
  tagline: string;
  nav: {
    home: string;
    dashboard: string;
    businesses: string;
    tools: string;
    funding: string;
    opportunities: string;
    ideas: string;
    franchises: string;
    multazim: string;
    pricing: string;
    help: string;
    login: string;
    register: string;
  };
  tools: {
    feasibility: string;
    financial: string;
    proposal: string;
    funding: string;
    qualification: string;
    opportunities: string;
    franchise: string;
    reports: string;
  };
  hero: { title: string; subtitle: string; cta: string; secondary: string };
  features: { title: string; items: { title: string; body: string }[] };
  investors: { title: string; body: string; cta: string };
  status: { title: string; body: string };
  footer: {
    rights: string;
    disclaimer: string;
    product: string;
    forInvestors: string;
    company: string;
    links: {
      feasibility: string;
      funding: string;
      opportunities: string;
      pricing: string;
      help: string;
      source: string;
    };
  };
};

export const dictionaries: Record<Locale, Dict> = {
  ar: {
    brand: "سعودي بزنس",
    tagline: "من الفكرة إلى قرار الاستثمار",
    nav: {
      home: "الرئيسية",
      dashboard: "لوحة التحكم",
      businesses: "أعمالي",
      tools: "الأدوات",
      funding: "برامج التمويل",
      opportunities: "فرص استثمارية",
      ideas: "بنك الأفكار",
      franchises: "فرص الامتياز",
      multazim: "ملتزم",
      pricing: "الأسعار",
      help: "مركز المساعدة",
      login: "تسجيل الدخول",
      register: "إنشاء حساب",
    },
    tools: {
      feasibility: "دراسة الجدوى",
      financial: "التحليل المالي",
      proposal: "بناء العروض",
      funding: "مطابقة التمويل",
      qualification: "التأهيل",
      opportunities: "فرص الاستثمار",
      franchise: "الامتياز التجاري",
      reports: "التقارير",
    },
    hero: {
      title: "منصّة سعودية لدراسات الجدوى وقرارات الاستثمار",
      subtitle: "محرّك مالي حقيقي، ومطابقة شفافة لبرامج التمويل السعودية، وتقارير احترافية بالعربية والإنجليزية.",
      cta: "ابدأ دراسة جدوى",
      secondary: "استكشف برامج التمويل",
    },
    features: {
      title: "ماذا تقدّم المنصّة",
      items: [
        { title: "دراسة الجدوى", body: "معالج متعدّد الخطوات ينتهي بتقرير قابل للتصدير PDF و Word." },
        { title: "التحليل المالي", body: "ROI و NPV و IRR وفترة الاسترداد ونقطة التعادل وتحليل الحساسية." },
        { title: "مطابقة التمويل", body: "مطابقة قابلة للتفسير مع برامج مثل منشآت و NTDP و كفالة." },
      ],
    },
    investors: {
      title: "هل أنت مستثمر؟",
      body: "تصفّح فرصًا استثمارية مصنّفة حسب القطاع ومستوى المخاطرة، وحدّد المبلغ المتاح لديك لعرض الفرص المناسبة فقط.",
      cta: "استعرض الفرص الاستثمارية",
    },
    status: {
      title: "الوظائف الأساسية متاحة",
      body: "منصة مترابطة تشمل المحركات المالية والتأهيل ولوحة الإدارة. بعض خدمات الحساب تعتمد على إعداد البريد التشغيلي.",
    },
    footer: {
      rights: "جميع الحقوق محفوظة",
      disclaimer: "المنصّة أداة مساعدة ولا تُعدّ استشارة قانونية أو مالية أو ضريبية، ولا تُنفّذ أي تحويلات مالية.",
      product: "المنتج",
      forInvestors: "للمستثمرين",
      company: "الشركة",
      links: {
        feasibility: "دراسة جدوى جديدة",
        funding: "برامج التمويل",
        opportunities: "الفرص الاستثمارية",
        pricing: "الأسعار",
        help: "مركز المساعدة",
        source: "الكود المصدري",
      },
    },
  },
  en: {
    brand: "Saudi Business",
    tagline: "From idea to investment decision",
    nav: {
      home: "Home",
      dashboard: "Dashboard",
      businesses: "My Businesses",
      tools: "Tools",
      funding: "Funding Programs",
      opportunities: "Investment Opportunities",
      ideas: "Idea Bank",
      franchises: "Franchises",
      multazim: "Multazim",
      pricing: "Pricing",
      help: "Help Center",
      login: "Log in",
      register: "Sign up",
    },
    tools: {
      feasibility: "Feasibility Study",
      financial: "Financial Analysis",
      proposal: "Proposal Builder",
      funding: "Funding Matcher",
      qualification: "Qualification",
      opportunities: "Opportunities",
      franchise: "Franchise",
      reports: "Reports",
    },
    hero: {
      title: "A Saudi platform for feasibility studies and investment decisions",
      subtitle: "A real financial engine, transparent Saudi funding-program matching, and professional reports in Arabic and English.",
      cta: "Start a feasibility study",
      secondary: "Explore funding programs",
    },
    features: {
      title: "What the platform offers",
      items: [
        { title: "Feasibility Study", body: "A multi-step wizard ending in an exportable PDF and Word report." },
        { title: "Financial Analysis", body: "ROI, NPV, IRR, payback, break-even, and sensitivity analysis." },
        { title: "Funding Matching", body: "Explainable matching against programs like Monsha'at, NTDP, and Kafalah." },
      ],
    },
    investors: {
      title: "Investing?",
      body: "Browse opportunities categorized by sector and risk level, and enter the amount you have available to see only what fits.",
      cta: "Browse investment opportunities",
    },
    status: {
      title: "Core capabilities available",
      body: "An integrated platform covering financial engines, qualification, and administration. Some account services depend on operational email configuration.",
    },
    footer: {
      rights: "All rights reserved",
      disclaimer: "This platform is a decision-support tool, not legal, financial, or tax advice, and does not execute any financial transfers.",
      product: "Product",
      forInvestors: "For Investors",
      company: "Company",
      links: {
        feasibility: "New Feasibility Study",
        funding: "Funding Programs",
        opportunities: "Investment Opportunities",
        pricing: "Pricing",
        help: "Help Center",
        source: "Source Code",
      },
    },
  },
};
