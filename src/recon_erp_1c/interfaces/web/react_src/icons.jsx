// Minimal line icons — inline SVG, stroke-based, 1.75 weight
const Icon = ({ d, size = 16, stroke = 'currentColor', fill = 'none', sw = 1.75, viewBox = '0 0 24 24', children }) => (
  <svg xmlns="http://www.w3.org/2000/svg" width={size} height={size} viewBox={viewBox} fill={fill} stroke={stroke} strokeWidth={sw} strokeLinecap="round" strokeLinejoin="round">
    {d ? <path d={d} /> : children}
  </svg>
);

const IconCheck = (p) => <Icon {...p} d="M4 12l5 5L20 6" />;
const IconX = (p) => <Icon {...p} d="M6 6l12 12M18 6L6 18" />;
const IconAlert = (p) => <Icon {...p}><path d="M12 9v4M12 17h0"/><path d="M10.3 3.9L2.4 17a2 2 0 001.7 3h15.8a2 2 0 001.7-3L13.7 3.9a2 2 0 00-3.4 0z"/></Icon>;
const IconInfo = (p) => <Icon {...p}><circle cx="12" cy="12" r="9"/><path d="M12 8h0M11 12h1v5h1"/></Icon>;
const IconCopy = (p) => <Icon {...p}><rect x="9" y="9" width="11" height="11" rx="2"/><path d="M5 15V5a2 2 0 012-2h10"/></Icon>;
const IconExternal = (p) => <Icon {...p}><path d="M14 4h6v6"/><path d="M20 4L10 14"/><path d="M20 14v5a1 1 0 01-1 1H5a1 1 0 01-1-1V5a1 1 0 011-1h5"/></Icon>;
const IconLink = (p) => <Icon {...p}><path d="M10 14a5 5 0 007 0l3-3a5 5 0 00-7-7l-1 1"/><path d="M14 10a5 5 0 00-7 0l-3 3a5 5 0 007 7l1-1"/></Icon>;
const IconDownload = (p) => <Icon {...p}><path d="M12 3v13M7 12l5 5 5-5"/><path d="M5 21h14"/></Icon>;
const IconSearch = (p) => <Icon {...p}><circle cx="11" cy="11" r="7"/><path d="M20 20l-4-4"/></Icon>;
const IconFilter = (p) => <Icon {...p}><path d="M3 5h18M6 12h12M10 19h4"/></Icon>;
const IconRefresh = (p) => <Icon {...p}><path d="M3 12a9 9 0 0115-6.7L21 8"/><path d="M21 3v5h-5"/><path d="M21 12a9 9 0 01-15 6.7L3 16"/><path d="M3 21v-5h5"/></Icon>;
const IconDoc = (p) => <Icon {...p}><path d="M7 3h8l5 5v11a2 2 0 01-2 2H7a2 2 0 01-2-2V5a2 2 0 012-2z"/><path d="M14 3v5h5"/></Icon>;
const IconReceipt = (p) => <Icon {...p}><path d="M6 3h12v18l-3-2-3 2-3-2-3 2V3z"/><path d="M9 8h6M9 12h6M9 16h3"/></Icon>;
const IconMoney = (p) => <Icon {...p}><rect x="2" y="6" width="20" height="12" rx="2"/><circle cx="12" cy="12" r="3"/><path d="M6 12h0M18 12h0"/></Icon>;
const IconPlay = (p) => <Icon {...p} d="M7 4v16l13-8z" fill="currentColor" stroke="none"/>;
const IconPause = (p) => <Icon {...p}><rect x="6" y="4" width="4" height="16" rx="1" fill="currentColor" stroke="none"/><rect x="14" y="4" width="4" height="16" rx="1" fill="currentColor" stroke="none"/></Icon>;
const IconMore = (p) => <Icon {...p}><circle cx="6" cy="12" r="1.3" fill="currentColor"/><circle cx="12" cy="12" r="1.3" fill="currentColor"/><circle cx="18" cy="12" r="1.3" fill="currentColor"/></Icon>;
const IconPlus = (p) => <Icon {...p} d="M12 5v14M5 12h14"/>;
const IconArrowRight = (p) => <Icon {...p}><path d="M5 12h14M13 6l6 6-6 6"/></Icon>;
const IconArrowLeft = (p) => <Icon {...p}><path d="M19 12H5M11 6l-6 6 6 6"/></Icon>;
const IconChevron = (p) => <Icon {...p} d="M6 9l6 6 6-6"/>;
const IconSparkle = (p) => <Icon {...p}><path d="M12 3v4M12 17v4M3 12h4M17 12h4M6 6l2.5 2.5M15.5 15.5L18 18M6 18l2.5-2.5M15.5 8.5L18 6"/></Icon>;
const IconBell = (p) => <Icon {...p}><path d="M6 9a6 6 0 0112 0v4l2 3H4l2-3V9z"/><path d="M10 19a2 2 0 004 0"/></Icon>;
const IconSettings = (p) => <Icon {...p}><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.7 1.7 0 00.3 1.8l.1.1a2 2 0 11-2.8 2.8l-.1-.1a1.7 1.7 0 00-1.8-.3 1.7 1.7 0 00-1 1.5V21a2 2 0 01-4 0v-.1a1.7 1.7 0 00-1.1-1.5 1.7 1.7 0 00-1.8.3l-.1.1a2 2 0 11-2.8-2.8l.1-.1a1.7 1.7 0 00.3-1.8 1.7 1.7 0 00-1.5-1H3a2 2 0 010-4h.1a1.7 1.7 0 001.5-1.1 1.7 1.7 0 00-.3-1.8l-.1-.1a2 2 0 112.8-2.8l.1.1a1.7 1.7 0 001.8.3H9a1.7 1.7 0 001-1.5V3a2 2 0 014 0v.1a1.7 1.7 0 001 1.5 1.7 1.7 0 001.8-.3l.1-.1a2 2 0 112.8 2.8l-.1.1a1.7 1.7 0 00-.3 1.8V9a1.7 1.7 0 001.5 1H21a2 2 0 010 4h-.1a1.7 1.7 0 00-1.5 1z"/></Icon>;
const IconBox = (p) => <Icon {...p}><path d="M3 7l9-4 9 4v10l-9 4-9-4V7z"/><path d="M3 7l9 4 9-4M12 11v10"/></Icon>;
const IconList = (p) => <Icon {...p}><path d="M8 6h13M8 12h13M8 18h13M3 6h0M3 12h0M3 18h0"/></Icon>;
const IconChart = (p) => <Icon {...p}><path d="M3 3v18h18"/><path d="M7 14l4-4 3 3 5-6"/></Icon>;
const IconSpinner = ({ size = 18 }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" style={{ animation: 'spin 1s linear infinite' }}>
    <circle cx="12" cy="12" r="9" fill="none" stroke="currentColor" strokeOpacity="0.2" strokeWidth="2.5"/>
    <path d="M21 12a9 9 0 00-9-9" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round"/>
  </svg>
);

// Inject spinner keyframes once
if (typeof document !== 'undefined' && !document.getElementById('__spin_kf')) {
  const s = document.createElement('style');
  s.id = '__spin_kf';
  s.textContent = '@keyframes spin { to { transform: rotate(360deg); } }';
  document.head.appendChild(s);
}

Object.assign(window, {
  IconCheck, IconX, IconAlert, IconInfo, IconCopy, IconExternal, IconLink, IconDownload,
  IconSearch, IconFilter, IconRefresh, IconDoc, IconReceipt, IconMoney,
  IconPlay, IconPause, IconMore, IconPlus, IconArrowRight, IconArrowLeft, IconChevron,
  IconSparkle, IconBell, IconSettings, IconBox, IconList, IconChart, IconSpinner,
});
