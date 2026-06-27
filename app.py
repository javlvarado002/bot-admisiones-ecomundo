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
    "15": "Segundo de Bachillerato"
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
🔟 Séptimo Grado
1️⃣1️⃣ Octavo Grado
1️⃣2️⃣ Noveno Grado
1️⃣3️⃣ Décimo Grado
1️⃣4️⃣ Primero de Bachillerato
1️⃣5️⃣ Segundo de Bachillerato"""


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
        if str(asesor.get("Activo", "")).strip().lower() == "si":
            asignados = asesor.get("Asignados", 0) or 0
            activos.append({
                "fila": index,
                "nombre": asesor.get("Nombres", "Asesor asignado"),
                "whatsapp": str(asesor.get("WhatsApp", "")).strip(),
                "asignados": int(asignados)
            })

    if not activos:
        return "Sin asesor disponible", ""

    asesor = sorted(activos, key=lambda x: x["asignados"])[0]

    hoja_asesores.update_cell(
        asesor["fila"],
        5,
        asesor["asignados"] + 1
    )

    return asesor["nombre"], asesor["whatsapp"]


def generar_codigo_caso():
    sheet = conectar_sheet()
    total_filas = len(sheet.get_all_values())
    return f"ADM-2026-{total_filas:04d}"


def guardar_en_sheets(telefono_contacto, representante, nivel, correo, asesor):
    sheet = conectar_sheet()
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


def enviar_privacidad(telefono):
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
    return (
        "✅ ¡Gracias por confirmar!\n\n"
        "Para continuar con el proceso de admisión, envíe en un solo mensaje la siguiente información:\n\n"
        "👤 Nombre del representante\n"
        "📧 Correo electrónico\n"
        "📱 Teléfono de contacto\n"
        "🎓 Número del nivel de estudio de su interés\n\n"
        f"{NIVELES_TEXTO}\n\n"
        "📝 *Ejemplo:*\n\n"
        "María Pérez\n"
        "correo@ejemplo.com\n"
        "0999999999\n"
        "15"
    )


def mensaje_menu():
    return (
        "📚 ¿Qué información desea consultar?\n\n"
        "1️⃣ 📋 Proceso de admisión\n"
        "2️⃣ 💰 Precios\n"
        "3️⃣ ⚽ Actividades extracurriculares\n"
        "4️⃣ 🎁 Descuentos disponibles\n"
        "5️⃣ 📝 Inscripción\n"
        "6️⃣ 👩‍💼 Contactar con un asesor\n\n"
        "✍️ Escriba únicamente el número de la opción que desea consultar."
    )


def extraer_mensaje(value):
    msg = value["messages"][0]

    if msg["type"] == "text":
        return msg["text"]["body"].strip()

    if msg["type"] == "interactive":
        interactive = msg["interactive"]

        if interactive["type"] == "button_reply":
            return interactive["button_reply"]["id"]

        if interactive["type"] == "list_reply":
            return interactive["list_reply"]["id"]

    return ""


def extraer_datos_admision(mensaje):
    lineas = [linea.strip() for linea in mensaje.split("\n") if linea.strip()]

    if len(lineas) < 4:
        return None

    nivel_codigo = lineas[3]
    nivel = NIVELES.get(nivel_codigo)

    if not nivel:
        return None

    return {
        "representante": lineas[0],
        "correo": lineas[1],
        "telefono_contacto": lineas[2],
        "nivel": nivel
    }


def responder_opcion_menu(telefono, opcion):
    estado = USER_STATE.get(telefono, {})
    asesor = estado.get("asesor", "Asesor asignado")
    asesor_whatsapp = estado.get("asesor_whatsapp", "")
    codigo = estado.get("codigo", "")

    if opcion == "1":
        enviar_texto(
            telefono,
            "📋 *Proceso de admisión*\n\n"
            "Nuestro proceso inicia con el registro de datos del representante. "
            "Posteriormente, el equipo de admisiones tomará contacto para brindar información personalizada, "
            "validar disponibilidad del nivel de interés y orientar los siguientes pasos del proceso."
        )

    elif opcion == "2":
        enviar_texto(
            telefono,
            "💰 *Precios*\n\n"
            "Los valores pueden variar según el nivel de estudio solicitado. "
            "Un asesor de admisiones le compartirá la información actualizada y personalizada."
        )

    elif opcion == "3":
        enviar_texto(
            telefono,
            "⚽ *Actividades extracurriculares*\n\n"
            "Ecomundo cuenta con actividades orientadas al desarrollo integral de los estudiantes, "
            "incluyendo áreas deportivas, artísticas, tecnológicas y formativas."
        )

    elif opcion == "4":
        enviar_texto(
            telefono,
            "🎁 *Descuentos disponibles*\n\n"
            "Los descuentos y beneficios dependen de las políticas institucionales vigentes, "
            "el nivel de ingreso y las condiciones aplicables. "
            "Un asesor podrá brindarle mayor información."
        )

    elif opcion == "5":
        enviar_texto(
            telefono,
            "📝 *Inscripción*\n\n"
            "El área de admisiones le proporcionará el enlace o QR oficial para continuar con el proceso de inscripción."
        )

    elif opcion == "6":
        mensaje = (
            "👩‍💼 *Contactar con un asesor*\n\n"
            f"📋 Código de seguimiento: *{codigo}*\n"
            f"👩‍💼 Asesor asignado: *{asesor}*\n\n"
        )

        if asesor_whatsapp:
            numero = asesor_whatsapp.replace(" ", "")
            if numero.startswith("0"):
                numero = "593" + numero[1:]

            mensaje += (
                "Puede contactar directamente a su asesor en el siguiente enlace:\n"
                f"https://wa.me/{numero}?text=Hola,%20deseo%20información%20sobre%20mi%20proceso%20de%20admisión.%20Mi%20código%20es%20{codigo}"
            )
        else:
            mensaje += "Uno de nuestros asesores se pondrá en contacto con usted en las próximas horas."

        enviar_texto(telefono, mensaje)

    else:
        enviar_texto(telefono, "Por favor seleccione una opción válida del 1 al 6.")

    enviar_texto(telefono, "\n━━━━━━━━━━━━━━━━━━━━━━\n\n" + mensaje_menu())


@app.route("/")
def home():
    return "Bot Admisiones Ecomundo activo"


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
        mensaje_original = extraer_mensaje(value)
        mensaje = mensaje_original.lower().strip()

        print("TELÉFONO:", telefono)
        print("MENSAJE:", mensaje_original)

        if mensaje in ["hola", "inicio", "menu", "menú", "reiniciar", "reset"]:
            USER_STATE[telefono] = {"estado": "inicio"}
            enviar_privacidad(telefono)
            return "OK", 200

        if mensaje in ["acepto_privacidad", "a", "si", "sí", "acepto"]:
            USER_STATE[telefono] = {"estado": "esperando_datos"}
            enviar_texto(telefono, mensaje_solicitud_datos())
            return "OK", 200

        if mensaje in ["no_acepto_privacidad", "b", "no", "no acepto"]:
            USER_STATE[telefono] = {"estado": "finalizado"}
            enviar_texto(
                telefono,
                "Gracias por contactarnos.\n\n"
                "No podremos recopilar ni procesar información personal sin su consentimiento."
            )
            return "OK", 200

        estado_actual = USER_STATE.get(telefono, {}).get("estado")

        if estado_actual == "esperando_datos":
            datos = extraer_datos_admision(mensaje_original)

            if not datos:
                enviar_texto(
                    telefono,
                    "No logramos registrar la información.\n\n"
                    "Por favor envíe los datos en este orden:\n\n"
                    "👤 Nombre del representante\n"
                    "📧 Correo electrónico\n"
                    "📱 Teléfono de contacto\n"
                    "🎓 Número del nivel de interés\n\n"
                    "Ejemplo:\n"
                    "María Pérez\n"
                    "correo@ejemplo.com\n"
                    "0999999999\n"
                    "15"
                )
                return "OK", 200

            asesor, asesor_whatsapp = obtener_asesor()

            codigo = guardar_en_sheets(
                datos["telefono_contacto"],
                datos["representante"],
                datos["nivel"],
                datos["correo"],
                asesor
            )

            USER_STATE[telefono] = {
                "estado": "menu_consultas",
                "asesor": asesor,
                "asesor_whatsapp": asesor_whatsapp,
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

            enviar_texto(telefono, mensaje_menu())
            return "OK", 200

        if estado_actual == "menu_consultas":
            responder_opcion_menu(telefono, mensaje)
            return "OK", 200

        enviar_texto(telefono, "Para iniciar el proceso de admisiones, escriba: *Hola*")

    except Exception as e:
        print("ERROR EN WEBHOOK:", e)

    return "OK", 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
