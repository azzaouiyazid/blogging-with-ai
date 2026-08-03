from sqlalchemy import Column, Integer, String, Text, Date, Numeric
from sqlalchemy.orm import declarative_base


Base = declarative_base()


class Post(Base):  # type: ignore
    __tablename__ = 'Posts'
    id = Column(Integer, primary_key=True)
    title = Column('title', String(255))
    content = Column('content', Text)
    release = Column('release', Date)
    generated = Column('generated', Date)
    wordcount = Column('wordcount', Integer)
    costs_in_dollar = Column('costs_in_dollar', Numeric)
    platform = Column('platform', String(32), nullable=True)
    external_id = Column('external_id', String(128), nullable=True)
    url = Column('url', String(1024), nullable=True)
    status = Column('status', String(32), nullable=True)
