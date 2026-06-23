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


def extraer_datos_con_etiquetas(mensaje):
    datos = {}

    for linea in mensaje.split("\n"):
        if ":" in linea:
            clave, valor = linea.split(":", 1)
            datos[clave.strip().lower()] = valor.strip()

    return {
        "representante": datos.get("nombre representante", ""),
        "estudiante": datos.get("nombre estudiante", ""),
        "edad": datos.get("edad estudiante", ""),
        "nivel": datos.get("grado/nivel", ""),
        "correo": datos.get("correo", "")
    }


def extraer_datos_sin_etiquetas(mensaje):
    lineas = [linea.strip() for linea in mensaje.split("\n") if linea.strip()]

    if len(lineas) >= 5:
        return {
            "representante": lineas[0],
            "estudiante": lineas[1],
            "edad": lineas[2],
            "nivel": lineas[3],
            "correo": lineas[4]
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
                "👋 Bienvenido/a a Admisiones Ecomundo.\n\n"
                "Antes de continuar, le informamos que los datos personales proporcionados "
                "serán tratados con la finalidad de gestionar solicitudes de admisión, "
                "brindar información institucional y realizar seguimiento al proceso.\n\n"
                "De conformidad con la LOPDP, escriba una opción:\n\n"
                "1️⃣ ACEPTO\n"
                "2️⃣ NO ACEPTO"
            )

        elif mensaje in ["acepto", "1", "1️⃣"]:
            respuesta = (
                "Gracias por aceptar.\n\n"
                "Por favor envíenos los siguientes datos en un solo mensaje, uno debajo del otro:\n\n"
                "Nombre del representante\n"
                "Nombre del estudiante\n"
                "Edad del estudiante\n"
                "Grado o nivel de interés\n"
                "Correo electrónico\n\n"
                "Ejemplo:\n"
                "María Pérez\n"
                "Juan Pérez\n"
                "10\n"
                "5to EGB\n"
                "correo@ejemplo.com"
            )

        elif mensaje in ["no acepto", "2", "2️⃣"]:
            respuesta = (
                "Gracias por contactarnos.\n\n"
                "No podremos recopilar ni procesar información personal sin su consentimiento."
            )

        else:
            datos = None

            if "nombre representante" in mensaje and "nombre estudiante" in mensaje:
                datos = extraer_datos_con_etiquetas(mensaje_original)
            else:
                datos = extraer_datos_sin_etiquetas(mensaje_original)

            if datos:
                codigo = guardar_en_sheets(
                    telefono,
                    datos["representante"],
                    datos["estudiante"],
                    datos["edad"],
                    datos["nivel"],
                    datos["correo"]
                )

                respuesta = (
                    "✅ Información registrada correctamente.\n\n"
                    f"Su código de caso es: {codigo}\n\n"
                    "Un asesor de admisiones se comunicará con usted en breve."
                )
            else:
                respuesta = (
                    "No logramos registrar la información.\n\n"
                    "Por favor envíe los datos en este orden:\n\n"
                    "Nombre del representante\n"
                    "Nombre del estudiante\n"
                    "Edad del estudiante\n"
                    "Grado o nivel de interés\n"
                    "Correo electrónico"
                )

        enviar_whatsapp(telefono, respuesta)

    except Exception as e:
        print("ERROR EN WEBHOOK:")
        print(e)

    return "OK", 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
