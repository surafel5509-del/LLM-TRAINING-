from datetime import datetime
from uuid import uuid4
from sqlalchemy import String, Text, Integer, Float, DateTime, ForeignKey, JSON, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .db import Base

def uid(): return str(uuid4())

class Project(Base):
    __tablename__='projects'
    id: Mapped[str]=mapped_column(String(36), primary_key=True, default=uid)
    name: Mapped[str]=mapped_column(String(200), nullable=False)
    created_at: Mapped[datetime]=mapped_column(DateTime, default=datetime.utcnow)

class Dataset(Base):
    __tablename__='datasets'
    id: Mapped[str]=mapped_column(String(36), primary_key=True, default=uid)
    project_id: Mapped[str]=mapped_column(ForeignKey('projects.id'), index=True)
    name: Mapped[str]=mapped_column(String(200))
    path: Mapped[str]=mapped_column(Text)
    format: Mapped[str]=mapped_column(String(20))
    rows: Mapped[int|None]=mapped_column(Integer)
    columns: Mapped[int|None]=mapped_column(Integer)
    created_at: Mapped[datetime]=mapped_column(DateTime, default=datetime.utcnow)

class Model(Base):
    __tablename__='models'
    id: Mapped[str]=mapped_column(String(36), primary_key=True, default=uid)
    project_id: Mapped[str]=mapped_column(ForeignKey('projects.id'), index=True)
    name: Mapped[str]=mapped_column(String(200))
    task: Mapped[str]=mapped_column(String(40))
    architecture: Mapped[dict]=mapped_column(JSON)
    created_at: Mapped[datetime]=mapped_column(DateTime, default=datetime.utcnow)

class TrainingRun(Base):
    __tablename__='training_runs'
    id: Mapped[str]=mapped_column(String(36), primary_key=True, default=uid)
    project_id: Mapped[str]=mapped_column(ForeignKey('projects.id'), index=True)
    dataset_id: Mapped[str]=mapped_column(ForeignKey('datasets.id'))
    model_id: Mapped[str]=mapped_column(ForeignKey('models.id'))
    status: Mapped[str]=mapped_column(String(20), default='QUEUED')
    config: Mapped[dict]=mapped_column(JSON)
    error: Mapped[str|None]=mapped_column(Text)
    started_at: Mapped[datetime|None]=mapped_column(DateTime)
    finished_at: Mapped[datetime|None]=mapped_column(DateTime)

class Metric(Base):
    __tablename__='metrics'
    id: Mapped[str]=mapped_column(String(36), primary_key=True, default=uid)
    run_id: Mapped[str]=mapped_column(ForeignKey('training_runs.id'), index=True)
    epoch: Mapped[int]=mapped_column(Integer)
    split: Mapped[str]=mapped_column(String(20))
    loss: Mapped[float]=mapped_column(Float)
    metric: Mapped[float|None]=mapped_column(Float)
    learning_rate: Mapped[float|None]=mapped_column(Float)
    samples_per_sec: Mapped[float|None]=mapped_column(Float)

class Checkpoint(Base):
    __tablename__='checkpoints'
    id: Mapped[str]=mapped_column(String(36), primary_key=True, default=uid)
    run_id: Mapped[str]=mapped_column(ForeignKey('training_runs.id'), index=True)
    epoch: Mapped[int]=mapped_column(Integer)
    path: Mapped[str]=mapped_column(Text)
    is_best: Mapped[bool]=mapped_column(Boolean, default=False)
    created_at: Mapped[datetime]=mapped_column(DateTime, default=datetime.utcnow)

class Evaluation(Base):
    __tablename__='evaluations'
    id: Mapped[str]=mapped_column(String(36), primary_key=True, default=uid)
    run_id: Mapped[str]=mapped_column(ForeignKey('training_runs.id'), index=True)
    metrics: Mapped[dict]=mapped_column(JSON)
    created_at: Mapped[datetime]=mapped_column(DateTime, default=datetime.utcnow)
