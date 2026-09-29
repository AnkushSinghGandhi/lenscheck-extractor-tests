from sqlalchemy.orm import scoped_session, sessionmaker

session = scoped_session(sessionmaker())     # named `session` → recognised as a SQLAlchemy session
