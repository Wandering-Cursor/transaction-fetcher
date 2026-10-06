from fetcher.enums.account import AccountProvider
from fetcher.providers.account.abank import ABankProvider
from fetcher.providers.account.base import BaseAccountProvider
from fetcher.providers.account.monobank import MonoBankProvider
from fetcher.providers.account.novapay import NovaPayProvider
from fetcher.providers.account.privatbank_fop import PrivatBankFOPProvider


def get_provider_class(
    provider_name: AccountProvider,
) -> type[BaseAccountProvider]:
    return {
        AccountProvider.MONOBANK: MonoBankProvider,
        AccountProvider.ABANK: ABankProvider,
        AccountProvider.PRIVATBANK_FOP: PrivatBankFOPProvider,
        AccountProvider.NOVAPAY: NovaPayProvider,
    }[provider_name]
