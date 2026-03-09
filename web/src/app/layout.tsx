import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
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
    <nav className="bg-navy text-white">
      <div className="max-w-6xl mx-auto px-4 py-3 flex items-center justify-between">
        <Link href="/" className="text-lg font-bold tracking-wide">
          LYC Racing Archive
        </Link>
        <div className="flex gap-4 text-sm">
          {links.map((l) => (
            <Link
              key={l.href}
              href={l.href}
              className="hover:text-gold transition-colors"
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
        className={`${geistSans.variable} ${geistMono.variable} antialiased`}
      >
        <Nav />
        <main className="max-w-6xl mx-auto px-4 py-8">{children}</main>
        <footer className="text-center text-sm text-gray-500 py-8 border-t">
          Lunenburg Yacht Club Racing Archive — 1999 to 2025
        </footer>
      </body>
    </html>
  );
}
