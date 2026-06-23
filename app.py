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
    credentials = Credentials.from_service_account_info(
        cred_dict,
        scopes=SCOPES
    )
    gc = gspread.authorize(credentials)
    return gc.open("Admisiones Ecomundo").sheet1


def guardar_en_sheets(telefono, nombre_representante, nombre_estudiante, edad, nivel, correo):
    sheet = conectar_sheet()
    sheet.append_row([
        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        telefono,
        nombre_representante,
        nombre_estudiante,
        edad,
        nivel,
        correo,
        "Nuevo"
    ])


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
                "De conformidad con la LOPDP, escriba:\n\n"
                "✅ ACEPTO\n"
                "para continuar.\n\n"
                "❌ NO ACEPTO\n"
                "para finalizar."
            )

        elif mensaje == "acepto":
            respuesta = (
                "Gracias por aceptar.\n\n"
                "Por favor envíenos los siguientes datos en un solo mensaje:\n\n"
                "Nombre representante:\n"
                "Nombre estudiante:\n"
                "Edad estudiante:\n"
                "Grado/Nivel:\n"
                "Correo:"
            )

        elif mensaje == "no acepto":
            respuesta = (
                "Gracias por contactarnos.\n\n"
                "No podremos recopilar ni procesar información personal sin su consentimiento."
            )

        elif "nombre representante" in mensaje and "nombre estudiante" in mensaje:
            lineas = mensaje_original.split("\n")
            datos = {}

            for linea in lineas:
                if ":" in linea:
                    clave, valor = linea.split(":", 1)
                    datos[clave.strip().lower()] = valor.strip()

            guardar_en_sheets(
                telefono,
                datos.get("nombre representante", ""),
                datos.get("nombre estudiante", ""),
                datos.get("edad estudiante", ""),
                datos.get("grado/nivel", ""),
                datos.get("correo", "")
            )

            respuesta = (
                "✅ Información registrada correctamente.\n\n"
                "Un asesor de admisiones se comunicará con usted en breve."
            )

        else:
            respuesta = (
                "Gracias. Hemos recibido su mensaje.\n\n"
                "Para iniciar el proceso de admisiones, escriba: Hola"
            )

        enviar_whatsapp(telefono, respuesta)

    except Exception as e:
        print("ERROR EN WEBHOOK:")
        print(e)

    return "OK", 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
