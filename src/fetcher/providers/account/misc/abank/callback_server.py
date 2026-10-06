import requests
from flask import Flask, request

app = Flask(__name__)


@app.route("/", methods=["GET", "POST"])
def index() -> str:
    requests.post(
        "https://api.telegram.org/BOT-TOKEN/sendMessage",
        data={
            "chat_id": "CHAT-ID",
            "text": request.data.decode("utf-8"),
        },
    )
    return "ok"


app.run(host="0.0.0.0", port=5000)
