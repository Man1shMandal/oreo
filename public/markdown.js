const esc = s => String(s).replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
function inline(s) {
  const codes = [];
  s = s.replace(/`([^`\n]+)`/g, (_, c) => { codes.push(c); return `\u0000${codes.length - 1}\u0000`; });
  s = esc(s)
    .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
    .replace(/(^|[^*\w])\*(?!\s)(.+?)\*(?!\w)/g, "$1<em>$2</em>")
    .replace(/\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)/g, '<a href="$2" target="_blank" rel="noopener">$1</a>')
    .replace(/(^|\s)(https?:\/\/[^\s<]+[^\s<.,;:!?)])/g, '$1<a href="$2" target="_blank" rel="noopener">$2</a>');
  return s.replace(/\u0000(\d+)\u0000/g, (_, i) => `<code>${esc(codes[i])}</code>`);
}

function blocks(text) {
  const lines = text.split("\n"), out = [];
  let i = 0;
  while (i < lines.length) {
    const l = lines[i];
    if (!l.trim()) { i++; continue; }
    let m;
    if ((m = l.match(/^(#{1,4})\s+(.*)/))) { out.push(`<h${m[1].length}>${inline(m[2])}</h${m[1].length}>`); i++; continue; }
    if (/^(-{3,}|\*{3,})\s*$/.test(l)) { out.push("<hr>"); i++; continue; }
    if (/^\s*>/.test(l)) {
      const q = []; while (i < lines.length && /^\s*>/.test(lines[i])) q.push(lines[i++].replace(/^\s*>\s?/, ""));
      out.push(`<blockquote>${blocks(q.join("\n"))}</blockquote>`); continue;
    }
    if (/^\s*\|.*\|\s*$/.test(l) && /^\s*\|[\s:|-]+\|\s*$/.test(lines[i + 1] || "")) {
      const row = r => r.trim().replace(/^\||\|$/g, "").split("|").map(c => inline(c.trim()));
      const head = row(l); i += 2; const body = [];
      while (i < lines.length && /^\s*\|.*\|\s*$/.test(lines[i])) body.push(row(lines[i++]));
      out.push(`<table><tr>${head.map(c => `<th>${c}</th>`).join("")}</tr>` +
               body.map(r => `<tr>${r.map(c => `<td>${c}</td>`).join("")}</tr>`).join("") + "</table>");
      continue;
    }
    if ((m = l.match(/^\s*([-*+]|\d+[.)])\s+/))) {
      const ordered = /\d/.test(m[1]), items = [];
      while (i < lines.length && lines[i].trim()) {
        const lm = lines[i].match(/^\s*([-*+]|\d+[.)])\s+(.*)/);
        if (lm) items.push(lm[2]); else items[items.length - 1] += " " + lines[i].trim();
        i++;
      }
      const tag = ordered ? "ol" : "ul";
      out.push(`<${tag}>${items.map(x => `<li>${inline(x)}</li>`).join("")}</${tag}>`); continue;
    }
    const p = [];
    while (i < lines.length && lines[i].trim() && !/^(#{1,4}\s|\s*>|\s*([-*+]|\d+[.)])\s)/.test(lines[i])) p.push(lines[i++]);
    if (!p.length) p.push(lines[i++]);
    out.push(`<p>${p.map(inline).join("<br>")}</p>`);
  }
  return out.join("");
}

function markdown(text) {
  let html = "", inCode = false;
  // split with a capture group alternates: text, lang, code-and-rest, lang, ...
  const segs = text.split(/(^```[^\n]*$)/m);
  for (const seg of segs) {
    if (/^```/.test(seg)) { inCode = !inCode; html += inCode ? "<pre><code>" : "</code><button class='copy' type='button'>Copy</button></pre>"; continue; }
    html += inCode ? esc(seg.replace(/^\n/, "").replace(/\n$/, "")) : blocks(seg);
  }
  if (inCode) html += "</code><button class='copy' type='button'>Copy</button></pre>";
  return html;
}


export { markdown };
