const RLT_CARD_VERSION = "0.4.0-beta.1";

const CATEGORY_META = [
  ["starter", "Entrée", "🥗"],
  ["main_course", "Plat principal", "🍽️"],
  ["side", "Garniture", "🥕"],
  ["dairy", "Produit laitier", "🧀"],
  ["dessert", "Dessert", "🍎"],
  ["other", "Autre", "•"],
];

const DEFAULT_CATEGORIES = CATEGORY_META.map(([key]) => key);
const DEFAULT_DAY_MODES = new Set(["smart", "today", "next", "first"]);


const LABEL_PRIORITY = [
  "organic", "local", "home_made", "label_rouge", "aop", "igp", "msc", "hve",
  "meat", "fish", "egg", "plant_based", "fruit", "vegetable", "starch", "dairy",
];

const REDUNDANT_LABELS_BY_CATEGORY = {
  dairy: new Set(["dairy"]),
};

const LABEL_META = {
  organic: ["🌱", "Bio"],
  local: ["📍", "Local"],
  home_made: ["🏠", "Fait maison"],
  meat: ["🥩", "Viande"],
  fish: ["🐟", "Poisson"],
  egg: ["🥚", "Œuf"],
  dairy: ["🥛", "Laitier"],
  plant_based: ["🥬", "Végétal"],
  fruit: ["🍏", "Fruit"],
  vegetable: ["🥦", "Légume"],
  starch: ["🌾", "Féculent"],
  label_rouge: ["LR", "Label Rouge"],
  aop: ["AOP", "AOP"],
  igp: ["IGP", "IGP"],
  msc: ["MSC", "MSC"],
  hve: ["HVE", "HVE"],
};

function esc(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function parseDateOnly(value) {
  if (typeof value !== "string") return null;
  const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(value.trim());
  if (!match) return null;
  const year = Number(match[1]);
  const month = Number(match[2]);
  const day = Number(match[3]);
  const date = new Date(Date.UTC(year, month - 1, day));
  if (
    date.getUTCFullYear() !== year ||
    date.getUTCMonth() !== month - 1 ||
    date.getUTCDate() !== day
  ) return null;
  return date;
}

function isoTodayLocal() {
  const now = new Date();
  const year = now.getFullYear();
  const month = String(now.getMonth() + 1).padStart(2, "0");
  const day = String(now.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

function normalizeList(value) {
  if (!Array.isArray(value)) return [];
  return value.map((item) => String(item ?? "").trim()).filter(Boolean);
}

function normalizeDays(rawDays) {
  if (!Array.isArray(rawDays)) return [];
  return rawDays
    .map((raw) => {
      if (!raw || typeof raw !== "object" || !parseDateOnly(raw.date)) return null;
      const day = { date: raw.date, label: String(raw.label || raw.date), details: {} };
      for (const [key] of CATEGORY_META) {
        day[key] = normalizeList(raw[key]);
        const rawDetails = raw.details && Array.isArray(raw.details[key]) ? raw.details[key] : [];
        day.details[key] = rawDetails
          .filter((item) => item && typeof item === "object" && String(item.name || "").trim())
          .map((item) => ({
            name: String(item.name).trim(),
            labels: normalizeList(item.labels).filter((label) => LABEL_META[label]),
          }));
      }
      day.items = normalizeList(raw.items);
      return day;
    })
    .filter(Boolean)
    .sort((a, b) => a.date.localeCompare(b.date));
}

function chooseInitialDay(days, todayIso = isoTodayLocal(), mode = "smart") {
  if (!days.length) return -1;
  const normalizedMode = DEFAULT_DAY_MODES.has(mode) ? mode : "smart";
  const todayIndex = days.findIndex((day) => day.date === todayIso);
  const futureIndex = days.findIndex((day) => day.date > todayIso);
  if (normalizedMode === "first") return 0;
  if (normalizedMode === "today") return todayIndex >= 0 ? todayIndex : (futureIndex >= 0 ? futureIndex : days.length - 1);
  if (normalizedMode === "next") return futureIndex >= 0 ? futureIndex : (todayIndex >= 0 ? todayIndex : days.length - 1);
  if (todayIndex >= 0) return todayIndex;
  return futureIndex >= 0 ? futureIndex : days.length - 1;
}

function shortDayLabel(day) {
  const date = parseDateOnly(day.date);
  if (!date) return day.label;
  const weekday = new Intl.DateTimeFormat("fr-FR", { weekday: "short", timeZone: "UTC" })
    .format(date).replace(".", "");
  const dd = String(date.getUTCDate()).padStart(2, "0");
  return `${weekday.charAt(0).toUpperCase()}${weekday.slice(1)} ${dd}`;
}

function longDayLabel(day) {
  const date = parseDateOnly(day.date);
  if (!date) return day.label;
  const formatted = new Intl.DateTimeFormat("fr-FR", {
    weekday: "long", day: "numeric", month: "long", timeZone: "UTC",
  }).format(date);
  return formatted.charAt(0).toUpperCase() + formatted.slice(1);
}

function weekLabel(stateObj, days) {
  const start = parseDateOnly(stateObj?.attributes?.week_start || days[0]?.date);
  const end = parseDateOnly(stateObj?.attributes?.week_end || days[days.length - 1]?.date);
  if (!start || !end) return "";
  const startDay = start.getUTCDate();
  const endDay = end.getUTCDate();
  const startMonth = new Intl.DateTimeFormat("fr-FR", { month: "long", timeZone: "UTC" }).format(start);
  const endMonth = new Intl.DateTimeFormat("fr-FR", { month: "long", timeZone: "UTC" }).format(end);
  if (start.getUTCMonth() === end.getUTCMonth()) return `Semaine du ${startDay} au ${endDay} ${endMonth}`;
  return `Semaine du ${startDay} ${startMonth} au ${endDay} ${endMonth}`;
}

function schoolName(stateObj, fallback = "Cantine") {
  const friendly = stateObj?.attributes?.friendly_name || "";
  return friendly.replace(/\s+Menu de la semaine$/i, "").trim() || fallback;
}

function normalizeCategories(value) {
  if (!Array.isArray(value)) return [...DEFAULT_CATEGORIES];
  const allowed = new Set(DEFAULT_CATEGORIES);
  const deduped = [];
  for (const item of value) {
    if (allowed.has(item) && !deduped.includes(item)) deduped.push(item);
  }
  return deduped.length ? deduped : [...DEFAULT_CATEGORIES];
}

function categoryItems(day, key) {
  const details = Array.isArray(day?.details?.[key]) ? day.details[key] : [];
  if (details.length) return details;
  return normalizeList(day?.[key]).map((name) => ({ name, labels: [] }));
}

function visibleSemanticLabels(labels, categoryKey = "", showRedundant = false) {
  const unique = [...new Set(normalizeList(labels).filter((label) => LABEL_META[label]))];
  const redundant = REDUNDANT_LABELS_BY_CATEGORY[categoryKey] || new Set();
  const filtered = showRedundant ? unique : unique.filter((label) => !redundant.has(label));
  return filtered.sort((a, b) => {
    const ai = LABEL_PRIORITY.indexOf(a);
    const bi = LABEL_PRIORITY.indexOf(b);
    return (ai < 0 ? 999 : ai) - (bi < 0 ? 999 : bi);
  });
}

function renderSemanticBadges(labels, categoryKey = "", showRedundant = false) {
  const safe = visibleSemanticLabels(labels, categoryKey, showRedundant);
  if (!safe.length) return "";
  return `<span class="semantic-badges" aria-label="${esc(safe.map((label) => LABEL_META[label][1]).join(", "))}">${safe.map((label) => {
    const [mark, title] = LABEL_META[label];
    const textual = mark.length > 2 && !/\p{Extended_Pictographic}/u.test(mark);
    return `<span class="semantic-badge${textual ? " text-badge" : ""}" title="${esc(title)}" aria-label="${esc(title)}">${esc(mark)}</span>`;
  }).join("")}</span>`;
}

function renderChoice(item, showBadges = true, categoryKey = "", showRedundant = false) {
  const normalized = typeof item === "string" ? { name: item, labels: [] } : item;
  return `<span class="choice"><span class="choice-name">${esc(normalized?.name || "")}</span>${showBadges ? renderSemanticBadges(normalized?.labels || [], categoryKey, showRedundant) : ""}</span>`;
}

function renderChoices(values, showBadges = true, categoryKey = "", showRedundant = false) {
  if (!values.length) return "";
  if (values.length === 1) return renderChoice(values[0], showBadges, categoryKey, showRedundant);
  return `<span class="choices-inline">${values.map((item, index) => `${index ? '<span class="choice-separator">ou</span>' : ''}${renderChoice(item, showBadges, categoryKey, showRedundant)}`).join("")}</span>`;
}

function selectedDayBadge(day, days = [], todayIso = isoTodayLocal()) {
  if (!day?.date) return "";
  if (day.date === todayIso) return "Aujourd’hui";

  // "Prochain repas" is contextual, not a generic label for any future day.
  // Show it only when there is no menu for today and the selected day is the
  // first published menu after today.
  const hasToday = days.some((candidate) => candidate?.date === todayIso);
  if (hasToday) return "";

  const nextDay = days
    .filter((candidate) => candidate?.date && candidate.date > todayIso)
    .sort((a, b) => a.date.localeCompare(b.date))[0];
  return nextDay?.date === day.date ? "Prochain repas" : "";
}

class RadisLaToqueCard extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._config = null;
    this._hass = null;
    this._selectedDate = null;
    this._lastEntity = null;
  }

  static getStubConfig(hass) {
    const entity = Object.keys(hass?.states || {}).find(
      (id) => id.startsWith("sensor.") && id.endsWith("_menu_de_la_semaine")
    );
    return entity ? { entity } : {};
  }

  static getConfigElement() {
    return document.createElement("radis-la-toque-card-editor");
  }

  setConfig(config) {
    if (!config || !config.entity) throw new Error("Sélectionnez l'entité « Menu de la semaine ».");
    this._config = {
      entity: config.entity,
      title: typeof config.title === "string" ? config.title : "",
      show_header: config.show_header !== false,
      show_school_name: config.show_school_name !== false,
      show_week: config.show_week !== false,
      show_empty_categories: config.show_empty_categories === true,
      compact: config.compact === true,
      show_semantic_badges: config.show_semantic_badges !== false,
      show_redundant_badges: config.show_redundant_badges === true,
      default_day: DEFAULT_DAY_MODES.has(config.default_day) ? config.default_day : "smart",
      categories: normalizeCategories(config.categories),
    };
    if (this._lastEntity !== this._config.entity) {
      this._selectedDate = null;
      this._lastEntity = this._config.entity;
    }
    this._render();
  }

  set hass(hass) {
    this._hass = hass;
    this._render();
  }

  getCardSize() { return this._config?.compact ? 4 : 5; }
  getGridOptions() { return { columns: 6, min_columns: 3, rows: this._config?.compact ? 4 : 5, min_rows: 3 }; }

  _selectDay(date) {
    this._selectedDate = date;
    this._render();
  }

  _render() {
    if (!this.shadowRoot || !this._config || !this._hass) return;
    const stateObj = this._hass.states[this._config.entity];
    if (!stateObj) {
      this.shadowRoot.innerHTML = this._shell(`<div class="empty">Entité introuvable : <code>${esc(this._config.entity)}</code></div>`);
      return;
    }

    const days = normalizeDays(stateObj.attributes?.days);
    if (!days.length) {
      const unavailable = stateObj.state === "unavailable" || stateObj.state === "unknown";
      const header = this._renderHeader(stateObj, days);
      this.shadowRoot.innerHTML = this._shell(`${header}<div class="empty">${unavailable ? "Menu actuellement indisponible." : "Aucun menu publié pour cette semaine."}</div>`);
      return;
    }

    if (!this._selectedDate || !days.some((day) => day.date === this._selectedDate)) {
      const initialIndex = chooseInitialDay(days, isoTodayLocal(), this._config.default_day);
      this._selectedDate = days[Math.max(0, initialIndex)].date;
    }
    const selected = days.find((day) => day.date === this._selectedDate) || days[0];
    const todayIso = isoTodayLocal();

    const tabs = days.map((day) => {
      const active = day.date === selected.date;
      const today = day.date === todayIso;
      return `<button type="button" class="day-tab${active ? " active" : ""}${today ? " today" : ""}" data-date="${esc(day.date)}" aria-pressed="${active}">
        <span>${esc(shortDayLabel(day))}</span>${today && !this._config.compact ? '<small>Aujourd’hui</small>' : ""}
      </button>`;
    }).join("");

    const visibleMeta = CATEGORY_META.filter(([key]) => this._config.categories.includes(key));
    const mealRows = visibleMeta.map(([key, label, icon]) => {
      const values = categoryItems(selected, key);
      if (!values.length && !this._config.show_empty_categories) return "";
      return `<div class="meal-row${values.length ? "" : " empty-row"}">
        <div class="meal-icon" aria-hidden="true">${icon}</div>
        <div class="meal-copy">
          <div class="meal-label">${esc(label)}</div>
          <div class="meal-value">${values.length ? renderChoices(values, this._config.show_semantic_badges, key, this._config.show_redundant_badges) : "—"}</div>
        </div>
      </div>`;
    }).join("");

    const badge = selectedDayBadge(selected, days, todayIso);
    this.shadowRoot.innerHTML = this._shell(`
      ${this._renderHeader(stateObj, days)}
      <div class="day-tabs" role="group" aria-label="Choisir un jour">${tabs}</div>
      <div class="selected-day-line">
        <div class="selected-day">${esc(longDayLabel(selected))}</div>
        ${badge ? `<span class="day-badge">${esc(badge)}</span>` : ""}
      </div>
      <div class="meal-grid">${mealRows || '<div class="empty">Aucune catégorie affichable pour cette journée.</div>'}</div>
    `);

    this.shadowRoot.querySelectorAll(".day-tab").forEach((button) => {
      button.addEventListener("click", () => this._selectDay(button.dataset.date));
    });
  }

  _renderHeader(stateObj, days) {
    if (!this._config.show_header) return "";
    const title = this._config.title || (this._config.show_school_name ? schoolName(stateObj) : "Menu de la cantine");
    const week = this._config.show_week && days.length ? weekLabel(stateObj, days) : "";
    return `<div class="header">
      <div class="header-copy">
        ${title ? `<div class="title">${esc(title)}</div>` : ""}
        ${week ? `<div class="subtitle">${esc(week)}</div>` : ""}
      </div>
      <ha-icon icon="mdi:silverware-fork-knife" class="header-icon"></ha-icon>
    </div>`;
  }

  _shell(content) {
    const compactClass = this._config?.compact ? " compact" : "";
    return `
      <style>
        :host { display:block; min-width:0; }
        ha-card { overflow:hidden; color:var(--primary-text-color); }
        .wrap { padding:14px; min-width:0; }
        .wrap.compact { padding:10px 12px; }
        .header { display:flex; align-items:center; justify-content:space-between; gap:12px; margin-bottom:11px; }
        .compact .header { margin-bottom:8px; }
        .header-copy { min-width:0; }
        .title { font-size:1.08rem; font-weight:650; line-height:1.25; overflow-wrap:anywhere; }
        .compact .title { font-size:.98rem; }
        .subtitle { margin-top:2px; font-size:.80rem; color:var(--secondary-text-color); }
        .compact .subtitle { font-size:.74rem; }
        .header-icon { color:var(--secondary-text-color); --mdc-icon-size:24px; flex:0 0 auto; }
        .compact .header-icon { --mdc-icon-size:21px; }
        .day-tabs { display:grid; grid-template-columns:repeat(var(--day-count, 5), minmax(0,1fr)); gap:6px; margin:0 -2px 11px; }
        .compact .day-tabs { gap:5px; margin-bottom:8px; }
        .day-tab { appearance:none; border:1px solid var(--divider-color); border-radius:11px; background:var(--card-background-color); color:var(--primary-text-color); padding:7px 5px; min-height:42px; font:inherit; font-size:.80rem; line-height:1.1; cursor:pointer; min-width:0; transition:border-color .12s ease, background .12s ease, box-shadow .12s ease; }
        .compact .day-tab { min-height:36px; padding:5px 4px; border-radius:9px; font-size:.76rem; }
        .day-tab span { display:block; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
        .day-tab small { display:block; margin-top:4px; font-size:.62rem; color:var(--secondary-text-color); }
        .day-tab.active { border:2px solid var(--primary-color); background:color-mix(in srgb, var(--primary-color) 14%, var(--card-background-color)); color:var(--primary-text-color); font-weight:700; box-shadow:0 0 0 1px color-mix(in srgb, var(--primary-color) 10%, transparent); }
        .day-tab.today:not(.active) { box-shadow:inset 0 -2px 0 var(--primary-color); }
        .day-tab:focus-visible { outline:2px solid var(--primary-color); outline-offset:2px; }
        .selected-day-line { display:flex; align-items:center; justify-content:space-between; gap:8px; margin:0 0 7px; min-width:0; }
        .compact .selected-day-line { margin-bottom:5px; }
        .selected-day { font-size:.92rem; font-weight:650; min-width:0; }
        .compact .selected-day { font-size:.86rem; }
        .day-badge { flex:0 0 auto; font-size:.68rem; font-weight:650; padding:3px 7px; border-radius:999px; color:var(--primary-color); background:color-mix(in srgb, var(--primary-color) 11%, transparent); border:1px solid color-mix(in srgb, var(--primary-color) 28%, transparent); }
        .compact .day-badge { font-size:.62rem; padding:2px 6px; }
        .meal-grid { display:grid; gap:0; border-top:1px solid var(--divider-color); }
        .meal-row { display:grid; grid-template-columns:26px minmax(0,1fr); gap:7px; padding:7px 0; border-bottom:1px solid var(--divider-color); min-width:0; }
        .compact .meal-row { grid-template-columns:22px minmax(0,1fr); gap:5px; padding:5px 0; }
        .meal-icon { font-size:1rem; line-height:1.35; text-align:center; }
        .compact .meal-icon { font-size:.9rem; }
        .meal-copy { min-width:0; display:grid; grid-template-columns:minmax(112px, 29%) minmax(0,1fr); gap:8px; align-items:start; }
        .compact .meal-copy { grid-template-columns:minmax(100px, 27%) minmax(0,1fr); gap:6px; }
        .meal-label { font-size:.77rem; font-weight:650; color:var(--secondary-text-color); }
        .compact .meal-label { font-size:.72rem; }
        .meal-value { font-size:.88rem; line-height:1.30; min-width:0; overflow-wrap:anywhere; }
        .compact .meal-value { font-size:.82rem; line-height:1.24; }
        .choices-inline { display:inline-flex; flex-wrap:wrap; align-items:baseline; column-gap:7px; row-gap:2px; }
        .choice-separator { color:var(--secondary-text-color); font-size:.78rem; font-style:italic; margin:0 1px; }
        .compact .choice-separator { font-size:.72rem; }
        .choice { min-width:0; display:inline-flex; flex-wrap:wrap; align-items:center; gap:6px; }
        .choice-name { min-width:0; }
        .semantic-badges { display:inline-flex; align-items:center; gap:3px; white-space:nowrap; vertical-align:middle; margin-left:1px; }
        .semantic-badge { display:inline-flex; align-items:center; justify-content:center; min-width:16px; height:16px; line-height:1; font-size:.72rem; border-radius:999px; }
        .semantic-badge.text-badge { min-width:auto; height:15px; padding:0 4px; font-size:.54rem; font-weight:800; letter-spacing:.01em; color:var(--secondary-text-color); border:1px solid var(--divider-color); background:var(--secondary-background-color); }
        .compact .semantic-badge { min-width:14px; height:14px; font-size:.66rem; }
        .compact .semantic-badge.text-badge { height:13px; font-size:.50rem; padding:0 3px; }
        .empty-row .meal-value { color:var(--secondary-text-color); }
        .empty { padding:14px 0 4px; color:var(--secondary-text-color); font-style:italic; line-height:1.4; }
        code { font-family:var(--code-font-family, monospace); overflow-wrap:anywhere; }
        @media (max-width:520px) {
          .wrap { padding:12px; }
          .wrap.compact { padding:9px 10px; }
          .day-tabs { display:flex; overflow-x:auto; scrollbar-width:none; padding:2px; margin-left:-2px; margin-right:-2px; }
          .day-tabs::-webkit-scrollbar { display:none; }
          .day-tab { flex:1 0 62px; padding:7px 6px; }
          .compact .day-tab { flex-basis:56px; padding:5px; }
          .meal-copy, .compact .meal-copy { grid-template-columns:1fr; gap:1px; }
          .meal-row { padding:7px 0; }
          .compact .meal-row { padding:5px 0; }
          .day-badge { font-size:.64rem; }
        }
      </style>
      <ha-card><div class="wrap${compactClass}" style="--day-count:${Math.max(1, normalizeDays(this._hass?.states?.[this._config?.entity]?.attributes?.days).length || 5)}">${content}</div></ha-card>
    `;
  }
}

class RadisLaToqueCardEditor extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._config = {};
    this._hass = null;
  }

  set hass(hass) { this._hass = hass; this._render(); }
  setConfig(config) { this._config = { ...config }; this._render(); }

  _emit(patch) {
    this._config = { ...this._config, ...patch };
    this.dispatchEvent(new CustomEvent("config-changed", { detail: { config: this._config }, bubbles: true, composed: true }));
  }

  _toggleCategory(key, enabled) {
    const current = normalizeCategories(this._config.categories);
    let next = enabled ? [...new Set([...current, key])] : current.filter((item) => item !== key);
    if (!next.length) next = ["main_course"];
    this._emit({ categories: next });
  }

  _render() {
    if (!this.shadowRoot || !this._hass) return;
    const entities = Object.entries(this._hass.states)
      .filter(([id, st]) => id.startsWith("sensor.") && (id.endsWith("_menu_de_la_semaine") || Array.isArray(st.attributes?.days)))
      .sort((a, b) => (a[1].attributes?.friendly_name || a[0]).localeCompare(b[1].attributes?.friendly_name || b[0], "fr"));
    const categories = normalizeCategories(this._config.categories);
    const defaultDay = DEFAULT_DAY_MODES.has(this._config.default_day) ? this._config.default_day : "smart";

    this.shadowRoot.innerHTML = `
      <style>
        .form { display:grid; gap:16px; padding:8px 0; }
        .group { display:grid; gap:9px; }
        .group-title { font-size:.82rem; font-weight:700; color:var(--secondary-text-color); text-transform:uppercase; letter-spacing:.03em; }
        label { display:grid; gap:6px; font-size:.92rem; }
        select,input[type="text"] { box-sizing:border-box; width:100%; min-height:44px; padding:8px 10px; font:inherit; color:var(--primary-text-color); background:var(--card-background-color); border:1px solid var(--divider-color); border-radius:8px; }
        .check { display:flex; align-items:center; gap:10px; min-height:32px; }
        .check input { width:18px; height:18px; margin:0; }
        .category-grid { display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:7px 12px; }
        @media (max-width:520px) { .category-grid { grid-template-columns:1fr; } }
      </style>
      <div class="form">
        <label>Menu de la semaine
          <select id="entity">
            <option value="">Sélectionner…</option>
            ${entities.map(([id, st]) => `<option value="${esc(id)}" ${this._config.entity === id ? "selected" : ""}>${esc(st.attributes?.friendly_name || id)}</option>`).join("")}
          </select>
        </label>

        <div class="group">
          <div class="group-title">En-tête</div>
          <label class="check"><input id="show_header" type="checkbox" ${this._config.show_header !== false ? "checked" : ""}>Afficher l’en-tête</label>
          <label class="check"><input id="show_school_name" type="checkbox" ${this._config.show_school_name !== false ? "checked" : ""}>Afficher le nom de l’établissement</label>
          <label class="check"><input id="show_week" type="checkbox" ${this._config.show_week !== false ? "checked" : ""}>Afficher la semaine</label>
          <label>Titre personnalisé (optionnel)
            <input id="title" type="text" value="${esc(this._config.title || "")}" placeholder="Ex. Cantine des enfants">
          </label>
        </div>

        <div class="group">
          <div class="group-title">Affichage</div>
          <label>Jour affiché à l’ouverture
            <select id="default_day">
              <option value="smart" ${defaultDay === "smart" ? "selected" : ""}>Intelligent (aujourd’hui, sinon prochain)</option>
              <option value="today" ${defaultDay === "today" ? "selected" : ""}>Aujourd’hui, sinon prochain</option>
              <option value="next" ${defaultDay === "next" ? "selected" : ""}>Prochain repas</option>
              <option value="first" ${defaultDay === "first" ? "selected" : ""}>Premier jour de la semaine</option>
            </select>
          </label>
          <label class="check"><input id="compact" type="checkbox" ${this._config.compact === true ? "checked" : ""}>Mode compact</label>
          <label class="check"><input id="show_semantic_badges" type="checkbox" ${this._config.show_semantic_badges !== false ? "checked" : ""}>Afficher les badges alimentaires</label>
          <label class="check"><input id="show_redundant_badges" type="checkbox" ${this._config.show_redundant_badges === true ? "checked" : ""}>Afficher aussi les badges redondants</label>
          <label class="check"><input id="show_empty_categories" type="checkbox" ${this._config.show_empty_categories === true ? "checked" : ""}>Afficher les catégories vides</label>
        </div>

        <div class="group">
          <div class="group-title">Catégories affichées</div>
          <div class="category-grid">
            ${CATEGORY_META.map(([key, label, icon]) => `<label class="check"><input class="cat" data-key="${esc(key)}" type="checkbox" ${categories.includes(key) ? "checked" : ""}>${icon} ${esc(label)}</label>`).join("")}
          </div>
        </div>
      </div>`;

    this.shadowRoot.getElementById("entity")?.addEventListener("change", (e) => this._emit({ entity: e.target.value }));
    this.shadowRoot.getElementById("title")?.addEventListener("change", (e) => this._emit({ title: e.target.value.trim() }));
    this.shadowRoot.getElementById("show_header")?.addEventListener("change", (e) => this._emit({ show_header: e.target.checked }));
    this.shadowRoot.getElementById("show_school_name")?.addEventListener("change", (e) => this._emit({ show_school_name: e.target.checked }));
    this.shadowRoot.getElementById("show_week")?.addEventListener("change", (e) => this._emit({ show_week: e.target.checked }));
    this.shadowRoot.getElementById("default_day")?.addEventListener("change", (e) => this._emit({ default_day: e.target.value }));
    this.shadowRoot.getElementById("compact")?.addEventListener("change", (e) => this._emit({ compact: e.target.checked }));
    this.shadowRoot.getElementById("show_semantic_badges")?.addEventListener("change", (e) => this._emit({ show_semantic_badges: e.target.checked }));
    this.shadowRoot.getElementById("show_redundant_badges")?.addEventListener("change", (e) => this._emit({ show_redundant_badges: e.target.checked }));
    this.shadowRoot.getElementById("show_empty_categories")?.addEventListener("change", (e) => this._emit({ show_empty_categories: e.target.checked }));
    this.shadowRoot.querySelectorAll(".cat").forEach((box) => {
      box.addEventListener("change", (e) => this._toggleCategory(e.target.dataset.key, e.target.checked));
    });
  }
}

if (!customElements.get("radis-la-toque-card")) customElements.define("radis-la-toque-card", RadisLaToqueCard);
if (!customElements.get("radis-la-toque-card-editor")) customElements.define("radis-la-toque-card-editor", RadisLaToqueCardEditor);

window.customCards = window.customCards || [];
if (!window.customCards.some((card) => card.type === "radis-la-toque-card")) {
  window.customCards.push({
    type: "radis-la-toque-card",
    name: "Radis la Toque",
    description: "Affiche le menu de cantine de la semaine avec navigation par jour.",
    preview: true,
    documentationURL: "https://github.com/guat37/ha-radis-la-toque",
  });
}

console.info(`%c RADIS LA TOQUE CARD %c ${RLT_CARD_VERSION} `, "color:white;background:#5f8b62;font-weight:700;padding:2px 5px", "color:#5f8b62;background:#edf5ee;padding:2px 5px");

globalThis.__RLT_CARD_TEST__ = {
  normalizeDays,
  normalizeCategories,
  chooseInitialDay,
  shortDayLabel,
  longDayLabel,
  weekLabel,
  schoolName,
  selectedDayBadge,
  categoryItems,
  visibleSemanticLabels,
  renderSemanticBadges,
  renderChoice,
  renderChoices,
};
