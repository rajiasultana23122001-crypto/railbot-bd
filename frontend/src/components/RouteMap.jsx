/**
 * Faint route lines behind the passenger view's heading.
 *
 * Decorative only. Drawn as thin strokes at low opacity so it reads as paper
 * texture rather than competing with the content on top of it.
 */
function RouteMap() {
  return (
    <svg
      className="route-map"
      viewBox="0 0 520 300"
      fill="none"
      aria-hidden="true"
      focusable="false"
    >
      <g stroke="currentColor" strokeWidth="1" opacity="0.5">
        <path d="M18 214C86 214 104 150 168 150s84 -54 148 -54 92 -34 150 -34" />
        <path d="M4 258c78 0 96 -46 160 -46s86 40 150 40 96 -46 160 -46" />
        <path d="M36 122c54 0 78 -46 136 -46s78 34 132 34 82 -40 140 -40" />
        <path d="M262 292V150M168 150V64M414 62V16M348 96v104" />
        <path d="M96 20c0 60 34 82 34 130s-28 66 -28 116" />
        <path d="M470 132c-52 0-70 44-124 44" />
      </g>
      <g fill="currentColor" opacity="0.65">
        <circle cx="168" cy="150" r="3.2" />
        <circle cx="262" cy="150" r="2.6" />
        <circle cx="316" cy="96" r="3.2" />
        <circle cx="414" cy="62" r="2.6" />
        <circle cx="348" cy="200" r="2.6" />
        <circle cx="130" cy="150" r="2.2" />
      </g>
    </svg>
  )
}

export default RouteMap
