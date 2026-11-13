// Self-calibration project page: copy buttons, folding cards, tabs,
// deployment-map tooltips and layer toggles, and the stepper of the decision
// tree. Built on the script of the HYMN project page. The page is fully readable
// without this script: every card shows in full, both deployments show, and the
// decision tree shows as a figure.
(() => {
  // ---------------------------------------------------------------- copy buttons
  document.querySelectorAll("pre[data-copy]").forEach((pre) => {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "copy";
    btn.textContent = "Copy";
    btn.addEventListener("click", async () => {
      try {
        await navigator.clipboard.writeText(pre.innerText.trim());
        btn.textContent = "Copied";
      } catch {
        btn.textContent = "Select and copy";
      }
      setTimeout(() => { btn.textContent = "Copy"; }, 1600);
    });
    pre.parentElement.insertBefore(btn, pre);
  });

  // --------------------------------------------------------------- folding cards
  // Lesson and research cards fold to their head. The text of the heading moves
  // into a button, so the heading stays a heading for assistive technology, and
  // the button's ::after (style.css) makes the whole head clickable.
  const folds = new Map();
  document.querySelectorAll("[data-fold]").forEach((card, i) => {
    const title = card.querySelector("[data-fold-title]");
    const body = card.querySelector("[data-fold-body]");
    if (!title || !body) return;
    if (!body.id) body.id = `fold-${i}`;
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "fold";
    btn.setAttribute("aria-controls", body.id);
    btn.append(...title.childNodes);
    const chev = document.createElement("span");
    chev.className = "chev";
    chev.setAttribute("aria-hidden", "true");
    btn.append(chev);
    title.append(btn);
    const set = (open) => {
      btn.setAttribute("aria-expanded", String(open));
      body.hidden = !open;
      card.classList.toggle("is-open", open);
    };
    btn.addEventListener("click", () => set(btn.getAttribute("aria-expanded") !== "true"));
    card.classList.add("is-foldable");
    set(false);
    folds.set(card, set);
  });
  // A link to a card, or into one, opens it before the browser scrolls there, and
  // a link to a BibTeX entry opens its <details>.
  const reveal = (hash) => {
    if (!hash || hash.length < 2) return;
    const el = document.getElementById(decodeURIComponent(hash.slice(1)));
    if (!el) return;
    folds.forEach((set, card) => { if (card.contains(el)) set(true); });
    if (el.tagName === "DETAILS") el.open = true;
  };
  document.addEventListener("click", (e) => {
    const a = e.target.closest('a[href^="#"]');
    if (a) reveal(a.getAttribute("href"));
  });
  window.addEventListener("hashchange", () => reveal(location.hash));
  reveal(location.hash);

  // ------------------------------------------------------------------------ tabs
  // WAI-ARIA tabs with automatic activation: arrow keys, Home and End move the
  // selection, and only the selected tab is in the tab order.
  const onTab = new Map();
  document.querySelectorAll('[role="tablist"]').forEach((list) => {
    const tabs = [...list.querySelectorAll('[role="tab"]')];
    const select = (tab, focus) => {
      tabs.forEach((t) => {
        const on = t === tab;
        t.setAttribute("aria-selected", String(on));
        t.tabIndex = on ? 0 : -1;
        const panel = document.getElementById(t.getAttribute("aria-controls"));
        if (panel) panel.hidden = !on;
      });
      if (focus) tab.focus();
      (onTab.get(list) || []).forEach((fn) => fn(tab));
    };
    tabs.forEach((tab, i) => {
      tab.addEventListener("click", () => select(tab, false));
      tab.addEventListener("keydown", (e) => {
        let j = null;
        if (e.key === "ArrowRight") j = (i + 1) % tabs.length;
        else if (e.key === "ArrowLeft") j = (i - 1 + tabs.length) % tabs.length;
        else if (e.key === "Home") j = 0;
        else if (e.key === "End") j = tabs.length - 1;
        if (j !== null) { e.preventDefault(); select(tabs[j], true); }
      });
    });
    list.hidden = false;
    select(tabs.find((t) => t.getAttribute("aria-selected") === "true") || tabs[0], false);
  });

  // ------------------------------------------------------------ deployment map
  document.querySelectorAll(".map-wrap").forEach((wrap) => {
    const svg = wrap.querySelector("svg");
    const tip = wrap.querySelector(".map-tip");
    if (!svg || !tip) return;
    // Native <title> tooltips remain for readers without JavaScript; replace them here.
    svg.querySelectorAll("[data-tip] > title").forEach((t) => t.remove());
    let active = null;
    const place = (x, y) => {
      const box = wrap.getBoundingClientRect();
      let left = x - box.left + 12;
      let top = y - box.top + 12;
      if (left + tip.offsetWidth > box.width - 4) left = x - box.left - tip.offsetWidth - 12;
      if (top + tip.offsetHeight > box.height - 4) top = y - box.top - tip.offsetHeight - 12;
      tip.style.left = `${Math.max(4, left)}px`;
      tip.style.top = `${Math.max(4, top)}px`;
    };
    const show = (el, e) => {
      if (active && active !== el) active.classList.remove("is-active");
      active = el;
      el.classList.add("is-active");
      tip.textContent = el.dataset.tip;
      tip.hidden = false;
      place(e.clientX, e.clientY);
    };
    const hide = () => {
      if (active) active.classList.remove("is-active");
      active = null;
      tip.hidden = true;
    };
    wrap.hideTip = hide;
    svg.addEventListener("pointermove", (e) => {
      const el = e.target.closest("[data-tip]");
      if (el) show(el, e);
      else if (e.pointerType === "mouse") hide();
    });
    svg.addEventListener("pointerleave", (e) => { if (e.pointerType === "mouse") hide(); });
    svg.addEventListener("pointerdown", (e) => {
      const el = e.target.closest("[data-tip]");
      if (el) show(el, e); else hide();
    });
  });

  // Layer toggles apply to both panels. A toggle that has nothing to show in the
  // selected deployment (the walks in the NLOS deployment, the markers in the LOS
  // deployment) is hidden while that deployment is selected.
  const layers = document.querySelector(".layers");
  const panels = [...document.querySelectorAll(".deploy-panel")];
  if (layers && panels.length) {
    layers.hidden = false;
    layers.querySelectorAll("button[data-layer]").forEach((btn) => {
      btn.addEventListener("click", () => {
        const on = btn.getAttribute("aria-pressed") !== "true";
        btn.setAttribute("aria-pressed", String(on));
        panels.forEach((p) => { p.classList.toggle(`hide-${btn.dataset.layer}`, !on); if (p.hideTip) p.hideTip(); });
      });
    });
    const deployTabs = document.querySelector(".deploy-tabs");
    if (deployTabs) {
      const sync = (tab) => {
        const set = document.getElementById(tab.getAttribute("aria-controls"))?.dataset.set;
        layers.querySelectorAll("button[data-for]").forEach((b) => {
          b.closest("li").hidden = b.dataset.for !== set;
        });
        panels.forEach((p) => { if (p.hideTip) p.hideTip(); });
      };
      onTab.set(deployTabs, [sync]);
      sync(deployTabs.querySelector('[aria-selected="true"]'));
    }
  }

  // ------------------------------------------------------------ decision guide
  // The nodes are the texts of Fig. 12 of the tutorial (fig_decision_tree.tex),
  // stored in the page as JSON; tools/check_page.py checks them against the source.
  const data = document.getElementById("guide-data");
  const stepper = document.querySelector(".stepper");
  if (data && stepper) {
    const T = JSON.parse(data.textContent);
    const trail = stepper.querySelector(".trail");
    const body = stepper.querySelector(".step-body");
    const live = stepper.querySelector(".step-live");
    const path = [];
    // a no-break space before the last word keeps it off a line of its own, as
    // tools/no_runts.py does for the static text
    const tie = (s) => s.replace(/ (\S+)$/, " $1");
    const el = (tag, cls, text) => {
      const e = document.createElement(tag);
      if (cls) e.className = cls;
      if (text) e.textContent = tie(text);
      return e;
    };
    const render = (id) => {
      const n = T.nodes[id];
      trail.replaceChildren(...path.map(([q, a]) => {
        const li = el("li");
        li.append(el("span", "cap", q), " ", el("span", "ans", a));
        return li;
      }));
      trail.hidden = path.length === 0;
      body.replaceChildren();
      if (n.q) {
        body.append(el("p", "step-kicker", `Question ${path.length + 1}`));
        const h = el("p", "step-q cap", n.q);
        h.tabIndex = -1;
        body.append(h);
        const acts = el("div", "step-actions");
        n.answers.forEach(([label, next]) => {
          const b = el("button", "", label);
          b.type = "button";
          b.addEventListener("click", () => { path.push([n.q, label]); render(next); });
          acts.append(b);
        });
        body.append(acts);
        live.textContent = n.q;
        if (path.length) h.focus();
      } else {
        body.append(el("p", "step-kicker", "Result"));
        const box = el("div", `leaf ${n.kind === "leaf" ? "is-leaf" : "is-dead"}`);
        if (n.name) {
          const name = el("p", "leaf-name cap", n.name);
          if (n.evidence) name.append(" ", el("span", "leaf-evidence", n.evidence));
          box.append(name);
        }
        if (n.cond) box.append(el("p", "leaf-cond cap", n.cond));
        const adv = el("p", "leaf-advice");
        if (n.prefix) adv.append(el("span", "leaf-prefix cap", n.prefix), " ");
        adv.append(el("strong", n.prefix ? "" : "cap", n.advice));
        if (n.ref) adv.append(" ", el("span", "leaf-ref", n.ref));
        box.append(adv);
        if (n.method) {
          const m = el("p", "leaf-method");
          n.method.forEach((part) => m.append(part.code ? el("code", "", part.code) : part.text));
          box.append(m);
        }
        if (n.topo) {
          // the topology card is highlighted by its :target style
          const p = el("p", "leaf-method");
          const a = el("a", "", "the topology in the tutorial's factor-graph notation");
          a.href = `#topo-${n.topo}`;
          p.append("See ", a, ".");
          box.append(p);
        }
        body.append(box);
        const again = el("button", "restart", "Start again");
        again.type = "button";
        again.addEventListener("click", () => { path.length = 0; render(T.first); stepper.querySelector(".step-q").focus(); });
        body.append(again);
        live.textContent = [n.name, n.advice].filter(Boolean).join(": ");
        box.tabIndex = -1;
        box.focus();
      }
    };
    stepper.hidden = false;
    const fallback = document.querySelector(".guide-fallback");
    if (fallback) fallback.open = false;
    render(T.first);
  }
})();
