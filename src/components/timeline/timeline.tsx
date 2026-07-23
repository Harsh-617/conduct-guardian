"use client";

import { touchpoints } from "./data";
import { TimelineItem } from "./timeline-item";
import { PatternCallout } from "./pattern-callout";

export function Timeline() {
  return (
    <div className="rounded border border-hairline bg-card-white px-6 py-6 sm:px-8">
      <div>
        {touchpoints.map((touchpoint, index) => (
          <TimelineItem
            key={touchpoint.id}
            touchpoint={touchpoint}
            index={index}
            isLast={index === touchpoints.length - 1}
          />
        ))}
      </div>

      <div className="mt-2">
        <PatternCallout />
      </div>
    </div>
  );
}
