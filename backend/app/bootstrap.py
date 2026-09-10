"""Create an administrator interactively without storing credentials in source."""
import getpass
from sqlalchemy import select
from .database import Base,engine,Session,User
from .security import hash_password
if __name__=='__main__':
    Base.metadata.create_all(engine)
    email=input('Administrator email: ').strip().lower()
    password=getpass.getpass('Password (12+ characters): ')
    if '@' not in email or len(password)<12:raise SystemExit('Invalid email or password')
    with Session() as db:
        if db.scalar(select(User).where(User.email==email)):raise SystemExit('User already exists')
        db.add(User(email=email,password=hash_password(password),role='admin'));db.commit()
