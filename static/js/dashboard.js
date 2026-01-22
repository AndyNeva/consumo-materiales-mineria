// CONTRATO /api/dashboard
// Devuelve:
// {
//   consumo_diario: number,
//   cantidad_registros_semana: number,
//   registros_ultima_semana: Array<{
//     fecha: string (YYYY-MM-DD),
//     diseno_mezcla: string,
//     zona: string,
//     wbs: string,
//     volumen_m3: number
//   }>
// }

(() => {
  "use strict";

  // ====== LocalStorage Keys (inventario/sesion) ======
  const LS_INV  = "ph_inventario";
  const LS_USER = "ph_user";

  // ====== Helpers ======
  function fmt(n, d = 2) {
    const x = Number(n);
    if (!Number.isFinite(x)) return (0).toFixed(d);
    return x.toLocaleString("es-EC", { minimumFractionDigits: d, maximumFractionDigits: d });
  }

  function safeJsonParse(raw, fallback) {
    try { return JSON.parse(raw); } catch (_) { return fallback; }
  }

  function getTodayISO() {
    const d = new Date();
    const yyyy = d.getFullYear();
    const mm = String(d.getMonth() + 1).padStart(2, "0");
    const dd = String(d.getDate()).padStart(2, "0");
    return `${yyyy}-${mm}-${dd}`;
  }

  function escapeHtml(str) {
    return String(str).replace(/[&<>"']/g, s => ({
      "&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#039;"
    }[s]));
  }

  function toast(title, msg) {
    const el = document.getElementById("toast");
    if (!el) return;
    document.getElementById("toastTitle").textContent = title;
    document.getElementById("toastMsg").textContent = msg;
    el.style.display = "block";
    clearTimeout(window.__t);
    window.__t = setTimeout(() => { el.style.display = "none"; }, 4200);
  }

  function ensureDefaultsInventario() {
    if (!localStorage.getItem(LS_INV)) {
      const base = [
        { material:"Cemento", unidad:"kg", stock: 25000, minimo: 12000 },
        { material:"Arena", unidad:"kg", stock: 60000, minimo: 25000 },
        { material:"Grava", unidad:"kg", stock: 80000, minimo: 35000 },
        { material:"RHEO 1000", unidad:"kg", stock: 1000, minimo: 500 },
        { material:"Sika 115", unidad:"kg", stock: 800, minimo: 300 }
      ];
      localStorage.setItem(LS_INV, JSON.stringify(base));
    }
  }

  // ====== Backend fetch ======
  async function fetchDashboard() {
    const res = await fetch("/api/dashboard", { method: "GET" });

    if (!res.ok) {
      const txt = await res.text().catch(() => "");
      throw new Error(`Error HTTP ${res.status} al pedir /api/dashboard. Respuesta: ${txt.slice(0, 140)}`);
    }

    const data = await res.json();

    // Validación: debe ser objeto con llaves esperadas
    if (!data || typeof data !== "object" || Array.isArray(data)) {
      throw new Error("Respuesta inválida: se esperaba un objeto JSON desde /api/dashboard.");
    }

    // Normalizamos valores por si vienen undefined
    return {
      consumo_diario: Number(data.consumo_diario) || 0,
      registros_ultima_semana: Array.isArray(data.registros_ultima_semana) ? data.registros_ultima_semana : [],
      cantidad_registros_semana: Number(data.cantidad_registros_semana) || 0,
      inventario: Array.isArray(data.inventario) ? data.inventario : [],
    };
  }

  // ====== Render ======
  function renderSession() {
    const user = safeJsonParse(localStorage.getItem(LS_USER), null);
    const userName = (user && (user.nombre || user.user || user.usuario))
      ? (user.nombre || user.user || user.usuario)
      : "Sin usuario";

    const userChip = document.getElementById("userChip");
    const todayChip = document.getElementById("todayChip");
    if (userChip) userChip.textContent = userName;
    if (todayChip) todayChip.textContent = getTodayISO();

    if (!localStorage.getItem(LS_USER)) {
      toast("Sesión", "No se detectó usuario guardado. Puedes iniciar sesión desde /login.");
    }
  }

  function renderKPIs(payload) {
    // Tu backend ya manda el consumo diario calculado:
    const kpiTodayValue = document.getElementById("kpiTodayValue");
    if (kpiTodayValue) kpiTodayValue.textContent = fmt(payload.consumo_diario, 2);

    // Cantidad de registros últimos 7 días
    const kpi7dValue = document.getElementById("kpi7dValue");
    if (kpi7dValue) kpi7dValue.textContent = String(payload.cantidad_registros_semana);
  }

  function renderLastRows(payload) {
    // En tu HTML la tabla tiene 5 columnas:
    // Fecha | Diseño | Volumen (m³) | Destino | WBS

    const rows = payload.registros_ultima_semana;
    const lastRows = document.getElementById("lastRows");
    if (!lastRows) return;

    lastRows.innerHTML = "";

    if (!rows.length) {
      lastRows.innerHTML = `<tr><td colspan="5" style="color:rgba(255,255,255,.72);">Sin registros aún.</td></tr>`;
      return;
    }

    // ===== PASO 2.3: Ordenar por fecha desc y tomar los 5 más recientes =====
    const sorted = [...rows].sort((a, b) => {
      const da = new Date(String(a.fecha || "").slice(0, 10)).getTime();
      const db = new Date(String(b.fecha || "").slice(0, 10)).getTime();
      return (db || 0) - (da || 0);
    });

    const last = sorted.slice(0, 5);

    for (const r of last) {
      const fecha = String(r.fecha || "").slice(0, 10) || "—";
      const diseno = r.diseno_mezcla || r.diseno || r.diseño || "—";
      const volumen = (r.volumen_m3 ?? r.volumen ?? 0);
      const destino = r.zona || r.destino || "—";
      const wbs = r.wbs || "—";

      lastRows.insertAdjacentHTML("beforeend", `
        <tr>
          <td>${escapeHtml(fecha)}</td>
          <td>${escapeHtml(diseno)}</td>
          <td>${fmt(volumen, 2)}</td>
          <td>${escapeHtml(destino)}</td>
          <td><span class="badge"><span class="dot"></span>${escapeHtml(wbs)}</span></td>
        </tr>
      `);
    }
  }

  function renderInventarioAlerts() {
    // Usar inventario real del backend (inyectado en window._dashboardInventario)
    const inv = window._dashboardInventario || [];

    const alerts = inv
      .map(x => {
        const stock = Number(x.stock) || 0;
        const min = Number(x.minimo) || 0;
        let state = "OK", cls = "good";
        if (stock <= min) {
          state = "BAJO";
          cls = "bad";
        } else if (stock <= min * 1.15) {
          state = "CERCA";
          cls = "warn";
        }
        return { ...x, stock, min, state, cls };
      });

    const lowCount = alerts.filter(x => x.cls === "bad").length;
    const kpiLowValue = document.getElementById("kpiLowValue");
    if (kpiLowValue) kpiLowValue.textContent = String(lowCount);

    const invAlerts = document.getElementById("invAlerts");
    if (!invAlerts) return;

    invAlerts.innerHTML = "";

    if (alerts.length === 0) {
      invAlerts.innerHTML = `<tr><td colspan="4" style="color:rgba(255,255,255,.72);">Sin datos de inventario aún.</td></tr>`;
      return;
    }

    for (const a of alerts.slice(0, 8)) {
      invAlerts.insertAdjacentHTML("beforeend", `
        <tr>
          <td>${escapeHtml(a.material || "—")}</td>
          <td>${fmt(a.stock, 0)} ${escapeHtml(a.unidad || "")}</td>
          <td>${fmt(a.min, 0)} ${escapeHtml(a.unidad || "")}</td>
          <td><span class="badge"><span class="dot ${a.cls}"></span>${a.state}</span></td>
        </tr>
      `);
    }
  }

  // ====== Events ======
  function wireLogout() {
    const logoutBtn = document.getElementById("logoutBtn");
    if (!logoutBtn) return;

    logoutBtn.addEventListener("click", () => {
      localStorage.removeItem(LS_USER);
      window.location.href = "/login";
    });
  }

  // ====== Init ======
  async function init() {
    renderSession();
    wireLogout();

    try {
      const payload = await fetchDashboard();
      console.log("API /api/dashboard =>", payload);

      // Inyectar inventario real para renderInventarioAlerts
      window._dashboardInventario = payload.inventario || [];
      renderInventarioAlerts();

      renderKPIs(payload);
      renderLastRows(payload);

      console.log("dashboard.js cargado correctamente");
    } catch (err) {
      console.error(err);
      toast("Error", String(err.message || err));
    }
  }

  document.addEventListener("DOMContentLoaded", init);
})();
