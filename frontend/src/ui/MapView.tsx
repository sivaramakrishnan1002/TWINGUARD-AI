import { useEffect, useRef, useState } from 'react';
import { Map as MapLibreMap, NavigationControl, setWorkerUrl, type StyleSpecification } from 'maplibre-gl';
import mapWorkerUrl from 'maplibre-gl/dist/maplibre-gl-worker.mjs?worker&url';

setWorkerUrl(mapWorkerUrl);

type ViewMode = '2D' | '3D';

// Centered on the bounding-box midpoint of the provisional boundary source. The
// boundary itself is deliberately not drawn until a tile service is available.
const provisionalStudyAreaCenter: [number, number] = [80.174609, 13.071951];

const emptyMapStyle: StyleSpecification = {
  version: 8,
  sources: {},
  layers: [{
    id: 'empty-background',
    type: 'background',
    paint: { 'background-color': '#101d29' },
  }],
};

export function MapView({ compact = false }: { compact?: boolean }) {
  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<MapLibreMap | null>(null);
  const [view, setView] = useState<ViewMode>('2D');
  const [mapError, setMapError] = useState('');
  const [mapLoading, setMapLoading] = useState(true);

  useEffect(() => {
    if (!containerRef.current) return;

    const map = new MapLibreMap({
      container: containerRef.current,
      style: emptyMapStyle,
      center: provisionalStudyAreaCenter,
      zoom: 8,
      minZoom: 3,
      maxZoom: 18,
      pitch: 0,
      bearing: 0,
      attributionControl: false,
      keyboard: true,
      cooperativeGestures: true,
    });
    map.addControl(new NavigationControl({ visualizePitch: true }), 'bottom-right');
    map.once('load', () => setMapLoading(false));
    map.on('error', (event) => {
      setMapError(event.error.message);
      setMapLoading(false);
    });
    mapRef.current = map;

    return () => {
      map.remove();
      mapRef.current = null;
    };
  }, []);

  function setViewMode(nextView: ViewMode) {
    const map = mapRef.current;
    if (map) {
      map.easeTo({
        pitch: nextView === '3D' ? 55 : 0,
        bearing: nextView === '3D' ? -18 : 0,
        duration: 450,
      });
    }
    setView(nextView);
  }

  return (
    <section className="map-panel" aria-label="Map view">
      <div className={`map-toolbar${compact ? ' map-toolbar--compact' : ''}`}>
        <div className="map-title"><span className="eyebrow">{compact ? 'EMPTY MAP CANVAS' : 'SPATIAL VIEW · CHENNAI'}</span><strong>Study area · boundary not verified</strong></div>
        <div className="view-toggle" role="group" aria-label="Map perspective">
          <button type="button" aria-pressed={view === '2D'} onClick={() => setViewMode('2D')}>2D</button>
          <button type="button" aria-pressed={view === '3D'} onClick={() => setViewMode('3D')}>3D</button>
        </div>
      </div>
      <div className="map-canvas">
        <div ref={containerRef} className="maplibre-canvas" aria-label="Interactive map canvas" />
        <div className="map-empty" aria-live="polite" aria-atomic="true">
          <div className="map-glyph" aria-hidden="true"><span /><span /><span /></div>
          <span className="eyebrow">{mapError ? 'RENDERER ERROR' : mapLoading ? 'LOCAL CANVAS' : 'MAP DATA UNAVAILABLE'} · {view}</span>
          <h2>{mapError ? 'Map renderer unavailable' : mapLoading ? 'Preparing map canvas' : 'No verified map sources'}</h2>
          <p>{mapError ? `The map could not initialize: ${mapError}` : mapLoading ? 'Starting the local renderer. No external tiles or flood data are requested.' : 'No basemap, project boundary, terrain, or event layer is connected.'}</p>
          <span className="map-empty-badge">EMPTY STYLE · NO GEOGRAPHIC RESULT</span>
          {view === '3D' && <p className="terrain-notice">Perspective only · terrain tiles unavailable</p>}
        </div>
        <div className="map-coordinates"><span>TILE SERVICE <b>UNAVAILABLE</b></span><span>BOUNDARY <b>PROVISIONAL · NOT DRAWN</b></span></div>
      </div>
      <div className="map-legend" aria-label="Map legend">
        <span className="legend-title">FLOOD LAYER LEGEND · NO LAYERS CONNECTED</span>
        <div className="legend-slots">
          <div className="legend-slot"><strong>Flood extent</strong><span>Unavailable</span></div>
          <div className="legend-slot"><strong>Depth</strong><span>m · no raster loaded</span></div>
          <div className="legend-slot"><strong>Risk class</strong><span>Legend unavailable</span></div>
          <div className="legend-slot"><strong>Uncertainty</strong><span>Coverage unavailable</span></div>
          <div className="legend-slot legend-slot--nodata"><strong>NoData</strong><span><i className="legend-hatch" />Transparent · not dry</span></div>
        </div>
        <p className="legend-explainer">NoData is transparent. Missing coverage means unknown, not dry; no depth, class, or uncertainty values are being shown.</p>
      </div>
    </section>
  );
}
