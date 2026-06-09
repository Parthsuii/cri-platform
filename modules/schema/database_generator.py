from __future__ import annotations

import os
from typing import List, Optional
from pydantic import BaseModel, Field
from modules.architecture.generator import ArchitectureResult

class FieldSpec(BaseModel):
    name: str
    type: str
    primary_key: bool = False
    nullable: bool = True
    unique: bool = False
    references: Optional[str] = None

class TableSpec(BaseModel):
    name: str
    fields: List[FieldSpec]

class DatabaseSchema(BaseModel):
    tables: List[TableSpec]

def generate_database(architecture: ArchitectureResult) -> DatabaseSchema:
    """Generate database schema containing tables, fields, and relationships."""
    from modules.utils.llm import call_llm_structured
    res = call_llm_structured(
        messages=[{"role": "user", "content": architecture.model_dump_json()}],
        response_model=DatabaseSchema,
        system_prompt="You are a database schema compiler. Generate tables, field definitions, and foreign keys matching the application architecture. Crucial: Table names MUST be lowercase and pluralized (e.g., 'users', 'contacts', 'orders')."
    )
    if res:
        return res

    # Deterministic generation fallback
    tables = []

    # Map architecture entities to database tables
    for entity in architecture.entities:
        ent_lower = entity.lower()
        if ent_lower == "user":
            tables.append(TableSpec(
                name="users",
                fields=[
                    FieldSpec(name="id", type="int", primary_key=True, nullable=False),
                    FieldSpec(name="email", type="string", unique=True, nullable=False),
                    FieldSpec(name="password_hash", type="string", nullable=False),
                    FieldSpec(name="role", type="string", nullable=False)
                ]
            ))
        elif ent_lower == "contact":
            tables.append(TableSpec(
                name="contacts",
                fields=[
                    FieldSpec(name="id", type="int", primary_key=True, nullable=False),
                    FieldSpec(name="user_id", type="int", references="users.id", nullable=False),
                    FieldSpec(name="first_name", type="string", nullable=False),
                    FieldSpec(name="last_name", type="string", nullable=False),
                    FieldSpec(name="email", type="string", nullable=True),
                    FieldSpec(name="phone", type="string", nullable=True)
                ]
            ))
        elif ent_lower == "subscription":
            tables.append(TableSpec(
                name="subscriptions",
                fields=[
                    FieldSpec(name="id", type="int", primary_key=True, nullable=False),
                    FieldSpec(name="user_id", type="int", references="users.id", nullable=False),
                    FieldSpec(name="tier", type="string", nullable=False),
                    FieldSpec(name="status", type="string", nullable=False)
                ]
            ))
        elif ent_lower == "product":
            tables.append(TableSpec(
                name="products",
                fields=[
                    FieldSpec(name="id", type="int", primary_key=True, nullable=False),
                    FieldSpec(name="name", type="string", nullable=False),
                    FieldSpec(name="price", type="float", nullable=False),
                    FieldSpec(name="description", type="string", nullable=True)
                ]
            ))
        elif ent_lower == "cartitem":
            tables.append(TableSpec(
                name="cart_items",
                fields=[
                    FieldSpec(name="id", type="int", primary_key=True, nullable=False),
                    FieldSpec(name="user_id", type="int", references="users.id", nullable=False),
                    FieldSpec(name="product_id", type="int", references="products.id", nullable=False),
                    FieldSpec(name="quantity", type="int", nullable=False)
                ]
            ))
        elif ent_lower == "order":
            tables.append(TableSpec(
                name="orders",
                fields=[
                    FieldSpec(name="id", type="int", primary_key=True, nullable=False),
                    FieldSpec(name="user_id", type="int", references="users.id", nullable=False),
                    FieldSpec(name="total_price", type="float", nullable=False),
                    FieldSpec(name="status", type="string", nullable=False)
                ]
            ))
        else:
            # Fallback for dynamic/custom entities
            tables.append(TableSpec(
                name=f"{ent_lower}s",
                fields=[
                    FieldSpec(name="id", type="int", primary_key=True, nullable=False),
                    FieldSpec(name="user_id", type="int", references="users.id", nullable=False),
                    FieldSpec(name="name", type="string", nullable=False)
                ]
            ))

    # Ensure a users table always exists for authentication/roles
    if not any(t.name == "users" for t in tables):
        tables.insert(0, TableSpec(
            name="users",
            fields=[
                FieldSpec(name="id", type="int", primary_key=True, nullable=False),
                FieldSpec(name="email", type="string", unique=True, nullable=False),
                FieldSpec(name="password_hash", type="string", nullable=False),
                FieldSpec(name="role", type="string", nullable=False)
            ]
        ))

    return DatabaseSchema(tables=tables)
