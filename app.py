
import os
import requests
from flask import Flask, request

app = Flask(__name__)

VERIFY_TOKEN = "ecomundo2026"

WHATSAPP_TOKEN = os.environ.get("EAAbIZAZCC9l7kBRhKYZB0cZB5etDRsbL1NwSZAX2DJkzmEZCXr4tZCgvNLWLGzIaD8J89H25ZAcv6RGVC0GmbAZB0Uj8xFVt8jTaOCkxM3wvXPgCdYcpp7FZCeyNX8J5hfK91J6DaB5FDJx1155tTdNJWIRaGcEXInCOFbcpG6RgaxfWA7uenGylBKEOg7Y15irOJhvW4EJpBUTj3GCq96tk4aPZC98d1HZAWkWxeqzyZBhMHY2giU0wKkUZAZARomZCZB5nVyZCs3nZBMawR97uRTB2Iqw8bHwbZA6D")
PHONE_NUMBER_ID = os.environ.get("1165732796623545")


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
    url = f"https://graph.facebook.com/v25.0/{PHONE_NUMBER_ID}/messages"

    headers = {
        "Authorization": f"Bearer {WHATSAPP_TOKEN}",
        "Content-Type": "application/json"
    }

    data = {
        "messaging_product": "whatsapp",
        "to": telefono,
        "type": "text",
        "text": {
            "body": mensaje
        }
    }

    response = requests.post(url, headers=headers, json=data)
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

        mensaje = value["messages"][0]["text"]["body"].strip().lower()
        telefono = value["messages"][0]["from"]

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

        else:
            respuesta = (
                "Gracias. Hemos recibido su mensaje.\n\n"
                "Un asesor de admisiones revisará la información y se comunicará con usted."
            )

        enviar_whatsapp(telefono, respuesta)

    except Exception as e:
        print("ERROR:")
        print(e)

    return "OK", 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
