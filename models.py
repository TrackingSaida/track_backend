from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    JSON,
    Numeric,
    SmallInteger,
    Text,
)
from sqlalchemy.orm import relationship

from db import Base

# ======================
# OWNER (EMPRESA / PRESTADOR)
# ======================
class Owner(Base):
    __tablename__ = "owner"
    __table_args__ = {"schema": "mt"}

    id_owner = Column(BigInteger, primary_key=True, autoincrement=True)
    nome_empresa = Column(Text, nullable=False)
    tipo_empresa = Column(Text, nullable=False)  # enum mt.owner_tipo
    documento_empresa = Column(Text, nullable=True)
    email_contato = Column(Text, nullable=True)
    telefone_empresa = Column(Text, nullable=True)
    ativo_empresa = Column(Boolean, nullable=False, default=True)

    slug = Column(Text, nullable=True)
    custom_domain = Column(Text, nullable=True)
    tema_json = Column(JSON, nullable=True, default=dict)
    espelhar_status = Column(Boolean, nullable=True, default=True)

    criado_em = Column(DateTime(timezone=True), nullable=True)
    atualizado_em = Column(DateTime(timezone=True), nullable=True)

    # relacionamentos
    users = relationship("User", back_populates="owner", lazy="selectin")

    clientes = relationship(
        "Cliente",
        back_populates="owner",
        lazy="selectin",
        foreign_keys="Cliente.owner_id",
    )

    orders = relationship(
        "Order",
        back_populates="empresa",
        lazy="selectin",
        foreign_keys="Order.owner_id",
    )

    movimentos_financeiros = relationship(
        "FinanceiroMovimento",
        back_populates="owner",
        lazy="selectin",
        foreign_keys="FinanceiroMovimento.owner_id",
    )

    entregador_valores = relationship(
        "EntregadorValor",
        back_populates="empresa",
        lazy="selectin",
        foreign_keys="EntregadorValor.owner_id",
    )


# ======================
# USERS
# ======================
class User(Base):
    __tablename__ = "users"
    __table_args__ = {"schema": "mt"}

    user_id = Column(BigInteger, primary_key=True, autoincrement=True)
    owner_id = Column(BigInteger, ForeignKey("mt.owner.id_owner"), nullable=False)

    nome = Column(Text, nullable=True)
    email = Column(Text, nullable=True)
    username = Column(Text, nullable=True)

    password_hash = Column(Text, nullable=False)
    tipo = Column(Text, nullable=True)  # enum mt.user_tipo
    ativo = Column(Boolean, nullable=True, default=True)
    coletador = Column(Boolean, nullable=True, default=False)

    criado_em = Column(DateTime(timezone=True), nullable=True)
    atualizado_em = Column(DateTime(timezone=True), nullable=True)

    sobrenome = Column(Text, nullable=True)
    documento = Column(Text, nullable=True)
    telefone = Column(Text, nullable=True)

    endereco_rua = Column(Text, nullable=True)
    endereco_numero = Column(Text, nullable=True)
    endereco_complemento = Column(Text, nullable=True)
    endereco_bairro = Column(Text, nullable=True)
    endereco_cidade = Column(Text, nullable=True)
    endereco_estado = Column(Text, nullable=True)
    endereco_cep = Column(Text, nullable=True)

    owner = relationship("Owner", back_populates="users", lazy="joined")

    # relacionamentos com outras tabelas
    deliveries = relationship(
        "Delivery",
        back_populates="entregador",
        lazy="selectin",
        foreign_keys="Delivery.entregador_id",
    )

    entregador_valores = relationship(
        "EntregadorValor",
        back_populates="entregador",
        lazy="selectin",
        foreign_keys="EntregadorValor.entregador_id",
    )

# ======================
# CLIENTE
# ======================
class Cliente(Base):
    __tablename__ = "cliente"
    __table_args__ = {"schema": "mt"}

    id_cliente = Column(BigInteger, primary_key=True, autoincrement=True)
    owner_id = Column(BigInteger, ForeignKey("mt.owner.id_owner"), nullable=False)
    link_owner_id = Column(BigInteger, ForeignKey("mt.owner.id_owner"), nullable=False)

    nome = Column(Text, nullable=False)
    endereco_cep = Column(Text, nullable=True)  # varchar(9)
    endereco_cidade = Column(Text, nullable=True)
    endereco_estado = Column(Text, nullable=True)  # char(2)
    ativo = Column(Boolean, nullable=True, default=True)

    criado_em = Column(DateTime(timezone=True), nullable=True)

    preco_shopee = Column(Numeric(12, 2), nullable=True, default=0)
    preco_ml = Column(Numeric(12, 2), nullable=True, default=0)
    preco_avulso = Column(Numeric(12, 2), nullable=True, default=0)
    endereco_rua = Column(Text, nullable=True)
    endereco_numero = Column(Text, nullable=True)
    endereco_complemento = Column(Text, nullable=True)
    endereco_bairro = Column(Text, nullable=True)
    documento_cliente = Column(Text, nullable=True)
    email_cliente = Column(Text, nullable=True)
    telefone_cliente = Column(Text, nullable=True)
    tipo_cliente = Column(Text, nullable=False)  # enum mt.tipo_cliente

    # deixa claro que essa relação usa a FK owner_id
    owner = relationship(
        "Owner",
        back_populates="clientes",
        lazy="joined",
        foreign_keys=[owner_id],
    )

    # relação opcional usando link_owner_id (sem back_populates)
    link_owner = relationship(
        "Owner",
        lazy="joined",
        foreign_keys=[link_owner_id],
    )

    orders = relationship("Order", back_populates="cliente", lazy="selectin")


# ======================
# ORDERS
# ======================
class Order(Base):
    __tablename__ = "orders"
    __table_args__ = {"schema": "mt"}

    order_id = Column(BigInteger, primary_key=True, autoincrement=True)

    owner_id = Column(BigInteger, ForeignKey("mt.owner.id_owner"), nullable=False)
    cliente_id = Column(BigInteger, ForeignKey("mt.cliente.id_cliente"), nullable=True)
    base_order_id = Column(BigInteger, ForeignKey("mt.orders.order_id"), nullable=True)

    codigo_pacote = Column(Text, nullable=False)
    servico = Column(Text, nullable=False)

    criado_em = Column(DateTime(timezone=True), nullable=True)
    atualizado_em = Column(DateTime(timezone=True), nullable=True)

    status = Column(SmallInteger, nullable=False, default=0)  # enum mt.pedido_status

    orders_rua = Column(Text, nullable=True)
    orders_cep = Column(Text, nullable=True)

    # não há FK no schema atual
    user_id = Column(BigInteger, nullable=True)

    empresa = relationship(
        "Owner",
        back_populates="orders",
        lazy="joined",
        foreign_keys=[owner_id],
    )

    cliente = relationship(
        "Cliente",
        back_populates="orders",
        lazy="joined",
        foreign_keys=[cliente_id],
    )

    events = relationship(
        "OrderEvent",
        back_populates="order",
        cascade="all, delete-orphan",
        lazy="selectin",
        foreign_keys="OrderEvent.order_id",
    )

    deliveries = relationship(
        "Delivery",
        back_populates="order",
        cascade="all, delete-orphan",
        lazy="selectin",
        foreign_keys="Delivery.order_id",
    )

    movimentos_financeiros = relationship(
        "FinanceiroMovimento",
        back_populates="order",
        cascade="all, delete-orphan",
        lazy="selectin",
        foreign_keys="FinanceiroMovimento.order_id",
    )


# ======================
# ORDER EVENTS
# ======================
class OrderEvent(Base):
    __tablename__ = "order_events"
    __table_args__ = {"schema": "mt"}

    event_id = Column(BigInteger, primary_key=True, autoincrement=True)
    order_id = Column(BigInteger, ForeignKey("mt.orders.order_id"), nullable=True)

    tipo = Column(SmallInteger, nullable=False)
    actor_user_id = Column(BigInteger, nullable=True)  # sem FK no schema
    payload = Column(JSON, nullable=True, default=dict)
    data_hora = Column(DateTime(timezone=True), nullable=True)
    owner_id = Column(BigInteger, nullable=True)  # sem FK no schema

    order = relationship("Order", back_populates="events", lazy="joined")


# ======================
# DELIVERIES
# ======================
class Delivery(Base):
    __tablename__ = "deliveries"
    __table_args__ = {"schema": "mt"}

    delivery_id = Column(BigInteger, primary_key=True, autoincrement=True)

    order_id = Column(
        BigInteger,
        ForeignKey("mt.orders.order_id"),
        nullable=True,
    )
    entregador_id = Column(
        BigInteger,
        ForeignKey("mt.users.user_id"),
        nullable=True,
    )
    cliente_id = Column(
        BigInteger,
        ForeignKey("mt.owner.id_owner"),
        nullable=True,
    )

    status = Column(Text, nullable=True)
    entregue_em = Column(DateTime(timezone=True), nullable=True)
    motivo_ocorrencia = Column(Text, nullable=True)
    criado_em = Column(DateTime(timezone=True), nullable=True)

    order = relationship(
        "Order",
        back_populates="deliveries",
        lazy="joined",
        foreign_keys=[order_id],
    )

    entregador = relationship(
        "User",
        back_populates="deliveries",
        lazy="joined",
        foreign_keys=[entregador_id],
    )

    # no Excel o nome da coluna é cliente_id, mas aponta para owner
    prestador = relationship(
        "Owner",
        lazy="joined",
        foreign_keys=[cliente_id],
    )

    proofs = relationship(
        "Proof",
        back_populates="delivery",
        cascade="all, delete-orphan",
        lazy="selectin",
        foreign_keys="Proof.delivery_id",
    )


# ======================
# PROOFS
# ======================
class Proof(Base):
    __tablename__ = "proofs"
    __table_args__ = {"schema": "mt"}

    id_proof = Column(BigInteger, primary_key=True, autoincrement=True)

    delivery_id = Column(
        BigInteger,
        ForeignKey("mt.deliveries.delivery_id"),
        nullable=True,
    )
    tipo = Column(Text, nullable=True)
    storage_key = Column(Text, nullable=False)

    criado_em = Column(DateTime(timezone=True), nullable=True)

    delivery = relationship(
        "Delivery",
        back_populates="proofs",
        lazy="joined",
        foreign_keys=[delivery_id],
    )


# ======================
# FINANCEIRO_MOVIMENTO
# ======================
class FinanceiroMovimento(Base):
    __tablename__ = "financeiro_movimento"
    __table_args__ = {"schema": "mt"}

    id_mov = Column(BigInteger, primary_key=True, autoincrement=True)

    order_id = Column(
        BigInteger,
        ForeignKey("mt.orders.order_id"),
        nullable=True,
    )
    owner_id = Column(
        BigInteger,
        ForeignKey("mt.owner.id_owner"),
        nullable=True,
    )

    destino_tipo = Column(Text, nullable=True)
    destino_id = Column(BigInteger, nullable=True)

    tipo = Column(Text, nullable=True)
    servico = Column(Text, nullable=True)

    valor = Column(Numeric(12, 2), nullable=True)
    status = Column(Text, nullable=True, default="pendente")

    criado_em = Column(DateTime(timezone=True), nullable=True)

    order = relationship(
        "Order",
        back_populates="movimentos_financeiros",
        lazy="joined",
        foreign_keys=[order_id],
    )
    owner = relationship(
        "Owner",
        back_populates="movimentos_financeiros",
        lazy="joined",
        foreign_keys=[owner_id],
    )


# ======================
# ENTREGADOR_VALOR
# ======================
class EntregadorValor(Base):
    __tablename__ = "entregador_valor"
    __table_args__ = {"schema": "mt"}

    valor_entregado_id = Column(BigInteger, primary_key=True, autoincrement=True)

    owner_id = Column(
        BigInteger,
        ForeignKey("mt.owner.id_owner"),
        nullable=False,
    )
    entregador_id = Column(
        BigInteger,
        ForeignKey("mt.users.user_id"),
        nullable=False,
    )

    servico = Column(Text, nullable=False)
    valor = Column(Numeric(12, 2), nullable=False)

    ativo = Column(Boolean, nullable=True, default=True)
    criado_em = Column(DateTime(timezone=True), nullable=True)

    empresa = relationship(
        "Owner",
        back_populates="entregador_valores",
        lazy="joined",
        foreign_keys=[owner_id],
    )
    entregador = relationship(
        "User",
        back_populates="entregador_valores",
        lazy="joined",
        foreign_keys=[entregador_id],
    )
