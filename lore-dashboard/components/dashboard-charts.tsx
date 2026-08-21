"use client";

import {ArrowUpRight} from "lucide-react";
import {Bar, BarChart, CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis} from "recharts";

const activityData = [{day: "Mon", events: 24}, {day: "Tue", events: 22}, {day: "Wed", events: 31}, {day: "Thu", events: 34}, {day: "Fri", events: 37}, {day: "Sat", events: 33}, {day: "Sun", events: 45}];
const coverageData = [{day: "Mon", risk: 12, coverage: 7}, {day: "Tue", risk: 16, coverage: 7}, {day: "Wed", risk: 22, coverage: 12}, {day: "Thu", risk: 19, coverage: 11}, {day: "Fri", risk: 24, coverage: 14}, {day: "Sat", risk: 27, coverage: 15}, {day: "Sun", risk: 29, coverage: 16}];
const tooltipStyle = {background: "#181818", border: "1px solid #333", borderRadius: "8px", color: "#fafafa"};

function ChartHeader({title, detail, trend}: {title: string; detail: string; trend: string}) {
  return <div className="flex items-start justify-between gap-3"><div><h2 className="text-lg font-semibold tracking-tight text-white">{title}</h2><p className="mt-1 text-xs text-zinc-500">{detail}</p></div><span className="flex items-center gap-1 rounded-full bg-emerald-400/10 px-2 py-1 text-xs font-medium text-emerald-400"><ArrowUpRight className="h-3.5 w-3.5" />{trend}</span></div>;
}

export function DashboardCharts() {
  return <div className="grid gap-4 xl:grid-cols-2">
    <section className="min-h-[300px] border border-white/10 bg-[#0d0d0d] p-4"><ChartHeader title="Protection activity" detail="Protected events, last 7 days." trend="66.9%" /><div className="mt-5 h-[190px]"><ResponsiveContainer width="100%" height="100%"><BarChart data={activityData} margin={{top: 8, right: 0, bottom: 0, left: -24}}><CartesianGrid vertical={false} stroke="#262626" /><XAxis dataKey="day" tickLine={false} axisLine={false} tick={{fill: "#71717a", fontSize: 12}} /><YAxis tickLine={false} axisLine={false} tick={{fill: "#71717a", fontSize: 12}} /><Tooltip cursor={{fill: "#ffffff0a"}} contentStyle={tooltipStyle} /><Bar dataKey="events" fill="#a1a1aa" radius={[1, 1, 0, 0]} /></BarChart></ResponsiveContainer></div></section>
    <section className="min-h-[300px] border border-white/10 bg-[#0d0d0d] p-4"><ChartHeader title="Risk coverage" detail="Coverage and guardrail events, last 7 days." trend="58.3%" /><div className="mt-5 h-[190px]"><ResponsiveContainer width="100%" height="100%"><LineChart data={coverageData} margin={{top: 8, right: 6, bottom: 0, left: -24}}><CartesianGrid vertical={false} stroke="#262626" /><XAxis dataKey="day" tickLine={false} axisLine={false} tick={{fill: "#71717a", fontSize: 12}} /><YAxis tickLine={false} axisLine={false} tick={{fill: "#71717a", fontSize: 12}} /><Tooltip contentStyle={tooltipStyle} /><Line type="stepAfter" dataKey="risk" stroke="#f4f4f5" strokeWidth={2} dot={false} /><Line type="stepAfter" dataKey="coverage" stroke="#71717a" strokeWidth={2} dot={false} /></LineChart></ResponsiveContainer></div></section>
  </div>;
}
