"use client";

import Link from "next/link";
import {usePathname} from "next/navigation";
import type {ReactNode} from "react";
import {useState} from "react";
import {
  Analytics,
  ChevronDown,
  Dashboard,
  Folder,
  Notification,
  Security,
  Task,
  User
} from "@carbon/icons-react";

type DetailItem = {href: string; label: string; icon: typeof Dashboard};
type DetailSection = {title: string; items: DetailItem[]};

const sections: DetailSection[] = [
  {title: "Security overview", items: [{href: "/", label: "Overview", icon: Dashboard}, {href: "/traces", label: "Trace activity", icon: Analytics}, {href: "/protection", label: "Protection controls", icon: Security}]},
  {title: "Operations", items: [{href: "/attack-lab", label: "Attack Lab", icon: Task}, {href: "/memory", label: "Protected Memory", icon: Folder}]}
];

function isCurrent(pathname: string, href: string) {
  return href === "/" ? pathname === "/" : pathname.startsWith(href);
}

function DetailSidebar() {
  const pathname = usePathname();
  const [collapsed, setCollapsed] = useState(false);
  return <aside className={`hidden h-screen shrink-0 flex-col border-r border-white/10 bg-black transition-[width] duration-300 lg:flex ${collapsed ? "w-14" : "w-60"}`}>
    <div className="flex h-20 shrink-0 items-center border-b border-white/10 px-3">
      {collapsed ? <button type="button" aria-label="Expand sidebar" onClick={() => setCollapsed(false)} className="grid h-10 w-10 place-items-center rounded-lg text-zinc-400 hover:bg-neutral-800 hover:text-white"><ChevronDown size={18} className="rotate-90" /></button> : <><div className="min-w-0 flex-1"><img src="/rails-logo.svg" alt="Application logo" className="h-7 w-auto max-w-[170px]" /></div><button type="button" aria-label="Collapse sidebar" onClick={() => setCollapsed(true)} className="grid h-10 w-10 place-items-center rounded-lg text-zinc-400 hover:bg-neutral-800 hover:text-white"><ChevronDown size={18} className="-rotate-90" /></button></>}
    </div>
    <div className="min-h-0 flex-1 overflow-y-auto overscroll-contain p-3 [scrollbar-color:#52525b_transparent]">
      {collapsed ? <nav className="space-y-2">{sections.flatMap((section) => section.items).map(({href, label, icon: Icon}) => <Link key={`${label}-collapsed`} href={href} aria-label={label} title={label} className={`grid h-10 w-10 place-items-center rounded-lg ${isCurrent(pathname, href) ? "bg-neutral-800 text-white" : "text-zinc-400 hover:bg-neutral-800 hover:text-white"}`}><Icon size={17} /></Link>)}</nav> : <div className="space-y-7">{sections.map((section) => <section key={section.title}><p className="mb-2 px-3 text-xs font-medium text-zinc-500">{section.title}</p><nav className="space-y-1">{section.items.map(({href, label, icon: Icon}) => <Link key={label} href={href} className={`flex h-10 items-center gap-3 rounded-lg px-3 text-sm transition-colors ${isCurrent(pathname, href) ? "bg-neutral-800 text-white" : "text-zinc-300 hover:bg-neutral-800 hover:text-white"}`}><Icon size={17} /><span className="truncate">{label}</span></Link>)}</nav></section>)}</div>}
    </div>
    {!collapsed && <div className="shrink-0 border-t border-neutral-800 p-3"><div className="flex items-center gap-2 rounded-lg px-2 py-1.5 text-xs text-zinc-300"><div className="grid h-7 w-7 place-items-center rounded-full border border-neutral-700"><User size={14} /></div><span className="min-w-0 flex-1 truncate">LORE operator</span><Notification size={14} className="text-zinc-500" /></div></div>}
  </aside>;
}

export function AppShell({children}: {children: ReactNode}) {
  return <div className="flex h-screen overflow-hidden bg-[#080808] text-zinc-100"><DetailSidebar /><div className="min-w-0 flex-1 overflow-y-auto overscroll-contain"><header className="sticky top-0 z-10 flex h-20 items-center justify-between border-b border-white/10 bg-[#080808]/95 px-4 backdrop-blur sm:px-6"><div className="flex items-center gap-2"><Dashboard size={18} className="text-zinc-300" /><span className="text-base font-semibold text-white">Dashboard</span></div><div className="grid h-8 w-8 place-items-center rounded-full bg-zinc-100 text-xs font-bold text-zinc-900">L</div></header><main className="p-3 sm:p-4 lg:p-5">{children}</main></div></div>;
}
