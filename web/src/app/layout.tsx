import type { Metadata } from "next";
import Image from "next/image";
import { Geist, Geist_Mono } from "next/font/google";
import { Crimson_Pro } from "next/font/google";
import Link from "next/link";
import DesktopNav from "@/components/DesktopNav";
import MobileNav from "@/components/MobileNav";
import SearchOverlay from "@/components/SearchOverlay";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

const crimsonPro = Crimson_Pro({
  variable: "--font-crimson-pro",
  subsets: ["latin"],
  weight: ["400", "600", "700"],
});

export const metadata: Metadata = {
  title: "LYC Racing Archive",
  description:
    "27 years of Lunenburg Yacht Club racing history — results, leaderboards, and boat profiles from 1999 to 2025.",
  // Favicons come from app/icon.png and app/apple-icon.png, which Next.js
  // links with the basePath applied.
};

const NAV_LINKS = [
  { href: "/", label: "Home" },
  { href: "/seasons/", label: "Seasons" },
  { href: "/boats/", label: "Boats" },
  { href: "/leaderboards/", label: "Leaderboards" },
  { href: "/trophies/", label: "Trophies" },
  { href: "/analysis/", label: "Analysis" },
  { href: "/compare/", label: "Compare" },
  { href: "/methodology/", label: "Methodology" },
];

function Nav() {
  return (
    <nav className="bg-navy">
      <div className="max-w-6xl mx-auto px-4 py-3 md:py-4 flex items-center justify-between">
        <Link href="/" className="flex items-center gap-2 md:gap-3 group">
          <Image
            src="/lyc-racing-data/lyc-crest.png"
            alt="LYC Burgee"
            width={36}
            height={36}
            className="rounded-full w-8 h-8 md:w-9 md:h-9"
          />
          <span className="text-white text-base md:text-lg font-semibold tracking-wide">
            LYC Racing
          </span>
        </Link>
        <div className="flex items-center gap-1 md:gap-6">
          {/* Desktop nav (hidden below md) */}
          <DesktopNav links={NAV_LINKS} />
          {/* One search instance; it renders its own desktop and mobile triggers */}
          <SearchOverlay />
          {/* Mobile nav (hidden at md and up) */}
          <MobileNav links={NAV_LINKS} />
        </div>
      </div>
    </nav>
  );
}

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body
        className={`${geistSans.variable} ${geistMono.variable} ${crimsonPro.variable} antialiased`}
      >
        <Nav />
        <main className="max-w-6xl mx-auto px-4 py-6 md:py-8">{children}</main>
        <footer className="border-t border-border">
          <div className="max-w-6xl mx-auto px-4 py-4 md:py-6 flex items-center justify-between text-xs md:text-sm text-gray-400">
            <span>Lunenburg Yacht Club Racing Archive</span>
            <span>1999 &ndash; 2025</span>
          </div>
        </footer>
      </body>
    </html>
  );
}
