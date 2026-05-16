const layerColors = {
  Syndrome: "#2f6fbb",
  Phenotype: "#0f9f8f",
  Gene: "#6d5bd0",
  Treatment: "#d97628",
  Outcome: "#c24b78",
  Entity: "#5e6b7c",
};

const state = {
  graph: null,
  selected: null,
  search: "",
  nodePositions: new Map(),
};

const taskPerformance = {
  t1: {
    kicker: "Task 1 comparison",
    title: "Clinical Decision Accuracy",
    summary:
      "Graph-RAG improves epilepsy MCQ accuracy and open-ended reasoning quality across all six evaluated LLMs.",
    primary: "+11.3 pp",
    primaryLabel: "avg. MCQ accuracy gain",
    secondary: "+0.51",
    secondaryLabel: "avg. judge-score gain",
    best: "75.0%",
    bestLabel: "best Graph-RAG MCQ accuracy",
    rows: [
      ["GPT-4o MCQ", "68.0%", "75.0%", "+10.3%"],
      ["Claude S4 MCQ", "69.0%", "73.0%", "+5.8%"],
      ["Mistral MCQ", "51.0%", "61.0%", "+19.6%"],
      ["GPT-4o open QA", "3.61", "4.33", "+19.9%"],
    ],
    note:
      "T1 combines MCQ and open-ended QA. The paper reports avg. +11.3 percentage-point MCQ gain and +0.51 LLM-as-judge gain with Graph-RAG.",
  },
  t2: {
    kicker: "Task 2 comparison",
    title: "Clinical Report Generation",
    summary:
      "On the restricted Harvard EEG setting, EpiKG evidence improves neurologist-style impression generation for every locally evaluated model.",
    primary: "+13.6%",
    primaryLabel: "avg. METEOR lift",
    secondary: "+30.8%",
    secondaryLabel: "largest single-model lift",
    best: "0.34",
    bestLabel: "best Graph-RAG METEOR",
    rows: [
      ["Gemma-3-4B", "0.23", "0.26", "+13.0%"],
      ["Llama-3.2-3B", "0.29", "0.31", "+6.8%"],
      ["MedGemma-4B", "0.26", "0.34", "+30.8%"],
      ["Qwen3-4B", "0.26", "0.27", "+3.8%"],
    ],
    note:
      "T2 uses a private Harvard EEG-derived local evaluation pipeline; the public release includes schema and runnable adapter code rather than patient data.",
  },
  t3: {
    kicker: "Task 3 comparison",
    title: "Biomarker Precision Medicine",
    summary:
      "Precision-medicine questions show the largest gains because graph paths expose gene, phenotype, mechanism, and antiseizure-medication links.",
    primary: "+34.8%",
    primaryLabel: "avg. accuracy lift",
    secondary: "+33.2%",
    secondaryLabel: "avg. guideline lift",
    best: "82.0%",
    bestLabel: "best Graph-RAG accuracy",
    rows: [
      ["GPT-4o", "53.0%", "69.0%", "+30.2%"],
      ["Claude S4", "66.0%", "82.0%", "+24.2%"],
      ["Qwen", "41.0%", "58.0%", "+41.5%"],
      ["Mistral", "38.0%", "51.0%", "+34.2%"],
    ],
    note:
      "T3 is the strongest evidence-intensive setting: all models improve, with especially large gains for open-source models.",
  },
  t4: {
    kicker: "Task 4 comparison",
    title: "Treatment Recommendation",
    summary:
      "Graph-RAG improves answer correctness, drug safety, guideline concordance, and KG evidence coverage on treatment recommendation.",
    primary: "+15.6%",
    primaryLabel: "MedQA accuracy lift",
    secondary: "+17.2%",
    secondaryLabel: "MMLU accuracy lift",
    best: "83.0%",
    bestLabel: "best Graph-RAG accuracy",
    rows: [
      ["GPT-4o MedQA", "72.0%", "81.0%", "+12.5%"],
      ["Claude S4 MedQA", "70.0%", "79.0%", "+12.9%"],
      ["GPT-4o MMLU", "74.0%", "83.0%", "+12.2%"],
      ["Claude S4 MMLU", "71.0%", "80.0%", "+12.7%"],
    ],
    note:
      "Beyond raw accuracy, MMLU Professional Medicine shows large safety and guideline gains: +28.1% DFS and +28.4% guideline concordance.",
  },
  t5: {
    kicker: "Task 5 comparison",
    title: "Deep Research Planning",
    summary:
      "Structured KG evidence helps models synthesize more coherent, feasible, and literature-grounded epilepsy research plans.",
    primary: "+12.2%",
    primaryLabel: "avg. judge-score lift",
    secondary: "+15.6%",
    secondaryLabel: "avg. ROUGE-L lift",
    best: "4.25",
    bestLabel: "best Graph-RAG judge score",
    rows: [
      ["GPT-4o", "3.56", "4.25", "+19.4%"],
      ["Claude S4", "3.69", "4.13", "+11.9%"],
      ["Llama", "3.37", "3.87", "+14.8%"],
      ["Mistral", "3.49", "3.77", "+8.0%"],
    ],
    note:
      "T5 narrows the closed/open-source gap because retrieved evidence paths help models build grounded hypotheses and study designs.",
  },
};

initHeroCanvas();
initQuickstartCopy();
initTaskPerformance();
loadGraph();

async function loadGraph() {
  const response = await fetch("./data/demo_graph.json");
  state.graph = await response.json();
  renderChips();
  renderGraph();
  document.getElementById("kg-search").addEventListener("input", (event) => {
    setSearchQuery(event.target.value, false);
  });
  window.addEventListener("resize", () => renderGraph());
}

function renderChips() {
  const holder = document.getElementById("query-chips");
  holder.innerHTML = "";
  state.graph.examples.forEach((item) => {
    const button = document.createElement("button");
    button.type = "button";
    button.textContent = item.label;
    button.addEventListener("click", () => {
      const input = document.getElementById("kg-search");
      input.value = item.query;
      setSearchQuery(item.query, true);
    });
    holder.appendChild(button);
  });
}

function setSearchQuery(query, autoSelect) {
  state.search = query.trim().toLowerCase();
  if (!state.search) {
    state.selected = null;
    resetInspector();
    updateHighlighting();
    return;
  }

  if (autoSelect) {
    const match = findBestNodeForQuery(state.search);
    if (match) {
      selectNode(match);
      return;
    }
  } else {
    state.selected = null;
    resetInspector();
  }
  updateHighlighting();
}

function resetInspector() {
  document.getElementById("inspector").innerHTML = `
    <p class="inspector-label">Selected item</p>
    <h3>Click a node or edge</h3>
    <p>
      The explorer shows how evidence paths connect syndromes,
      genes, treatments, and outcomes.
    </p>
  `;
}

function findBestNodeForQuery(query) {
  const terms = query.split(/\s+/).filter(Boolean);
  if (!terms.length) return null;

  let best = null;
  let bestScore = 0;
  const queryPhrase = terms.join(" ");
  state.graph.nodes.forEach((node) => {
    const id = node.id.toLowerCase();
    const label = node.label.toLowerCase();
    let score = 0;
    if (queryPhrase.includes(label) || queryPhrase.includes(id)) score += 20;
    terms.forEach((term, index) => {
      if (id === term || label === term) score += 12 - index;
      else if (id.startsWith(term) || label.startsWith(term)) score += 6 - Math.min(index, 4);
      else if (id.includes(term) || label.includes(term)) score += 3 - Math.min(index, 2);
    });
    if (score > bestScore || (score === bestScore && node.degree > (best?.degree || 0))) {
      best = node;
      bestScore = score;
    }
  });
  return bestScore > 0 ? best : null;
}

function renderGraph() {
  const svg = document.getElementById("kg-svg");
  const rect = svg.getBoundingClientRect();
  const width = Math.max(rect.width, 680);
  const height = Math.max(rect.height || 560, 520);
  svg.setAttribute("viewBox", `0 0 ${width} ${height}`);
  svg.innerHTML = "";
  state.nodePositions.clear();

  const nodes = state.graph.nodes.map((node) => ({ ...node }));
  const links = state.graph.links.map((link) => ({ ...link }));
  const centerX = width * 0.5;
  const centerY = height * 0.5;
  const radius = Math.min(width, height) * 0.36;

  const layerOrder = ["Syndrome", "Phenotype", "Gene", "Treatment", "Outcome", "Entity"];
  nodes.sort((a, b) => layerOrder.indexOf(a.layer) - layerOrder.indexOf(b.layer) || b.degree - a.degree);
  nodes.forEach((node, index) => {
    const angle = (index / nodes.length) * Math.PI * 2 - Math.PI / 2;
    const layerOffset = Math.max(layerOrder.indexOf(node.layer), 0) * 9;
    const localRadius = radius - layerOffset + (index % 5) * 4;
    node.x = centerX + Math.cos(angle) * localRadius;
    node.y = centerY + Math.sin(angle) * localRadius * 0.78;
    state.nodePositions.set(node.id, node);
  });

  const edgeLayer = svgEl("g", { class: "edges" });
  links.forEach((link, index) => {
    const source = state.nodePositions.get(link.source);
    const target = state.nodePositions.get(link.target);
    if (!source || !target) return;
    const path = svgEl("path", {
      class: "edge-line",
      d: curvedPath(source, target, index),
      "data-source": link.source,
      "data-target": link.target,
      "data-relation": link.relation,
    });
    path.addEventListener("click", () => selectEdge(link));
    edgeLayer.appendChild(path);
  });
  svg.appendChild(edgeLayer);

  const nodeLayer = svgEl("g", { class: "nodes" });
  nodes.forEach((node) => {
    const group = svgEl("g", { class: "node", "data-id": node.id, transform: `translate(${node.x}, ${node.y})` });
    const radius = Math.max(8, Math.min(19, 8 + Math.sqrt(node.degree) * 2.2));
    group.appendChild(svgEl("circle", { r: radius, fill: layerColors[node.layer] || layerColors.Entity }));
    const label = truncate(node.label, 22);
    const text = svgEl("text", { x: radius + 7, y: 4 });
    text.textContent = label;
    group.appendChild(text);
    group.addEventListener("click", () => selectNode(node));
    nodeLayer.appendChild(group);
  });
  svg.appendChild(nodeLayer);
  updateHighlighting();
}

function curvedPath(source, target, index) {
  const mx = (source.x + target.x) / 2;
  const my = (source.y + target.y) / 2;
  const dx = target.x - source.x;
  const dy = target.y - source.y;
  const len = Math.max(Math.hypot(dx, dy), 1);
  const bend = ((index % 5) - 2) * 8;
  const cx = mx - (dy / len) * bend;
  const cy = my + (dx / len) * bend;
  return `M ${source.x} ${source.y} Q ${cx} ${cy} ${target.x} ${target.y}`;
}

function selectNode(node) {
  state.selected = { type: "node", item: node };
  const connected = state.graph.links.filter((link) => link.source === node.id || link.target === node.id);
  document.getElementById("inspector").innerHTML = `
    <p class="inspector-label">Entity</p>
    <h3>${escapeHtml(node.label)}</h3>
    <span class="pill">${escapeHtml(node.layer)}</span>
    ${node.source ? `<span class="pill">${escapeHtml(node.source)}</span>` : ""}
    <p>${connected.length} visible relations in this demo subgraph.</p>
    <ul>
      ${connected.slice(0, 8).map((link) => `<li>${escapeHtml(link.source)} <strong>${escapeHtml(link.relation)}</strong> ${escapeHtml(link.target)}</li>`).join("")}
    </ul>
  `;
  updateHighlighting();
}

function selectEdge(edge) {
  state.selected = { type: "edge", item: edge };
  const papers = edge.supporting_papers?.length ? edge.supporting_papers.join(", ") : "Not shown in demo";
  document.getElementById("inspector").innerHTML = `
    <p class="inspector-label">Relation</p>
    <h3>${escapeHtml(edge.relation.replaceAll("_", " "))}</h3>
    <p><strong>${escapeHtml(edge.source)}</strong> to <strong>${escapeHtml(edge.target)}</strong></p>
    <span class="pill">${edge.paper_count || 1} papers</span>
    <span class="pill">confidence ${edge.confidence || "n/a"}</span>
    ${edge.cross_layer ? '<span class="pill">cross-layer</span>' : ""}
    <p>Supporting papers: ${escapeHtml(papers)}</p>
  `;
  updateHighlighting();
}

function updateHighlighting() {
  const terms = state.search.split(/\s+/).filter(Boolean);
  const selectedNode = state.selected?.type === "node" ? state.selected.item.id : null;
  const selectedEdge = state.selected?.type === "edge" ? state.selected.item : null;
  const connectedToSelected = (id) =>
    selectedNode &&
    state.graph.links.some((link) => (link.source === selectedNode && link.target === id) || (link.target === selectedNode && link.source === id));

  document.querySelectorAll(".node").forEach((nodeEl) => {
    const id = nodeEl.dataset.id;
    const text = id.toLowerCase();
    const matchesSearch = terms.length === 0 || terms.some((term) => text.includes(term));
    const matchesSelected = !selectedNode || id === selectedNode || connectedToSelected(id);
    const shouldShow = selectedNode ? matchesSelected || matchesSearch : matchesSearch;
    nodeEl.classList.toggle("dimmed", !shouldShow);
  });

  document.querySelectorAll(".edge-line").forEach((edgeEl) => {
    const source = edgeEl.dataset.source;
    const target = edgeEl.dataset.target;
    const rel = edgeEl.dataset.relation;
    const edgeText = `${source} ${target} ${rel}`.toLowerCase();
    const matchesSearch = terms.length === 0 || terms.some((term) => edgeText.includes(term));
    const matchesSelected = !selectedNode || source === selectedNode || target === selectedNode;
    const isActive = selectedEdge && selectedEdge.source === source && selectedEdge.target === target && selectedEdge.relation === rel;
    const shouldShow = selectedNode ? matchesSelected || matchesSearch : matchesSearch;
    edgeEl.classList.toggle("dimmed", !shouldShow);
    edgeEl.classList.toggle("active", Boolean(isActive));
  });
}

function initHeroCanvas() {
  const canvas = document.getElementById("hero-canvas");
  const context = canvas.getContext("2d");
  const nodes = Array.from({ length: 54 }, (_, index) => ({
    x: Math.random(),
    y: Math.random(),
    vx: (Math.random() - 0.5) * 0.0008,
    vy: (Math.random() - 0.5) * 0.0008,
    r: 2 + (index % 5),
    color: ["#2f6fbb", "#0f9f8f", "#6d5bd0", "#d97628", "#c24b78"][index % 5],
  }));

  function resize() {
    const ratio = window.devicePixelRatio || 1;
    canvas.width = Math.floor(canvas.clientWidth * ratio);
    canvas.height = Math.floor(canvas.clientHeight * ratio);
    context.setTransform(ratio, 0, 0, ratio, 0, 0);
  }

  function draw() {
    const width = canvas.clientWidth;
    const height = canvas.clientHeight;
    context.clearRect(0, 0, width, height);
    context.fillStyle = "#102033";
    context.fillRect(0, 0, width, height);

    nodes.forEach((node) => {
      node.x += node.vx;
      node.y += node.vy;
      if (node.x < 0 || node.x > 1) node.vx *= -1;
      if (node.y < 0 || node.y > 1) node.vy *= -1;
    });

    for (let i = 0; i < nodes.length; i++) {
      for (let j = i + 1; j < nodes.length; j++) {
        const a = nodes[i];
        const b = nodes[j];
        const ax = a.x * width;
        const ay = a.y * height;
        const bx = b.x * width;
        const by = b.y * height;
        const dist = Math.hypot(ax - bx, ay - by);
        if (dist < 170) {
          context.strokeStyle = `rgba(220, 232, 246, ${0.2 * (1 - dist / 170)})`;
          context.lineWidth = 1;
          context.beginPath();
          context.moveTo(ax, ay);
          context.lineTo(bx, by);
          context.stroke();
        }
      }
    }

    nodes.forEach((node) => {
      context.fillStyle = node.color;
      context.beginPath();
      context.arc(node.x * width, node.y * height, node.r, 0, Math.PI * 2);
      context.fill();
    });
    requestAnimationFrame(draw);
  }

  resize();
  window.addEventListener("resize", resize);
  draw();
}

function initQuickstartCopy() {
  const button = document.getElementById("copy-quickstart");
  button.addEventListener("click", async () => {
    const code = document.getElementById("quickstart-code").textContent;
    await navigator.clipboard.writeText(code);
    button.textContent = "Copied";
    window.setTimeout(() => {
      button.textContent = "Copy";
    }, 1400);
  });
}

function initTaskPerformance() {
  const cards = Array.from(document.querySelectorAll(".task-card[data-task]"));
  cards.forEach((card) => {
    const activate = () => renderTaskPerformance(card.dataset.task);
    card.addEventListener("click", activate);
    card.addEventListener("keydown", (event) => {
      if (event.key === "Enter" || event.key === " ") {
        event.preventDefault();
        activate();
      }
    });
  });
  renderTaskPerformance("t1");
}

function renderTaskPerformance(taskId) {
  const data = taskPerformance[taskId] || taskPerformance.t1;
  document.querySelectorAll(".task-card[data-task]").forEach((card) => {
    const active = card.dataset.task === taskId;
    card.classList.toggle("active", active);
    card.setAttribute("aria-selected", String(active));
  });

  document.getElementById("perf-kicker").textContent = data.kicker;
  document.getElementById("perf-title").textContent = data.title;
  document.getElementById("perf-summary").textContent = data.summary;
  document.getElementById("perf-primary").textContent = data.primary;
  document.getElementById("perf-primary-label").textContent = data.primaryLabel;
  document.getElementById("perf-secondary").textContent = data.secondary;
  document.getElementById("perf-secondary-label").textContent = data.secondaryLabel;
  document.getElementById("perf-best").textContent = data.best;
  document.getElementById("perf-best-label").textContent = data.bestLabel;
  document.getElementById("perf-note").textContent = data.note;
  document.getElementById("perf-rows").innerHTML = data.rows
    .map(
      ([setting, baseline, graphRag, lift]) => `
        <tr>
          <td>${escapeHtml(setting)}</td>
          <td>${escapeHtml(baseline)}</td>
          <td>${escapeHtml(graphRag)}</td>
          <td>${escapeHtml(lift)}</td>
        </tr>
      `,
    )
    .join("");
}

function svgEl(name, attrs = {}) {
  const element = document.createElementNS("http://www.w3.org/2000/svg", name);
  Object.entries(attrs).forEach(([key, value]) => element.setAttribute(key, value));
  return element;
}

function truncate(text, max) {
  return text.length > max ? `${text.slice(0, max - 1)}…` : text;
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}
