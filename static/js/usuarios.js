"use strict";

let usuarios = [];

const $ = (id) => document.getElementById(id);

function escapeHtml(value){
  return String(value ?? "").replace(/[&<>"']/g, c => ({
    "&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#039;"
  }[c]));
}

function setStatus(id, texto, tipo){
  const el = $(id);
  if(!el) return;
  el.textContent = texto || "";
  el.className = "status" + (tipo ? ` ${tipo}` : "");
}

function validarPassword(password){
  const letras = /\p{L}/u.test(password);
  const numeros = /\d/.test(password);
  const simbolos = /[^\p{L}\d\s]/u.test(password);
  return { letras, numeros, simbolos, ok: letras && numeros && simbolos };
}

function actualizarChecks(){
  const password = $("password")?.value || "";
  const validacion = validarPassword(password);
  const mapa = {
    checkLetra: validacion.letras,
    checkNumero: validacion.numeros,
    checkSimbolo: validacion.simbolos
  };
  Object.entries(mapa).forEach(([id, ok]) => {
    const el = $(id);
    if(el) el.classList.toggle("ok", Boolean(ok));
  });
  return validacion;
}

async function cargarUsuarios(){
  try{
    setStatus("tablaStatus", "Cargando usuarios...");
    const res = await fetch("/api/usuarios");
    const json = await res.json().catch(() => ({}));

    if(!res.ok || !json.ok){
      setStatus("tablaStatus", "Error al cargar usuarios: " + (json.error || `HTTP ${res.status}`), "err-text");
      return;
    }

    usuarios = Array.isArray(json.usuarios) ? json.usuarios : [];
    renderUsuarios();
    setStatus("tablaStatus", usuarios.length ? `Usuarios cargados: ${usuarios.length}` : "Sin usuarios registrados", "ok-text");
  }catch(err){
    console.error(err);
    setStatus("tablaStatus", "Error de red al cargar usuarios", "err-text");
  }
}

function renderUsuarios(){
  const tb = $("tbodyUsuarios");
  if(!tb) return;
  tb.innerHTML = "";

  if(!usuarios.length){
    tb.innerHTML = `<tr><td colspan="3" class="empty">Sin usuarios registrados.</td></tr>`;
    return;
  }

  usuarios.forEach((usuario) => {
    tb.insertAdjacentHTML("beforeend", `
      <tr>
        <td>${escapeHtml(usuario.id)}</td>
        <td>${escapeHtml(usuario.username)}</td>
        <td><span class="badge">${escapeHtml(usuario.rol)}</span></td>
      </tr>
    `);
  });
}

async function guardarUsuario(event){
  event.preventDefault();

  const username = $("username").value.trim();
  const password = $("password").value;
  const rol = $("rol").value;
  const validacion = actualizarChecks();

  if(!username){
    setStatus("formStatus", "Ingrese el nombre de usuario.", "err-text");
    return;
  }

  const repetido = usuarios.some(u => String(u.username || "").toLowerCase() === username.toLowerCase());
  if(repetido){
    setStatus("formStatus", "Ya existe un usuario con ese nombre.", "err-text");
    return;
  }

  if(!validacion.ok){
    setStatus("formStatus", "La contraseña debe contener al menos una letra, un número y un símbolo.", "err-text");
    return;
  }

  try{
    setStatus("formStatus", "Guardando usuario...");
    const res = await fetch("/api/usuarios", {
      method:"POST",
      headers:{"Content-Type":"application/json"},
      body:JSON.stringify({ username, password, rol })
    });
    const json = await res.json().catch(() => ({}));

    if(!res.ok || !json.ok){
      setStatus("formStatus", "Error al guardar: " + (json.error || `HTTP ${res.status}`), "err-text");
      return;
    }

    $("formUsuario").reset();
    actualizarChecks();
    setStatus("formStatus", "Usuario creado correctamente.", "ok-text");
    await cargarUsuarios();
  }catch(err){
    console.error(err);
    setStatus("formStatus", "Error de red al guardar usuario", "err-text");
  }
}

function wireEvents(){
  const form = $("formUsuario");
  if(form) form.addEventListener("submit", guardarUsuario);

  const password = $("password");
  if(password) password.addEventListener("input", actualizarChecks);

  const logout = $("btnLogout");
  if(logout){
    logout.addEventListener("click", () => {
      localStorage.removeItem("ph_user");
      window.location.href = "/logout";
    });
  }
}

wireEvents();
actualizarChecks();
cargarUsuarios();
