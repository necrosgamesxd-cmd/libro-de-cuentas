import streamlit as st
import pandas as pd
from pathlib import Path
from datetime import date, timedelta
import io, uuid, subprocess

# ═══════════════════════ CONFIGURACIÓN ═══════════════════════
st.set_page_config(page_title="Libro de Cuentas", page_icon="📒", layout="wide")

ADMIN_PASSWORD = "cambiar123"          # ⚠️ CAMBIÁ ESTA CONTRASEÑA
CARPETA = Path(__file__).resolve().parent / "data"
CARPETA.mkdir(exist_ok=True)

MESES = ["Enero","Febrero","Marzo","Abril","Mayo","Junio","Julio",
         "Agosto","Septiembre","Octubre","Noviembre","Diciembre"]

COL_SOCIOS = ["socio_id","nombre","cuota"]
COL_CUOTAS = ["pago_id","socio_id","nombre","monto","fecha"]
COL_ESP    = ["ingreso_id","fecha","concepto","detalle","monto"]
COL_GAS    = ["gasto_id","fecha","concepto","categoria","monto"]
CATEGORIAS = ["Servicios","Mantenimiento","Insumos","Sueldos","Transporte","Otros"]

# ═══════════════════════ UTILIDADES ═══════════════════════
def cargar(nombre, columnas):
    p = CARPETA / f"{nombre}.csv"
    df = pd.read_csv(p) if p.exists() else pd.DataFrame(columns=columnas)
    for c in columnas:
        if c not in df.columns: df[c] = ""
    df = df[columnas]
    if "monto" in df.columns:
        df["monto"] = pd.to_numeric(df["monto"], errors="coerce").fillna(0)
    if "cuota" in df.columns:
        df["cuota"] = pd.to_numeric(df["cuota"], errors="coerce").fillna(0)
    return df

def guardar(nombre, df):
    df.to_csv(CARPETA / f"{nombre}.csv", index=False)

def leer_entidad():
    p = CARPETA / "entidad.txt"
    return p.read_text(encoding="utf-8").strip() if p.exists() else "Mi Institución"

def guardar_entidad(t):
    (CARPETA / "entidad.txt").write_text(t.strip(), encoding="utf-8")

def uid(): return uuid.uuid4().hex[:10]

def fmt(n):
    s = f"{abs(float(n)):,.2f}".replace(",", "@").replace(".", ",").replace("@", ".")
    return ("−$ " if n < 0 else "$ ") + s

def mes_key(anio, mes_idx): return f"{anio:04d}-{mes_idx+1:02d}"

def norm(n): return " ".join(str(n).lower().split())

def parse_monto(v, defecto):
    try: return float(v)
    except Exception:
        s = str(v).replace("$","").strip()
        if "," in s and "." in s: s = s.replace(".","").replace(",",".")
        elif "," in s: s = s.replace(",",".")
        try: return float(s)
        except Exception: return defecto

def fecha_defecto(anio, mes_idx):
    h = date.today()
    return h if (h.year==anio and h.month==mes_idx+1) else date(anio, mes_idx+1, 1)

def fecha_pago(anio, mes_idx):
    h = date.today()
    if h.year==anio and h.month==mes_idx+1: return h
    fin = date(anio,12,31) if mes_idx==11 else date(anio, mes_idx+2, 1) - timedelta(days=1)
    return fin

# ═══════════════════════ ESTÉTICA ═══════════════════════
st.markdown("""
<style>
div[data-testid="stMetric"]{background:rgba(255,255,255,.05);
  border:1px solid rgba(255,255,255,.13);border-radius:14px;padding:14px 18px}
.chip-deuda{display:inline-block;background:rgba(224,82,82,.16);
  border:1px dashed rgba(224,82,82,.65);color:#ff9d98;font-weight:700;
  padding:6px 13px;border-radius:99px;margin:3px;font-size:.95rem}
.titulo-rojo{color:#ff8078;font-weight:800;letter-spacing:.08em}
</style>""", unsafe_allow_html=True)

# ═══════════════════════ SESIÓN ═══════════════════════
if "admin" not in st.session_state: st.session_state.admin = False

hoy = date.today()

# ─────────── BARRA LATERAL ───────────
with st.sidebar:
    st.title("📒 Libro de Cuentas")
    st.caption(leer_entidad())

    st.markdown("#### 📅 Período consultado")
    col_a, col_m = st.columns([1,1.4])
    anio  = col_a.selectbox("Año", list(range(hoy.year-3, hoy.year+2)),
                            index=list(range(hoy.year-3, hoy.year+2)).index(hoy.year))
    mes   = col_m.selectbox("Mes", range(12), index=hoy.month-1,
                            format_func=lambda m: MESES[m])
    kk = mes_key(anio, mes)

    st.divider()
    # ── acceso administrador ──
    if st.session_state.admin:
        st.success("🔓 Modo administrador activo")
        if st.button("Salir del modo administrador", use_container_width=True):
            st.session_state.admin = False; st.rerun()
    else:
        with st.expander("🔒 Acceso administrador"):
            p = st.text_input("Contraseña", type="password")
            if st.button("Entrar", use_container_width=True):
                if p == ADMIN_PASSWORD:
                    st.session_state.admin = True; st.rerun()
                else:
                    st.error("Contraseña incorrecta")
        st.caption("Los miembros pueden consultar todo sin contraseña.")

    admin = st.session_state.admin

    # ── gestión (solo admin) ──
    if admin:
        st.divider()
        with st.expander("⚙️ Gestión del libro", expanded=True):
            nuevo_nombre = st.text_input("Nombre de la institución", value=leer_entidad())
            if nuevo_nombre != leer_entidad():
                guardar_entidad(nuevo_nombre)

        with st.expander("🔀 Push a GitHub", expanded=False):
            st.caption("Subir los datos del libro al repositorio remoto.")
            token = st.text_input("Token de GitHub (Personal Access Token)", type="password",
                                  help="Generalo en GitHub → Settings → Developer settings → Tokens")
            msg_commit = st.text_input("Mensaje del commit", value="Actualización libro de cuentas")
            if st.button("⬆ Push a GitHub", type="primary", use_container_width=True):
                if not token.strip():
                    st.error("Ingresá un token de GitHub válido.")
                else:
                    with st.spinner("Subiendo cambios..."):
                        try:
                            remote = f"https://{token.strip()}@github.com/necrosgamesxd-cmd/libro-de-cuentas.git"
                            subprocess.run(["git", "remote", "set-url", "origin", remote], cwd=CARPETA.parent, check=True)
                            subprocess.run(["git", "add", "data/"], cwd=CARPETA.parent, check=True,
                                           capture_output=True, text=True)
                            subprocess.run(["git", "add", "app.py"], cwd=CARPETA.parent, check=True,
                                           capture_output=True, text=True)
                            r = subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=CARPETA.parent,
                                               capture_output=True)
                            if r.returncode == 0:
                                st.info("No hay cambios para subir.")
                            else:
                                subprocess.run(["git", "commit", "-m", msg_commit], cwd=CARPETA.parent,
                                               check=True, capture_output=True, text=True)
                                subprocess.run(["git", "push", "origin", "main"], cwd=CARPETA.parent,
                                               check=True, capture_output=True, text=True)
                                st.success("Cambios subidos a GitHub ✔")
                        except subprocess.CalledProcessError as e:
                            st.error(f"Error al subir: {e.stderr or e.stdout or e}")

        with st.expander("📤 Subir Excel de miembros", expanded=True):
            st.caption("Columnas reconocidas: **Nombre** y **Cuota** (en cualquier orden).")
            plantilla = pd.DataFrame({"Nombre":["Juan Pérez","María López"],"Cuota":[5000,5000]})
            buf = io.BytesIO()
            plantilla.to_excel(buf, index=False, engine="openpyxl")
            st.download_button("⬇ Descargar plantilla Excel", buf.getvalue(),
                               "plantilla-miembros.xlsx",
                               "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
            subido = st.file_uploader("Archivo de miembros", type=["xlsx","csv"])
            if subido is not None:
                try:
                    dfm = pd.read_excel(subido) if subido.name.lower().endswith((".xlsx",".xls")) \
                          else pd.read_csv(subido)
                    cols = {str(c).lower().strip(): c for c in dfm.columns}
                    col_nom = next((cols[k] for k in cols
                                    if any(x in k for x in ["nombre","socio","miembro"])), dfm.columns[0])
                    col_cuo = next((cols[k] for k in cols
                                    if any(x in k for x in ["cuota","monto","importe","valor"])), None)
                    st.dataframe(dfm, use_container_width=True, height=150)
                    cuota_def = st.number_input("Cuota si el archivo no trae monto", 0, 10**9, 5000)
                    modo = st.radio("¿Cómo importar?",
                                    ["Agregar los que faltan", "Reemplazar toda la lista"])
                    if st.button("✅ Confirmar importación", type="primary", use_container_width=True):
                        socios = cargar("socios", COL_SOCIOS)
                        mapa = {norm(n): i for n, i in zip(socios["nombre"], socios["socio_id"])}
                        filas, agregados, conservados = [], 0, 0
                        for _, fila in dfm.iterrows():
                            nombre = str(fila[col_nom]).strip()
                            if not nombre or nombre.lower() == "nan": continue
                            cuota = parse_monto(fila[col_cuo], cuota_def) if col_cuo else cuota_def
                            if norm(nombre) in mapa:
                                sid = mapa[norm(nombre)]; conservados += 1
                                if modo.startswith("Reemplazar"):
                                    filas.append({"socio_id":sid,"nombre":nombre,"cuota":cuota})
                            else:
                                filas.append({"socio_id":uid(),"nombre":nombre,"cuota":cuota}); agregados += 1
                        if modo.startswith("Reemplazar"):
                            guardar("socios", pd.DataFrame(filas, columns=COL_SOCIOS))
                        else:
                            guardar("socios", pd.concat([socios,
                                    pd.DataFrame(filas, columns=COL_SOCIOS)], ignore_index=True))
                        st.success(f"Importado ✔ · {agregados} nuevos · {conservados} ya existían")
                        st.rerun()
                except Exception as e:
                    st.error(f"No se pudo leer el archivo: {e}")

        with st.expander("🧪 Datos de prueba / reinicio"):
            if st.button("Cargar datos de ejemplo"):
                cargar_demo() if False else None  # función definida más abajo
            confirmar = st.checkbox("Confirmo borrar TODO el libro")
            if st.button("🗑 Reiniciar libro", disabled=not confirmar):
                for f in ["socios","cuotas","especiales","gastos"]:
                    (CARPETA / f"{f}.csv").unlink(missing_ok=True)
                st.rerun()

    # ── descargas públicas (transparencia) ──
    st.divider()
    st.markdown("**⬇ Descargas públicas**")
    socios = cargar("socios", COL_SOCIOS)
    cuotas = cargar("cuotas", COL_CUOTAS)
    esp    = cargar("especiales", COL_ESP)
    gas    = cargar("gastos", COL_GAS)

    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as w:
        socios.to_excel(w, sheet_name="Socios", index=False)
        cuotas.to_excel(w, sheet_name="Cuotas pagadas", index=False)
        esp.to_excel(w, sheet_name="Ingresos especiales", index=False)
        gas.to_excel(w, sheet_name="Gastos", index=False)
        resumen = pd.DataFrame({
            "Concepto":["Ingresos del período","Egresos del período","Saldo del período","Saldo histórico"],
        })
        resumen.to_excel(w, sheet_name="Resumen", index=False)
    st.download_button("Libro completo (Excel)", buf.getvalue(),
                       f"libro-cuentas-{hoy.isoformat()}.xlsx",
                       "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                       use_container_width=True)

# ═══════════════════════ DATOS DEL PERÍODO ═══════════════════════
socios = cargar("socios", COL_SOCIOS)
cuotas = cargar("cuotas", COL_CUOTAS)
esp    = cargar("especiales", COL_ESP)
gas    = cargar("gastos", COL_GAS)

pagos_mes = cuotas[cuotas["fecha"].astype(str).str.startswith(kk)]
esp_mes   = esp[esp["fecha"].astype(str).str.startswith(kk)]
gas_mes   = gas[gas["fecha"].astype(str).str.startswith(kk)]

tot_cuotas = pagos_mes["monto"].sum()
tot_esp    = esp_mes["monto"].sum()
tot_gas    = gas_mes["monto"].sum()
tot_ing    = tot_cuotas + tot_esp
saldo_mes  = tot_ing - tot_gas
saldo_hist = cuotas["monto"].sum() + esp["monto"].sum() - gas["monto"].sum()

pagados_ids = set(pagos_mes["socio_id"])
deudores = socios[~socios["socio_id"].isin(pagados_ids)].copy()
esperado = socios["cuota"].sum()
pendiente = deudores["cuota"].sum()

st.header(f"📒 Libro de Cuentas — {MESES[mes]} {anio}")
st.caption(f"**{leer_entidad()}** · Libro público: todos los movimientos son visibles para los miembros.")

# ═══════════════════════ PESTAÑAS ═══════════════════════
t_inicio, t_ing, t_egr = st.tabs(["🏠 Inicio", "📈 Ingresos", "📉 Egresos"])

# ─────────────── INICIO ───────────────
with t_inicio:
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("TOTAL INGRESOS", fmt(tot_ing), help=f"Cuotas {fmt(tot_cuotas)} · Especiales {fmt(tot_esp)}")
    c2.metric("TOTAL EGRESOS", fmt(tot_gas), help=f"{len(gas_mes)} gastos registrados")
    c3.metric("SALDO DEL MES", fmt(saldo_mes), help=f"Saldo histórico: {fmt(saldo_hist)}")
    c4.metric("DEUDORES", f"{len(deudores)} socio/s",
              delta=f"{fmt(pendiente)} pendiente" if len(deudores) else "Nadie debe ✔",
              delta_color="inverse")

    st.markdown("### <span class='titulo-rojo'>⚠ DEUDORES</span>", unsafe_allow_html=True)
    if len(deudores):
        chips = "".join(
            f'<span class="chip-deuda">{n} · {fmt(c)}</span>'
            for n, c in zip(deudores["nombre"], deudores["cuota"]))
        st.html(f'<div style="margin-top:8px">{chips}</div>')
        st.dataframe(
            deudores[["nombre","cuota"]].rename(columns={"nombre":"Socio","cuota":"Cuota adeudada"})
            .assign(Cuota=lambda d: d["Cuota adeudada"].map(fmt)),
            use_container_width=True, hide_index=True)
        if admin:
            st.info("Para registrar un cobro andá a **Ingresos → Cuotas → Gestionar cobros**.")
    else:
        st.success("✓ Sin deudores — todas las cuotas al día.")

    st.markdown("### Lista de ingresos y egresos del período")
    movs = []
    for _, r in pagos_mes.iterrows():
        movs.append({"Fecha":r["fecha"], "Tipo":"CUOTA", "Concepto":f"Cuota · {r['nombre']}", "Monto": r["monto"]})
    for _, r in esp_mes.iterrows():
        movs.append({"Fecha":r["fecha"], "Tipo":"INGRESO ESPECIAL", "Concepto":r["concepto"], "Monto": r["monto"]})
    for _, r in gas_mes.iterrows():
        movs.append({"Fecha":r["fecha"], "Tipo":"GASTO", "Concepto":f"{r['concepto']} ({r['categoria']})", "Monto": -r["monto"]})
    if movs:
        dfm = pd.DataFrame(movs).sort_values("Fecha", ascending=False).head(60).reset_index(drop=True)
        st.caption(f"{len(dfm)} movimiento/s (más recientes primero)")
        st.dataframe(
            dfm.style.map(lambda v: "color:#3fb984;font-weight:700" if v >= 0
                          else "color:#ff8078;font-weight:700", subset=["Monto"])
               .format({"Monto": lambda v: ("+ " if v>=0 else "− ") + fmt(abs(v)).replace("−$ ","$ ")}),
            use_container_width=True, hide_index=True, height=380)
    else:
        st.info("Sin movimientos en este período.")

# ─────────────── INGRESOS ───────────────
with t_ing:
    st.metric("Total ingresos del período", fmt(tot_ing))
    stc, ste = st.tabs(["💳 Cuotas", "✨ Ingresos especiales"])

    with stc:
        ca, cb, cc = st.columns(3)
        ca.metric("Esperado", fmt(esperado))
        cb.metric("Cobrado", fmt(tot_cuotas))
        cc.metric("Pendiente", fmt(pendiente))
        st.progress(0 if esperado == 0 else min(1.0, tot_cuotas/esperado),
                    text=f"Cobrado {0 if esperado==0 else round(tot_cuotas/esperado*100)}%")

        tabla = socios.copy()
        pago_de = {r["socio_id"]: r for _, r in pagos_mes.iterrows()}
        tabla["Estado"] = tabla["socio_id"].map(lambda i: "PAGADO" if i in pago_de else "PENDIENTE")
        tabla["Fecha pago"] = tabla["socio_id"].map(lambda i: pago_de.get(i, {}).get("fecha", "—"))
        tabla = tabla.rename(columns={"nombre":"Socio","cuota":"Cuota"})
        st.dataframe(
            tabla[["Socio","Cuota","Estado","Fecha pago"]]
            .style.apply(lambda row: ["color:#ff8f8a;font-weight:700"]*len(row)
                         if row["Estado"]=="PENDIENTE" else [""]*len(row), axis=1)
            .format({"Cuota": fmt}),
            use_container_width=True, hide_index=True, height=360)

        if admin:
            with st.expander("🛠 Gestionar cobros y socios (solo admin)"):
                g1, g2 = st.columns(2)
                with g1:
                    if len(deudores):
                        ops = {f"{n} — {fmt(c)}": i for n, c, i in
                               zip(deudores["nombre"], deudores["cuota"], deudores["socio_id"])}
                        elegido = st.selectbox("Cobrar cuota a:", list(ops))
                        if st.button("✓ Registrar cobro", type="primary"):
                            s = socios[socios["socio_id"]==ops[elegido]].iloc[0]
                            nuevo = pd.DataFrame([{"pago_id":uid(),"socio_id":s["socio_id"],
                                                   "nombre":s["nombre"],"monto":s["cuota"],
                                                   "fecha":fecha_pago(anio,mes).isoformat()}])
                            guardar("cuotas", pd.concat([cuotas, nuevo], ignore_index=True))
                            st.rerun()
                    else:
                        st.success("Todos al día.")
                    pagados = {f"{pago_de[i]['nombre']} ({pago_de[i]['fecha']})": i for i in pago_de}
                    if pagados:
                        anul = st.selectbox("Anular pago de:", list(pagados))
                        if st.button("✖ Anular pago"):
                            guardar("cuotas", cuotas[cuotas["socio_id"]!=pagados[anul]])
                            st.rerun()
                with g2:
                    with st.form("nuevo_socio"):
                        st.markdown("**Agregar socio manualmente**")
                        nn = st.text_input("Nombre")
                        nc = st.number_input("Cuota mensual", 0.0, float(10**9), 5000.0)
                        if st.form_submit_button("＋ Agregar"):
                            if nn.strip():
                                guardar("socios", pd.concat([socios,
                                    pd.DataFrame([{"socio_id":uid(),"nombre":nn.strip(),"cuota":nc}])],
                                    ignore_index=True))
                                st.rerun()
                    if len(socios):
                        borrar = st.selectbox("Eliminar socio:", list(socios["nombre"]))
                        if st.button("🗑 Eliminar socio"):
                            guardar("socios", socios[socios["nombre"]!=borrar])
                            st.warning("Se elimina de la lista; sus pagos históricos se conservan.")
                            st.rerun()

    with ste:
        if admin:
            with st.form("nuevo_esp"):
                f1, f2, f3, f4 = st.columns([1,2,2,1])
                fe = f1.date_input("Fecha", fecha_defecto(anio, mes))
                ce = f2.text_input("Concepto")
                de = f3.text_input("Detalle (opcional)")
                me = f4.number_input("Monto", 0.0, float(10**9), 0.0)
                if st.form_submit_button("＋ Registrar ingreso especial", type="primary"):
                    if ce.strip() and me > 0:
                        guardar("especiales", pd.concat([esp, pd.DataFrame(
                            [{"ingreso_id":uid(),"fecha":fe.isoformat(),"concepto":ce.strip(),
                              "detalle":de.strip(),"monto":me}])], ignore_index=True))
                        st.rerun()
        st.metric("Total del período", fmt(tot_esp))
        if len(esp_mes):
            st.dataframe(
                esp_mes.sort_values("fecha", ascending=False)
                       .rename(columns={"fecha":"Fecha","concepto":"Concepto",
                                        "detalle":"Detalle","monto":"Monto"})[
                                        ["Fecha","Concepto","Detalle","Monto"]]
                       .style.format({"Monto": lambda v: "+ " + fmt(v)}),
                use_container_width=True, hide_index=True)
            if admin:
                ops = {f"{r['fecha']} · {r['concepto']} · {fmt(r['monto'])}": r["ingreso_id"]
                       for _, r in esp_mes.iterrows()}
                sel = st.selectbox("Eliminar ingreso:", list(ops))
                if st.button("🗑 Eliminar"):
                    guardar("especiales", esp[esp["ingreso_id"]!=ops[sel]]); st.rerun()
        else:
            st.info("Sin ingresos especiales en este período.")

# ─────────────── EGRESOS ───────────────
with t_egr:
    st.markdown("### Gastos")
    if admin:
        with st.form("nuevo_gas"):
            f1, f2, f3, f4 = st.columns([1,2,1.4,1])
            fg = f1.date_input("Fecha", fecha_defecto(anio, mes), key="fg")
            cg = f2.text_input("Concepto")
            cat = f3.selectbox("Categoría", CATEGORIAS)
            mg = f4.number_input("Monto", 0.0, float(10**9), 0.0)
            if st.form_submit_button("＋ Registrar gasto", type="primary"):
                if cg.strip() and mg > 0:
                    guardar("gastos", pd.concat([gas, pd.DataFrame(
                        [{"gasto_id":uid(),"fecha":fg.isoformat(),"concepto":cg.strip(),
                          "categoria":cat,"monto":mg}])], ignore_index=True))
                    st.rerun()

    st.metric("Total gastos del período", fmt(tot_gas))
    if len(gas_mes):
        por_cat = gas_mes.groupby("categoria")["monto"].sum().sort_values(ascending=False)
        st.bar_chart(por_cat.rename(fmt), horizontal=True, height=160, color="#ff8078")
        st.dataframe(
            gas_mes.sort_values("fecha", ascending=False)
                   .rename(columns={"fecha":"Fecha","concepto":"Concepto",
                                    "categoria":"Categoría","monto":"Monto"})[
                                    ["Fecha","Concepto","Categoría","Monto"]]
                   .style.format({"Monto": lambda v: "− " + fmt(v)}),
            use_container_width=True, hide_index=True)
        if admin:
            ops = {f"{r['fecha']} · {r['concepto']} · {fmt(r['monto'])}": r["gasto_id"]
                   for _, r in gas_mes.iterrows()}
            sel = st.selectbox("Eliminar gasto:", list(ops))
            if st.button("🗑 Eliminar gasto"):
                guardar("gastos", gas[gas["gasto_id"]!=ops[sel]]); st.rerun()
    else:
        st.info("Sin gastos en este período.")

st.divider()
st.caption("📖 Libro de cuentas transparente — todos los registros son públicos. "
           "Los datos se guardan en la carpeta `data/` del servidor.")

# ═══════════════════════ DATOS DE EJEMPLO ═══════════════════════
def cargar_demo():
    a, m = hoy.year, hoy.month
    kM = mes_key(a, m)
    kP = mes_key(a-1, 11) if m == 1 else mes_key(a, m-2)
    nombres = ["Marta González","Jorge Peralta","Lucía Fernández",
               "Andrés Sosa","Carolina Vega","Raúl Domínguez"]
    soc = pd.DataFrame([{"socio_id":uid(),"nombre":n,"cuota":5000} for n in nombres])
    pagos = []
    def pay(kk, i, dia):
        pagos.append({"pago_id":uid(),"socio_id":soc.iloc[i]["socio_id"],
                      "nombre":nombres[i],"monto":5000,"fecha":f"{kk}-{dia:02d}"})
    for i, d in [(0,3),(1,7),(4,12)]: pay(kM, i, d)
    for i, d in [(0,4),(1,5),(2,9),(4,15)]: pay(kP, i, d)
    guardar("socios", soc)
    guardar("cuotas", pd.DataFrame(pagos))
    guardar("especiales", pd.DataFrame([
        {"ingreso_id":uid(),"fecha":f"{kM}-10","concepto":"Kermés anual","detalle":"Evento en el salón","monto":85000},
        {"ingreso_id":uid(),"fecha":f"{kM}-21","concepto":"Alquiler de salón","detalle":"Familia Ruiz","monto":40000}]))
    guardar("gastos", pd.DataFrame([
        {"gasto_id":uid(),"fecha":f"{kM}-05","concepto":"Electricidad y agua","categoria":"Servicios","monto":18500},
        {"gasto_id":uid(),"fecha":f"{kM}-14","concepto":"Corte de césped","categoria":"Mantenimiento","monto":25000},
        {"gasto_id":uid(),"fecha":f"{kM}-25","concepto":"Pelotas y conos","categoria":"Insumos","monto":32000}]))

st.caption("")  # ancla
