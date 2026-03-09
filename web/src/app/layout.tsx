import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import { Crimson_Pro } from "next/font/google";
import Link from "next/link";
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
};

function Nav() {
  const links = [
    { href: "/", label: "Home" },
    { href: "/seasons/", label: "Seasons" },
    { href: "/boats/", label: "Boats" },
    { href: "/leaderboards/", label: "Leaderboards" },
    { href: "/trophies/", label: "Trophies" },
  ];
  return (
    <nav className="bg-navy">
      <div className="max-w-6xl mx-auto px-4 py-4 flex items-center justify-between">
        <Link href="/" className="flex items-center gap-3 group">
          <div className="w-8 h-8 rounded-full border-2 border-gold flex items-center justify-center text-gold text-sm font-bold group-hover:bg-gold group-hover:text-navy transition-colors">
            L
          </div>
          <span className="text-white text-lg font-semibold tracking-wide">
            LYC Racing
          </span>
        </Link>
        <div className="flex gap-6 text-sm">
          {links.map((l) => (
            <Link
              key={l.href}
              href={l.href}
              className="text-white/70 hover:text-gold transition-colors font-medium"
            >
              {l.label}
            </Link>
          ))}
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
        <main className="max-w-6xl mx-auto px-4 py-8">{children}</main>
        <footer className="border-t border-border">
          <div className="max-w-6xl mx-auto px-4 py-6 flex items-center justify-between text-sm text-gray-400">
            <span>Lunenburg Yacht Club Racing Archive</span>
            <span>1999 &ndash; 2025</span>
          </div>
        </footer>
      </body>
    </html>
  );
}
