import json
import uuid

import requests
import rsa


def calculate_signature(body: dict) -> tuple[str, bytes]:
    post_body = json.dumps(body, separators=(",", ":")).encode("utf-8")

    with open("privatekey.pem", "rb") as key_file:
        private_key = rsa.PrivateKey.load_pkcs1(key_file.read())

    return rsa.sign(post_body, private_key, "SHA-1").hex(), post_body


body = {
    "request_ref": str(uuid.uuid4()),
    "phone": "PHONE-NUMBER",
    "client_id": "CLIENT-ID",
    "callback_url": "https://your-callback-address.com/",
}

signature, body = calculate_signature(body)

response = requests.post(
    url="https://open-api.a-bank.com.ua/legal-entity/link/get",
    data=body.decode("utf-8"),
    headers={
        "signature": signature,
        "system": "SYSTEM (UUID4)",
        "Content-Type": "application/json",
    },
)

print(response.status_code)  # noqa: T201
print(response.content)  # noqa: T201
