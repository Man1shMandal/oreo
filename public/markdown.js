const esc = value => String(value).replace(/[&<>"']/g, char => ({
  '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;',
}[char]));

const pendingMath = new Set();
let mathListenerReady = false;

function typesetMath(root) {
  if (!root) return;
  const render = window.renderMathInElement;
  if (typeof render === 'function') {
    try {
      render(root, {
        delimiters: [
          { left: '$$', right: '$$', display: true },
          { left: '\\[', right: '\\]', display: true },
          { left: '\\(', right: '\\)', display: false },
          { left: '$', right: '$', display: false },
        ],
        throwOnError: false,
        strict: 'ignore',
      });
    } catch { /* Keep the source visible if a malformed formula defeats KaTeX. */ }
    return;
  }
  pendingMath.add(root);
  if (mathListenerReady) return;
  mathListenerReady = true;
  window.addEventListener('oreo-math-ready', () => {
    for (const node of pendingMath) {
      if (!node.isConnected) { pendingMath.delete(node); continue; }
      typesetMath(node);
      pendingMath.delete(node);
    }
  });
}

function markdown(source, sources = []) {
  const math = [];
  const codeSpans = [];
  const addMath = (tex, display) => {
    math.push({ tex, display });
    return `\uE000${math.length - 1}\uE001`;
  };
  const citation = index => {
    const source = sources[index - 1];
    if (!source || typeof source.url !== 'string') return null;
    try {
      const url = new URL(source.url);
      if (!['http:', 'https:'].includes(url.protocol)) return null;
      return `<a class="citation" href="${esc(url.href)}" target="_blank" rel="noopener noreferrer" title="${esc(source.title || url.href)}">[${index}]</a>`;
    } catch { return null; }
  };
  const inline = text => {
    text = text
      .replace(/\\\[([\s\S]+?)\\\]/g, (_, tex) => addMath(tex, true))
      .replace(/\\\(([\s\S]+?)\\\)/g, (_, tex) => addMath(tex, false))
      .replace(/(?<!\\)\$(?!\$)([^\n$]+?)(?<!\\)\$(?!\$)/g, (_, tex) =>
        /^\s|\s$/.test(tex) ? _ : addMath(tex, false));
    text = esc(text)
      .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
      .replace(/__(.+?)__/g, '<strong>$1</strong>')
      .replace(/~~(.+?)~~/g, '<del>$1</del>')
      .replace(/(^|[^*\w])\*(?!\s)(.+?)\*(?!\w)/g, '$1<em>$2</em>')
      .replace(/(^|[^_\w])_(?!\s)(.+?)_(?!\w)/g, '$1<em>$2</em>')
      .replace(/\[([^\]]+)\]\((https?:\/\/[^\s)]+)(?:\s+"([^"]*)")?\)/g, (_, label, href, title) =>
        `<a href="${href}" target="_blank" rel="noopener noreferrer"${title ? ` title="${title}"` : ''}>${label}</a>`)
      .replace(/(^|\s)(https?:\/\/[^\s<]+[^\s<.,;:!?)])/g, '$1<a href="$2" target="_blank" rel="noopener noreferrer">$2</a>')
      .replace(/\[(\d{1,3})\]/g, (match, value) => citation(Number(value)) || match);
    return text;
  };

  const formatBlocks = text => {
    const lines = text.split('\n'), out = [];
    let i = 0;
    const isDisplayMath = line => /^\uE000\d+\uE001$/.test(line.trim());
    const isBlockStart = line => /^( {0,3}#{1,6}\s|\s*>|\s*([-*+]\s+|\d+[.)]\s+)|\s*(```|~~~))/.test(line) ||
      /^\s*(?:[-*_]\s*){3,}$/.test(line) || isDisplayMath(line);
    while (i < lines.length) {
      const line = lines[i];
      if (!line.trim()) { i++; continue; }
      let match;
      if (isDisplayMath(line)) {
        out.push(line.trim()); i++; continue;
      }
      if ((match = line.match(/^ {0,3}(#{1,6})\s+(.*?)(?:\s+#+\s*)?$/))) {
        const level = match[1].length;
        out.push(`<h${level}>${inline(match[2])}</h${level}>`); i++; continue;
      }
      if (/^\s*(?:[-*_]\s*){3,}$/.test(line)) { out.push('<hr>'); i++; continue; }
      if (/^\s*>/.test(line)) {
        const quote = [];
        while (i < lines.length && /^\s*>/.test(lines[i])) quote.push(lines[i++].replace(/^\s*>\s?/, ''));
        out.push(`<blockquote>${formatBlocks(quote.join('\n'))}</blockquote>`); continue;
      }
      if (/^\s*\|.*\|\s*$/.test(line) && /^\s*\|?\s*:?-{3,}:?\s*(?:\|\s*:?-{3,}:?\s*)+\|?\s*$/.test(lines[i + 1] || '')) {
        const cells = row => row.trim().replace(/^\||\|$/g, '').split('|').map(cell => inline(cell.trim()));
        const headers = cells(line); i += 2;
        const rows = [];
        while (i < lines.length && /^\s*\|.*\|\s*$/.test(lines[i])) rows.push(cells(lines[i++]));
        out.push(`<div class="table-scroll"><table><thead><tr>${headers.map(cell => `<th>${cell}</th>`).join('')}</tr></thead><tbody>${rows.map(row =>
          `<tr>${headers.map((_, index) => `<td>${row[index] || ''}</td>`).join('')}</tr>`).join('')}</tbody></table></div>`);
        continue;
      }
      if ((match = line.match(/^(\s*)([-*+]|\d+[.)])\s+(.*)/))) {
        const root = { ordered: /^\d/.test(match[2]), items: [] }, stack = [{ indent: match[1].length, list: root }];
        while (i < lines.length) {
          const item = lines[i].match(/^(\s*)([-*+]|\d+[.)])\s+(.*)/);
          if (!item) break;
          const indent = item[1].length, ordered = /^\d/.test(item[2]);
          if (indent < stack[0].indent) break;
          while (stack.length > 1 && indent < stack.at(-1).indent) stack.pop();
          if (indent > stack.at(-1).indent) {
            const parent = stack.at(-1).list.items.at(-1);
            if (!parent) break;
            const child = { ordered, items: [] };
            parent.children.push(child);
            stack.push({ indent, list: child });
          } else if (ordered !== stack.at(-1).list.ordered) break;
          stack.at(-1).list.items.push({ text: item[3], children: [] });
          i++;
        }
        const renderList = list => {
          const tag = list.ordered ? 'ol' : 'ul';
          return `<${tag}>${list.items.map(item => {
            const task = item.text.match(/^\[([ xX])\]\s+(.*)/);
            const content = task ? `<input type="checkbox" disabled${task[1].toLowerCase() === 'x' ? ' checked' : ''}> ${inline(task[2])}` : inline(item.text);
            return `<li>${content}${item.children.map(renderList).join('')}</li>`;
          }).join('')}</${tag}>`;
        };
        out.push(renderList(root)); continue;
      }
      const paragraph = [];
      while (i < lines.length && lines[i].trim() && (paragraph.length === 0 || !isBlockStart(lines[i]))) paragraph.push(lines[i++]);
      if (!paragraph.length) paragraph.push(lines[i++]);
      out.push(`<p>${paragraph.map(inline).join('<br>')}</p>`);
    }
    return out.join('');
  };

  let html = '', plain = [];
  const flush = () => {
    if (!plain.length) return;
    const text = plain.join('\n')
      .replace(/`([^`\n]+)`/g, (_, value) => {
        codeSpans.push(value);
        return `\uE100${codeSpans.length - 1}\uE101`;
      })
      .replace(/\$\$([\s\S]+?)\$\$/g, (_, tex) => `\n${addMath(tex, true)}\n`)
      .replace(/\\\[([\s\S]+?)\\\]/g, (_, tex) => `\n${addMath(tex, true)}\n`);
    html += formatBlocks(text);
    plain = [];
  };
  const lines = String(source ?? '').replace(/\r\n?/g, '\n').split('\n');
  for (let i = 0; i < lines.length;) {
    const fence = lines[i].match(/^ {0,3}(`{3,}|~{3,})\s*([\w+-]*)[^\n]*$/);
    if (!fence) { plain.push(lines[i++]); continue; }
    flush();
    const marker = fence[1], language = fence[2];
    i++;
    const code = [];
    while (i < lines.length && !new RegExp(`^ {0,3}${marker[0]}{${marker.length},}\\s*$`).test(lines[i])) code.push(lines[i++]);
    if (i < lines.length) i++;
    const languageClass = /^[\w+-]+$/.test(language) ? ` class="language-${esc(language)}"` : '';
    html += `<pre><code${languageClass}>${esc(code.join('\n'))}</code><button class="copy" type="button">Copy</button></pre>`;
  }
  flush();
  html = html.replace(/\uE100(\d+)\uE101/g, (_, rawIndex) => `<code>${esc(codeSpans[Number(rawIndex)])}</code>`);
  html = html.replace(/\uE000(\d+)\uE001/g, (_, rawIndex) => {
    const item = math[Number(rawIndex)];
    if (!item) return '';
    const delimiters = item.display ? ['\\[', '\\]'] : ['\\(', '\\)'];
    return `<span class="${item.display ? 'math-display' : 'math-inline'}">${delimiters[0]}${esc(item.tex)}${delimiters[1]}</span>`;
  });
  return html;
}

export { markdown, typesetMath };
