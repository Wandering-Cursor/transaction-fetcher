from enum import StrEnum


class AccountProvider(StrEnum):
    PRIVATBANK = "PrivatBank"
    PRIVATBANK_FOP = "PrivatBankFOP"
    MONOBANK = "MonoBank"
    ABANK = "ABank"
    NOVAPAY = "NovaPay"
