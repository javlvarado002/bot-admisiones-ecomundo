import os
import requests
import gspread

from flask import Flask, request
from google.oauth2.service_account import Credentials
from datetime import datetime

app = Flask(__name__)

VERIFY_TOKEN = "ecomundo2026"

WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN")
PHONE_NUMBER_ID = os.getenv("PHONE_NUMBER_ID")
GOOGLE_SHEET_ID = os.getenv("GOOGLE_SHEET_ID")

# ==================================================
# GOOGLE SHEETS
# ==================================================

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

creds = Credentials.from_service_account_file(
    "credenciales.json",
    scopes=SCOPES
)

client = gspread.authorize(creds)

sheet = client.open_by_key(GOOGLE_SHEET_ID).sheet1


# ==================================================
# ENVIAR WHATSAPP
# ==================================================

def enviar_whatsapp(numero, mensaje):

    url = f"https://graph.facebook.com/v23.0/{PHONE_NUMBER_ID}/messages"

    headers = {
        "Authorization": f"Bearer {WHATSAPP_TOKEN}",
        "Content-Type": "application/json"
    }

    payload = {
        "messaging_product": "whatsapp",
        "to": numero,
        "type": "text",
        "text": {
            "body": mensaje
        }
    }

    requests.post(url, headers=headers, json=payload)


# ==================================================
# GUARDAR EN SHEETS
# ==================================================

def guardar_admision(
    telefono,
    representante,
    estudiante,
    edad,
    nivel,
    correo
):

    fecha = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    sheet.append_row([
        fecha,
        telefono,
        representante,
        estudiante,
        edad,
        nivel,
        correo,
        "Nuevo"
    ])


# ==================================================
# HOME
# ==================================================

@app.route("/")
def home():
    return "Bot Admisiones Ecomundo"


# ==================================================
# VERIFICACION META
# ==================================================

@app.route("/webhook", methods=["GET"])
def verify():

    mode = request.args.get("hub.mode")
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")

    if mode == "subscribe" and token == VERIFY_TOKEN:
        return challenge, 200

    return "Error", 403


# ==================================================
# WEBHOOK
# ==================================================

@app.route("/webhook", methods=["POST"])
def webhook():

    data = request.get_json()

    try:

        value = data["entry"][0]["changes"][0]["value"]

        if "messages" not in value:
            return "OK", 200

        telefono = value["messages"][0]["from"]
        mensaje = value["messages"][0]["text"]["body"].strip()

        mensaje_lower = mensaje.lower()

        print("MENSAJE:", mensaje)

        # ==========================================
        # INICIO
        # ==========================================

        if mensaje_lower in [
            "hola",
            "inicio",
            "menu",
            "menú"
        ]:

            respuesta = (
                    "👋 Bienvenido/a a *Unidad Educación Particular Bilingüe Ecomundo*.\n\n"
                "Para brindarle una atención personalizada necesitamos su consentimiento para el tratamiento de datos personales conforme a la LOPDP.\n\n"
                "Por favor responda:\n\n"
                "✅ ACEPTO\n"
                "❌ NO ACEPTO"
            )

        # ==========================================
        # ACEPTA
        # ==========================================

        elif mensaje_lower in [
            "acepto",
            "si",
            "sí"
        ]:

            respuesta = (
                "✅ Gracias por confirmar.\n\n"
                "Seleccione una opción:\n\n"
                "1. Quiero información de admisiones\n"
                "2. Ya soy representante\n"
                "3. Salir"
            )

        # ==========================================
        # OPCION 1
        # ==========================================

        elif mensaje_lower == "1":

            respuesta = (
                "📚 Información de Admisiones\n\n"
                "Seleccione el nivel de interés:\n\n"
                "1. Maternal\n"
                "2. Inicial 2 (3 años)\n"
                "3. Inicial 2 (4 años)\n"
                "4. Primero EGB\n"
                "5. Segundo EGB\n"
                "6. Tercero EGB\n"
                "7. Cuarto EGB\n"
                "8. Quinto EGB\n"
                "9. Sexto EGB\n"
                "10. Séptimo EGB\n"
                "11. Octavo EGB\n"
                "12. Noveno EGB\n"
                "13. Décimo EGB\n"
                "14. Primero BGU\n"
                "15. Segundo BGU\n"
                "16. Tercero BGU"
            )

        # ==========================================
        # OPCION 2
        # ==========================================

        elif mensaje_lower == "2":

            respuesta = (
                "Gracias por contactarnos.\n\n"
                "Un asesor institucional se comunicará con usted en breve."
            )

        # ==========================================
        # NIVELES
        # ==========================================

        elif mensaje_lower in [
            "maternal",
            "inicial",
            "primero",
            "segundo",
            "tercero",
            "cuarto",
            "quinto",
            "sexto",
            "séptimo",
            "septimo",
            "octavo",
            "noveno",
            "décimo",
            "decimo",
            "bgu",
            "3",
            "4",
            "5",
            "6",
            "7",
            "8",
            "9",
            "10",
            "11",
            "12",
            "13",
            "14",
            "15",
            "16"
        ]:

            respuesta = (
                "Excelente elección. 🎓\n\n"
                "Para continuar envíe en un solo mensaje:\n\n"
                "Nombre representante\n"
                "Nombre estudiante\n"
                "Edad\n"
                "Nivel\n"
                "Correo"
            )

        # ==========================================
        # GUARDAR DATOS
        # ==========================================

        else:

            lineas = mensaje.split("\n")

            if len(lineas) >= 5:

                representante = lineas[0].strip()
                estudiante = lineas[1].strip()
                edad = lineas[2].strip()
                nivel = lineas[3].strip()
                correo = lineas[4].strip()

                guardar_admision(
                    telefono,
                    representante,
                    estudiante,
                    edad,
                    nivel,
                    correo
                )

                respuesta = (
                    "✅ Hemos registrado correctamente su solicitud.\n\n"
                    "Un asesor de admisiones se comunicará con usted en las próximas horas.\n\n"
                    "Gracias por elegir Ecomundo."
                )

            else:

                respuesta = (
                    "No comprendí su mensaje.\n\n"
                    "Escriba *Hola* para iniciar nuevamente."
                )

        enviar_whatsapp(telefono, respuesta)

    except Exception as e:
        print("ERROR:", e)

    return "OK", 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
