import streamlit as st
import itertools
import pandas as pd
import os

# Configuración de la interfaz de Streamlit (Modo ancho para mejor visualización del calendario)
st.set_page_config(
    page_title="Generador de Horarios Inteligente",
    page_icon="🗓️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Estilos de diseño personalizados (Azul institucional, Naranja de acción y fondos limpios)
st.markdown("""
    <style>
    .main { background-color: #F8FAFC; }
    h1 { color: #1E3A8A; font-family: 'Segoe UI', Arial, sans-serif; font-weight: 700; }
    h2, h3 { color: #334155; font-family: 'Segoe UI', Arial, sans-serif; }
    .stButton>button { background-color: #F97316; color: white; border-radius: 8px; font-weight: bold; width: 100%; border: none; }
    .stButton>button:hover { background-color: #EA580C; color: white; }
    .stMultiSelect [data-baseweb="tag"] { background-color: #3B82F6; color: white; }
    .footer { text-align: center; margin-top: 50px; color: #94A3B8; font-size: 0.85rem; }
    </style>
""", unsafe_allow_html=True)

st.title("🗓️ Diseñador de Horarios Universitario Multi-Carreras")
st.write("Selecciona tu carrera, elige tus materias y diseña tu horario ideal optimizado según tus preferencias de profesores.")

CARPETA_DATA = "data"

if not os.path.exists(CARPETA_DATA):
    os.makedirs(CARPETA_DATA)

def parsear_oferta_completa(texto):
    """
    Parsea el bloque de texto con formato de 8 líneas por sesión:
    1. NRC, 2. Clave, 3. Materia, 4. Secc, 5. Día, 6. Horas (HHMM-HHMM), 7. Profesor, 8. Sesión/Aula
    """
    lineas = [linea.strip() for linea in texto.split("\n") if linea.strip()]
    nrc_dict = {}
    
    for i in range(0, len(lineas) - 7, 8):
        try:
            nrc = lineas[i]
            clave = lineas[i+1]
            materia = lineas[i+2]
            seccion = lineas[i+3]
            dia_letra = lineas[i+4]
            hora_rango = lineas[i+5]
            profesor = lineas[i+6].upper() # Normalizar nombre del profesor a mayúsculas
            aula = lineas[i+7]
            
            mapa_dias = {
                'L': 'Lunes', 
                'A': 'Martes', 
                'M': 'Miércoles', 
                'J': 'Jueves', 
                'V': 'Viernes', 
                'S': 'Sábado'
            }
            dia_nombre = mapa_dias.get(dia_letra.upper(), dia_letra)
            
            h_inicio = f"{hora_rango[:2]}:{hora_rango[2:4]}"
            h_fin = f"{hora_rango[5:7]}:{hora_rango[7:9]}"
            
            if nrc not in nrc_dict:
                nrc_dict[nrc] = {
                    "nrc": nrc,
                    "clave": clave,
                    "materia": materia,
                    "grupo": seccion,
                    "profesor": profesor,
                    "horario": {}
                }
            
            nrc_dict[nrc]["horario"][dia_nombre] = (h_inicio, h_fin)
            
        except Exception:
            continue
            
    materias_agrupadas = {}
    for nrc, datos in nrc_dict.items():
        nom_materia = datos["materia"]
        if nom_materia not in materias_agrupadas:
            materias_agrupadas[nom_materia] = []
        materias_agrupadas[nom_materia].append(datos)
        
    return materias_agrupadas

def hay_choque_entre_grupos(grupo_a, grupo_b):
    """Retorna True si dos secciones coinciden en el mismo día y se traslapan en horas."""
    for dia, (inicio_a, fin_a) in grupo_a["horario"].items():
        if dia in grupo_b["horario"]:
            inicio_b, fin_b = grupo_b["horario"][dia]
            if inicio_a < fin_b and inicio_b < fin_a:
                return True
    return False

def combinacion_es_compatible(combinacion):
    """Verifica si todos los elementos de una combinación son compatibles entre sí."""
    for i in range(len(combinacion)):
        for j in range(i + 1, len(combinacion)):
            if hay_choque_entre_grupos(combinacion[i], combinacion[j]):
                return False
    return True

def calcular_puntaje_horario(combo, pref, evit):
    """
    Suma +10 por cada profesor deseado y resta -10 por cada profesor a evitar.
    Esto permite ordenar las mejores opciones arriba sin descartar nada.
    """
    puntaje = 0
    for clase in combo:
        prof = clase["profesor"]
        if prof in pref:
            puntaje += 10
        if prof in evit:
            puntaje -= 10
    return puntaje

st.subheader("📁 Paso 1: Selecciona tu Carrera")

archivos_carreras = [f for f in os.listdir(CARPETA_DATA) if f.endswith(".txt")]
carreras_disponibles = [os.path.splitext(f)[0].replace("_", " ") for f in archivos_carreras]

col_origen, col_upload = st.columns([2, 1])
texto_horarios = ""
carrera_seleccionada = None

with col_origen:
    if carreras_disponibles:
        carrera_elegida = st.selectbox(
            "Selecciona una carrera precargada:",
            options=["-- Selecciona una opción --"] + carreras_disponibles
        )
        if carrera_elegida != "-- Selecciona una opción --":
            carrera_seleccionada = carrera_elegida
            archivo_nombre = carrera_elegida.replace(" ", "_") + ".txt"
            ruta_archivo = os.path.join(CARPETA_DATA, archivo_nombre)
            try:
                with open(ruta_archivo, "r", encoding="utf-8") as f:
                    texto_horarios = f.read()
            except UnicodeDecodeError:
                # Fallback de codificación por compatibilidad de sistemas operativos
                with open(ruta_archivo, "r", encoding="latin-1") as f:
                    texto_horarios = f.read()
    else:
        st.info("📂 No se detectaron carreras precargadas en la carpeta 'data/'. ¡Añade archivos de texto a tu repositorio!")

with col_upload:
    archivo_subido = st.file_uploader(
        "O importa manualmente tu propio archivo (.txt):",
        type=["txt"],
        help="Copia y guarda los bloques de horarios en un archivo .txt y súbelo aquí."
    )
    if archivo_subido is not None:
        texto_horarios = archivo_subido.read().decode("utf-8", errors="ignore")
        carrera_seleccionada = archivo_subido.name.replace(".txt", "")

if texto_horarios:
    oferta_total = parsear_oferta_completa(texto_horarios)
    todas_las_materias = sorted(list(oferta_total.keys()))
    
    if not todas_las_materias:
        st.error("⚠️ Error en el formato del archivo. Recuerda que debe estructurarse en bloques de exactamente 8 líneas por sesión.")
    else:
        st.success(f"📚 Datos cargados con éxito para: **{carrera_seleccionada}**. Se encontraron **{len(todas_las_materias)}** materias diferentes.")
        
        st.subheader("🎯 Paso 2: Selecciona las Materias de tu Semestre")
        materias_seleccionadas = st.multiselect(
            "Elige todas las asignaturas que vas a cursar (No se sacrificará ninguna):",
            options=todas_las_materias,
            help="El sistema buscará combinaciones que incluyan obligatoriamente todas las materias seleccionadas."
        )
        
        if not materias_seleccionadas:
            st.info("💡 Selecciona tus materias arriba para comenzar a modelar tus opciones de horario.")
        else:
            todos_profesores = sorted(list(set(
                grupo["profesor"] 
                for mat in materias_seleccionadas 
                for grupo in oferta_total[mat]
            )))
            
            st.subheader("👨‍🏫 Paso 3: Configura tus Profesores y Filtros de Tiempo")
            col_pref, col_evit = st.columns(2)
            
            with col_pref:
                profesores_preferidos = st.multiselect(
                    "⭐ Profesores que PREFIERES (Prioridad Alta):",
                    options=todos_profesores,
                    help="Los horarios que incluyan a estos académicos se posicionarán al inicio de la lista."
                )
                
            with col_evit:
                opciones_evitar = [p for p in todos_profesores if p not in profesores_preferidos]
                profesores_a_evitar = st.multiselect(
                    "⚠️ Profesores que deseas EVITAR (Baja prioridad):",
                    options=opciones_evitar,
                    help="No eliminará la opción de horario si es la única disponible, pero la enviará al final."
                )
                
            st.sidebar.header("📅 Configuración de Días")
            dias_a_evitar = st.sidebar.multiselect(
                "Descartar combinaciones con clases en estos días:",
                options=["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado"],
                help="Este filtro eliminará por completo cualquier opción que requiera asistir los días marcados."
            )
            
            listas_de_grupos = [oferta_total[mat] for mat in materias_seleccionadas]
            
            todas_combinaciones = list(itertools.product(*listas_de_grupos))
            combinaciones_validas = [combo for combo in todas_combinaciones if combinacion_es_compatible(combo)]
            
            combinaciones_filtradas_dias = []
            for combo in combinaciones_validas:
                tiene_clase_dia_restringido = any(dia in dias_a_evitar for g in combo for dia in g["horario"].keys())
                if not tiene_clase_dia_restringido:
                    combinaciones_filtradas_dias.append(combo)
            
            if not combinaciones_validas:
                st.error("❌ **Conflicto de Horarios:** Es matemáticamente imposible llevar todas estas materias juntas sin que se encimen. Intenta modificando tu lista de materias.")
            elif not combinaciones_filtradas_dias:
                st.warning("⚠️ El filtro de días libres descartó todas las opciones viables. Prueba desmarcando algún día en el panel izquierdo.")
            else:
                combinaciones_con_puntos = []
                for combo in combinaciones_filtradas_dias:
                    puntos = calcular_puntaje_horario(combo, profesores_preferidos, profesores_a_evitar)
                    combinaciones_con_puntos.append((puntos, combo))
                
                combinaciones_con_puntos.sort(key=lambda x: x[0], reverse=True)
                
                st.sidebar.header("⚙️ Horarios Generados")
                st.sidebar.markdown(f"Materias a cursar: **{len(materias_seleccionadas)}**")
                st.sidebar.markdown(f"Opciones viables: **{len(combinaciones_filtradas_dias)}**")
                
                opciones_select = []
                for idx, (puntos, _) in enumerate(combinaciones_con_puntos):
                    if puntos > 0:
                        estrellas = "⭐" * (puntos // 10)
                        opciones_select.append(f"Opción {idx + 1} ({estrellas} Recomendado / +{puntos} pts)")
                    elif puntos < 0:
                        opciones_select.append(f"Opción {idx + 1} (⚠️ Lleva profes a evitar / {puntos} pts)")
                    else:
                        opciones_select.append(f"Opción {idx + 1} (Neutral / 0 pts)")
                
                idx_seleccionado = st.sidebar.selectbox(
                    "Selecciona una opción para ver detalles y agenda:",
                    range(len(combinaciones_con_puntos)),
                    format_func=lambda x: opciones_select[x]
                )
                
                puntaje_actual, horario_elegido = combinaciones_con_puntos[idx_seleccionado]
                
                st.subheader(f"📋 Detalles de la Opción Seleccionada (Opción {idx_seleccionado + 1})")
                
                if puntaje_actual > 0:
                    st.info(f"🎉 **¡Excelente Horario!** Tiene una puntuación de **+{puntaje_actual}** porque coincide de gran manera con tus preferencias de profesores.")
                elif puntaje_actual < 0:
                    st.warning(f"⚠️ **Nota Importante:** Este horario tiene puntaje negativo (**{puntaje_actual}**) porque incluye profesores de tu lista a evitar. Sin embargo, se guardó la opción para que no sacrifiques tus materias.")
                
                datos_tabla = []
                for clase in horario_elegido:
                    dias_formateados = ", ".join([f"{dia} ({rango[0]}-{rango[1]})" for dia, rango in clase["horario"].items()])
                    
                    prof = clase["profesor"]
                    tag_prof = prof
                    if prof in profesores_preferidos:
                        tag_prof = f"⭐ {prof}"
                    elif prof in profesores_a_evitar:
                        tag_prof = f"⚠️ {prof}"
                        
                    datos_tabla.append({
                        "Materia": clase["materia"],
                        "Clave": clase["clave"],
                        "NRC": clase["nrc"],
                        "Sección": clase["grupo"],
                        "Profesor": tag_prof,
                        "Horarios Semanales": dias_formateados
                    })
                
                st.table(pd.DataFrame(datos_tabla))
                
                st.subheader("📅 Distribución en la Agenda Semanal")
                
                dias_semana = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado"]
                horas_dia = [f"{h:02d}:00" for h in range(7, 22)]
                agenda_df = pd.DataFrame("", index=horas_dia, columns=dias_semana)
                
                for clase in horario_elegido:
                    for dia, (inicio, fin) in clase["horario"].items():
                        if dia in agenda_df.columns:
                            try:
                                h_inicio_int = int(inicio.split(":")[0])
                                h_fin_int = int(fin.split(":")[0])
                                
                                for h in range(h_inicio_int, h_fin_int + 1):
                                    slot_hora = f"{h:02d}:00"
                                    if slot_hora in agenda_df.index:
                                        agenda_df.at[slot_hora, dia] = f"{clase['materia']} ({clase['grupo']})"
                            except Exception:
                                pass
                
                agenda_filtrada = agenda_df.loc[(agenda_df != "").any(axis=1)]
                
                if not agenda_filtrada.empty:
                    st.dataframe(
                        agenda_filtrada.style.map(
                            lambda valor: 'background-color: #1E3A8A; color: white; font-weight: bold; text-align: center;' if valor != "" else ''
                        ),
                        use_container_width=True
                    )
                else:
                    st.info("No se registran sesiones en las horas estándar programadas.")
else:
    st.info("👈 Por favor, selecciona una carrera precargada o sube tu archivo `.txt` en el Paso 1 para comenzar.")

st.markdown("""
    <div class="footer">
        Desarrollado para optimizar el proceso de inscripción académica. Universidad Libre de Choques © 2026.
    </div>
""", unsafe_allow_html=True)
