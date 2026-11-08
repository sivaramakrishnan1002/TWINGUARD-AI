import { useEffect, useRef, useState } from 'react';
import * as Cesium from 'cesium';
import 'cesium/Build/Cesium/Widgets/widgets.css';
import { lonLatToUtm, terrainHeight, utmToLonLat, type TerrainGrid } from '../api/geo';
import { depthClass, estimatedLevels, LEVEL_HEIGHT_M, loadBoundary, loadWaterways, type FocusFile } from '../api/fixtures';
import type { DepthClass, DepthFrame, EdgeState, Incident, LonLat, RoadFeatureCollection, RouteOption, Shelter, StaticFeatureCollection } from '../api/v3types';

/**
 * B48 3D city twin (CesiumJS).
 * With VITE_CESIUM_ION_TOKEN (frontend/.env.local, git-ignored): Google Photorealistic 3D Tiles (ion 2275207),
 * Cesium World Terrain (ion 1) and Google 2D imagery (ion 3830182-3830184); attribution stays on screen.
 * Without it: our GLO-30 terrain, Esri/CARTO imagery and OSM footprints extruded and coloured by depth.
 * Simulated water is draped on the 3D tiles (classification volumes) or drawn as an animated water body.
 * Tokens are read only here and are never logged or sent to the TwinGuard API.
 */

export type ViewMode = '3d' | '2d' | 'satellite';
export interface TwinLayers { water: boolean; buildings: boolean; roads: boolean; wards: boolean; shelters: boolean; incidents: boolean; google: boolean }
export interface PickInfo { kind: 'building' | 'road' | 'shelter' | 'incident' | 'ward' | 'ground' | 'river'; title: string; lines: [string, string][]; location: LonLat }
export type TwinCommand = { type: 'home' | 'zoomIn' | 'zoomOut' | 'north' | 'tilt'; key: number };
export interface CameraInfo { headingDeg: number; metersPer100px: number | null; heightM: number }

/** Fallback EGM2008 undulation for Chennai until the datum is calibrated against the loaded surface. */
const GEOID_N_M = -86;
/** Water is drawn with this vertical exaggeration so sub-metre depths read at city scale (presentation only). */
export const WATER_EXAGGERATION = 3;

export const DEPTH_CLASS_STYLE: Record<DepthClass, { label: string; color: string }> = {
  dry: { label: 'Dry', color: '#5b6b7a' },
  lt_0_15: { label: '< 0.15 m', color: '#5fd0f0' },
  '0_15_to_0_5': { label: '0.15 – 0.5 m', color: '#2f7cff' },
  '0_5_to_1_0': { label: '0.5 – 1.0 m', color: '#ff9f43' },
  gt_1_0: { label: '> 1.0 m', color: '#ff3b5c' },
  unknown: { label: 'Unknown (outside model)', color: '#3a4652' },
};
export const EDGE_STYLE: Record<EdgeState, { label: string; color: string }> = {
  ASSESSED_PASSABLE: { label: 'Assessed passable', color: '#3ddc84' },
  ASSESSED_BLOCKED: { label: 'Assessed blocked', color: '#ff3b5c' },
  UNKNOWN: { label: 'Unknown / not assessed', color: '#f5c542' },
};
export const WATER_CLASS: { min: number; label: string; color: string; alpha: number }[] = [
  { min: 0.01, label: '0.01 – 0.15', color: '#8ff3ff', alpha: 0.42 },
  { min: 0.15, label: '0.15 – 0.5', color: '#2fb4ff', alpha: 0.55 },
  { min: 0.5, label: '0.5 – 1.0', color: '#2a5cff', alpha: 0.65 },
  { min: 1.0, label: '> 1.0 (hotspot)', color: '#ff2f8a', alpha: 0.7 },
];
const SEVERITY_COLOR: Record<string, string> = { critical: '#ff3b5c', warning: '#ff9f43', watch: '#f5c542', info: '#5fd0f0' };
/** Approximate locality centres for map callouts (static reference). */
export const PLACES: { name: string; lon: number; lat: number }[] = [
  { name: 'Anna Nagar', lon: 80.2101, lat: 13.085 }, { name: 'T. Nagar', lon: 80.2341, lat: 13.0418 }, { name: 'Adyar', lon: 80.2565, lat: 13.0012 },
  { name: 'Guindy', lon: 80.2206, lat: 13.0067 }, { name: 'Velachery', lon: 80.2209, lat: 12.9815 }, { name: 'Porur', lon: 80.1565, lat: 13.0382 },
  { name: 'Marina Beach', lon: 80.2824, lat: 13.05 }, { name: 'Tambaram', lon: 80.1275, lat: 12.9249 }, { name: 'Chromepet', lon: 80.1462, lat: 12.9516 },
  { name: 'Pallavaram', lon: 80.1504, lat: 12.9675 }, { name: 'Perungudi', lon: 80.2451, lat: 12.9654 }, { name: 'Sholinganallur', lon: 80.2279, lat: 12.901 },
  { name: 'Ambattur', lon: 80.1548, lat: 13.1143 }, { name: 'Avadi', lon: 80.0970, lat: 13.1147 }, { name: 'Madhavaram', lon: 80.2311, lat: 13.1488 },
  { name: 'Tiruvottiyur', lon: 80.3014, lat: 13.1643 }, { name: 'Egmore', lon: 80.2615, lat: 13.0732 }, { name: 'Mylapore', lon: 80.2676, lat: 13.0368 },
  { name: 'Kodambakkam', lon: 80.2245, lat: 13.0524 }, { name: 'Saidapet', lon: 80.2231, lat: 13.0213 },
];
/** Cinematic oblique home view framing the whole study boundary (looking north over the city). */
export const HOME_VIEW = { lon: 80.215, lat: 12.71, height: 30000, heading: 8, pitch: -38 };

const GOOGLE_KEY = (import.meta.env.VITE_GOOGLE_MAPS_API_KEY as string | undefined)?.trim() || '';
const ION_TOKEN = (import.meta.env.VITE_CESIUM_ION_TOKEN as string | undefined)?.trim() || '';
if (ION_TOKEN) Cesium.Ion.defaultAccessToken = ION_TOKEN;
const ION_ASSETS = { googlePhotorealistic: 2275207, worldTerrain: 1, osmBuildings: 96188, satellite: 3830182, satelliteLabels: 3830183, roadmap: 3830184 } as const;
/** Camera height (m) below which the Google photorealistic mesh replaces the citywide OSM buildings. */
const GOOGLE_NEAR_M = 3200;
export const googleTilesConfigured = () => ION_TOKEN.length > 0 || GOOGLE_KEY.length > 0;
export const ionConfigured = () => ION_TOKEN.length > 0;
export const imagerySourceLabel = () => (ION_TOKEN ? 'Google Maps 2D (Cesium ion)' : 'Esri World Imagery / CARTO');

function depthAtUtm(frame: DepthFrame | null, e: number, n: number): number | null {
  if (!frame) return null;
  const c = Math.floor((e - frame.grid.origin_x_m) / frame.grid.cell_size_m);
  const r = Math.floor((frame.grid.origin_y_m - n) / frame.grid.cell_size_m);
  if (r < 0 || c < 0 || r >= frame.rows || c >= frame.cols) return null;
  return frame.values[r][c];
}
function iconCanvas(color: string, shape: 'triangle' | 'house' | 'pin'): HTMLCanvasElement {
  const cv = document.createElement('canvas');
  cv.width = 36; cv.height = 36;
  const g = cv.getContext('2d')!;
  g.shadowColor = color; g.shadowBlur = 8; g.fillStyle = color; g.strokeStyle = '#06121b'; g.lineWidth = 2;
  g.beginPath();
  if (shape === 'triangle') { g.moveTo(18, 4); g.lineTo(33, 31); g.lineTo(3, 31); g.closePath(); }
  else if (shape === 'house') { g.moveTo(18, 4); g.lineTo(32, 16); g.lineTo(28, 16); g.lineTo(28, 31); g.lineTo(8, 31); g.lineTo(8, 16); g.lineTo(4, 16); g.closePath(); }
  else { g.arc(18, 14, 10, 0, Math.PI * 2); g.moveTo(10, 20); g.lineTo(18, 34); g.lineTo(26, 20); }
  g.fill(); g.stroke();
  if (shape === 'triangle') { g.shadowBlur = 0; g.fillStyle = '#06121b'; g.fillRect(16.5, 13, 3, 10); g.fillRect(16.5, 25, 3, 3); }
  return cv;
}
function calloutCanvas(text: string): HTMLCanvasElement {
  const cv = document.createElement('canvas');
  const g0 = cv.getContext('2d')!;
  g0.font = '600 26px Inter, Segoe UI, sans-serif';
  const w = Math.ceil(g0.measureText(text).width) + 34;
  cv.width = w; cv.height = 50;
  const g = cv.getContext('2d')!;
  g.font = '600 26px Inter, Segoe UI, sans-serif';
  g.fillStyle = 'rgba(8,22,36,0.9)'; g.strokeStyle = 'rgba(255,255,255,0.92)'; g.lineWidth = 2.5;
  const r = 10;
  g.beginPath(); g.moveTo(r, 2); g.lineTo(w - r, 2); g.quadraticCurveTo(w - 2, 2, w - 2, r); g.lineTo(w - 2, 48 - r); g.quadraticCurveTo(w - 2, 48, w - r, 48); g.lineTo(r, 48); g.quadraticCurveTo(2, 48, 2, 48 - r); g.lineTo(2, r); g.quadraticCurveTo(2, 2, r, 2); g.closePath();
  g.fill(); g.stroke();
  g.fillStyle = '#ffffff'; g.textBaseline = 'middle'; g.fillText(text, 17, 26);
  return cv;
}
/** Study-area camera limits (pre-2022 CMA bbox with a small margin). */
const BOUNDS = { west: 79.99, south: 12.84, east: 80.36, north: 13.30 };
const MAX_ZOOM_DISTANCE_M = 80000;
/** One Cesium viewer (one WebGL context) shared by every tab; it is re-parented into the visible map host. */
let SHARED: { v: Cesium.Viewer; el: HTMLDivElement; dusk: Cesium.PostProcessStage; google: Cesium.Cesium3DTileset | null; osm: Cesium.Cesium3DTileset | null } | null = null;
const glow = (color: string, power = 0.22) => Cesium.Material.fromType('PolylineGlow', { color: Cesium.Color.fromCssColorString(color), glowPower: power, taperPower: 1 });

function setupScene(v: Cesium.Viewer): Cesium.PostProcessStage {
  const scene = v.scene;
  scene.globe.baseColor = Cesium.Color.fromCssColorString('#07131d');
  scene.globe.depthTestAgainstTerrain = true;
  scene.backgroundColor = Cesium.Color.fromCssColorString('#020711');
  if (scene.skyAtmosphere) scene.skyAtmosphere.show = false;
  if (scene.skyBox) scene.skyBox.show = false;
  if (scene.sun) scene.sun.show = false;
  if (scene.moon) scene.moon.show = false;
  const ssc = scene.screenSpaceCameraController;
  ssc.maximumZoomDistance = MAX_ZOOM_DISTANCE_M;
  ssc.minimumZoomDistance = 60;
  scene.fog.enabled = true;
  scene.fog.density = 2.6e-4;
  scene.globe.showGroundAtmosphere = false;
  scene.globe.enableLighting = true;
  v.clock.currentTime = Cesium.JulianDate.fromIso8601('2026-11-07T13:00:00Z'); // 18:30 IST dusk
  v.clock.shouldAnimate = false;
  const bloom = scene.postProcessStages.bloom;
  bloom.enabled = true;
  bloom.uniforms.glowOnly = false;
  bloom.uniforms.contrast = 119;
  bloom.uniforms.brightness = -0.32;
  bloom.uniforms.delta = 1.0;
  bloom.uniforms.sigma = 3.2;
  bloom.uniforms.stepSize = 3.5;
  const dusk = scene.postProcessStages.add(Cesium.PostProcessStageLibrary.createBrightnessStage()) as Cesium.PostProcessStage;
  dusk.uniforms.brightness = 0.78;
  v.camera.setView({ destination: Cesium.Cartesian3.fromDegrees(HOME_VIEW.lon, HOME_VIEW.lat, HOME_VIEW.height), orientation: { heading: Cesium.Math.toRadians(HOME_VIEW.heading), pitch: Cesium.Math.toRadians(HOME_VIEW.pitch), roll: 0 } });
  return dusk;
}

const CLASS_RGBA: Record<DepthClass, [number, number, number, number]> = {
  dry: [0, 0, 0, 0], unknown: [0, 0, 0, 0], lt_0_15: [95, 208, 240, 255], '0_15_to_0_5': [47, 124, 255, 255], '0_5_to_1_0': [255, 159, 67, 255], gt_1_0: [255, 59, 92, 255],
};
/** Depth-class texture (row 0 = north) for colouring citywide buildings in a CustomShader. */
function depthClassUniform(frame: DepthFrame | null) {
  const cols = frame?.cols ?? 1;
  const rows = frame?.rows ?? 1;
  const data = new Uint8Array(cols * rows * 4);
  if (frame) for (let r = 0; r < rows; r += 1) for (let c = 0; c < cols; c += 1) data.set(CLASS_RGBA[depthClass(frame.values[r][c])], (r * cols + c) * 4);
  return new Cesium.TextureUniform({ typedArray: data, width: cols, height: rows, minificationFilter: Cesium.TextureMinificationFilter.NEAREST, magnificationFilter: Cesium.TextureMagnificationFilter.NEAREST });
}
function buildingShader(frame: DepthFrame | null) {
  const g = frame?.grid;
  const [lon, lat] = g ? utmToLonLat(g.origin_x_m, g.origin_y_m) : [80, 13];
  const enuInv = Cesium.Matrix4.inverse(Cesium.Transforms.eastNorthUpToFixedFrame(Cesium.Cartesian3.fromDegrees(lon, lat)), new Cesium.Matrix4());
  return new Cesium.CustomShader({
    uniforms: {
      u_depth: { type: Cesium.UniformType.SAMPLER_2D, value: depthClassUniform(frame) },
      u_enuInv: { type: Cesium.UniformType.MAT4, value: enuInv },
      u_size: { type: Cesium.UniformType.VEC2, value: new Cesium.Cartesian2(g ? g.cols * g.cell_size_m : 1, g ? g.rows * g.cell_size_m : 1) },
    },
    lightingModel: Cesium.LightingModel.UNLIT,
    fragmentShaderText: `
      void fragmentMain(FragmentInput fsInput, inout czm_modelMaterial material) {
        vec4 local = u_enuInv * vec4(fsInput.attributes.positionWC, 1.0);
        vec2 uv = vec2(local.x / u_size.x, -local.y / u_size.y);
        vec3 base = vec3(0.16, 0.22, 0.30) + 0.10 * clamp(fsInput.attributes.positionMC.z / 40.0, 0.0, 1.0);
        vec3 n = normalize(fsInput.attributes.normalEC);
        float shade = 0.55 + 0.45 * abs(n.z);
        material.diffuse = base * shade;
        if (uv.x >= 0.0 && uv.x <= 1.0 && uv.y >= 0.0 && uv.y <= 1.0) {
          vec4 c = texture(u_depth, uv);
          if (c.a > 0.5) material.diffuse = mix(material.diffuse, c.rgb * shade * 1.15, 0.85);
        }
        material.alpha = 1.0;
      }`,
  });
}

/** Upsample a depth frame into an RGBA canvas over its WGS84 bbox; bilinear between valid cells, dry/NoData transparent. */
export function depthFieldCanvas(frame: DepthFrame): { canvas: HTMLCanvasElement; bbox: [number, number, number, number] } | null {
  const g = frame.grid;
  const [w0, s0] = utmToLonLat(g.origin_x_m, g.origin_y_m - frame.rows * g.cell_size_m);
  const [e0, n0] = utmToLonLat(g.origin_x_m + frame.cols * g.cell_size_m, g.origin_y_m);
  const [w1] = utmToLonLat(g.origin_x_m, g.origin_y_m);
  const [e1] = utmToLonLat(g.origin_x_m + frame.cols * g.cell_size_m, g.origin_y_m - frame.rows * g.cell_size_m);
  const bbox: [number, number, number, number] = [Math.min(w0, w1), s0, Math.max(e0, e1), n0];
  const W = Math.min(1400, frame.cols * 12);
  const H = Math.round(W * ((bbox[3] - bbox[1]) / (bbox[2] - bbox[0])));
  const cv = document.createElement('canvas');
  cv.width = W; cv.height = H;
  const ctx = cv.getContext('2d');
  if (!ctx) return null;
  const img = ctx.createImageData(W, H);
  const stops = [
    [0.03, [143, 243, 255, 0]], [0.08, [143, 243, 255, 120]], [0.15, [70, 200, 255, 150]], [0.3, [47, 140, 255, 175]],
    [0.5, [42, 92, 255, 195]], [1.0, [120, 60, 255, 210]], [1.5, [255, 47, 138, 225]],
  ] as [number, number[]][];
  const colour = (d: number) => {
    if (d <= stops[0][0]) return null;
    for (let i = 1; i < stops.length; i += 1) if (d <= stops[i][0]) {
      const [d0, c0] = stops[i - 1]; const [d1, c1] = stops[i]; const t = (d - d0) / (d1 - d0);
      return c0.map((c, k) => c + (c1[k] - c) * t);
    }
    return stops[stops.length - 1][1];
  };
  const val = (r: number, c: number) => (r < 0 || c < 0 || r >= frame.rows || c >= frame.cols ? null : frame.values[r][c]);
  for (let y = 0; y < H; y += 1) {
    const lat = bbox[3] - ((y + 0.5) / H) * (bbox[3] - bbox[1]);
    for (let x = 0; x < W; x += 1) {
      const lon = bbox[0] + ((x + 0.5) / W) * (bbox[2] - bbox[0]);
      const [e, n] = lonLatToUtm(lon, lat);
      const fc = (e - g.origin_x_m) / g.cell_size_m - 0.5;
      const fr = (g.origin_y_m - n) / g.cell_size_m - 0.5;
      const c0 = Math.floor(fc); const r0 = Math.floor(fr); const dx = fc - c0; const dy = fr - r0;
      let sum = 0; let wsum = 0;
      for (const [rr, cc, ww] of [[r0, c0, (1 - dx) * (1 - dy)], [r0, c0 + 1, dx * (1 - dy)], [r0 + 1, c0, (1 - dx) * dy], [r0 + 1, c0 + 1, dx * dy]] as [number, number, number][]) {
        const vv = val(rr, cc);
        if (vv !== null && ww > 0) { sum += vv * ww; wsum += ww; }
      }
      if (wsum < 0.35) continue;
      const rgba = colour(sum / wsum);
      if (!rgba) continue;
      const i = (y * W + x) * 4;
      img.data[i] = rgba[0]; img.data[i + 1] = rgba[1]; img.data[i + 2] = rgba[2]; img.data[i + 3] = rgba[3];
    }
  }
  ctx.putImageData(img, 0, 0);
  return { canvas: cv, bbox };
}

export function Twin3D({ mode, layers, terrain, frame, focus, roads, wards, shelters, incidents, route, flyTo, command, onCamera, onPick, onMapClick, className = '' }: {
  mode: ViewMode;
  layers: TwinLayers;
  terrain: TerrainGrid | null;
  frame: DepthFrame | null;
  focus: FocusFile | null;
  roads?: RoadFeatureCollection | null;
  wards?: StaticFeatureCollection | null;
  shelters?: Shelter[] | null;
  incidents?: Incident[] | null;
  route?: RouteOption[] | null;
  flyTo?: { lon: number; lat: number; range?: number; key: string } | null;
  command?: TwinCommand | null;
  onCamera?: (c: CameraInfo) => void;
  onPick?: (info: PickInfo | null) => void;
  onMapClick?: (p: LonLat) => void;
  className?: string;
}) {
  const host = useRef<HTMLDivElement>(null);
  const viewer = useRef<Cesium.Viewer | null>(null);
  const prims = useRef<Record<string, Cesium.Primitive | Cesium.GroundPolylinePrimitive | Cesium.PrimitiveCollection | Cesium.BillboardCollection | Cesium.Cesium3DTileset | null>>({});
  const buildingIds = useRef<{ e: number; n: number }[]>([]);
  const pickRef = useRef(onPick);
  const clickRef = useRef(onMapClick);
  const camRef = useRef(onCamera);
  const frameRef = useRef(frame);
  pickRef.current = onPick;
  clickRef.current = onMapClick;
  camRef.current = onCamera;
  frameRef.current = frame;
  const [error, setError] = useState<string | null>(null);
  const [googleState, setGoogleState] = useState<'off' | 'loading' | 'on' | 'failed'>('off');
  const [datum, setDatum] = useState(GEOID_N_M);
  const datumRef = useRef(datum);
  datumRef.current = datum;
  const [rivers, setRivers] = useState<StaticFeatureCollection | null>(null);
  const [boundary, setBoundary] = useState<StaticFeatureCollection | null>(null);
  const [near, setNear] = useState(false);
  const [osmReady, setOsmReady] = useState(false);
  const nearRef = useRef(near);
  const boundaryRef = useRef<StaticFeatureCollection | null>(null);
  boundaryRef.current = boundary;
  const makeClip = (b: StaticFeatureCollection) => new Cesium.ClippingPolygonCollection({
    inverse: true,
    polygons: b.features.map((f) => new Cesium.ClippingPolygon({ positions: Cesium.Cartesian3.fromDegreesArray(((f.geometry.coordinates as number[][][])[0]).slice(0, -1).flat()) })),
  });
  const googleOn = googleState === 'on' && layers.google && mode !== '2d';

  const ground = (lon: number, lat: number) => terrainHeight(terrain, lon, lat) + datum;

  useEffect(() => { loadWaterways().then(setRivers); loadBoundary().then(setBoundary); }, []);

  /* viewer lifecycle and scene mood */
  useEffect(() => {
    const hostEl = host.current;
    if (!hostEl) return;
    if (!SHARED || SHARED.v.isDestroyed()) {
      const el = document.createElement('div');
      el.className = 'tg-twin__shared';
      hostEl.appendChild(el);
      try {
        const created = new Cesium.Viewer(el, {
          baseLayer: false, animation: false, timeline: false, baseLayerPicker: false, geocoder: false, homeButton: false, sceneModePicker: false,
          navigationHelpButton: false, fullscreenButton: false, infoBox: false, selectionIndicator: false, scene3DOnly: false, requestRenderMode: true, maximumRenderTimeChange: Infinity,
          showRenderLoopErrors: false,
          contextOptions: { webgl: { failIfMajorPerformanceCaveat: false, powerPreference: 'high-performance' } },
        });
        created.scene.renderError.addEventListener(() => { if (!created.isDestroyed()) created.useDefaultRenderLoop = (created.canvas.clientWidth > 0); });
        SHARED = { v: created, el, dusk: setupScene(created), google: null, osm: null };
      } catch (e) {
        el.remove();
        setError(e instanceof Error ? e.message : 'WebGL is unavailable in this browser.');
        return;
      }
    } else hostEl.appendChild(SHARED.el);
    const v = SHARED.v;
    viewer.current = v;
    v.useDefaultRenderLoop = true;
    prims.current = { google: SHARED.google, osm: SHARED.osm };
    (prims.current as Record<string, unknown>).dusk = SHARED.dusk;
    if (SHARED.google) { setGoogleState(SHARED.google.show ? 'on' : 'off'); }
    if (v.canvas.clientWidth > 0) v.resize();
    if (import.meta.env.DEV) (window as unknown as { __tgViewer?: Cesium.Viewer }).__tgViewer = v;
    const scene = v.scene;
    v.camera.percentageChanged = 0.02;
    const report = () => {
      const c = v.scene.canvas;
      const a = v.camera.pickEllipsoid(new Cesium.Cartesian2(c.clientWidth / 2 - 50, c.clientHeight - 40));
      const b = v.camera.pickEllipsoid(new Cesium.Cartesian2(c.clientWidth / 2 + 50, c.clientHeight - 40));
      const height = v.camera.positionCartographic.height - datumRef.current;
      camRef.current?.({ headingDeg: Cesium.Math.toDegrees(v.camera.heading), metersPer100px: a && b ? Cesium.Cartesian3.distance(a, b) : null, heightM: height });
      const isNear = v.scene.mode !== Cesium.SceneMode.SCENE2D && height < GOOGLE_NEAR_M;
      if (isNear !== nearRef.current) { nearRef.current = isNear; setNear(isNear); }
    };
    const removeCam = v.camera.changed.addEventListener(report);
    /* keep the view centred inside the study area */
    const clamp = () => {
      const c = scene.canvas;
      const mid = scene.pickPosition(new Cesium.Cartesian2(c.clientWidth / 2, c.clientHeight / 2)) ?? v.camera.pickEllipsoid(new Cesium.Cartesian2(c.clientWidth / 2, c.clientHeight / 2));
      if (!mid) return;
      const ll = Cesium.Cartographic.fromCartesian(mid);
      const lon = Cesium.Math.toDegrees(ll.longitude);
      const lat = Cesium.Math.toDegrees(ll.latitude);
      const cl = Math.min(BOUNDS.east, Math.max(BOUNDS.west, lon));
      const ca = Math.min(BOUNDS.north, Math.max(BOUNDS.south, lat));
      if (Math.abs(cl - lon) < 1e-6 && Math.abs(ca - lat) < 1e-6) return;
      const range = Cesium.Cartesian3.distance(v.camera.position, mid);
      if (scene.mode === Cesium.SceneMode.SCENE2D) v.camera.flyTo({ destination: Cesium.Cartesian3.fromDegrees(cl, ca, Math.min(range, MAX_ZOOM_DISTANCE_M)), duration: 0.6 });
      else v.camera.flyToBoundingSphere(new Cesium.BoundingSphere(Cesium.Cartesian3.fromDegrees(cl, ca, ll.height), 1), { offset: new Cesium.HeadingPitchRange(v.camera.heading, v.camera.pitch, Math.min(range, MAX_ZOOM_DISTANCE_M)), duration: 0.6 });
    };
    const removeMove = v.camera.moveEnd.addEventListener(clamp);
    setTimeout(report, 500);
    const handler = new Cesium.ScreenSpaceEventHandler(scene.canvas);
    handler.setInputAction((ev: { position: Cesium.Cartesian2 }) => {
      const picked = scene.pick(ev.position) as { id?: unknown } | undefined;
      const cart = scene.pickPosition(ev.position) ?? v.camera.pickEllipsoid(ev.position);
      const ll = cart ? Cesium.Cartographic.fromCartesian(cart) : null;
      const location = ll ? { lon: +Cesium.Math.toDegrees(ll.longitude).toFixed(5), lat: +Cesium.Math.toDegrees(ll.latitude).toFixed(5) } : null;
      if (location) clickRef.current?.(location);
      const info = picked && typeof picked.id === 'object' && picked.id && 'kind' in (picked.id as object) ? (picked.id as PickInfo) : null;
      if (info) pickRef.current?.(info);
      else if (location) {
        const [e, n] = lonLatToUtm(location.lon, location.lat);
        const d = depthAtUtm(frameRef.current, e, n);
        pickRef.current?.({ kind: 'ground', title: 'Model cell', location, lines: [['Simulated depth', d === null ? 'Outside model (unknown)' : `${d.toFixed(2)} m`], ['UTM 44N', `${Math.round(e)} E, ${Math.round(n)} N`]] });
      }
    }, Cesium.ScreenSpaceEventType.LEFT_CLICK);
    return () => {
      removeCam(); removeMove(); handler.destroy();
      for (const [k, p] of Object.entries(prims.current)) {
        if (k === 'google' || k === 'osm' || k === 'dusk' || !p) continue;
        if (v.scene.primitives.contains(p as Cesium.Primitive)) v.scene.primitives.remove(p as Cesium.Primitive);
      }
      v.entities.removeAll();
      v.useDefaultRenderLoop = false;
      if (SHARED?.el.parentElement === hostEl) hostEl.removeChild(SHARED.el);
      viewer.current = null;
      prims.current = {};
      setGoogleState('off');
    };
  }, []);

  /* dusk tint only in the dark 3D mode */
  useEffect(() => {
    const v = viewer.current;
    const dusk = (prims.current as Record<string, unknown>).dusk as Cesium.PostProcessStage | undefined;
    if (!v || !dusk) return;
    dusk.uniforms.brightness = mode === '3d' ? 0.78 : 1.0;
    v.scene.postProcessStages.bloom.enabled = mode !== 'satellite';
    v.scene.requestRender();
  }, [mode]);

  /* terrain: Cesium World Terrain via ion when configured, otherwise (or on failure) our GLO-30 DEM */
  useEffect(() => {
    const v = viewer.current;
    if (!v) return;
    let cancelled = false;
    const useDem = () => {
      if (cancelled || viewer.current !== v) return;
      if (!terrain) { v.terrainProvider = new Cesium.EllipsoidTerrainProvider(); return; }
      const scheme = new Cesium.GeographicTilingScheme();
      const W = 32;
      v.terrainProvider = new Cesium.CustomHeightmapTerrainProvider({
        width: W, height: W, tilingScheme: scheme, credit: 'Terrain: Copernicus GLO-30 (project cleaned DEM)',
        callback: (x, y, level) => {
          const rect = scheme.tileXYToRectangle(x, y, level);
          const out = new Float32Array(W * W);
          const west = Cesium.Math.toDegrees(rect.west); const east = Cesium.Math.toDegrees(rect.east);
          const north = Cesium.Math.toDegrees(rect.north); const south = Cesium.Math.toDegrees(rect.south);
          for (let j = 0; j < W; j += 1) for (let i = 0; i < W; i += 1) out[j * W + i] = terrainHeight(terrain, west + ((east - west) * i) / (W - 1), north - ((north - south) * j) / (W - 1)) + GEOID_N_M;
          return out;
        },
      });
      setDatum(GEOID_N_M);
      v.scene.requestRender();
    };
    if (ION_TOKEN && v.terrainProvider instanceof Cesium.CesiumTerrainProvider) return () => { cancelled = true; };
    if (ION_TOKEN) Cesium.CesiumTerrainProvider.fromIonAssetId(ION_ASSETS.worldTerrain).then((tp) => { if (!cancelled && viewer.current === v) { v.terrainProvider = tp; v.scene.requestRender(); } }).catch(useDem);
    else useDem();
    return () => { cancelled = true; };
  }, [terrain]);

  /* datum calibration: ellipsoid height of the loaded surface (tiles or globe) minus our DEM, low percentile = street level */
  useEffect(() => {
    const v = viewer.current;
    if (!v || !terrain || !flyTo) return;
    let done = false;
    const calibrate = () => {
      if (done || viewer.current !== v) return;
      const diffs: number[] = [];
      for (let i = -4; i <= 4; i += 1) for (let j = -4; j <= 4; j += 1) {
        const lon = flyTo.lon + i * 0.004;
        const lat = flyTo.lat + j * 0.004;
        const carto = Cesium.Cartographic.fromDegrees(lon, lat);
        const useTiles = googleOn && nearRef.current;
        const h = useTiles ? v.scene.sampleHeight(carto) : v.scene.globe.getHeight(carto);
        if (h !== undefined && Number.isFinite(h)) diffs.push(h - terrainHeight(terrain, lon, lat));
      }
      if (diffs.length < 20) return;
      diffs.sort((a, b) => a - b);
      const off = diffs[Math.floor(diffs.length * (googleOn && nearRef.current ? 0.15 : 0.5))];
      if (Math.abs(off - GEOID_N_M) < 40) { done = true; setDatum(+off.toFixed(1)); }
    };
    const ts = prims.current.google as Cesium.Cesium3DTileset | null | undefined;
    const removeA = googleOn && ts ? ts.allTilesLoaded.addEventListener(calibrate) : undefined;
    const removeB = v.scene.globe.tileLoadProgressEvent.addEventListener((n: number) => { if (n === 0 && !(googleOn && nearRef.current)) calibrate(); });
    const t = window.setTimeout(calibrate, 6000);
    return () => { removeA?.(); removeB(); window.clearTimeout(t); };
  }, [terrain, googleOn, near, flyTo?.key]);

  /* base imagery per view mode */
  useEffect(() => {
    const v = viewer.current;
    if (!v) return;
    let cancelled = false;
    v.imageryLayers.removeAll();
    const scene = v.scene;
    const tint = (layer: Cesium.ImageryLayer, dark: boolean) => { layer.brightness = dark ? 0.5 : 1.0; layer.saturation = dark ? 0.6 : 1.0; layer.contrast = dark ? 1.15 : 1.0; layer.hue = dark ? 0.04 : 0; };
    const fallback = () => {
      if (cancelled) return;
      if (mode === '2d') { v.imageryLayers.addImageryProvider(new Cesium.UrlTemplateImageryProvider({ url: 'https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}.png', subdomains: 'abcd', maximumLevel: 19, credit: '© OpenStreetMap contributors © CARTO' })); scene.requestRender(); return; }
      Cesium.ArcGisMapServerImageryProvider.fromUrl('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer').then((p) => { if (!cancelled) { tint(v.imageryLayers.addImageryProvider(p), mode === '3d'); scene.requestRender(); } }).catch(() => { /* offline: dark globe colour remains */ });
    };
    if (mode === '2d') { if (scene.mode !== Cesium.SceneMode.SCENE2D) scene.morphTo2D(0.6); }
    else if (scene.mode !== Cesium.SceneMode.SCENE3D) scene.morphTo3D(0.6);
    if (ION_TOKEN) {
      const asset = mode === '2d' ? ION_ASSETS.roadmap : mode === 'satellite' ? ION_ASSETS.satelliteLabels : ION_ASSETS.satellite;
      Cesium.IonImageryProvider.fromAssetId(asset).then((p) => {
        if (cancelled) return;
        const layer = v.imageryLayers.addImageryProvider(p);
        if (mode === '3d') tint(layer, true);
        else if (mode === '2d') { layer.brightness = 0.62; layer.saturation = 0.55; layer.hue = 0.55; }
        scene.requestRender();
      }).catch(fallback);
    } else fallback();
    scene.requestRender();
    return () => { cancelled = true; };
  }, [mode]);

  /* Google Photorealistic 3D Tiles */
  useEffect(() => {
    const v = viewer.current;
    if (!v) return;
    const want = layers.google && mode !== '2d';
    if (!GOOGLE_KEY && !ION_TOKEN) return;
    const existing = prims.current.google as Cesium.Cesium3DTileset | null | undefined;
    if (!want) { if (existing) existing.show = false; v.scene.globe.show = true; setGoogleState('off'); v.scene.requestRender(); return; }
    if (existing) { existing.show = true; v.scene.globe.show = false; setGoogleState('on'); v.scene.requestRender(); return; }
    setGoogleState('loading');
    const load = ION_TOKEN ? Cesium.Cesium3DTileset.fromIonAssetId(ION_ASSETS.googlePhotorealistic, { showCreditsOnScreen: true }) : Cesium.createGooglePhotorealistic3DTileset({ key: GOOGLE_KEY }, { showCreditsOnScreen: true });
    load.then((ts) => {
      if (viewer.current !== v || v.isDestroyed() || (SHARED?.google && SHARED.google !== ts)) { ts.destroy(); return; }
      if (boundaryRef.current) ts.clippingPolygons = makeClip(boundaryRef.current);
      v.scene.primitives.add(ts);
      prims.current.google = ts;
      if (SHARED) SHARED.google = ts;
      v.scene.globe.show = false;
      setGoogleState('on');
      v.scene.requestRender();
    }).catch(() => { if (viewer.current === v && !v.isDestroyed()) setGoogleState('failed'); });
  }, [layers.google, mode]);

  /* citywide Cesium OSM Buildings (ion 96188), clipped to the CMA and coloured by depth class via a CustomShader */
  useEffect(() => {
    const v = viewer.current;
    if (!v || !ION_TOKEN || !boundary) return;
    let cancelled = false;
    const existing = prims.current.osm as Cesium.Cesium3DTileset | null | undefined;
    if (existing && !existing.isDestroyed()) { existing.customShader = buildingShader(frame); setOsmReady(true); v.scene.requestRender(); return; }
    Cesium.Cesium3DTileset.fromIonAssetId(ION_ASSETS.osmBuildings, { showCreditsOnScreen: true }).then((ts) => {
      if (cancelled || viewer.current !== v || v.isDestroyed()) { ts.destroy(); return; }
      ts.clippingPolygons = makeClip(boundary);
      ts.customShader = buildingShader(frame);
      v.scene.primitives.add(ts);
      prims.current.osm = ts;
      if (SHARED) SHARED.osm = ts;
      setOsmReady(true);
      v.scene.requestRender();
    }).catch(() => setOsmReady(false));
    return () => { cancelled = true; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [boundary, frame]);

  /* OSM focus-area footprints, extruded and coloured by depth class: fallback when ion buildings are unavailable */
  useEffect(() => {
    const v = viewer.current;
    if (!v) return;
    const old = prims.current.buildings;
    if (old) v.scene.primitives.remove(old);
    prims.current.buildings = null;
    buildingIds.current = [];
    if (!focus) return;
    const instances: Cesium.GeometryInstance[] = [];
    for (const [osmid, levels, e, n, ring] of focus.buildings) {
      const [lon, lat] = utmToLonLat(e, n);
      const h = (levels ?? estimatedLevels(ring)) * LEVEL_HEIGHT_M;
      const base = ground(lon, lat);
      const cls = depthClass(depthAtUtm(frame, e, n));
      instances.push(new Cesium.GeometryInstance({
        id: { kind: 'building', title: `Building way/${osmid}`, location: { lon: +lon.toFixed(5), lat: +lat.toFixed(5) }, lines: [['Height', `${h} m (${levels ? 'OSM levels' : 'estimated'})`], ['Depth class', DEPTH_CLASS_STYLE[cls].label]] } as PickInfo,
        geometry: new Cesium.PolygonGeometry({ polygonHierarchy: new Cesium.PolygonHierarchy(Cesium.Cartesian3.fromDegreesArray(ring)), height: base - 1, extrudedHeight: base + h, vertexFormat: Cesium.PerInstanceColorAppearance.VERTEX_FORMAT }),
        attributes: { color: Cesium.ColorGeometryInstanceAttribute.fromColor(Cesium.Color.fromCssColorString(DEPTH_CLASS_STYLE[cls].color).withAlpha(0.95)) },
      }));
      buildingIds.current.push({ e, n });
    }
    const p = new Cesium.Primitive({ geometryInstances: instances, appearance: new Cesium.PerInstanceColorAppearance({ translucent: false, closed: true }), releaseGeometryInstances: false, asynchronous: true });
    p.show = layers.buildings && !ION_TOKEN && !googleOn;
    v.scene.primitives.add(p);
    prims.current.buildings = p;
    v.scene.requestRender();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [focus, terrain, datum]);

  /* recolour buildings for the current frame */
  useEffect(() => {
    const v = viewer.current;
    const p = prims.current.buildings as Cesium.Primitive | null | undefined;
    if (!v || !p) return;
    const apply = () => {
      const instances = p.geometryInstances as Cesium.GeometryInstance[] | undefined;
      if (!p.ready || !instances) return false;
      instances.forEach((inst, i) => {
        const b = buildingIds.current[i];
        const cls = depthClass(depthAtUtm(frame, b.e, b.n));
        const attr = p.getGeometryInstanceAttributes(inst.id);
        if (attr) attr.color = Cesium.ColorGeometryInstanceAttribute.toValue(Cesium.Color.fromCssColorString(DEPTH_CLASS_STYLE[cls].color).withAlpha(0.95));
        (inst.id as PickInfo).lines[1] = ['Depth class', DEPTH_CLASS_STYLE[cls].label];
      });
      v.scene.requestRender();
      return true;
    };
    if (!apply()) { const remove = v.scene.postRender.addEventListener(() => { if (apply()) remove(); }); return remove; }
  }, [frame, focus, datum]);

  /* simulated water: a smooth depth field rendered to a texture (dry = transparent) and draped on terrain / 3D tiles */
  useEffect(() => {
    const v = viewer.current;
    if (!v) return;
    const old = prims.current.water;
    if (old) v.scene.primitives.remove(old);
    prims.current.water = null;
    if (!frame) return;
    const field = depthFieldCanvas(frame);
    if (!field) return;
    const material = Cesium.Material.fromType('Image', { image: field.canvas, transparent: true });
    const p = new Cesium.GroundPrimitive({
      geometryInstances: new Cesium.GeometryInstance({ geometry: new Cesium.RectangleGeometry({ rectangle: Cesium.Rectangle.fromDegrees(...field.bbox), vertexFormat: Cesium.MaterialAppearance.MaterialSupport.TEXTURED.vertexFormat }), id: { kind: 'ground', title: 'Simulated flood depth', location: { lon: (field.bbox[0] + field.bbox[2]) / 2, lat: (field.bbox[1] + field.bbox[3]) / 2 }, lines: [['Source', 'saved run depth grid'], ['Rendering', 'bilinear between model cells']] } as PickInfo }),
      appearance: new Cesium.MaterialAppearance({ material, translucent: true, materialSupport: Cesium.MaterialAppearance.MaterialSupport.TEXTURED }),
      classificationType: Cesium.ClassificationType.BOTH,
      asynchronous: true,
    });
    p.show = layers.water;
    v.scene.primitives.add(p);
    prims.current.water = p;
    v.scene.requestRender();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [frame]);

  /* continuous rendering keeps the water animated (respecting reduced motion) */
  useEffect(() => {
    const v = viewer.current;
    if (!v) return;
    const reduce = window.matchMedia?.('(prefers-reduced-motion: reduce)').matches;
    v.scene.requestRenderMode = true;
    void reduce;
    v.scene.requestRender();
  }, [layers.water, frame, googleOn]);

  /* study boundary: clip globe and 3D tiles to the CMA, draw a glowing outline */
  useEffect(() => {
    const v = viewer.current;
    if (!v || !boundary?.features.length) return;
    v.scene.globe.clippingPolygons = makeClip(boundary);
    const ts = prims.current.google as Cesium.Cesium3DTileset | null | undefined;
    if (ts && !ts.isDestroyed()) ts.clippingPolygons = makeClip(boundary);
    const old = prims.current.boundary;
    if (old) v.scene.primitives.remove(old);
    const coll = new Cesium.PrimitiveCollection();
    const lines = boundary.features.map((f) => new Cesium.GeometryInstance({ geometry: new Cesium.PolylineGeometry({ positions: Cesium.Cartesian3.fromDegreesArrayHeights(((f.geometry.coordinates as number[][][])[0]).flatMap(([lon, lat]) => [lon, lat, ground(lon, lat) + 25])), width: 3, vertexFormat: Cesium.PolylineMaterialAppearance.VERTEX_FORMAT }) }));
    coll.add(new Cesium.Primitive({ geometryInstances: lines, appearance: new Cesium.PolylineMaterialAppearance({ material: glow('#22d3ff', 0.35) }), asynchronous: true }));
    v.scene.primitives.add(coll);
    prims.current.boundary = coll;
    v.scene.requestRender();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [boundary, googleState, datum]);

  /* rivers and canals (glowing, draped) */
  useEffect(() => {
    const v = viewer.current;
    if (!v || !rivers?.features.length) return;
    const old = prims.current.rivers;
    if (old) v.scene.primitives.remove(old);
    const instances = rivers.features.map((f) => new Cesium.GeometryInstance({
      id: { kind: 'river', title: String(f.properties.name ?? f.properties.waterway), location: { lon: (f.geometry.coordinates as number[][])[0][0], lat: (f.geometry.coordinates as number[][])[0][1] }, lines: [['Type', String(f.properties.waterway)], ['Source', 'OpenStreetMap']] } as PickInfo,
      geometry: new Cesium.GroundPolylineGeometry({ positions: Cesium.Cartesian3.fromDegreesArray((f.geometry.coordinates as number[][]).flat()), width: f.properties.waterway === 'river' ? 7 : 4 }),
    }));
    const p = new Cesium.GroundPolylinePrimitive({ geometryInstances: instances, appearance: new Cesium.PolylineMaterialAppearance({ material: glow('#36b9ff', 0.3) }), classificationType: Cesium.ClassificationType.BOTH, asynchronous: true });
    v.scene.primitives.add(p);
    prims.current.rivers = p;
    v.scene.requestRender();
  }, [rivers]);

  /* roads, three-state, glowing and draped */
  useEffect(() => {
    const v = viewer.current;
    if (!v) return;
    const old = prims.current.roads;
    if (old) v.scene.primitives.remove(old);
    prims.current.roads = null;
    if (!roads?.features.length) return;
    const coll = new Cesium.PrimitiveCollection();
    (Object.keys(EDGE_STYLE) as EdgeState[]).forEach((state) => {
      const feats = roads.features.filter((f) => f.properties.state === state && f.geometry.coordinates.length > 1);
      if (!feats.length) return;
      const instances = feats.map((f) => {
        const p = f.properties;
        const major = !!p.road_class && /motorway|trunk|primary|secondary/.test(p.road_class);
        return new Cesium.GeometryInstance({
          id: { kind: 'road', title: `Road ${p.edge_id} (${p.road_class ?? 'road'})`, location: { lon: f.geometry.coordinates[0][0], lat: f.geometry.coordinates[0][1] }, lines: [['State', EDGE_STYLE[p.state].label], ['Depth at midpoint', p.depth_m == null ? 'Unknown' : `${p.depth_m.toFixed(2)} m`], ...(p.unknown_reason ? [['Reason', p.unknown_reason.replace(/_/g, ' ')] as [string, string]] : [])] } as PickInfo,
          geometry: new Cesium.GroundPolylineGeometry({ positions: Cesium.Cartesian3.fromDegreesArray(f.geometry.coordinates.flat()), width: major ? 5 : 2.4 }),
          attributes: { distanceDisplayCondition: new Cesium.DistanceDisplayConditionGeometryInstanceAttribute(0, 9000) },
        });
      });
      coll.add(new Cesium.GroundPolylinePrimitive({ geometryInstances: instances, appearance: new Cesium.PolylineMaterialAppearance({ material: glow(EDGE_STYLE[state].color, state === 'ASSESSED_PASSABLE' ? 0.12 : 0.25) }), classificationType: Cesium.ClassificationType.BOTH, asynchronous: true }));
    });
    coll.show = layers.roads;
    v.scene.primitives.add(coll);
    prims.current.roads = coll;
    v.scene.requestRender();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [roads]);

  /* ward outlines (draped) */
  useEffect(() => {
    const v = viewer.current;
    if (!v) return;
    const old = prims.current.wards;
    if (old) v.scene.primitives.remove(old);
    prims.current.wards = null;
    if (!wards?.features.length) return;
    const instances: Cesium.GeometryInstance[] = [];
    for (const f of wards.features) {
      const polys = (f.geometry.type === 'Polygon' ? [f.geometry.coordinates] : (f.geometry.coordinates as number[][][][])) as number[][][][];
      for (const rings of polys) instances.push(new Cesium.GeometryInstance({
        id: { kind: 'ward', title: String(f.properties.ward_name), location: { lon: rings[0][0][0], lat: rings[0][0][1] }, lines: [['Zone', String(f.properties.zone ?? '—')], ['Source', 'GCC ward boundary']] } as PickInfo,
        geometry: new Cesium.GroundPolylineGeometry({ positions: Cesium.Cartesian3.fromDegreesArray(rings[0].flat()), width: 1.6 }),
      }));
    }
    const p = new Cesium.GroundPolylinePrimitive({ geometryInstances: instances, appearance: new Cesium.PolylineMaterialAppearance({ material: glow('#9feaff', 0.08) }), classificationType: Cesium.ClassificationType.BOTH, asynchronous: true });
    p.show = layers.wards;
    v.scene.primitives.add(p);
    prims.current.wards = p;
    v.scene.requestRender();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [wards]);

  /* place callouts with leader lines */
  useEffect(() => {
    const v = viewer.current;
    if (!v) return;
    const old = prims.current.places;
    if (old) v.scene.primitives.remove(old);
    const coll = new Cesium.PrimitiveCollection();
    const bb = new Cesium.BillboardCollection({ scene: v.scene });
    const lines: Cesium.GeometryInstance[] = [];
    for (const p of PLACES) {
      const g = ground(p.lon, p.lat);
      bb.add({ position: Cesium.Cartesian3.fromDegrees(p.lon, p.lat, g + 170), image: calloutCanvas(p.name), scale: 0.5, verticalOrigin: Cesium.VerticalOrigin.BOTTOM, scaleByDistance: new Cesium.NearFarScalar(1500, 1.0, 40000, 0.55), disableDepthTestDistance: Number.POSITIVE_INFINITY, distanceDisplayCondition: new Cesium.DistanceDisplayCondition(0, 60000) });
      lines.push(new Cesium.GeometryInstance({ geometry: new Cesium.PolylineGeometry({ positions: Cesium.Cartesian3.fromDegreesArrayHeights([p.lon, p.lat, g, p.lon, p.lat, g + 170]), width: 1.5, vertexFormat: Cesium.PolylineColorAppearance.VERTEX_FORMAT }), attributes: { color: Cesium.ColorGeometryInstanceAttribute.fromColor(Cesium.Color.WHITE.withAlpha(0.8)) } }));
    }
    coll.add(new Cesium.Primitive({ geometryInstances: lines, appearance: new Cesium.PolylineColorAppearance({ translucent: true }), asynchronous: true }));
    coll.add(bb);
    v.scene.primitives.add(coll);
    prims.current.places = coll;
    v.scene.requestRender();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [terrain, datum]);

  /* shelters (near the focus area, only when zoomed in) and generated incidents (warning+) */
  useEffect(() => {
    const v = viewer.current;
    if (!v) return;
    for (const key of ['shelters', 'incidents'] as const) { const old = prims.current[key]; if (old) v.scene.primitives.remove(old); prims.current[key] = null; }
    const centre = focus?.centre;
    const near = (p: LonLat, km: number) => !centre || Math.hypot((p.lon - centre.lon) * 108, (p.lat - centre.lat) * 111) < km;
    if (shelters?.length) {
      const b = new Cesium.BillboardCollection({ scene: v.scene });
      const ok = iconCanvas('#3ddc84', 'house');
      const bad = iconCanvas('#8a97a3', 'house');
      for (const s of shelters.filter((x) => near(x.location, 1.8) && x.reachable)) b.add({ position: Cesium.Cartesian3.fromDegrees(s.location.lon, s.location.lat, ground(s.location.lon, s.location.lat) + 22), image: s.reachable ? ok : bad, scale: 0.5, verticalOrigin: Cesium.VerticalOrigin.BOTTOM, disableDepthTestDistance: 3.0e3, distanceDisplayCondition: new Cesium.DistanceDisplayCondition(0, 7000),
        id: { kind: 'shelter', title: s.name, location: s.location, lines: [['Category', s.category], ['Capacity', `${s.capacity_people.toLocaleString('en-IN')} (${s.capacity_source})`], ['Site depth', s.site_max_depth_m == null ? 'Unknown' : `${s.site_max_depth_m.toFixed(2)} m`], ['Reachable', s.reachable ? 'Yes (site dry)' : 'No']] } as PickInfo });
      b.show = layers.shelters;
      v.scene.primitives.add(b);
      prims.current.shelters = b;
    }
    if (incidents?.length) {
      const b = new Cesium.BillboardCollection({ scene: v.scene });
      const icons: Record<string, HTMLCanvasElement> = {};
      for (const i of incidents.filter((x) => x.severity === 'critical' || (x.severity === 'warning' && near(x.location, 6)))) {
        icons[i.severity] ??= iconCanvas(SEVERITY_COLOR[i.severity], 'triangle');
        b.add({ position: Cesium.Cartesian3.fromDegrees(i.location.lon, i.location.lat, ground(i.location.lon, i.location.lat) + 60), image: icons[i.severity], scale: i.severity === 'critical' ? 0.62 : 0.5, verticalOrigin: Cesium.VerticalOrigin.BOTTOM, disableDepthTestDistance: 6.0e3, distanceDisplayCondition: new Cesium.DistanceDisplayCondition(0, 30000),
          id: { kind: 'incident', title: i.title ?? i.type, location: i.location, lines: [['Severity', i.severity], ['Type', i.type.replace(/_/g, ' ')], ['Generated', 'Yes, from simulation']] } as PickInfo });
      }
      b.show = layers.incidents;
      v.scene.primitives.add(b);
      prims.current.incidents = b;
    }
    v.scene.requestRender();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [shelters, incidents, focus, terrain, datum]);

  /* routes (draped glow) */
  useEffect(() => {
    const v = viewer.current;
    if (!v) return;
    v.entities.removeAll();
    (route ?? []).forEach((r, i) => {
      if (!r.geometry) return;
      const color = i === 0 ? (r.route_status === 'CONDITIONAL' ? '#f5c542' : '#3ddc84') : '#b36bff';
      v.entities.add({ polyline: { positions: Cesium.Cartesian3.fromDegreesArray(r.geometry.coordinates.flat()), width: i === 0 ? 12 : 8, clampToGround: true, classificationType: Cesium.ClassificationType.BOTH, material: new Cesium.PolylineGlowMaterialProperty({ glowPower: 0.3, color: Cesium.Color.fromCssColorString(color) }) } });
      if (i === 0) {
        const [lon0, lat0] = r.geometry.coordinates[0];
        const [lon1, lat1] = r.geometry.coordinates[r.geometry.coordinates.length - 1];
        v.entities.add({ position: Cesium.Cartesian3.fromDegrees(lon0, lat0, ground(lon0, lat0) + 25), billboard: { image: iconCanvas('#3ddc84', 'pin'), verticalOrigin: Cesium.VerticalOrigin.BOTTOM, disableDepthTestDistance: Number.POSITIVE_INFINITY } });
        v.entities.add({ position: Cesium.Cartesian3.fromDegrees(lon1, lat1, ground(lon1, lat1) + 25), billboard: { image: iconCanvas('#ff3b5c', 'pin'), verticalOrigin: Cesium.VerticalOrigin.BOTTOM, disableDepthTestDistance: Number.POSITIVE_INFINITY } });
      }
    });
    v.scene.requestRender();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [route, datum]);

  /* layer visibility */
  useEffect(() => {
    const v = viewer.current;
    if (!v) return;
    const set = (k: string, s: boolean) => { const p = prims.current[k]; if (p) p.show = s; };
    const showGoogle = googleOn && near;
    const ts = prims.current.google as Cesium.Cesium3DTileset | null | undefined;
    if (ts && !ts.isDestroyed()) ts.show = showGoogle;
    v.scene.globe.show = !showGoogle;
    set('water', layers.water);
    set('osm', layers.buildings && osmReady && !showGoogle);
    set('buildings', layers.buildings && !osmReady && !showGoogle);
    set('roads', layers.roads);
    set('wards', layers.wards);
    set('shelters', layers.shelters);
    set('incidents', layers.incidents);
    v.scene.requestRender();
  }, [layers, googleOn, near, osmReady]);

  /* camera fly-to and tool commands */
  const flyToTarget = (v: Cesium.Viewer, lon: number, lat: number, range: number) => {
    if (v.scene.mode === Cesium.SceneMode.SCENE2D) v.camera.flyTo({ destination: Cesium.Cartesian3.fromDegrees(lon, lat, range * 2.2), duration: 1.2 });
    else v.camera.flyToBoundingSphere(new Cesium.BoundingSphere(Cesium.Cartesian3.fromDegrees(lon, lat, ground(lon, lat)), 250), { offset: new Cesium.HeadingPitchRange(Cesium.Math.toRadians(28), Cesium.Math.toRadians(range > 10000 ? -45 : -28), range), duration: 1.6 });
  };
  useEffect(() => {
    const v = viewer.current;
    if (!v || !flyTo) return;
    flyToTarget(v, flyTo.lon, flyTo.lat, flyTo.range ?? 2800);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [flyTo?.key]);
  useEffect(() => {
    const v = viewer.current;
    if (!v || !command) return;
    const cam = v.camera;
    const h = cam.positionCartographic.height;
    if (command.type === 'zoomIn') cam.zoomIn(Math.max(150, h * 0.35));
    else if (command.type === 'zoomOut') cam.zoomOut(Math.max(150, h * 0.5));
    else if (command.type === 'home' && flyTo) flyToTarget(v, flyTo.lon, flyTo.lat, flyTo.range ?? 2800);
    else if (command.type === 'north' || command.type === 'tilt') {
      const c = v.scene.canvas;
      const target = v.scene.pickPosition(new Cesium.Cartesian2(c.clientWidth / 2, c.clientHeight / 2)) ?? cam.pickEllipsoid(new Cesium.Cartesian2(c.clientWidth / 2, c.clientHeight / 2));
      if (target) {
        const range = Cesium.Cartesian3.distance(cam.position, target);
        const pitch = command.type === 'tilt' ? (cam.pitch < Cesium.Math.toRadians(-60) ? -28 : -85) : Cesium.Math.toDegrees(cam.pitch);
        cam.flyToBoundingSphere(new Cesium.BoundingSphere(target, 1), { offset: new Cesium.HeadingPitchRange(command.type === 'north' ? 0 : cam.heading, Cesium.Math.toRadians(pitch), range), duration: 0.8 });
      }
    }
    v.scene.requestRender();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [command?.key]);

  return (
    <div className={`tg-twin ${className}`}>
      <div className="tg-twin__canvas" ref={host} role="img" aria-label="3D city twin: 3D buildings, simulated water surface coloured by depth, rivers, three-state roads, shelters and generated incidents" />
      {error && <div className="tg-twin__error" role="status"><strong>3D view unavailable</strong><span>{error}</span></div>}
      {googleTilesConfigured() && googleState === 'loading' && <div className="tg-twin__chip">Loading Google Photorealistic 3D Tiles…</div>}
      {googleTilesConfigured() && googleState === 'failed' && <div className="tg-twin__chip is-warn">Google 3D Tiles unavailable; showing OSM buildings.</div>}
    </div>
  );
}
