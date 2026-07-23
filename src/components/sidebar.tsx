"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";
import {
  Building2,
  GitBranch,
  HeartHandshake,
  LayoutDashboard,
  Lock,
  Menu,
  ShieldCheck,
  Users,
  X,
} from "lucide-react";

const navItems = [
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { href: "/screening", label: "Live Screening", icon: ShieldCheck },
  { href: "/timeline", label: "Case Timeline", icon: GitBranch },
  { href: "/ledger", label: "Evidence Ledger", icon: Lock },
  { href: "/coaching", label: "Coaching", icon: Users },
  { href: "/hardship", label: "Hardship Queue", icon: HeartHandshake },
  { href: "/agencies", label: "Agency Oversight", icon: Building2 },
];

export function Sidebar() {
  const pathname = usePathname();
  const [open, setOpen] = useState(false);

  return (
    <>
      <button
        type="button"
        onClick={() => setOpen(true)}
        className="fixed left-4 top-4 z-40 flex h-10 w-10 items-center justify-center rounded border border-hairline bg-card-white text-ink-navy md:hidden"
        aria-label="Open navigation"
      >
        <Menu className="h-5 w-5" />
      </button>

      {open && (
        <div
          className="fixed inset-0 z-40 bg-ink-navy/40 md:hidden"
          onClick={() => setOpen(false)}
          aria-hidden="true"
        />
      )}

      <aside
        className={`fixed inset-y-0 left-0 z-50 flex w-60 flex-col border-r border-hairline bg-card-white transition-transform duration-200 ease-in-out md:translate-x-0 ${
          open ? "translate-x-0" : "-translate-x-full"
        }`}
      >
        <div className="flex items-start justify-between px-5 pb-5 pt-6">
          <div>
            <p className="font-mono text-[10px] uppercase tracking-[0.2em] text-navy-light">
              Track 2 · UI Prototype
            </p>
            <p className="mt-1 font-serif text-xl font-bold text-ink-navy">
              Conduct Guardian
            </p>
          </div>
          <button
            type="button"
            onClick={() => setOpen(false)}
            className="text-navy-light md:hidden"
            aria-label="Close navigation"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        <nav className="mt-2 flex flex-1 flex-col gap-1 px-3">
          {navItems.map((item) => {
            const active = pathname === item.href;
            const Icon = item.icon;
            return (
              <Link
                key={item.href}
                href={item.href}
                onClick={() => setOpen(false)}
                className={`flex items-center gap-3 rounded px-3 py-2 text-sm font-medium transition-colors ${
                  active
                    ? "bg-soft-brass text-brass-accent"
                    : "text-navy-light hover:bg-soft-brass/40 hover:text-ink-navy"
                }`}
              >
                <Icon
                  className={`h-4 w-4 shrink-0 ${
                    active ? "text-brass-accent" : "text-navy-light"
                  }`}
                />
                {item.label}
              </Link>
            );
          })}
        </nav>
      </aside>
    </>
  );
}
