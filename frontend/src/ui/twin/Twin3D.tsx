import { useEffect, useMemo, useRef, useState } from 'react';
import * as Cesium from 'cesium';
import 'cesium/Build/Cesium/Widgets/widgets.css';
import { lonLatToUtm, terrainHeight, utmToLonLat, type TerrainGrid } from '../api/geo';
import { depthClass, estimatedLevels, LEVEL_HEIGHT_M, loadBoundary, loadCityRoads, loadGazetteer, loadWaterways, type CityRoads, type FocusFile, type GazPlace } from '../api/fixtures';
import { DEPTH_CLASS_STYLE, EDGE_STYLE, HOME_VIEW, PLACES, googleTilesConfigured } from './constants';
export { DEPTH_CLASS_STYLE, EDGE_STYLE, HOME_VIEW, PLACES, WATER_CLASS, WATER_EXAGGERATION, googleTilesConfigured, imagerySourceLabel, ionConfigured } from './constants';
import type { DepthClass, DepthFrame, EdgeState, FlowFrame, Incident, LonLat, RoadFeatureCollection, RouteOption, Shelter, StaticFeatureCollection } from '../api/v3types';

/**
 * B48 3D city twin (CesiumJS).
 * With VITE_CESIUM_ION_TOKEN (frontend/.env.local, git-ignored): Google Photorealistic 3D Tiles (ion 2275207),
 * Cesium World Terrain (ion 1) and Google 2D imagery (ion 3830182-3830184); attribution stays on screen.
 * Without it: our GLO-30 terrain, Esri/CARTO imagery and OSM footprints extruded and coloured by depth.
 * Simulated water is draped on the 3D tiles (classification volumes) or drawn as an animated water body.
 * Tokens are read only here and are never logged or sent to the TwinGuard API.
 */

export type ViewMode = '3d' | '2d' | 'satellite';
export interface TwinLayers { water: boolean; hqWater: boolean; buildings: boolean; roads: boolean; wards: boolean; shelters: boolean; incidents: boolean; google: boolean; photoreal: boolean }
export interface PickInfo { kind: 'building' | 'road' | 'shelter' | 'incident' | 'ward' | 'ground' | 'river'; title: string; lines: [string, string][]; location: LonLat }
export type TwinCommand = { type: 'home' | 'zoomIn' | 'zoomOut' | 'north' | 'tilt'; key: number };
export interface CameraInfo { headingDeg: number; metersPer100px: number | null; heightM: number; /** visible ground [w, s, e, n] in degrees, when computable */ viewBbox: [number, number, number, number] | null }

/** Fallback EGM2008 undulation for Chennai until the datum is calibrated against the loaded surface. */
const GEOID_N_M = -86;

const SEVERITY_COLOR: Record<string, string> = { critical: '#ff3b5c', warning: '#ff9f43', watch: '#f5c542', info: '#5fd0f0' };

const GOOGLE_KEY = (import.meta.env.VITE_GOOGLE_MAPS_API_KEY as string | undefined)?.trim() || '';
const ION_TOKEN = (import.meta.env.VITE_CESIUM_ION_TOKEN as string | undefined)?.trim() || '';
if (ION_TOKEN) Cesium.Ion.defaultAccessToken = ION_TOKEN;
const ION_ASSETS = { googlePhotorealistic: 2275207, worldTerrain: 1, osmBuildings: 96188, satellite: 3830182, satelliteLabels: 3830183, roadmap: 3830184 } as const;
/** Camera height (m) below which the Google photorealistic mesh replaces the citywide OSM buildings. */
const GOOGLE_NEAR_M = 3200;

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
/** Streaming settings shared by the citywide 3D tilesets (load fast, refine when the camera settles). */
const TILESET_OPTIONS = {
  showCreditsOnScreen: true, maximumScreenSpaceError: 16, skipLevelOfDetail: true, baseScreenSpaceError: 1024, skipScreenSpaceErrorFactor: 16, skipLevels: 1,
  immediatelyLoadDesiredLevelOfDetail: false, loadSiblings: false, cullRequestsWhileMoving: true, cullRequestsWhileMovingMultiplier: 60,
  foveatedScreenSpaceError: true, preferLeaves: false, progressiveResolutionHeightFraction: 0.5, cacheBytes: 512 * 1024 * 1024, dynamicScreenSpaceError: true,
};
let globeSettled = false;
/** Active WebGL renderer and the quality tier chosen from it (discrete GPU = high). */
export interface GpuInfo { renderer: string; vendor: string; tier: 'high' | 'standard' | 'low' }
let GPU: GpuInfo | null = null;
const gpuListeners = new Set<(g: GpuInfo) => void>();
export const getGpuInfo = () => GPU;
export function onGpuInfo(fn: (g: GpuInfo) => void) { gpuListeners.add(fn); if (GPU) fn(GPU); return () => { gpuListeners.delete(fn); }; }
function detectGpu(v: Cesium.Viewer): GpuInfo {
  const gl = (v.scene as unknown as { context: { _gl: WebGLRenderingContext } }).context._gl;
  const ext = gl.getExtension('WEBGL_debug_renderer_info');
  const renderer = String(ext ? gl.getParameter(ext.UNMASKED_RENDERER_WEBGL) : gl.getParameter(gl.RENDERER));
  const vendor = String(ext ? gl.getParameter(ext.UNMASKED_VENDOR_WEBGL) : gl.getParameter(gl.VENDOR));
  const r = renderer.toLowerCase();
  const tier = /swiftshader|llvmpipe|software|basic render/.test(r) ? 'low' : /nvidia|geforce|rtx|gtx|radeon rx|radeon pro|quadro|arc a/.test(r) ? 'high' : 'standard';
  return { renderer, vendor, tier };
}
/** Scale rendering quality to the GPU: MSAA, bloom, resolution and tile detail. */
function applyQuality(v: Cesium.Viewer, g: GpuInfo) {
  const scene = v.scene;
  scene.msaaSamples = g.tier === 'high' ? 4 : g.tier === 'standard' ? 2 : 1;
  scene.postProcessStages.fxaa.enabled = g.tier !== 'high';
  scene.postProcessStages.bloom.enabled = g.tier !== 'low';
  v.resolutionScale = g.tier === 'low' ? 0.8 : 1;
  scene.globe.maximumScreenSpaceError = g.tier === 'high' ? 1.5 : 2;
  TILESET_OPTIONS.maximumScreenSpaceError = g.tier === 'high' ? 8 : g.tier === 'standard' ? 16 : 24;
}
const glow = (color: string, power = 0.22) => Cesium.Material.fromType('PolylineGlow', { color: Cesium.Color.fromCssColorString(color), glowPower: power, taperPower: 1 });

/**
 * View-mode switch. 3D tilesets (OSM buildings, Google) cannot render in the 2D projection: their model matrices
 * throw inside GeographicProjection during the morph, and with render-loop errors hidden the animated morph stalls
 * in MORPHING forever (white map). So: hide tilesets before 2D and morph instantly (no tween); they are shown
 * again in 3D. "Satellite" stays in 3D as a top-down view, no morph.
 */
function switchSceneMode(v: Cesium.Viewer, mode: ViewMode) {
  const scene = v.scene;
  const tilesets: Cesium.Cesium3DTileset[] = [];
  for (let i = 0; i < scene.primitives.length; i += 1) {
    const p = scene.primitives.get(i);
    if (p instanceof Cesium.Cesium3DTileset) tilesets.push(p);
  }
  const c = scene.canvas;
  const mid = v.camera.pickEllipsoid(new Cesium.Cartesian2(c.clientWidth / 2, c.clientHeight / 2));
  const centre = mid ? Cesium.Cartographic.fromCartesian(mid) : null;
  const height = Math.max(800, Math.min(v.camera.positionCartographic.height || 6000, MAX_ZOOM_DISTANCE_M));
  if (mode === '2d') {
    if (scene.mode === Cesium.SceneMode.SCENE2D) return;
    // a hidden tileset skips its update, so it never reaches the 2D projection (its clipping can stay attached)
    for (const ts of tilesets) ts.show = false;
    scene.morphTo2D(0);
    if (centre) v.camera.setView({ destination: Cesium.Cartesian3.fromRadians(centre.longitude, centre.latitude, height * 1.3) });
  } else {
    const from2d = scene.mode !== Cesium.SceneMode.SCENE3D;
    if (from2d) {
      scene.morphTo3D(0); // tileset visibility is restored by the layer-visibility effect (mode !== '2d')
    }
    if (centre) {
      const pitch = mode === 'satellite' ? -90 : -32;
      // keep the same ground footprint: undo the 2D frustum factor
      const base = from2d ? height / 1.3 : height;
      // camera height = range * sin(|pitch|): keep the height the viewer had
      const range = Math.min(base / Math.sin(Cesium.Math.toRadians(-pitch)), MAX_ZOOM_DISTANCE_M);
      v.camera.flyToBoundingSphere(new Cesium.BoundingSphere(Cesium.Cartesian3.fromRadians(centre.longitude, centre.latitude, 0), 1), { offset: new Cesium.HeadingPitchRange(mode === 'satellite' ? 0 : v.camera.heading, Cesium.Math.toRadians(pitch), range), duration: 0.8 });
    }
  }
  scene.requestRender();
}

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
function buildingShader(frame: DepthFrame | null, groundEllipsoidM: number, night: boolean, photoreal = false) {
  const g = frame?.grid;
  const [lon, lat] = g ? utmToLonLat(g.origin_x_m, g.origin_y_m) : [80, 13];
  const enuInv = Cesium.Matrix4.inverse(Cesium.Transforms.eastNorthUpToFixedFrame(Cesium.Cartesian3.fromDegrees(lon, lat)), new Cesium.Matrix4());
  return new Cesium.CustomShader({
    uniforms: {
      u_depth: { type: Cesium.UniformType.SAMPLER_2D, value: depthClassUniform(frame) },
      u_enuInv: { type: Cesium.UniformType.MAT4, value: enuInv },
      u_size: { type: Cesium.UniformType.VEC2, value: new Cesium.Cartesian2(g ? g.cols * g.cell_size_m : 1, g ? g.rows * g.cell_size_m : 1) },
      u_ground: { type: Cesium.UniformType.FLOAT, value: groundEllipsoidM },
      u_night: { type: Cesium.UniformType.FLOAT, value: night ? 1 : 0 },
      u_photo: { type: Cesium.UniformType.FLOAT, value: photoreal ? 1 : 0 },
    },
    lightingModel: Cesium.LightingModel.UNLIT,
    fragmentShaderText: `
      float tgHash(vec2 p) { return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453); }
      void fragmentMain(FragmentInput fsInput, inout czm_modelMaterial material) {
        vec3 p = fsInput.attributes.positionWC;
        float r = length(p);
        float s = p.z / r;
        float c2 = 1.0 - s * s;
        float a = 6378137.0; float b = 6356752.3142;
        float h = r - a * b / sqrt(b * b * c2 + a * a * s * s) - u_ground;
        vec3 up = normalize(p);
        vec3 nW = normalize(czm_inverseViewRotation * fsInput.attributes.normalEC);
        float upness = abs(dot(nW, up));
        bool roof = upness > 0.7;
        // base palette: cool slate roofs, lighter walls with a soft vertical gradient and darker base (AO)
        // dry palette is light enough to read against the dark-tinted imagery from citywide distances
        vec3 roofCol = vec3(0.47, 0.56, 0.66);
        vec3 wallCol = mix(vec3(0.34, 0.41, 0.50), vec3(0.56, 0.64, 0.73), clamp(h / 45.0, 0.0, 1.0));
        float ao = mix(0.55, 1.0, clamp(h / 6.0, 0.0, 1.0));
        float sun = 0.75 + 0.25 * dot(nW, normalize(vec3(0.3, -0.5, 0.8)));
        vec3 col = roof ? roofCol * (0.9 + 0.1 * sun) : wallCol * ao * sun;
        if (u_photo > 0.5) {
          // experimental: satellite imagery draped on the tileset gives real roof colours; graded towards dusk.
          // Walls keep the procedural shading (vertical projection of imagery would only streak them).
          vec3 img = material.diffuse;
          float lum = dot(img, vec3(0.299, 0.587, 0.114));
          vec3 dusk = mix(vec3(lum), img, 0.65) * mix(1.0, 0.62, u_night) + vec3(0.0, 0.015, 0.04) * u_night;
          if (roof) col = dusk;
          else col = mix(col, col * (0.85 + 0.3 * lum), 0.5);
        }
        // flood colouring by the building's model cell
        vec4 local = u_enuInv * vec4(p, 1.0);
        vec2 uv = vec2(local.x / u_size.x, -local.y / u_size.y);
        bool flooded = false;
        if (uv.x >= 0.0 && uv.x <= 1.0 && uv.y >= 0.0 && uv.y <= 1.0) {
          vec4 fc = texture(u_depth, uv);
          if (fc.a > 0.5) { flooded = true; col = mix(col, fc.rgb * (roof ? 0.95 : 0.8 * ao), 0.78); }
        }
        // dusk window lights on walls
        if (!roof && u_night > 0.5 && h > 2.5) {
          vec3 t = normalize(cross(up, nW));
          float along = dot(p, t);
          vec2 cell = vec2(floor(along / 3.2), floor(h / 3.1));
          vec2 f = vec2(fract(along / 3.2), fract(h / 3.1));
          float win = step(0.28, f.x) * step(f.x, 0.72) * step(0.30, f.y) * step(f.y, 0.75);
          float lit = step(0.45, tgHash(cell + floor(p.xy / 97.0)));
          vec3 warm = mix(vec3(1.0, 0.78, 0.45), vec3(0.75, 0.9, 1.0), step(0.8, tgHash(cell * 1.7)));
          col = mix(col, flooded ? col * 0.6 : warm, win * lit * 0.85);
        }
        material.diffuse = col;
        material.emissive = u_night > 0.5 ? col * (roof ? 0.10 : 0.15) : vec3(0.0);
        material.alpha = 1.0;
      }`,
  });
}

/** Max depth encoded in the water texture's red channel (m). */
const WATER_DEPTH_SCALE = 2.5;
/**
 * Encode a depth frame as a WGS84 texture for the water shader: R = depth / 2.5 m (bilinear between valid
 * model cells; dry and NoData = 0), G/B = flow direction from the water-surface gradient (terrain + depth),
 * scaled by depth. When a real FlowFrame (u east, v north, m/s) for the same run and frame is given, G/B carry
 * the modelled velocity instead (bilinear, 1 m/s = full scale, sqrt-compressed so slow sheet flow still drifts). Alpha is always 255 so browser premultiplication cannot destroy the data.
 */
export function depthFieldCanvas(frame: DepthFrame, terrain: TerrainGrid | null, flow: FlowFrame | null = null, hole: [number, number, number, number] | null = null): { canvas: HTMLCanvasElement; bbox: [number, number, number, number] } | null {
  const g = frame.grid;
  const [w0, s0] = utmToLonLat(g.origin_x_m, g.origin_y_m - frame.rows * g.cell_size_m);
  const [e0, n0] = utmToLonLat(g.origin_x_m + frame.cols * g.cell_size_m, g.origin_y_m);
  const [w1] = utmToLonLat(g.origin_x_m, g.origin_y_m);
  const [e1] = utmToLonLat(g.origin_x_m + frame.cols * g.cell_size_m, g.origin_y_m - frame.rows * g.cell_size_m);
  const bbox: [number, number, number, number] = [Math.min(w0, w1), s0, Math.max(e0, e1), n0];
  const W = Math.min(1200, frame.cols * 10);
  const H = Math.round(W * ((bbox[3] - bbox[1]) / (bbox[2] - bbox[0])));
  const cv = document.createElement('canvas');
  cv.width = W; cv.height = H;
  const ctx = cv.getContext('2d');
  if (!ctx) return null;
  const val = (r: number, c: number) => (r < 0 || c < 0 || r >= frame.rows || c >= frame.cols ? null : frame.values[r][c]);
  const depth = new Float32Array(W * H);
  const surf = new Float32Array(W * H);
  const useFlow = !!flow && flow.run_id === frame.run_id && (frame.frame_index == null || flow.frame_index === frame.frame_index);
  const fu = new Float32Array(useFlow ? W * H : 0);
  const fv = new Float32Array(useFlow ? W * H : 0);
  const fg = flow?.grid;
  const flowAt = (e: number, n: number): [number, number] => {
    const fc = (e - fg!.origin_x_m) / fg!.cell_size_m - 0.5;
    const fr = (fg!.origin_y_m - n) / fg!.cell_size_m - 0.5;
    const c0 = Math.floor(fc); const r0 = Math.floor(fr); const dx = fc - c0; const dy = fr - r0;
    let su = 0; let sv = 0; let ws = 0;
    for (const [rr, cc, ww] of [[r0, c0, (1 - dx) * (1 - dy)], [r0, c0 + 1, dx * (1 - dy)], [r0 + 1, c0, (1 - dx) * dy], [r0 + 1, c0 + 1, dx * dy]] as [number, number, number][]) {
      if (rr < 0 || cc < 0 || rr >= flow!.rows || cc >= flow!.cols || ww <= 0) continue;
      const uu = flow!.u[rr]?.[cc]; const vv = flow!.v[rr]?.[cc];
      if (uu == null || vv == null) continue;
      su += uu * ww; sv += vv * ww; ws += ww;
    }
    return ws > 0 ? [su / ws, sv / ws] : [0, 0];
  };
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
      const inHole = !!hole && lon >= hole[0] && lon <= hole[2] && lat >= hole[1] && lat <= hole[3];
      const d = wsum < 0.35 || inHole ? 0 : sum / wsum;
      depth[y * W + x] = d;
      if (useFlow) { if (d > 0.01) { const [uu, vv] = flowAt(e, n); fu[y * W + x] = uu; fv[y * W + x] = vv; } }
      else surf[y * W + x] = terrainHeight(terrain, lon, lat) + d;
    }
  }
  const img = ctx.createImageData(W, H);
  for (let y = 0; y < H; y += 1) for (let x = 0; x < W; x += 1) {
    const i = y * W + x;
    const d = depth[i];
    let fx = 0; let fy = 0;
    if (useFlow) {
      if (d > 0.01) {
        const sp = Math.hypot(fu[i], fv[i]);
        if (sp > 1e-4) { const k = Math.min(1, Math.sqrt(sp / 1.0)); fx = (fu[i] / sp) * k; fy = (fv[i] / sp) * k; }
      }
    } else if (d > 0.01) {
      const sx = surf[y * W + Math.min(W - 1, x + 1)] - surf[y * W + Math.max(0, x - 1)];
      const sy = surf[Math.max(0, y - 1) * W + x] - surf[Math.min(H - 1, y + 1) * W + x]; // +y = north
      const len = Math.hypot(sx, sy);
      if (len > 1e-4) { const k = Math.min(1, d / 1.0); fx = (-sx / len) * k; fy = (-sy / len) * k; }
    }
    img.data[i * 4] = Math.round(Math.min(1, d / WATER_DEPTH_SCALE) * 255);
    img.data[i * 4 + 1] = Math.round(128 + 127 * fx);
    img.data[i * 4 + 2] = Math.round(128 + 127 * fy);
    img.data[i * 4 + 3] = 255;
  }
  ctx.putImageData(img, 0, 0);
  return { canvas: cv, bbox };
}

/** Animated flood-water material for the draped surface (ripples, Fresnel dusk sky, glints, flow streaks, shoreline foam). */
function floodWaterMaterial() {
  return new Cesium.Material({
    translucent: true,
    fabric: {
      type: 'TwinGuardFloodWater',
      uniforms: { image0: Cesium.Material.DefaultImageId, image1: Cesium.Material.DefaultImageId, mixT: 1.0, normalMap: Cesium.buildModuleUrl('Assets/Textures/waterNormals.jpg'), time: 0.0, hq: 1.0, depthScale: WATER_DEPTH_SCALE, fade: 1.0 },
      source: `
        czm_material czm_getMaterial(czm_materialInput materialInput) {
          czm_material m = czm_getDefaultMaterial(materialInput);
          vec2 st = materialInput.st;
          vec4 d = mix(texture(image0, st), texture(image1, st), mixT);
          float depth = d.r * depthScale;
          float alpha = smoothstep(0.0, 0.05, depth);
          if (alpha < 0.002) { m.alpha = 0.0; return m; }
          vec2 flow = (d.gb - 0.5) * 2.0;
          vec3 shallow = vec3(0.40, 0.42, 0.28);
          vec3 mid = vec3(0.13, 0.36, 0.42);
          vec3 deep = vec3(0.04, 0.16, 0.33);
          vec3 base = depth < 0.3 ? mix(shallow, mid, depth / 0.3) : mix(mid, deep, clamp((depth - 0.3) / 1.2, 0.0, 1.0));
          vec2 uv = st * vec2(850.0, 1100.0);
          vec2 drift = flow * time * 0.05;
          vec3 n1 = texture(normalMap, uv * 0.9 + vec2(time * 0.010, time * 0.006) - drift).xyz * 2.0 - 1.0;
          vec3 n2 = texture(normalMap, uv * 1.7 - vec2(time * 0.007, -time * 0.011) - drift * 1.6).xyz * 2.0 - 1.0;
          vec3 up = normalize(materialInput.normalEC);
          vec3 zEC = normalize(vec3(czm_view[2].xyz));
          vec3 east = normalize(cross(zEC, up));
          vec3 north = cross(up, east);
          vec2 slope = (n1.xy + n2.xy) * 0.35 * hq;
          vec3 nEC = normalize(up + east * slope.x + north * slope.y);
          vec3 v = normalize(-materialInput.positionToEyeEC);
          float fres = pow(1.0 - max(dot(nEC, v), 0.0), 3.0);
          vec3 sky = vec3(0.36, 0.46, 0.66);
          vec3 col = mix(base, sky, 0.18 + 0.55 * fres);
          vec3 L = normalize(czm_lightDirectionEC + vec3(0.0, 0.0, 0.4));
          float spec = pow(max(dot(reflect(-L, nEC), v), 0.0), 70.0) * hq;
          col += vec3(1.0, 0.88, 0.7) * spec * 0.7;
          float speed = length(flow);
          float streak = texture(normalMap, uv * 0.18 - flow * time * 0.25).r;
          col += vec3(0.75, 0.88, 0.95) * smoothstep(0.66, 0.92, streak) * speed * 0.45 * hq;
          float foamNoise = texture(normalMap, uv * 2.4 + vec2(time * 0.03)).g;
          float foam = (1.0 - smoothstep(0.03, 0.14, depth)) * smoothstep(0.5, 0.78, foamNoise);
          col = mix(col, vec3(0.88, 0.92, 0.9), foam * 0.55);
          m.diffuse = col * 0.8;
          m.emission = col * 0.22 + vec3(1.0, 0.9, 0.75) * spec * 0.3;
          m.specular = 0.7;
          m.shininess = 70.0;
          m.normal = nEC;
          m.alpha = alpha * mix(0.62, 0.92, clamp(depth / 0.8, 0.0, 1.0)) * fade;
          return m;
        }`,
    },
  });
}

export function Twin3D({ mode, layers, terrain, frame, flow = null, contextFrame = null, focusBox = null, focus, roads, wards, wardShapes, highlightWard, shelters, incidents, route, flyTo, command, onCamera, onPick, onMapClick, className = '' }: {
  mode: ViewMode;
  layers: TwinLayers;
  terrain: TerrainGrid | null;
  frame: DepthFrame | null;
  /** Real per-frame flow velocities (B49); null falls back to the surface-gradient estimate. */
  flow?: FlowFrame | null;
  /** Citywide depth drawn faded outside a 30 m focus run's box (city context). */
  contextFrame?: DepthFrame | null;
  /** A focus run's simulation box, outlined and labelled. */
  focusBox?: { bbox: [number, number, number, number]; label: string } | null;
  focus: FocusFile | null;
  roads?: RoadFeatureCollection | null;
  wards?: StaticFeatureCollection | null;
  /** All ward polygons (for highlighting a searched ward even when the ward layer is off). */
  wardShapes?: StaticFeatureCollection | null;
  highlightWard?: number | null;
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
  /** flips true once the shared viewer exists, so layer effects that ran too early re-run */
  const [viewerOk, setViewerOk] = useState(false);
  const datumRef = useRef(datum);
  datumRef.current = datum;
  const [rivers, setRivers] = useState<StaticFeatureCollection | null>(null);
  const [cityRoads, setCityRoads] = useState<CityRoads | null>(null);
  const [boundary, setBoundary] = useState<StaticFeatureCollection | null>(null);
  const [near, setNear] = useState(false);
  const [osmReady, setOsmReady] = useState(false);
  const [pending, setPending] = useState(0);
  const nearRef = useRef(near);
  const boundaryRef = useRef<StaticFeatureCollection | null>(null);
  boundaryRef.current = boundary;
  const makeClip = (b: StaticFeatureCollection) => new Cesium.ClippingPolygonCollection({
    inverse: true,
    polygons: b.features.map((f) => new Cesium.ClippingPolygon({ positions: Cesium.Cartesian3.fromDegreesArray(((f.geometry.coordinates as number[][][])[0]).slice(0, -1).flat()) })),
  });
  const googleOn = googleState === 'on' && layers.google && mode !== '2d';

  const ground = (lon: number, lat: number) => terrainHeight(terrain, lon, lat) + datum;

  const [places, setPlaces] = useState<GazPlace[] | null>(null);
  useEffect(() => { loadCityRoads().then(setCityRoads); loadWaterways().then(setRivers); loadBoundary().then(setBoundary); loadGazetteer().then((g) => setPlaces(g?.places ?? null)); }, []);

  /* locality labels from the gazetteer, decluttered by rank: more appear as you zoom in */
  useEffect(() => {
    const v = viewer.current;
    if (!v || !places?.length) return;
    const old = prims.current.labels;
    if (old) v.scene.primitives.remove(old);
    const curated = new Set(PLACES.map((p) => p.name.toLowerCase()));
    const lc = new Cesium.LabelCollection({ scene: v.scene });
    const far: Record<number, number> = { 1: 70000, 2: 16000, 3: 6000, 4: 3200 };
    for (const p of places) {
      if (curated.has(p.name.toLowerCase())) continue;
      lc.add({
        position: Cesium.Cartesian3.fromDegrees(p.lon, p.lat, ground(p.lon, p.lat) + 35), text: p.name,
        font: p.rank <= 2 ? '600 14px Inter, Segoe UI, sans-serif' : '500 12px Inter, Segoe UI, sans-serif',
        fillColor: Cesium.Color.fromCssColorString(p.rank <= 2 ? '#f2fbff' : '#cfe6f2'), outlineColor: Cesium.Color.fromCssColorString('#04101c'), outlineWidth: 3,
        style: Cesium.LabelStyle.FILL_AND_OUTLINE, horizontalOrigin: Cesium.HorizontalOrigin.CENTER, verticalOrigin: Cesium.VerticalOrigin.BOTTOM,
        distanceDisplayCondition: new Cesium.DistanceDisplayCondition(0, far[p.rank] ?? 3200), disableDepthTestDistance: 4000,
        translucencyByDistance: new Cesium.NearFarScalar((far[p.rank] ?? 3200) * 0.6, 1.0, far[p.rank] ?? 3200, 0.0),
      });
    }
    v.scene.primitives.add(lc);
    prims.current.labels = lc as unknown as Cesium.Primitive;
    v.scene.requestRender();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [places, terrain, datum]);

  /* highlighted ward (search / Areas list) */
  useEffect(() => {
    const v = viewer.current;
    if (!v) return;
    const old = prims.current.highlight;
    if (old) v.scene.primitives.remove(old);
    prims.current.highlight = null;
    const f = highlightWard ? wardShapes?.features.find((x) => Number(x.properties.ward_id) === highlightWard) : null;
    if (!f) { v.scene.requestRender(); return; }
    const polys = (f.geometry.type === 'Polygon' ? [f.geometry.coordinates] : (f.geometry.coordinates as number[][][][])) as number[][][][];
    const p = new Cesium.GroundPolylinePrimitive({
      geometryInstances: polys.map((rings) => new Cesium.GeometryInstance({ geometry: new Cesium.GroundPolylineGeometry({ positions: Cesium.Cartesian3.fromDegreesArray(rings[0].flat()), width: 5 }) })),
      appearance: new Cesium.PolylineMaterialAppearance({ material: glow('#ffd166', 0.35) }), classificationType: Cesium.ClassificationType.BOTH, asynchronous: true,
    });
    v.scene.primitives.add(p);
    prims.current.highlight = p;
    v.scene.requestRender();
  }, [highlightWard, wardShapes]);

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
          contextOptions: { webgl: { failIfMajorPerformanceCaveat: false, powerPreference: 'high-performance', antialias: true } },
        });
        created.scene.renderError.addEventListener(() => { if (!created.isDestroyed()) created.useDefaultRenderLoop = (created.canvas.clientWidth > 0); });
        SHARED = { v: created, el, dusk: setupScene(created), google: null, osm: null };
        performance.mark('tg-viewer-ready');
        GPU = detectGpu(created);
        applyQuality(created, GPU);
        console.info(`[TwinGuard] WebGL renderer: ${GPU.renderer} (${GPU.vendor}); quality tier ${GPU.tier}`);
        gpuListeners.forEach((fn) => fn(GPU!));
        const rmGlobe = created.scene.globe.tileLoadProgressEvent.addEventListener((n: number) => { if (n === 0 && created.scene.globe.tilesLoaded) { performance.mark('tg-globe-loaded'); rmGlobe(); } });
      } catch (e) {
        el.remove();
        setError(e instanceof Error ? e.message : 'WebGL is unavailable in this browser.');
        return;
      }
    } else hostEl.appendChild(SHARED.el);
    const v = SHARED.v;
    viewer.current = v;
    setViewerOk(true);
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
      const rect = v.camera.computeViewRectangle();
      const viewBbox: [number, number, number, number] | null = rect ? [Cesium.Math.toDegrees(rect.west), Cesium.Math.toDegrees(rect.south), Cesium.Math.toDegrees(rect.east), Cesium.Math.toDegrees(rect.north)] : null;
      camRef.current?.({ headingDeg: Cesium.Math.toDegrees(v.camera.heading), metersPer100px: a && b ? Cesium.Cartesian3.distance(a, b) : null, heightM: height, viewBbox });
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
    let lastPending = -1;
    let lastCheck = 0;
    const removeProgress = v.scene.postRender.addEventListener(() => {
      const now = performance.now();
      if (now - lastCheck < 400) return;
      lastCheck = now;
      let n = v.scene.globe.tilesLoaded ? 0 : 1;
      for (let i = 0; i < v.scene.primitives.length; i += 1) {
        const p = v.scene.primitives.get(i) as { statistics?: { numberOfPendingRequests: number; numberOfTilesProcessing: number }; show?: boolean };
        if (p?.statistics && p.show !== false) n += p.statistics.numberOfPendingRequests + p.statistics.numberOfTilesProcessing;
      }
      if (n !== lastPending) { lastPending = n; setPending(n); }
    });
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
      removeCam(); removeMove(); removeProgress(); handler.destroy();
      for (const [k, p] of Object.entries(prims.current)) {
        if (k === 'google' || k === 'osm' || k === 'dusk' || !p) continue;
        if (v.scene.primitives.contains(p as Cesium.Primitive)) v.scene.primitives.remove(p as Cesium.Primitive);
      }
      v.entities.removeAll();
      v.useDefaultRenderLoop = false;
      if (SHARED?.el.parentElement === hostEl) hostEl.removeChild(SHARED.el);
      viewer.current = null;
      setViewerOk(false);
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
    switchSceneMode(v, mode);
    if (ION_TOKEN) {
      const asset = mode === '2d' ? ION_ASSETS.roadmap : mode === 'satellite' ? ION_ASSETS.satelliteLabels : ION_ASSETS.satellite;
      Cesium.IonImageryProvider.fromAssetId(asset).then((p) => {
        if (cancelled) return;
        const layer = v.imageryLayers.addImageryProvider(p);
        if (mode === '3d') tint(layer, true);
        else if (mode === '2d') { layer.brightness = 0.42; layer.contrast = 1.35; layer.gamma = 1.25; layer.saturation = 0.3; layer.hue = 0; } // dark, low-saturation roadmap to match the UI
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
    const load = ION_TOKEN ? Cesium.Cesium3DTileset.fromIonAssetId(ION_ASSETS.googlePhotorealistic, TILESET_OPTIONS) : Cesium.createGooglePhotorealistic3DTileset({ key: GOOGLE_KEY }, TILESET_OPTIONS);
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
    if (existing && !existing.isDestroyed()) { existing.customShader = buildingShader(frame, datum + 6, mode === '3d', layers.photoreal); setOsmReady(true); v.scene.requestRender(); return; }
    // load order: terrain + imagery first, citywide buildings once the globe has settled (or after 4 s)
    const start = () => Cesium.Cesium3DTileset.fromIonAssetId(ION_ASSETS.osmBuildings, TILESET_OPTIONS);
    const ready = globeSettled ? Promise.resolve() : new Promise<void>((res) => {
      const t = window.setTimeout(res, 4000);
      const rm = v.scene.globe.tileLoadProgressEvent.addEventListener((n: number) => { if (n === 0) { globeSettled = true; window.clearTimeout(t); rm(); res(); } });
    });
    ready.then(start).then((ts) => {
      if (cancelled || viewer.current !== v || v.isDestroyed()) { ts.destroy(); return; }
      ts.clippingPolygons = makeClip(boundary);
      ts.customShader = buildingShader(frame, datum + 6, mode === '3d', layers.photoreal);
      const rmTiles = ts.allTilesLoaded.addEventListener(() => { performance.mark('tg-buildings-loaded'); rmTiles(); });
      v.scene.primitives.add(ts);
      prims.current.osm = ts;
      if (SHARED) SHARED.osm = ts;
      setOsmReady(true);
      v.scene.requestRender();
    }).catch(() => setOsmReady(false));
    return () => { cancelled = true; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [boundary, frame, datum, mode, layers.photoreal]);

  /* experimental photoreal roofs: drape the ion satellite imagery on the OSM buildings tileset (roof colour source) */
  useEffect(() => {
    const v = viewer.current;
    const ts = prims.current.osm as Cesium.Cesium3DTileset | null | undefined;
    if (!v || !ts || ts.isDestroyed() || !osmReady) return;
    const layersOnTiles = ts.imageryLayers;
    if (!layers.photoreal) { layersOnTiles.removeAll(true); v.scene.requestRender(); return; }
    if (layersOnTiles.length) return;
    let live = true;
    Cesium.IonImageryProvider.fromAssetId(ION_ASSETS.satellite).then((provider) => {
      if (!live || ts.isDestroyed()) return;
      layersOnTiles.add(new Cesium.ImageryLayer(provider));
      v.scene.requestRender();
    }).catch(() => { /* imagery unavailable: roofs keep the procedural palette */ });
    return () => { live = false; };
  }, [layers.photoreal, osmReady]);

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

  /* simulated water: depth field draped on the rendered ground with an animated water material.
     Frame changes cross-fade the depth texture so the water visibly rises and falls between saved frames. */
  const waterRef = useRef<{ material: Cesium.Material; canvas: HTMLCanvasElement; key: string } | null>(null);
  const field = useMemo(() => (frame && typeof document !== 'undefined' ? depthFieldCanvas(frame, terrain, flow) : null), [frame, terrain, flow]);
  const classifyOnTiles = googleOn && near;
  useEffect(() => {
    const v = viewer.current;
    if (!v) return;
    if (!field) {
      const old = prims.current.water; if (old) v.scene.primitives.remove(old); prims.current.water = null; waterRef.current = null; return;
    }
    const key = `${field.bbox.join(',')}|${classifyOnTiles}`;
    const cur = waterRef.current;
    if (cur && cur.key === key && prims.current.water) {
      // tween from the shown depth to the new frame
      const mat = cur.material;
      mat.uniforms.image0 = cur.canvas;
      mat.uniforms.image1 = field.canvas;
      mat.uniforms.mixT = 0;
      cur.canvas = field.canvas;
      const start = performance.now();
      const reduce = window.matchMedia?.('(prefers-reduced-motion: reduce)').matches;
      const dur = reduce ? 1 : 1400;
      const step = () => {
        const t = Math.min(1, (performance.now() - start) / dur);
        mat.uniforms.mixT = t * t * (3 - 2 * t);
        v.scene.requestRender();
        if (t < 1 && waterRef.current?.material === mat) requestAnimationFrame(step);
      };
      requestAnimationFrame(step);
      return;
    }
    const old = prims.current.water;
    if (old) v.scene.primitives.remove(old);
    const material = floodWaterMaterial();
    // canvases are assigned after construction: Cesium deep-clones the fabric and cannot clone an HTMLCanvasElement
    material.uniforms.image0 = field.canvas;
    material.uniforms.image1 = field.canvas;
    const p = new Cesium.GroundPrimitive({
      geometryInstances: new Cesium.GeometryInstance({ geometry: new Cesium.RectangleGeometry({ rectangle: Cesium.Rectangle.fromDegrees(...field.bbox), vertexFormat: Cesium.MaterialAppearance.MaterialSupport.ALL.vertexFormat }), id: { kind: 'ground', title: 'Simulated flood water', location: { lon: (field.bbox[0] + field.bbox[2]) / 2, lat: (field.bbox[1] + field.bbox[3]) / 2 }, lines: [['Source', 'saved run depth grid'], ['Rendering', 'bilinear between model cells, draped on ground']] } as PickInfo }),
      appearance: new Cesium.MaterialAppearance({ material, translucent: true, materialSupport: Cesium.MaterialAppearance.MaterialSupport.ALL }),
      // Terrain only, so water lies on the ground between buildings and never paints building roofs or walls;
      // with Google 3D tiles shown up close it must drape on the tile mesh as well.
      classificationType: classifyOnTiles ? Cesium.ClassificationType.BOTH : Cesium.ClassificationType.TERRAIN,
      asynchronous: true,
    });
    p.show = layers.water;
    v.scene.primitives.add(p);
    prims.current.water = p;
    waterRef.current = { material, canvas: field.canvas, key };
    v.scene.requestRender();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [field, classifyOnTiles]);

  /* focus runs: citywide context water (faded, with a hole where the 30 m run has its own detailed water) */
  const ctxMatRef = useRef<Cesium.Material | null>(null);
  const ctxField = useMemo(() => (contextFrame && typeof document !== 'undefined' ? depthFieldCanvas(contextFrame, terrain, null, focusBox?.bbox ?? null) : null), [contextFrame, terrain, focusBox?.bbox]);
  useEffect(() => {
    const v = viewer.current;
    if (!v) return;
    const old = prims.current.ctxWater; if (old) v.scene.primitives.remove(old);
    prims.current.ctxWater = null; ctxMatRef.current = null;
    if (!ctxField) { v.scene.requestRender(); return; }
    const material = floodWaterMaterial();
    material.uniforms.image0 = ctxField.canvas;
    material.uniforms.image1 = ctxField.canvas;
    material.uniforms.fade = 0.42;
    const p = new Cesium.GroundPrimitive({
      geometryInstances: new Cesium.GeometryInstance({ geometry: new Cesium.RectangleGeometry({ rectangle: Cesium.Rectangle.fromDegrees(...ctxField.bbox), vertexFormat: Cesium.MaterialAppearance.MaterialSupport.ALL.vertexFormat }), id: { kind: 'ground', title: 'Citywide context water (faded)', location: { lon: (ctxField.bbox[0] + ctxField.bbox[2]) / 2, lat: (ctxField.bbox[1] + ctxField.bbox[3]) / 2 }, lines: [['Source', 'nearest citywide run, same forcing'], ['Note', 'context only; the 30 m focus run is inside the box']] } as PickInfo }),
      appearance: new Cesium.MaterialAppearance({ material, translucent: true, materialSupport: Cesium.MaterialAppearance.MaterialSupport.ALL }),
      classificationType: Cesium.ClassificationType.TERRAIN,
      asynchronous: true,
    });
    p.show = layers.water;
    v.scene.primitives.add(p);
    prims.current.ctxWater = p;
    ctxMatRef.current = material;
    v.scene.requestRender();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [ctxField, viewerOk]);

  /* focus-run box: glowing outline and label */
  useEffect(() => {
    const v = viewer.current;
    if (!v) return;
    const old = prims.current.focusBox; if (old) v.scene.primitives.remove(old);
    const oldL = prims.current.focusLabel; if (oldL) v.scene.primitives.remove(oldL);
    prims.current.focusBox = null; prims.current.focusLabel = null;
    if (!focusBox) { v.scene.requestRender(); return; }
    const [w, s, e, n] = focusBox.bbox;
    const p = new Cesium.GroundPolylinePrimitive({
      geometryInstances: new Cesium.GeometryInstance({ geometry: new Cesium.GroundPolylineGeometry({ positions: Cesium.Cartesian3.fromDegreesArray([w, s, e, s, e, n, w, n, w, s]), width: 9 }) }),
      appearance: new Cesium.PolylineMaterialAppearance({ material: glow('#5fe8ff', 0.32) }),
      classificationType: Cesium.ClassificationType.BOTH, asynchronous: true,
    });
    v.scene.primitives.add(p);
    const lc = new Cesium.LabelCollection({ scene: v.scene });
    lc.add({
      position: Cesium.Cartesian3.fromDegrees((w + e) / 2, n, ground((w + e) / 2, n) + 60), text: focusBox.label,
      font: '600 14px Inter, Segoe UI, sans-serif', fillColor: Cesium.Color.fromCssColorString('#dffbff'), outlineColor: Cesium.Color.fromCssColorString('#04101c'), outlineWidth: 4,
      style: Cesium.LabelStyle.FILL_AND_OUTLINE, showBackground: true, backgroundColor: Cesium.Color.fromCssColorString('#06283a').withAlpha(0.82), backgroundPadding: new Cesium.Cartesian2(10, 6),
      horizontalOrigin: Cesium.HorizontalOrigin.CENTER, verticalOrigin: Cesium.VerticalOrigin.BOTTOM, disableDepthTestDistance: Number.POSITIVE_INFINITY,
    });
    v.scene.primitives.add(lc);
    prims.current.focusBox = p; prims.current.focusLabel = lc as unknown as Cesium.PrimitiveCollection;
    v.scene.requestRender();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [focusBox?.bbox.join(','), focusBox?.label, datum]);

  /* water clock and quality */
  useEffect(() => {
    const v = viewer.current;
    if (!v) return;
    const remove = v.scene.preRender.addEventListener(() => {
      const w = waterRef.current;
      if (w) { w.material.uniforms.time = performance.now() / 1000; w.material.uniforms.hq = layers.hqWater ? 1 : 0; }
      const cm = ctxMatRef.current;
      if (cm) { cm.uniforms.time = performance.now() / 1000; cm.uniforms.hq = 0; }
    });
    return remove;
  }, [layers.hqWater]);

  /* continuous rendering keeps the water animated (respecting reduced motion) */
  useEffect(() => {
    const v = viewer.current;
    if (!v) return;
    const reduce = window.matchMedia?.('(prefers-reduced-motion: reduce)').matches;
    v.scene.requestRenderMode = !(layers.water && layers.hqWater && frame && !reduce);
    v.scene.requestRender();
  }, [layers.water, layers.hqWater, frame]);

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

  /* citywide major roads: neutral context everywhere (not assessed in this run unless the run colours them) */
  useEffect(() => {
    const v = viewer.current;
    if (!v || !cityRoads?.lines.length) return;
    const old = prims.current.cityRoads; if (old) v.scene.primitives.remove(old);
    const WIDTH: Record<string, number> = { motorway: 4.2, trunk: 3.8, primary: 3.2, secondary: 2.5, tertiary: 1.8 };
    const coll = new Cesium.PrimitiveCollection();
    cityRoads.classes.forEach((cls, ci) => {
      const instances: Cesium.GeometryInstance[] = [];
      for (const ln of cityRoads.lines) {
        if (ln[0] !== ci) continue;
        const deg: number[] = [];
        let x = ln[1]; let y = ln[2];
        deg.push(x / 1e5, y / 1e5);
        for (let i = 3; i + 1 < ln.length; i += 2) { x += ln[i]; y += ln[i + 1]; deg.push(x / 1e5, y / 1e5); }
        instances.push(new Cesium.GeometryInstance({ geometry: new Cesium.GroundPolylineGeometry({ positions: Cesium.Cartesian3.fromDegreesArray(deg), width: WIDTH[cls] ?? 1.8 }) }));
      }
      if (!instances.length) return;
      coll.add(new Cesium.GroundPolylinePrimitive({
        geometryInstances: instances,
        appearance: new Cesium.PolylineMaterialAppearance({ material: Cesium.Material.fromType('Color', { color: Cesium.Color.fromCssColorString(ci <= 1 ? '#9aa9ba' : '#7f8fa1').withAlpha(ci <= 2 ? 0.62 : 0.45) }) }),
        classificationType: Cesium.ClassificationType.TERRAIN, asynchronous: true,
      }));
    });
    coll.show = layers.roads;
    v.scene.primitives.add(coll);
    prims.current.cityRoads = coll;
    v.scene.requestRender();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [cityRoads]);

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
          attributes: { distanceDisplayCondition: new Cesium.DistanceDisplayConditionGeometryInstanceAttribute(0, 18000) },
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
    // 3D tiles (OSM buildings, Google) cannot be drawn in the 2D projection; they come back with 3D
    set('osm', layers.buildings && osmReady && mode !== '2d');
    set('buildings', layers.buildings && !osmReady);
    set('roads', layers.roads);
    set('cityRoads', layers.roads);
    set('ctxWater', layers.water);
    set('wards', layers.wards);
    set('shelters', layers.shelters);
    set('incidents', layers.incidents);
    v.scene.requestRender();
  }, [layers, googleOn, near, osmReady, mode]);

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
      {pending > 0 && <div className="tg-twin__progress" role="status" aria-label={`Loading map tiles: ${pending} pending`}><i /><span>Loading map tiles · {pending}</span></div>}
      {googleTilesConfigured() && googleState === 'loading' && <div className="tg-twin__chip">Loading Google Photorealistic 3D Tiles…</div>}
      {googleTilesConfigured() && googleState === 'failed' && <div className="tg-twin__chip is-warn">Google 3D Tiles unavailable; showing OSM buildings.</div>}
    </div>
  );
}
