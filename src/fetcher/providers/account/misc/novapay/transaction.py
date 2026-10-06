from uuid import uuid4

from zeep import Client

client = Client("https://business.novapay.ua/Services/ClientAPIService.svc?wsdl")

jwt_token = input("Enter JWT token: ")

result = client.service.GetPaymentsList(
    {
        "request_ref": str(uuid4()),
        "jwt": jwt_token,
    }
)

print(result)
