from sqlalchemy import Boolean, Column, DateTime, Integer, Sequence, String, create_engine, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, scoped_session

import os

Base = declarative_base()

class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, Sequence('users_id_seq'), primary_key=True)
    login = Column(String)
    name = Column(String)
    role = Column(String)
    email = Column(String)
    last_login = Column(DateTime(timezone=True))
    salt = Column(String)
    password = Column(String)
    create_date = Column(DateTime(timezone=True))

class Task(Base):
    __tablename__ = 'tasks'

    id = Column(Integer, Sequence('tasks_id_seq'), primary_key=True)
    name = Column(String)
    time_limit = Column(Integer)
    memory_limit = Column(Integer)
    generate = Column(Boolean)
    modifiable = Column(Boolean)
    modify_date = Column(DateTime(timezone=True))
    visible = Column(Boolean)
    create_date = Column(DateTime(timezone=True))

class Tag_list(Base):
    __tablename__ = 'tags_list'

    id = Column(Integer, Sequence('tags_list_id_seq'), primary_key=True)
    tag = Column(String)

class Tag(Base):
    __tablename__ = 'tags'

    id = Column(Integer, Sequence('tags_id_seq'), primary_key=True)
    task_id = Column(Integer, ForeignKey('tasks.id'))
    tag_id = Column(Integer, ForeignKey('tags_list.id'))

class Section(Base):
    __tablename__ = 'sections'

    id = Column(Integer, Sequence('sections_id_seq'), primary_key=True)
    name = Column(String)
    password_admin = Column(String)
    password_overseer = Column(String)
    password_guest = Column(String)
    password_user = Column(String)
    hide = Column(Boolean)
    archive = Column(Boolean)
    create_date = Column(DateTime(timezone=True))

class User_in_section(Base):
    __tablename__ = 'users_in_sections'

    id = Column(Integer, Sequence('users_in_sections_id_seq'), primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    section_id = Column(Integer, ForeignKey('sections.id'))
    role = Column(String)
    date = Column(DateTime(timezone=True))

class Subsection(Base):
    __tablename__ = 'subsections'

    id = Column(Integer, Sequence('subsections_id_seq'), primary_key=True)
    section_id = Column(Integer, ForeignKey('sections.id'))
    name = Column(String)
    create_date = Column(DateTime(timezone=True))

class Task_in_subsection(Base):
    __tablename__ = 'tasks_in_subsections'

    id = Column(Integer, Sequence('tasks_in_subsections_id_seq'), primary_key=True)
    task_id = Column(Integer, ForeignKey('tasks.id'))
    Subsection_id = Column(Integer, ForeignKey('subsections.id'))
    add_date = Column(DateTime(timezone=True))
    release_date = Column(DateTime(timezone=True))
    end_date = Column(DateTime(timezone=True))
    frozen_date = Column(DateTime(timezone=True))
    multiplier = Column(Integer)
    acm = Column(Boolean)
    count_other = Column(Boolean)

class Custom_Invocation(Base):
    __tablename__ = 'custom_invocations'

    id = Column(Integer, Sequence('custom_invocations_id_seq'), primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    state = Column(String)
    lang = Column(String)
    date = Column(DateTime(timezone=True))
    time_usage = Column(Integer)
    memory_usage = Column(Integer)

class Submit(Base):
    __tablename__ = 'submits'

    id = Column(Integer, Sequence('submits_id_seq'), primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    task_id = Column(Integer, ForeignKey('tasks.id'))
    state = Column(String)
    lang = Column(String)
    date = Column(DateTime(timezone=True))
    points = Column(Integer)
    compiled = Column(Boolean)
    acm = Column(Boolean)
    subsection_id = Column(Integer, ForeignKey('subsections.id'))

class Test_submit(Base):
    __tablename__ = 'tests_submits'

    id = Column(Integer, Sequence('tests_submits_id_seq'), primary_key=True)
    submit_id = Column(Integer, ForeignKey('submits.id'))
    group_id = Column(Integer)
    test_id = Column(Integer)
    time_usage = Column(Integer)
    memory_usage = Column(Integer)
    status = Column(String)

class Test(Base):
    __tablename__ = 'tests'

    id = Column(Integer, Sequence('tests_id_seq'), primary_key=True)
    task_id = Column(Integer, ForeignKey('tasks.id'))
    group_id = Column(Integer)
    test_id = Column(Integer)
    memory_limit = Column(Integer)
    time_limit = Column(Integer)

class Sessions(Base):
    __tablename__ = 'sessions'

    id = Column(Integer, Sequence('sessions_id_seq'), primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    sid = Column(String)
    date = Column(DateTime(timezone=True))


NEMESIS_USER    = os.getenv("NEMESIS_USER")
NEMESIS_PASSWD  = os.getenv("NEMESIS_PASSWD")
NEMESIS_HOST    = os.getenv("NEMESIS_HOST")
NEMESIS_DB      = os.getenv("NEMESIS_DB")

engine = create_engine('postgresql+psycopg2://%s:%s@%s/%s' % (NEMESIS_USER, NEMESIS_PASSWD, NEMESIS_HOST, NEMESIS_DB), encoding="utf8")
Session = sessionmaker(bind=engine)
session = scoped_session(Session)


def init_db():
    User.metadata.create_all(engine)
    Task.metadata.create_all(engine)
    Tag_list.metadata.create_all(engine)
    Tag.metadata.create_all(engine)
    Section.metadata.create_all(engine)
    User_in_section.metadata.create_all(engine)
    Subsection.metadata.create_all(engine)
    Task_in_subsection.metadata.create_all(engine)
    Custom_Invocation.metadata.create_all(engine)
    Submit.metadata.create_all(engine)
    Test_submit.metadata.create_all(engine)
    Test.metadata.create_all(engine)
    Sessions.metadata.create_all(engine)
