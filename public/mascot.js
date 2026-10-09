const artwork = `
<svg class="mascot" viewBox="0 0 120 76" role="presentation" focusable="false" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <linearGradient id="iris" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="#9ce8f5"/><stop offset=".36" stop-color="#4baedc"/><stop offset="1" stop-color="#5367c9"/>
    </linearGradient>
    <linearGradient id="lid" x1="0" y1="0" x2="0" y2="1">
      <stop stop-color="#eaf9ff"/><stop offset="1" stop-color="#c9e8f3"/>
    </linearGradient>
    <clipPath id="left-eye"><path d="M8 36C17 20 34 18 52 34C42 49 23 52 8 36Z"/></clipPath>
    <clipPath id="right-eye"><path d="M68 34C86 18 103 20 112 36C97 52 78 49 68 34Z"/></clipPath>
  </defs>
  <g class="eye-pair">
    <g class="eye left-eye">
      <path class="white" d="M8 36C17 20 34 18 52 34C42 49 23 52 8 36Z" fill="url(#lid)"/>
      <g clip-path="url(#left-eye)"><circle class="iris" cx="31" cy="36" r="12" fill="url(#iris)"/><circle class="pupil" cx="32" cy="35" r="6.1" fill="#17234f"/><ellipse cx="27" cy="30" rx="3.5" ry="2.4" fill="#fff" opacity=".96"/><circle cx="37" cy="40" r="1.8" fill="#aaf6f1"/><circle cx="23" cy="39" r="1.4" fill="#8ce4ef"/></g>
      <path class="upper-lid" d="M7 36C16 19 35 16 54 33C41 24 24 24 8 39Z" fill="#172044"/>
      <path d="M17 26C24 20 36 20 44 25" fill="none" stroke="#fff" stroke-opacity=".48" stroke-width="1.2" stroke-linecap="round"/>
      <path d="M14 45l-3 3m8-1-2 4" fill="none" stroke="#28345d" stroke-width="1.7" stroke-linecap="round"/>
    </g>
    <g class="eye right-eye">
      <path class="white" d="M68 34C86 18 103 20 112 36C97 52 78 49 68 34Z" fill="url(#lid)"/>
      <g clip-path="url(#right-eye)"><circle class="iris" cx="89" cy="36" r="12" fill="url(#iris)"/><circle class="pupil" cx="88" cy="35" r="6.1" fill="#17234f"/><ellipse cx="84" cy="30" rx="3.5" ry="2.4" fill="#fff" opacity=".96"/><circle cx="94" cy="40" r="1.8" fill="#aaf6f1"/><circle cx="81" cy="39" r="1.4" fill="#8ce4ef"/></g>
      <path class="upper-lid" d="M66 33C85 16 104 19 113 36L112 39C96 24 79 24 66 33Z" fill="#172044"/>
      <path d="M76 25C84 20 96 20 103 26" fill="none" stroke="#fff" stroke-opacity=".48" stroke-width="1.2" stroke-linecap="round"/>
      <path d="M106 45l3 3m-8-1 2 4" fill="none" stroke="#28345d" stroke-width="1.7" stroke-linecap="round"/>
    </g>
    <path class="smile" d="M53 59Q60 65 67 59" fill="none" stroke="#c7d9ff" stroke-width="2.2" stroke-linecap="round"/>
    <path class="smile-glint" d="M56 59Q60 62 64 59" fill="none" stroke="#fff" stroke-opacity=".8" stroke-width="1" stroke-linecap="round"/>
  </g>
</svg>`;

class OreoMascot extends HTMLElement {
  constructor() {
    super();
    const root = this.attachShadow({ mode: 'open' });
    root.innerHTML = `<style>
      :host { display:block; width:100%; height:100%; overflow:visible; }
      .mascot { display:block; width:100%; height:100%; overflow:visible; }
      .eye-pair { transform-box:fill-box; transform-origin:center; animation: float 4.2s ease-in-out infinite; }
      .eye { transform-box:fill-box; transform-origin:center; animation: blink 6.3s ease-in-out infinite; }
      .right-eye { animation-delay:.12s; }
      .iris { transform-box:fill-box; transform-origin:center; animation: glance 8s ease-in-out infinite; }
      .smile { animation: smile 4.2s ease-in-out infinite; transform-origin:center; }
      :host(.attentive) .iris { animation: focus 1.5s ease-in-out infinite; }
      :host(.working) .iris { animation: search 2.8s ease-in-out infinite; }
      :host(.working) .right-eye { animation-duration:5.4s; }
      :host(.celebrate) .eye { animation: happy-blink .65s ease-in-out 2; }
      :host(.celebrate) .eye-pair { animation: bounce .48s cubic-bezier(.2,.8,.2,1) 3; }
      :host(.celebrate) .smile { stroke-width:3; }
      @keyframes float { 0%,100% { transform:translateY(0) } 50% { transform:translateY(-1.5px) } }
      @keyframes blink { 0%,43%,47%,100% { transform:scaleY(1) } 45% { transform:scaleY(.12) } }
      @keyframes happy-blink { 0%,100% { transform:scaleY(1) } 50% { transform:scaleY(.18) } }
      @keyframes glance { 0%,20%,65%,100% { transform:translateX(0) } 28%,58% { transform:translateX(1.8px) } }
      @keyframes focus { 0%,100% { transform:translateY(0) } 50% { transform:translateY(-1px) } }
      @keyframes search { 0%,100% { transform:translateX(-1.5px) } 50% { transform:translateX(1.5px) } }
      @keyframes smile { 0%,100% { transform:scaleX(1) } 50% { transform:scaleX(1.12) } }
      @keyframes bounce { 0%,100% { transform:translateY(0) scale(1) } 45% { transform:translateY(-3px) scale(1.04) } }
      @media (prefers-reduced-motion: reduce) { *,*::before,*::after { animation:none!important; } }
    </style>${artwork}`;
  }
}

if (!customElements.get('oreo-mascot')) customElements.define('oreo-mascot', OreoMascot);
