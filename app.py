from flask import Flask, request

app = Flask(__name__)

VERIFY_TOKEN = "ecomundo2026"

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

    print("MENSAJE RECIBIDO:")
    print(data)

    return "OK", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
