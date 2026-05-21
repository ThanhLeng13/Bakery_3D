"use client";

import { useCallback } from "react";
import type { CakeDesign } from "@/types";

export type CakeZone = "top" | "body" | "border";

interface CakeSVGProps {
  design: CakeDesign;
  activeZone: CakeZone | null;
  hoveredZone: CakeZone | null;
  onZoneClick: (zone: CakeZone) => void;
  onZoneHover: (zone: CakeZone | null) => void;
}

/** Cream color options */
export const CREAM_COLORS: Record<string, string> = {
  pink: "#E8837A",
  white: "#FFFFFF",
  chocolate: "#5C3D2E",
  matcha: "#7AB648",
  vanilla: "#FFF8DC",
  lavender: "#B57EDC",
};

/** Topping decoration SVG patterns */
const TOPPING_VISUALS: Record<string, (cx: number, cy: number) => JSX.Element> =
  {
    flowers: (cx, cy) => (
      <g key={`flower-${cx}-${cy}`}>
        <circle cx={cx} cy={cy} r="6" fill="#E8837A" opacity="0.9" />
        <circle cx={cx - 4} cy={cy - 3} r="3" fill="#FFB6C1" />
        <circle cx={cx + 4} cy={cy - 3} r="3" fill="#FFB6C1" />
        <circle cx={cx - 4} cy={cy + 3} r="3" fill="#FFB6C1" />
        <circle cx={cx + 4} cy={cy + 3} r="3" fill="#FFB6C1" />
        <circle cx={cx} cy={cy} r="2.5" fill="#FFD700" />
      </g>
    ),
    fruits: (cx, cy) => (
      <g key={`fruit-${cx}-${cy}`}>
        <circle cx={cx - 5} cy={cy} r="4" fill="#FF6347" />
        <circle cx={cx + 5} cy={cy} r="3.5" fill="#FFD700" />
        <circle cx={cx} cy={cy - 4} r="3" fill="#90EE90" />
      </g>
    ),
    "chocolate drip": (cx, cy) => (
      <g key={`chocdrip-${cx}-${cy}`}>
        <rect x={cx - 3} y={cy - 2} width="6" height="4" rx="2" fill="#3D1F0E" />
        <rect x={cx - 6} y={cy - 2} width="4" height="3" rx="1.5" fill="#5C3D2E" />
      </g>
    ),
    sprinkles: (cx, cy) => (
      <g key={`sprinkle-${cx}-${cy}`}>
        <rect x={cx - 5} y={cy - 1} width="4" height="2" rx="1" fill="#FF69B4" transform={`rotate(30 ${cx - 3} ${cy})`} />
        <rect x={cx + 1} y={cy - 2} width="4" height="2" rx="1" fill="#87CEEB" transform={`rotate(-20 ${cx + 3} ${cy - 1})`} />
        <rect x={cx - 2} y={cy + 1} width="4" height="2" rx="1" fill="#98FB98" transform={`rotate(60 ${cx} ${cy + 2})`} />
      </g>
    ),
    macarons: (cx, cy) => (
      <g key={`macaron-${cx}-${cy}`}>
        <ellipse cx={cx} cy={cy} rx="7" ry="5" fill="#FFB6C1" />
        <rect x={cx - 6} y={cy - 1} width="12" height="2" fill="#FFF0F5" />
        <ellipse cx={cx} cy={cy} rx="7" ry="5" fill="none" stroke="#E8837A" strokeWidth="0.5" />
      </g>
    ),
    text: (cx, cy) => (
      <g key={`text-${cx}-${cy}`}>
        <text x={cx} y={cy + 3} textAnchor="middle" fontSize="8" fill="#5C3D2E" fontFamily="serif" fontWeight="bold">
          HBD
        </text>
      </g>
    ),
  };

/** Border decoration patterns */
const BORDER_VISUALS: Record<string, (x: number, y: number, width: number) => JSX.Element> = {
  piping: (x, y, width) => (
    <g key="piping">
      {Array.from({ length: Math.floor(width / 16) }, (_, i) => (
        <circle key={i} cx={x + 8 + i * 16} cy={y} r="5" fill="currentColor" opacity="0.7" />
      ))}
    </g>
  ),
  rosettes: (x, y, width) => (
    <g key="rosettes">
      {Array.from({ length: Math.floor(width / 24) }, (_, i) => (
        <g key={i}>
          <circle cx={x + 12 + i * 24} cy={y} r="6" fill="currentColor" opacity="0.6" />
          <circle cx={x + 12 + i * 24} cy={y} r="3" fill="currentColor" opacity="0.9" />
        </g>
      ))}
    </g>
  ),
  sprinkles: (x, y, width) => (
    <g key="border-sprinkles">
      {Array.from({ length: Math.floor(width / 10) }, (_, i) => (
        <rect
          key={i}
          x={x + 3 + i * 10}
          y={y - 2 + (i % 3) * 2}
          width="4"
          height="2"
          rx="1"
          fill={["#FF69B4", "#87CEEB", "#98FB98", "#FFD700"][i % 4]}
          transform={`rotate(${(i * 30) % 90} ${x + 5 + i * 10} ${y})`}
        />
      ))}
    </g>
  ),
  ribbon: (x, y, width) => (
    <g key="ribbon">
      <rect x={x} y={y - 4} width={width} height="8" fill="currentColor" opacity="0.5" rx="2" />
      <rect x={x} y={y - 1} width={width} height="2" fill="currentColor" opacity="0.8" />
    </g>
  ),
  pearls: (x, y, width) => (
    <g key="pearls">
      {Array.from({ length: Math.floor(width / 12) }, (_, i) => (
        <circle key={i} cx={x + 6 + i * 12} cy={y} r="3.5" fill="#FFFDD0" stroke="#D4AF37" strokeWidth="0.5" />
      ))}
    </g>
  ),
};

export default function CakeSVG({
  design,
  activeZone,
  hoveredZone,
  onZoneClick,
  onZoneHover,
}: CakeSVGProps) {
  const getZoneStyle = useCallback(
    (zone: CakeZone) => {
      const isActive = activeZone === zone;
      const isHovered = hoveredZone === zone;

      if (isActive) {
        return "drop-shadow(0 0 8px rgba(232, 131, 122, 0.8))";
      }
      if (isHovered) {
        return "drop-shadow(0 0 5px rgba(232, 131, 122, 0.5))";
      }
      return "none";
    },
    [activeZone, hoveredZone]
  );

  const getZoneStroke = useCallback(
    (zone: CakeZone) => {
      const isActive = activeZone === zone;
      const isHovered = hoveredZone === zone;

      if (isActive) return { stroke: "#E8837A", strokeWidth: 2.5 };
      if (isHovered) return { stroke: "#E8837A", strokeWidth: 1.5, strokeDasharray: "4 2" };
      return { stroke: "#D4A574", strokeWidth: 0.5 };
    },
    [activeZone, hoveredZone]
  );

  const handleZoneInteraction = useCallback(
    (zone: CakeZone) => (e: React.MouseEvent | React.TouchEvent) => {
      e.preventDefault();
      onZoneClick(zone);
    },
    [onZoneClick]
  );

  const handleZoneHoverEnter = useCallback(
    (zone: CakeZone) => () => onZoneHover(zone),
    [onZoneHover]
  );

  const handleZoneHoverLeave = useCallback(
    () => onZoneHover(null),
    [onZoneHover]
  );

  // Get cream color for body
  const bodyColor = design.zones.body.color || design.cream_color || CREAM_COLORS.pink;
  const borderColor = design.zones.border.color || "#D4A574";

  // Render toppings on top zone
  const renderToppings = () => {
    const topping = design.zones.top.topping;
    if (!topping || !TOPPING_VISUALS[topping]) return null;

    const positions = [
      { cx: 150, cy: 75 },
      { cx: 120, cy: 85 },
      { cx: 180, cy: 85 },
      { cx: 135, cy: 65 },
      { cx: 165, cy: 65 },
    ];

    return positions.map((pos) => TOPPING_VISUALS[topping](pos.cx, pos.cy));
  };

  // Render border decorations
  const renderBorderDecorations = () => {
    const decoration = design.zones.border.decoration;
    if (!decoration || !BORDER_VISUALS[decoration]) return null;

    return (
      <g style={{ color: borderColor }}>
        {BORDER_VISUALS[decoration](70, 230, 160)}
      </g>
    );
  };

  // Render body pattern
  const renderBodyPattern = () => {
    const decoration = design.zones.body.decoration;
    if (!decoration) return null;

    switch (decoration) {
      case "stripes":
        return (
          <g opacity="0.3">
            {Array.from({ length: 5 }, (_, i) => (
              <line
                key={i}
                x1={80 + i * 25}
                y1={110}
                x2={80 + i * 25}
                y2={220}
                stroke="#FFF"
                strokeWidth="2"
              />
            ))}
          </g>
        );
      case "dots":
        return (
          <g opacity="0.4">
            {Array.from({ length: 12 }, (_, i) => (
              <circle
                key={i}
                cx={90 + (i % 4) * 30}
                cy={130 + Math.floor(i / 4) * 30}
                r="3"
                fill="#FFF"
              />
            ))}
          </g>
        );
      case "waves":
        return (
          <path
            d="M70 150 Q95 140 120 150 Q145 160 170 150 Q195 140 220 150 M70 180 Q95 170 120 180 Q145 190 170 180 Q195 170 220 180"
            fill="none"
            stroke="#FFF"
            strokeWidth="1.5"
            opacity="0.4"
          />
        );
      default:
        return null;
    }
  };

  return (
    <div className="w-full max-w-[400px] mx-auto aspect-square flex items-center justify-center">
      <svg
        viewBox="0 0 300 300"
        className="w-full h-full"
        role="img"
        aria-label="Interactive cake builder. Click on different zones to customize."
      >
        <title>Cake Builder - Click zones to customize</title>

        {/* Top Zone - Toppings area */}
        <g
          className="cursor-pointer transition-all duration-100"
          style={{ filter: getZoneStyle("top") }}
          onClick={handleZoneInteraction("top")}
          onTouchEnd={handleZoneInteraction("top")}
          onMouseEnter={handleZoneHoverEnter("top")}
          onMouseLeave={handleZoneHoverLeave}
          role="button"
          aria-label="Top zone: toppings and decorations. Click to customize."
          tabIndex={0}
          onKeyDown={(e) => {
            if (e.key === "Enter" || e.key === " ") {
              e.preventDefault();
              onZoneClick("top");
            }
          }}
        >
          {/* Top surface - ellipse */}
          <ellipse
            cx="150"
            cy="95"
            rx="85"
            ry="25"
            fill={bodyColor}
            {...getZoneStroke("top")}
          />
          {/* Cream swirl on top */}
          <ellipse
            cx="150"
            cy="90"
            rx="70"
            ry="18"
            fill={bodyColor}
            opacity="0.8"
          />
          <ellipse
            cx="150"
            cy="87"
            rx="50"
            ry="12"
            fill="#FFF"
            opacity="0.3"
          />
          {/* Toppings */}
          {renderToppings()}
          {/* Touch target overlay (invisible, ensures 44x44 minimum) */}
          <rect
            x="65"
            y="55"
            width="170"
            height="55"
            fill="transparent"
            className="min-w-[44px] min-h-[44px]"
          />
        </g>

        {/* Body Zone - Main cake body */}
        <g
          className="cursor-pointer transition-all duration-100"
          style={{ filter: getZoneStyle("body") }}
          onClick={handleZoneInteraction("body")}
          onTouchEnd={handleZoneInteraction("body")}
          onMouseEnter={handleZoneHoverEnter("body")}
          onMouseLeave={handleZoneHoverLeave}
          role="button"
          aria-label="Body zone: cream color and pattern. Click to customize."
          tabIndex={0}
          onKeyDown={(e) => {
            if (e.key === "Enter" || e.key === " ") {
              e.preventDefault();
              onZoneClick("body");
            }
          }}
        >
          {/* Main cake body - rounded rectangle */}
          <path
            d={`M65 95 L65 215 Q65 225 75 225 L225 225 Q235 225 235 215 L235 95 Z`}
            fill={bodyColor}
            {...getZoneStroke("body")}
          />
          {/* Body pattern */}
          {renderBodyPattern()}
          {/* Subtle shading for 3D effect */}
          <path
            d="M65 95 L65 215 Q65 225 75 225 L85 225 L85 95 Z"
            fill="#000"
            opacity="0.05"
          />
          <path
            d="M225 95 L235 95 L235 215 Q235 225 225 225 L215 225 L215 95 Z"
            fill="#000"
            opacity="0.08"
          />
          {/* Touch target overlay */}
          <rect
            x="65"
            y="95"
            width="170"
            height="130"
            fill="transparent"
          />
        </g>

        {/* Border Zone - Bottom decorations */}
        <g
          className="cursor-pointer transition-all duration-100"
          style={{ filter: getZoneStyle("border") }}
          onClick={handleZoneInteraction("border")}
          onTouchEnd={handleZoneInteraction("border")}
          onMouseEnter={handleZoneHoverEnter("border")}
          onMouseLeave={handleZoneHoverLeave}
          role="button"
          aria-label="Border zone: border decorations. Click to customize."
          tabIndex={0}
          onKeyDown={(e) => {
            if (e.key === "Enter" || e.key === " ") {
              e.preventDefault();
              onZoneClick("border");
            }
          }}
        >
          {/* Border/base band */}
          <path
            d={`M65 215 Q65 225 75 225 L225 225 Q235 225 235 215 L235 245 Q235 255 225 255 L75 255 Q65 255 65 245 Z`}
            fill={borderColor}
            {...getZoneStroke("border")}
          />
          {/* Border decorations */}
          {renderBorderDecorations()}
          {/* Cake board/plate */}
          <ellipse
            cx="150"
            cy="258"
            rx="100"
            ry="8"
            fill="#F5F5DC"
            stroke="#D4A574"
            strokeWidth="0.5"
          />
          {/* Touch target overlay */}
          <rect
            x="55"
            y="215"
            width="190"
            height="50"
            fill="transparent"
          />
        </g>

        {/* Zone labels (shown on hover) */}
        {hoveredZone === "top" && (
          <text x="150" y="50" textAnchor="middle" fontSize="10" fill="#5C3D2E" fontWeight="500">
            Toppings & Decorations
          </text>
        )}
        {hoveredZone === "body" && (
          <text x="150" y="165" textAnchor="middle" fontSize="10" fill="#FFF" fontWeight="500" opacity="0.9">
            Cream & Pattern
          </text>
        )}
        {hoveredZone === "border" && (
          <text x="150" y="275" textAnchor="middle" fontSize="10" fill="#5C3D2E" fontWeight="500">
            Border Decorations
          </text>
        )}
      </svg>
    </div>
  );
}
