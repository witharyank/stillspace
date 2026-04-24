(() => {
    const MODES = {
        fastest: { label: "Fastest", color: "#3b82f6", family: "simple" },
        calm: { label: "Calm", color: "#22c55e", family: "simple" },
        safe: { label: "Safe", color: "#f97316", family: "simple" },
        accessibility: { label: "Accessibility", color: "#8b5cf6", family: "advanced" },
        dog: { label: "Dog Walk", color: "#f59e0b", family: "advanced" },
        weather: { label: "Weather Smart", color: "#06b6d4", family: "advanced" },
    };
    const DEFAULT_CENTER = [30.7333, 76.7794];
    const DEFAULT_ZOOM = 14;
    const TILE_DARK = "https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png";
    const TILE_LIGHT = "https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png";
    const SIMPLE_MODES = new Set(["fastest", "calm", "safe"]);

    const state = {
        mode: "calm",
        dogSubMode: "quick",
        preferenceBias: 50,
        theme: "dark",
        map: null,
        tileLayer: null,
        startPoint: null,
        endPoint: null,
        pendingPoint: null,
        startMarker: null,
        endMarker: null,
        fastestLayer: null,
        smartLayer: null,
        smartGlowLayer: null,
        connectorLayers: [],
        safetyLayer: null,
        graphBounds: null,
        maxSnapDistanceM: null,
        loading: false,
        animationFrames: [],
        activeRequestController: null,
        requestSequence: 0,
        mobilePanelCollapsed: false,
    };

    const DOM = {
        body: document.body,
        controlPanel: document.getElementById("controlPanel"),
        sheetToggle: document.getElementById("sheetToggle"),
        themeToggle: document.getElementById("themeToggle"),
        simpleModeTabs: document.getElementById("simpleModeTabs"),
        advancedToggle: document.getElementById("advancedToggle"),
        advancedPanel: document.getElementById("advancedPanel"),
        advancedModeGrid: document.getElementById("advancedModeGrid"),
        routeTuning: document.getElementById("routeTuning"),
        dogContextPanel: document.getElementById("dogContextPanel"),
        dogOptionButtons: document.getElementById("dogOptionButtons"),
        routeBtn: document.getElementById("routeBtn"),
        resetBtn: document.getElementById("resetBtn"),
        startCard: document.getElementById("startCard"),
        endCard: document.getElementById("endCard"),
        startText: document.getElementById("startText"),
        endText: document.getElementById("endText"),
        statusLine: document.getElementById("statusLine"),
        loadingStrip: document.getElementById("loadingStrip"),
        metricsPanel: document.getElementById("metricsPanel"),
        fastestStatText: document.getElementById("fastestStatText"),
        smartStatText: document.getElementById("smartStatText"),
        smartMetricCard: document.getElementById("smartMetricCard"),
        comparisonGrid: document.getElementById("comparisonGrid"),
        extraDistance: document.getElementById("extraDistance"),
        extraTime: document.getElementById("extraTime"),
        distanceDiff: document.getElementById("distanceDiff"),
        modeHud: document.getElementById("modeHud"),
        weatherHud: document.getElementById("weatherHud"),
        floatingSummary: document.getElementById("floatingSummary"),
        summaryTitle: document.getElementById("summaryTitle"),
        summaryEta: document.getElementById("summaryEta"),
        summaryDist: document.getElementById("summaryDist"),
        summaryTime: document.getElementById("summaryTime"),
        summaryScore: document.getElementById("summaryScore"),
        tabRouteBtn: document.getElementById("tabRouteBtn"),
        tabHistoryBtn: document.getElementById("tabHistoryBtn"),
        routePanel: document.getElementById("routePanel"),
        historyPanel: document.getElementById("historyPanel"),
        refreshHistoryBtn: document.getElementById("refreshHistoryBtn"),
        historyList: document.getElementById("historyList"),
        historyEmpty: document.getElementById("historyEmpty"),
        historyLoadingStrip: document.getElementById("historyLoadingStrip"),
    };

    function init() {
        applyPreferredTheme();
        initializeMap();
        bindEvents();
        setMode("calm");
        bootstrapCoverage();
        setStatus("Step 1: Pick start. Step 2: Pick destination. Step 3: Generate route.");
    }

    function applyPreferredTheme() {
        const stored = localStorage.getItem("stillspace-theme");
        if (stored === "light" || stored === "dark") {
            state.theme = stored;
        } else if (window.matchMedia && window.matchMedia("(prefers-color-scheme: light)").matches) {
            state.theme = "light";
        }
        applyTheme(state.theme);
    }

    function applyTheme(theme) {
        state.theme = theme === "light" ? "light" : "dark";
        DOM.body.classList.toggle("theme-light", state.theme === "light");
        DOM.themeToggle.textContent = state.theme === "light" ? "Dark" : "Light";
        localStorage.setItem("stillspace-theme", state.theme);

        if (state.map) {
            const nextUrl = state.theme === "light" ? TILE_LIGHT : TILE_DARK;
            state.map.removeLayer(state.tileLayer);
            state.tileLayer = L.tileLayer(nextUrl, { maxZoom: 19 }).addTo(state.map);
        }
    }

    function initializeMap() {
        state.map = L.map("map", {
            zoomControl: false,
            preferCanvas: true,
            doubleClickZoom: false,
        }).setView(DEFAULT_CENTER, DEFAULT_ZOOM);
        L.control.zoom({ position: "bottomright" }).addTo(state.map);
        state.tileLayer = L.tileLayer(state.theme === "light" ? TILE_LIGHT : TILE_DARK, { maxZoom: 19 }).addTo(state.map);
        state.map.on("click", handleMapClick);
    }

    async function bootstrapCoverage() {
        try {
            const response = await fetch("/health");
            if (!response.ok) {
                return;
            }
            const data = await response.json();
            const bbox = data.graph_bbox;
            if (bbox && Number.isFinite(bbox.min_lat) && Number.isFinite(bbox.min_lon) && Number.isFinite(bbox.max_lat) && Number.isFinite(bbox.max_lon)) {
                state.graphBounds = L.latLngBounds(
                    [bbox.min_lat, bbox.min_lon],
                    [bbox.max_lat, bbox.max_lon]
                );
            }
            if (typeof data.max_snap_distance_m === "number") {
                state.maxSnapDistanceM = data.max_snap_distance_m;
            }
        } catch (_error) {
            // Non-blocking: app can still work without coverage metadata.
        }
    }

    function bindEvents() {
        DOM.themeToggle.addEventListener("click", () => applyTheme(state.theme === "dark" ? "light" : "dark"));
        DOM.simpleModeTabs.addEventListener("click", handleSimpleModeClick);
        DOM.advancedModeGrid.addEventListener("click", handleAdvancedModeClick);
        DOM.advancedToggle.addEventListener("click", toggleAdvancedPanel);
        DOM.routeTuning.addEventListener("input", () => {
            state.preferenceBias = Number(DOM.routeTuning.value);
        });
        DOM.dogOptionButtons.addEventListener("click", handleDogOptionClick);
        DOM.routeBtn.addEventListener("click", generateRoute);
        DOM.resetBtn.addEventListener("click", resetJourney);
        DOM.startCard.addEventListener("click", () => {
            state.pendingPoint = "start";
            setStatus("Click on the map to place your start point.");
        });
        DOM.endCard.addEventListener("click", () => {
            state.pendingPoint = "end";
            setStatus("Click on the map to place your destination.");
        });
        DOM.sheetToggle.addEventListener("click", toggleMobilePanel);
        DOM.tabRouteBtn.addEventListener("click", () => switchTab("route"));
        DOM.tabHistoryBtn.addEventListener("click", () => switchTab("history"));
        DOM.refreshHistoryBtn.addEventListener("click", fetchHistory);
        window.addEventListener("resize", debounce(() => state.map.invalidateSize(), 180));
    }

    function switchTab(tab) {
        const isRoute = tab === "route";
        DOM.tabRouteBtn.classList.toggle("active", isRoute);
        DOM.tabRouteBtn.setAttribute("aria-selected", String(isRoute));
        DOM.tabHistoryBtn.classList.toggle("active", !isRoute);
        DOM.tabHistoryBtn.setAttribute("aria-selected", String(!isRoute));

        DOM.routePanel.classList.toggle("hidden", !isRoute);
        DOM.historyPanel.classList.toggle("hidden", isRoute);

        if (!isRoute) {
            fetchHistory();
        }
    }

    async function fetchHistory() {
        DOM.historyEmpty.classList.add("hidden");
        DOM.historyLoadingStrip.classList.remove("hidden");
        Array.from(DOM.historyList.children).forEach(el => {
            if (el !== DOM.historyEmpty && el !== DOM.historyLoadingStrip) {
                el.remove();
            }
        });

        try {
            const resp = await fetch("/api/history");
            const data = await resp.json();
            renderHistory(data.history || []);
        } catch (e) {
            console.error("Failed to load history", e);
            renderHistory([]);
        }
    }

    function renderHistory(items) {
        DOM.historyLoadingStrip.classList.add("hidden");
        if (!items || items.length === 0) {
            DOM.historyEmpty.classList.remove("hidden");
            return;
        }
        DOM.historyEmpty.classList.add("hidden");

        items.forEach(item => {
            const card = document.createElement("div");
            card.className = "history-item";
            
            const date = new Date(item.timestamp + "Z");
            const timeStr = date.toLocaleString();
            
            const modeLabel = MODES[item.mode] ? MODES[item.mode].label : item.mode;
            const modeColor = MODES[item.mode] ? MODES[item.mode].color : "inherit";

            card.innerHTML = `
                <span class="hist-mode" style="color: ${modeColor}">${modeLabel}</span>
                <span class="hist-coords">S: ${item.start_lat.toFixed(4)}, ${item.start_lon.toFixed(4)}</span>
                <span class="hist-coords">D: ${item.end_lat.toFixed(4)}, ${item.end_lon.toFixed(4)}</span>
                <span class="hist-time">${timeStr}</span>
                <button class="history-delete" title="Delete" aria-label="Delete">🗑️</button>
            `;

            card.addEventListener("click", () => loadHistoryRoute(item));
            card.querySelector(".history-delete").addEventListener("click", (e) => {
                e.stopPropagation();
                deleteHistory(item.id, card);
            });

            DOM.historyList.appendChild(card);
        });
    }

    async function deleteHistory(id, cardElement) {
        try {
            const resp = await fetch("/api/history/" + id, { method: "DELETE" });
            if (resp.ok) {
                cardElement.remove();
                if (DOM.historyList.children.length <= 2) {
                    DOM.historyEmpty.classList.remove("hidden");
                }
            }
        } catch (e) {
            console.error("Delete failed", e);
        }
    }

    function loadHistoryRoute(item) {
        if (!item.start_lat || !item.end_lat) return;

        switchTab("route");
        resetJourney();

        const startLngLat = L.latLng(item.start_lat, item.start_lon);
        const endLngLat = L.latLng(item.end_lat, item.end_lon);

        setStartPoint(startLngLat);
        setEndPoint(endLngLat);
        if (MODES[item.mode]) {
            setMode(item.mode);
        }
        
        setTimeout(() => {
            generateRoute();
        }, 300);
    }

    function handleSimpleModeClick(event) {
        const tab = event.target.closest(".mode-tab");
        if (!tab) {
            return;
        }
        setMode(tab.dataset.mode);
    }

    function handleAdvancedModeClick(event) {
        const card = event.target.closest(".mode-card");
        if (!card) {
            return;
        }
        setMode(card.dataset.mode);
    }

    function toggleAdvancedPanel() {
        const isHidden = DOM.advancedPanel.classList.contains("hidden");
        DOM.advancedPanel.classList.toggle("hidden", !isHidden);
        DOM.advancedToggle.setAttribute("aria-expanded", String(isHidden));
        DOM.advancedToggle.textContent = isHidden
            ? "Hide Specialized Modes"
            : "Advanced / Specialized Modes";
        if (isHidden) {
            setStatus("Specialized modes opened.");
        }
    }

    function handleDogOptionClick(event) {
        const button = event.target.closest(".dog-option");
        if (!button) {
            return;
        }
        state.dogSubMode = button.dataset.dogMode;
        DOM.dogOptionButtons.querySelectorAll(".dog-option").forEach((chip) => {
            chip.classList.toggle("active", chip === button);
        });
    }

    function setMode(modeName) {
        if (!MODES[modeName]) {
            return;
        }
        state.mode = modeName;
        const modeColor = MODES[modeName].color;
        document.documentElement.style.setProperty("--mode-accent", modeColor);

        DOM.simpleModeTabs.querySelectorAll(".mode-tab").forEach((tab) => {
            const active = tab.dataset.mode === modeName;
            tab.classList.toggle("active", active);
            tab.setAttribute("aria-selected", String(active));
        });

        DOM.advancedModeGrid.querySelectorAll(".mode-card").forEach((card) => {
            const active = card.dataset.mode === modeName;
            card.classList.toggle("active", active);
            card.setAttribute("aria-pressed", String(active));
        });

        if (SIMPLE_MODES.has(modeName)) {
            DOM.advancedModeGrid.querySelectorAll(".mode-card").forEach((card) => card.classList.remove("active"));
        }

        DOM.modeHud.textContent = `Mode: ${MODES[modeName].label}`;
        DOM.summaryTitle.textContent = `${MODES[modeName].label} Route`;

        const dogMode = modeName === "dog";
        DOM.dogContextPanel.classList.toggle("hidden", !dogMode);
        if (dogMode) {
            DOM.dogOptionButtons.querySelectorAll(".dog-option").forEach((chip) => {
                chip.classList.toggle("active", chip.dataset.dogMode === state.dogSubMode);
            });
            setStatus("Dog walk mode active. Pick the walk intent.");
        }

        if (modeName === "safe") {
            ensureSafetyZonesVisible();
        } else {
            hideSafetyZones();
        }
    }

    async function ensureSafetyZonesVisible() {
        if (state.safetyLayer) {
            if (!state.map.hasLayer(state.safetyLayer)) {
                state.safetyLayer.addTo(state.map);
            }
            return;
        }
        try {
            const response = await fetch("/api/safety_zones");
            const geojson = await response.json();
            state.safetyLayer = L.geoJSON(geojson, {
                style: {
                    color: "#ef4444",
                    fillColor: "#ef4444",
                    fillOpacity: 0.16,
                    weight: 1.2,
                },
            }).addTo(state.map);
        } catch (error) {
            setStatus("Safety zones failed to load.", true);
        }
    }

    function hideSafetyZones() {
        if (state.safetyLayer && state.map.hasLayer(state.safetyLayer)) {
            state.map.removeLayer(state.safetyLayer);
        }
    }

    function toggleMobilePanel() {
        state.mobilePanelCollapsed = !state.mobilePanelCollapsed;
        DOM.controlPanel.classList.toggle("collapsed", state.mobilePanelCollapsed);
        DOM.sheetToggle.setAttribute("aria-expanded", String(!state.mobilePanelCollapsed));
        setTimeout(() => state.map.invalidateSize(), 220);
    }

    function handleMapClick(event) {
        if (state.loading) {
            return;
        }

        const normalizedLatLng = event.latlng.wrap();

        if (state.pendingPoint === "start") {
            setStartPoint(normalizedLatLng);
            state.pendingPoint = null;
            setStatus("Start point updated.");
            return;
        }
        if (state.pendingPoint === "end") {
            setEndPoint(normalizedLatLng);
            state.pendingPoint = null;
            setStatus("Destination updated.");
            return;
        }

        if (!state.startPoint) {
            setStartPoint(normalizedLatLng);
            setStatus("Start selected. Now click destination.");
            return;
        }
        if (!state.endPoint) {
            setEndPoint(normalizedLatLng);
            setStatus("Destination selected. Generate route.");
            return;
        }

        setEndPoint(normalizedLatLng);
        setStatus("Destination moved to new location.");
    }

    function setStartPoint(latlng) {
        state.startPoint = latlng;
        DOM.startText.textContent = `${latlng.lat.toFixed(5)}, ${latlng.lng.toFixed(5)}`;
        DOM.startCard.classList.add("active");

        if (state.startMarker) {
            state.startMarker.setLatLng(latlng);
        } else {
            state.startMarker = L.marker(latlng, { icon: markerIcon("#22c55e") }).addTo(state.map);
        }
    }

    function setEndPoint(latlng) {
        state.endPoint = latlng;
        DOM.endText.textContent = `${latlng.lat.toFixed(5)}, ${latlng.lng.toFixed(5)}`;
        DOM.endCard.classList.add("active");

        if (state.endMarker) {
            state.endMarker.setLatLng(latlng);
        } else {
            state.endMarker = L.marker(latlng, { icon: markerIcon("#3b82f6") }).addTo(state.map);
        }
    }

    function markerIcon(color) {
        return L.divIcon({
            className: "stillspace-marker",
            html: `<span style="display:block;width:16px;height:16px;border-radius:999px;border:2px solid #fff;background:${color};box-shadow:0 3px 10px rgba(0,0,0,0.36);"></span>`,
            iconSize: [16, 16],
            iconAnchor: [8, 8],
        });
    }

    function setLoading(loading) {
        state.loading = loading;
        DOM.loadingStrip.classList.toggle("hidden", !loading);
        DOM.routeBtn.disabled = loading;
        DOM.resetBtn.disabled = loading;
    }

    function setStatus(message, isWarning = false) {
        DOM.statusLine.textContent = message;
        DOM.statusLine.style.color = isWarning ? "#f97316" : "";
    }

    function abortActiveRequest() {
        if (state.activeRequestController) {
            state.activeRequestController.abort();
            state.activeRequestController = null;
        }
    }

    async function generateRoute() {
        if (!state.startPoint || !state.endPoint) {
            setStatus("Please select both start and destination points.", true);
            return;
        }

        abortActiveRequest();
        const controller = new AbortController();
        state.activeRequestController = controller;
        const requestSeq = ++state.requestSequence;

        setLoading(true);
        clearRouteLayers();
        DOM.metricsPanel.classList.add("hidden");
        DOM.floatingSummary.classList.add("hidden");
        setStatus("Routing in progress...");

        try {
            const response = await fetch("/smart_route", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    start_lat: state.startPoint.lat,
                    start_lon: state.startPoint.lng,
                    end_lat: state.endPoint.lat,
                    end_lon: state.endPoint.lng,
                    route_mode: state.mode,
                    dog_sub_mode: state.dogSubMode,
                    preference_bias: state.preferenceBias,
                }),
                signal: controller.signal,
            });
            const payload = await response.json();
            if (requestSeq !== state.requestSequence) {
                return;
            }
            if (!response.ok) {
                if (payload.code === "outside_coverage" && payload.details) {
                    const s = payload.details.start_snap_distance_m;
                    const e = payload.details.end_snap_distance_m;
                    const max = payload.details.max_snap_distance_m;
                    throw new Error(`Point outside coverage (snap: start ${s}m, end ${e}m, max ${max}m).`);
                }
                throw new Error(payload.error || "Route calculation failed.");
            }
            renderRouteResult(payload);
        } catch (error) {
            if (error.name === "AbortError") {
                return;
            }
            setStatus(error.message || "Unable to generate route.", true);
            DOM.weatherHud.textContent = "Weather: --";
        } finally {
            if (requestSeq === state.requestSequence) {
                setLoading(false);
            }
        }
    }

    function renderRouteResult(payload) {
        const fastestRaw = payload.fastest_route || (payload.routes && payload.routes.fastest) || [];
        const smartRaw = payload.smart_route || (payload.routes && payload.routes.smart) || [];
        const fastestRoute = fastestRaw;
        const smartRoute = smartRaw;
        const connectors = payload.connectors || {};
        const fastestConnectors = connectors.fastest || {};
        const smartConnectors = connectors.smart || {};
        const shortestStats = payload.shortest_stats || (payload.stats && payload.stats.fastest) || null;
        const smartStats = payload.smart_stats || (payload.stats && payload.stats.smart) || null;
        const comparison = payload.comparison || (payload.stats && payload.stats.comparison) || null;
        const weather = payload.weather || null;

        if (!fastestRoute || fastestRoute.length < 2) {
            setStatus("Route geometry is incomplete for these points.", true);
            return;
        }

        const isFastestOnly = state.mode === "fastest" || !smartRoute || smartRoute.length < 2;
        const modeColor = MODES[state.mode].color;

        if (isFastestOnly) {
            state.fastestLayer = L.polyline([], {
                color: MODES.fastest.color,
                weight: 6,
                opacity: 0.95,
                lineCap: "round",
                lineJoin: "round",
            }).addTo(state.map);
            animatePolyline(state.fastestLayer, fastestRoute, 900);
            drawConnectorSegments(fastestConnectors, MODES.fastest.color);
            fitRouteBounds([fastestRoute]);
        } else {
            state.fastestLayer = L.polyline([], {
                color: MODES.fastest.color,
                weight: 4,
                opacity: 0.72,
                lineCap: "round",
                lineJoin: "round",
                dashArray: "10 10",
            }).addTo(state.map);
            state.smartGlowLayer = L.polyline([], {
                color: modeColor,
                weight: 14,
                opacity: 0.2,
                lineCap: "round",
                lineJoin: "round",
            }).addTo(state.map);
            state.smartLayer = L.polyline([], {
                color: modeColor,
                weight: 6,
                opacity: 0.95,
                lineCap: "round",
                lineJoin: "round",
            }).addTo(state.map);

            animatePolyline(state.fastestLayer, fastestRoute, 720);
            animatePolyline(state.smartGlowLayer, smartRoute, 900);
            animatePolyline(state.smartLayer, smartRoute, 980);
            drawConnectorSegments(smartConnectors, modeColor);
            fitRouteBounds([fastestRoute, smartRoute]);
        }

        updateMetrics(shortestStats, smartStats, comparison, isFastestOnly);
        updateWeatherHud(weather);
        setStatus("Route generated successfully.");
    }

    function animatePolyline(layer, coordinates, durationMs) {
        if (!coordinates || !coordinates.length) {
            return;
        }
        if (coordinates.length < 3) {
            layer.setLatLngs(coordinates);
            return;
        }

        const startTime = performance.now();
        const minChunk = 3;
        const frame = (now) => {
            const progress = Math.min((now - startTime) / durationMs, 1);
            const count = Math.max(minChunk, Math.floor(coordinates.length * progress));
            layer.setLatLngs(coordinates.slice(0, count));
            if (progress < 1) {
                const frameId = requestAnimationFrame(frame);
                state.animationFrames.push(frameId);
            }
        };
        const firstFrameId = requestAnimationFrame(frame);
        state.animationFrames.push(firstFrameId);
    }

    function clearAnimations() {
        state.animationFrames.forEach((frameId) => cancelAnimationFrame(frameId));
        state.animationFrames = [];
    }

    function clearRouteLayers() {
        clearAnimations();
        if (state.fastestLayer) {
            state.map.removeLayer(state.fastestLayer);
            state.fastestLayer = null;
        }
        if (state.smartLayer) {
            state.map.removeLayer(state.smartLayer);
            state.smartLayer = null;
        }
        if (state.smartGlowLayer) {
            state.map.removeLayer(state.smartGlowLayer);
            state.smartGlowLayer = null;
        }
        if (state.connectorLayers.length) {
            state.connectorLayers.forEach((layer) => state.map.removeLayer(layer));
            state.connectorLayers = [];
        }
    }

    function drawConnectorSegments(connectorSet, color) {
        const segments = [];
        if (connectorSet && Array.isArray(connectorSet.start) && connectorSet.start.length >= 2) {
            segments.push(connectorSet.start);
        }
        if (connectorSet && Array.isArray(connectorSet.end) && connectorSet.end.length >= 2) {
            segments.push(connectorSet.end);
        }
        segments.forEach((segment) => {
            const layer = L.polyline(segment, {
                color,
                weight: 3,
                opacity: 0.65,
                lineCap: "round",
                lineJoin: "round",
                dashArray: "5 7",
            }).addTo(state.map);
            state.connectorLayers.push(layer);
        });
    }

    function fitRouteBounds(routes) {
        const allCoords = [];
        routes.forEach((route) => {
            if (Array.isArray(route)) {
                route.forEach((point) => allCoords.push(point));
            }
        });
        if (!allCoords.length) {
            return;
        }
        const bounds = L.latLngBounds(allCoords);
        if (bounds.isValid()) {
            state.map.fitBounds(bounds, { padding: [64, 64], maxZoom: 17, animate: true });
        }
    }

    function updateMetrics(shortestStats, smartStats, comparison, isFastestOnly) {
        if (!shortestStats) {
            DOM.metricsPanel.classList.add("hidden");
            DOM.floatingSummary.classList.add("hidden");
            return;
        }

        DOM.fastestStatText.textContent = `${shortestStats.dist_km} km | ${shortestStats.time_min} min`;
        DOM.metricsPanel.classList.remove("hidden");

        const modeLabel = MODES[state.mode].label;
        let summaryDist = shortestStats.dist_km;
        let summaryTime = shortestStats.time_min;
        let score = 100;

        if (isFastestOnly || !smartStats || !comparison) {
            DOM.smartMetricCard.classList.add("hidden");
            DOM.comparisonGrid.classList.add("hidden");
        } else {
            DOM.smartMetricCard.classList.remove("hidden");
            DOM.comparisonGrid.classList.remove("hidden");
            DOM.smartStatText.textContent = `${smartStats.dist_km} km | ${smartStats.time_min} min`;
            DOM.extraDistance.textContent = formatSignedValue(comparison.extra_dist_km, "km");
            DOM.extraTime.textContent = formatSignedValue(comparison.extra_time_min, "min");
            DOM.distanceDiff.textContent = formatSignedValue(comparison.dist_diff_pct, "%");
            summaryDist = smartStats.dist_km;
            summaryTime = smartStats.time_min;
            score = Math.max(58, Math.round(100 - Math.abs(comparison.dist_diff_pct || 0)));
        }

        DOM.summaryTitle.textContent = `${modeLabel} Route`;
        DOM.summaryDist.textContent = `${summaryDist} km`;
        DOM.summaryTime.textContent = `${summaryTime} min`;
        DOM.summaryScore.textContent = `${score}`;
        DOM.summaryEta.textContent = `ETA ${calculateEta(summaryTime)}`;
        DOM.floatingSummary.classList.remove("hidden");
    }

    function updateWeatherHud(weather) {
        if (!weather || !weather.condition_text) {
            DOM.weatherHud.textContent = "Weather: --";
            return;
        }
        DOM.weatherHud.textContent = `Weather: ${weather.condition_text}`;
    }

    function formatSignedValue(value, unit) {
        const numeric = Number(value || 0);
        const sign = numeric > 0 ? "+" : "";
        return `${sign}${numeric}${unit ? ` ${unit}` : ""}`;
    }

    function calculateEta(minutes) {
        const eta = new Date();
        eta.setMinutes(eta.getMinutes() + Number(minutes || 0));
        return eta.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
    }

    function resetJourney() {
        abortActiveRequest();
        state.requestSequence += 1;
        setLoading(false);
        clearRouteLayers();

        if (state.startMarker) {
            state.map.removeLayer(state.startMarker);
            state.startMarker = null;
        }
        if (state.endMarker) {
            state.map.removeLayer(state.endMarker);
            state.endMarker = null;
        }

        state.startPoint = null;
        state.endPoint = null;
        state.pendingPoint = null;

        DOM.startText.textContent = "Not selected";
        DOM.endText.textContent = "Not selected";
        DOM.startCard.classList.remove("active");
        DOM.endCard.classList.remove("active");
        DOM.metricsPanel.classList.add("hidden");
        DOM.floatingSummary.classList.add("hidden");
        DOM.weatherHud.textContent = "Weather: --";
        setStatus("Journey reset. Step 1: Pick start. Step 2: Pick destination.");

        state.map.setView(DEFAULT_CENTER, DEFAULT_ZOOM, { animate: true });
    }

    function debounce(fn, delay) {
        let timer = null;
        return (...args) => {
            clearTimeout(timer);
            timer = setTimeout(() => fn(...args), delay);
        };
    }

    init();
})();
