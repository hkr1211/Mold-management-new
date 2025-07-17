# app/utils/models.py (完整修正版 - 仅修改必要的字段名)

import datetime
from sqlalchemy import (
    create_engine, Column, Integer, String, Text, DateTime,
    ForeignKey, Boolean, Numeric, MetaData
)
from sqlalchemy.orm import relationship, declarative_base

# --- SQLAlchemy 最佳实践：定义命名约定 ---
metadata_obj = MetaData(naming_convention={
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s"
})

# 创建所有模型的基类
Base = declarative_base(metadata=metadata_obj)


class User(Base):
    """用户表 - 仅修改主键字段名"""
    __tablename__ = 'users'
    
    # 唯一修改：id -> user_id，其他保持原样
    user_id = Column(Integer, primary_key=True)  # 原来是: id = Column(Integer, primary_key=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(50), nullable=False, default='operator')  # 角色: operator, manager, admin
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.now)
    
    # 根据实际数据库，可能还需要添加这些字段：
    full_name = Column(String(100))  # 从数据库结构看到有这个字段
    email = Column(String(100))      # 从数据库结构看到有这个字段
    role_id = Column(Integer)        # 从数据库结构看到有这个字段
    updated_at = Column(DateTime, default=datetime.datetime.now, onupdate=datetime.datetime.now)

    # 关系: 一个用户可以有多条借用记录和维修记录
    loan_records = relationship("LoanRecord", back_populates="user", cascade="all, delete-orphan")
    maintenance_records = relationship("MaintenanceRecord", back_populates="user", cascade="all, delete-orphan")


class Mold(Base):
    """模具主数据表 - 保持原样"""
    __tablename__ = 'molds'
    id = Column(Integer, primary_key=True)  # 这个保持不变，除非数据库中也不同
    mold_id = Column(String(100), unique=True, nullable=False, index=True)
    mold_name = Column(String(255), nullable=False)
    status = Column(String(50), default='in_storage', index=True) # 状态: in_storage, in_use, under_maintenance, scrapped
    location = Column(String(100))
    asset_number = Column(String(100), unique=True) # 固定资产编号
    project_name = Column(String(255))
    part_number = Column(String(255))
    part_name = Column(String(255))
    material = Column(String(100)) # 材质
    cavity_count = Column(Integer) # 穴数
    size = Column(String(100)) # 尺寸 (长*宽*高)
    weight_kg = Column(Numeric(10, 2)) # 重量(KG)
    supplier = Column(String(255)) # 供应商
    purchase_date = Column(DateTime)
    purchase_price = Column(Numeric(12, 2))
    total_shots = Column(Integer, default=0) # 总模次
    maintenance_cycle_shots = Column(Integer, default=50000) # 保养周期模次
    last_maintenance_shots = Column(Integer, default=0) # 上次保养时模次
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.datetime.now)
    updated_at = Column(DateTime, default=datetime.datetime.now, onupdate=datetime.datetime.now)

    # 关系: 一个模具可以有多条借用记录、维修记录和关联备件
    loan_records = relationship("LoanRecord", back_populates="mold", cascade="all, delete-orphan")
    maintenance_records = relationship("MaintenanceRecord", back_populates="mold", cascade="all, delete-orphan")
    parts = relationship("Part", back_populates="mold")


class LoanRecord(Base):
    """模具借用/归还记录表"""
    __tablename__ = 'loan_records'
    id = Column(Integer, primary_key=True)
    mold_id_fk = Column(Integer, ForeignKey('molds.id'), nullable=False, index=True)
    user_id_fk = Column(Integer, ForeignKey('users.user_id'), nullable=False, index=True)  # 修改：指向users.user_id
    loan_date = Column(DateTime, default=datetime.datetime.now)
    expected_return_date = Column(DateTime)
    actual_return_date = Column(DateTime)
    status = Column(String(50), default='pending', index=True)  # 状态: pending, approved, rejected, returned
    purpose = Column(Text) # 借用事由
    created_at = Column(DateTime, default=datetime.datetime.now)

    # 关系: 每一条借用记录都对应一个模具和一个用户
    mold = relationship("Mold", back_populates="loan_records")
    user = relationship("User", back_populates="loan_records")


class MaintenanceRecord(Base):
    """模具维修/保养记录表"""
    __tablename__ = 'maintenance_records'
    id = Column(Integer, primary_key=True)
    mold_id_fk = Column(Integer, ForeignKey('molds.id'), nullable=False, index=True)
    user_id_fk = Column(Integer, ForeignKey('users.user_id'), nullable=False, index=True) # 修改：指向users.user_id
    maintenance_type = Column(String(50), nullable=False) # 'maintenance' (保养) or 'repair' (维修)
    maintenance_date = Column(DateTime, default=datetime.datetime.now)
    description = Column(Text, nullable=False) # 维修/保养内容描述
    cost = Column(Numeric(12, 2)) # 费用
    created_at = Column(DateTime, default=datetime.datetime.now)

    # 关系: 每一条维修记录都对应一个模具和一个执行用户
    mold = relationship("Mold", back_populates="maintenance_records")
    user = relationship("User", back_populates="maintenance_records")


class Part(Base):
    """备件信息表"""
    __tablename__ = 'parts'
    id = Column(Integer, primary_key=True)
    part_number = Column(String(100), unique=True, nullable=False, index=True)
    part_name = Column(String(255), nullable=False)
    description = Column(Text)
    stock_quantity = Column(Integer, default=0, nullable=False)
    safe_stock_level = Column(Integer, default=0) # 安全库存水平
    location = Column(String(100)) # 存放位置
    
    # 关系: 一个备件可以用于一个主模具 (如果备件是通用的，此字段可为NULL)
    mold_id_fk = Column(Integer, ForeignKey('molds.id'), nullable=True, index=True)
    mold = relationship("Mold", back_populates="parts")


class SystemLog(Base):
    """系统操作日志表"""
    __tablename__ = 'system_logs'
    id = Column(Integer, primary_key=True)
    user_id_fk = Column(Integer, ForeignKey('users.user_id'), nullable=True) # 修改：指向users.user_id
    action_type = Column(String(100), nullable=False)
    target_resource = Column(String(100))
    target_id = Column(String(100))
    details = Column(Text) # 使用Text存储JSON字符串
    created_at = Column(DateTime, default=datetime.datetime.now)

    user = relationship("User")