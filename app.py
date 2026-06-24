
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

NIVELES = {
    "maternal": "Maternal",
    "ini3": "Inicial 2 (3 años)",
    "ini4": "Inicial 2 (4 años)",
    "primero": "Primer grado de Educación General Preparatoria",
    "segundo": "Segundo grado de Educación General Básica",
    "tercero": "Tercer grado de Educación General Básica",
    "cuarto": "Cuarto grado de Educación General Básica",
    "quinto": "Quinto grado de Educación General Básica",
    "sexto": "Sexto grado de Educación General Básica",
    "septimo": "Séptimo grado de Educación General Básica",
    "octavo": "Octavo grado de Educación General Básica",
    "noveno": "Noveno grado de Educación General Básica",
    "decimo": "Décimo grado de Educación General Básica",
    "bgu1": "Primer año de Bachillerato",
    "bgu2": "Segundo año de Bachillerato",
    "bgu3": "Tercer año de Bachillerato"
}


def conectar_sheet():
    cred_dict = json.loads(GOOGLE_CREDENTIALS)
    credentials = Credentials.from_service_account_info(cred_dict, scopes=SCOPES)
    gc = gspread.authorize(credentials)
    return gc.open("Admisiones Ecomundo").sheet1


def generar_codigo_caso():
    sheet = conectar_sheet()
    total_filas = len(sheet.get_all_values())
    return f"ADM-2026-{total_filas:04d}"


def guardar_en_sheets(telefono, representante, estudiante, edad, nivel, correo, estado, asesor=""):
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
                    "👋 ¡Hola! Bienvenido/a a *Ecomundo Educación Particular Bilingüe*.\n\n"
                    "Para poder atender su requerimiento por este canal, necesitamos que lea y acepte "
                    "nuestra Política de Privacidad y Tratamiento de Datos Personales.\n\n"
                    "¿Nos confirma su aceptación para brindarle una atención personalizada?"
                )
            },
            "action": {
                "buttons": [
                    {
                        "type": "reply",
                        "reply": {"id": "acepto_privacidad", "title": "✅ Sí"}
                    },
                    {
                        "type": "reply",
                        "reply": {"id": "no_acepto_privacidad", "title": "❌ No"}
                    }
                ]
            }
        }
    }
    enviar_payload(payload)


def enviar_menu_principal(telefono):
    payload = {
        "messaging_product": "whatsapp",
        "to": telefono,
        "type": "interactive",
        "interactive": {
            "type": "button",
            "body": {
                "text": (
                    "✅ ¡Gracias por confirmar!\n\n"
                    "Para continuar, por favor seleccione una de las siguientes opciones:"
                )
            },
            "action": {
                "buttons": [
                    {
                        "type": "reply",
                        "reply": {"id": "menu_admisiones", "title": "🎓 Admisiones"}
                    },
                    {
                        "type": "reply",
                        "reply": {"id": "menu_representante", "title": "👨‍👩‍👧 Representante"}
                    },
                    {
                        "type": "reply",
                        "reply": {"id": "menu_asesor", "title": "👩‍💼 Asesor"}
                    }
                ]
            }
        }
    }
    enviar_payload(payload)


def enviar_lista_grupos_nivel(telefono):
    payload = {
        "messaging_product": "whatsapp",
        "to": telefono,
        "type": "interactive",
        "interactive": {
            "type": "list",
            "body": {
                "text": (
                    "🎓 ¡Excelente elección!\n\n"
                    "Ser parte de Ecomundo Educación Particular Bilingüe permite acceder a una "
                    "formación integral, bilingüe y orientada al desarrollo académico y personal.\n\n"
                    "Seleccione el grupo de nivel que desea consultar:"
                )
            },
            "action": {
                "button": "Ver niveles",
                "sections": [
                    {
                        "title": "Niveles disponibles",
                        "rows": [
                            {"id": "grupo_inicial", "title": "Maternal e Inicial"},
                            {"id": "grupo_egb", "title": "Educación General Básica"},
                            {"id": "grupo_bgu", "title": "Bachillerato"}
                        ]
                    }
                ]
            }
        }
    }
    enviar_payload(payload)


def enviar_lista_inicial(telefono):
    enviar_lista_niveles(telefono, "Maternal e Inicial", [
        ("maternal", "Maternal"),
        ("ini3", "Inicial 2 (3 años)"),
        ("ini4", "Inicial 2 (4 años)")
    ])


def enviar_lista_egb(telefono):
    enviar_lista_niveles(telefono, "Educación General Básica", [
        ("primero", "Primero EGB"),
        ("segundo", "Segundo EGB"),
        ("tercero", "Tercero EGB"),
        ("cuarto", "Cuarto EGB"),
        ("quinto", "Quinto EGB"),
        ("sexto", "Sexto EGB"),
        ("septimo", "Séptimo EGB"),
        ("octavo", "Octavo EGB"),
        ("noveno", "Noveno EGB"),
        ("decimo", "Décimo EGB")
    ])


def enviar_lista_bgu(telefono):
    enviar_lista_niveles(telefono, "Bachillerato", [
        ("bgu1", "Primero BGU"),
        ("bgu2", "Segundo BGU"),
        ("bgu3", "Tercero BGU")
    ])


def enviar_lista_niveles(telefono, titulo, filas):
    payload = {
        "messaging_product": "whatsapp",
        "to": telefono,
        "type": "interactive",
        "interactive": {
            "type": "list",
            "body": {"text": f"Seleccione el nivel de interés en *{titulo}*:"},
            "action": {
                "button": "Seleccionar",
                "sections": [
                    {
                        "title": titulo,
                        "rows": [
                            {"id": f"nivel_{id_nivel}", "title": nombre}
                            for id_nivel, nombre in filas
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
        return {
            "representante": lineas[0],
            "estudiante": lineas[1],
            "edad": lineas[2],
            "correo": lineas[3]
        }

    return None


def extraer_datos_asesor(mensaje):
    lineas = [linea.strip() for linea in mensaje.split("\n") if linea.strip()]

    if len(lineas) >= 3:
        return {
            "nombre": lineas[0],
            "contacto": lineas[1],
            "nivel": lineas[2]
        }

    return None


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
            USER_STATE[telefono] = {"estado": "menu"}
            enviar_menu_principal(telefono)

        elif mensaje == "no_acepto_privacidad" or mensaje in ["b", "no", "no acepto"]:
            enviar_texto(
                telefono,
                "Gracias por contactarnos.\n\n"
                "No podremos recopilar ni procesar información personal sin su consentimiento."
            )

        elif mensaje == "menu_admisiones":
            USER_STATE[telefono] = {"estado": "seleccion_grupo"}
            enviar_lista_grupos_nivel(telefono)

        elif mensaje == "menu_representante":
            enviar_texto(
                telefono,
                "Gracias por escribirnos.\n\n"
                "Este canal está orientado al proceso de admisiones. "
                "Por favor indique brevemente su requerimiento para derivarlo al área correspondiente."
            )

        elif mensaje == "menu_asesor":
            USER_STATE[telefono] = {"estado": "esperando_asesor"}
            enviar_texto(
                telefono,
                "👩‍💼 Atención personalizada\n\n"
                "Para que uno de nuestros asesores pueda atenderle, por favor envíe en un solo mensaje:\n\n"
                "Nombre completo\n"
                "Número de contacto\n"
                "Nivel de interés\n\n"
                "Ejemplo:\n"
                "Victoria Méndez\n"
                "0999999999\n"
                "Octavo EGB"
            )

        elif mensaje == "grupo_inicial":
            enviar_lista_inicial(telefono)

        elif mensaje == "grupo_egb":
            enviar_lista_egb(telefono)

        elif mensaje == "grupo_bgu":
            enviar_lista_bgu(telefono)

        elif mensaje.startswith("nivel_"):
            id_nivel = mensaje.replace("nivel_", "")
            nivel = NIVELES.get(id_nivel, "No especificado")

            USER_STATE[telefono] = {
                "estado": "esperando_datos_admision",
                "nivel": nivel
            }

            enviar_texto(
                telefono,
                f"Ha seleccionado: *{nivel}*.\n\n"
                "Para continuar con el proceso de admisión, envíe los siguientes datos en un solo mensaje:\n\n"
                "Nombre del representante\n"
                "Nombre del estudiante\n"
                "Edad del estudiante\n"
                "Correo electrónico\n\n"
                "Ejemplo:\n"
                "María Pérez\n"
                "Juan Pérez\n"
                "10\n"
                "correo@ejemplo.com"
            )

        else:
            estado_actual = USER_STATE.get(telefono, {}).get("estado")

            if estado_actual == "esperando_datos_admision":
                datos = extraer_datos_admision(mensaje_original)
                nivel = USER_STATE.get(telefono, {}).get("nivel", "")

                if datos:
                    codigo = guardar_en_sheets(
                        telefono,
                        datos["representante"],
                        datos["estudiante"],
                        datos["edad"],
                        nivel,
                        datos["correo"],
                        "Nuevo",
                        ""
                    )

                    enviar_texto(
                        telefono,
                        "✅ Información registrada correctamente.\n\n"
                        f"Su código de caso es: *{codigo}*.\n\n"
                        "Un asesor de admisiones se comunicará con usted en breve.\n\n"
                        "Gracias por elegir Ecomundo."
                    )

                    USER_STATE[telefono] = {"estado": "finalizado"}

                else:
                    enviar_texto(
                        telefono,
                        "No logramos registrar la información.\n\n"
                        "Por favor envíe los datos en este orden:\n\n"
                        "Nombre del representante\n"
                        "Nombre del estudiante\n"
                        "Edad del estudiante\n"
                        "Correo electrónico"
                    )

            elif estado_actual == "esperando_asesor":
                datos = extraer_datos_asesor(mensaje_original)

                if datos:
                    codigo = guardar_en_sheets(
                        telefono,
                        datos["nombre"],
                        "",
                        "",
                        datos["nivel"],
                        "",
                        "Pendiente Asesor",
                        "Por asignar"
                    )

                    enviar_texto(
                        telefono,
                        "✅ Su solicitud ha sido registrada correctamente.\n\n"
                        f"Su código de caso es: *{codigo}*.\n\n"
                        "Uno de nuestros asesores de admisiones se comunicará con usted en breve "
                        "para brindarle atención personalizada."
                    )

                    USER_STATE[telefono] = {"estado": "finalizado"}

                else:
                    enviar_texto(
                        telefono,
                        "Por favor envíe los datos en este orden:\n\n"
                        "Nombre completo\n"
                        "Número de contacto\n"
                        "Nivel de interés"
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
