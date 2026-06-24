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
    "2": "Inicial 2 (3 años)",
    "3": "Inicial 2 (4 años)",
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
    numero = total_filas
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
    texto = "🎓 Seleccione el nivel de interés:\n\n"
    for numero, nivel in NIVELES.items():
        texto += f"{numero}. {nivel}\n"
    texto += "\nResponda únicamente con el número del nivel deseado."
    return texto


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
                "Nos alegra acompañarle en este proceso. Para brindarle una atención personalizada "
                "y gestionar adecuadamente su solicitud, le invitamos a revisar nuestra Política de "
                "Privacidad y Tratamiento de Datos Personales.\n\n"
                "Sus datos serán utilizados exclusivamente para atender consultas, brindar información "
                "institucional y realizar seguimiento al proceso de admisión, de conformidad con la "
                "Ley Orgánica de Protección de Datos Personales (LOPDP).\n\n"
                "¿Nos confirma su aceptación para continuar?\n\n"
                "✅ A. Sí, acepto.\n\n"
                "❌ B. No acepto.\n\n"
                "Por favor, responda únicamente con la letra A o B."
            )

        elif mensaje in ["a", "a.", "acepto", "si", "sí"]:
            respuesta = (
                "✅ Gracias por confirmar.\n\n"
                "Es un gusto atenderle.\n\n"
                "Por favor, seleccione una de las siguientes opciones:\n\n"
                "1️⃣ Información de admisiones\n\n"
                "2️⃣ Ya soy representante de Ecomundo\n\n"
                "3️⃣ Contactar a un asesor de admisiones\n\n"
                "4️⃣ Salir\n\n"
                "Responda únicamente con el número de la opción deseada."
            )

        elif mensaje in ["b", "b.", "no", "no acepto"]:
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
                "Por favor indique brevemente su requerimiento para derivarlo al área correspondiente."
            )

        elif mensaje == "3":
            respuesta = (
                "Con gusto le ayudaremos.\n\n"
                "Por favor envíe su nombre completo y un asesor de admisiones se comunicará con usted."
            )

        elif mensaje == "4":
            respuesta = (
                "Gracias por contactarse con Ecomundo Educación Particular Bilingüe.\n\n"
                "Estamos atentos para apoyarle cuando lo necesite."
            )

        elif mensaje in NIVELES:
            nivel = NIVELES[mensaje]
            respuesta = (
                f"Ha seleccionado: *{nivel}*.\n\n"
                "Para continuar con el proceso de admisión, envíe los siguientes datos "
                "en un solo mensaje, uno debajo del otro:\n\n"
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
                    "Un asesor de admisiones se comunicará con usted en breve.\n\n"
                    "Gracias por elegir Ecomundo."
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
