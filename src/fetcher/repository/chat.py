from typing import TYPE_CHECKING

from sqlalchemy.orm import Session, joinedload

from fetcher.enums.chat import ChatProvider
from fetcher.models.account_chat_model import AccountChatModel
from fetcher.models.chat import ChatModel

if TYPE_CHECKING:
    from sqlalchemy.engine import Engine

    from fetcher.schemas.chat import CreateChatSchema


class ChatRepository:
    def __init__(self, db: "Engine") -> None:
        self.db = db

    def create_chat(self, data: "CreateChatSchema") -> ChatModel:
        with Session(self.db) as session:
            existent_chat = (
                session.query(ChatModel)
                .filter(
                    ChatModel.external_id == data.external_id,
                    ChatModel.provider == data.provider,
                )
                .first()
            )
            if existent_chat:
                return existent_chat

            chat = ChatModel(
                name=data.name,
                provider=data.provider,
                external_id=data.external_id,
            )
            session.add(chat)
            session.commit()
            session.refresh(chat)

            return chat

    def get_chat_by_id(
        self,
        chat_id: int,
    ) -> ChatModel | None:
        with Session(self.db) as session:
            q = session.query(ChatModel).filter(
                ChatModel.id == chat_id,
            )
            return q.first()

    def get_chat_by_external_id(
        self,
        external_id: str,
        provider: ChatProvider | None = None,
    ) -> ChatModel | None:
        with Session(self.db) as session:
            q = session.query(ChatModel).filter(
                ChatModel.external_id == external_id,
            )

            if provider:
                q = q.filter(
                    ChatModel.provider == provider,
                )

            return q.first()

    def get_chats(
        self,
        page: int = 1,
        limit: int = 10,
        account_id: int | None = None,
        provider: ChatProvider | None = None,
        fetch_all: bool = False,
    ) -> list[ChatModel]:
        with Session(self.db) as session:
            q = session.query(ChatModel)

            if account_id is not None:
                q = (
                    session.query(ChatModel)
                    .join(
                        AccountChatModel,
                        AccountChatModel.chat_id == ChatModel.id,
                    )
                    .filter(
                        AccountChatModel.account_id == account_id,
                    )
                )

            if provider:
                q = q.filter(
                    ChatModel.provider == provider,
                )

            if fetch_all:
                return q.all()

            return (
                q.offset((page - 1) * limit)
                .limit(
                    limit,
                )
                .all()
            )

    def add_account_to_chat(
        self,
        chat_id: int,
        account_id: int,
    ) -> AccountChatModel:
        with Session(self.db) as session:
            account_chat = AccountChatModel(
                account_id=account_id,
                chat_id=chat_id,
            )
            session.add(account_chat)
            session.commit()
            session.refresh(account_chat)

            return account_chat

    def get_accounts_by_chat_id(
        self,
        chat_id: int,
    ) -> list[AccountChatModel]:
        with Session(self.db) as session:
            q = (
                session.query(AccountChatModel)
                .options(
                    joinedload(
                        AccountChatModel.account,
                    ),
                    joinedload(
                        AccountChatModel.chat,
                    ),
                )
                .filter(
                    AccountChatModel.chat_id == chat_id,
                )
            )

            return q.all()

    def get_account_chat_by_id(
        self,
        account_chat_id: int,
    ) -> AccountChatModel | None:
        with Session(self.db) as session:
            q = (
                session.query(AccountChatModel)
                .options(
                    joinedload(
                        AccountChatModel.account,
                    ),
                    joinedload(
                        AccountChatModel.chat,
                    ),
                )
                .filter(
                    AccountChatModel.id == account_chat_id,
                )
            )
            return q.first()

    def delete_account_chat(
        self,
        account_chat_id: int,
    ) -> None:
        with Session(self.db) as session:
            q = session.query(AccountChatModel).filter(
                AccountChatModel.id == account_chat_id,
            )
            q.delete()
            session.commit()
