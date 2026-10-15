const artwork = `
<svg class="mascot" viewBox="0 0 120 120" role="presentation" focusable="false" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <linearGradient id="hair" x2=".8" y2="1"><stop stop-color="#363354"/><stop offset=".5" stop-color="#797298"/><stop offset="1" stop-color="#c6b6d9"/></linearGradient>
    <linearGradient id="skin" x2="0" y2="1"><stop stop-color="#fff0e6"/><stop offset="1" stop-color="#efc5bd"/></linearGradient>
    <linearGradient id="iris" x2="0" y2="1"><stop stop-color="#382c68"/><stop offset=".6" stop-color="#9d84cf"/><stop offset="1" stop-color="#d8c6f4"/></linearGradient>
  </defs>
  <g class="eye-pair">
    <path d="M24 94C12 64 15 25 40 14C67 0 96 18 100 47L103 99L82 110H35Z" fill="url(#hair)" stroke="#39344d" stroke-width="1.4"/>
    <path d="M24 118Q26 96 47 94H74Q95 98 97 118" fill="#282838"/>
    <path d="M51 84V97L60 105L70 97V84" fill="url(#skin)"/>
    <path d="M46 95L60 105L52 116L39 99M74 95L60 105L68 116L81 99" fill="#eee8f5"/>
    <path d="M57 105L52 115L60 112L68 115L63 105" fill="#9a83bc"/>
    <path d="M31 46Q27 77 42 87Q60 103 79 85Q91 73 88 44Q62 24 31 46Z" fill="url(#skin)" stroke="#c7989b" stroke-width=".7"/>
    <path d="M32 65Q25 57 27 70Q28 77 35 77M87 65Q96 57 93 70Q92 77 85 77" fill="#efc5bd"/>
    <path d="M38 54Q45 50 51 54M68 54Q76 50 82 54" fill="none" stroke="#79617b" stroke-width="1.4" stroke-linecap="round"/>
    <g class="eye left-eye">
      <path d="M35 63Q43 55 53 63L51 71Q42 76 36 69Z" fill="#fff9fa"/>
      <ellipse class="iris" cx="45" cy="65" rx="6" ry="8" fill="url(#iris)"/>
      <ellipse cx="45" cy="64" rx="2.8" ry="5" fill="#302440"/><circle cx="43" cy="61" r="2.4" fill="white"/><circle cx="48" cy="68" r="1.2" fill="white"/>
      <path d="M33 60L36 63Q43 56 53 63M34 64L32 62" fill="none" stroke="#372c44" stroke-width="2.3" stroke-linecap="round"/>
    </g>
    <g class="eye right-eye">
      <path d="M67 63Q77 55 85 63L84 69Q78 76 69 71Z" fill="#fff9fa"/>
      <ellipse class="iris" cx="75" cy="65" rx="6" ry="8" fill="url(#iris)"/>
      <ellipse cx="75" cy="64" rx="2.8" ry="5" fill="#302440"/><circle cx="73" cy="61" r="2.4" fill="white"/><circle cx="78" cy="68" r="1.2" fill="white"/>
      <path d="M67 63Q77 56 84 63L87 60M86 64L88 62" fill="none" stroke="#372c44" stroke-width="2.3" stroke-linecap="round"/>
    </g>
    <ellipse cx="39" cy="77" rx="6" ry="2.7" fill="#e99ba9" opacity=".45"/><ellipse cx="81" cy="77" rx="6" ry="2.7" fill="#e99ba9" opacity=".45"/>
    <path d="M60 70L58 77H61" fill="none" stroke="#cf9f9e" stroke-width="1" stroke-linecap="round"/>
    <path class="smile" d="M55 83Q60 87 65 83" fill="none" stroke="#a9617a" stroke-width="1.5" stroke-linecap="round"/>
    <path d="M25 61Q20 30 42 20Q73 5 90 34L92 68Q82 54 76 32Q61 49 43 51L55 34Q39 50 25 61Z" fill="url(#hair)"/>
    <path d="M35 30Q52 15 72 22M29 43Q32 36 36 33M81 37L86 52" fill="none" stroke="#d6c8eb" stroke-opacity=".55" stroke-width="2" stroke-linecap="round"/>
    <path d="M27 55Q22 82 34 102L40 95Q31 76 36 52M88 49Q99 79 86 104L80 96Q89 77 83 48" fill="url(#hair)"/>
    <path d="M83 42L89 38L94 44L88 49Z" fill="#e8d9ff"/><circle cx="88" cy="44" r="2" fill="#b79bd4"/>
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
