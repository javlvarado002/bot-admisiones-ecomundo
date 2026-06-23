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
    "4": "Maternal",
    "5": "Inicial 2 (3 años)",
    "6": "Inicial 2 (4 años)",
    "7": "Primer grado de Educación General Preparatoria",
    "8": "Segundo grado de Educación General Básica",
    "9": "Tercer grado de Educación General Básica",
    "10": "Cuarto grado de Educación General Básica",
    "11": "Quinto grado de Educación General Básica",
    "12": "Sexto grado de Educación General Básica",
    "13": "Séptimo grado de Educación General Básica",
    "14": "Octavo grado de Educación General Básica",
    "15": "Noveno grado de Educación General Básica",
    "16": "Décimo grado de Educación General Básica",
    "17": "Primer año de Bachillerato",
    "18": "Segundo año de Bachillerato",
    "19": "Tercer año de Bachillerato"
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
    print("RESPUESTA WHATSAPP:", response.status_code, response.text)


def menu_niveles():
    return (
        "🎓 Excelente elección.\n\n"
        "Seleccione el nivel de interés:\n\n"
        "4. Maternal\n"
        "5. Inicial 2 (3 años)\n"
        "6. Inicial 2 (4 años)\n"
        "7. Primer grado de Educación General Preparatoria\n"
        "8. Segundo grado de Educación General Básica\n"
        "9. Tercer grado de Educación General Básica\n"
        "10. Cuarto grado de Educación General Básica\n"
        "11. Quinto grado de Educación General Básica\n"
        "12. Sexto grado de Educación General Básica\n"
        "13. Séptimo grado de Educación General Básica\n"
        "14. Octavo grado de Educación General Básica\n"
        "15. Noveno grado de Educación General Básica\n"
        "16. Décimo grado de Educación General Básica\n"
        "17. Primer año de Bachillerato\n"
        "18. Segundo año de Bachillerato\n"
        "19. Tercer año de Bachillerato\n\n"
        "Responda solo con el número del nivel."
    )


def extraer_datos(mensaje):
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
    print("MENSAJE RECIBIDO:", data)

    try:
        value = data["entry"][0]["changes"][0]["value"]

        if "messages" not in value:
            return "OK", 200

        mensaje_original = value["messages"][0]["text"]["body"].strip()
        mensaje = mensaje_original.lower()
        telefono = value["messages"][0]["from"]

        print("TELÉFONO:", telefono)
        print("MENSAJE:", mensaje_original)

        if mensaje in ["hola", "inicio", "menu", "menú"]:
            respuesta = (
                "👋 ¡Hola! Bienvenido/a a *Ecomundo Educación Particular Bilingüe*.\n\n"
                "Para poder atender su requerimiento por este canal, necesitamos que lea y acepte "
                "el tratamiento de sus datos personales para gestionar solicitudes de admisión, "
                "brindar información institucional y realizar seguimiento al proceso.\n\n"
                "¿Nos confirma su aceptación?\n\n"
                "Escriba:\n"
                "✅ ACEPTO\n"
                "❌ NO ACEPTO"
            )

        elif mensaje in ["acepto", "sí", "si"]:
            respuesta = (
                "✅ Gracias por confirmar.\n\n"
                "Para continuar, seleccione una opción:\n\n"
                "1. Quiero información de admisiones\n"
                "2. Ya soy representante\n"
                "3. Salir"
            )

        elif mensaje in ["no acepto", "no"]:
            respuesta = (
                "Gracias por contactarnos.\n\n"
                "No podremos recopilar ni procesar información personal sin su consentimiento."
            )

        elif mensaje == "1":
            respuesta = menu_niveles()

        elif mensaje == "2":
            respuesta = (
                "Gracias por escribirnos.\n\n"
                "Este canal está orientado al proceso de admisiones. "
                "Por favor indique brevemente su requerimiento para poder derivarlo al área correspondiente."
            )

        elif mensaje == "3":
            respuesta = "Gracias por contactarse con Ecomundo. Estamos atentos para apoyarle."

        elif mensaje in NIVELES:
            nivel = NIVELES[mensaje]
            respuesta = (
                f"Ha seleccionado: *{nivel}*.\n\n"
                "Para continuar con el proceso de admisión, envíe los siguientes datos en un solo mensaje, uno debajo del otro:\n\n"
                "Nombre del representante\n"
                "Nombre del estudiante\n"
                "Edad del estudiante\n"
                f"{nivel}\n"
                "Correo electrónico\n\n"
                "Ejemplo:\n"
                "María Pérez\n"
                "Juan Pérez\n"
                "10\n"
                f"{nivel}\n"
                "correo@ejemplo.com"
            )

        else:
            datos = extraer_datos(mensaje_original)

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
                    f"Su código de caso es: *{codigo}*.\n\n"
                    "Un asesor de admisiones se comunicará con usted en breve."
                )
            else:
                respuesta = (
                    "No logramos registrar la información.\n\n"
                    "Por favor escriba *Hola* para iniciar nuevamente."
                )

        enviar_whatsapp(telefono, respuesta)

    except Exception as e:
        print("ERROR EN WEBHOOK:", e)

    return "OK", 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
