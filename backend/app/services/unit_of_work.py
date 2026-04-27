from types import TracebackType
from typing import Literal

from sqlalchemy.orm import Session


class UnitOfWork:
    def __init__(self, session: Session) -> None:
        self.session = session

    def __enter__(self) -> "UnitOfWork":
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> Literal[False]:
        if exc_type is not None:
            self.session.rollback()
            return False

        try:
            self.session.commit()
        except Exception:
            self.session.rollback()
            raise

        return False

    def refresh(self, instance: object) -> None:
        self.session.refresh(instance)
