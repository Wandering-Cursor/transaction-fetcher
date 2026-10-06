# ruff: noqa: T201
from uuid import uuid4

from zeep import Client

client = Client("https://business.novapay.ua/Services/ClientAPIService.svc?wsdl")


login = input("Enter login: ")
refresh_token = input("Enter refresh token: ")
public_certificate = input(
    "Enter public certificate (should end with -----END RSA PUBLIC KEY-----): "
)

while True:
    if not public_certificate.endswith("-----END RSA PUBLIC KEY-----"):
        public_certificate += input("next line: ").replace("\n", "")
    else:
        break

response = client.service.UserAuthenticationJWT(
    {
        "request_ref": str(uuid4()),
        "refresh_token": refresh_token,
        "login": login,
        "public_certificate": public_certificate,
    }
)

print("JWT: ", response["jwt"])
print("Expiration: ", response["expiration"])
print("New refresh token: ", response["refresh_token"])
print("New public certificate: ", response["public_certificate"])
