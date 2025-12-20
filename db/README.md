📦 Proyecto Consumo de Materiales

Sistema web desarrollado con Flask, SQLite, Estructuras de Datos y Machine Learning para el análisis y proyección del consumo de materiales.

Este repositorio se trabaja estrictamente con ramas, siguiendo reglas claras para evitar conflictos de merge.

🧰 Requisitos previos

Antes de empezar, cada integrante debe tener instalado:

🔹 Git

Windows / Mac / Linux

Descargar desde:
👉 https://git-scm.com/

Verificar instalación:

git --version

🔹 Python (si aplica a tu rol)

Versión recomendada: Python 3.10+

Verificar:

python --version

📥 Clonar el repositorio

Cada integrante debe clonar el proyecto una sola vez:

git clone https://github.com/USUARIO/proyecto-consumo-materiales.git
cd proyecto-consumo-materiales


⚠️ Nunca descargar el proyecto como ZIP.

🌿 Trabajo con ramas (OBLIGATORIO)
🔹 Regla principal

❌ Nadie trabaja en main
✅ Cada integrante trabaja solo en su rama

🔹 Ramas del proyecto
Rama	Rol
frontend	HTML / CSS
javascript	JS e integración
backend	Flask + ED
database	SQLite
machine_learning	Datos y ML
🔹 Cambiar a tu rama
Desde terminal:
git switch nombre_de_tu_rama

Desde VS Code:

esquina inferior izquierda

clic en el nombre de la rama

seleccionar tu rama

✍️ Flujo correcto de trabajo
1️⃣ Trabaja solo en tus carpetas asignadas

(No tocar archivos de otros roles)

2️⃣ Guarda cambios y haz commit
Desde terminal:
git status
git add .
git commit -m "Mensaje claro del cambio"


Ejemplos de buenos commits:

Diseño inicial del dashboard

Agrega búsqueda con árbol BST

Entrena modelo de predicción

Desde VS Code (UI):

Ir a Source Control

Revisar archivos en CHANGES

Escribir mensaje de commit

Clic en Commit

3️⃣ Subir cambios (push)
Terminal:
git push origin nombre_de_tu_rama

VS Code:

botón Sync / Push 🔄

🔄 Sincronizar tu rama con main (MUY IMPORTANTE)

Esto se hace SIEMPRE:

antes de avisar para merge

después de que alguien más hizo merge

🔹 Desde terminal
git switch main
git pull origin main
git switch nombre_de_tu_rama
git merge main


Si hay conflictos:

se resuelven

se hace commit del merge

🔹 Desde VS Code (UI)

Cambiar a main

Clic en Sync

Cambiar a tu rama

Ctrl + Shift + P

Merge Branch

Seleccionar main

Resolver conflictos si aparecen

Commit del merge

📣 Aviso para integración (Pull Request)

👉 Los integrantes NO hacen Pull Request

Cuando termines una tarea:

Asegúrate de que tu rama esté sincronizada con main

Haz push

Avísame por el canal del equipo

qué hiciste

qué archivos tocaste

Yo me encargo de:

revisar

hacer el PR

hacer el merge a main

🕘🕓 Horario de integración (merge)

Los merges se hacen solo en estos horarios:

🕘 Mañana: 09:00 – 11:00

🕓 Tarde: 16:00 – 18:00

📌 Máximo un merge por ventana
📌 Fuera de ese horario no se integra a main

🛑 Reglas de oro (léelas dos veces)

❌ No trabajar en main

❌ No hacer merge por cuenta propia

❌ No tocar carpetas que no te corresponden

✅ Commits pequeños y claros

✅ Sincronizar tu rama con main

✅ Avisar antes de integrar

🧠 Nota final

Estas reglas existen para:

evitar conflictos

no perder trabajo

avanzar rápido y ordenado

Si tienes dudas, pregunta antes de hacer merge.