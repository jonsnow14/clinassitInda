import type { Metadata } from "next";
import { Noto_Sans, Noto_Sans_Devanagari } from "next/font/google";
import "./globals.css";

const sans = Noto_Sans({
  variable: "--font-sans",
  subsets: ["latin"],
  weight: ["400", "600", "700"],
});

const deva = Noto_Sans_Devanagari({
  subsets: ["devanagari"],
  weight: ["400", "600", "700"],
});

export const metadata: Metadata = {
  title: "ClinAssistIndia",
  description: "ICMR-grounded decision support for PHC workers",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="hi">
      <body className={`${sans.variable} ${deva.className} antialiased`}>{children}</body>
    </html>
  );
}
