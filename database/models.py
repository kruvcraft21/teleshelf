from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy import Integer, BigInteger, Text, ForeignKey, Index
from sqlalchemy.ext.asyncio import AsyncAttrs

class Base(AsyncAttrs, DeclarativeBase):
    pass

class UserChats(Base):
    __tablename__ = 'user_chats'

    user_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    chat_id : Mapped[int] = mapped_column(BigInteger, primary_key=True)

class Topic(Base):
    __tablename__ = 'topics'

    id: Mapped[int] = mapped_column(Integer, autoincrement=True, primary_key=True)
    chat_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    topic_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    title: Mapped[str] = mapped_column(Text)

    files: Mapped[list["File"]] = relationship(back_populates="topic", cascade="all, delete-orphan")

    __table_args__ = (
        Index("uniqe_chat_topic_id", "chat_id", "topic_id", unique=True),
    )

class File(Base):
    __tablename__ = 'files'

    id : Mapped[int] = mapped_column(Integer, autoincrement=True, primary_key=True)
    topic_id: Mapped[int] = mapped_column(Integer, ForeignKey('topics.id', ondelete='CASCADE'))
    tg_file_id: Mapped[str] = mapped_column(Text, nullable=False)
    caption: Mapped[str | None] = mapped_column(Text)

    topic: Mapped["Topic"] = relationship(back_populates="files")
    positions: Mapped[list["Position"]] = relationship(back_populates="file", cascade="all, delete-orphan")

class Position(Base):
    __tablename__ = 'positions'

    user_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    file_id: Mapped[int] = mapped_column(Integer, ForeignKey('files.id', ondelete='CASCADE'), primary_key=True)
    page: Mapped[int] = mapped_column(Integer)

    file: Mapped["File"] = relationship(back_populates="positions")