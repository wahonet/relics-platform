function _isMobile() { return window.innerWidth <= 768; }

function updateLayout() {
    if (_isMobile()) return;
    const filterPanel = document.getElementById('filterPanel');
    const infoPanel = document.getElementById('infoPanel');
    const filterOpen = filterPanel ? filterPanel.classList.contains('open') : false;
    const infoOpen = infoPanel ? infoPanel.style.display === 'block' : false;
    const SIDE_W = 360;

    if (infoOpen) {
        infoPanel.style.right = '14px';
    }

    const legendLeft = filterOpen ? SIDE_W + 16 : 16;
    const legend = document.getElementById('legend');
    if (legend) legend.style.left = legendLeft + 'px';
}

function togglePanel(which) {
    const fp = document.getElementById('filterPanel');
    if (which === 'filter') {
        fp.classList.toggle('open');
        document.getElementById('btnFilter').classList.toggle('on', fp.classList.contains('open'));
        updateLayout();
        if (_isMobile()) {
            _syncMobileNav(fp.classList.contains('open') ? 'filter' : 'map');
        }
    }
}

function toggleFullscreen() {
    if (!document.fullscreenElement) document.documentElement.requestFullscreen();
    else document.exitFullscreen();
}

function resetAll() {
    if (document.getElementById('model3dBox').classList.contains('open')) close3DBox();

    document.getElementById('filterPanel').classList.remove('open');
    document.getElementById('btnFilter').classList.remove('on');
    document.getElementById('infoPanel').style.display = 'none';

    document.getElementById('searchInput').value = '';
    document.getElementById('filterTown').value = '';
    document.getElementById('filterLevel').value = '';
    document.getElementById('filterCond').value = '';
    document.getElementById('filter3D').value = '';
    activeCats = new Set(allRelics.map(r => r.category_main));
    document.querySelectorAll('.fp-chk').forEach(e => e.classList.add('active'));
    statFilters = {};

    if (typeof _relicPointsHidden !== 'undefined' && _relicPointsHidden) {
        const hideRelicToggle = document.getElementById('hideRelicToggle');
        if (hideRelicToggle) hideRelicToggle.checked = false;
        toggleHideRelicPoints();
    }
    activeGroup = 'category_main';
    dimColorMaps = {};

    onFilterChange();
    updateLayout();
    if (_isMobile()) mobileSetTab('map');

    viewer.camera.flyTo({
        destination: Cesium.Cartesian3.fromDegrees(CENTER.lng, CENTER.lat, CENTER.h),
        orientation: { heading: 0, pitch: Cesium.Math.toRadians(-90), roll: 0 },
        duration: 1.2,
    });

    toast('已重置所有筛选和视图');
}

function toggleSettings() {
    const panel = document.getElementById('settingsPanel');
    const mask = document.getElementById('settingsMask');
    const btn = document.getElementById('settingsBtn');
    const open = panel.classList.toggle('open');
    mask.classList.toggle('open', open);
    btn.classList.toggle('on', open);
}

const _themes = {
    blue:   { accent:'#58a6ff', accent2:'#79c0ff', bd:'rgba(88,166,255,0.2)',  bdActive:'rgba(88,166,255,0.5)',  gradient:'135deg,rgba(13,17,23,.97),rgba(22,40,65,.97)' },
    purple: { accent:'#bc8cff', accent2:'#d2a8ff', bd:'rgba(188,140,255,0.2)', bdActive:'rgba(188,140,255,0.5)', gradient:'135deg,rgba(13,17,23,.97),rgba(35,22,55,.97)' },
    gold:   { accent:'#ffd700', accent2:'#ffe566', bd:'rgba(255,215,0,0.2)',   bdActive:'rgba(255,215,0,0.5)',   gradient:'135deg,rgba(13,17,23,.97),rgba(50,40,15,.97)' },
    pink:   { accent:'#f778ba', accent2:'#ffb3d9', bd:'rgba(247,120,186,0.2)', bdActive:'rgba(247,120,186,0.5)', gradient:'135deg,rgba(13,17,23,.97),rgba(50,18,35,.97)' },
};

function setTheme(name) {
    const t = _themes[name];
    if (!t) return;
    const root = document.documentElement.style;
    root.setProperty('--accent', t.accent);
    root.setProperty('--accent2', t.accent2);
    root.setProperty('--bd', t.bd);
    root.setProperty('--bd-active', t.bdActive);
    document.getElementById('header').style.background = 'linear-gradient(' + t.gradient + ')';
    document.querySelectorAll('.sp-theme').forEach(el => el.classList.toggle('on', el.getAttribute('data-theme') === name));
}

function doLogout() {
    document.cookie = 'session=; path=/; expires=Thu, 01 Jan 1970 00:00:00 GMT';
    window.location.href = '/login';
}

function toggleHelp() {
    const panel = document.getElementById('helpPanel');
    const mask = document.getElementById('helpMask');
    const open = panel.classList.toggle('open');
    mask.classList.toggle('open', open);
}

function setHDMode(enabled) {
    _hdMode = !!enabled;
    try { localStorage.setItem('hdMode', _hdMode ? '1' : '0'); } catch (e) {}

    var cb = document.getElementById('hdModeToggle');
    if (cb) cb.checked = _hdMode;

    if (typeof applyHDRendering === 'function') applyHDRendering();

    _symbolCache = {};
    if (typeof onFilterChange === 'function') onFilterChange();

    var hdBoost = _hdMode ? 1.3 : 1.0;
    (bndLayers.townLabel || []).forEach(function (e) {
        if (e && e.label) {
            e.label.scale = 0.7 * hdBoost;
            e.label.outlineWidth = _hdMode ? 5 : 4;
        }
    });
    (bndLayers.villageLabel || []).forEach(function (e) {
        if (e && e.label) {
            e.label.scale = 0.6 * hdBoost;
            e.label.outlineWidth = _hdMode ? 5 : 4;
        }
    });

    if (typeof updateLegend === 'function') updateLegend();

    if (typeof toast === 'function') toast(_hdMode ? '已切换为高清模式（画面更清晰）' : '已切换为性能模式');
    viewer.scene.requestRender();
}

function setUISize(size) {
    document.querySelectorAll('.sp-size').forEach(b => {
        b.classList.toggle('on', b.getAttribute('data-size') === size);
    });
    const root = document.documentElement.style;
    if (size === 'sm') {
        root.setProperty('--hdr', '42px');
        root.setProperty('--side-w', '300px');
        root.setProperty('--info-w', '370px');
        document.body.style.fontSize = '12px';
    } else if (size === 'lg') {
        root.setProperty('--hdr', '56px');
        root.setProperty('--side-w', '420px');
        root.setProperty('--info-w', '480px');
        document.body.style.fontSize = '15px';
    } else {
        root.setProperty('--hdr', '50px');
        root.setProperty('--side-w', '360px');
        root.setProperty('--info-w', '420px');
        document.body.style.fontSize = '13.5px';
    }
    updateLayout();
}


let _mobileTab = 'map';
function _syncMobileNav(tab) {
    _mobileTab = tab;
    document.querySelectorAll('#mobileNav .mn-btn').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.tab === tab);
    });
}

function mobileSetTab(tab) {
    _mobileTab = tab;

    document.querySelectorAll('#mobileNav .mn-btn').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.tab === tab);
    });

    const body = document.body;
    document.getElementById('filterPanel').classList.remove('open');
    document.getElementById('btnFilter').classList.remove('on');

    switch (tab) {
        case 'filter':
            document.getElementById('filterPanel').classList.add('open');
            document.getElementById('btnFilter').classList.add('on');
            break;
        default:
            _syncMobileNav('map');
            break;
    }
}

function _mobileUpdateFilterBadge() {
    if (!_isMobile()) return;
    const btn = document.querySelector('#mobileNav .mn-btn[data-tab="filter"]');
    if (!btn) return;
    let badge = btn.querySelector('.mn-badge');
    const count = typeof filtered !== 'undefined' ? filtered.length : 0;
    const total = typeof allRelics !== 'undefined' ? allRelics.length : 0;
    if (count > 0 && count < total) {
        if (!badge) {
            badge = document.createElement('span');
            badge.className = 'mn-badge';
            btn.appendChild(badge);
        }
        badge.textContent = count;
    } else if (badge) {
        badge.remove();
    }
}
