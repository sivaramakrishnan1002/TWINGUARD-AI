import assert from 'node:assert/strict';
import path from 'node:path';
import test from 'node:test';
import { createRequire } from 'node:module';
import { fileURLToPath } from 'node:url';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../../..');
const frontendRoot = path.join(root, 'frontend');
const require = createRequire(path.join(frontendRoot, 'package.json'));
const { createServer } = require('vite');

const places = [
  { name: 'Royapuram', alt: ['ராயபுரம்'], type: 'suburb', lon: 80.2937, lat: 13.1137, ward_id: 51, zone: 'V Royapuram', rank: 2 },
  { name: 'Thiruvottiyur', alt: [], type: 'town', lon: 80.3014, lat: 13.1643, ward_id: 4, zone: 'I Thiruvottiyur', rank: 1 },
  { name: 'Seva Nagar Velachery', alt: [], type: 'neighbourhood', lon: 80.22, lat: 12.98, ward_id: 177, zone: 'XIII Adyar', rank: 3 },
];
const wards = [{ ward_id: 178, name: 'Ward 178', zone: 'XIII Adyar', lon: 80.21, lat: 12.97, bbox: [80.2, 12.96, 80.22, 12.98] }];

test('area search finds localities, wards and near-miss spellings', async () => {
  const vite = await createServer({ configFile: path.join(frontendRoot, 'vite.config.ts'), root: frontendRoot, appType: 'custom', logLevel: 'silent', server: { middlewareMode: true, hmr: false, watch: { ignored: () => true } }, envDir: path.join(frontendRoot, 'node_modules/.tg-test-env') });
  try {
    const { buildIndex } = await vite.ssrLoadModule('/src/ui/product/search.ts');
    const search = buildIndex(places, wards, [{ name: 'Velachery', lon: 80.2209, lat: 12.9815 }]);
    assert.equal(search('royapuram')[0].label, 'Royapuram');
    assert.equal(search('Roya')[0].label, 'Royapuram', 'prefix match');
    assert.equal(search('ராயபுரம்')[0].label, 'Royapuram', 'Tamil alt name');
    assert.equal(search('ward 178')[0].label, 'Ward 178');
    assert.equal(search('178')[0].kind, 'ward');
    assert.equal(search('tiruvottiyur')[0].label, 'Thiruvottiyur', 'th/t folding');
    assert.equal(search('velachery')[0].label, 'Velachery', 'curated name ranks first');
    assert.deepEqual(search('zzzz'), []);
  } finally {
    await vite.close();
  }
});
