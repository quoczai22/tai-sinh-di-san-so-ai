// decor/phoenix.js — HÌNH TRANG TRÍ: chim phượng dưới ảnh bìa trang chủ. Ra: phoenix(). Dùng ở views/library.js.
// Chim phượng "vươn mình" (lấy từ giao diện gốc của nhóm, archive/web_ui_2026-09/components/sections/experience.html),
// vẽ lại theo bảng màu men Bát Tràng: lam cobalt, lam nhạt, ánh vàng kim; bỏ cam/xanh lá pastel.
// Đuôi được "vẽ dần" theo vị trí cuộn: một mặt nạ (mask) chạy dọc đường đuôi với stroke-dashoffset
// lấy từ biến --p của khối [data-scene] (core/scenes.js). Hình thuần trang trí: aria-hidden.
// Dựng bằng DOMParser từ chuỗi tĩnh (không chứa dữ liệu người dùng), không dùng innerHTML.

const TAIL = `M 1280 200 C 1400 340, 1180 450, 940 490 C 680 530, 360 640, 280 820 C 200 1000, 340 1160, 620 1230
C 900 1300, 1240 1380, 1260 1540 C 1280 1660, 980 1715, 700 1705 C 440 1695, 180 1655, -60 1610`;

const SVG = `<svg xmlns="http://www.w3.org/2000/svg" class="phoenix-svg" viewBox="0 0 1440 1800" fill="none" preserveAspectRatio="xMidYMin meet" focusable="false">
<defs>
  <linearGradient id="phxBody" x1="0.88" y1="0.05" x2="0.25" y2="1">
    <stop offset="0%" stop-color="#24508A" stop-opacity="0.42"/>
    <stop offset="40%" stop-color="#3D6FB0" stop-opacity="0.34"/>
    <stop offset="75%" stop-color="#5B86C5" stop-opacity="0.26"/>
    <stop offset="92%" stop-color="#C9A35F" stop-opacity="0.18"/>
    <stop offset="100%" stop-color="#C9A35F" stop-opacity="0"/>
  </linearGradient>
  <linearGradient id="phxSoft" x1="0.88" y1="0.05" x2="0.25" y2="1">
    <stop offset="0%" stop-color="#7FA3D6" stop-opacity="0.34"/>
    <stop offset="60%" stop-color="#9DB8DE" stop-opacity="0.24"/>
    <stop offset="100%" stop-color="#D4B47A" stop-opacity="0"/>
  </linearGradient>
  <linearGradient id="phxSpine" x1="0.88" y1="0.05" x2="0.25" y2="1">
    <stop offset="0%" stop-color="#24508A" stop-opacity="0.9"/>
    <stop offset="55%" stop-color="#3D6FB0" stop-opacity="0.8"/>
    <stop offset="82%" stop-color="#C9A35F" stop-opacity="0.85"/>
    <stop offset="100%" stop-color="#C9A35F" stop-opacity="0"/>
  </linearGradient>
  <filter id="phxGlow" x="-20%" y="-20%" width="140%" height="140%">
    <feGaussianBlur stdDeviation="12" result="b"/><feComposite in="SourceGraphic" in2="b" operator="over"/>
  </filter>
  <filter id="phxSoftGlow" x="-30%" y="-30%" width="160%" height="160%">
    <feGaussianBlur stdDeviation="6" result="b"/><feComposite in="SourceGraphic" in2="b" operator="over"/>
  </filter>
  <mask id="phxReveal" maskUnits="userSpaceOnUse" x="-200" y="0" width="1840" height="1900">
    <path class="phx-draw" d="${TAIL}" stroke="#fff" stroke-width="420" stroke-linecap="round" pathLength="1" fill="none"/>
  </mask>
</defs>
<g class="phx-tail" mask="url(#phxReveal)">
  <path d="${TAIL}" stroke="url(#phxSoft)" stroke-width="78" stroke-linecap="round" opacity="0.4" filter="url(#phxGlow)"/>
  <path d="${TAIL}" stroke="url(#phxBody)" stroke-width="58" stroke-linecap="round" filter="url(#phxGlow)"/>
  <path class="phx-spine" d="${TAIL}" stroke="url(#phxSpine)" stroke-width="14" stroke-linecap="round" stroke-dasharray="20 10"/>
  <path d="${TAIL}" stroke="#E9D3A4" stroke-width="2.2" stroke-linecap="round" opacity="0.85" transform="translate(0 -4)"/>
  <path class="phx-pulse" d="${TAIL}" stroke="#F4E2B8" stroke-width="4" stroke-linecap="round" pathLength="1"/>
  <path d="M 1250 250 C 1340 390, 1120 490, 910 530 C 670 570, 420 670, 340 820 C 260 970, 410 1120, 670 1190
    C 940 1260, 1210 1340, 1230 1500 C 1250 1620, 950 1675, 680 1665 C 420 1655, 170 1615, -60 1575"
    stroke="#5B86C5" stroke-width="2.2" stroke-linecap="round" stroke-dasharray="6 8" opacity="0.7"/>
  <g class="phx-wisps" stroke-linecap="round">
    <path d="M 280 820 C 160 760, 120 660, 180 590 C 230 540, 300 600, 260 680 C 230 730, 180 770, 210 820" stroke="url(#phxSoft)" stroke-width="4" opacity="0.8"/>
    <path d="M 620 1230 C 500 1180, 440 1090, 520 1020 C 580 970, 660 1040, 610 1120 C 580 1170, 540 1200, 570 1240" stroke="url(#phxSoft)" stroke-width="4.5" opacity="0.8"/>
    <path d="M 610 1210 C 520 1160, 480 1090, 530 1040" stroke="#C9A35F" stroke-width="2" stroke-dasharray="8 6" opacity="0.8"/>
    <path d="M 1260 1540 C 1380 1460, 1440 1360, 1380 1280 C 1320 1220, 1220 1290, 1270 1380 C 1310 1440, 1360 1480, 1300 1540" stroke="url(#phxSoft)" stroke-width="5" opacity="0.8"/>
  </g>
  <g fill="#C9A35F" opacity="0.85">
    <circle cx="290" cy="800" r="4" filter="url(#phxGlow)"/><circle cx="630" cy="1210" r="4.5" filter="url(#phxGlow)"/>
    <circle cx="1240" cy="1510" r="5" filter="url(#phxGlow)"/><circle cx="720" cy="1680" r="4.5" filter="url(#phxGlow)"/>
  </g>
  <g class="phx-ocellus" transform="translate(940 490)"><circle r="19" fill="#5B86C5" filter="url(#phxGlow)" opacity="0.7"/><circle r="10.5" fill="#FCFBF7" stroke="#24508A" stroke-width="2"/><circle r="4.8" fill="#16325C"/></g>
  <g class="phx-ocellus" transform="translate(280 820)"><circle r="20" fill="#7FA3D6" filter="url(#phxGlow)" opacity="0.7"/><circle r="11" fill="#FCFBF7" stroke="#24508A" stroke-width="2"/><circle r="5.2" fill="#24508A"/></g>
  <g class="phx-ocellus" transform="translate(620 1230)"><circle r="21" fill="#D4B47A" filter="url(#phxGlow)" opacity="0.75"/><circle r="11.5" fill="#FCFBF7" stroke="#B08A45" stroke-width="2"/><circle r="5.4" fill="#8B5E3C"/></g>
    <g class="phx-ocellus" transform="translate(1260 1540)"><circle r="21" fill="#D4B47A" filter="url(#phxGlow)" opacity="0.75"/><circle r="11.5" fill="#FCFBF7" stroke="#B08A45" stroke-width="2"/><circle r="5.4" fill="#8B5E3C"/></g>
</g>
<g class="phx-bird" transform="translate(1260 150)">
  <g class="phx-body">
    <g class="phx-wings">
      <path d="M -10,-20 C 40,-90 120,-110 160,-80 C 130,-60 80,-40 20,-10 Z" fill="rgba(36,80,138,0.55)" stroke="#24508A" stroke-width="2.4"/>
      <path d="M 20,-10 C 70,-70 145,-75 180,-45 C 145,-30 95,-15 35,5 Z" fill="rgba(61,111,176,0.46)" stroke="#3D6FB0" stroke-width="2.2"/>
      <path d="M 35,5 C 90,-45 160,-40 185,-10 C 150,2 105,12 45,18 Z" fill="rgba(91,134,197,0.04)" stroke="#5B86C5" stroke-width="2.1"/>
      <path d="M 45,18 C 95,-15 155,-5 170,20 C 135,25 90,25 40,28 Z" fill="rgba(201,163,95,0.50)" stroke="#B08A45" stroke-width="2.0"/>
      <path d="M -5,-15 Q 80,-70 150,-78" stroke="#5B86C5" stroke-width="1.8"/>
      <path d="M 15,-5 Q 95,-45 165,-42" stroke="#7FA3D6" stroke-width="1.8"/>
      <path d="M 30,8 Q 105,-20 170,-8" stroke="#C9A35F" stroke-width="1.8"/>
      <path d="M -35,10 C -90,25 -140,10 -170,-15 C -140,8 -90,35 -30,32 Z" fill="rgba(36,80,138,0.46)" stroke="#24508A" stroke-width="2.2"/>
      <path d="M -30,32 C -80,50 -130,40 -155,15 C -125,35 -75,55 -20,48 Z" fill="rgba(91,134,197,0.04)" stroke="#5B86C5" stroke-width="2.1"/>
      <path d="M -20,48 C -65,70 -110,65 -130,42 C -105,60 -60,75 -10,60 Z" fill="rgba(201,163,95,0.46)" stroke="#B08A45" stroke-width="2.0"/>
    </g>
    <path d="M -20,-15 C -40,-35 -35,-65 -20,-85 C -5,-105 15,-100 20,-80 C 25,-60 10,-35 0,-15 C -5,10 5,35 15,60 C 5,65 -15,40 -20,-15 Z" fill="#5B86C5" fill-opacity="0.55" stroke="#24508A" stroke-width="2.4"/>
    <circle cx="-5" cy="-35" r="4.5" fill="#F4E2B8" stroke="#8B5E3C" stroke-width="1.8"/>
    <g transform="translate(-15 -88)">
      <path d="M 0,0 C -15,-10 -30,-8 -40,2 C -30,8 -15,6 5,10 C 15,6 15,-4 0,0 Z" fill="rgba(252,251,247,0.62)" stroke="#8B5E3C" stroke-width="2.2"/>
      <path d="M -40,2 L -58,6 L -38,10 Z" fill="#C9A35F" stroke="#8B5E3C" stroke-width="1.8"/>
      <circle class="phx-pearl" cx="-68" cy="8" r="9" fill="#9DB8DE" filter="url(#phxSoftGlow)"/>
      <circle cx="-68" cy="8" r="4.5" fill="#fff"/>
      <circle cx="-16" cy="-1" r="3.2" fill="#16325C"/><circle cx="-17" cy="-2" r="1.2" fill="#fff"/>
      <path d="M 2,-4 C 15,-25 35,-30 50,-20 C 40,-15 25,-15 12,2" stroke="#24508A" stroke-width="2.4" fill="rgba(36,80,138,0.59)"/>
      <path d="M 5,0 C 25,-18 50,-18 68,-8 C 52,-5 35,-5 16,6" stroke="#5B86C5" stroke-width="2.2" fill="rgba(91,134,197,0.50)"/>
      <path d="M 8,4 C 30,-10 60,-8 78,5 C 60,5 40,4 18,10" stroke="#B08A45" stroke-width="2.0" fill="rgba(201,163,95,0.55)"/>
    </g>
  </g>
  <g class="phx-ocellus" transform="translate(20 50)"><circle r="22" fill="#5B86C5" filter="url(#phxGlow)" opacity="0.75"/><circle r="12" fill="#FCFBF7" stroke="#24508A" stroke-width="2"/><circle r="5.5" fill="#16325C"/></g>
</g>
</svg>`;

import { pauseOffscreen } from '../core/motion.js';

let template = null;

/** Trả về một bản sao của hình chim phượng, bọc trong khối cảnh cuộn. */
export function phoenix() {
    if (!template) template = new DOMParser().parseFromString(SVG, 'image/svg+xml').documentElement;
    const wrap = document.createElement('div');
    wrap.className = 'phoenix';
    wrap.setAttribute('aria-hidden', 'true');
    wrap.setAttribute('data-scene', '');
    wrap.append(document.importNode(template, true));
    pauseOffscreen(wrap);
    return wrap;
}
