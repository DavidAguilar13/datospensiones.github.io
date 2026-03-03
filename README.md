
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Pensiones en España — Datos por Provincia.</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Playfair+Display:wght@700;900&family=DM+Sans:wght@300;400;500;600&display=swap" rel="stylesheet">
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
<style>
  :root {
    --bg: #f9f7f4;
    --surface: #ffffff;
    --border: #e8e4de;
    --text-primary: #1a1714;
    --text-secondary: #6b6560;
    --text-muted: #a09a94;
    --accent: #c84b31;
    --accent-light: #f5ede9;
    --amber: #e8a020;
    --green: #2d7a5a;
    --col-low: #fff5eb;
    --col-mid: #f59e44;
    --col-high: #b73a1a;
    --shadow: 0 2px 20px rgba(0,0,0,0.06);
    --shadow-lg: 0 8px 40px rgba(0,0,0,0.10);
  }

  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

  body {
    font-family: 'DM Sans', sans-serif;
    background: var(--bg);
    color: var(--text-primary);
    font-size: 15px;
    line-height: 1.6;
    min-height: 100vh;
  }

  /* HEADER */
  header {
    background: var(--surface);
    border-bottom: 1px solid var(--border);
    padding: 24px 40px 20px;
    display: flex;
    align-items: flex-end;
    justify-content: space-between;
    position: sticky;
    top: 0;
    z-index: 1000;
  }
  .logo-area h1 {
    font-family: 'Playfair Display', serif;
    font-size: 22px;
    font-weight: 900;
    letter-spacing: -0.5px;
    color: var(--text-primary);
  }
  .logo-area h1 span { color: var(--accent); }
  .logo-area p {
    font-size: 12px;
    color: var(--text-muted);
    font-weight: 400;
    margin-top: 2px;
    letter-spacing: 0.3px;
  }
  .header-meta {
    font-size: 12px;
    color: var(--text-muted);
    text-align: right;
    line-height: 1.8;
  }
  .header-meta strong { color: var(--accent); font-weight: 600; }

  /* HERO */
  .hero {
    padding: 40px 40px 0;
    max-width: 1400px;
    margin: 0 auto;
  }
  .hero-title {
    font-family: 'Playfair Display', serif;
    font-size: clamp(32px, 4vw, 56px);
    font-weight: 900;
    line-height: 1.1;
    letter-spacing: -1.5px;
    margin-bottom: 12px;
  }
  .hero-subtitle {
    font-size: 16px;
    color: var(--text-secondary);
    max-width: 600px;
    font-weight: 300;
    line-height: 1.7;
  }

  /* KPI CARDS */
  .kpi-grid {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 16px;
    padding: 28px 40px;
    max-width: 1400px;
    margin: 0 auto;
  }
  .kpi-card {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 20px 24px;
    position: relative;
    overflow: hidden;
    transition: box-shadow 0.2s;
  }
  .kpi-card:hover { box-shadow: var(--shadow); }
  .kpi-card::before {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 3px;
    background: var(--accent);
  }
  .kpi-card.green::before { background: var(--green); }
  .kpi-card.amber::before { background: var(--amber); }
  .kpi-card.blue::before { background: #3b82f6; }
  .kpi-label {
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: 0.8px;
    color: var(--text-muted);
    font-weight: 600;
    margin-bottom: 6px;
  }
  .kpi-value {
    font-family: 'Playfair Display', serif;
    font-size: 32px;
    font-weight: 700;
    line-height: 1;
    color: var(--text-primary);
  }
  .kpi-sub {
    font-size: 12px;
    color: var(--text-secondary);
    margin-top: 4px;
  }

  /* MAIN LAYOUT */
  .main-content {
    max-width: 1400px;
    margin: 0 auto;
    padding: 0 40px 60px;
    display: grid;
    grid-template-columns: 1fr 380px;
    gap: 24px;
  }

  /* CONTROLS */
  .controls {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-bottom: 16px;
    flex-wrap: wrap;
  }
  .controls-label {
    font-size: 12px;
    color: var(--text-muted);
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    margin-right: 4px;
  }
  .pill-btn {
    padding: 6px 16px;
    border-radius: 100px;
    border: 1.5px solid var(--border);
    background: var(--surface);
    font-family: 'DM Sans', sans-serif;
    font-size: 13px;
    font-weight: 500;
    color: var(--text-secondary);
    cursor: pointer;
    transition: all 0.15s;
    white-space: nowrap;
  }
  .pill-btn:hover { border-color: var(--accent); color: var(--accent); }
  .pill-btn.active {
    background: var(--accent);
    border-color: var(--accent);
    color: white;
  }

  /* MAP */
  .map-section {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 16px;
    overflow: hidden;
  }
  .map-header {
    padding: 20px 24px 16px;
    border-bottom: 1px solid var(--border);
    display: flex;
    align-items: center;
    justify-content: space-between;
  }
  .map-title {
    font-size: 14px;
    font-weight: 600;
    color: var(--text-primary);
  }
  .map-hint {
    font-size: 12px;
    color: var(--text-muted);
  }
  #map {
    height: 480px;
    background: #f0ece6;
  }
  .map-footer {
    padding: 14px 24px;
    border-top: 1px solid var(--border);
  }
  .legend {
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 12px;
    color: var(--text-secondary);
  }
  .legend-bar {
    flex: 1;
    max-width: 200px;
    height: 10px;
    border-radius: 5px;
    background: linear-gradient(to right, #fff5eb, #fbb740, #c84b31, #7a1d0a);
  }
  .legend-label { font-weight: 500; font-size: 11px; color: var(--text-muted); }
  .kpi-note {
    font-size: 11px;
    color: var(--text-muted);
    line-height: 1.5;
    margin-top: 8px;
    padding-top: 8px;
    border-top: 1px dashed var(--border);
  }

  /* SIDEBAR */
  .sidebar { display: flex; flex-direction: column; gap: 16px; }

  .panel {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 16px;
    overflow: hidden;
  }
  .panel-header {
    padding: 16px 20px;
    border-bottom: 1px solid var(--border);
    display: flex;
    align-items: center;
    justify-content: space-between;
  }
  .panel-title {
    font-size: 13px;
    font-weight: 600;
    color: var(--text-primary);
    text-transform: uppercase;
    letter-spacing: 0.4px;
  }
  .panel-badge {
    font-size: 11px;
    color: var(--text-muted);
    background: var(--bg);
    border: 1px solid var(--border);
    padding: 2px 8px;
    border-radius: 100px;
  }
  .panel-body { padding: 20px; }

  /* PROVINCE DETAIL */
  .province-placeholder {
    text-align: center;
    padding: 40px 20px;
    color: var(--text-muted);
  }
  .province-placeholder svg { margin-bottom: 12px; opacity: 0.3; }
  .province-placeholder p { font-size: 13px; line-height: 1.6; }

  .province-name-display {
    font-family: 'Playfair Display', serif;
    font-size: 26px;
    font-weight: 700;
    color: var(--text-primary);
    margin-bottom: 4px;
  }
  .province-sub-display {
    font-size: 13px;
    color: var(--text-muted);
    margin-bottom: 20px;
  }
  .province-main-stat {
    background: var(--accent-light);
    border-radius: 10px;
    padding: 16px;
    margin-bottom: 16px;
    display: flex;
    align-items: flex-end;
    justify-content: space-between;
  }
  .province-main-stat .big-num {
    font-family: 'Playfair Display', serif;
    font-size: 38px;
    font-weight: 700;
    color: var(--accent);
    line-height: 1;
  }
  .province-main-stat .big-label {
    font-size: 12px;
    color: var(--text-secondary);
    font-weight: 500;
  }
  .province-main-stat .rank-badge {
    text-align: right;
  }
  .province-main-stat .rank-num {
    font-family: 'Playfair Display', serif;
    font-size: 22px;
    font-weight: 700;
    color: var(--text-primary);
  }
  .province-main-stat .rank-label {
    font-size: 11px;
    color: var(--text-muted);
  }

  .type-rows { display: flex; flex-direction: column; gap: 8px; }
  .type-row {
    display: flex;
    align-items: center;
    gap: 10px;
  }
  .type-dot {
    width: 8px; height: 8px;
    border-radius: 50%;
    flex-shrink: 0;
  }
  .type-name {
    font-size: 13px;
    color: var(--text-secondary);
    flex: 1;
  }
  .type-bar-wrap {
    flex: 1;
    height: 4px;
    background: var(--border);
    border-radius: 2px;
    overflow: hidden;
  }
  .type-bar-fill {
    height: 100%;
    border-radius: 2px;
    transition: width 0.4s ease;
  }
  .type-val {
    font-size: 13px;
    font-weight: 600;
    color: var(--text-primary);
    text-align: right;
    min-width: 60px;
  }

  /* RANKING */
  .ranking-list {
    display: flex;
    flex-direction: column;
    gap: 0;
    max-height: 360px;
    overflow-y: auto;
  }
  .ranking-list::-webkit-scrollbar { width: 4px; }
  .ranking-list::-webkit-scrollbar-track { background: transparent; }
  .ranking-list::-webkit-scrollbar-thumb { background: var(--border); border-radius: 2px; }

  .rank-item {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 9px 0;
    border-bottom: 1px solid var(--border);
    cursor: pointer;
    transition: background 0.1s;
  }
  .rank-item:last-child { border-bottom: none; }
  .rank-item:hover { background: var(--bg); margin: 0 -20px; padding: 9px 20px; }
  .rank-item.highlighted { background: var(--accent-light); margin: 0 -20px; padding: 9px 20px; }
  .rank-num-badge {
    font-size: 11px;
    font-weight: 600;
    color: var(--text-muted);
    min-width: 22px;
    text-align: right;
  }
  .rank-name { font-size: 13px; font-weight: 500; flex: 1; }
  .rank-bar-wrap {
    flex: 1;
    height: 3px;
    background: var(--border);
    border-radius: 2px;
    overflow: hidden;
  }
  .rank-bar-fill {
    height: 100%;
    border-radius: 2px;
    background: var(--accent);
    transition: width 0.3s ease;
  }
  .rank-value {
    font-size: 13px;
    font-weight: 600;
    min-width: 58px;
    text-align: right;
  }

  /* CHART SECTION */
  .chart-section {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 16px;
    overflow: hidden;
    margin-top: 0;
  }
  .chart-header {
    padding: 20px 24px 16px;
    border-bottom: 1px solid var(--border);
  }
  .chart-title { font-size: 14px; font-weight: 600; }
  .chart-subtitle { font-size: 12px; color: var(--text-muted); margin-top: 2px; }
  .chart-body { padding: 20px 24px; }
  #barChart { max-height: 300px; }

  /* TOOLTIP */
  .leaflet-tooltip-custom {
    background: var(--text-primary) !important;
    border: none !important;
    border-radius: 8px !important;
    padding: 10px 14px !important;
    color: white !important;
    font-family: 'DM Sans', sans-serif !important;
    font-size: 13px !important;
    box-shadow: var(--shadow-lg) !important;
    pointer-events: none !important;
  }
  .leaflet-tooltip-custom::before { display: none !important; }
  .tip-name { font-weight: 600; margin-bottom: 4px; }
  .tip-val { font-size: 18px; font-weight: 700; color: #fbbf24; }
  .tip-sub { font-size: 11px; color: rgba(255,255,255,0.6); margin-top: 2px; }

  /* FOOTER */
  footer {
    text-align: center;
    padding: 30px;
    font-size: 12px;
    color: var(--text-muted);
    border-top: 1px solid var(--border);
    line-height: 1.8;
  }
  footer a { color: var(--accent); text-decoration: none; }

  @media (max-width: 1100px) {
    .main-content { grid-template-columns: 1fr; }
    .kpi-grid { grid-template-columns: repeat(2, 1fr); }
    header, .hero, .kpi-grid, .main-content { padding-left: 20px; padding-right: 20px; }
  }
</style>
</head>
<body>

<header>
  <div class="logo-area">
    <h1>datos<span>pensiones</span>.es</h1>
    <p>Estadísticas sobre pensiones contributivas y no contributivas del sistema de la Seguridad Social</p>
  </div>
  <div class="header-meta">
    Datos a <strong>1 de febrero de 2026</strong><br>
    Fuente: INSS · Ministerio de Inclusión
  </div>
</header>

<div class="hero">
  <div class="hero-title">¿Cuánto cobran<br>los pensionistas de tu provincia?</div>
  <div class="hero-subtitle">Análisis de las pensiones contributivas y no contributivas del sistema de la Seguridad Social en las 50 provincias y las 2 ciudades autónomas de España.</div>
</div>

<div class="kpi-grid">
  <div class="kpi-card">
    <div class="kpi-label">Media nacional</div>
    <div class="kpi-value" id="kpi-media">—</div>
    <div class="kpi-sub">€ / mes · Total sistema</div>
  </div>
  <div class="kpi-card green">
    <div class="kpi-label">Provincia más alta</div>
    <div class="kpi-value" id="kpi-max-val">—</div>
    <div class="kpi-sub" id="kpi-max-name">—</div>
  </div>
  <div class="kpi-card amber">
    <div class="kpi-label">Provincia más baja</div>
    <div class="kpi-value" id="kpi-min-val">—</div>
    <div class="kpi-sub" id="kpi-min-name">—</div>
  </div>
  <div class="kpi-card blue">
    <div class="kpi-label">Total pensiones en España</div>
    <div class="kpi-value" id="kpi-total">—</div>
    <div class="kpi-sub"> *Un pensionista puede tener dos pensiones a la vez (como de jubilación y viuedad).</div>
    <div class="kpi-note" id="kpi-total-note">Incluye jubilación, incapacidad permanente, viudedad, orfandad y a favor de familiares. Datos a 1 de febrero de 2026.</div>
  </div>
</div>

<div class="main-content">

  <!-- LEFT: MAP + CHART -->
  <div>
    <div class="controls">
      <span class="controls-label">Mostrar</span>
      <button class="pill-btn active" onclick="setType('total_media')">Total</button>
      <button class="pill-btn" onclick="setType('jub_media')">Jubilación</button>
      <button class="pill-btn" onclick="setType('ip_media')">Incap. Permanente</button>
      <button class="pill-btn" onclick="setType('viu_media')">Viudedad</button>
      <button class="pill-btn" onclick="setType('orf_media')">Orfandad</button>
    </div>

    <div class="map-section">
      <div class="map-header">
        <div class="map-title" id="map-title">Pensión media por provincia · Total sistema</div>
        <div class="map-hint">Pasa el cursor sobre una provincia</div>
      </div>
      <div id="map"></div>
      <div class="map-footer">
        <div class="legend">
          <span class="legend-label" id="leg-min">—</span>
          <div class="legend-bar"></div>
          <span class="legend-label" id="leg-max">—</span>
          <span style="margin-left:12px;font-size:11px;color:var(--text-muted)">€/mes</span>
        </div>
      </div>
    </div>

    <div class="chart-section" style="margin-top:16px;">
      <div class="chart-header">
        <div class="chart-title" id="chart-title">Pensión media por tipo — Selecciona una provincia</div>
        <div class="chart-subtitle" id="chart-subtitle">Haz clic en cualquier provincia del mapa</div>
      </div>
      <div class="chart-body">
        <canvas id="barChart"></canvas>
      </div>
    </div>
  </div>

  <!-- RIGHT: SIDEBAR -->
  <div class="sidebar">

    <!-- Province detail -->
    <div class="panel">
      <div class="panel-header">
        <div class="panel-title">Detalle de provincia</div>
        <div class="panel-badge" id="selected-label">Ninguna</div>
      </div>
      <div class="panel-body" id="province-detail">
        <div class="province-placeholder">
          <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
            <path d="M12 2C8.13 2 5 5.13 5 9c0 5.25 7 13 7 13s7-7.75 7-13c0-3.87-3.13-7-7-7z"/>
            <circle cx="12" cy="9" r="2.5"/>
          </svg>
          <p>Haz clic sobre cualquier<br>provincia en el mapa</p>
        </div>
      </div>
    </div>

    <!-- Ranking -->
    <div class="panel">
      <div class="panel-header">
        <div class="panel-title">Ranking</div>
        <div class="panel-badge" id="rank-label">Total · mayor a menor</div>
      </div>
      <div class="panel-body" style="padding:0 20px;">
        <div class="ranking-list" id="ranking-list"></div>
      </div>
    </div>

  </div>
</div>

<footer>
  Datos extraídos del <a href="https://www.seg-social.es" target="_blank">Instituto Nacional de la Seguridad Social (INSS)</a><br>
  Creado por David Aguilar
</footer>

<script>
// ─── DATA ───────────────────────────────────────────────────────────────────
const NATIONAL = {"total_num": 10446888, "total_media": 1366.2, "ip_num": 1055274, "ip_media": 1253.57, "jub_num": 6670447, "jub_media": 1566.81, "viu_num": 2339414, "viu_media": 972.79, "orf_num": 335157, "orf_media": 550.14, "fam_num": 46596, "fam_media": 819.46};
const PENSIONS = {
  "Almería": {
    "total_num": 121243,
    "total_media": 1128.46,
    "ip_num": 11823,
    "ip_media": 1162.45,
    "jub_num": 74325,
    "jub_media": 1291.9,
    "viu_num": 29076,
    "viu_media": 829.27,
    "orf_num": 5488,
    "orf_media": 461.93,
    "fam_num": 531,
    "fam_media": 765.35
  },
  "Cádiz": {
    "total_num": 237683,
    "total_media": 1357.04,
    "ip_num": 36775,
    "ip_media": 1248.26,
    "jub_num": 130580,
    "jub_media": 1611.15,
    "viu_num": 57127,
    "viu_media": 1017.57,
    "orf_num": 10289,
    "orf_media": 562.55,
    "fam_num": 2912,
    "fam_media": 803.07
  },
  "Córdoba": {
    "total_num": 184658,
    "total_media": 1155.61,
    "ip_num": 17811,
    "ip_media": 1105.66,
    "jub_num": 116184,
    "jub_media": 1320.06,
    "viu_num": 42502,
    "viu_media": 839.41,
    "orf_num": 6735,
    "orf_media": 530.62,
    "fam_num": 1426,
    "fam_media": 756.95
  },
  "Granada": {
    "total_num": 204962,
    "total_media": 1177.07,
    "ip_num": 25097,
    "ip_media": 1172.22,
    "jub_num": 125915,
    "jub_media": 1350.34,
    "viu_num": 44833,
    "viu_media": 820.82,
    "orf_num": 7671,
    "orf_media": 504.16,
    "fam_num": 1446,
    "fam_media": 788.59
  },
  "Huelva": {
    "total_num": 107219,
    "total_media": 1241.75,
    "ip_num": 14027,
    "ip_media": 1111.95,
    "jub_num": 62868,
    "jub_media": 1452.45,
    "viu_num": 25149,
    "viu_media": 926.09,
    "orf_num": 4341,
    "orf_media": 524.95,
    "fam_num": 834,
    "fam_media": 792.1
  },
  "Jaén": {
    "total_num": 152299,
    "total_media": 1143.64,
    "ip_num": 23227,
    "ip_media": 1098.13,
    "jub_num": 87503,
    "jub_media": 1309.66,
    "viu_num": 35499,
    "viu_media": 866.06,
    "orf_num": 5226,
    "orf_media": 520.15,
    "fam_num": 844,
    "fam_media": 719.79
  },
  "Málaga": {
    "total_num": 298361,
    "total_media": 1246.62,
    "ip_num": 33088,
    "ip_media": 1228.78,
    "jub_num": 183155,
    "jub_media": 1433.28,
    "viu_num": 67747,
    "viu_media": 901.49,
    "orf_num": 12636,
    "orf_media": 504.06,
    "fam_num": 1735,
    "fam_media": 767.01
  },
  "Sevilla": {
    "total_num": 411644,
    "total_media": 1267.39,
    "ip_num": 64550,
    "ip_media": 1145.19,
    "jub_num": 236334,
    "jub_media": 1482.18,
    "viu_num": 92061,
    "viu_media": 940.82,
    "orf_num": 15792,
    "orf_media": 544.22,
    "fam_num": 2907,
    "fam_media": 790.13
  },
  "Huesca": {
    "total_num": 55410,
    "total_media": 1319.55,
    "ip_num": 4993,
    "ip_media": 1202.09,
    "jub_num": 36047,
    "jub_media": 1501.95,
    "viu_num": 12673,
    "viu_media": 950.13,
    "orf_num": 1618,
    "orf_media": 538.35,
    "fam_num": 79,
    "fam_media": 774.9
  },
  "Teruel": {
    "total_num": 36444,
    "total_media": 1331.18,
    "ip_num": 3673,
    "ip_media": 1185.94,
    "jub_num": 23757,
    "jub_media": 1520.77,
    "viu_num": 7912,
    "viu_media": 935.32,
    "orf_num": 1004,
    "orf_media": 540.42,
    "fam_num": 98,
    "fam_media": 874.79
  },
  "Zaragoza": {
    "total_num": 227630,
    "total_media": 1490.72,
    "ip_num": 14341,
    "ip_media": 1373.77,
    "jub_num": 154579,
    "jub_media": 1688.52,
    "viu_num": 51500,
    "viu_media": 1053.97,
    "orf_num": 6581,
    "orf_media": 575.3,
    "fam_num": 629,
    "fam_media": 884.2
  },
  "Asturias": {
    "total_num": 302888,
    "total_media": 1575.22,
    "ip_num": 28589,
    "ip_media": 1409.4,
    "jub_num": 187932,
    "jub_media": 1835.0,
    "viu_num": 75684,
    "viu_media": 1109.98,
    "orf_num": 8632,
    "orf_media": 665.25,
    "fam_num": 2051,
    "fam_media": 1081.83
  },
  "Illes Balears": {
    "total_num": 215113,
    "total_media": 1274.75,
    "ip_num": 18732,
    "ip_media": 1186.35,
    "jub_num": 144750,
    "jub_media": 1445.08,
    "viu_num": 45470,
    "viu_media": 877.65,
    "orf_num": 6045,
    "orf_media": 466.23,
    "fam_num": 116,
    "fam_media": 795.72
  },
  "Las Palmas": {
    "total_num": 199745,
    "total_media": 1266.26,
    "ip_num": 34273,
    "ip_media": 1254.74,
    "jub_num": 111327,
    "jub_media": 1470.07,
    "viu_num": 43241,
    "viu_media": 926.0,
    "orf_num": 9111,
    "orf_media": 528.32,
    "fam_num": 1793,
    "fam_media": 787.04
  },
  "Santa Cruz de Tenerife": {
    "total_num": 178436,
    "total_media": 1225.34,
    "ip_num": 26816,
    "ip_media": 1126.85,
    "jub_num": 103204,
    "jub_media": 1427.19,
    "viu_num": 40423,
    "viu_media": 909.07,
    "orf_num": 7139,
    "orf_media": 516.38,
    "fam_num": 854,
    "fam_media": 821.16
  },
  "Cantabria": {
    "total_num": 149434,
    "total_media": 1435.5,
    "ip_num": 14156,
    "ip_media": 1304.92,
    "jub_num": 94596,
    "jub_media": 1653.99,
    "viu_num": 34737,
    "viu_media": 1024.54,
    "orf_num": 4562,
    "orf_media": 601.61,
    "fam_num": 1383,
    "fam_media": 900.61
  },
  "Albacete": {
    "total_num": 77089,
    "total_media": 1252.43,
    "ip_num": 6978,
    "ip_media": 1183.37,
    "jub_num": 48141,
    "jub_media": 1433.12,
    "viu_num": 18363,
    "viu_media": 934.93,
    "orf_num": 2844,
    "orf_media": 557.86,
    "fam_num": 763,
    "fam_media": 712.8
  },
  "Ciudad Real": {
    "total_num": 106314,
    "total_media": 1286.61,
    "ip_num": 17061,
    "ip_media": 1141.22,
    "jub_num": 58223,
    "jub_media": 1512.19,
    "viu_num": 26185,
    "viu_media": 1003.61,
    "orf_num": 3945,
    "orf_media": 577.63,
    "fam_num": 900,
    "fam_media": 790.3
  },
  "Cuenca": {
    "total_num": 46141,
    "total_media": 1191.5,
    "ip_num": 6732,
    "ip_media": 1102.7,
    "jub_num": 26812,
    "jub_media": 1362.18,
    "viu_num": 10705,
    "viu_media": 926.36,
    "orf_num": 1583,
    "orf_media": 564.51,
    "fam_num": 309,
    "fam_media": 714.43
  },
  "Guadalajara": {
    "total_num": 47589,
    "total_media": 1447.47,
    "ip_num": 6250,
    "ip_media": 1270.32,
    "jub_num": 30167,
    "jub_media": 1662.89,
    "viu_num": 9499,
    "viu_media": 1036.69,
    "orf_num": 1568,
    "orf_media": 538.87,
    "fam_num": 105,
    "fam_media": 829.74
  },
  "Toledo": {
    "total_num": 129328,
    "total_media": 1272.18,
    "ip_num": 12199,
    "ip_media": 1152.16,
    "jub_num": 81977,
    "jub_media": 1450.54,
    "viu_num": 30010,
    "viu_media": 958.57,
    "orf_num": 4567,
    "orf_media": 519.39,
    "fam_num": 575,
    "fam_media": 736.54
  },
  "Ávila": {
    "total_num": 40282,
    "total_media": 1213.22,
    "ip_num": 3567,
    "ip_media": 1128.04,
    "jub_num": 25760,
    "jub_media": 1372.7,
    "viu_num": 9468,
    "viu_media": 905.09,
    "orf_num": 1253,
    "orf_media": 591.64,
    "fam_num": 234,
    "fam_media": 750.8
  },
  "Burgos": {
    "total_num": 95428,
    "total_media": 1466.53,
    "ip_num": 5517,
    "ip_media": 1376.95,
    "jub_num": 66371,
    "jub_media": 1655.39,
    "viu_num": 20453,
    "viu_media": 1006.12,
    "orf_num": 2771,
    "orf_media": 585.61,
    "fam_num": 316,
    "fam_media": 885.7
  },
  "León": {
    "total_num": 140863,
    "total_media": 1363.83,
    "ip_num": 14405,
    "ip_media": 1312.02,
    "jub_num": 88052,
    "jub_media": 1567.84,
    "viu_num": 33286,
    "viu_media": 952.55,
    "orf_num": 4009,
    "orf_media": 606.24,
    "fam_num": 1111,
    "fam_media": 922.39
  },
  "Palencia": {
    "total_num": 44576,
    "total_media": 1399.29,
    "ip_num": 4153,
    "ip_media": 1212.24,
    "jub_num": 28775,
    "jub_media": 1603.89,
    "viu_num": 10033,
    "viu_media": 1007.85,
    "orf_num": 1333,
    "orf_media": 627.8,
    "fam_num": 282,
    "fam_media": 849.87
  },
  "Salamanca": {
    "total_num": 83624,
    "total_media": 1285.36,
    "ip_num": 6004,
    "ip_media": 1182.59,
    "jub_num": 54774,
    "jub_media": 1458.82,
    "viu_num": 19746,
    "viu_media": 935.67,
    "orf_num": 2444,
    "orf_media": 609.86,
    "fam_num": 656,
    "fam_media": 785.09
  },
  "Segovia": {
    "total_num": 36132,
    "total_media": 1308.91,
    "ip_num": 2769,
    "ip_media": 1139.23,
    "jub_num": 23936,
    "jub_media": 1492.66,
    "viu_num": 8222,
    "viu_media": 936.93,
    "orf_num": 1067,
    "orf_media": 562.85,
    "fam_num": 138,
    "fam_media": 772.86
  },
  "Soria": {
    "total_num": 23135,
    "total_media": 1328.39,
    "ip_num": 1324,
    "ip_media": 1239.92,
    "jub_num": 16025,
    "jub_media": 1500.85,
    "viu_num": 5035,
    "viu_media": 910.7,
    "orf_num": 678,
    "orf_media": 585.92,
    "fam_num": 73,
    "fam_media": 778.12
  },
  "Valladolid": {
    "total_num": 125492,
    "total_media": 1488.65,
    "ip_num": 11350,
    "ip_media": 1219.2,
    "jub_num": 81404,
    "jub_media": 1712.24,
    "viu_num": 28486,
    "viu_media": 1083.28,
    "orf_num": 3572,
    "orf_media": 600.87,
    "fam_num": 680,
    "fam_media": 864.69
  },
  "Zamora": {
    "total_num": 47733,
    "total_media": 1186.84,
    "ip_num": 2257,
    "ip_media": 1150.34,
    "jub_num": 31374,
    "jub_media": 1339.8,
    "viu_num": 12179,
    "viu_media": 890.68,
    "orf_num": 1507,
    "orf_media": 582.79,
    "fam_num": 416,
    "fam_media": 708.27
  },
  "Barcelona": {
    "total_num": 1354048,
    "total_media": 1459.3,
    "ip_num": 123824,
    "ip_media": 1415.27,
    "jub_num": 904619,
    "jub_media": 1643.34,
    "viu_num": 287990,
    "viu_media": 1016.49,
    "orf_num": 36523,
    "orf_media": 558.19,
    "fam_num": 1092,
    "fam_media": 913.29
  },
  "Girona": {
    "total_num": 172343,
    "total_media": 1286.92,
    "ip_num": 14329,
    "ip_media": 1243.56,
    "jub_num": 117203,
    "jub_media": 1452.92,
    "viu_num": 36014,
    "viu_media": 873.52,
    "orf_num": 4740,
    "orf_media": 459.26,
    "fam_num": 57,
    "fam_media": 875.78
  },
  "Lleida": {
    "total_num": 104812,
    "total_media": 1237.84,
    "ip_num": 11792,
    "ip_media": 1218.89,
    "jub_num": 66266,
    "jub_media": 1412.57,
    "viu_num": 23535,
    "viu_media": 856.33,
    "orf_num": 3157,
    "orf_media": 491.58,
    "fam_num": 62,
    "fam_media": 900.62
  },
  "Tarragona": {
    "total_num": 185538,
    "total_media": 1340.23,
    "ip_num": 19000,
    "ip_media": 1272.16,
    "jub_num": 120556,
    "jub_media": 1523.66,
    "viu_num": 40342,
    "viu_media": 939.82,
    "orf_num": 5443,
    "orf_media": 504.04,
    "fam_num": 197,
    "fam_media": 758.83
  },
  "Alicante": {
    "total_num": 352958,
    "total_media": 1188.0,
    "ip_num": 25899,
    "ip_media": 1149.86,
    "jub_num": 231156,
    "jub_media": 1342.28,
    "viu_num": 82471,
    "viu_media": 877.27,
    "orf_num": 12191,
    "orf_media": 487.57,
    "fam_num": 1241,
    "fam_media": 776.66
  },
  "Castellón": {
    "total_num": 142843,
    "total_media": 1237.44,
    "ip_num": 15693,
    "ip_media": 1209.53,
    "jub_num": 91868,
    "jub_media": 1394.97,
    "viu_num": 30537,
    "viu_media": 889.53,
    "orf_num": 4514,
    "orf_media": 505.24,
    "fam_num": 231,
    "fam_media": 780.91
  },
  "Valencia": {
    "total_num": 578558,
    "total_media": 1319.26,
    "ip_num": 62273,
    "ip_media": 1215.96,
    "jub_num": 363446,
    "jub_media": 1518.47,
    "viu_num": 131631,
    "viu_media": 941.48,
    "orf_num": 20115,
    "orf_media": 538.4,
    "fam_num": 1093,
    "fam_media": 831.45
  },
  "Badajoz": {
    "total_num": 145669,
    "total_media": 1173.05,
    "ip_num": 20664,
    "ip_media": 1077.12,
    "jub_num": 82384,
    "jub_media": 1358.41,
    "viu_num": 35114,
    "viu_media": 920.98,
    "orf_num": 5954,
    "orf_media": 545.72,
    "fam_num": 1553,
    "fam_media": 720.49
  },
  "Cáceres": {
    "total_num": 101294,
    "total_media": 1155.24,
    "ip_num": 11003,
    "ip_media": 1092.38,
    "jub_num": 62937,
    "jub_media": 1309.98,
    "viu_num": 23558,
    "viu_media": 862.74,
    "orf_num": 3171,
    "orf_media": 557.15,
    "fam_num": 625,
    "fam_media": 739.14
  },
  "A Coruña": {
    "total_num": 311504,
    "total_media": 1231.84,
    "ip_num": 32329,
    "ip_media": 1139.87,
    "jub_num": 194326,
    "jub_media": 1417.32,
    "viu_num": 73321,
    "viu_media": 878.75,
    "orf_num": 9072,
    "orf_media": 568.84,
    "fam_num": 2456,
    "fam_media": 756.63
  },
  "Lugo": {
    "total_num": 112634,
    "total_media": 1079.26,
    "ip_num": 12560,
    "ip_media": 1127.47,
    "jub_num": 70013,
    "jub_media": 1229.49,
    "viu_num": 26067,
    "viu_media": 729.17,
    "orf_num": 2940,
    "orf_media": 541.41,
    "fam_num": 1054,
    "fam_media": 683.36
  },
  "Ourense": {
    "total_num": 109247,
    "total_media": 1019.24,
    "ip_num": 13602,
    "ip_media": 1146.31,
    "jub_num": 67151,
    "jub_media": 1131.24,
    "viu_num": 24462,
    "viu_media": 715.77,
    "orf_num": 2847,
    "orf_media": 516.79,
    "fam_num": 1185,
    "fam_media": 685.95
  },
  "Pontevedra": {
    "total_num": 254056,
    "total_media": 1220.36,
    "ip_num": 26859,
    "ip_media": 1136.35,
    "jub_num": 158531,
    "jub_media": 1406.26,
    "viu_num": 58189,
    "viu_media": 865.96,
    "orf_num": 8185,
    "orf_media": 543.55,
    "fam_num": 2292,
    "fam_media": 760.93
  },
  "Madrid": {
    "total_num": 1291865,
    "total_media": 1576.74,
    "ip_num": 98608,
    "ip_media": 1355.13,
    "jub_num": 881869,
    "jub_media": 1790.49,
    "viu_num": 273598,
    "viu_media": 1101.22,
    "orf_num": 35079,
    "orf_media": 584.68,
    "fam_num": 2711,
    "fam_media": 932.33
  },
  "Murcia": {
    "total_num": 270553,
    "total_media": 1222.11,
    "ip_num": 32772,
    "ip_media": 1142.19,
    "jub_num": 162170,
    "jub_media": 1417.9,
    "viu_num": 62140,
    "viu_media": 902.37,
    "orf_num": 11809,
    "orf_media": 503.65,
    "fam_num": 1662,
    "fam_media": 754.14
  },
  "Navarra": {
    "total_num": 149020,
    "total_media": 1558.51,
    "ip_num": 10595,
    "ip_media": 1485.03,
    "jub_num": 103808,
    "jub_media": 1749.23,
    "viu_num": 30027,
    "viu_media": 1071.32,
    "orf_num": 4227,
    "orf_media": 577.73,
    "fam_num": 363,
    "fam_media": 884.54
  },
  "Álava": {
    "total_num": 85049,
    "total_media": 1702.61,
    "ip_num": 6858,
    "ip_media": 1580.69,
    "jub_num": 58671,
    "jub_media": 1917.57,
    "viu_num": 17287,
    "viu_media": 1159.62,
    "orf_num": 2074,
    "orf_media": 610.05,
    "fam_num": 159,
    "fam_media": 925.83
  },
  "Gipuzkoa": {
    "total_num": 197670,
    "total_media": 1645.93,
    "ip_num": 13078,
    "ip_media": 1628.6,
    "jub_num": 136284,
    "jub_media": 1846.54,
    "viu_num": 42954,
    "viu_media": 1136.15,
    "orf_num": 4832,
    "orf_media": 633.16,
    "fam_num": 522,
    "fam_media": 1030.28
  },
  "Bizkaia": {
    "total_num": 305761,
    "total_media": 1689.25,
    "ip_num": 23178,
    "ip_media": 1567.02,
    "jub_num": 200213,
    "jub_media": 1933.39,
    "viu_num": 71971,
    "viu_media": 1186.89,
    "orf_num": 8797,
    "orf_media": 682.63,
    "fam_num": 1602,
    "fam_media": 1042.94
  },
  "La Rioja": {
    "total_num": 75852,
    "total_media": 1355.8,
    "ip_num": 5269,
    "ip_media": 1291.7,
    "jub_num": 52467,
    "jub_media": 1514.91,
    "viu_num": 15980,
    "viu_media": 961.74,
    "orf_num": 1963,
    "orf_media": 531.68,
    "fam_num": 173,
    "fam_media": 807.2
  },
  "Ceuta": {
    "total_num": 9526,
    "total_media": 1404.71,
    "ip_num": 1160,
    "ip_media": 1423.5,
    "jub_num": 4962,
    "jub_media": 1733.92,
    "viu_num": 2624,
    "viu_media": 1047.64,
    "orf_num": 733,
    "orf_media": 454.65,
    "fam_num": 47,
    "fam_media": 937.59
  },
  "Melilla": {
    "total_num": 9193,
    "total_media": 1342.17,
    "ip_num": 1392,
    "ip_media": 1377.94,
    "jub_num": 4700,
    "jub_media": 1663.41,
    "viu_num": 2298,
    "viu_media": 982.1,
    "orf_num": 780,
    "orf_media": 417.84,
    "fam_num": 23,
    "fam_media": 857.73
  }
};

// GeoJSON province name → our data key
const NAME_MAP = {
  // Andalucía
  "Almería":"Almería","Almeria":"Almería",
  "Cádiz":"Cádiz","Cadiz":"Cádiz",
  "Córdoba":"Córdoba","Cordoba":"Córdoba",
  "Granada":"Granada",
  "Huelva":"Huelva",
  "Jaén":"Jaén","Jaen":"Jaén",
  "Málaga":"Málaga","Malaga":"Málaga",
  "Sevilla":"Sevilla",
  // Aragón
  "Huesca":"Huesca","Teruel":"Teruel","Zaragoza":"Zaragoza",
  // Asturias
  "Asturias":"Asturias","Principado de Asturias":"Asturias",
  // Baleares — todas las variantes
  "Baleares":"Illes Balears","Islas Baleares":"Illes Balears",
  "Illes Balears":"Illes Balears","Balears":"Illes Balears","Illes Balears (Balearic Islands)":"Illes Balears",
  // Canarias
  "Las Palmas":"Las Palmas","Gran Canaria":"Las Palmas",
  "Santa Cruz de Tenerife":"Santa Cruz de Tenerife",
  "Santa Cruz De Tenerife":"Santa Cruz de Tenerife",
  "Tenerife":"Santa Cruz de Tenerife","S.C. Tenerife":"Santa Cruz de Tenerife",
  "SC Tenerife":"Santa Cruz de Tenerife","S.C.Tenerife":"Santa Cruz de Tenerife",
  // Cantabria
  "Cantabria":"Cantabria",
  // Castilla-La Mancha
  "Albacete":"Albacete","Ciudad Real":"Ciudad Real","Cuenca":"Cuenca",
  "Guadalajara":"Guadalajara","Toledo":"Toledo",
  // Castilla y León
  "Ávila":"Ávila","Avila":"Ávila","Burgos":"Burgos","León":"León","Leon":"León",
  "Palencia":"Palencia","Salamanca":"Salamanca","Segovia":"Segovia",
  "Soria":"Soria","Valladolid":"Valladolid","Zamora":"Zamora",
  // Cataluña
  "Barcelona":"Barcelona",
  "Girona":"Girona","Gerona":"Girona",
  "Lleida":"Lleida","Lérida":"Lleida","Lerida":"Lleida",
  "Tarragona":"Tarragona",
  // Comunitat Valenciana — variantes oficiales y castellanizadas
  "Alicante":"Alicante","Alacant":"Alicante","Alicante/Alacant":"Alicante","Alacant/Alicante":"Alicante",
  "Castellón":"Castellón","Castelló":"Castellón","Castellon":"Castellón",
  "Castellón de la Plana":"Castellón","Castelló de la Plana":"Castellón",
  "Castelló/Castellón":"Castellón","Castellón/Castelló":"Castellón",
  "Valencia":"Valencia","València":"Valencia","Valencia/València":"Valencia","València/Valencia":"Valencia",
  // Extremadura
  "Badajoz":"Badajoz","Cáceres":"Cáceres","Caceres":"Cáceres",
  // Galicia
  "A Coruña":"A Coruña","La Coruña":"A Coruña","Coruña (A)":"A Coruña",
  "La Coruna":"A Coruña","A Coruna":"A Coruña",
  "Lugo":"Lugo",
  "Ourense":"Ourense","Orense":"Ourense",
  "Pontevedra":"Pontevedra",
  // Madrid
  "Madrid":"Madrid","Comunidad de Madrid":"Madrid",
  // Murcia
  "Murcia":"Murcia","Región de Murcia":"Murcia",
  // Navarra
  "Navarra":"Navarra","Nafarroa":"Navarra","Comunidad Foral de Navarra":"Navarra",
  // País Vasco — todas las variantes
  "Álava":"Álava","Alava":"Álava","Araba":"Álava","Araba/Álava":"Álava",
  "Gipuzkoa":"Gipuzkoa","Guipúzcoa":"Gipuzkoa","Guipuzcoa":"Gipuzkoa","Gipuzkoa/Guipúzcoa":"Gipuzkoa","Guipúzcoa/Gipuzkoa":"Gipuzkoa",
  "Bizkaia":"Bizkaia","Vizcaya":"Bizkaia","Bizkaia/Vizcaya":"Bizkaia","Vizcaya/Bizkaia":"Bizkaia",
  // La Rioja
  "La Rioja":"La Rioja","Rioja":"La Rioja",
  // Ciudades autónomas
  "Ceuta":"Ceuta","Melilla":"Melilla"
};

const TYPE_META = {
  total_media: { label: 'Total sistema', color: '#c84b31' },
  jub_media:   { label: 'Jubilación',    color: '#2d7a5a' },
  ip_media:    { label: 'Incap. Permanente', color: '#3b82f6' },
  viu_media:   { label: 'Viudedad',      color: '#7c3aed' },
  orf_media:   { label: 'Orfandad',      color: '#e8a020' },
};

const TYPE_COLORS = {
  jub_media: '#2d7a5a', ip_media: '#3b82f6',
  viu_media: '#7c3aed', orf_media: '#e8a020', fam_media: '#ec4899'
};

// ─── STATE ───────────────────────────────────────────────────────────────────
let currentType = 'total_media';
let selectedProvince = null;
let geojsonLayer = null;
let map, barChart;

// ─── INIT ────────────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  initKPIs();
  initMap();
  initBarChart();
  buildRanking();
});

function fmt(v) { return v != null ? v.toFixed(2).replace('.', ',') + ' €' : '—'; }
function fmtNum(v) { return v != null ? v.toLocaleString('es-ES') : '—'; }

function initKPIs() {
  // Use official national totals from Excel
  document.getElementById('kpi-media').textContent = NATIONAL.total_media.toFixed(2).replace('.',',') + ' €';
  document.getElementById('kpi-total').textContent = fmtNum(NATIONAL.total_num);
  const sorted = Object.entries(PENSIONS).sort((a,b)=>b[1].total_media-a[1].total_media);
  const [maxName, maxD] = sorted[0];
  const [minName, minD] = sorted[sorted.length-1];
  document.getElementById('kpi-max-val').textContent = maxD.total_media.toFixed(2).replace('.',',') + ' €';
  document.getElementById('kpi-max-name').textContent = maxName;
  document.getElementById('kpi-min-val').textContent = minD.total_media.toFixed(2).replace('.',',') + ' €';
  document.getElementById('kpi-min-name').textContent = minName;
}

// ─── MAP ─────────────────────────────────────────────────────────────────────
function getColor(val, min, max) {
  const t = (val - min) / (max - min);
  const stops = [
    [255,245,235], [251,191,64], [200,75,49], [122,29,10]
  ];
  const seg = t * (stops.length-1);
  const i = Math.floor(seg), f = seg - i;
  const a = stops[Math.min(i, stops.length-1)];
  const b = stops[Math.min(i+1, stops.length-1)];
  const r = Math.round(a[0]+(b[0]-a[0])*f);
  const g = Math.round(a[1]+(b[1]-a[1])*f);
  const bl = Math.round(a[2]+(b[2]-a[2])*f);
  return `rgb(${r},${g},${bl})`;
}

function initMap() {
  map = L.map('map', {
    center: [40.4, -3.7], zoom: 5,
    zoomControl: true, attributionControl: false,
    scrollWheelZoom: false
  });

  // Subtle tile layer
  L.tileLayer('https://{s}.basemaps.cartocdn.com/light_nolabels/{z}/{x}/{y}{r}.png', {
    maxZoom: 19
  }).addTo(map);

  loadGeoJSON();
}

function loadGeoJSON() {
  fetch('https://cdn.jsdelivr.net/gh/codeforgermany/click_that_hood@main/public/data/spain-provinces.geojson')
    .then(r => r.json())
    .then(data => {
      renderMap(data);
    })
    .catch(() => {
      // Try alternative
      fetch('https://raw.githubusercontent.com/codeforamerica/click_that_hood/master/public/data/spain-provinces.geojson')
        .then(r => r.json())
        .then(data => renderMap(data))
        .catch(() => {
          document.getElementById('map').innerHTML = '<div style="padding:40px;text-align:center;color:#999">No se pudo cargar el mapa. Asegúrate de tener conexión a internet.</div>';
        });
    });
}

function renderMap(geojsonData) {
  const vals = Object.values(PENSIONS)
    .map(d => d[currentType])
    .filter(Boolean);
  const min = Math.min(...vals), max = Math.max(...vals);

  document.getElementById('leg-min').textContent = min.toFixed(0) + ' €';
  document.getElementById('leg-max').textContent = max.toFixed(0) + ' €';

  if (geojsonLayer) map.removeLayer(geojsonLayer);

  // DEBUG: detect all property keys available in first feature
  if (geojsonData.features.length) {
    console.log('GeoJSON properties disponibles:', Object.keys(geojsonData.features[0].properties));
  }
  // Detect which name property the GeoJSON uses
  const nameProp = (() => {
    const sample = geojsonData.features[0]?.properties || {};
    return ['name','NAME','nombre','NOMBRE','provincia','PROVINCIA','nom','NOM']
      .find(k => sample[k]) || 'name';
  })();
  console.log('Usando propiedad de nombre:', nameProp);

  // DEBUG: log unmatched provinces
  const unmatched = geojsonData.features
    .map(f => f.properties[nameProp] || '')
    .filter(rawName => !PENSIONS[NAME_MAP[rawName] || rawName]);
  if (unmatched.length) {
    console.warn('⚠️ Sin datos (' + unmatched.length + ' provincias):\n' + unmatched.join('\n'));
    document.getElementById('debug-banner')?.remove();
    const dbg = document.createElement('div');
    dbg.id = 'debug-banner';
    dbg.style.cssText = 'position:fixed;bottom:16px;right:16px;background:#1a1714;color:#fbbf24;padding:14px 18px;border-radius:10px;font-size:12px;font-family:monospace;max-width:360px;z-index:9999;line-height:1.7;box-shadow:0 4px 20px rgba(0,0,0,0.3)';
    dbg.innerHTML = '<strong style="display:block;margin-bottom:4px">⚠️ ' + unmatched.length + ' provincias sin mapeo</strong>'
      + unmatched.map(n => `• <span style="color:#fff">"${n}"</span>`).join('<br>')
      + '<br><small style="color:#888">Comparte estos nombres para corregirlos</small>'
      + '<br><button onclick="this.parentElement.remove()" style="margin-top:8px;padding:3px 10px;background:#333;color:#fff;border:none;border-radius:4px;cursor:pointer;font-size:11px">Cerrar ✕</button>';
    document.body.appendChild(dbg);
  } else {
    console.log('✅ Todas las provincias mapeadas correctamente');
  }

  geojsonLayer = L.geoJSON(geojsonData, {
    style: feature => {
      const rawName = feature.properties[nameProp] || '';
      const key = NAME_MAP[rawName] || rawName;
      const d = PENSIONS[key];
      const val = d ? d[currentType] : null;
      return {
        fillColor: val ? getColor(val, min, max) : '#ddd8d0',
        fillOpacity: val ? 0.88 : 0.4,
        color: '#fff',
        weight: 1.2,
        opacity: 1
      };
    },
    onEachFeature: (feature, layer) => {
      const rawName = feature.properties[nameProp] || '';
      const key = NAME_MAP[rawName] || rawName;
      const d = PENSIONS[key];

      layer.on('mouseover', function(e) {
        this.setStyle({ weight: 2.5, color: '#333', fillOpacity: 1 });
        const val = d ? d[currentType] : null;
        const numStr = d ? fmtNum(d.total_num) : '—';
        L.tooltip({
          permanent: false, sticky: true, className: 'leaflet-tooltip-custom',
          offset: [12, 0]
        })
        .setContent(`
          <div class="tip-name">${key}</div>
          <div class="tip-val">${val ? val.toFixed(2).replace('.', ',') + ' €' : '—'}</div>
          <div class="tip-sub">${TYPE_META[currentType].label} · ${numStr} pensionistas</div>
        `)
        .setLatLng(e.latlng)
        .addTo(map);
      });

      layer.on('mousemove', e => {
        map.eachLayer(l => { if (l.getTooltip) { const t = l.getTooltip(); if(t) t.setLatLng(e.latlng); }});
      });

      layer.on('mouseout', function() {
        this.setStyle({
          weight: 1.2, color: '#fff', fillOpacity: 0.88
        });
        map.eachLayer(l => { if (l.getTooltip && l.getTooltip()) map.removeLayer(l); });
      });

      layer.on('click', () => {
        if (d) selectProvince(key);
      });
    }
  }).addTo(map);
}

function updateMap() {
  if (!geojsonLayer) return;
  const vals = Object.values(PENSIONS)
    .map(d => d[currentType]).filter(Boolean);
  const min = Math.min(...vals), max = Math.max(...vals);

  document.getElementById('leg-min').textContent = min.toFixed(0) + ' €';
  document.getElementById('leg-max').textContent = max.toFixed(0) + ' €';

  const namePropU = (() => {
    const sample = geojsonLayer.getLayers()[0]?.feature?.properties || {};
    return ['name','NAME','nombre','NOMBRE','provincia','PROVINCIA','nom','NOM'].find(k => sample[k]) || 'name';
  })();
  geojsonLayer.eachLayer(layer => {
    const rawName = layer.feature.properties[namePropU] || '';
    const key = NAME_MAP[rawName] || rawName;
    const d = PENSIONS[key];
    const val = d ? d[currentType] : null;
    layer.setStyle({
      fillColor: val ? getColor(val, min, max) : '#ddd8d0',
      fillOpacity: val ? 0.88 : 0.4,
    });
  });

  document.getElementById('map-title').textContent =
    `Pensión media por provincia · ${TYPE_META[currentType].label}`;
}

function setType(type) {
  currentType = type;
  document.querySelectorAll('.pill-btn').forEach(b => b.classList.remove('active'));
  event.target.classList.add('active');
  updateMap();
  buildRanking();
  if (selectedProvince) updateBarChart(selectedProvince);
}

// ─── PROVINCE DETAIL ─────────────────────────────────────────────────────────
function selectProvince(name) {
  selectedProvince = name;
  const d = PENSIONS[name];
  if (!d) return;

  document.getElementById('selected-label').textContent = name;
  document.getElementById('chart-title').textContent = `Pensión media por tipo — ${name}`;
  document.getElementById('chart-subtitle').textContent = `${fmtNum(d.total_num)} pensionistas · Datos a 1 de febrero de 2026`;

  // Ranking position
  const sorted = Object.entries(PENSIONS)
    .filter(([,v]) => v[currentType] != null)
    .sort((a,b) => b[1][currentType] - a[1][currentType]);
  const rank = sorted.findIndex(([k]) => k === name) + 1;
  const total = sorted.length;

  const html = `
    <div class="province-name-display">${name}</div>
    <div class="province-sub-display">${fmtNum(d.total_num)} pensionistas</div>
    <div class="province-main-stat">
      <div>
        <div class="big-num">${d.total_media.toFixed(0)} €</div>
        <div class="big-label">Pensión media total</div>
      </div>
      <div class="rank-badge">
        <div class="rank-num">#${rank}</div>
        <div class="rank-label">de ${total} provincias</div>
      </div>
    </div>
    <div class="type-rows">
      ${buildTypeRows(d)}
    </div>
  `;
  document.getElementById('province-detail').innerHTML = html;

  updateBarChart(name);
  buildRanking();
}

function buildTypeRows(d) {
  const types = [
    { mediaKey: 'jub_media', numKey: 'jub_num', label: 'Jubilación',     color: '#2d7a5a' },
    { mediaKey: 'ip_media',  numKey: 'ip_num',  label: 'Incap. Perm.',   color: '#3b82f6' },
    { mediaKey: 'viu_media', numKey: 'viu_num', label: 'Viudedad',       color: '#7c3aed' },
    { mediaKey: 'orf_media', numKey: 'orf_num', label: 'Orfandad',       color: '#e8a020' },
    { mediaKey: 'fam_media', numKey: 'fam_num', label: 'Fav. Familiar',  color: '#ec4899' },
  ];
  const maxNum = Math.max(...types.map(t => d[t.numKey] || 0));
  return types.map(t => {
    const media = d[t.mediaKey];
    const num   = d[t.numKey];
    const pct   = num ? (num / maxNum * 100).toFixed(0) : 0;
    return `
      <div class="type-row" style="align-items:flex-start;flex-direction:column;gap:4px;padding:8px 0;border-bottom:1px solid var(--border)">
        <div style="display:flex;align-items:center;gap:8px;width:100%">
          <div class="type-dot" style="background:${t.color};flex-shrink:0"></div>
          <div class="type-name" style="flex:1;font-weight:500">${t.label}</div>
          <div style="font-size:13px;font-weight:700;color:${t.color}">${media ? media.toFixed(2).replace('.',',') + ' €' : '—'}</div>
        </div>
        <div style="display:flex;align-items:center;gap:8px;width:100%;padding-left:16px">
          <div class="type-bar-wrap" style="flex:1">
            <div class="type-bar-fill" style="width:${pct}%;background:${t.color}"></div>
          </div>
          <div style="font-size:11px;color:var(--text-muted);min-width:72px;text-align:right">${num ? fmtNum(num) + ' pens.' : '—'}</div>
        </div>
      </div>`;
  }).join('');
}

// ─── BAR CHART ───────────────────────────────────────────────────────────────
function initBarChart() {
  const ctx = document.getElementById('barChart').getContext('2d');
  barChart = new Chart(ctx, {
    type: 'bar',
    data: {
      labels: ['Jubilación', 'Incap. Perm.', 'Viudedad', 'Orfandad', 'Fav. Familiar'],
      datasets: [{
        data: [0, 0, 0, 0, 0],
        backgroundColor: ['#2d7a5a','#3b82f6','#7c3aed','#e8a020','#ec4899'],
        borderRadius: 6,
        borderSkipped: false,
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: true,
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: {
            label: ctx => ' ' + ctx.raw.toFixed(2).replace('.',',') + ' €/mes'
          }
        }
      },
      scales: {
        y: {
          beginAtZero: false,
          grid: { color: '#f0ece6' },
          ticks: {
            font: { family: "'DM Sans', sans-serif", size: 11 },
            color: '#a09a94',
            callback: v => v.toLocaleString('es-ES') + ' €'
          }
        },
        x: {
          grid: { display: false },
          ticks: { font: { family: "'DM Sans', sans-serif", size: 12 }, color: '#6b6560' }
        }
      }
    }
  });
}

function updateBarChart(name) {
  const d = PENSIONS[name];
  if (!d) return;
  barChart.data.datasets[0].data = [
    d.jub_media, d.ip_media, d.viu_media, d.orf_media, d.fam_media
  ];
  barChart.update();
}

// ─── RANKING ─────────────────────────────────────────────────────────────────
function buildRanking() {
  const sorted = Object.entries(PENSIONS)
    .filter(([,v]) => v[currentType] != null)
    .sort((a,b) => b[1][currentType] - a[1][currentType]);

  const maxVal = sorted[0][1][currentType];
  const label = TYPE_META[currentType].label;
  document.getElementById('rank-label').textContent = `${label} · mayor a menor`;

  const list = document.getElementById('ranking-list');
  list.innerHTML = sorted.map(([name, d], i) => {
    const val = d[currentType];
    const pct = (val / maxVal * 100).toFixed(0);
    const isSelected = name === selectedProvince;
    return `
      <div class="rank-item ${isSelected ? 'highlighted' : ''}" onclick="selectProvince('${name.replace(/'/,"\\'")}')">
        <div class="rank-num-badge">${i+1}</div>
        <div class="rank-name">${name}</div>
        <div class="rank-bar-wrap">
          <div class="rank-bar-fill" style="width:${pct}%"></div>
        </div>
        <div class="rank-value" style="color:${isSelected?'var(--accent)':'var(--text-primary)'}">${val.toFixed(0)} €</div>
      </div>`;
  }).join('');
}
</script>
</body>
</html>
