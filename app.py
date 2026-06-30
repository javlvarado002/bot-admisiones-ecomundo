import os
import json
import re
from datetime import datetime

import requests
import gspread
from flask import Flask, request
from google.oauth2.service_account import Credentials


# ============================================================
# PIAE - PLATAFORMA INTELIGENTE DE ADMISIONES ECOMUNDO
# APP.PY VERSION 3.0
# ============================================================
# Requisitos en requirements.txt:
# flask
# gunicorn
# requests
# gspread
# google-auth
#
# Variables de entorno en Render:
# VERIFY_TOKEN=ecomundo2026
# WHATSAPP_TOKEN=...
# PHONE_NUMBER_ID=...
# GOOGLE_CREDENTIALS={JSON completo de cuenta de servicio}
# ============================================================

app = Flask(__name__)

VERIFY_TOKEN = os.environ.get("VERIFY_TOKEN", "ecomundo2026")
WHATSAPP_TOKEN = os.environ.get("WHATSAPP_TOKEN")
PHONE_NUMBER_ID = os.environ.get("PHONE_NUMBER_ID")
GOOGLE_CREDENTIALS = os.environ.get("GOOGLE_CREDENTIALS")

SPREADSHEET_NAME = "Admisiones Ecomundo"
ASESORES_SHEET_NAME = "Asesores"

PRIVACIDAD_URL = (
    "https://ecomundo.edu.ec/np/wp-content/uploads/2025/11/"
    "CONSENTIMIENTO-PARA-EL-TRATAMIENTO-DE-DATOS-PERSONALES-TERCEROS-formularios.pdf"
)

INSCRIPCION_URL = "https://ecomundo.edu.ec/"

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

USER_STATE = {}

NIVELES = {
    "1": "Maternal",
    "2": "Inicial 2 (3 años)",
    "3": "Inicial 2 (4 años)",
    "4": "Primer Grado",
    "5": "Segundo Grado",
    "6": "Tercer Grado",
    "7": "Cuarto Grado",
    "8": "Quinto Grado",
    "9": "Sexto Grado",
    "10": "Séptimo Grado",
    "11": "Octavo Grado",
    "12": "Noveno Grado",
    "13": "Décimo Grado",
    "14": "Primero de Bachillerato",
    "15": "Segundo de Bachillerato",
}

NIVELES_TEXTO = """1️⃣ Maternal
2️⃣ Inicial 2 (3 años)
3️⃣ Inicial 2 (4 años)
4️⃣ Primer Grado
5️⃣ Segundo Grado
6️⃣ Tercer Grado
7️⃣ Cuarto Grado
8️⃣ Quinto Grado
9️⃣ Sexto Grado
10. Séptimo Grado
11. Octavo Grado
12. Noveno Grado
13. Décimo Grado
14. Primero de Bachillerato
15. Segundo de Bachillerato"""

MENU_OPCIONES = {"1", "2", "3", "4", "5", "6", "7"}


def conectar_google():
    if not GOOGLE_CREDENTIALS:
        raise RuntimeError("Falta GOOGLE_CREDENTIALS en variables de entorno.")
    cred_dict = json.loads(GOOGLE_CREDENTIALS)
    credentials = Credentials.from_service_account_info(cred_dict, scopes=SCOPES)
    return gspread.authorize(credentials)


def obtener_spreadsheet():
    gc = conectar_google()
    return gc.open(SPREADSHEET_NAME)


def hoja_admisiones():
    return obtener_spreadsheet().sheet1


def hoja_asesores():
    return obtener_spreadsheet().worksheet(ASESORES_SHEET_NAME)


def generar_codigo_caso():
    sheet = hoja_admisiones()
    total_filas = len(sheet.get_all_values())
    return f"ADM-2026-{total_filas:04d}"


def guardar_lead(telefono_contacto, representante, nivel, correo, asesor):
    sheet = hoja_admisiones()
    codigo = generar_codigo_caso()
    sheet.append_row([
        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        telefono_contacto,
        representante,
        "",
        "",
        nivel,
        correo,
        "Pendiente Contacto",
        asesor,
        codigo,
    ])
    return codigo


def obtener_asesor():
    sheet = hoja_asesores()
    asesores = sheet.get_all_records()
    activos = []
    for fila, asesor in enumerate(asesores, start=2):
        activo = str(asesor.get("Activo", "")).strip().lower()
        if activo == "si":
            asignados = asesor.get("Asignados", 0) or 0
            try:
                asignados = int(asignados)
            except ValueError:
                asignados = 0
            activos.append({
                "fila": fila,
                "nombre": str(asesor.get("Nombres", "Asesor asignado")).strip(),
                "correo": str(asesor.get("Correo", "")).strip(),
                "whatsapp": str(asesor.get("WhatsApp", "")).strip(),
                "asignados": asignados,
            })
    if not activos:
        return {"nombre": "Sin asesor disponible", "correo": "", "whatsapp": ""}
    seleccionado = sorted(activos, key=lambda a: a["asignados"])[0]
    sheet.update_cell(seleccionado["fila"], 5, seleccionado["asignados"] + 1)
    return seleccionado


def enviar_payload(payload):
    if not WHATSAPP_TOKEN or not PHONE_NUMBER_ID:
        print("ERROR: faltan WHATSAPP_TOKEN o PHONE_NUMBER_ID.")
        return
    url = f"https://graph.facebook.com/v23.0/{PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {WHATSAPP_TOKEN}",
        "Content-Type": "application/json",
    }
    response = requests.post(url, headers=headers, json=payload, timeout=20)
    print("RESPUESTA WHATSAPP:", response.status_code, response.text)


def enviar_texto(telefono, mensaje):
    payload = {
        "messaging_product": "whatsapp",
        "to": telefono,
        "type": "text",
        "text": {"body": mensaje},
    }
    enviar_payload(payload)


def enviar_botones_privacidad(telefono):
    payload = {
        "messaging_product": "whatsapp",
        "to": telefono,
        "type": "interactive",
        "interactive": {
            "type": "button",
            "body": {
                "text": (
                    "👋 ¡Hola! Bienvenido/a a Unidad Educación Particular Bilingüe Ecomundo.\n\n"
                    "Para poder atender su requerimiento por este canal, necesitamos que lea y acepte "
                    "nuestra Política de Privacidad y Tratamiento de Datos Personales.\n\n"
                    f"🔗 Privacidad y Tratamiento de Datos Personales:\n{PRIVACIDAD_URL}\n\n"
                    "¿Nos confirma su aceptación para brindarle una atención personalizada?"
                )
            },
            "action": {
                "buttons": [
                    {"type": "reply", "reply": {"id": "acepto_privacidad", "title": "✅ Sí"}},
                    {"type": "reply", "reply": {"id": "no_acepto_privacidad", "title": "❌ No"}},
                ]
            },
        },
    }
    enviar_payload(payload)


def mensaje_solicitud_datos_representante():
    return (
        "✅ ¡Gracias por confirmar!\n\n"
        "Para continuar con el proceso de admisión, envíe en un solo mensaje la siguiente información:\n\n"
        "👤 Nombre del representante\n"
        "📧 Correo electrónico\n"
        "📱 Teléfono de contacto\n\n"
        "📝 *Ejemplo:*\n\n"
        "María Pérez\n"
        "correo@ejemplo.com\n"
        "0999999999"
    )


def mensaje_pedir_nivel():
    return (
        "🎓 Por favor escriba el número del nivel de estudio de interés:\n\n"
        f"{NIVELES_TEXTO}\n\n"
        "📝 Ejemplo:\n5"
    )


def mensaje_otro_hijo():
    return (
        "¿Tiene otro hijo/a interesado/a en el proceso de admisión?\n\n"
        "1️⃣ Sí, registrar otro nivel de estudio\n"
        "2️⃣ No, continuar al menú principal\n\n"
        "✍️ Escriba 1 o 2."
    )


def mensaje_menu_principal():
    return (
        "📚 *Menú principal*\n\n"
        "1️⃣ 📋 Proceso de admisión\n"
        "2️⃣ 💰 Precios\n"
        "3️⃣ ⚽ Actividades extracurriculares\n"
        "4️⃣ 🎁 Descuento disponible\n"
        "5️⃣ 📝 Inscripción QR\n"
        "6️⃣ 👩‍💼 Consulta con un asesor\n"
        "7️⃣ ✅ Finalizar\n\n"
        "✍️ Escriba únicamente el número de la opción que desea consultar."
    )


def mensaje_final():
    return (
        "🎓 Gracias por elegir Ecomundo Educación Particular Bilingüe.\n\n"
        "Ha sido un gusto atenderle.\n\n"
        "Si desea volver a realizar otra consulta, escriba: *Hola*"
    )


def mensaje_error_datos_representante():
    return (
        "No logramos registrar la información.\n\n"
        "Por favor envíe los datos en este orden:\n\n"
        "👤 Nombre del representante\n"
        "📧 Correo electrónico\n"
        "📱 Teléfono de contacto\n\n"
        "Ejemplo:\nMaría Pérez\ncorreo@ejemplo.com\n0999999999"
    )


def mensaje_volver_menu():
    return "\n━━━━━━━━━━━━━━━━━━━━━━\n\n¿Desea realizar otra consulta?\n\n" + mensaje_menu_principal()


def normalizar_texto(texto):
    return str(texto or "").strip().lower()


def extraer_mensaje_entrante(value):
    msg = value["messages"][0]
    tipo = msg.get("type")
    if tipo == "text":
        return msg["text"]["body"].strip()
    if tipo == "interactive":
        interactive = msg.get("interactive", {})
        if interactive.get("type") == "button_reply":
            return interactive["button_reply"]["id"]
        if interactive.get("type") == "list_reply":
            return interactive["list_reply"]["id"]
    return ""


def extraer_datos_representante(mensaje):
    lineas = [linea.strip() for linea in mensaje.split("\n") if linea.strip()]
    if len(lineas) < 3:
        return None
    representante, correo, telefono_contacto = lineas[0], lineas[1], lineas[2]
    if "@" not in correo or "." not in correo:
        return None
    if len(re.sub(r"\D", "", telefono_contacto)) < 7:
        return None
    return {"representante": representante, "correo": correo, "telefono_contacto": telefono_contacto}


def obtener_nivel_por_codigo(codigo):
    return NIVELES.get(str(codigo or "").strip())


def convertir_numero_ecuador(numero):
    limpio = re.sub(r"\D", "", str(numero or ""))
    if limpio.startswith("593"):
        return limpio
    if limpio.startswith("0"):
        return "593" + limpio[1:]
    return limpio


def obtener_niveles_usuario(telefono):
    return USER_STATE.get(telefono, {}).get("niveles", [])


def resumen_niveles_usuario(telefono):
    niveles = obtener_niveles_usuario(telefono)
    if not niveles:
        return "No registra niveles seleccionados."
    return "\n".join([f"• {nivel}" for nivel in niveles])


def registrar_nivel_para_usuario(telefono, nivel_codigo):
    nivel = obtener_nivel_por_codigo(nivel_codigo)
    if not nivel:
        return None
    estado = USER_STATE.get(telefono, {})
    codigo = guardar_lead(
        telefono_contacto=estado.get("telefono_contacto", telefono),
        representante=estado.get("representante", ""),
        nivel=nivel,
        correo=estado.get("correo", ""),
        asesor=estado.get("asesor", ""),
    )
    estado.setdefault("codigos", [])
    estado.setdefault("niveles", [])
    estado["codigos"].append(codigo)
    estado["niveles"].append(nivel)
    estado["ultimo_codigo"] = codigo
    estado["ultimo_nivel"] = nivel
    return {"codigo": codigo, "nivel": nivel}


def categoria_nivel(nivel):
    n = nivel.lower()
    if "maternal" in n or "inicial" in n:
        return "inicial"
    if "bachillerato" in n:
        return "bachillerato"
    return "egb"


def proceso_por_nivel(nivel):
    categoria = categoria_nivel(nivel)
    if categoria == "inicial":
        return (
            f"🏫 *{nivel}*\n\n"
            "1. Registro de datos del representante.\n"
            "2. Contacto del equipo de admisiones.\n"
            "3. Revisión de disponibilidad del nivel.\n"
            "4. Agendamiento de visita o entrevista informativa.\n"
            "5. Orientación sobre requisitos y proceso de matrícula."
        )
    if categoria == "egb":
        return (
            f"🏫 *{nivel}*\n\n"
            "1. Registro de datos del representante.\n"
            "2. Contacto del asesor asignado.\n"
            "3. Revisión de cupo disponible.\n"
            "4. Socialización de requisitos académicos y administrativos.\n"
            "5. Continuación del proceso de admisión y matrícula."
        )
    return (
        f"🎓 *{nivel}*\n\n"
        "1. Registro de datos del representante.\n"
        "2. Contacto del equipo de admisiones.\n"
        "3. Revisión de disponibilidad.\n"
        "4. Orientación sobre requisitos de ingreso a Bachillerato.\n"
        "5. Continuación del proceso de admisión y matrícula."
    )


def precios_por_nivel(nivel):
    return (
        f"💰 *{nivel}*\n\n"
        "Los valores pueden variar según el nivel de estudio solicitado y las políticas institucionales vigentes. "
        "Un asesor de admisiones le compartirá la información actualizada y personalizada."
    )


def extracurriculares_por_nivel(nivel):
    categoria = categoria_nivel(nivel)
    if categoria == "inicial":
        return (
            f"🌈 *{nivel}*\n\n"
            "Actividades orientadas al desarrollo integral, psicomotricidad, expresión artística, "
            "estimulación temprana y experiencias formativas acordes a la edad."
        )
    if categoria == "egb":
        return (
            f"📚 *{nivel}*\n\n"
            "Actividades deportivas, artísticas, tecnológicas y formativas que fortalecen el desarrollo académico, "
            "social y personal del estudiante."
        )
    return (
        f"🎓 *{nivel}*\n\n"
        "Actividades orientadas al liderazgo, deportes, arte, tecnología, orientación vocacional "
        "y formación integral para estudiantes de Bachillerato."
    )


def descuentos_por_nivel(nivel):
    return (
        f"🎁 *{nivel}*\n\n"
        "Los descuentos y beneficios dependen de las políticas institucionales vigentes, "
        "el nivel de ingreso y las condiciones aplicables. El asesor asignado podrá brindarle mayor detalle."
    )


def construir_respuesta_por_niveles(titulo, telefono, generador):
    niveles = obtener_niveles_usuario(telefono)
    if not niveles:
        return f"{titulo}\n\nNo se encontraron niveles registrados. Para iniciar nuevamente, escriba: *Hola*"
    bloques = [titulo]
    for idx, nivel in enumerate(niveles, start=1):
        bloques.append(f"👦 *Estudiante {idx}*")
        bloques.append(generador(nivel))
    return "\n\n━━━━━━━━━━━━━━━━━━━━━━\n\n".join(bloques)


def responder_menu(telefono, opcion):
    opcion = str(opcion or "").strip()
    estado = USER_STATE.get(telefono, {})
    asesor = estado.get("asesor", "Asesor asignado")
    asesor_whatsapp = estado.get("asesor_whatsapp", "")
    codigo = estado.get("ultimo_codigo", "")
    codigos = estado.get("codigos", [])

    if opcion == "1":
        enviar_texto(telefono, construir_respuesta_por_niveles(
            "📋 *Proceso de admisión*\n\nHemos preparado la información correspondiente a los niveles registrados:",
            telefono,
            proceso_por_nivel,
        ))
    elif opcion == "2":
        enviar_texto(telefono, construir_respuesta_por_niveles(
            "💰 *Información de precios*\n\nEstos son los niveles consultados:",
            telefono,
            precios_por_nivel,
        ))
    elif opcion == "3":
        enviar_texto(telefono, construir_respuesta_por_niveles(
            "⚽ *Actividades extracurriculares*\n\nInformación según los niveles registrados:",
            telefono,
            extracurriculares_por_nivel,
        ))
    elif opcion == "4":
        enviar_texto(telefono, construir_respuesta_por_niveles(
            "🎁 *Descuento disponible*\n\nInformación general según los niveles registrados:",
            telefono,
            descuentos_por_nivel,
        ))
    elif opcion == "5":
        enviar_texto(
            telefono,
            "📝 *Inscripción QR*\n\n"
            "El área de admisiones le proporcionará el enlace o QR oficial para continuar con el proceso de inscripción.\n\n"
            f"También puede revisar información institucional en:\n{INSCRIPCION_URL}"
        )
    elif opcion == "6":
        codigos_texto = "\n".join([f"• {c}" for c in codigos]) or codigo or "No disponible"
        mensaje = (
            "👩‍💼 *Consulta con un asesor*\n\n"
            f"📋 Códigos de seguimiento:\n{codigos_texto}\n\n"
            f"👩‍💼 Asesor asignado: *{asesor}*\n\n"
            "🎓 Niveles registrados:\n"
            f"{resumen_niveles_usuario(telefono)}\n\n"
        )
        if asesor_whatsapp:
            numero = convertir_numero_ecuador(asesor_whatsapp)
            mensaje += (
                "Puede contactar directamente a su asesor en el siguiente enlace:\n"
                f"https://wa.me/{numero}?text=Hola,%20deseo%20información%20sobre%20mi%20proceso%20de%20admisión."
            )
        else:
            mensaje += "Uno de nuestros asesores se pondrá en contacto con usted en las próximas horas."
        enviar_texto(telefono, mensaje)
    elif opcion == "7":
        USER_STATE[telefono] = {"estado": "finalizado"}
        enviar_texto(telefono, mensaje_final())
        return
    else:
        enviar_texto(telefono, "Por favor seleccione una opción válida del 1 al 7.")

    enviar_texto(telefono, mensaje_volver_menu())


def iniciar_flujo(telefono):
    USER_STATE[telefono] = {"estado": "inicio"}
    enviar_botones_privacidad(telefono)


def aceptar_privacidad(telefono):
    USER_STATE[telefono] = {"estado": "esperando_datos_representante"}
    enviar_texto(telefono, mensaje_solicitud_datos_representante())


def rechazar_privacidad(telefono):
    USER_STATE[telefono] = {"estado": "finalizado"}
    enviar_texto(
        telefono,
        "Gracias por contactarnos.\n\nNo podremos recopilar ni procesar información personal sin su consentimiento."
    )


def manejar_datos_representante(telefono, mensaje_original):
    datos = extraer_datos_representante(mensaje_original)
    if not datos:
        enviar_texto(telefono, mensaje_error_datos_representante())
        return
    asesor = obtener_asesor()
    USER_STATE[telefono] = {
        "estado": "esperando_nivel_hijo",
        "representante": datos["representante"],
        "correo": datos["correo"],
        "telefono_contacto": datos["telefono_contacto"],
        "asesor": asesor["nombre"],
        "asesor_correo": asesor.get("correo", ""),
        "asesor_whatsapp": asesor.get("whatsapp", ""),
        "codigos": [],
        "niveles": [],
        "ultimo_codigo": "",
        "ultimo_nivel": "",
    }
    enviar_texto(telefono, f"✅ Datos del representante registrados correctamente.\n\n👤 Representante: *{datos['representante']}*")
    enviar_texto(telefono, mensaje_pedir_nivel())


def manejar_nivel_hijo(telefono, mensaje_original):
    resultado = registrar_nivel_para_usuario(telefono, mensaje_original.strip())
    if not resultado:
        enviar_texto(telefono, "Por favor escriba un número válido del 1 al 15.")
        enviar_texto(telefono, mensaje_pedir_nivel())
        return
    total = len(USER_STATE.get(telefono, {}).get("niveles", []))
    enviar_texto(
        telefono,
        f"✅ Nivel registrado correctamente.\n\n👦 Estudiante {total}\n🎓 Nivel: *{resultado['nivel']}*\n📋 Código: *{resultado['codigo']}*"
    )
    USER_STATE[telefono]["estado"] = "preguntar_otro_hijo"
    enviar_texto(telefono, mensaje_otro_hijo())


def manejar_otro_hijo(telefono, mensaje):
    if mensaje == "1":
        USER_STATE[telefono]["estado"] = "esperando_nivel_hijo"
        enviar_texto(telefono, mensaje_pedir_nivel())
        return
    if mensaje == "2":
        USER_STATE[telefono]["estado"] = "menu_principal"
        estado = USER_STATE.get(telefono, {})
        codigos = estado.get("codigos", [])
        codigos_texto = "\n".join([f"• {c}" for c in codigos]) or "No disponible"
        niveles_texto = resumen_niveles_usuario(telefono)
        enviar_texto(
            telefono,
            "✅ Registro completado correctamente.\n\n"
            f"👤 Representante:\n*{estado.get('representante', '')}*\n\n"
            f"👦 Estudiantes / niveles registrados:\n{niveles_texto}\n\n"
            f"👩‍💼 Asesor asignado:\n*{estado.get('asesor', '')}*\n\n"
            f"📋 Códigos generados:\n{codigos_texto}"
        )
        enviar_texto(telefono, mensaje_menu_principal())
        return
    enviar_texto(telefono, mensaje_otro_hijo())


def manejar_menu_principal(telefono, mensaje):
    if mensaje not in MENU_OPCIONES:
        enviar_texto(telefono, "Por favor seleccione una opción válida del 1 al 7.")
        enviar_texto(telefono, mensaje_menu_principal())
        return
    responder_menu(telefono, mensaje)


@app.route("/")
def home():
    return "PIAE Ecomundo activo - Version 3.0"


@app.route("/webhook", methods=["GET"])
def verify():
    mode = request.args.get("hub.mode")
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")
    if mode == "subscribe" and token == VERIFY_TOKEN:
        return challenge, 200
    return "Error de verificación", 403


@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json()
    print("MENSAJE RECIBIDO:", data)
    try:
        value = data["entry"][0]["changes"][0]["value"]
        if "messages" not in value:
            return "OK", 200
        telefono = value["messages"][0]["from"]
        mensaje_original = extraer_mensaje_entrante(value)
        mensaje = normalizar_texto(mensaje_original)
        print("TELÉFONO:", telefono)
        print("MENSAJE:", mensaje_original)

        if mensaje in ["hola", "inicio", "menu", "menú", "reiniciar", "reset"]:
            iniciar_flujo(telefono)
            return "OK", 200
        if mensaje in ["acepto_privacidad", "a", "si", "sí", "acepto"]:
            aceptar_privacidad(telefono)
            return "OK", 200
        if mensaje in ["no_acepto_privacidad", "b", "no", "no acepto"]:
            rechazar_privacidad(telefono)
            return "OK", 200

        estado_actual = USER_STATE.get(telefono, {}).get("estado")
        if estado_actual == "esperando_datos_representante":
            manejar_datos_representante(telefono, mensaje_original)
            return "OK", 200
        if estado_actual == "esperando_nivel_hijo":
            manejar_nivel_hijo(telefono, mensaje_original)
            return "OK", 200
        if estado_actual == "preguntar_otro_hijo":
            manejar_otro_hijo(telefono, mensaje)
            return "OK", 200
        if estado_actual == "menu_principal":
            manejar_menu_principal(telefono, mensaje)
            return "OK", 200
        if estado_actual == "finalizado":
            enviar_texto(telefono, "Para iniciar una nueva consulta, escriba: *Hola*")
            return "OK", 200
        enviar_texto(telefono, "Para iniciar el proceso de admisiones, escriba: *Hola*")
    except Exception as e:
        print("ERROR EN WEBHOOK:", e)
    return "OK", 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
