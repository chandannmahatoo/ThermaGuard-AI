from sqlalchemy import create_engine, String, JSON, ForeignKey, UniqueConstraint, event
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker
from .config import settings

class Base(DeclarativeBase): pass
class User(Base):
    __tablename__ = 'users'
    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String, unique=True)
    password: Mapped[str]
    role: Mapped[str] = mapped_column(default='organization')
    organization_id: Mapped[int | None] = mapped_column(ForeignKey('organizations.id'))
class Organization(Base):
    __tablename__ = 'organizations'
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str]
    email: Mapped[str]
class AreaAssignment(Base):
    __tablename__ = 'assignments'
    id: Mapped[int] = mapped_column(primary_key=True)
    organization_id: Mapped[int] = mapped_column(ForeignKey('organizations.id'))
    area_name: Mapped[str]
    bounds: Mapped[list] = mapped_column(JSON)
    minimum_alert_level: Mapped[str] = mapped_column(default='High')
class Detection(Base):
    __tablename__ = 'detections'
    id: Mapped[str] = mapped_column(primary_key=True)
    is_demo: Mapped[bool]
    payload: Mapped[dict] = mapped_column(JSON)
class Event(Base):
    __tablename__ = 'events'
    id: Mapped[str] = mapped_column(primary_key=True)
    is_demo: Mapped[bool]
    payload: Mapped[dict] = mapped_column(JSON)
class Alert(Base):
    __tablename__ = 'alerts'
    __table_args__ = (UniqueConstraint('event_id', 'organization_id'),)
    id: Mapped[int] = mapped_column(primary_key=True)
    event_id: Mapped[str] = mapped_column(ForeignKey('events.id'))
    organization_id: Mapped[int] = mapped_column(ForeignKey('organizations.id'))
    risk_level: Mapped[str]
    created_at: Mapped[str]
    status: Mapped[str] = mapped_column(default='open')
    notification_status: Mapped[str] = mapped_column(default='dashboard_delivered; email_unconfigured')

engine = create_engine(settings.database_url, connect_args={'check_same_thread': False} if settings.database_url.startswith('sqlite') else {})
if settings.database_url.startswith('sqlite'):
    @event.listens_for(engine, 'connect')
    def enable_foreign_keys(connection, _):
        connection.execute('PRAGMA foreign_keys=ON')
Session = sessionmaker(engine, expire_on_commit=False)
def get_db():
    with Session() as db: yield db

class RuntimeSetting(Base):
    __tablename__ = 'runtime_settings'
    key: Mapped[str] = mapped_column(primary_key=True)
    value: Mapped[dict] = mapped_column(JSON)
