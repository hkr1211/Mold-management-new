# app/utils/models.py
#
# SQLAlchemy ORM 模型 — 仅作为人类可读的 schema 文档。
# ⚠️ 非权威、非运行时依赖：schema 的唯一事实来源是 sql/sqlite_init.sql。
#     实际查询全部通过 utils/database.py 的原生 SQL 执行，不依赖此文件。
#     （注意 sqlalchemy 未列入 requirements.txt，本文件在部署环境无法 import。）

import datetime
from sqlalchemy import (
    create_engine, Column, Integer, String, Text, Date,
    DateTime, ForeignKey, Boolean, Numeric, MetaData, BigInteger
)
from sqlalchemy.orm import relationship, declarative_base

metadata_obj = MetaData(naming_convention={
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s"
})

Base = declarative_base(metadata=metadata_obj)


class Role(Base):
    """角色表"""
    __tablename__ = 'roles'

    role_id = Column(Integer, primary_key=True)
    role_name = Column(String(50), unique=True, nullable=False)
    description = Column(Text)

    users = relationship("User", back_populates="role")


class User(Base):
    """用户表"""
    __tablename__ = 'users'

    user_id = Column(Integer, primary_key=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(100))
    email = Column(String(100))
    role_id = Column(Integer, ForeignKey('roles.role_id'))
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), default=datetime.datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.datetime.utcnow,
                        onupdate=datetime.datetime.utcnow)

    role = relationship("Role", back_populates="users")
    loan_records = relationship("MoldLoanRecord", back_populates="applicant")
    maintenance_logs = relationship("MoldMaintenanceLog", back_populates="technician")
    system_logs = relationship("SystemLog", back_populates="user")


class MoldFunctionalType(Base):
    """模具功能类型字典"""
    __tablename__ = 'mold_functional_types'

    type_id = Column(Integer, primary_key=True)
    type_name = Column(String(100), unique=True, nullable=False)
    description = Column(Text)

    molds = relationship("Mold", back_populates="functional_type")


class MoldStatus(Base):
    """模具状态字典"""
    __tablename__ = 'mold_statuses'

    status_id = Column(Integer, primary_key=True)
    status_name = Column(String(50), unique=True, nullable=False)
    description = Column(Text)

    molds = relationship("Mold", back_populates="current_status")


class StorageLocation(Base):
    """存放位置字典"""
    __tablename__ = 'storage_locations'

    location_id = Column(Integer, primary_key=True)
    location_name = Column(String(100), unique=True, nullable=False)
    description = Column(Text)

    molds = relationship("Mold", back_populates="current_location")


class Mold(Base):
    """模具主数据表"""
    __tablename__ = 'molds'

    mold_id = Column(Integer, primary_key=True)
    mold_code = Column(String(100), unique=True, nullable=False, index=True)
    mold_name = Column(String(255), nullable=False)
    mold_drawing_number = Column(String(100))
    mold_functional_type_id = Column(Integer, ForeignKey('mold_functional_types.type_id'))
    supplier = Column(String(255))
    manufacturing_date = Column(Date)
    theoretical_lifespan_strokes = Column(BigInteger)
    accumulated_strokes = Column(BigInteger, default=0)
    maintenance_cycle_strokes = Column(BigInteger)
    current_status_id = Column(Integer, ForeignKey('mold_statuses.status_id'))
    current_location_id = Column(Integer, ForeignKey('storage_locations.location_id'))
    responsible_person_id = Column(Integer, ForeignKey('users.user_id'))
    remarks = Column(Text)
    created_at = Column(DateTime(timezone=True), default=datetime.datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.datetime.utcnow,
                        onupdate=datetime.datetime.utcnow)

    functional_type = relationship("MoldFunctionalType", back_populates="molds")
    current_status = relationship("MoldStatus", back_populates="molds")
    current_location = relationship("StorageLocation", back_populates="molds")
    loan_records = relationship("MoldLoanRecord", back_populates="mold")
    maintenance_logs = relationship("MoldMaintenanceLog", back_populates="mold")
    parts = relationship("MoldPart", back_populates="mold")


class LoanStatus(Base):
    """借用状态字典"""
    __tablename__ = 'loan_statuses'

    status_id = Column(Integer, primary_key=True)
    status_name = Column(String(50), unique=True, nullable=False)
    description = Column(Text)

    loan_records = relationship("MoldLoanRecord", back_populates="loan_status")


class MoldLoanRecord(Base):
    """模具借用记录表"""
    __tablename__ = 'mold_loan_records'

    loan_id = Column(Integer, primary_key=True)
    mold_id = Column(Integer, ForeignKey('molds.mold_id'), nullable=False, index=True)
    applicant_id = Column(Integer, ForeignKey('users.user_id'), nullable=False)
    loan_status_id = Column(Integer, ForeignKey('loan_statuses.status_id'))
    application_date = Column(DateTime(timezone=True), default=datetime.datetime.utcnow)
    expected_return_date = Column(DateTime(timezone=True))
    actual_return_date = Column(DateTime(timezone=True))
    purpose = Column(Text)
    remarks = Column(Text)
    created_at = Column(DateTime(timezone=True), default=datetime.datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.datetime.utcnow,
                        onupdate=datetime.datetime.utcnow)

    mold = relationship("Mold", back_populates="loan_records")
    applicant = relationship("User", back_populates="loan_records")
    loan_status = relationship("LoanStatus", back_populates="loan_records")


class MaintenanceType(Base):
    """维修保养类型字典"""
    __tablename__ = 'maintenance_types'

    type_id = Column(Integer, primary_key=True)
    type_name = Column(String(100), unique=True, nullable=False)
    is_repair = Column(Boolean, default=False)
    description = Column(Text)


class MaintenanceResultStatus(Base):
    """维修结果状态字典"""
    __tablename__ = 'maintenance_result_statuses'

    status_id = Column(Integer, primary_key=True)
    status_name = Column(String(50), unique=True, nullable=False)
    description = Column(Text)

    maintenance_logs = relationship("MoldMaintenanceLog", back_populates="result_status")


class MoldMaintenanceLog(Base):
    """模具维修保养记录表"""
    __tablename__ = 'mold_maintenance_logs'

    log_id = Column(Integer, primary_key=True)
    mold_id = Column(Integer, ForeignKey('molds.mold_id'), nullable=False, index=True)
    maintenance_type_id = Column(Integer, ForeignKey('maintenance_types.type_id'))
    technician_id = Column(Integer, ForeignKey('users.user_id'))
    result_status_id = Column(Integer, ForeignKey('maintenance_result_statuses.status_id'))
    maintenance_start_timestamp = Column(DateTime(timezone=True))
    maintenance_end_timestamp = Column(DateTime(timezone=True))
    description = Column(Text)
    cost = Column(Numeric(12, 2))
    strokes_at_maintenance = Column(BigInteger)
    created_at = Column(DateTime(timezone=True), default=datetime.datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.datetime.utcnow,
                        onupdate=datetime.datetime.utcnow)

    mold = relationship("Mold", back_populates="maintenance_logs")
    technician = relationship("User", back_populates="maintenance_logs")
    result_status = relationship("MaintenanceResultStatus", back_populates="maintenance_logs")


class MoldPartCategory(Base):
    """模具部件分类字典"""
    __tablename__ = 'mold_part_categories'

    category_id = Column(Integer, primary_key=True)
    category_name = Column(String(100), unique=True, nullable=False)
    description = Column(Text)

    parts = relationship("MoldPart", back_populates="category")


class MoldPart(Base):
    """模具部件表"""
    __tablename__ = 'mold_parts'

    part_id = Column(Integer, primary_key=True)
    mold_id = Column(Integer, ForeignKey('molds.mold_id', ondelete='CASCADE'),
                     nullable=False, index=True)
    part_code = Column(String(100), unique=True)
    part_name = Column(String(255), nullable=False)
    part_category_id = Column(Integer, ForeignKey('mold_part_categories.category_id'),
                               nullable=False)
    material = Column(String(100))
    supplier = Column(String(255))
    installation_date = Column(Date)
    lifespan_strokes = Column(BigInteger)
    current_status_id = Column(Integer, ForeignKey('mold_statuses.status_id'))
    remarks = Column(Text)
    created_at = Column(DateTime(timezone=True), default=datetime.datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.datetime.utcnow,
                        onupdate=datetime.datetime.utcnow)

    mold = relationship("Mold", back_populates="parts")
    category = relationship("MoldPartCategory", back_populates="parts")


class SystemLog(Base):
    """系统操作审计日志表"""
    __tablename__ = 'system_logs'

    log_id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.user_id'), nullable=True, index=True)
    action_type = Column(String(100), nullable=False)
    target_resource = Column(String(100))
    target_id = Column(String(100))
    details = Column(Text)
    timestamp = Column(DateTime(timezone=True), default=datetime.datetime.utcnow)

    user = relationship("User", back_populates="system_logs")
