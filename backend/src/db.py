import os
from sqlalchemy import create_engine, Column, Integer, String, LargeBinary
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import dotenv
dotenv.load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL","sqlite:///./test.db")
print(DATABASE_URL)

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    password = Column(String)

class ImageKey(Base):
    __tablename__ = "image_keys"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String)
    image_key = Column(String, unique=True)
    encrypted_key = Column(LargeBinary)

Base.metadata.create_all(bind=engine)
