/**
 * Small, strict decoder for the bounded A20 single-band Float32 GeoTIFFs.
 * It intentionally supports only the compression/predictor and GeoKeys used by
 * those saved assets; it is not a general purpose TIFF reader.
 */

const MAX_TIFF_BYTES = 1024 * 1024;
const MAX_CELLS = 100_000;
const MAX_IFD_ENTRIES = 128;

const TIFF_TYPE_SIZE = new Map([
  [1, 1], [2, 1], [3, 2], [4, 4], [5, 8], [6, 1], [7, 1],
  [8, 2], [9, 4], [10, 8], [11, 4], [12, 8],
]);

function assert(condition, message) {
  if (!condition) throw new Error(message);
}

function readAscii(view, offset, count) {
  assert(offset >= 0 && count >= 0 && offset + count <= view.byteLength, 'TIFF string is outside the file.');
  const bytes = new Uint8Array(view.buffer, view.byteOffset + offset, count);
  return new TextDecoder().decode(bytes).replace(/\0+$/, '');
}

function readTagValues(view, littleEndian, type, count, valueOffset) {
  const size = TIFF_TYPE_SIZE.get(type);
  assert(size !== undefined && count > 0 && count <= 4096, 'TIFF tag type or count is unsupported.');
  const total = size * count;
  const offset = total <= 4 ? valueOffset : view.getUint32(valueOffset, littleEndian);
  assert(offset >= 0 && offset + total <= view.byteLength, 'TIFF tag value is outside the file.');

  if (type === 2) return readAscii(view, offset, count);
  const values = [];
  for (let i = 0; i < count; i += 1) {
    const pos = offset + i * size;
    switch (type) {
      case 1:
      case 7: values.push(view.getUint8(pos)); break;
      case 3: values.push(view.getUint16(pos, littleEndian)); break;
      case 4: values.push(view.getUint32(pos, littleEndian)); break;
      case 6: values.push(view.getInt8(pos)); break;
      case 8: values.push(view.getInt16(pos, littleEndian)); break;
      case 9: values.push(view.getInt32(pos, littleEndian)); break;
      case 11: values.push(view.getFloat32(pos, littleEndian)); break;
      case 12: values.push(view.getFloat64(pos, littleEndian)); break;
      default: throw new Error('TIFF tag value representation is unsupported.');
    }
  }
  return values;
}

function parseIfd(view, littleEndian) {
  assert(view.byteLength >= 8, 'TIFF header is truncated.');
  const order = String.fromCharCode(view.getUint8(0), view.getUint8(1));
  assert(order === 'II' || order === 'MM', 'TIFF byte order is invalid.');
  assert(view.getUint16(2, littleEndian) === 42, 'BigTIFF or non-classic TIFF is not supported.');
  const ifdOffset = view.getUint32(4, littleEndian);
  assert(ifdOffset + 2 <= view.byteLength, 'TIFF directory is outside the file.');
  const entryCount = view.getUint16(ifdOffset, littleEndian);
  assert(entryCount > 0 && entryCount <= MAX_IFD_ENTRIES, 'TIFF directory exceeds the supported bound.');
  assert(ifdOffset + 2 + entryCount * 12 + 4 <= view.byteLength, 'TIFF directory is truncated.');

  const tags = new Map();
  for (let i = 0; i < entryCount; i += 1) {
    const entry = ifdOffset + 2 + i * 12;
    const tag = view.getUint16(entry, littleEndian);
    const type = view.getUint16(entry + 2, littleEndian);
    const count = view.getUint32(entry + 4, littleEndian);
    tags.set(tag, readTagValues(view, littleEndian, type, count, entry + 8));
  }
  return { littleEndian, tags };
}

function one(tags, id, label) {
  const values = tags.get(id);
  assert(values && values.length === 1, `Required TIFF ${label} tag is missing or ambiguous.`);
  return values[0];
}

async function inflateStrip(bytes, expectedSize) {
  assert(typeof DecompressionStream !== 'undefined', 'This browser does not support the required deflate decoder.');
  const stream = new Blob([bytes]).stream().pipeThrough(new DecompressionStream('deflate'));
  const result = new Uint8Array(await new Response(stream).arrayBuffer());
  assert(result.byteLength === expectedSize, 'Decoded TIFF strip length does not match its grid.');
  return result;
}

function undoFloatPredictor(row, width, littleEndian) {
  // Predictor 3 accumulates the shuffled byte stream, then restores the
  // interleaved IEEE-754 bytes. The TIFF has one sample per pixel (stride 1).
  for (let i = 1; i < row.length; i += 1) row[i] = (row[i] + row[i - 1]) & 0xff;
  const shuffled = row.slice();
  for (let pixel = 0; pixel < width; pixel += 1) {
    for (let byte = 0; byte < 4; byte += 1) {
      const plane = littleEndian ? 3 - byte : byte;
      row[pixel * 4 + byte] = shuffled[plane * width + pixel];
    }
  }
}

function projectedCode(tags) {
  const keys = tags.get(34735);
  if (!keys || keys.length < 4) return null;
  const count = keys[3];
  for (let i = 0; i < count; i += 1) {
    const base = 4 + i * 4;
    if (keys[base] === 3072 && keys[base + 1] === 0 && keys[base + 2] === 1) {
      return keys[base + 3];
    }
  }
  return null;
}

/** Decode and validate one original A20 Float32 GeoTIFF response. */
export async function parseA20Float32GeoTiff(input, expectedGrid) {
  const bytes = input instanceof Uint8Array ? input : new Uint8Array(input);
  assert(bytes.byteLength > 0 && bytes.byteLength <= MAX_TIFF_BYTES, 'Saved raster size is outside the allowed bound.');
  const view = new DataView(bytes.buffer, bytes.byteOffset, bytes.byteLength);
  const order = String.fromCharCode(view.getUint8(0), view.getUint8(1));
  const littleEndian = order === 'II';
  const { tags } = parseIfd(view, littleEndian);

  const width = one(tags, 256, 'ImageWidth');
  const height = one(tags, 257, 'ImageLength');
  assert(Number.isInteger(width) && Number.isInteger(height) && width * height <= MAX_CELLS, 'TIFF grid exceeds the supported bound.');
  assert(one(tags, 258, 'BitsPerSample') === 32, 'Only single-band Float32 rasters are supported.');
  assert(one(tags, 259, 'Compression') === 8, 'Only the saved deflate compression is supported.');
  assert(one(tags, 277, 'SamplesPerPixel') === 1, 'Only a single-band raster is supported.');
  assert(one(tags, 284, 'PlanarConfiguration') === 1, 'Only contiguous single-band storage is supported.');
  assert(one(tags, 317, 'Predictor') === 3, 'Only the saved floating-point predictor is supported.');
  assert(one(tags, 339, 'SampleFormat') === 3, 'Raster samples are not IEEE Float32.');

  const pixelScale = tags.get(33550);
  const tiepoint = tags.get(33922);
  assert(pixelScale?.length === 3 && tiepoint?.length === 6, 'GeoTIFF spatial transform is missing.');
  const transform = [
    pixelScale[0], 0, tiepoint[3] - tiepoint[0] * pixelScale[0],
    0, -pixelScale[1], tiepoint[4] + tiepoint[1] * pixelScale[1],
  ];
  const crsCode = projectedCode(tags);
  const noDataText = tags.get(42113);
  assert(typeof noDataText === 'string' && Number.isFinite(Number(noDataText)), 'GeoTIFF NoData tag is unavailable.');
  const nodata = Number(noDataText);
  assert(crsCode === expectedGrid.epsg, 'GeoTIFF CRS does not match the selected manifest grid.');
  assert(width === expectedGrid.width && height === expectedGrid.height, 'GeoTIFF dimensions do not match the selected manifest grid.');
  assert(transform.every((v, i) => Math.abs(v - expectedGrid.transform[i]) < 1e-8), 'GeoTIFF transform does not match the selected manifest grid.');
  assert(nodata === expectedGrid.nodata, 'GeoTIFF NoData value does not match the selected manifest.');

  const offsets = tags.get(273);
  const byteCounts = tags.get(279);
  const rowsPerStrip = one(tags, 278, 'RowsPerStrip');
  assert(offsets?.length && offsets.length === byteCounts?.length, 'TIFF strip index is incomplete.');
  assert(rowsPerStrip > 0 && offsets.length === Math.ceil(height / rowsPerStrip), 'TIFF strip layout is invalid.');

  const values = new Float32Array(width * height);
  const validMask = new Uint8Array(width * height);
  let startRow = 0;
  let validCount = 0;
  for (let strip = 0; strip < offsets.length; strip += 1) {
    const stripRows = Math.min(rowsPerStrip, height - startRow);
    const expectedBytes = stripRows * width * 4;
    const offset = offsets[strip];
    const count = byteCounts[strip];
    assert(Number.isInteger(offset) && Number.isInteger(count) && count > 0 && offset + count <= bytes.byteLength, 'TIFF strip is outside the file.');
    const decoded = await inflateStrip(bytes.subarray(offset, offset + count), expectedBytes);
    for (let row = 0; row < stripRows; row += 1) {
      const rowBytes = decoded.slice(row * width * 4, (row + 1) * width * 4);
      undoFloatPredictor(rowBytes, width, littleEndian);
      for (let col = 0; col < width; col += 1) {
        const pixel = (startRow + row) * width + col;
        const value = new DataView(rowBytes.buffer, rowBytes.byteOffset, rowBytes.byteLength).getFloat32(col * 4, littleEndian);
        values[pixel] = value;
        if (Number.isFinite(value) && value !== nodata) {
          validMask[pixel] = 1;
          validCount += 1;
        }
      }
    }
    startRow += stripRows;
  }

  return {
    width,
    height,
    crs: `EPSG:${crsCode}`,
    epsg: crsCode,
    transform,
    bounds: [transform[2], transform[5] - height * pixelScale[1], transform[2] + width * pixelScale[0], transform[5]],
    pixelSizeM: [pixelScale[0], pixelScale[1]],
    nodata,
    values,
    validMask,
    validCount,
    nodataCount: values.length - validCount,
    metadata: {
      compression: one(tags, 259, 'Compression'),
      predictor: one(tags, 317, 'Predictor'),
      bitsPerSample: one(tags, 258, 'BitsPerSample'),
      sampleFormat: one(tags, 339, 'SampleFormat'),
      areaOrPoint: tags.get(34735)?.some((value, index, all) => value === 1025 && all[index + 3] === 1) ? 'Area' : 'Unknown',
      gdalMetadata: tags.get(42112) ?? null,
    },
  };
}

/** UTM zone 44N to WGS 84; the selected A20 manifest declares EPSG:32644. */
export function utm44ToWgs84(easting, northing) {
  const a = 6378137;
  const eccentricitySquared = 0.0066943799901413165;
  const secondEccentricitySquared = eccentricitySquared / (1 - eccentricitySquared);
  const scale = 0.9996;
  const e1 = (1 - Math.sqrt(1 - eccentricitySquared)) / (1 + Math.sqrt(1 - eccentricitySquared));
  const x = easting - 500000;
  const meridian = northing / scale;
  const mu = meridian / (a * (1 - eccentricitySquared / 4 - 3 * eccentricitySquared ** 2 / 64 - 5 * eccentricitySquared ** 3 / 256));
  const phi1 = mu
    + (3 * e1 / 2 - 27 * e1 ** 3 / 32) * Math.sin(2 * mu)
    + (21 * e1 ** 2 / 16 - 55 * e1 ** 4 / 32) * Math.sin(4 * mu)
    + (151 * e1 ** 3 / 96) * Math.sin(6 * mu)
    + (1097 * e1 ** 4 / 512) * Math.sin(8 * mu);
  const sin = Math.sin(phi1);
  const cos = Math.cos(phi1);
  const tan = Math.tan(phi1);
  const n1 = a / Math.sqrt(1 - eccentricitySquared * sin ** 2);
  const t1 = tan ** 2;
  const c1 = secondEccentricitySquared * cos ** 2;
  const r1 = a * (1 - eccentricitySquared) / (1 - eccentricitySquared * sin ** 2) ** 1.5;
  const d = x / (n1 * scale);
  const latitude = phi1 - (n1 * tan / r1) * (
    d ** 2 / 2
    - (5 + 3 * t1 + 10 * c1 - 4 * c1 ** 2 - 9 * secondEccentricitySquared) * d ** 4 / 24
    + (61 + 90 * t1 + 298 * c1 + 45 * t1 ** 2 - 252 * secondEccentricitySquared - 3 * c1 ** 2) * d ** 6 / 720
  );
  const longitude = (81 * Math.PI / 180) + (
    d - (1 + 2 * t1 + c1) * d ** 3 / 6
    + (5 - 2 * c1 + 28 * t1 - 3 * c1 ** 2 + 8 * secondEccentricitySquared + 24 * t1 ** 2) * d ** 5 / 120
  ) / cos;
  return [longitude * 180 / Math.PI, latitude * 180 / Math.PI];
}

export function rasterToFeatures(raster) {
  const features = [];
  const [pixelWidth, , originX, , negativePixelHeight, originY] = raster.transform;
  const pixelHeight = -negativePixelHeight;
  for (let row = 0; row < raster.height; row += 1) {
    for (let col = 0; col < raster.width; col += 1) {
      const index = row * raster.width + col;
      if (!raster.validMask[index]) continue;
      const left = originX + col * pixelWidth;
      const right = left + pixelWidth;
      const top = originY - row * pixelHeight;
      const bottom = top - pixelHeight;
      const ring = [
        utm44ToWgs84(left, bottom), utm44ToWgs84(right, bottom),
        utm44ToWgs84(right, top), utm44ToWgs84(left, top), utm44ToWgs84(left, bottom),
      ];
      features.push({
        type: 'Feature',
        properties: { depth_m: raster.values[index], row, col },
        geometry: { type: 'Polygon', coordinates: [ring] },
      });
    }
  }
  return { type: 'FeatureCollection', features };
}

export function colorForDepth(value, min, max) {
  if (max <= min) return '#78c9d1';
  const ratio = Math.max(0, Math.min(1, (value - min) / (max - min)));
  const stops = [
    [0.0, [226, 240, 231]],
    [0.5, [77, 168, 182]],
    [1.0, [20, 83, 139]],
  ];
  const [low, high] = ratio <= 0.5 ? [stops[0], stops[1]] : [stops[1], stops[2]];
  const local = (ratio - low[0]) / (high[0] - low[0]);
  const rgb = low[1].map((channel, index) => Math.round(channel + (high[1][index] - channel) * local));
  return `#${rgb.map((channel) => channel.toString(16).padStart(2, '0')).join('')}`;
}

export function summarizeValidValues(raster) {
  let min = Infinity;
  let max = -Infinity;
  for (let i = 0; i < raster.values.length; i += 1) {
    if (!raster.validMask[i]) continue;
    min = Math.min(min, raster.values[i]);
    max = Math.max(max, raster.values[i]);
  }
  return { min: min === Infinity ? null : min, max: max === -Infinity ? null : max };
}
