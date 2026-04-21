// 筛选逻辑、结果列表、视角定位。
function populateFilters() {
    const towns = new Set(), levels = new Set(), conds = new Set();
    const lvDim = DIMS.find(d => d.id === 'heritage_level');
    const twDim = DIMS.find(d => d.id === 'township');
    allRelics.forEach(r => {
        if (r.township) towns.add(twDim ? dimValue(r, twDim) : r.township);
        if (r.heritage_level) levels.add(lvDim ? dimValue(r, lvDim) : r.heritage_level);
        if (r.condition_level) conds.add(r.condition_level);
    });
    fillSel('filterTown', [...towns].sort());
    fillSel('filterLevel', [...levels].sort());
    fillSel('filterCond', [...conds].sort());

    const catBox = document.getElementById('catChecks');
    const catDim = DIMS.find(d => d.id === 'category_main');
    const catNames = [...new Set(allRelics.map(r=>r.category_main))].sort();
    catNames.forEach(name => {
        const displayName = catDim && catDim.transform ? catDim.transform(name) : name;
        const cm = dimColorMaps['category_main'] || {};
        const color = cm[displayName] || DEF_COLOR;
        const el = document.createElement('div');
        el.className = 'fp-chk active';
        el.dataset.cat = name;
        el.innerHTML = '<div class="dot" style="background:' + color + '"></div>' + displayName;
        el.onclick = () => { el.classList.toggle('active'); toggleCat(name, el.classList.contains('active')); };
        catBox.appendChild(el);
    });
}

function fillSel(id, opts) {
    const sel = document.getElementById(id);
    opts.forEach(o => { const op = document.createElement('option'); op.value = o; op.textContent = o; sel.appendChild(op); });
}

function toggleCat(name, on) {
    if (on) activeCats.add(name); else activeCats.delete(name);
    onFilterChange();
}

function onFilterChange() {
    const kw = document.getElementById('searchInput').value.trim().toLowerCase();
    const town = document.getElementById('filterTown').value;
    const level = document.getElementById('filterLevel').value;
    const cond = document.getElementById('filterCond').value;
    const f3d = document.getElementById('filter3D').value;

    filtered = allRelics.filter(r => {
        if (activeCats.size && !activeCats.has(r.category_main)) return false;
        if (kw && !r.name.toLowerCase().includes(kw) && !r.archive_code.toLowerCase().includes(kw) && !(r.address || '').toLowerCase().includes(kw)) return false;
        if (town) { const td = DIMS.find(d=>d.id==='township'); if (td && dimValue(r,td) !== town) return false; }
        if (level) { const ld = DIMS.find(d=>d.id==='heritage_level'); if (ld && dimValue(r,ld) !== level) return false; }
        if (cond && r.condition_level !== cond) return false;
        if (f3d === '1' && !is3D(r)) return false;
        if (f3d === '0' && is3D(r)) return false;
        for (const [sfDim, sfVal] of Object.entries(statFilters)) {
            if (sfDim === '_village') {
                if (!(r.address || '').includes(sfVal)) return false;
                continue;
            }
            const dim = DIMS.find(d => d.id === sfDim);
            if (dim) {
                const vals = dimValues(r, dim);
                if (!vals.includes(sfVal)) return false;
            }
        }
        return true;
    });

    document.getElementById('tbCount').textContent = filtered.length;
    const n3d = filtered.filter(r => is3D(r)).length;
    document.getElementById('filterStat').innerHTML = '当前 <b>' + filtered.length + '</b> 处文物，其中 <small>' + n3d + '</small> 处有三维模型';

    dimColorMaps[activeGroup] = buildColorMap(allRelics, DIMS.find(d=>d.id===activeGroup));
    if (_symbolMode) _symbolCache = {};
    renderPoints(filtered);
    renderResultList(filtered);
    renderAllCharts(filtered);
    updateLegend();

    updateStatusSummary();
    if (filtered.length > 0 && filtered.length < allRelics.length) fitToRelics(filtered);
}

function updateStatusSummary() {
    const el = document.getElementById('statusSummary');
    if (!el) return;
    const parts = [];
    const town = document.getElementById('filterTown').value;
    if (town) parts.push(town);
    for (const [dimId, val] of Object.entries(statFilters)) {
        parts.push(val);
    }
    if (parts.length === 0 && filtered.length === allRelics.length) {
        el.textContent = '当前位置：全部文物 ' + filtered.length + ' 处';
    } else if (parts.length === 0) {
        el.textContent = '当前显示 ' + filtered.length + ' 处文物';
    } else {
        el.textContent = '当前位置：' + parts.join('、') + ' ' + filtered.length + ' 处';
    }
}

function resetFilters() {
    document.getElementById('searchInput').value = '';
    document.getElementById('filterTown').value = '';
    document.getElementById('filterLevel').value = '';
    document.getElementById('filterCond').value = '';
    document.getElementById('filter3D').value = '';
    activeCats = new Set(allRelics.map(r=>r.category_main));
    document.querySelectorAll('.fp-chk').forEach(e => e.classList.add('active'));
    statFilters = {};
    onFilterChange();
}

function fitToRelics(relics) {
    const pts = relics.filter(r => r.center_lat && r.center_lng);
    if (pts.length === 0) return;
    if (pts.length === 1) {
        viewer.camera.flyTo({ destination: Cesium.Cartesian3.fromDegrees(pts[0].center_lng, pts[0].center_lat, 1500), duration: 1.2 });
        return;
    }
    let w = 180, s = 90, e = -180, n = -90;
    pts.forEach(r => { if (r.center_lng < w) w = r.center_lng; if (r.center_lng > e) e = r.center_lng; if (r.center_lat < s) s = r.center_lat; if (r.center_lat > n) n = r.center_lat; });
    const pad = 0.008;
    viewer.camera.flyTo({ destination: Cesium.Rectangle.fromDegrees(w - pad, s - pad, e + pad, n + pad), duration: 1.2 });
}

function renderResultList(relics) {
    const box = document.getElementById('resultList');
    if (relics.length === allRelics.length || relics.length === 0) { box.innerHTML = ''; return; }
    box.innerHTML = relics.slice(0, 80).map(r =>
        '<div class="list-item" onclick="flyTo(\'' + r.archive_code + '\')">' +
        '<div class="li-name">' + r.name + '</div>' +
        '<div class="li-meta"><span class="li-cat">' + (r.category_main || '') + '</span><span class="li-era">' + (r.era || '') + '</span><span>' + (r.township || '') + '</span></div></div>'
    ).join('');
}

function flyTo(code) {
    const r = allRelics.find(x => x.archive_code === code);
    if (!r || !r.center_lat) return;
    viewer.camera.flyTo({ destination: Cesium.Cartesian3.fromDegrees(r.center_lng, r.center_lat, 600), orientation: { heading: 0, pitch: Cesium.Math.toRadians(-90), roll: 0 }, duration: 1.2 });
    showInfo(r);
}
