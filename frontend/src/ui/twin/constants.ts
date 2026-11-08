/** Cesium-free display constants for the 3D twin, safe to import from the main bundle. */
import type { DepthClass, EdgeState } from '../api/v3types';

const GOOGLE_KEY = (import.meta.env.VITE_GOOGLE_MAPS_API_KEY as string | undefined)?.trim() || '';
const ION_TOKEN = (import.meta.env.VITE_CESIUM_ION_TOKEN as string | undefined)?.trim() || '';
export const googleTilesConfigured = () => ION_TOKEN.length > 0 || GOOGLE_KEY.length > 0;
export const ionConfigured = () => ION_TOKEN.length > 0;
export const imagerySourceLabel = () => (ION_TOKEN ? 'Google Maps 2D (Cesium ion)' : 'Esri World Imagery / CARTO');

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
