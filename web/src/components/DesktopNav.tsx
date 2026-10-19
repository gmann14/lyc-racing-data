"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { isActivePath } from "@/lib/paths";

export default function DesktopNav({
  links,
}: {
  links: { href: string; label: string }[];
}) {
  const pathname = usePathname();

  return (
    <div className="hidden md:flex items-center gap-6 text-sm">
      {links.map((l) => {
        const isActive = isActivePath(pathname, l.href);
        return (
          <Link
            key={l.href}
            href={l.href}
            aria-current={isActive ? "page" : undefined}
            className={`font-medium transition-colors ${
              isActive ? "text-gold" : "text-white/70 hover:text-gold"
            }`}
          >
            {l.label}
          </Link>
        );
      })}
    </div>
  );
}
