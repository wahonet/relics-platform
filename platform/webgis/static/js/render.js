// 地图渲染：点位符号、颜色映射、面图层。符号/图例图标通过 Canvas 动态生成并缓存。
function buildColorMap(relics, dim) {
    const counts = {};
    relics.forEach(r => { dimValues(r, dim).forEach(v => { counts[v] = (counts[v]||0)+1; }); });
    let keys = dim.order ? dim.order.filter(k => counts[k]) : Object.keys(counts).sort((a,b) => (counts[b]||0)-(counts[a]||0));
    const map = {};
    keys.forEach((k,i) => { map[k] = PALETTE[i % PALETTE.length]; });
    return map;
}

function getPointColor(r) {
    const dim = DIMS.find(d => d.id === activeGroup);
    if (!dim) return DEF_COLOR;
    const v = dimValue(r, dim);
    const cm = dimColorMaps[activeGroup];
    return (cm && cm[v]) || DEF_COLOR;
}

const CATEGORY_ICONS = {
    '古建筑': '/static/古建筑.png',
    '古墓葬': '/static/古墓葬.png',
    '古文化遗址': '/static/古文化遗址.png',
    '石窟寺及石刻': '/static/石窟寺及石刻.png',
    '近现代重要史迹及代表性建筑': '/static/近现代重要史迹及代表性建筑.png',
    '近现代史迹': '/static/近现代重要史迹及代表性建筑.png',
};
const _catImgs = {};
let _symbolCache = {};
let _symbolMode = true;
let _showTextLabels = true;
let _labelFontSize = 14;
let _labelFontFamily = '"Microsoft YaHei", sans-serif';

(function preloadCategoryIcons() {
    for (const [cat, url] of Object.entries(CATEGORY_ICONS)) {
        const img = new Image();
        img.crossOrigin = 'anonymous';
        img.src = url;
        img.onload = () => { _catImgs[cat] = img; };
    }
})();

function _hiDpiCanvas(size) {
    const S = size;
    const canvas = document.createElement('canvas');
    canvas.width = S; canvas.height = S;
    const ctx = canvas.getContext('2d');
    ctx.imageSmoothingEnabled = true;
    ctx.imageSmoothingQuality = 'high';
    return { canvas, ctx, S, logical: size };
}

function makeSymbolIcon(category, color, has3d) {
    const key = category + '|' + color + '|' + (has3d ? '1' : '0') + '|' + (_hdMode ? 'hd' : 'std');
    if (_symbolCache[key]) return _symbolCache[key];

    const L = _hdMode ? 128 : 64;
    const { canvas, ctx } = _hiDpiCanvas(L);
    const r = L / 2;
    const bw = 3;

    const bwScaled = bw * (L / 64);
    ctx.beginPath();
    ctx.arc(r, r, r - bwScaled, 0, Math.PI * 2);
    ctx.fillStyle = color;
    ctx.fill();
    ctx.lineWidth = bwScaled;
    ctx.strokeStyle = has3d ? '#ffd700' : '#222';
    ctx.stroke();

    const img = _catImgs[category];
    if (img) {
        const tmpC = document.createElement('canvas');
        tmpC.width = L; tmpC.height = L;
        const tc = tmpC.getContext('2d');
        tc.imageSmoothingEnabled = true;
        tc.imageSmoothingQuality = 'high';
        const iconS = L * 0.56;
        const off = (L - iconS) / 2;
        tc.drawImage(img, off, off, iconS, iconS);
        tc.globalCompositeOperation = 'source-in';
        tc.fillStyle = 'rgba(255,255,255,0.92)';
        tc.fillRect(0, 0, L, L);
        ctx.drawImage(tmpC, 0, 0);
    }

    const url = canvas.toDataURL();
    _symbolCache[key] = url;
    return url;
}

function makeLegendIcon(category, color) {
    const L = _hdMode ? 64 : 32;
    const { canvas, ctx } = _hiDpiCanvas(L);
    const r = L / 2;
    ctx.beginPath();
    ctx.arc(r, r, r - 1, 0, Math.PI * 2);
    ctx.fillStyle = color;
    ctx.fill();
    ctx.lineWidth = 1;
    ctx.strokeStyle = 'rgba(0,0,0,0.3)';
    ctx.stroke();
    const img = _catImgs[category];
    if (img) {
        const tmpC = document.createElement('canvas');
        tmpC.width = L; tmpC.height = L;
        const tc = tmpC.getContext('2d');
        tc.imageSmoothingEnabled = true;
        tc.imageSmoothingQuality = 'high';
        const iconS = L * 0.58;
        const off = (L - iconS) / 2;
        tc.drawImage(img, off, off, iconS, iconS);
        tc.globalCompositeOperation = 'source-in';
        tc.fillStyle = 'rgba(255,255,255,0.9)';
        tc.fillRect(0, 0, L, L);
        ctx.drawImage(tmpC, 0, 0);
    }
    return canvas.toDataURL();
}

let _relicPointsHidden = false;

function toggleHideRelicPoints() {
    _relicPointsHidden = document.getElementById('hideRelicToggle').checked;
    const show = !_relicPointsHidden;
    Object.values(entityMap).forEach(function (e) {
        e.show = show;
    });
    polygonEntities.forEach(function (e) {
        e.show = show;
    });
    viewer.scene.requestRender();
}

function toggleNonSymbolize() {
    _symbolMode = !document.getElementById('nonSymbolToggle').checked;
    _symbolCache = {};
    onFilterChange();
}

function toggleTextLabels() {
    _showTextLabels = document.getElementById('textLabelToggle').checked;
    Object.values(entityMap).forEach(function (e) {
        if (e.label) e.label.show = _showTextLabels;
    });
    viewer.scene.requestRender();
}

function setLabelSize(val) {
    _labelFontSize = parseInt(val);
    document.getElementById('labelSizeVal').textContent = val + 'px';
    var font = _labelFontSize + 'px ' + _labelFontFamily;
    Object.values(entityMap).forEach(function (e) {
        if (e.label) e.label.font = font;
    });
    viewer.scene.requestRender();
}

function setLabelFont(val) {
    _labelFontFamily = val;
    document.getElementById('labelFontSel').value = val;
    var font = _labelFontSize + 'px ' + _labelFontFamily;
    Object.values(entityMap).forEach(function (e) {
        if (e.label) e.label.font = font;
    });
    viewer.scene.requestRender();
}

function _makePointCanvas(color, outlineColor, outlineW, sz) {
    const key = 'pt|' + color + '|' + outlineColor + '|' + outlineW + '|' + sz + '|' + (_hdMode ? 'hd' : 'std');
    if (_symbolCache[key]) return _symbolCache[key];
    const L = _hdMode ? 64 : 32;
    const { canvas, ctx } = _hiDpiCanvas(L);
    const r = L / 2;
    const oScale = L / 32;
    ctx.beginPath();
    ctx.arc(r, r, r - outlineW * 2 * oScale, 0, Math.PI * 2);
    ctx.fillStyle = color;
    ctx.fill();
    if (outlineW > 0) {
        ctx.lineWidth = outlineW * 2 * oScale;
        ctx.strokeStyle = outlineColor;
        ctx.stroke();
    }
    const url = canvas.toDataURL();
    _symbolCache[key] = url;
    return url;
}

function renderPoints(relics) {
    Object.values(entityMap).forEach(e => viewer.entities.remove(e));
    entityMap = {};

    relics.forEach(r => {
        if (!r.center_lat || !r.center_lng) return;
        const cssC = getPointColor(r);
        const h3d = is3D(r);
        const pos = Cesium.Cartesian3.fromDegrees(r.center_lng, r.center_lat, r.center_alt || 0);

        let bbImage, bbW, bbH;
        if (_symbolMode && CATEGORY_ICONS[r.category_main]) {
            bbW = 12; bbH = 12;
            bbImage = makeSymbolIcon(r.category_main, cssC, h3d);
        } else {
            bbW = h3d ? 10 : 7;
            bbH = bbW;
            const olC = h3d ? '#ffd700' : 'rgba(0,0,0,0.6)';
            const olW = h3d ? 2 : 1;
            bbImage = _makePointCanvas(cssC, olC, olW, bbW);
        }

        const ent = viewer.entities.add({
            position: pos,
            show: !_relicPointsHidden,
            billboard: {
                image: bbImage,
                width: bbW, height: bbH,
                verticalOrigin: Cesium.VerticalOrigin.CENTER,
                disableDepthTestDistance: Number.POSITIVE_INFINITY,
                heightReference: Cesium.HeightReference.CLAMP_TO_GROUND,
            },
            label: {
                text: r.name,
                font: _labelFontSize + 'px ' + _labelFontFamily,
                show: _showTextLabels,
                fillColor: Cesium.Color.WHITE, outlineColor: Cesium.Color.BLACK, outlineWidth: _hdMode ? 4 : 3,
                style: Cesium.LabelStyle.FILL_AND_OUTLINE,
                verticalOrigin: Cesium.VerticalOrigin.BOTTOM,
                pixelOffset: new Cesium.Cartesian2(0, -(bbH / 2 + 5)),
                distanceDisplayCondition: new Cesium.DistanceDisplayCondition(0, 25000),
                disableDepthTestDistance: Number.POSITIVE_INFINITY,
                heightReference: Cesium.HeightReference.CLAMP_TO_GROUND,
                scale: _hdMode ? 1.0 : 0.85,
            },
            properties: r,
        });
        entityMap[r.archive_code] = ent;
    });
}

async function loadPolygons() {
    try {
        const geojson = await (await fetch(API + '/api/geojson/polygons')).json();
        geojson.features.forEach(f => {
            const coords = f.geometry.coordinates[0];
            const code = f.properties.archive_code;
            const relic = allRelics.find(r => r.archive_code === code);
            const cc = Cesium.Color.fromCssColorString(relic ? getPointColor(relic) : DEF_COLOR);
            const pos = []; coords.forEach(c => pos.push(c[0], c[1]));
            polygonEntities.push(viewer.entities.add({
                polygon: { hierarchy: Cesium.Cartesian3.fromDegreesArray(pos), material: cc.withAlpha(0.28), outline: true, outlineColor: cc.withAlpha(0.7), outlineWidth: 1, height: 0 },
            }));
        });
    } catch (e) { console.error('面图层:', e); }
}
