import assert from 'node:assert/strict';
import path from 'node:path';
import test from 'node:test';
import { createRequire } from 'node:module';
import { fileURLToPath } from 'node:url';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../../..');
const frontendRoot = path.join(root, 'frontend');
const require = createRequire(path.join(frontendRoot, 'package.json'));
const React = require('react');
const { renderToStaticMarkup } = require('react-dom/server');
const { createServer } = require('vite');

async function withUi(callback) {
  const server = await createServer({ configFile: path.join(frontendRoot, 'vite.config.ts'), root: frontendRoot, appType: 'custom', server: { middlewareMode: true }, define: { 'import.meta.env.VITE_GATE_G0_STATUS': JSON.stringify('unknown') } });
  try {
    const ui = await server.ssrLoadModule('/src/ui/product/ProductExperience.tsx');
    const flow = await server.ssrLoadModule('/src/ui/product/professor-refinement/guided-flow.ts');
    await callback({ ui, flow });
  } finally {
    await server.close();
  }
}

test('guided demo flow stays in the five registered local walkthrough steps', async () => {
  await withUi(async ({ ui, flow }) => {
    assert.deepEqual(flow.professorDemoFlow.map(({ id, section }) => [id, section]), [
      ['scenario', 'overview'], ['time-steps', 'twin'], ['impacts', 'impacts'], ['response', 'response'], ['what-if', 'what-if'],
    ]);
    assert.equal(flow.activeProfessorStep('reservoirs'), null);
    assert.equal(flow.fixtureBarHeight(0, [0, 0, 0, 0]), '0px', 'known zero stays visually zero');
    assert.ok(Number.parseFloat(flow.fixtureBarHeight(50, [0, 25, 50])) > Number.parseFloat(flow.fixtureBarHeight(25, [0, 25, 50])));
    const actions = [];
    for (const step of flow.professorDemoFlow) flow.activateProfessorStep(step.id, {
      navigate: (section) => actions.push(`navigate:${section}`),
      focusScenario: () => actions.push('focus:scenario'),
    });
    assert.deepEqual(actions, [
      'navigate:overview', 'focus:scenario', 'navigate:twin', 'navigate:impacts', 'navigate:response', 'navigate:what-if',
    ]);

    for (const [section, stepId] of [['overview', 'scenario'], ['twin', 'time-steps'], ['impacts', 'impacts'], ['response', 'response'], ['what-if', 'what-if']]) {
      const markup = renderToStaticMarkup(React.createElement(ui.ProductExperience, { initialSection: section }));
      assert.match(markup, /aria-label="Guided demo flow"/);
      assert.match(markup, new RegExp(`aria-current="step"[^>]*`));
      assert.match(markup, new RegExp(`data-flow-step="${stepId}"`));
    }
  });
});

test('walkthrough preserves demo-only labels, A21 pending state, and distinct unknown coverage', async () => {
  await withUi(async ({ ui }) => {
    const overview = renderToStaticMarkup(React.createElement(ui.ProductExperience, { initialSection: 'overview' }));
    assert.match(overview, /DEMO \/ SIMULATED/);
    assert.match(overview, /FICTIONAL SCENE · NOT GEOREFERENCED/);
    assert.match(overview, /ILLUSTRATIVE WATER/);
    assert.match(overview, /no measured depth, flood extent, building impact, or hydraulic result/i);
    assert.match(overview, /Select demo scenario/);
    const response = renderToStaticMarkup(React.createElement(ui.ProductExperience, { initialSection: 'response' }));
    assert.match(response, /UPCOMING A21 ANALYSIS · NOT CONNECTED/);
    assert.match(response, /Unknown · verify/);
    assert.match(response, /Reachability does not establish flood access or safety/);
    const whatIf = renderToStaticMarkup(React.createElement(ui.ProductExperience, { initialSection: 'what-if' }));
    assert.match(whatIf, /WAITING FOR A21/);
    assert.match(whatIf, /A21 is still in progress\. Its outputs remain unavailable here until the task completes and its evidence is reviewed\./);
    const system = renderToStaticMarkup(React.createElement(ui.ProductExperience, { initialSection: 'system' }));
    for (const state of ['Unknown', 'Unavailable', 'Known zero', 'Explicit dry fixture', 'NoData']) assert.ok(system.includes(state), `${state} remains distinct`);
  });
});

test('reservoir fixture chart has readable synthetic values without asserting dates', async () => {
  await withUi(async ({ ui }) => {
    const markup = renderToStaticMarkup(React.createElement(ui.ProductExperience, { initialSection: 'reservoirs' }));
    assert.match(markup, /Synthetic storage fixture sequence:.*dates unavailable/);
    assert.match(markup, /Fixture sequence · dates unavailable/);
    assert.match(markup, /DEMO values · no source date or operational status/);
    assert.match(markup, /Synthetic storage fixture sequence: [0-9, ]+ mcft; dates unavailable/);
  });
});

test('walkthrough controls retain visible keyboard focus and responsive overflow', async () => {
  const { readFile } = await import('node:fs/promises');
  const css = await readFile(path.join(frontendRoot, 'src/ui/product/product.css'), 'utf8');
  assert.match(css, /\.tg-product__guided-flow button\[aria-current="step"\]/);
  assert.match(css, /\.tg-product__guided-flow ol\s*\{[^}]*grid-template-columns:\s*repeat\(5,minmax\(0,1fr\)\)/s);
  assert.match(css, /\.tg-product__guided-flow ol\s*\{[^}]*overflow-x:\s*auto/s);
  assert.match(css, /\.tg-product__guided-flow button\s*\{[^}]*min-height:\s*43px/s);
  assert.match(css, /\.tg-product :focus-visible/);
  assert.match(css, /prefers-reduced-motion:\s*reduce/);
});
