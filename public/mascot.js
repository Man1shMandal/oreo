// One shared portrait in the local and hosted app.
class OreoMascot extends HTMLElement {
  constructor() {
    super();
    const root = this.attachShadow({ mode: 'open' });
    root.innerHTML = `<style>
      :host { display:block; width:100%; height:100%; overflow:visible; }
      .portrait { display:block; width:100%; height:100%; object-fit:contain;
        transform-origin:50% 80%; animation:breathe 5s ease-in-out infinite;
        transition:filter .3s ease; }
      :host(.attentive) .portrait { filter:brightness(1.08); }
      :host(.working) .portrait { animation:thinking 3s ease-in-out infinite; }
      :host(.celebrate) .portrait { animation:celebrate .65s ease-in-out 2; }
      @keyframes breathe { 0%,100% { transform:translateY(0) } 50% { transform:translateY(-1px) } }
      @keyframes thinking { 0%,100% { transform:rotate(-1deg) } 50% { transform:rotate(1deg) translateY(-1px) } }
      @keyframes celebrate { 0%,100% { transform:translateY(0) } 50% { transform:translateY(-3px) rotate(2deg) } }
      @media (prefers-reduced-motion: reduce) { .portrait { animation:none!important; transition:none; } }
    </style><img class="portrait" src="/mascot-anime.webp" alt="" decoding="async" width="512" height="512">`;
  }
}

if (!customElements.get('oreo-mascot')) customElements.define('oreo-mascot', OreoMascot);
