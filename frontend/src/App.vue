<template>
  <main class="app">
    <header id="header">
      <h1>文物数字档案平台</h1>
      <div class="hdr-right">
        <span class="badge">显示 <b>{{ filteredRelics.length }}</b> / {{ relics.length }}</span>
        <button class="icon-btn">?</button>
        <button class="icon-btn" :class="{ on: settingsOpen }" @click="settingsOpen = !settingsOpen">设置</button>
        <button class="icon-btn">退</button>
      </div>
    </header>
    <section id="toolbar">
      <button class="tb" :class="{ on: filterOpen }" @click="filterOpen = !filterOpen">筛选</button>
      <button class="tb" @click="resetViewAllPoints">重置视角</button>
      <div class="tb-sep"></div>
      <select class="tb-select">
        <option>离线影像</option>
        <option>离线路网</option>
      </select>
      <div class="tb-range-wrap">透明<input type="range" class="tb-range" min="0" max="100" value="90" />90%</div>
      <div class="tb-sep"></div>
      <button class="tb" @click="resetAllFilters">重置</button>
      <button class="tb" @click="copyShareLink">{{ shareText }}</button>
      <div class="tb-sep"></div>
      <div class="tb-info">显示 <b>{{ filteredRelics.length }}</b> 处</div>
      <div class="status-summary">当前位置：{{ activeRelic?.name || "全部文物" }}</div>
    </section>
    <div id="map"></div>
    <aside id="filterPanel" :class="{ open: filterOpen, mobile: mobileTab==='filter' }">
      <div class="fp-title">筛选条件 <button @click="filterOpen = false">&times;</button></div>
      <div class="fp-section"><div class="fp-label">关键词</div><input v-model.trim="keyword" class="fp-search" placeholder="名称 / 编号 / 地址" /></div>
      <div class="fp-section"><div class="fp-label">乡镇</div><select v-model="selectedTown" class="fp-select"><option value="">全部乡镇</option><option v-for="t in towns" :key="t" :value="t">{{ t }}</option></select></div>
      <div class="fp-section"><div class="fp-label">保护级别</div><select v-model="selectedLevel" class="fp-select"><option value="">全部级别</option><option v-for="l in levels" :key="l" :value="l">{{ l }}</option></select></div>
      <div class="fp-section"><div class="fp-label">保存现状</div><select v-model="selectedCond" class="fp-select"><option value="">全部现状</option><option v-for="c in conditions" :key="c" :value="c">{{ c }}</option></select></div>
      <div class="fp-section">
        <div class="fp-label">文物类别</div>
        <div class="fp-checks">
          <button v-for="c in categories" :key="c" class="fp-chk" :class="{ active: selectedCats.has(c) }" @click="toggleCat(c)"><span class="dot" :style="{ background: colorOf(c) }"></span>{{ c }}</button>
        </div>
      </div>
      <div class="fp-section bnd">
        <label><input type="checkbox" v-model="showCounty" /> 县界</label><label><input type="checkbox" v-model="showTownship" /> 镇街界</label><label><input type="checkbox" v-model="showVillage" /> 村界</label><label><input type="checkbox" v-model="showTownLabel" /> 镇街名</label><label><input type="checkbox" v-model="showVillageLabel" /> 村名</label>
      </div>
      <div class="fp-section route">
        <div class="rt-h"><strong>路线</strong><button class="small" @click="loadRoutes">刷新</button></div>
        <div class="rt-acts"><button class="small" @click="selectAllRoutes">全选</button><button class="small" @click="clearRoutes">清空</button><button class="small" :class="{ on: coverageOn }" @click="toggleCoverage">村村达</button></div>
        <div class="rt-list"><label v-for="d in routeDates" :key="d" class="rt-row"><input type="checkbox" :checked="visibleRouteDates.has(d)" @change="toggleRouteDate(d, $event.target.checked)" /><span>{{ d }}</span><button class="mini" @click.prevent="openWorklog(d)">日志</button></label></div>
      </div>
      <div class="fp-stat">共 <b>{{ filteredRelics.length }}</b> 处</div>
      <div class="list"><button v-for="r in filteredRelics" :key="r.archive_code" class="item" @click="focusRelic(r)"><div class="n">{{ r.name }}</div><div class="m">{{ r.archive_code }} · {{ r.township || "-" }}</div></button></div>
    </aside>
    <aside id="infoPanel" :class="{ open: !!activeRelic, mobile: mobileTab==='info' }" v-if="activeRelic">
      <div class="pi-hdr"><h2>{{ activeRelic.name }}</h2><button class="pi-close" @click="activeRelic = null">&times;</button></div>
      <div class="tc">
        <p>编号: {{ activeRelic.archive_code }}</p><p>年代: {{ activeRelic.era || "-" }}</p><p>类别: {{ activeRelic.category_main || "-" }}</p><p>级别: {{ activeRelic.heritage_level || "-" }}</p><p>乡镇: {{ activeRelic.township || "-" }}</p><p>地址: {{ activeRelic.address || "-" }}</p>
        <p class="intro-text">{{ detail.intro || "暂无简介" }}</p>
        <div class="actions"><button v-if="detail.pdf_path" class="small" @click="openPdf(detail.pdf_path, activeRelic.name)">档案</button></div>
        <div class="media"><h4>照片</h4><div class="grid"><a v-for="p in photos" :key="p.relative_path" :href="`/photos/${p.relative_path}`" target="_blank"><img :src="`/photos/${p.relative_path}`" alt="" /></a></div><h4>图纸</h4><div class="grid"><a v-for="d in drawings" :key="d.relative_path" :href="`/drawings/${d.relative_path}`" target="_blank"><img :src="`/drawings/${d.relative_path}`" alt="" /></a></div></div>
      </div>
    </aside>
    <section class="settings" v-if="settingsOpen">
      <div class="st-row">
        <span>主题</span>
        <div class="st-btns">
          <button class="small" :class="{ on: theme==='dark' }" @click="setTheme('dark')">暗</button>
          <button class="small" :class="{ on: theme==='blue' }" @click="setTheme('blue')">蓝</button>
          <button class="small" :class="{ on: theme==='gold' }" @click="setTheme('gold')">金</button>
        </div>
      </div>
      <div class="st-row">
        <span>尺寸</span>
        <div class="st-btns">
          <button class="small" :class="{ on: uiSize==='sm' }" @click="setSize('sm')">小</button>
          <button class="small" :class="{ on: uiSize==='md' }" @click="setSize('md')">中</button>
          <button class="small" :class="{ on: uiSize==='lg' }" @click="setSize('lg')">大</button>
        </div>
      </div>
      <div class="st-row">
        <label><input type="checkbox" v-model="hdMode" @change="applyHdMode" /> 高清渲染</label>
      </div>
    </section>
    <aside id="legend">
      <strong>类别图例</strong>
      <div class="lg" v-for="c in categories" :key="`lg-${c}`">
        <span class="dot" :style="{ background: colorOf(c) }"></span>
        <span>{{ c }}</span>
      </div>
    </aside>
    <div class="chat-fab">
      <button class="small" @click="chatOpen = !chatOpen">{{ chatOpen ? "收起AI" : "AI" }}</button>
    </div>
    <section class="chat" v-if="chatOpen">
      <div class="chat-h">
        <strong>AI 助手</strong>
        <select v-model="chatModel">
          <option v-for="m in chatModels" :key="m.id" :value="m.id">{{ m.name }}</option>
        </select>
      </div>
      <div class="chat-m">
        <div v-for="(m, i) in chatMessages" :key="i" :class="['msg', m.role]">
          <div class="bubble" v-html="renderChat(m.content)"></div>
        </div>
      </div>
      <div class="chat-i">
        <input v-model.trim="chatInput" placeholder="输入问题..." @keydown.enter.prevent="sendChat" />
        <button class="small" @click="sendChat" :disabled="chatLoading">{{ chatLoading ? "..." : "发送" }}</button>
      </div>
    </section>
    <aside class="coverage" v-if="coverageOn && coverage">
      <strong>村村达</strong>
      <p>{{ coverage.reached }} / {{ coverage.total }} 村</p>
      <p>{{ coveragePct }}%</p>
      <div class="cv-list">
        <button v-for="v in unreachedVillages" :key="`${v.name}-${v.center_lon}`" class="cv-item" @click="flyVillage(v)">
          {{ v.name }} · {{ v.township }}
        </button>
      </div>
    </aside>
    <div class="worklog" v-if="worklogDate">
      <div class="wk-h">
        <strong>工作日志 {{ worklogDate }}</strong>
        <button class="small" @click="closeWorklog">关闭</button>
      </div>
      <iframe v-if="worklogPdf" :src="`/pdf-viewer?url=${encodeURIComponent(`/worklog-pdfs/${worklogPdf}`)}&name=${encodeURIComponent(worklogDate)}`"></iframe>
      <p v-else>该日期无 PDF</p>
    </div>
    <p v-if="error" class="err">{{ error }}</p>
    <div id="mobileNav">
      <button class="mn-btn" :class="{ active: mobileTab==='map' }" @click="mobileTab='map'">地图</button>
      <button class="mn-btn" :class="{ active: mobileTab==='filter' }" @click="mobileTab='filter'; filterOpen=true">筛选</button>
      <button class="mn-btn" :class="{ active: mobileTab==='info' }" @click="mobileTab='info'" :disabled="!activeRelic">详情</button>
    </div>
  </main>
</template>

<script setup>
import { computed, onMounted, ref, watch } from "vue";

const relics = ref([]);
const keyword = ref("");
const activeRelic = ref(null);
const error = ref("");
const viewer = ref(null);
const entities = new Map();
const detail = ref({});
const photos = ref([]);
const drawings = ref([]);
const selectedTown = ref("");
const selectedCats = ref(new Set());
const selectedLevel = ref("");
const selectedCond = ref("");
const shareText = ref("复制筛选链接");
const showCounty = ref(true);
const showTownship = ref(true);
const showVillage = ref(false);
const showTownLabel = ref(true);
const showVillageLabel = ref(false);
const boundaryEntities = ref({
  county: [],
  township: [],
  village: [],
  townLabel: [],
  villageLabel: [],
});
const routeData = ref({});
const routeDates = ref([]);
const routeEntities = ref([]);
const visibleRouteDates = ref(new Set());
const worklogMap = ref({});
const worklogDate = ref("");
const worklogPdf = ref("");
const coverage = ref(null);
const coverageOn = ref(false);
const chatOpen = ref(false);
const chatInput = ref("");
const chatLoading = ref(false);
const chatMessages = ref([]);
const chatHistory = ref([]);
const chatModels = ref([]);
const chatModel = ref("");
const settingsOpen = ref(false);
const theme = ref("dark");
const uiSize = ref("md");
const hdMode = ref(false);
const filterOpen = ref(true);
const mobileTab = ref("map");

const towns = computed(() => {
  return [...new Set(relics.value.map((r) => r.township).filter(Boolean))].sort();
});

const categories = computed(() => {
  return [...new Set(relics.value.map((r) => r.category_main).filter(Boolean))].sort();
});
const levels = computed(() => {
  return [...new Set(relics.value.map((r) => r.heritage_level).filter(Boolean))].sort();
});
const conditions = computed(() => {
  return [...new Set(relics.value.map((r) => r.condition_level).filter(Boolean))].sort();
});
const coveragePct = computed(() => {
  const c = coverage.value;
  if (!c || !c.total) return "0.0";
  return ((c.reached / c.total) * 100).toFixed(1);
});
const unreachedVillages = computed(() => {
  const c = coverage.value;
  if (!c || !Array.isArray(c.villages)) return [];
  return c.villages.filter((v) => !v.reached);
});

const filteredRelics = computed(() => {
  const kw = keyword.value.toLowerCase();
  if (!kw) return relics.value;
  return relics.value.filter((r) =>
    ((r.name || "").toLowerCase().includes(kw) ||
      (r.archive_code || "").toLowerCase().includes(kw) ||
      (r.address || "").toLowerCase().includes(kw)) &&
    (!selectedTown.value || r.township === selectedTown.value) &&
    (!selectedLevel.value || r.heritage_level === selectedLevel.value) &&
    (!selectedCond.value || r.condition_level === selectedCond.value) &&
    (!selectedCats.value.size || selectedCats.value.has(r.category_main))
  );
});

function safeNum(v, d = 0) {
  const n = Number(v);
  return Number.isFinite(n) ? n : d;
}

function initMap() {
  const Cesium = window.Cesium;
  if (!Cesium) {
    error.value = "Cesium 未加载";
    return;
  }
  viewer.value = new Cesium.Viewer("map", {
    sceneMode: Cesium.SceneMode.SCENE2D,
    timeline: false,
    animation: false,
    baseLayerPicker: false,
    geocoder: false,
    homeButton: false,
    sceneModePicker: false,
    navigationHelpButton: false,
    fullscreenButton: false,
  });
  viewer.value.imageryLayers.removeAll();
  const osm = new Cesium.UrlTemplateImageryProvider({
    url: "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
    subdomains: ["a", "b", "c"],
    credit: "© OpenStreetMap contributors",
    maximumLevel: 19,
  });
  const osmLayer = viewer.value.imageryLayers.addImageryProvider(osm);
  let fallbackUsed = false;
  osmLayer.imageryProvider.errorEvent.addEventListener(() => {
    if (fallbackUsed) return;
    fallbackUsed = true;
    viewer.value.imageryLayers.removeAll();
    viewer.value.imageryLayers.addImageryProvider(
      new Cesium.UrlTemplateImageryProvider({
        url: "https://services.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
        credit: "Tiles © Esri",
        maximumLevel: 19,
      })
    );
  });
  viewer.value.scene.globe.baseColor = Cesium.Color.fromCssColorString("#0d1117");
  viewer.value.scene.screenSpaceCameraController.enableTilt = false;
  viewer.value.scene.screenSpaceCameraController.enableLook = false;
  viewer.value.scene.screenSpaceCameraController.enableRotate = false;
  const handler = new Cesium.ScreenSpaceEventHandler(viewer.value.scene.canvas);
  handler.setInputAction((click) => {
    const picked = viewer.value.scene.pick(click.position);
    const code = picked?.id?.properties?.archive_code?.getValue?.();
    if (!code) return;
    const r = relics.value.find((x) => x.archive_code === code);
    if (r) activeRelic.value = r;
  }, Cesium.ScreenSpaceEventType.LEFT_CLICK);
}

function drawPoints(list) {
  if (!viewer.value || !window.Cesium) return;
  viewer.value.entities.removeAll();
  entities.clear();
  const Cesium = window.Cesium;
  for (const r of list) {
    if (!r.center_lng || !r.center_lat) continue;
    const e = viewer.value.entities.add({
      position: Cesium.Cartesian3.fromDegrees(safeNum(r.center_lng), safeNum(r.center_lat), 0),
      point: {
        pixelSize: 8,
        color: Cesium.Color.fromCssColorString(colorOf(r.category_main)),
        outlineColor: Cesium.Color.WHITE,
        outlineWidth: 1,
      },
      properties: { archive_code: r.archive_code },
    });
    entities.set(r.archive_code, e);
  }
}

function resetViewAllPoints() {
  if (!viewer.value || !window.Cesium) return;
  const pts = relics.value.filter((r) => Number.isFinite(Number(r.center_lng)) && Number.isFinite(Number(r.center_lat)));
  if (!pts.length) return;
  let minLng = Infinity;
  let maxLng = -Infinity;
  let minLat = Infinity;
  let maxLat = -Infinity;
  for (const p of pts) {
    const lng = Number(p.center_lng);
    const lat = Number(p.center_lat);
    if (lng < minLng) minLng = lng;
    if (lng > maxLng) maxLng = lng;
    if (lat < minLat) minLat = lat;
    if (lat > maxLat) maxLat = lat;
  }
  const padLng = Math.max((maxLng - minLng) * 0.12, 0.01);
  const padLat = Math.max((maxLat - minLat) * 0.12, 0.01);
  const Cesium = window.Cesium;
  const rect = Cesium.Rectangle.fromDegrees(minLng - padLng, minLat - padLat, maxLng + padLng, maxLat + padLat);
  viewer.value.camera.flyTo({ destination: rect, duration: 0.8 });
}

function ringCenter(ring) {
  const lngs = ring.map((c) => c[0]);
  const lats = ring.map((c) => c[1]);
  return [(Math.min(...lngs) + Math.max(...lngs)) / 2, (Math.min(...lats) + Math.max(...lats)) / 2];
}

function addBoundaryPolygon(ring, color, alpha = 0.08) {
  const Cesium = window.Cesium;
  const positions = ring.map((pt) => Cesium.Cartesian3.fromDegrees(pt[0], pt[1]));
  const fill = viewer.value.entities.add({
    polygon: {
      hierarchy: new Cesium.PolygonHierarchy(positions),
      material: Cesium.Color.fromCssColorString(color).withAlpha(alpha),
    },
  });
  const line = viewer.value.entities.add({
    polyline: {
      positions: [...positions, positions[0]],
      width: 2,
      material: Cesium.Color.fromCssColorString(color).withAlpha(0.65),
      clampToGround: true,
    },
  });
  return [fill, line];
}

function addBoundaryLabel(lng, lat, text, color) {
  const Cesium = window.Cesium;
  return viewer.value.entities.add({
    position: Cesium.Cartesian3.fromDegrees(lng, lat),
    label: {
      text,
      font: '14px "Microsoft YaHei", sans-serif',
      fillColor: Cesium.Color.fromCssColorString(color),
      outlineColor: Cesium.Color.BLACK,
      outlineWidth: 3,
      style: Cesium.LabelStyle.FILL_AND_OUTLINE,
      disableDepthTestDistance: Number.POSITIVE_INFINITY,
      heightReference: Cesium.HeightReference.CLAMP_TO_GROUND,
      distanceDisplayCondition: new Cesium.DistanceDisplayCondition(0, 90000),
      scale: 0.7,
    },
  });
}

async function loadBoundaries() {
  if (!viewer.value) return;
  const sets = boundaryEntities.value;
  Object.values(sets).flat().forEach((e) => viewer.value.entities.remove(e));
  sets.county = [];
  sets.township = [];
  sets.village = [];
  sets.townLabel = [];
  sets.villageLabel = [];
  try {
    const [countyRes, townRes, villageRes] = await Promise.all([
      fetch("/boundaries/county.geojson"),
      fetch("/boundaries/townships.geojson"),
      fetch("/boundaries/villages.geojson"),
    ]);
    if (countyRes.ok) {
      const gj = await countyRes.json();
      for (const f of gj.features || []) {
        for (const ring of f.geometry?.coordinates || []) {
          sets.county.push(...addBoundaryPolygon(ring, "#ffc832", 0.02));
        }
      }
    }
    if (townRes.ok) {
      const gj = await townRes.json();
      for (const f of gj.features || []) {
        const name = f.properties?.XZQMC || f.properties?._township_name || "";
        for (const ring of f.geometry?.coordinates || []) {
          sets.township.push(...addBoundaryPolygon(ring, "#58a6ff", 0.05));
          if (name) {
            const [cx, cy] = ringCenter(ring);
            sets.townLabel.push(addBoundaryLabel(cx, cy, name, "rgba(255,200,50,0.95)"));
          }
        }
      }
    }
    if (villageRes.ok) {
      const gj = await villageRes.json();
      for (const f of gj.features || []) {
        const name = f.properties?.ZLDWMC || "";
        for (const ring of f.geometry?.coordinates || []) {
          sets.village.push(...addBoundaryPolygon(ring, "#3fb950", 0.03));
          if (name) {
            const [cx, cy] = ringCenter(ring);
            sets.villageLabel.push(addBoundaryLabel(cx, cy, name, "rgba(230,237,243,0.9)"));
          }
        }
      }
    }
    applyBoundaryVisibility();
  } catch {
  }
}

function applyBoundaryVisibility() {
  const sets = boundaryEntities.value;
  sets.county.forEach((e) => (e.show = showCounty.value));
  sets.township.forEach((e) => (e.show = showTownship.value));
  sets.village.forEach((e) => (e.show = showVillage.value));
  sets.townLabel.forEach((e) => (e.show = showTownLabel.value));
  sets.villageLabel.forEach((e) => (e.show = showVillageLabel.value));
  if (viewer.value) viewer.value.scene.requestRender();
}

function routeColor(date) {
  let hash = 0;
  for (let i = 0; i < date.length; i += 1) hash = (hash * 31 + date.charCodeAt(i)) >>> 0;
  const hue = hash % 360;
  return `hsl(${hue} 78% 60%)`;
}

function removeRouteEntities(date) {
  const keep = [];
  for (const it of routeEntities.value) {
    if (it.date === date) viewer.value.entities.remove(it.entity);
    else keep.push(it);
  }
  routeEntities.value = keep;
}

function renderRoute(date) {
  if (!viewer.value || !window.Cesium) return;
  const pts = routeData.value[date] || [];
  if (!pts.length) return;
  const Cesium = window.Cesium;
  const color = Cesium.Color.fromCssColorString(routeColor(date));
  if (pts.length >= 2) {
    const line = viewer.value.entities.add({
      polyline: {
        positions: pts.map((p) => Cesium.Cartesian3.fromDegrees(p.lon, p.lat)),
        width: 3,
        material: color.withAlpha(0.8),
        clampToGround: true,
      },
    });
    routeEntities.value.push({ date, entity: line });
  }
  for (const p of pts) {
    const dot = viewer.value.entities.add({
      position: Cesium.Cartesian3.fromDegrees(p.lon, p.lat),
      point: {
        pixelSize: 7,
        color,
        outlineColor: Cesium.Color.WHITE,
        outlineWidth: 1,
      },
    });
    routeEntities.value.push({ date, entity: dot });
  }
}

function toggleRouteDate(date, checked) {
  const next = new Set(visibleRouteDates.value);
  if (checked) {
    next.add(date);
    renderRoute(date);
  } else {
    next.delete(date);
    removeRouteEntities(date);
  }
  visibleRouteDates.value = next;
}

function clearRoutes() {
  for (const it of routeEntities.value) viewer.value.entities.remove(it.entity);
  routeEntities.value = [];
  visibleRouteDates.value = new Set();
}

function selectAllRoutes() {
  clearRoutes();
  const next = new Set();
  for (const d of routeDates.value) {
    next.add(d);
    renderRoute(d);
  }
  visibleRouteDates.value = next;
}

async function loadRoutes() {
  try {
    const [r1, r2] = await Promise.all([
      fetch("/api/survey-routes"),
      fetch("/api/worklog/dates"),
    ]);
    if (r1.ok) {
      routeData.value = await r1.json();
      routeDates.value = Object.keys(routeData.value).sort();
    }
    if (r2.ok) {
      const w = await r2.json();
      const m = {};
      for (const it of w.items || []) m[it.date] = it;
      worklogMap.value = m;
    }
  } catch {
  }
}

function openWorklog(date) {
  worklogDate.value = date;
  worklogPdf.value = worklogMap.value?.[date]?.pdf_file || "";
}

function closeWorklog() {
  worklogDate.value = "";
  worklogPdf.value = "";
}

async function toggleCoverage() {
  coverageOn.value = !coverageOn.value;
  if (!coverageOn.value) return;
  if (!coverage.value) {
    try {
      const resp = await fetch("/api/village-coverage");
      if (resp.ok) coverage.value = await resp.json();
    } catch {
    }
  }
}

function flyVillage(v) {
  if (!viewer.value || !window.Cesium) return;
  const Cesium = window.Cesium;
  viewer.value.camera.flyTo({
    destination: Cesium.Cartesian3.fromDegrees(safeNum(v.center_lon), safeNum(v.center_lat), 5000),
    duration: 1.0,
  });
}

function escHtml(t) {
  return String(t || "").replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

function renderChat(text) {
  let h = escHtml(text);
  h = h.replace(/\[\[([^\]|]+)\|([^\]]+)\]\]/g, (_m, label, action) => {
    const encoded = encodeURIComponent(action);
    return `<a href="#" data-act="${encoded}" class="chat-link">${label}</a>`;
  });
  h = h.replace(/\n/g, "<br>");
  return h;
}

async function loadChatModels() {
  try {
    const r = await fetch("/api/chat/models");
    if (!r.ok) return;
    const data = await r.json();
    chatModels.value = data.models || [];
    chatModel.value = data.default || (chatModels.value[0]?.id || "");
  } catch {
  }
}

function applyChatFilter(filterStr) {
  const params = {};
  for (const p of String(filterStr).split("&")) {
    const idx = p.indexOf(":");
    if (idx > 0) params[p.slice(0, idx).trim()] = p.slice(idx + 1).trim();
  }
  keyword.value = params.kw || "";
  selectedTown.value = params.t || "";
  selectedLevel.value = params.l || "";
  selectedCond.value = params.s || "";
  if (params.c) selectedCats.value = new Set([params.c]);
}

function onChatAction(action) {
  if (action.startsWith("fly:")) {
    const code = action.slice(4);
    const r = relics.value.find((x) => x.archive_code === code);
    if (r) focusRelic(r);
    return;
  }
  if (action.startsWith("log:")) {
    openWorklog(action.slice(4));
    return;
  }
  applyChatFilter(action);
}

async function sendChat() {
  const msg = chatInput.value;
  if (!msg || chatLoading.value) return;
  chatInput.value = "";
  chatMessages.value.push({ role: "user", content: msg });
  const aiMsg = { role: "assistant", content: "..." };
  chatMessages.value.push(aiMsg);
  chatLoading.value = true;
  let full = "";
  try {
    const resp = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: msg, history: chatHistory.value.slice(-10), model: chatModel.value }),
    });
    const reader = resp.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n");
      buffer = lines.pop() || "";
      for (const line of lines) {
        if (!line.startsWith("data: ")) continue;
        const payload = line.slice(6);
        if (payload === "[DONE]") continue;
        try {
          const data = JSON.parse(payload);
          if (data.error) full += `\n${data.error}`;
          else if (data.content) full += data.content;
          aiMsg.content = full || "...";
        } catch {
        }
      }
    }
  } catch {
    aiMsg.content = "请求失败";
  }
  chatHistory.value.push({ role: "user", content: msg });
  chatHistory.value.push({ role: "assistant", content: aiMsg.content });
  chatLoading.value = false;
}

function colorOf(cat) {
  if (!cat) return "#58a6ff";
  let hash = 0;
  for (let i = 0; i < cat.length; i += 1) hash = (hash * 31 + cat.charCodeAt(i)) >>> 0;
  const hue = hash % 360;
  return `hsl(${hue} 70% 55%)`;
}

function toggleCat(c) {
  const next = new Set(selectedCats.value);
  if (next.has(c)) next.delete(c);
  else next.add(c);
  selectedCats.value = next;
}

function syncQueryToState() {
  const q = new URLSearchParams(window.location.search);
  keyword.value = q.get("q") || "";
  selectedTown.value = q.get("town") || "";
  selectedLevel.value = q.get("level") || "";
  selectedCond.value = q.get("cond") || "";
  const cats = (q.get("cats") || "").split(",").map((x) => x.trim()).filter(Boolean);
  selectedCats.value = new Set(cats);
}

function syncStateToQuery() {
  const q = new URLSearchParams();
  if (keyword.value) q.set("q", keyword.value);
  if (selectedTown.value) q.set("town", selectedTown.value);
  if (selectedLevel.value) q.set("level", selectedLevel.value);
  if (selectedCond.value) q.set("cond", selectedCond.value);
  if (selectedCats.value.size) q.set("cats", [...selectedCats.value].join(","));
  const next = `${window.location.pathname}${q.toString() ? `?${q.toString()}` : ""}`;
  window.history.replaceState(null, "", next);
}

async function copyShareLink() {
  try {
    await navigator.clipboard.writeText(window.location.href);
    shareText.value = "已复制";
  } catch {
    shareText.value = "复制失败";
  }
  setTimeout(() => {
    shareText.value = "复制筛选链接";
  }, 1200);
}

function focusRelic(r) {
  if (!viewer.value || !window.Cesium) return;
  activeRelic.value = r;
  const Cesium = window.Cesium;
  viewer.value.camera.flyTo({
    destination: Cesium.Cartesian3.fromDegrees(safeNum(r.center_lng), safeNum(r.center_lat), 1500),
    duration: 1.0,
  });
}

function openPdf(path, name) {
  const url = `/pdf-viewer?url=${encodeURIComponent(`/pdfs/${path}`)}&name=${encodeURIComponent(name || "档案")}`;
  window.open(url, "_blank");
}

function setTheme(t) {
  theme.value = t;
  const root = document.documentElement.style;
  if (t === "blue") {
    root.setProperty("--accent", "#58a6ff");
    root.setProperty("--panel", "#102030");
  } else if (t === "gold") {
    root.setProperty("--accent", "#ffd700");
    root.setProperty("--panel", "#2a2210");
  } else {
    root.setProperty("--accent", "#58a6ff");
    root.setProperty("--panel", "#11161d");
  }
}

function setSize(s) {
  uiSize.value = s;
  const root = document.documentElement.style;
  if (s === "sm") root.setProperty("--ui-scale", "0.92");
  else if (s === "lg") root.setProperty("--ui-scale", "1.08");
  else root.setProperty("--ui-scale", "1");
}

function applyHdMode() {
  if (!viewer.value) return;
  if (hdMode.value) {
    viewer.value.useBrowserRecommendedResolution = false;
    viewer.value.resolutionScale = Math.min(window.devicePixelRatio || 1, 2);
  } else {
    viewer.value.useBrowserRecommendedResolution = true;
    viewer.value.resolutionScale = 1;
  }
  viewer.value.scene.requestRender();
}

function resetAllFilters() {
  keyword.value = "";
  selectedTown.value = "";
  selectedLevel.value = "";
  selectedCond.value = "";
  selectedCats.value = new Set();
}

async function loadRelics() {
  try {
    const resp = await fetch("/api/relics");
    if (!resp.ok) throw new Error("load failed");
    relics.value = await resp.json();
    drawPoints(relics.value);
    resetViewAllPoints();
  } catch {
    error.value = "读取文物数据失败";
  }
}

watch(filteredRelics, (v) => drawPoints(v));
watch([keyword, selectedTown, selectedLevel, selectedCond, selectedCats], () => syncStateToQuery(), { deep: true });
watch([showCounty, showTownship, showVillage, showTownLabel, showVillageLabel], () => applyBoundaryVisibility());

watch(activeRelic, async (r) => {
  detail.value = {};
  photos.value = [];
  drawings.value = [];
  if (!r?.archive_code) return;
  try {
    const [d1, d2, d3] = await Promise.all([
      fetch(`/api/relics/${r.archive_code}`),
      fetch(`/api/relics/${r.archive_code}/photos`),
      fetch(`/api/relics/${r.archive_code}/drawings`),
    ]);
    if (d1.ok) detail.value = await d1.json();
    if (d2.ok) photos.value = await d2.json();
    if (d3.ok) drawings.value = await d3.json();
  } catch {
  }
});

onMounted(async () => {
  syncQueryToState();
  initMap();
  await loadRelics();
  await loadBoundaries();
  await loadRoutes();
  await loadChatModels();
  chatMessages.value.push({ role: "assistant", content: "你好，我可以回答文物与日志问题。" });
  document.addEventListener("click", (e) => {
    const a = e.target.closest?.(".chat-link");
    if (!a) return;
    e.preventDefault();
    onChatAction(decodeURIComponent(a.dataset.act || ""));
  });
});
</script>
