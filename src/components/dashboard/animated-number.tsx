"use client";

import { animate } from "framer-motion";
import { useEffect, useState } from "react";

export function AnimatedNumber({
  value,
  decimals = 0,
  suffix = "",
  prefix = "",
  delay = 0,
  duration = 1,
}: {
  value: number;
  decimals?: number;
  suffix?: string;
  prefix?: string;
  delay?: number;
  duration?: number;
}) {
  const [display, setDisplay] = useState(0);

  useEffect(() => {
    const controls = animate(0, value, {
      duration,
      delay,
      ease: "easeOut",
      onUpdate: (v) => setDisplay(v),
    });
    return () => controls.stop();
  }, [value, delay, duration]);

  return (
    <span>
      {prefix}
      {display.toFixed(decimals)}
      {suffix}
    </span>
  );
}
