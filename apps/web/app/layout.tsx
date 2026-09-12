import type { Metadata } from "next";
import { Inter, Tajawal } from "next/font/google";
import "./globals.css";
import { LanguageProvider } from "@/components/LanguageProvider";
import { AppChrome } from "@/components/AppChrome";

// Professional bilingual pairing: Inter for Latin script, Tajawal for Arabic
// (both variable weights, both self-hosted by next/font -- no runtime
// request to Google Fonts, no layout shift).
const inter = Inter({
  subsets: ["latin"],
  variable: "--font-latin",
  display: "swap",
});
const tajawal = Tajawal({
  subsets: ["arabic"],
  weight: ["300", "400", "500", "700", "800"],
  variable: "--font-arabic",
  display: "swap",
});

export const metadata: Metadata = {
  title: {
    default: "Saudi Business | سعودي بزنس",
    template: "%s | Saudi Business",
  },
  description:
    "Saudi Business | سعودي بزنس — feasibility studies, financial analysis, and Saudi funding-program matching, in Arabic and English.",
  keywords: ["Saudi Arabia", "feasibility study", "funding", "Vision 2030", "دراسة جدوى", "تمويل"],
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  // Defaults to Arabic/RTL; LanguageProvider updates lang/dir on the client.
  // AppChrome chooses marketing vs product shell (footer / density) by route.
  return (
    <html lang="ar" dir="rtl" className={inter.variable + " " + tajawal.variable}>
      <body>
        <LanguageProvider>
          <AppChrome>{children}</AppChrome>
        </LanguageProvider>
      </body>
    </html>
  );
}
