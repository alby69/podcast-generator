from typing import Optional
from sqlmodel import Field, SQLModel, create_engine, Session

class EpisodeDB(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    title: str
    url: str
    date: str
    audio_path: str
    script_path: str
    created_at: str

sqlite_file_name = "podcast.db"
sqlite_url = f"sqlite:///{sqlite_file_name}"

engine = create_engine(sqlite_url, echo=True)

def create_db_and_tables():
    SQLModel.metadata.create_all(engine)

def get_session():
    with Session(engine) as session:
        yield session
