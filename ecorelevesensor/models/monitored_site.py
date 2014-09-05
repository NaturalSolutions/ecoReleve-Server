"""
Created on Mon Sep  1 14:38:09 2014

@author: Natural Solutions (Thomas)
"""

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    func,
    Index,
    Integer,
    Numeric,
    Sequence,
    String,
    UniqueConstraint
)

from ..models import Base, dbConfig
from .user import User
from .thesaurus import Thesaurus

schema = dbConfig['data_schema']
dialect = dbConfig['dialect']

class MonitoredSite(Base):
    __tablename__ = 'TMonitoredStations'
    id = Column('TGeo_pk_id', Integer, Sequence('seq_monitoredsite_pk_id'),
                primary_key=True)
    creator = Column(Integer)
    type_ = Column('name_Type', String(200))
    name = Column(String(50))
    id_type = Column('id_Type', Integer)
    creation_date = Column(DateTime, server_default=func.now(), nullable=False)
    active = Column(Boolean)
    __table_args__ = (
        Index('idx_Tmonitoredsite_name', name),
        UniqueConstraint(type_, name),
        {'schema': schema}
    )

    def __json__(self, request):
        return {
            'id':self.id,
            'name':self.name,
            'type':self.type_
        }
    """
    A utiliser une fois qu'eReleve aura disparu ...
    __tablename__ = 'T_MonitoredSite'
    id = Column('PK_id', Integer, Sequence('seq_monitoredsite_pk_id'),
                primary_key=True)
    creator = Column('FK_creator', Integer, ForeignKey(User.id))
    type_ = Column('FK_type', String(256), ForeignKey(Thesaurus.topic_en))
    name = Column(String(50))
    creation_date = Column(DateTime, server_default=func.now(), nullable=False)
    active = Column(Boolean)
    __table_args__ = (
        Index('idx_Tmonitoredsite_name', name),
        {'schema': schema}
    )
    """