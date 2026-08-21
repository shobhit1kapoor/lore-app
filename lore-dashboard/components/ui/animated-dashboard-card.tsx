"use client";

import {motion, useReducedMotion} from "framer-motion";

type SecuritySignalsCardProps = {
  total: number;
  primaryLabel: string;
  primaryValue: number;
  secondaryLabel: string;
  secondaryValue: number;
  enableAnimations?: boolean;
};

function dots(count: number, radius: number) {
  return Array.from({length: count}, (_, index) => {
    const angle = (index / count) * Math.PI * 2;
    return {x: 160 + radius * Math.cos(angle), y: 160 + radius * Math.sin(angle), delay: index * 0.012};
  });
}

const outerDots = dots(44, 128);
const innerDots = dots(32, 105);

export function SecuritySignalsCard({total, primaryLabel, primaryValue, secondaryLabel, secondaryValue, enableAnimations = true}: SecuritySignalsCardProps) {
  const reducedMotion = useReducedMotion();
  const animate = enableAnimations && !reducedMotion;
  const reveal = {hidden: {opacity: 0, scale: 0.75}, visible: {opacity: 0.65, scale: 1, transition: {duration: 0.35}}};

  return <motion.section initial={animate ? {opacity: 0, y: 12} : false} animate={{opacity: 1, y: 0}} transition={{type: "spring", stiffness: 280, damping: 26}} className="relative min-h-[300px] overflow-hidden border border-white/10 bg-[#0d0d0d] p-4">
    <div className="relative z-10 flex items-start justify-between"><div><p className="text-xs font-medium text-zinc-500">Security signals</p><h2 className="mt-1 text-base font-semibold text-white">Protected traffic</h2></div><span className="rounded-full bg-emerald-400/10 px-2 py-1 text-[11px] font-medium text-emerald-400">Live</span></div>
    <div className="pointer-events-none absolute left-1/2 top-7 h-64 w-64 -translate-x-1/2 opacity-90"><svg className="h-full w-full" viewBox="0 0 320 320" fill="none">{outerDots.map((dot, index) => <motion.circle key={`outer-${index}`} cx={dot.x} cy={dot.y} r="4.5" fill="#69a8ff" variants={reveal} initial={animate ? "hidden" : "visible"} animate="visible" transition={{delay: dot.delay}} />)}{innerDots.map((dot, index) => <motion.circle key={`inner-${index}`} cx={dot.x} cy={dot.y} r="4.5" fill="#55d88c" variants={reveal} initial={animate ? "hidden" : "visible"} animate="visible" transition={{delay: dot.delay + 0.12}} />)}</svg></div>
    <div className="pointer-events-none absolute left-1/2 top-[100px] z-[1] w-44 -translate-x-1/2 text-center"><p className="text-[10px] font-medium uppercase tracking-[0.18em] text-zinc-500">Total</p><p className="mt-1 text-4xl font-semibold tabular-nums text-white">{total.toLocaleString()}</p><p className="mt-1 text-xs text-zinc-400">controlled events</p></div>
    <div className="absolute inset-x-0 bottom-0 z-10 border-t border-white/10 bg-[#0d0d0d]/95 p-4 backdrop-blur-sm"><div className="grid grid-cols-2 gap-4"><div className="border-l-2 border-[#69a8ff] pl-2"><p className="text-[11px] text-zinc-500">{primaryLabel}</p><p className="mt-1 text-xl font-semibold tabular-nums text-white">{primaryValue.toLocaleString()}</p></div><div className="border-l-2 border-[#55d88c] pl-2"><p className="text-[11px] text-zinc-500">{secondaryLabel}</p><p className="mt-1 text-xl font-semibold tabular-nums text-white">{secondaryValue.toLocaleString()}</p></div></div></div>
  </motion.section>;
}

export const BonusesIncentivesCard = SecuritySignalsCard;
