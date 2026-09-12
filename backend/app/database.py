from sqlalchemy import create_engine, String, JSON, ForeignKey, UniqueConstraint, event, inspect, text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker
from .config import settings

class Base(DeclarativeBase): pass
class User(Base):
    __tablename__ = 'users'
    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String, unique=True)
    password: Mapped[str]
    latitude: Mapped[float | None]
    longitude: Mapped[float | None]
    alert_radius_km: Mapped[float | None]
    notifications_enabled: Mapped[bool] = mapped_column(default=False, server_default='0')
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

def make_engine(url):
    sqlite = url.startswith('sqlite')
    result = create_engine(url, connect_args={'check_same_thread': False, 'timeout': 30} if sqlite else {})
    if sqlite:
        @event.listens_for(result, 'connect')
        def configure_sqlite(connection, _):
            connection.execute('PRAGMA busy_timeout=30000')
            connection.execute('PRAGMA foreign_keys=ON')
            connection.execute('PRAGMA journal_mode=WAL')
            # Retain SQLite's FULL durability; no synchronous=NORMAL tradeoff.
    return result


engine = make_engine(settings.database_url)
Session = sessionmaker(engine, expire_on_commit=False)


def get_db():
    with Session() as db:
        try:
            yield db
        except BaseException:
            db.rollback()
            db.info.pop('pending_notifications', None)
            raise

class RuntimeSetting(Base):
    __tablename__ = 'runtime_settings'
    key: Mapped[str] = mapped_column(primary_key=True)
    value: Mapped[dict] = mapped_column(JSON)


class EmailNotification(Base):
    __tablename__ = 'email_notifications'
    __table_args__ = (UniqueConstraint('event_id','user_id','risk_level','channel'),)
    id: Mapped[int] = mapped_column(primary_key=True)
    # Immutable event snapshot survives later reclustering; no cascading event FK.
    event_id: Mapped[str] = mapped_column(String, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'))
    risk_level: Mapped[str]
    channel: Mapped[str] = mapped_column(default='email')
    status: Mapped[str] = mapped_column(default='attempting')
    sent_at: Mapped[str | None]
    error_message: Mapped[str | None]
    evidence: Mapped[dict] = mapped_column(JSON)


def migrate_notification_preferences(bind):
    """Idempotent additive SQLite MVP migration; old users stay opted out."""
    if bind.dialect.name != 'sqlite':
        return  # Other deployments must use their normal schema migration tooling.
    fields = {column['name'] for column in inspect(bind).get_columns('users')}
    additions = {'latitude':'FLOAT','longitude':'FLOAT','alert_radius_km':'FLOAT',
                 'notifications_enabled':'BOOLEAN NOT NULL DEFAULT 0'}
    with bind.begin() as connection:
        for name, kind in additions.items():
            if name not in fields:
                connection.execute(text(f'ALTER TABLE users ADD COLUMN {name} {kind}'))


class PushSubscription(Base):
    __tablename__ = 'push_subscriptions'
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'), primary_key=True)
    token: Mapped[str] = mapped_column(String, unique=True)
