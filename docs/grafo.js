// Grafo da skill no branding. Os dados vêm de grafo-dados.js, gerado pelo graphify a partir do próprio repositório.
(function () {
  const G = window.GRAFO;
  const caixa = document.getElementById('rede');
  if (!G || !window.vis || !caixa) return;
  document.getElementById('g-nos').textContent = G.nos.length;
  document.getElementById('g-fios').textContent = G.fios.length;

  const corDe = Object.fromEntries(G.grupos.map(g => [g.id, g.cor]));
  const maiorGrau = Math.max(...G.nos.map(n => n.grau));
  // No desenho geral vão os nomes em português; as funções aparecem ao passar o mouse.
  const rotuloFixo = n => (n.tipo !== 'code' && n.grau >= 8) || n.grau >= maiorGrau * 0.5;

  const nos = new vis.DataSet(G.nos.map(n => ({
    id: n.id,
    x: n.x,
    y: n.y,
    title: n.rotulo,
    label: rotuloFixo(n) ? n.rotulo : undefined,
    value: n.grau,
    color: { background: corDe[n.grupo], border: corDe[n.grupo], highlight: { background: '#ff3350', border: '#f2ede4' }, hover: { background: '#ff3350', border: '#f2ede4' } },
  })));
  const fios = new vis.DataSet(G.fios.map((f, i) => ({ id: i, from: f.de, to: f.para })));

  const rede = new vis.Network(caixa, { nodes: nos, edges: fios }, {
    nodes: { shape: 'dot', borderWidth: 0, scaling: { min: 10, max: 52 }, font: { color: '#f2ede4', face: 'Archivo', size: 40, strokeWidth: 8, strokeColor: '#0d0b0c' } },
    edges: { width: 1.3, smooth: false, color: { color: 'rgba(167,159,151,.3)', highlight: '#ff3350', hover: 'rgba(242,237,228,.55)' }, selectionWidth: 1.2 },
    physics: false,
    interaction: { hover: true, tooltipDelay: 120, hideEdgesOnDrag: true, zoomView: false, dragView: true },
    layout: { improvedLayout: false },
  });
  const verTudo = (animar) => rede.fit({ animation: animar ? { duration: 400, easingFunction: 'easeInOutQuad' } : false });
  rede.once('afterDrawing', () => verTudo(false));
  new ResizeObserver(() => verTudo(false)).observe(caixa);
  const zoom = f => rede.moveTo({ scale: rede.getScale() * f, animation: { duration: 220, easingFunction: 'easeInOutQuad' } });
  document.getElementById('mais').onclick = () => zoom(1.35);
  document.getElementById('menos').onclick = () => zoom(1 / 1.35);
  document.getElementById('tudo').onclick = () => verTudo(true);

  const porId = Object.fromEntries(G.nos.map(n => [n.id, n]));
  const vizinhos = {};
  G.fios.forEach(f => { (vizinhos[f.de] = vizinhos[f.de] || []).push(f.para); (vizinhos[f.para] = vizinhos[f.para] || []).push(f.de); });
  const painel = document.getElementById('peca');
  const texto = t => { const d = document.createElement('div'); d.textContent = t == null ? '' : t; return d.innerHTML; };

  function mostrar(id, focar) {
    const n = porId[id];
    if (!n) return;
    const perto = [...new Set(vizinhos[id] || [])].map(v => porId[v]).filter(Boolean).sort((a, b) => b.grau - a.grau).slice(0, 8);
    const grupo = G.grupos.find(g => g.id === n.grupo);
    painel.innerHTML = `<b>${texto(n.rotulo)}</b>${n.porque ? texto(n.porque) : ''}<small>${texto(grupo ? grupo.nome : '')} · ${n.grau} ligações</small>` +
      (perto.length ? `<ul>${perto.map(p => `<li><button data-id="${texto(p.id)}">${texto(p.rotulo)}</button></li>`).join('')}</ul>` : '');
    painel.querySelectorAll('button').forEach(b => { b.onclick = () => mostrar(b.dataset.id, true); });
    rede.selectNodes([id]);
    if (focar) rede.focus(id, { scale: 0.75, animation: { duration: 500, easingFunction: 'easeInOutQuad' } });
  }
  rede.on('click', p => { if (p.nodes.length) mostrar(p.nodes[0]); });

  const busca = document.getElementById('busca');
  document.getElementById('nomes').innerHTML = G.nos.map(n => `<option value="${texto(n.rotulo)}">`).join('');
  busca.addEventListener('input', () => {
    const alvo = busca.value.trim().toLowerCase();
    const achado = alvo && (G.nos.find(n => n.rotulo.toLowerCase() === alvo) || G.nos.find(n => n.rotulo.toLowerCase().includes(alvo)));
    if (achado) mostrar(achado.id, true);
  });

  const lista = document.getElementById('grupos');
  G.grupos.forEach(g => {
    const li = document.createElement('li');
    li.innerHTML = `<button aria-pressed="true"><i style="background:${g.cor}"></i>${texto(g.nome)}<span>${g.n}</span></button>`;
    li.firstChild.onclick = e => {
      const b = e.currentTarget, ligado = b.getAttribute('aria-pressed') === 'true';
      b.setAttribute('aria-pressed', String(!ligado));
      nos.update(G.nos.filter(n => n.grupo === g.id).map(n => ({ id: n.id, hidden: ligado })));
    };
    lista.appendChild(li);
  });
})();
