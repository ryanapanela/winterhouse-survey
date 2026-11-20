(() => {
  "use strict";
  const C = window.SURVEY_CONFIG, Q = window.Q;
  const app = document.getElementById("app");
  const params = new URLSearchParams(location.search);
  const me = params.get("me"), key = params.get("k");
  const part = params.get("part") === "2" ? 2 : 1;
  const pilot = params.get("pilot") === "1";
  const VERSION = "2026-11-15";

  // ---------- utilities ----------
  const h = (tag, attrs = {}, ...kids) => {
    const e = document.createElement(tag);
    for (const [k, v] of Object.entries(attrs || {})) {
      if (v == null || v === false) continue;
      if (k === "class") e.className = v;
      else if (k.startsWith("on")) e.addEventListener(k.slice(2), v);
      else if (k === "html") e.innerHTML = v;
      else e.setAttribute(k, v === true ? "" : v);
    }
    for (const kid of kids.flat()) if (kid != null && kid !== false) e.append(kid.nodeType ? kid : document.createTextNode(kid));
    return e;
  };
  function seeded(str) {
    let s = 2166136261;
    for (const ch of str) s = Math.imul(s ^ ch.charCodeAt(0), 16777619);
    return () => { s += 0x6D2B79F5; let t = s; t = Math.imul(t ^ t >>> 15, t | 1); t ^= t + Math.imul(t ^ t >>> 7, t | 61); return ((t ^ t >>> 14) >>> 0) / 4294967296; };
  }
  const shuffle = (arr, rnd) => { const a = arr.slice(); for (let i = a.length - 1; i > 0; i--) { const j = Math.floor(rnd() * (i + 1)); [a[i], a[j]] = [a[j], a[i]]; } return a; };
  const get = (obj, path, dflt) => { let o = obj; for (const p of path) { if (o[p] == null) o[p] = {}; o = o[p]; } return o; };

  // ---------- bad link ----------
  if (!me || !key || !C.names.includes(me)) {
    app.append(h("main", { class: "screen" },
      h("p", { class: "eyebrow" }, "Winterhouse"),
      h("h1", {}, "This link isn't complete"),
      h("p", {}, "Use the personal link Ryan sent you. It includes your name and a code, so your answers are saved as yours.")));
    return;
  }
  const NAMES = [...C.names].sort((a, b) => a.localeCompare(b));
  const others = NAMES.filter(n => n !== me);
  const AWAY = C.away || [];                       // in the network but not at the cottage
  const nonPlayers = [C.host, ...AWAY];            // not in Traitors
  const players = others.filter(n => !nonPlayers.includes(n));
  const atCottage = others.filter(n => !AWAY.includes(n));
  const isHost = me === C.host;
  const isAway = AWAY.includes(me);
  const poolFor = (id, ex) => ex ? players : (Q.WEEKEND_ONLY || []).includes(id) ? atCottage : others;

  // ---------- state ----------
  const SKEY = `winterhouse:${pilot ? "pilot:" : ""}${me}:part${part}`;
  let state;
  try { state = JSON.parse(localStorage.getItem(SKEY)); } catch { state = null; }
  const freshDevice = !state || typeof state !== "object";
  if (freshDevice) state = { answers: {}, idx: 0, startedAt: new Date().toISOString() };
  const A = state.answers;
  let saveTimer;
  const save = () => { clearTimeout(saveTimer); saveTimer = setTimeout(() => { try { localStorage.setItem(SKEY, JSON.stringify(state)); } catch {} }, 150); };

  // ---------- controls ----------
  function segmented(bucket, id, labels, { values, cls = "", aria } = {}) {
    const vals = values || labels.map((_, i) => i + 1);
    const wrap = h("div", { class: "seg " + cls, role: "group", "aria-label": aria || "" });
    const paint = () => wrap.querySelectorAll("button").forEach((b, i) => b.setAttribute("aria-pressed", String(bucket[id] === vals[i])));
    labels.forEach((lab, i) => wrap.append(h("button", { type: "button", onclick: () => { bucket[id] = bucket[id] === vals[i] ? null : vals[i]; paint(); save(); } }, lab)));
    paint();
    return wrap;
  }
  function likert(bucket, id) { return segmented(bucket, id, Q.likert, { cls: "likert", aria: "Agreement" }); }
  function tot(bucket, id, a, b) { return segmented(bucket, id, [a, b], { values: ["a", "b"], cls: "tot", aria: "Pick one" }); }

  function iosSvg(level) { // 1 = separate circles, 7 = almost fully overlapping
    const d = [34, 28, 22, 16, 11, 7, 3][level - 1];
    return `<svg viewBox="0 0 80 40" aria-hidden="true"><circle cx="${40 - d / 2}" cy="20" r="15" class="c1"/><circle cx="${40 + d / 2}" cy="20" r="15" class="c2"/></svg>`;
  }
  function ios(bucket, id) {
    const wrap = h("div", { class: "ios", role: "group", "aria-label": "Closeness, 1 to 7" });
    const paint = () => wrap.querySelectorAll("button").forEach((b, i) => b.setAttribute("aria-pressed", String(bucket[id] === i + 1)));
    for (let i = 1; i <= 7; i++) wrap.append(h("button", { type: "button", "aria-label": `${i} of 7`, html: iosSvg(i) + `<span>${i}</span>`, onclick: () => { bucket[id] = bucket[id] === i ? null : i; paint(); save(); } }));
    paint();
    return wrap;
  }
  function multiPick(bucket, id, pool, max, { cls = "" } = {}) {
    if (!Array.isArray(bucket[id])) bucket[id] = [];
    const sel = bucket[id];
    const wrap = h("div", { class: "chips " + cls });
    const note = h("p", { class: "hint" });
    const paint = () => {
      wrap.querySelectorAll("button").forEach(b => {
        const on = sel.includes(b.dataset.v);
        b.setAttribute("aria-pressed", String(on));
        b.disabled = !on && sel.length >= max;
      });
      note.textContent = max === 1 ? (sel.length ? "Tap again to clear." : "Pick one.") : `${sel.length} of ${max} picked`;
    };
    pool.forEach(v => wrap.append(h("button", { type: "button", "data-v": v, onclick: () => {
      const i = sel.indexOf(v); if (i >= 0) sel.splice(i, 1); else if (sel.length < max) sel.push(v); paint(); save();
    } }, v)));
    paint();
    return h("div", {}, wrap, note);
  }
  function pairPicker(bucket, id, pool, count) {
    if (!Array.isArray(bucket[id])) bucket[id] = [];
    const rows = h("div", { class: "pairs" });
    for (let r = 0; r < count; r++) {
      if (!Array.isArray(bucket[id][r])) bucket[id][r] = ["", ""];
      const pair = bucket[id][r];
      const s1 = h("select", { id: `${id}-${r}-a`, "aria-label": `Pair ${r + 1}, first person` });
      const s2 = h("select", { id: `${id}-${r}-b`, "aria-label": `Pair ${r + 1}, second person` });
      const fill = () => {
        s1.replaceChildren(h("option", { value: "" }, "Choose…"), ...pool.map(n => h("option", { value: n, selected: pair[0] === n }, n)));
        s2.replaceChildren(h("option", { value: "" }, "Choose…"), ...pool.filter(n => n !== pair[0]).map(n => h("option", { value: n, selected: pair[1] === n }, n)));
      };
      s1.addEventListener("change", () => { pair[0] = s1.value; if (pair[1] === pair[0]) pair[1] = ""; fill(); save(); });
      s2.addEventListener("change", () => { pair[1] = s2.value; save(); });
      fill();
      rows.append(h("div", { class: "pair" }, s1, h("span", { class: "amp" }, "&"), s2));
    }
    return rows;
  }
  function textField(bucket, id, { label, multiline = false, placeholder = "", max = 600 } = {}) {
    const fid = `f-${id}-${Math.random().toString(36).slice(2, 7)}`;
    const input = h(multiline ? "textarea" : "input", { id: fid, maxlength: max, placeholder, rows: multiline ? 3 : null, type: multiline ? null : "text" });
    input.value = bucket[id] || "";
    input.addEventListener("input", () => { bucket[id] = input.value; save(); });
    return h("div", { class: "field" }, label ? h("label", { for: fid }, label) : null, input);
  }
  function select(bucket, id, options, label) {
    const fid = `s-${id}-${Math.random().toString(36).slice(2, 7)}`;
    const s = h("select", { id: fid }, h("option", { value: "" }, "Choose…"), ...options.map(o => h("option", { value: o, selected: bucket[id] === o }, o)));
    s.addEventListener("change", () => { bucket[id] = s.value || null; save(); });
    return h("div", { class: "field" }, h("label", { for: fid }, label), s);
  }
  const q = (num, text, ...body) => h("section", { class: "q" }, h("h3", {}, num ? h("span", { class: "qn" }, num) : null, text), ...body);

  // ---------- network ----------
  async function post(path, body) {
    if (!C.endpoint) throw new Error("The survey isn't connected yet. Tell Ryan.");
    const r = await fetch(C.endpoint.replace(/\/$/, "") + path, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ me, k: key, part, pilot, ...body }) });
    let data = {}; try { data = await r.json(); } catch {}
    if (!r.ok) throw new Error(data.error || `Couldn't save (error ${r.status}). Try again in a minute.`);
    return data;
  }

  // ---------- photo upload ----------
  async function shrink(file) {
    const bmp = await createImageBitmap(file).catch(() => null);
    if (!bmp) throw new Error("This photo format couldn't be read. Try a JPEG or PNG, or a screenshot of it.");
    const scale = Math.min(1, 1800 / Math.max(bmp.width, bmp.height));
    const cv = document.createElement("canvas");
    cv.width = Math.round(bmp.width * scale); cv.height = Math.round(bmp.height * scale);
    cv.getContext("2d").drawImage(bmp, 0, 0, cv.width, cv.height);
    const blob = await new Promise(res => cv.toBlob(res, "image/jpeg", 0.85));
    const buf = new Uint8Array(await blob.arrayBuffer());
    let s = ""; for (let i = 0; i < buf.length; i += 0x8000) s += String.fromCharCode.apply(null, buf.subarray(i, i + 0x8000));
    const tc = document.createElement("canvas"), ts = 160 / Math.max(cv.width, cv.height);
    tc.width = Math.round(cv.width * ts); tc.height = Math.round(cv.height * ts);
    tc.getContext("2d").drawImage(cv, 0, 0, tc.width, tc.height);
    return { data: btoa(s), preview: tc.toDataURL("image/jpeg", 0.6) };
  }
  function photoCard(H, p, onRemove) {
    const status = h("p", { class: "hint", "aria-live": "polite" }, p.error || (p.path ? "" : "Uploading…"));
    const img = h("img", { class: "thumb", alt: "", hidden: !p.preview });
    if (p.preview) img.src = p.preview;
    const tag = h("details", { class: "tag" }, h("summary", {}, p.who && p.who.length ? `Tagged: ${p.who.join(", ")}` : "Tag who's in it"),
      multiPick(p, "who", NAMES, NAMES.length, { cls: "small" }));
    tag.addEventListener("toggle", () => { if (!tag.open) tag.querySelector("summary").textContent = p.who && p.who.length ? `Tagged: ${p.who.join(", ")}` : "Tag who's in it"; });
    const card = h("div", { class: "photo" },
      h("div", { class: "photo-head" }, img,
        h("div", { class: "photo-fields" },
          h("div", { class: "row2 tight" }, textField(p, "year", { label: "Year", placeholder: "e.g. 2023", max: 20 }), textField(p, "caption", { label: "Caption (optional)", max: 140 })),
          status)),
      tag,
      h("div", { class: "photo-foot" },
        h("button", { type: "button", class: "linkbtn", onclick: () => { onRemove(p); } }, "Remove")));
    for (const [k, v] of [["_status", status], ["_img", img]]) Object.defineProperty(p, k, { value: v, writable: true, configurable: true, enumerable: false });
    return card;
  }
  async function uploadPhotos(H, files, rerender) {
    const queue = [];
    for (const f of files) {
      const id = Date.now().toString(36) + Math.random().toString(36).slice(2, 8);
      const p = { id, who: [] };
      H.photos.push(p); queue.push([p, f]);
    }
    save(); rerender();
    for (const [p, f] of queue) {
      try {
        const { data, preview } = await shrink(f);
        p.preview = preview;
        if (p._img) { p._img.src = preview; p._img.hidden = false; }
        const res = await post("/media", { id: p.id, data });
        p.path = res.path; delete p.error;
        if (p._status) p._status.textContent = "";
      } catch (e) { p.error = e.message; if (p._status) p._status.textContent = e.message; }
      save();
    }
  }

  // ---------- prediction items ----------
  const allItems = [];
  Q.B.forEach(g => g.items.forEach(([id, text, block]) => allItems.push({ id, kind: "likert", text, block })));
  Q.TOT.forEach(([id, a, b, block]) => allItems.push({ id, kind: "tot", a, b, block }));

  // ---------- screens ----------
  const screens = [];
  const add = (title, build, opts = {}) => screens.push({ title, build, ...opts });
  const rnd = seeded(me + ":" + part);

  const intro = (heading, paras) => add(heading, el => {
    el.append(h("p", { class: "greet" }, `Hi ${me}`), h("h1", {}, heading));
    paras.forEach(p => el.append(typeof p === "string" ? h("p", {}, p) : p));
  }, { intro: true });

  if (part === 1) {
    intro("Part 1: The Yearbook", [
      "Before Winterhouse, we're mapping how this group is connected: who's close, where we line up, and which connections haven't happened yet. This part is about you and five years of memories. It takes about 15 minutes. Part 2 comes later in the week.",
      h("dl", { class: "who-sees" },
        h("dt", {}, "Everyone will see"), h("dd", {}, "the network map, Unexpected Pairings, the group's split on hot takes, Traitors trust and suspicion counts, and the Prom Award finalists."),
        h("dt", {}, "Nobody will see"), h("dd", {}, "how you rated or described any individual person. Ratings are combined into scores by a script.")),
      "There are no right answers, and you can skip anything. Your progress saves on this device as you go.",
    ]);
    const B = () => get(A, ["B"]);
    const bNum = {}; let bn = 0;
    Q.B.forEach(g => g.items.forEach(([id]) => { bNum[id] = ++bn; }));
    Q.TOT.forEach(([id]) => { bNum[id] = ++bn; });
    Q.B.forEach((g, gi) => add(`Where you stand: ${g.group.toLowerCase()}`, el => {
      el.append(h("p", { class: "eyebrow" }, `Where you stand · ${gi + 1} of 6`), h("h2", {}, g.group), h("p", { class: "lede" }, "How much do you agree?"));
      g.items.forEach(([id, text]) => el.append(q(String(bNum[id]), text, likert(B(), id))));
    }));
    [[0, 10], [10, Q.TOT.length]].forEach(([s, e], k) => add("This or that", el => {
      el.append(h("p", { class: "eyebrow" }, `Where you stand · ${5 + k} of 6`), h("h2", {}, "This or that"), h("p", { class: "lede" }, "Go with your gut."));
      Q.TOT.slice(s, e).forEach(([id, a, b]) => el.append(q(String(bNum[id]), "", tot(B(), id, a, b))));
    }));
    add("Group quotes", el => {
      const H = get(A, ["H"]); if (!Array.isArray(H.quotes) || !H.quotes.length) H.quotes = [{}];
      el.append(h("p", { class: "eyebrow" }, "Yearbook submissions"), h("h2", {}, "Quotes from five years"),
        h("p", { class: "lede" }, "Share as many memorable things people in this group have said as you like. Write the quote only. The \"who said it\" answer is hidden and only Ryan sees it."));
      const list = h("div", { class: "stack-list" });
      const draw = () => {
        list.replaceChildren(...H.quotes.map((qq, i) => h("section", { class: "q card" },
          h("h3", {}, h("span", { class: "qn" }, i + 1), "Quote",
            H.quotes.length > 1 ? h("button", { type: "button", class: "linkbtn push", onclick: () => { H.quotes.splice(i, 1); save(); draw(); } }, "Remove") : null),
          textField(qq, "text", { multiline: true, placeholder: "\u201c\u2026\u201d", max: 400 }),
          h("div", { class: "row2" }, select(qq, "who", [...NAMES, "Not sure"], "Who said it? (hidden)"), textField(qq, "ctx", { label: "Context (optional)", max: 140 })))));
      };
      draw();
      el.append(list, h("button", { type: "button", class: "btn add", onclick: () => { H.quotes.push({}); save(); draw(); list.lastChild.querySelector("textarea").focus(); } }, "+ Add another quote"));
    });
    add("All about you", el => {
      const P = get(A, ["P"]);
      el.append(h("p", { class: "eyebrow" }, "Yearbook profile"), h("h2", {}, "All about you"),
        h("p", { class: "lede" }, "Short answers for your yearbook page. Skip any you like."),
        ...Q.ABOUT.map(([id, text, ph]) => q(id, text, textField(P, id, { placeholder: ph, max: 160 }))));
    });
    add("Your favourite quote", el => {
      const H = get(A, ["H"]);
      el.append(h("p", { class: "eyebrow" }, "Yearbook submissions"), h("h2", {}, "Your favourite quote"),
        h("p", { class: "lede" }, "From anywhere: a book, a film, a song, a professor, your mum. Don't say who said it, or that it's yours."),
        textField(H, "fav", { multiline: true, placeholder: "\u201c\u2026\u201d", max: 400 }));
    });
    add("Photos and videos", el => {
      const H = get(A, ["H"]); if (!Array.isArray(H.photos)) H.photos = [];
      el.append(h("p", { class: "eyebrow" }, "Yearbook submissions"), h("h2", {}, "Photos and videos"),
        h("p", { class: "lede" }, "Start with a baby photo of yourself, then add as many photos from the last five years with people in this group as you like. You can select lots at once. Year, caption and tags are optional."));
      // Baby photo: one slot, saved apart from the others
      const babyStatus = h("p", { class: "hint", "aria-live": "polite" }, H.baby && H.baby.path ? "Uploaded." : "");
      const babyImg = h("img", { class: "thumb", alt: "", hidden: !(H.baby && H.baby.preview) }); if (H.baby && H.baby.preview) babyImg.src = H.baby.preview;
      const babyInput = h("input", { type: "file", id: "baby-input", accept: "image/*", class: "file" });
      const babyLabel = h("label", { for: "baby-input", class: "btn add" }, H.baby && H.baby.path ? "Replace baby photo" : "+ Add your baby photo");
      babyInput.addEventListener("change", async () => {
        const f = babyInput.files[0]; babyInput.value = ""; if (!f) return;
        babyStatus.textContent = "Uploading…";
        try {
          const { data, preview } = await shrink(f);
          const id = "baby" + Date.now().toString(36);
          const res = await post("/media", { id, data });
          H.baby = { id, path: res.path, preview }; babyImg.src = preview; babyImg.hidden = false;
          babyStatus.textContent = "Uploaded."; babyLabel.textContent = "Replace baby photo"; save();
        } catch (e) { babyStatus.textContent = e.message; }
      });
      el.append(h("section", { class: "q" }, h("h3", {}, "Your baby photo"),
        h("p", {}, "One photo of you as a baby or little kid. Keep it to yourself!"),
        h("div", { class: "photo-head" }, babyImg, h("div", {}, babyLabel, babyInput, babyStatus))));
      el.append(h("h3", { class: "subhead" }, "Photos with the group"));
      const input = h("input", { type: "file", id: "photos-input", accept: "image/*", multiple: true, class: "file" });
      const count = h("p", { class: "hint count" });
      const list = h("div", { class: "stack-list" });
      const draw = () => {
        const done = H.photos.filter(p => p.path).length;
        count.textContent = H.photos.length ? `${done} of ${H.photos.length} uploaded` : "";
        list.replaceChildren(...H.photos.map(p => photoCard(H, p, gone => { H.photos.splice(H.photos.indexOf(gone), 1); save(); draw(); })));
        addBtn.textContent = H.photos.length ? "+ Add more photos" : "+ Add photos";
      };
      const addBtn = h("label", { for: "photos-input", class: "btn add" });
      input.addEventListener("change", async () => {
        const files = [...input.files]; input.value = "";
        if (!files.length) return;
        await uploadPhotos(H, files, draw); draw();
      });
      draw();
      el.append(addBtn, input, count, list);
      if (H.photos.length > 2) el.append(h("label", { for: "photos-input", class: "btn add" }, "+ Add more photos"));
      el.append(h("section", { class: "q" }, h("h3", {}, "Videos"),
        C.albumLink ? h("p", {}, "Videos are too big for this form. Add them to the ", h("a", { href: C.albumLink, target: "_blank", rel: "noopener" }, "shared video folder"), ", then tell us what you added:")
          : h("p", {}, "Videos are too big for this form. Send them to Ryan directly, then tell us what you sent:"),
        textField(H, "videos", { multiline: true, placeholder: "e.g. 2 videos: karaoke 2024, first lab retreat", max: 600 })));
    });
    add("Off the record", el => {
      const F = get(A, ["F"]);
      el.append(h("p", { class: "eyebrow" }, "Off the record"), h("h2", {}, isAway ? "One last thing" : "Two last things"),
        q("F1", "What is a fun fact about yourself that not many people know?", h("p", { class: "hint" }, "3 sentences max. Used anonymously in a \"who wrote this?\" game."), textField(F, "F1", { multiline: true, max: 400 })),
        isAway ? null : q("F2", "Is there anything you'd like to get out of this weekend?", h("p", { class: "hint" }, "Optional. Goes to Ryan so he can plan around it."), textField(F, "F2", { multiline: true })));
    });
  } else {
    intro("Part 2: The Network", [
      "This part is about everyone else: how you know them, how you see them, and how well you can read them. It takes about 20 minutes.",
      h("dl", { class: "who-sees" },
        h("dt", {}, "Everyone will see"), h("dd", {}, "the network map, Unexpected Pairings, the group's split on hot takes, Traitors trust and suspicion counts, and the Prom Award finalists."),
        h("dt", {}, "Nobody will see"), h("dd", {}, "how you rated or described any individual person. Ratings are combined into scores by a script.")),
      "There are no right answers, and you can skip anything. Your progress saves on this device as you go.",
    ]);
    const words = shuffle(Object.values(Q.WORDS).flat(), seeded(me + ":words"));
    add("Your own words", el => {
      const AA = get(A, ["A"]);
      el.append(h("p", { class: "eyebrow" }, "Your people"), h("h2", {}, "Start with you"),
        q("A0a", "Pick the 3 words that describe you best.", multiPick(AA, "self", words, 3, { cls: "words" })));
      const hist = get(AA, ["history"]);
      const grid = h("div", { class: "grid-q" });
      others.forEach(n => grid.append(h("div", { class: "grid-row" }, h("span", { class: "gname" }, n), segmented(hist, n, ["<6 mo", "6–12 mo", "1–2 yr", "2–5 yr", "5+ yr"], { cls: "small", aria: `How long you've known ${n}` }))));
      el.append(q("A0b", "How long have you known each person?", grid));
    });
    const order = others;
    order.forEach((n, k) => add(n, el => {
      const P = get(A, ["A", "people", n]);
      const noTrust = nonPlayers.includes(n) || nonPlayers.includes(me);
      el.append(h("p", { class: "eyebrow" }, `Your people · ${k + 1} of ${order.length}`), h("h2", { class: "person" }, n));
      const skipBox = h("input", { type: "checkbox", id: `unk-${n}` }); skipBox.checked = !!P.unknown;
      const wordsQs = h("div", { class: "qgroup" },
        q("A3", `Pick 3 words that describe ${n}.`, multiPick(P, "words", words, 3, { cls: "words" })),
        q("A4", `Which 3 words do you think ${n} would pick to describe you?`, multiPick(P, "meta", words, 3, { cls: "words" })));
      const metaTrust = noTrust ? null : q("A6", `How much do you think ${n} would trust you?`, segmented(P, "metaTrust", ["1", "2", "3", "4", "5"], { cls: "scale5" }), h("p", { class: "hint scale-ends" }, h("span", {}, "Not at all"), h("span", {}, "Completely")));
      const paintSkip = () => { wordsQs.hidden = skipBox.checked; if (metaTrust) metaTrust.hidden = skipBox.checked; };
      skipBox.addEventListener("change", () => { P.unknown = skipBox.checked; paintSkip(); save(); });
      el.append(...[h("label", { class: "check", for: `unk-${n}` }, skipBox, `I haven't really gotten to know ${n} yet`),
        q("A1", `Which picture best describes your relationship with ${n}?`, ios(P, "ios"), h("p", { class: "hint scale-ends" }, h("span", {}, "Separate"), h("span", {}, "Very close"))),
        q("A2", `In the last 3 months, how often have you spent time with ${n} one-on-one or in a group of 4 or fewer?`, segmented(P, "time", Q.SHARED_TIME, { cls: "stack" })),
        wordsQs,
        noTrust ? null : q("A5", `How much would you trust ${n} as an ally in Traitors?`, segmented(P, "trust", ["1", "2", "3", "4", "5"], { cls: "scale5" }), h("p", { class: "hint scale-ends" }, h("span", {}, "Not at all"), h("span", {}, "Completely"))),
        metaTrust].filter(Boolean));
      paintSkip();
    }));

    const targets = (C.prediction[me] || []).slice().sort((a, b) => a[0].localeCompare(b[0]));
    add("Read your friends", el => {
      el.append(h("p", { class: "eyebrow" }, "Read your friends"), h("h1", {}, "The prediction game"),
        h("p", {}, `Next are ${targets.length} people from the group. For each one, guess how they answered six questions from Part 1. Every person you're guessing about is also guessing about you. Scores get revealed at the cottage.`));
    }, { intro: true });
    targets.forEach(([t, block], k) => add(`Predict ${t}`, el => {
      const bucket = get(A, ["C", t]);
      el.append(h("p", { class: "eyebrow" }, `Read your friends · ${k + 1} of ${targets.length}`), h("h2", { class: "person" }, `How did ${t} answer?`));
      allItems.filter(it => it.block === block).forEach(it => el.append(
        it.kind === "likert" ? q("", it.text, likert(bucket, it.id)) : q("", "This or that", tot(bucket, it.id, it.a, it.b))));
    }));

    const nomScreen = (title, ids) => add(title, el => {
      const D = get(A, ["D"]);
      el.append(h("p", { class: "eyebrow" }, "Who would you…"), h("h2", {}, title));
      Q.D.filter(d => ids.includes(d[0])).forEach(([id, text, max, ex]) =>
        el.append(q(id.replace("D0", "D"), text, multiPick(D, id, poolFor(id, ex), max))));
    });
    nomScreen("Your people", ["D01", "D02", "D03", "D04", "D05", "D06", "D07", "D08", "D09"]);
    nomScreen("The game", ["D10", "D11", "D12", "D13"]);

    add("The group's view", el => {
      const E = get(A, ["E"]);
      el.append(h("p", { class: "eyebrow" }, "The group's view"), h("h2", {}, "Unexpected Pairings and more"),
        h("p", { class: "lede" }, "You're the observer here. Pairs never include you."));
      Q.E.forEach(([id, text, kind, n, ex]) => {
        const pool = poolFor(id, ex);
        el.append(q(id.replace("E0", "E"), text, kind === "pair" ? pairPicker(E, id, pool, n) : multiPick(E, id, pool, n)));
      });
    });
    add("Prom Awards", el => {
      const G = get(A, ["G"]);
      el.append(h("p", { class: "eyebrow" }, "Prom Awards"), h("h2", {}, "Yearbook superlatives"),
        h("p", { class: "lede" }, "Nominate one person for each. Skip any you can't decide. The top 3 become finalists on the Prom ballot."));
      const pick = (id, label, pool) => {
        const fid = `g-${id}`;
        const s = h("select", { id: fid }, h("option", { value: "" }, "Choose…"), ...pool.map(n => h("option", { value: n, selected: (G[id] || [])[0] === n }, n)));
        s.addEventListener("change", () => { G[id] = s.value ? [s.value] : []; save(); });
        return h("div", { class: "field award" }, h("label", { for: fid }, label), s);
      };
      const cats = [...new Set(Q.G.map(g => g[3]))];
      cats.forEach(cat => {
        const box = h("section", { class: "q" }, h("h3", {}, cat));
        Q.G.filter(g => g[3] === cat).forEach(([id, award, ex]) => {
          box.append(pick(id, award, ex ? players : others));
          if (Q.G_STORY && Q.G_STORY[id]) box.append(textField(get(A, ["G_text"]), id, { label: Q.G_STORY[id], multiline: true, max: 600 }));
        });
        if (cat === "Grad school" && Q.SUPERVISORS && Q.SUPERVISORS.length) box.append(pick("G22", "Most Eccentric Supervisor (if they win, their student shares their best story at Prom)", [...Q.SUPERVISORS].sort((a, b) => a.localeCompare(b))));
        el.append(box);
      });
    });
  }

  add("Submit", el => {
    el.append(h("p", { class: "eyebrow" }, `Part ${part}`), h("h1", {}, state.submittedAt ? "Submitted. Want to update?" : "Ready to send"));
    el.append(h("p", {}, state.submittedAt
      ? `Your answers were saved on ${new Date(state.submittedAt).toLocaleString()}. You can change anything and submit again; the newest version replaces the old one.`
      : "Your answers go straight into the group's survey data. You can come back to this link and resubmit until Sunday Nov 22."));
    const status = h("p", { class: "status", "aria-live": "polite" });
    const btn = h("button", { type: "button", class: "btn primary", onclick: async () => {
      btn.disabled = true; status.textContent = "Sending…";
      try {
        const submittedAt = new Date().toISOString();
        const clean = JSON.parse(JSON.stringify(A));
        if (clean.H?.photos) clean.H.photos = clean.H.photos.filter(p => p && p.path).map(({ preview, error, ...p }) => p);
        if (clean.H?.baby) delete clean.H.baby.preview;
        if (clean.H?.quotes) clean.H.quotes = clean.H.quotes.filter(q => q && (q.text || "").trim());
        await post("/submit", { answers: clean, meta: { startedAt: state.startedAt, submittedAt, version: VERSION } });
        state.submittedAt = submittedAt; save();
        status.textContent = part === 1 ? "Saved. Thank you! Part 2 arrives later this week." : "Saved. Thank you! See you at Winterhouse.";
        status.classList.add("ok");
      } catch (e) { status.textContent = e.message; status.classList.add("err"); }
      btn.disabled = false;
    } }, state.submittedAt ? "Submit again" : "Submit");
    el.append(btn, status);
  });

  // ---------- shell ----------
  const bar = h("div", { class: "bar" }, h("div", { class: "fill" }));
  const crumb = h("span", { class: "crumb" });
  const header = h("header", { class: "top" }, h("div", { class: "top-inner" }, h("span", { class: "brand" }, "Winterhouse"), crumb), bar,
    pilot ? h("div", { class: "pilot-band" }, "Pilot run: answers save to a separate test folder") : null);
  const main = h("main", { class: "screen", tabindex: "-1" });
  const back = h("button", { type: "button", class: "btn ghost", onclick: () => go(-1) }, "Back");
  const next = h("button", { type: "button", class: "btn primary", onclick: () => go(1) }, "Next");
  const footer = h("footer", { class: "nav" }, h("div", { class: "nav-inner" }, back, next));
  app.append(header, main, footer);

  function render() {
    state.idx = Math.max(0, Math.min(state.idx, screens.length - 1));
    const s = screens[state.idx];
    main.replaceChildren();
    s.build(main);
    crumb.textContent = `Part ${part} · ${state.idx + 1}/${screens.length}`;
    bar.firstChild.style.width = `${((state.idx + 1) / screens.length) * 100}%`;
    back.hidden = state.idx === 0;
    next.hidden = state.idx === screens.length - 1;
    next.textContent = s.intro ? "Start" : "Next";
    window.scrollTo(0, 0);
    main.focus({ preventScroll: true });
    save();
  }
  function go(d) { state.idx += d; render(); }
  render();
  // Opening the link on a new device: bring back what they already submitted.
  if (freshDevice && C.endpoint) {
    post("/load", {}).then(res => {
      if (!res.found || !res.answers || Object.keys(A).length) return;
      Object.assign(A, res.answers);
      state.submittedAt = res.submittedAt || state.submittedAt;
      render();
      const note = h("p", { class: "restored" }, "We've loaded the answers you already sent. Pick up where you left off, then submit again to save changes.");
      main.prepend(note);
    }).catch(() => {});
  }
})();
