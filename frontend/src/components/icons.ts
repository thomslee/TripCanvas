// 内联 SVG 图标（stroke 线性风格，24x24 viewBox）
const S = (paths: string, extra = '') =>
  `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" ${extra}>${paths}</svg>`

export const nodeIcons: Record<string, string> = {
  hotel: S('<path d="M3 21V5a1 1 0 0 1 1-1h11a1 1 0 0 1 1 1v16"/><path d="M16 10h4a1 1 0 0 1 1 1v10"/><path d="M6 8h2M10 8h2M6 12h2M10 12h2M6 16h2M10 16h2M3 21h20"/>'),
  attraction: S('<circle cx="12" cy="7" r="3"/><path d="M5 21c0-4 3-6 7-6s7 2 7 6"/><path d="M2 21h20"/>'),
  restaurant: S('<path d="M5 3v6a2 2 0 0 0 4 0V3M7 3v18M17 3c-1.5 2-2.5 4-2.5 7 0 2 .5 4 2.5 5 2-1 2.5-3 2.5-5 0-3-1-5-2.5-7Z"/>'),
}

export const transportIcons: Record<string, string> = {
  walk: S('<circle cx="12" cy="4.5" r="2"/><path d="M12 8v5l-3 6M12 10l3 4 1 5M12 8l-2 3-3 1M6.5 8.5l5 1"/>'),
  taxi: S('<path d="M4 12h16l-1.5 7H5.5L4 12Z"/><path d="M6 12 7.5 6h9L18 12"/><circle cx="8" cy="16.5" r="1"/><circle cx="16" cy="16.5" r="1"/><path d="M10 9h4"/>'),
  bus: S('<rect x="4" y="4" width="16" height="13" rx="2.5"/><path d="M4 11h16M8 4v7M16 4v7M8 19.5v1.5M16 19.5v1.5"/><circle cx="8" cy="17" r=".5" fill="currentColor"/><circle cx="16" cy="17" r=".5" fill="currentColor"/>'),
  metro: S('<path d="M5 17V7a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2v10"/><path d="M5 14h14M8 4.5l1.5 3M16 4.5l-1.5 3M8 21l2-2h4l2 2M9.5 17v1.5M14.5 17v1.5"/>'),
  bike: S('<circle cx="6" cy="17" r="3.5"/><circle cx="18" cy="17" r="3.5"/><path d="M6 17l4-7h4l2.5 5.5M12 8l-2 3M10 8h4"/>'),
  car: S('<path d="M4 13l1.5-4.5A2 2 0 0 1 7.4 7h9.2a2 2 0 0 1 1.9 1.5L20 13"/><rect x="3.5" y="13" width="17" height="5" rx="1.5"/><circle cx="8" cy="15.5" r=".6" fill="currentColor"/><circle cx="16" cy="15.5" r=".6" fill="currentColor"/>'),
  train: S('<rect x="4" y="4" width="16" height="12" rx="2.5"/><path d="M4 11h16M9 4v7M15 4v7M8 21l1.5-2M16 21l-1.5-2M9 16v2M15 16v2"/>'),
  ship: S('<path d="M4 16l8-3 8 3-8 3-8-3Z"/><path d="M12 4v9M12 4l-3 3M12 4l3 3M3 20c1.5 1 3 1 4.5 0s3-1 4.5 0 3 1 4.5 0 3-1 4.5 0"/>'),
  plane: S('<path d="M10.5 13.5 4 11l1-1.5L10 11V7l-2-1.5V4l4 1 4-1v1.5L14 7v4l5-1.5L20 11l-6.5 2.5L12 21l-1.5-7.5Z"/>'),
}

export const weatherIcons: Record<string, string> = {
  sun: S('<circle cx="12" cy="12" r="4.5"/><path d="M12 2.5v2.5M12 19v2.5M2.5 12H5M19 12h2.5M4.9 4.9l1.8 1.8M17.3 17.3l1.8 1.8M19.1 4.9l-1.8 1.8M6.7 17.3l-1.8 1.8"/>'),
  cloud: S('<path d="M6.5 18.5A4 4 0 0 1 7 10.6 5.5 5.5 0 0 1 17.6 12 3.5 3.5 0 0 1 17 19H6.5a4 4 0 0 1 0-.5Z"/>'),
  rain: S('<path d="M6.5 15A4 4 0 0 1 7 7.1 5.5 5.5 0 0 1 17.6 8.5 3.5 3.5 0 0 1 17 15.5H6.5Z"/><path d="M8.5 17.5l-1 3M13 17.5l-1 3M17.5 17.5l-1 3"/>'),
  snow: S('<path d="M6.5 14A4 4 0 0 1 7 6.1 5.5 5.5 0 0 1 17.6 7.5 3.5 3.5 0 0 1 17 14.5H6.5Z"/><path d="M12 16.5v2M12 20v1.5M9.5 17.5l1.5.5M14.5 17.5l-1.5.5M9.5 20.5l1.5-1M14.5 20.5l-1.5-1"/>'),
  thunder: S('<path d="M6.5 15A4 4 0 0 1 7 7.1 5.5 5.5 0 0 1 17.6 8.5 3.5 3.5 0 0 1 17 15.5H6.5Z"/><path d="M13 15.5 10.5 20h3L11 24"/>'),
  fog: S('<path d="M6.5 12A4 4 0 0 1 7 4.1 5.5 5.5 0 0 1 17.6 5.5 3.5 3.5 0 0 1 17 12H6.5Z"/><path d="M5 15.5h14M6.5 18.5h11M8 21.5h8"/>'),
}
