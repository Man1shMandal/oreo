// Keep the approved illustration intact; animate clipped copies of its features.
class OreoMascot extends HTMLElement {
  constructor() {
    super();
    const root = this.attachShadow({ mode: 'open' });
    const portrait = '<image href="/mascot-cookie.webp" width="1254" height="1254"/>';
    // Cookie texture from between the eyes fills the space behind a closing eye.
    const eye = (name, x, y, rx, ry) => `
      <defs>
        <clipPath id="${name}"><ellipse cx="${x}" cy="${y}" rx="${rx}" ry="${ry}"/></clipPath>
        <pattern id="${name}-crumb" patternUnits="userSpaceOnUse" width="1254" height="1254">
          <image href="/mascot-cookie.webp" x="${x - 1490}" y="${y - 1130}" width="2508" height="2508"/>
        </pattern>
      </defs>
      <ellipse cx="${x}" cy="${y}" rx="${rx}" ry="${ry}" fill="url(#${name}-crumb)"/>
      <g transform="translate(${x} ${y})"><g class="eye">
        <g transform="translate(${-x} ${-y})" clip-path="url(#${name})">${portrait}</g>
      </g></g>
      <path class="closed-eye" d="M${x-rx*.7} ${y} Q${x} ${y+22} ${x+rx*.7} ${y-6}"/>`;
    root.innerHTML = `<style>
      :host { display:block; width:100%; height:100%; }
      svg { position:absolute; inset:0; display:block; width:100%; height:100%; overflow:visible; }
      .portrait { display:block; width:100%; height:100%; object-fit:contain; }
      .cookie { position:relative; width:100%; height:100%; transform-origin:50% 65%; animation:float 5s ease-in-out infinite; }
      .eye { animation:blink 5.7s ease-in-out infinite; }
      .closed-eye { fill:none; stroke:#211511; stroke-width:9; stroke-linecap:round;
        opacity:0; animation:lid 5.7s ease-in-out infinite; }
      .smile { transform-origin:752px 680px; animation:smile 8s ease-in-out infinite;
        transition:transform .35s ease; }
      :host(.attentive) .cookie { animation:listen 3s ease-in-out infinite; }
      :host(.attentive) .smile, :host(.celebrate) .smile { animation:none; transform:scale(1.08,1.2); }
      :host(.working) .cookie { animation:think 2.8s ease-in-out infinite; }
      :host(.celebrate) .cookie { animation:happy .65s ease-in-out 2; }
      @keyframes blink { 0%,42%,46%,100% { transform:scaleY(1); } 44% { transform:scaleY(.025); } }
      @keyframes lid { 0%,42%,46%,100% { opacity:0; } 44% { opacity:1; } }
      @keyframes smile { 0%,55%,85%,100% { transform:scale(1); } 65%,75% { transform:scale(1.06,1.16); } }
      @keyframes float { 0%,100% { transform:translateY(0) rotate(-1deg); } 50% { transform:translateY(-13px) rotate(1deg); } }
      @keyframes listen { 0%,100% { transform:rotate(-3deg); } 50% { transform:translateY(-8px) rotate(-1deg); } }
      @keyframes think { 0%,100% { transform:rotate(-3deg); } 50% { transform:rotate(3deg) translateY(-10px); } }
      @keyframes happy { 0%,100% { transform:translateY(0); } 50% { transform:translateY(-32px) rotate(5deg); } }
      @media (prefers-reduced-motion: reduce) {
        .cookie, .eye, .closed-eye, .smile { animation:none!important; transition:none!important; transform:none!important; }
      }
    </style><div class="cookie"><img class="portrait" src="/mascot-cookie.webp" alt="" width="1254" height="1254"><svg viewBox="0 0 1254 1254" aria-hidden="true" focusable="false">
      <defs><clipPath id="mouth"><rect x="653" y="646" width="207" height="68" rx="28"/></clipPath></defs>
        ${eye('left', 603, 565, 92, 96)}
        ${eye('right', 899, 551, 77, 96)}
        <g class="smile"><g clip-path="url(#mouth)">${portrait}</g></g>
    </svg></div>`;
  }
}

if (!customElements.get('oreo-mascot')) customElements.define('oreo-mascot', OreoMascot);
