// 应用入口：加载数据、绑定交互、启动。
async function init() {
    try {
        const [rResp, sResp] = await Promise.all([
            fetch(API + '/api/relics'), fetch(API + '/api/stats'),
        ]);
        allRelics = await rResp.json();
        const globalStats = await sResp.json();
        allRelics.forEach(r => { activeCats.add(r.category_main); });
        dimColorMaps[activeGroup] = buildColorMap(allRelics, DIMS.find(d=>d.id===activeGroup));
        populateFilters();
        onFilterChange();
        loadPolygons();
        loadBoundaries();
        // 极简模式：只保留地图与文物检索主链路，不加载路线/日志数据。
        document.getElementById('loading').style.display = 'none';
    } catch (e) {
        console.error(e);
        document.getElementById('loading').innerHTML = '<div style="color:var(--red)">数据加载失败，请检查后端服务</div>';
    }
}

function updateBadges(s) {}

// 单击：显示文物/路线点信息；双击：按乡镇或村筛选。
const handler = new Cesium.ScreenSpaceEventHandler(viewer.scene.canvas);
let _clickTimer = null;
handler.setInputAction(function (click) {
    clearTimeout(_clickTimer);
    _clickTimer = setTimeout(() => {
        const picked = viewer.scene.pick(click.position);
        if (Cesium.defined(picked) && picked.id && picked.id.properties) {
            const r = {};
            picked.id.properties.propertyNames.forEach(n => { r[n] = picked.id.properties[n].getValue(); });
            if (r._isRoutePoint) {
                _onRoutePointClick(r);
            } else if (!r._boundaryType && !r._isRouteLine) {
                showInfo(r);
            }
        }
    }, 250);
}, Cesium.ScreenSpaceEventType.LEFT_CLICK);

handler.setInputAction(function (click) {
    clearTimeout(_clickTimer);
    const picked = viewer.scene.pick(click.position);
    if (Cesium.defined(picked) && picked.id && picked.id.properties) {
        try {
            const bt = picked.id.properties._boundaryType;
            if (bt) {
                const type = bt.getValue();
                const name = picked.id.properties._boundaryName.getValue();
                if (type === 'township' && name) {
                    statFilters['township'] = name;
                    onFilterChange();
                    toast('已筛选乡镇：' + name);
                } else if (type === 'village' && name) {
                    statFilters['_village'] = name;
                    onFilterChange();
                    toast('已筛选村：' + name);
                }
            }
        } catch(e) {}
    }
}, Cesium.ScreenSpaceEventType.LEFT_DOUBLE_CLICK);

// ESC：优先关闭 3D/PDF 弹窗，否则整体重置。
document.addEventListener('keydown', function(e) {
    if (e.key === 'Escape') {
        const m3d = document.getElementById('model3dBox');
        const pdf = document.getElementById('pdfBox');
        if (m3d && m3d.style.display !== 'none' && m3d.classList.contains('open')) {
            close3DBox();
        } else if (pdf && pdf.style.display !== 'none') {
            closePdfBox();
        } else {
            resetAll();
        }
    }
});

// 在移动端对几个全局函数做包装，联动底部导航和筛选角标。
(function _initMobile() {
    const origToggleChat = window.toggleChat;
    if (origToggleChat) {
        window.toggleChat = function() {
            origToggleChat();
            if (_isMobile()) {
                const open = document.getElementById('chatPanel').classList.contains('open');
                _syncMobileNav(open ? 'chat' : 'map');
            }
        };
    }

    const origOnFilterChange = window.onFilterChange;
    if (origOnFilterChange) {
        window.onFilterChange = function() {
            origOnFilterChange();
            if (typeof _mobileUpdateFilterBadge === 'function') _mobileUpdateFilterBadge();
        };
    }

    const origCloseInfo = window.closeInfo;
    if (origCloseInfo) {
        window.closeInfo = function() {
            origCloseInfo();
            if (_isMobile()) viewer.scene.requestRender();
        };
    }
})();

initMapZoomSlider();
updateLayout();
viewer.scene.postRender.addEventListener(updateScaleBar);

(function syncHDToggle() {
    var cb = document.getElementById('hdModeToggle');
    if (cb) cb.checked = !!_hdMode;
})();

init();
