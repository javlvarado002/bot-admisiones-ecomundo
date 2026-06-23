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

NIVELES = {
    "1": "Maternal",
    "2": "Inicial 2 - 3 años",
    "3": "Inicial 2 - 4 años",
    "4": "Primer grado de Educación General Preparatoria",
    "5": "Segundo grado de Educación General Básica",
    "6": "Tercer grado de Educación General Básica",
    "7": "Cuarto grado de Educación General Básica",
    "8": "Quinto grado de Educación General Básica",
    "9": "Sexto grado de Educación General Básica",
    "10": "Séptimo grado de Educación General Básica",
    "11": "Octavo grado de Educación General Básica",
    "12": "Noveno grado de Educación General Básica",
    "13": "Décimo grado de Educación General Básica",
    "14": "Primer año de Bachillerato",
    "15": "Segundo año de Bachillerato",
    "16": "Tercer año de Bachillerato"
}


def conectar_sheet():
    cred_dict = json.loads(GOOGLE_CREDENTIALS)
    credentials = Credentials.from_service_account_info(cred_dict, scopes=SCOPES)
    gc = gspread.authorize(credentials)
    return gc.open("Admisiones Ecomundo").sheet1


def generar_codigo_caso():
    sheet = conectar_sheet()
    total_filas = len(sheet.get_all_values())
    numero = total_filas - 1
    return f"ADM-2026-{numero:04d}"


def guardar_en_sheets(telefono, representante, estudiante, edad, nivel, correo):
    sheet = conectar_sheet()
    codigo = generar_codigo_caso()

    sheet.append_row([
        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        telefono,
        representante,
        estudiante,
        edad,
        nivel,
        correo,
        "Nuevo",
        codigo
    ])

    return codigo


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


def enviar_whatsapp(telefono, mensaje):
    url = f"https://graph.facebook.com/v23.0/{PHONE_NUMBER_ID}/messages"

    headers = {
        "Authorization": f"Bearer {WHATSAPP_TOKEN}",
        "Content-Type": "application/json"
    }

    payload = {
        "messaging_product": "whatsapp",
        "to": telefono,
        "type": "text",
        "text": {"body": mensaje}
    }

    response = requests.post(url, headers=headers, json=payload)

    print("RESPUESTA WHATSAPP:")
    print(response.status_code)
    print(response.text)


def menu_niveles():
    texto = "🎓 Para continuar, seleccione el nivel de interés:\n\n"
    for numero, nivel in NIVELES.items():
        texto += f"{numero}. {nivel}\n"
    texto += "\nResponda solo con el número del nivel."
    return texto


def detectar_nivel(mensaje):
    mensaje = mensaje.strip().lower()

    if mensaje in NIVELES:
        return NIVELES[mensaje]

    for nivel in NIVELES.values():
        if mensaje in nivel.lower():
            return nivel

    return None


def extraer_datos_sin_etiquetas(mensaje):
    lineas = [linea.strip() for linea in mensaje.split("\n") if linea.strip()]

    if len(lineas) >= 4:
        return {
            "representante": lineas[0],
            "estudiante": lineas[1],
            "edad": lineas[2],
            "correo": lineas[3]
        }

    return None


@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json()

    print("MENSAJE RECIBIDO:")
    print(data)

    try:
        value = data["entry"][0]["changes"][0]["value"]

        if "messages" not in value:
            return "OK", 200

        mensaje_original = value["messages"][0]["text"]["body"].strip()
        mensaje = mensaje_original.lower()
        telefono = value["messages"][0]["from"]

        print("TELÉFONO:", telefono)
        print("MENSAJE:", mensaje_original)

        if mensaje in ["hola", "buenas", "info", "informacion", "información"]:
            respuesta = (
                "👋 ¡Hola! Bienvenido/a a *Unidad Educación Particular Bilingüe Ecomundo*.\n\n"
                "Para poder atender su requerimiento por este canal, necesitamos que lea y acepte "
                "el tratamiento de sus datos personales para gestionar solicitudes de admisión, "
                "brindar información institucional y realizar seguimiento al proceso.\n\n"
                "¿Nos confirma su aceptación?\n\n"
                "1️⃣ Sí, acepto\n"
                "2️⃣ No acepto"
            )

        elif mensaje in ["1", "si", "sí", "acepto", "1️⃣"]:
            respuesta = (
                "✅ Gracias por confirmar.\n\n"
                "Para continuar con el proceso de admisión, por favor seleccione una opción:"
                "\n\n1. Quiero información de admisiones"
                "\n2. Ya soy representante"
                "\n3. Salir"
            )

        elif mensaje in ["2", "no", "no acepto", "2️⃣"]:
            respuesta = (
                "Gracias por contactarnos.\n\n"
                "No podremos recopilar ni procesar información personal sin su consentimiento."
            )

        elif mensaje in ["1.", "quiero información", "quiero informacion", "admisiones"]:
            respuesta = menu_niveles()

        elif mensaje in ["2.", "ya soy representante"]:
            respuesta = (
                "Gracias por escribirnos.\n\n"
                "Para consultas de representantes, por favor comuníquese con el área correspondiente "
                "o indique brevemente su requerimiento."
            )

        elif mensaje in ["3", "3.", "salir"]:
            respuesta = "Gracias por contactarse con Ecomundo. Estamos atentos para apoyarle."

        elif detectar_nivel(mensaje):
            nivel = detectar_nivel(mensaje)
            respuesta = (
                f"Excelente elección. 🎓\n\n"
                f"Ha seleccionado: *{nivel}*.\n\n"
                "Para continuar con el proceso de admisión, por favor envíe los siguientes datos "
                "en un solo mensaje, uno debajo del otro:\n\n"
                "Nombre del representante\n"
                "Nombre del estudiante\n"
                "Edad del estudiante\n"
                "Correo electrónico\n\n"
                "Ejemplo:\n"
                "María Pérez\n"
                "Juan Pérez\n"
                "10\n"
                "correo@ejemplo.com\n\n"
                f"Nivel seleccionado: {nivel}"
            )

        elif "nivel seleccionado:" in mensaje:
            partes = mensaje_original.split("Nivel seleccionado:")
            datos_texto = partes[0].strip()
            nivel = partes[1].strip() if len(partes) > 1 else ""

            datos = extraer_datos_sin_etiquetas(datos_texto)

            if datos and nivel:
                codigo = guardar_en_sheets(
                    telefono,
                    datos["representante"],
                    datos["estudiante"],
                    datos["edad"],
                    nivel,
                    datos["correo"]
                )

                respuesta = (
                    "✅ Información registrada correctamente.\n\n"
                    f"Su código de caso es: *{codigo}*.\n\n"
                    "Un asesor de admisiones se comunicará con usted en breve."
                )
            else:
                respuesta = (
                    "No logramos registrar la información.\n\n"
                    "Por favor envíe los datos en este orden:\n\n"
                    "Nombre del representante\n"
                    "Nombre del estudiante\n"
                    "Edad del estudiante\n"
                    "Correo electrónico\n"
                    "Nivel seleccionado: nivel"
                )

        else:
            respuesta = (
                "Para iniciar el proceso de admisiones, escriba: *Hola*"
            )

        enviar_whatsapp(telefono, respuesta)

    except Exception as e:
        print("ERROR EN WEBHOOK:")
        print(e)

    return "OK", 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
