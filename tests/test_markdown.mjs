import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';

const source = await readFile(new URL('../public/markdown.js', import.meta.url), 'utf8');
const { markdown } = await import(`data:text/javascript;base64,${Buffer.from(source).toString('base64')}`);

const sources = [
  { title: 'First source', url: 'https://example.com/one' },
  { title: 'Second source', url: 'https://example.org/two' },
];

const physics = markdown(`## Governing Physics

In the solid — Fourier's Law:
$$
\\nabla \\cdot (k_s \\nabla T) + \\dot{q} = \\rho_s c_s \\frac{\\partial T}{\\partial t}
$$

At the interface: $T_{solid} = T_{fluid}$. [1][2]`, sources);
assert.match(physics, /<h2>Governing Physics<\/h2>/);
assert.match(physics, /class="math-display"/);
assert.match(physics, /\\nabla \\cdot/);
assert.match(physics, /class="math-inline"/);
assert.match(physics, /href="https:\/\/example\.com\/one"[^>]*>\[1\]<\/a>/);
assert.match(physics, /href="https:\/\/example\.org\/two"[^>]*>\[2\]<\/a>/);

const features = markdown(`### Details

- **Bold** and *italic* and ~~removed~~
- \`inline code\`
- Literal formula source: \`$$x + y$$\`
  - Nested detail
- [x] Finished item
- [ ] Open item

| Name | Value |
| --- | ---: |
| Heat | 42 |

\`\`\`js
const raw = '<img src=x onerror=alert(1)> $$not math$$';
\`\`\`

<img src=x onerror=alert(1)>`);
assert.match(features, /<h3>Details<\/h3>/);
assert.match(features, /<strong>Bold<\/strong>/);
assert.match(features, /<em>italic<\/em>/);
assert.match(features, /<del>removed<\/del>/);
assert.match(features, /<code>inline code<\/code>/);
assert.match(features, /<code>\$\$x \+ y\$\$<\/code>/);
assert.match(features, /<li>Nested detail<\/li>/);
assert.match(features, /type="checkbox" disabled checked/);
assert.match(features, /type="checkbox" disabled>/);
assert.match(features, /class="table-scroll"><table>/);
assert.match(features, /class="language-js"/);
assert.match(features, /&lt;img src=x onerror=alert\(1\)&gt;/);
assert.doesNotMatch(features, /<img src=x/);
assert.doesNotMatch(features, /math-display/);

assert.doesNotMatch(markdown('See [1].', [{ url: 'javascript:alert(1)' }]), /href=/);
console.log('Markdown formatting checks passed.');
