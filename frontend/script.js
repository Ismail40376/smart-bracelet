(() => {
  "use strict";

  /* ===================== Движение и тема ===================== */
  const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)");
  const root = document.documentElement;
  const THEME_COLORS = { red: "#d7263d", green: "#15874f", orange: "#ffa13a", yellow: "#ffe55c" };
  const THEME_KEY = "bracelet-color";

  const safeGet = (k) => { try { return localStorage.getItem(k); } catch { return null; } };
  const safeSet = (k, v) => { try { localStorage.setItem(k, v); } catch { /* хранилище недоступно */ } };
  const safeGetSession = (k) => { try { return sessionStorage.getItem(k); } catch { return null; } };
  const safeSetSession = (k, v) => { try { v === null ? sessionStorage.removeItem(k) : sessionStorage.setItem(k, v); } catch { /* ничего */ } };

  const colorButtons = [...document.querySelectorAll("[data-color]")];
  const metaTheme = document.querySelector('meta[name="theme-color"]');
  const braceletWrap = document.getElementById("braceletWrap");
  let inkTimer = 0, prevTimer = 0;

  function clearPrev() { document.querySelectorAll(".prev").forEach((n) => n.classList.remove("prev")); }

  /* Фон, ореол и ремешок меняются наложением слоёв (opacity). Цвет текста
     переключается на середине наложения, чтобы контраст не проваливался. */
  function setTheme(name, save = true) {
    if (!THEME_COLORS[name]) name = "red";
    const old = root.dataset.theme;
    const animate = old !== name && !reduceMotion.matches;

    clearTimeout(inkTimer); clearTimeout(prevTimer); clearPrev();
    if (animate) {
      document.querySelectorAll(`.bg-layer[data-c="${old}"], .halo[data-c="${old}"], .strap-layer[data-c="${old}"]`)
        .forEach((n) => n.classList.add("prev"));
    }
    root.dataset.theme = name;
    if (metaTheme) metaTheme.content = THEME_COLORS[name];
    colorButtons.forEach((b) => {
      const on = b.dataset.color === name;
      b.setAttribute("aria-checked", String(on));
      b.tabIndex = on ? 0 : -1;
    });

    if (animate) {
      inkTimer = setTimeout(() => { root.dataset.ink = name; }, 140);
      prevTimer = setTimeout(clearPrev, 450);
      braceletWrap.classList.remove("pop"); void braceletWrap.offsetWidth; braceletWrap.classList.add("pop");
    } else {
      root.dataset.ink = name;
    }
    if (save) safeSet(THEME_KEY, name);
  }

  document.querySelectorAll("[data-group]").forEach((group) => {
    const items = [...group.querySelectorAll("[data-color]")];
    items.forEach((b, i) => {
      b.addEventListener("click", () => setTheme(b.dataset.color));
      b.addEventListener("keydown", (e) => {
        const step = { ArrowRight: 1, ArrowDown: 1, ArrowLeft: -1, ArrowUp: -1 }[e.key];
        if (!step) return;
        e.preventDefault();
        const next = items[(i + step + items.length) % items.length];
        next.focus();
        setTheme(next.dataset.color);
      });
    });
  });
  setTheme(root.dataset.theme || "red", false);

  /* Плавающий выбор цвета появляется, когда главный блок ушёл с экрана */
  const dock = document.getElementById("dock");
  if ("IntersectionObserver" in window) {
    new IntersectionObserver(([e]) => dock.classList.toggle("show", e.intersectionRatio < 0.35), { threshold: [0, 0.35, 1] })
      .observe(document.getElementById("hero"));
  } else { dock.classList.add("show"); }

  /* Появление блоков при прокрутке */
  const revealNodes = [...document.querySelectorAll("[data-reveal]")];
  if ("IntersectionObserver" in window) {
    const io = new IntersectionObserver((entries) => entries.forEach((e) => {
      if (e.isIntersecting) { e.target.classList.add("in"); io.unobserve(e.target); }
    }), { threshold: 0.12, rootMargin: "0px 0px -6% 0px" });
    revealNodes.forEach((n) => io.observe(n));
  } else { revealNodes.forEach((n) => n.classList.add("in")); }

  /* ===================== Экран браслета ===================== */
  const scrNum = document.getElementById("scrNum");
  const scrLabel = document.getElementById("scrLabel");
  const bigNum = document.getElementById("bigNum");
  const braceletSvg = document.querySelector(".bracelet");
  let liveHr = null;

  function setBeat(hr) {
    const s = Math.min(2, Math.max(0.3, 60 / hr));
    braceletSvg.style.setProperty("--beat", s.toFixed(2) + "s");
  }
  function setScreen(hr) {
    liveHr = hr;
    if (hr == null) { scrLabel.textContent = "демо"; setBeat(72); return; }
    scrLabel.textContent = "ваш браслет";
    scrNum.textContent = String(hr);
    if (bigNum) bigNum.textContent = String(hr);
    setBeat(hr);
  }
  setBeat(72);
  setInterval(() => {
    if (liveHr == null) {
      const v = 70 + Math.round(Math.random() * 6);
      scrNum.textContent = String(v);
      if (bigNum) bigNum.textContent = String(v);
      setBeat(v);
    }
  }, 1800);

  /* Подсказки и демо кнопки SOS */
  const hint = document.getElementById("hint");
  const toast = document.getElementById("toast");
  const scrSos = document.getElementById("scrSos");
  let toastTimer = 0, sosBusy = false;

  function say(text) {
    if (hint.textContent === text) return;
    hint.textContent = text;
    hint.classList.remove("swap"); void hint.offsetWidth; hint.classList.add("swap");
  }
  function showToast(text, ms) {
    toast.textContent = text;
    toast.classList.add("show");
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => toast.classList.remove("show"), ms);
  }
  document.querySelectorAll(".hot").forEach((h) => {
    ["mouseenter", "focus"].forEach((ev) => h.addEventListener(ev, () => say(h.dataset.hint)));
  });
  document.getElementById("sosBtn").addEventListener("click", () => {
    if (sosBusy) return;
    sosBusy = true;
    scrSos.classList.add("on");
    braceletWrap.classList.remove("shake"); void braceletWrap.offsetWidth; braceletWrap.classList.add("shake");
    showToast("Демо: так браслет отправляет просьбу о помощи. Экстренные службы не вызываются.", 3600);
    setTimeout(() => { scrSos.classList.remove("on"); sosBusy = false; }, 2200);
  });

  function bump(id) {
    const n = document.getElementById(id);
    if (!n) return;
    n.classList.remove("bump"); void n.offsetWidth; n.classList.add("bump");
  }

  /* ===================== API ===================== */
  const TOKEN_KEY = "bracelet-token";
  let token = safeGetSession(TOKEN_KEY);

  class ApiError extends Error {
    constructor(status, message) { super(message); this.status = status; }
  }

  function errorText(body, status) {
    const d = body && body.detail;
    if (typeof d === "string") return d;
    if (Array.isArray(d) && d.length) {
      return d.map((x) => {
        const field = Array.isArray(x.loc) ? x.loc[x.loc.length - 1] : "";
        return field ? `${field}: ${x.msg}` : x.msg;
      }).join("; ");
    }
    return `Сервер ответил с кодом ${status}`;
  }

  async function api(path, { method = "GET", body, headers = {}, auth = true } = {}) {
    const h = { Accept: "application/json", ...headers };
    if (body !== undefined) h["Content-Type"] = "application/json";
    if (auth && token) h.Authorization = `Bearer ${token}`;
    let res;
    try {
      res = await fetch(path, { method, headers: h, body: body !== undefined ? JSON.stringify(body) : undefined });
    } catch {
      throw new ApiError(0, "Нет связи с сервером. Проверьте, что он запущен.");
    }
    if (res.status === 204) return null;
    let data = null;
    try { data = await res.json(); } catch { /* пустой ответ */ }
    if (!res.ok) {
      if (res.status === 401 && auth && token) {
        logout();
        throw new ApiError(401, "Сессия закончилась. Войдите снова.");
      }
      throw new ApiError(res.status, errorText(data, res.status));
    }
    return data;
  }

  /* ===================== Вспомогательное ===================== */
  const $ = (id) => document.getElementById(id);
  const fmtDate = (iso) => new Date(iso).toLocaleString("ru-RU", { day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit", second: "2-digit" });
  const num = (v, d = 0) => (v === null || v === undefined ? "—" : Number(v).toFixed(d).replace(/\.0+$/, ""));

  function el(tag, props = {}, ...kids) {
    const n = document.createElement(tag);
    Object.entries(props).forEach(([k, v]) => {
      if (k === "class") n.className = v;
      else if (k === "onclick") n.addEventListener("click", v);
      else n.setAttribute(k, v);
    });
    kids.forEach((k) => n.append(k));
    return n;
  }

  function setMsg(node, text, kind = "err") {
    if (!node) return;
    node.textContent = text || "";
    node.className = "msg" + (text ? " " + kind : "");
  }
  const formMsg = (form) => form.querySelector("[data-msg]");

  async function guarded(form, fn) {
    const btn = form.querySelector('button[type="submit"]');
    const msg = formMsg(form);
    setMsg(msg, "");
    if (btn) btn.disabled = true;
    try { await fn(); }
    catch (e) { setMsg(msg, e.message || "Что-то пошло не так"); }
    finally { if (btn) btn.disabled = false; }
  }

  /* ===================== Вход / регистрация ===================== */
  const guest = $("guest"), dash = $("dash");
  const tabLogin = $("tabLogin"), tabRegister = $("tabRegister");
  const formLogin = $("formLogin"), formRegister = $("formRegister");

  function showTab(which) {
    const login = which === "login";
    tabLogin.setAttribute("aria-selected", String(login));
    tabRegister.setAttribute("aria-selected", String(!login));
    formLogin.hidden = !login;
    formRegister.hidden = login;
  }
  tabLogin.addEventListener("click", () => showTab("login"));
  tabRegister.addEventListener("click", () => showTab("register"));
  document.querySelectorAll("[data-switch]").forEach((b) => b.addEventListener("click", () => showTab(b.dataset.switch)));
  document.querySelectorAll(".reveal").forEach((b) => b.addEventListener("click", () => {
    const input = b.parentElement.querySelector("input");
    const show = input.type === "password";
    input.type = show ? "text" : "password";
    input.classList.toggle("shown", show);
    b.textContent = show ? "Скрыть" : "Показать";
    b.setAttribute("aria-pressed", String(show));
  }));

  formLogin.addEventListener("submit", (e) => {
    e.preventDefault();
    guarded(formLogin, async () => {
      const f = new FormData(formLogin);
      const data = await api("/auth/login", { method: "POST", auth: false, body: { email: f.get("email").trim(), password: f.get("password") } });
      token = data.access_token;
      safeSetSession(TOKEN_KEY, token);
      formLogin.reset();
      await enterCabinet();
    });
  });

  formRegister.addEventListener("submit", (e) => {
    e.preventDefault();
    guarded(formRegister, async () => {
      const f = new FormData(formRegister);
      const email = f.get("email").trim();
      const password = f.get("password");
      await api("/auth/register", { method: "POST", auth: false, body: { name: f.get("name"), email, password } });
      const data = await api("/auth/login", { method: "POST", auth: false, body: { email, password } });
      token = data.access_token;
      safeSetSession(TOKEN_KEY, token);
      formRegister.reset();
      await enterCabinet();
    });
  });

  function logout() {
    token = null;
    safeSetSession(TOKEN_KEY, null);
    state.bracelets = [];
    state.currentId = null;
    state.keys = {};
    setScreen(null);
    dash.hidden = true;
    guest.hidden = false;
    $("navCabinet").textContent = "Войти";
    $("keyBox").hidden = true;
  }
  $("logout").addEventListener("click", logout);

  /* ===================== Кабинет ===================== */
  const state = { bracelets: [], currentId: null, keys: {} };
  const select = $("braceletSelect");

  async function enterCabinet() {
    const me = await api("/auth/me");
    $("userName").textContent = me.name;
    $("navCabinet").textContent = "Кабинет";
    guest.hidden = true;
    dash.hidden = false;
    await loadBracelets();
    await loadNotifications();
  }

  async function loadBracelets(selectId) {
    state.bracelets = await api("/bracelets");
    select.replaceChildren(...state.bracelets.map((b) => el("option", { value: b.id }, b.name)));
    const has = state.bracelets.length > 0;
    $("noBracelets").hidden = has;
    $("braceletTools").hidden = !has;
    if (has) {
      const keep = selectId ?? state.currentId;
      state.currentId = state.bracelets.some((b) => b.id === keep) ? keep : state.bracelets[0].id;
      select.value = String(state.currentId);
      await loadBraceletData();
    } else {
      state.currentId = null;
      clearBraceletData();
    }
  }

  select.addEventListener("change", async () => {
    state.currentId = Number(select.value);
    $("keyBox").hidden = true;
    await loadBraceletData();
  });

  const cur = () => state.bracelets.find((b) => b.id === state.currentId);

  function clearBraceletData() {
    ["vHr", "vSpo2", "vBat"].forEach((i) => ($(i).textContent = "—"));
    $("vWhen").textContent = "Измерений пока нет.";
    $("vLoc").textContent = "";
    $("histBody").replaceChildren();
    $("histEmpty").hidden = false;
    $("ruleList").replaceChildren();
    $("ruleEmpty").hidden = true;
    setScreen(null);
  }

  async function loadBraceletData() {
    const b = cur();
    if (!b) return;
    $("formRename").elements.name.value = b.name;
    const keyField = $("formEmu").elements.key;
    keyField.value = state.keys[b.id] || "";
    await Promise.all([loadLatest(), loadHistory(), loadRules(), loadLocation()]);
  }

  async function loadLatest() {
    const id = state.currentId;
    try {
      const m = await api(`/bracelets/${id}/measurements/latest`);
      if (id !== state.currentId) return;
      $("vHr").textContent = num(m.heart_rate);
      $("vSpo2").textContent = num(m.spo2, 1);
      $("vBat").textContent = num(m.battery_level);
      ["vHr", "vSpo2", "vBat"].forEach(bump);
      $("vWhen").textContent = `Измерено ${fmtDate(m.measured_at)}`;
      setScreen(m.heart_rate);
    } catch (e) {
      if (e.status === 404) {
        ["vHr", "vSpo2", "vBat"].forEach((i) => ($(i).textContent = "—"));
        $("vWhen").textContent = "Измерений пока нет.";
        setScreen(null);
      } else if (e.status !== 401) { $("vWhen").textContent = e.message; }
    }
  }

  async function loadLocation() {
    const id = state.currentId;
    const out = $("vLoc");
    out.textContent = "";
    try {
      const l = await api(`/bracelets/${id}/locations/latest`);
      if (id !== state.currentId) return;
      out.textContent = `Последняя точка: ${l.latitude.toFixed(5)}, ${l.longitude.toFixed(5)} (${fmtDate(l.recorded_at)})`;
    } catch (e) {
      if (e.status === 404) out.textContent = "Координат пока нет.";
    }
  }

  async function loadHistory() {
    const id = state.currentId;
    try {
      const rows = await api(`/bracelets/${id}/measurements?limit=20`);
      if (id !== state.currentId) return;
      $("histBody").replaceChildren(...rows.map((m) => el("tr", {},
        el("td", {}, fmtDate(m.measured_at)),
        el("td", {}, num(m.heart_rate)),
        el("td", {}, num(m.spo2, 1)),
        el("td", {}, num(m.battery_level)),
      )));
      $("histEmpty").hidden = rows.length > 0;
    } catch (e) { if (e.status !== 401) { $("histEmpty").hidden = false; $("histEmpty").textContent = e.message; } }
  }

  /* --- уведомления --- */
  async function loadNotifications() {
    try {
      const rows = await api("/notifications?limit=20");
      $("notList").replaceChildren(...rows.map((n) => el("li", { class: n.is_read ? "" : "unread" },
        el("div", { class: "txt" }, el("span", {}, n.message), el("span", { class: "when" }, fmtDate(n.created_at))),
        n.is_read ? document.createTextNode("") : el("button", { class: "btn btn-small btn-ghost", type: "button", onclick: async () => {
          try { await api(`/notifications/${n.id}/read`, { method: "PATCH" }); await loadNotifications(); } catch (e) { alert(e.message); }
        } }, "Прочитано"),
      )));
      $("notEmpty").hidden = rows.length > 0;
    } catch (e) { if (e.status !== 401) { $("notEmpty").hidden = false; $("notEmpty").textContent = e.message; } }
  }

  /* --- правила --- */
  const METRIC = { heart_rate: "Пульс", spo2: "SpO₂", battery_level: "Заряд" };

  function ruleText(r) {
    const parts = [];
    if (r.min_value !== null) parts.push(`не ниже ${num(r.min_value, 1)}`);
    if (r.max_value !== null) parts.push(`не выше ${num(r.max_value, 1)}`);
    return `${METRIC[r.metric] || r.metric}: ${parts.join(", ")}`;
  }

  async function loadRules() {
    const id = state.currentId;
    try {
      const rules = await api(`/bracelets/${id}/alert-rules`);
      if (id !== state.currentId) return;
      $("ruleList").replaceChildren(...rules.map((r) => el("li", {},
        el("div", { class: "txt" }, el("span", {}, ruleText(r)), el("span", { class: "when" }, r.enabled ? "Включено" : "Выключено")),
        el("div", { class: "acts" },
          el("button", { class: "btn btn-small btn-ghost", type: "button", onclick: async () => {
            try { await api(`/bracelets/${id}/alert-rules/${r.id}`, { method: "PATCH", body: { enabled: !r.enabled } }); await loadRules(); } catch (e) { alert(e.message); }
          } }, r.enabled ? "Выключить" : "Включить"),
          el("button", { class: "btn btn-small btn-ghost", type: "button", onclick: async () => {
            try { await api(`/bracelets/${id}/alert-rules/${r.id}`, { method: "DELETE" }); await loadRules(); } catch (e) { alert(e.message); }
          } }, "Удалить"),
        ),
      )));
      $("ruleEmpty").hidden = rules.length > 0;
    } catch (e) { if (e.status !== 401) { $("ruleEmpty").hidden = false; $("ruleEmpty").textContent = e.message; } }
  }

  $("formRule").addEventListener("submit", (e) => {
    e.preventDefault();
    const form = e.currentTarget;
    guarded(form, async () => {
      if (!state.currentId) throw new Error("Сначала добавьте браслет.");
      const f = new FormData(form);
      const min = f.get("min"), max = f.get("max");
      const body = { metric: f.get("metric"), min_value: min === "" ? null : Number(min), max_value: max === "" ? null : Number(max) };
      await api(`/bracelets/${state.currentId}/alert-rules`, { method: "POST", body });
      form.elements.min.value = ""; form.elements.max.value = "";
      await loadRules();
    });
  });

  /* --- добавление, переименование, ключ --- */
  function showKey(key) {
    $("keyValue").textContent = key;
    $("keyBox").hidden = false;
  }

  $("formAddBracelet").addEventListener("submit", async (e) => {
    e.preventDefault();
    const form = e.currentTarget;
    const msg = $("msgBracelet");
    setMsg(msg, "");
    try {
      const b = await api("/bracelets", { method: "POST", body: { name: new FormData(form).get("name") } });
      state.keys[b.id] = b.device_key;
      form.reset();
      await loadBracelets(b.id);
      showKey(b.device_key);
      $("formEmu").elements.key.value = b.device_key;
      setMsg(msg, "Браслет добавлен.", "ok");
    } catch (err) { setMsg(msg, err.message); }
  });

  $("formRename").addEventListener("submit", async (e) => {
    e.preventDefault();
    const msg = $("msgBracelet");
    setMsg(msg, "");
    try {
      await api(`/bracelets/${state.currentId}`, { method: "PATCH", body: { name: new FormData(e.currentTarget).get("name") } });
      await loadBracelets(state.currentId);
      setMsg(msg, "Название сохранено.", "ok");
    } catch (err) { setMsg(msg, err.message); }
  });

  $("rotateKey").addEventListener("click", async () => {
    const msg = $("msgBracelet");
    setMsg(msg, "");
    if (!confirm("Старый ключ перестанет работать. Выпустить новый?")) return;
    try {
      const b = await api(`/bracelets/${state.currentId}/rotate-key`, { method: "POST" });
      state.keys[b.id] = b.device_key;
      showKey(b.device_key);
      $("formEmu").elements.key.value = b.device_key;
      setMsg(msg, "Новый ключ выпущен. Обновите его в прошивке.", "ok");
    } catch (err) { setMsg(msg, err.message); }
  });

  $("copyKey").addEventListener("click", async (e) => {
    try { await navigator.clipboard.writeText($("keyValue").textContent); e.currentTarget.textContent = "Скопировано"; }
    catch { e.currentTarget.textContent = "Выделите и скопируйте вручную"; }
  });

  /* --- тестовое измерение (как это делает браслет) --- */
  $("formEmu").addEventListener("submit", (e) => {
    e.preventDefault();
    const form = e.currentTarget;
    guarded(form, async () => {
      if (!state.currentId) throw new Error("Сначала добавьте браслет.");
      const f = new FormData(form);
      const body = { measured_at: new Date().toISOString() };
      if (f.get("hr") !== "") body.heart_rate = Number(f.get("hr"));
      if (f.get("spo2") !== "") body.spo2 = Number(f.get("spo2"));
      if (f.get("bat") !== "") body.battery_level = Number(f.get("bat"));
      await api(`/bracelets/${state.currentId}/measurements`, {
        method: "POST", auth: false, body, headers: { "X-Device-Key": f.get("key") },
      });
      setMsg(formMsg(form), "Измерение отправлено.", "ok");
      await Promise.all([loadLatest(), loadHistory(), loadNotifications()]);
    });
  });

  /* ===================== Старт ===================== */
  if (token) {
    enterCabinet().catch(() => logout());
  }
})();
