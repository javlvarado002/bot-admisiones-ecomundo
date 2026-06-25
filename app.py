import os
import json
import requests
import gspread
from datetime import datetime
from flask import Flask, request
from google.oauth2.service_account import Credentials

app = Flask(__name__)

VERIFY_TOKEN = os.environ.get("VERIFY_TOKEN", "ecomundo2026")
WHATSAPP_TOKEN = os.environ.get("WHATSAPP_TOKEN")
PHONE_NUMBER_ID = os.environ.get("PHONE_NUMBER_ID")
GOOGLE_CREDENTIALS = os.environ.get("GOOGLE_CREDENTIALS")

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

USER_STATE = {}

PRIVACIDAD_URL = "https://ecomundo.edu.ec/np/wp-content/uploads/2025/11/CONSENTIMIENTO-PARA-EL-TRATAMIENTO-DE-DATOS-PERSONALES-TERCEROS-formularios.pdf"

NIVELES = {
    "1": "Maternal",
    "2": "Inicial 2 (3 años)",
    "3": "Inicial 2 (4 años)",
    "4": "PRIMER GRADO",
    "5": "SEGUNDO GRADO",
    "6": "TERCER GRADO",
    "7": "CUARTO GRADO",
    "8": "QUINTO GRADO",
    "9": "SEXTO GRADO",
    "10": "SÉPTIMO GRADO",
    "11": "OCTAVO GRADO",
    "12": "NOVENO GRADO",
    "13": "DÉCIMO GRADO",
    "14": "PRIMERO BACHILLERATO",
    "15": "SEGUNDO BACHILLERATO"
}


def conectar_google():
    cred_dict = json.loads(GOOGLE_CREDENTIALS)
    credentials = Credentials.from_service_account_info(cred_dict, scopes=SCOPES)
    return gspread.authorize(credentials)


def conectar_sheet():
    gc = conectar_google()
    return gc.open("Admisiones Ecomundo").sheet1


def obtener_asesor():
    gc = conectar_google()
    hoja_asesores = gc.open("Admisiones Ecomundo").worksheet("Asesores")
    asesores = hoja_asesores.get_all_records()

    activos = []

    for index, asesor in enumerate(asesores, start=2):
        activo = str(asesor.get("Activo", "")).strip().lower()

        if activo == "si":
            asignados = asesor.get("Asignados", 0)
            if asignados == "":
                asignados = 0

            activos.append({
                "fila": index,
                "nombre": asesor.get("Nombres", "Asesor asignado"),
                "asignados": int(asignados)
            })

    if not activos:
        return "Sin asesor disponible"

    asesor_seleccionado = sorted(activos, key=lambda x: x["asignados"])[0]

    hoja_asesores.update_cell(
        asesor_seleccionado["fila"],
        5,
        asesor_seleccionado["asignados"] + 1
    )

    return asesor_seleccionado["nombre"]


def generar_codigo_caso():
    sheet = conectar_sheet()
    total_filas = len(sheet.get_all_values())
    return f"ADM-2026-{total_filas:04d}"


def guardar_en_sheets(telefono_whatsapp, representante, estudiante, edad, nivel, correo, estado, asesor=""):
    sheet = conectar_sheet()
    codigo = generar_codigo_caso()

    sheet.append_row([
        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        telefono_whatsapp,
        representante,
        estudiante,
        edad,
        nivel,
        correo,
        estado,
        asesor,
        codigo
    ])

    return codigo


def enviar_payload(payload):
    url = f"https://graph.facebook.com/v23.0/{PHONE_NUMBER_ID}/messages"

    headers = {
        "Authorization": f"Bearer {WHATSAPP_TOKEN}",
        "Content-Type": "application/json"
    }

    response = requests.post(url, headers=headers, json=payload)
    print("RESPUESTA WHATSAPP:", response.status_code, response.text)


def enviar_texto(telefono, mensaje):
    payload = {
        "messaging_product": "whatsapp",
        "to": telefono,
        "type": "text",
        "text": {"body": mensaje}
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
                    {"type": "reply", "reply": {"id": "no_acepto_privacidad", "title": "❌ No"}}
                ]
            }
        }
    }
    enviar_payload(payload)


def mensaje_solicitud_datos():
    niveles = "\n".join([f"{k}. {v}" for k, v in NIVELES.items()])

    return (
        "✅ ¡Gracias por confirmar!\n\n"
        "Para continuar con el proceso de admisión, por favor envíe los siguientes datos en un solo mensaje. "
        "Esta información nos sirve para poder tomar contacto inmediato con usted:\n\n"
        "Nombre del representante:\n"
        "Correo:\n"
        "Teléfono:\n"
        "Seleccione el número del nivel de estudio de su interés:\n\n"
        f"{niveles}\n\n"
        "Ejemplo:\n"
        "María Pérez\n"
        "correo@ejemplo.com\n"
        "0999999999\n"
        "15"
    )


def enviar_menu_consultas(telefono):
    payload = {
        "messaging_product": "whatsapp",
        "to": telefono,
        "type": "interactive",
        "interactive": {
            "type": "list",
            "body": {
                "text": "Por favor escoja la información que desea consultar:"
            },
            "action": {
                "button": "Ver opciones",
                "sections": [
                    {
                        "title": "Información disponible",
                        "rows": [
                            {"id": "info_proceso", "title": "Proceso de admisión"},
                            {"id": "info_precios", "title": "Precios"},
                            {"id": "info_extracurriculares", "title": "Extracurriculares"},
                            {"id": "info_descuentos", "title": "Descuentos disponibles"},
                            {"id": "info_inscripcion", "title": "Inscripción"},
                            {"id": "info_asesor", "title": "Contactar con un asesor"}
                        ]
                    }
                ]
            }
        }
    }
    enviar_payload(payload)


def extraer_mensaje(value):
    msg = value["messages"][0]

    if msg["type"] == "text":
        return msg["text"]["body"].strip(), "text"

    if msg["type"] == "interactive":
        interactive = msg["interactive"]

        if interactive["type"] == "button_reply":
            return interactive["button_reply"]["id"], "button"

        if interactive["type"] == "list_reply":
            return interactive["list_reply"]["id"], "list"

    return "", "unknown"


def extraer_datos_admision(mensaje):
    lineas = [linea.strip() for linea in mensaje.split("\n") if linea.strip()]

    if len(lineas) >= 4:
        nivel_codigo = lineas[3].strip()
        nivel = NIVELES.get(nivel_codigo, "No especificado")

        return {
            "representante": lineas[0],
            "correo": lineas[1],
            "telefono_contacto": lineas[2],
            "nivel": nivel,
            "nivel_codigo": nivel_codigo
        }

    return None


def enviar_respuesta_menu(telefono, opcion, asesor="", codigo=""):
    if opcion == "info_proceso":
        enviar_texto(
            telefono,
            "📌 *Proceso de admisión*\n\n"
            "1. Registro de datos del representante.\n"
            "2. Contacto por parte del equipo de admisiones.\n"
            "3. Revisión de disponibilidad según el nivel solicitado.\n"
            "4. Agendamiento de entrevista o visita institucional.\n"
            "5. Continuación del proceso de matrícula según los requisitos establecidos."
        )

    elif opcion == "info_precios":
        enviar_texto(
            telefono,
            "💰 *Precios*\n\n"
            "La información de valores puede variar según el nivel de estudio solicitado.\n\n"
            "Un asesor de admisiones le brindará la información actualizada y personalizada."
        )

    elif opcion == "info_extracurriculares":
        enviar_texto(
            telefono,
            "🎨 *Extracurriculares*\n\n"
            "Ecomundo cuenta con actividades orientadas al desarrollo integral de los estudiantes, "
            "incluyendo áreas deportivas, artísticas, tecnológicas y formativas.\n\n"
            "Un asesor podrá brindarle el detalle disponible según el nivel."
        )

    elif opcion == "info_descuentos":
        enviar_texto(
            telefono,
            "🏷️ *Descuentos disponibles*\n\n"
            "Los descuentos y beneficios dependen de las políticas institucionales vigentes, "
            "nivel de ingreso y condiciones aplicables.\n\n"
            "Un asesor de admisiones le brindará información personalizada."
        )

    elif opcion == "info_inscripcion":
        enviar_texto(
            telefono,
            "📝 *Inscripción*\n\n"
            "Puede continuar con el proceso de inscripción mediante el enlace o QR oficial que será proporcionado por el área de admisiones.\n\n"
            "Si ya cuenta con el enlace institucional, puede completarlo y un asesor dará seguimiento a su solicitud."
        )

    elif opcion == "info_asesor":
        enviar_texto(
            telefono,
            f"👩‍💼 *Contactar con un asesor*\n\n"
            f"Su solicitud ya fue registrada.\n\n"
            f"📋 Código de seguimiento: *{codigo}*\n"
            f"👩‍💼 Asesor asignado: *{asesor}*\n\n"
            "Uno de nuestros asesores se pondrá en contacto con usted en las próximas horas."
        )

    enviar_menu_consultas(telefono)


@app.route("/")
def home():
    return "Bot Admisiones Ecomundo"


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
        mensaje_original, tipo = extraer_mensaje(value)
        mensaje = mensaje_original.lower()

        print("TELÉFONO:", telefono)
        print("MENSAJE:", mensaje_original)

        if mensaje in ["hola", "inicio", "menu", "menú"]:
            USER_STATE[telefono] = {"estado": "inicio"}
            enviar_botones_privacidad(telefono)

        elif mensaje == "acepto_privacidad" or mensaje in ["a", "si", "sí", "acepto"]:
            USER_STATE[telefono] = {"estado": "esperando_datos"}
            enviar_texto(telefono, mensaje_solicitud_datos())

        elif mensaje == "no_acepto_privacidad" or mensaje in ["b", "no", "no acepto"]:
            USER_STATE[telefono] = {"estado": "finalizado"}
            enviar_texto(
                telefono,
                "Gracias por contactarnos.\n\n"
                "No podremos recopilar ni procesar información personal sin su consentimiento."
            )

        elif mensaje in [
            "info_proceso",
            "info_precios",
            "info_extracurriculares",
            "info_descuentos",
            "info_inscripcion",
            "info_asesor"
        ]:
            estado = USER_STATE.get(telefono, {})
            enviar_respuesta_menu(
                telefono,
                mensaje,
                asesor=estado.get("asesor", ""),
                codigo=estado.get("codigo", "")
            )

        else:
            estado_actual = USER_STATE.get(telefono, {}).get("estado")

            if estado_actual == "esperando_datos":
                datos = extraer_datos_admision(mensaje_original)

                if datos:
                    asesor = obtener_asesor()

                    codigo = guardar_en_sheets(
                        telefono,
                        datos["representante"],
                        "",
                        "",
                        datos["nivel"],
                        datos["correo"],
                        "Pendiente Contacto",
                        asesor
                    )

                    USER_STATE[telefono] = {
                        "estado": "menu_consultas",
                        "asesor": asesor,
                        "codigo": codigo,
                        "nivel": datos["nivel"]
                    }

                    enviar_texto(
                        telefono,
                        "✅ Información registrada correctamente.\n\n"
                        f"📋 Código de seguimiento:\n*{codigo}*\n\n"
                        f"👩‍💼 Asesor asignado:\n*{asesor}*\n\n"
                        "A continuación puede consultar información adicional sobre el proceso de admisión."
                    )

                    enviar_menu_consultas(telefono)

                else:
                    enviar_texto(
                        telefono,
                        "No logramos registrar la información.\n\n"
                        "Por favor envíe los datos en este orden:\n\n"
                        "Nombre del representante\n"
                        "Correo\n"
                        "Teléfono\n"
                        "Número del nivel de interés\n\n"
                        "Ejemplo:\n"
                        "María Pérez\n"
                        "correo@ejemplo.com\n"
                        "0999999999\n"
                        "15"
                    )

            else:
                enviar_texto(
                    telefono,
                    "Para iniciar el proceso de admisiones, escriba: *Hola*"
                )

    except Exception as e:
        print("ERROR EN WEBHOOK:", e)

    return "OK", 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
