from __future__ import annotations

import os
from typing import List
from pydantic import BaseModel, Field
from modules.architecture.generator import ArchitectureResult

class FormFieldSpec(BaseModel):
    name: str
    label: str
    type: str
    required: bool = True

class FormSpec(BaseModel):
    name: str
    fields: List[FormFieldSpec]

class ComponentSpec(BaseModel):
    type: str
    name: str
    properties: List[str] = Field(default_factory=list)

class PageSpec(BaseModel):
    name: str
    path: str
    layout: str
    components: List[ComponentSpec]
    forms: List[FormSpec] = Field(default_factory=list)

class NavigationItem(BaseModel):
    label: str
    path: str

class UiSchema(BaseModel):
    pages: List[PageSpec]
    navigation: List[NavigationItem]

def generate_ui(architecture: ArchitectureResult) -> UiSchema:
    """Generate UI schema containing pages, forms, components, layouts, and navigation."""
    from modules.utils.llm import call_llm_structured
    res = call_llm_structured(
        messages=[{"role": "user", "content": architecture.model_dump_json()}],
        response_model=UiSchema,
        system_prompt="You are a frontend UI spec generator. Generate page designs, layouts, form inputs, and navbar elements matching the application architecture."
    )
    if res:
        return res

    # Deterministic generation fallback
    pages = []
    navigation = []

    # Welcome/Dashboard page is always present
    pages.append(PageSpec(
        name="Dashboard",
        path="/dashboard",
        layout="sidebar",
        components=[
            ComponentSpec(type="MetricCard", name="Total Activity", properties=["count", "trends"]),
            ComponentSpec(type="LineChart", name="Usage over time")
        ]
    ))
    navigation.append(NavigationItem(label="Dashboard", path="/dashboard"))

    for entity in architecture.entities:
        ent_lower = entity.lower()
        if ent_lower == "contact":
            pages.append(PageSpec(
                name="Contacts",
                path="/contacts",
                layout="sidebar",
                components=[
                    ComponentSpec(type="Table", name="ContactsList", properties=["first_name", "last_name", "email", "phone"]),
                    ComponentSpec(type="Button", name="Add Contact Button")
                ],
                forms=[
                    FormSpec(
                        name="CreateContactForm",
                        fields=[
                            FormFieldSpec(name="first_name", label="First Name", type="text"),
                            FormFieldSpec(name="last_name", label="Last Name", type="text"),
                            FormFieldSpec(name="email", label="Email Address", type="email", required=False),
                            FormFieldSpec(name="phone", label="Phone Number", type="tel", required=False)
                        ]
                    )
                ]
            ))
            navigation.append(NavigationItem(label="Contacts", path="/contacts"))
        elif ent_lower == "subscription":
            pages.append(PageSpec(
                name="Billing",
                path="/billing",
                layout="sidebar",
                components=[
                    ComponentSpec(type="Card", name="SubscriptionPlans", properties=["Premium Tier", "Free Tier"]),
                    ComponentSpec(type="Button", name="Checkout Button")
                ]
            ))
            navigation.append(NavigationItem(label="Billing", path="/billing"))
        elif ent_lower == "product":
            pages.append(PageSpec(
                name="Products",
                path="/products",
                layout="grid",
                components=[
                    ComponentSpec(type="ProductGrid", name="ProductCatalog", properties=["name", "price", "description"])
                ],
                forms=[
                    FormSpec(
                        name="AddProductForm",
                        fields=[
                            FormFieldSpec(name="name", label="Product Name", type="text"),
                            FormFieldSpec(name="price", label="Price", type="number"),
                            FormFieldSpec(name="description", label="Description", type="textarea", required=False)
                        ]
                    )
                ]
            ))
            navigation.append(NavigationItem(label="Products", path="/products"))
        elif ent_lower == "cartitem":
            pages.append(PageSpec(
                name="Cart",
                path="/cart",
                layout="sidebar",
                components=[
                    ComponentSpec(type="Table", name="CartItemList", properties=["name", "quantity", "price"]),
                    ComponentSpec(type="Button", name="Proceed to Checkout Button")
                ]
            ))
            navigation.append(NavigationItem(label="Cart", path="/cart"))
        elif ent_lower == "order":
            pages.append(PageSpec(
                name="Orders",
                path="/orders",
                layout="sidebar",
                components=[
                    ComponentSpec(type="Table", name="OrdersHistoryList", properties=["id", "total_price", "status"])
                ]
            ))
            navigation.append(NavigationItem(label="Orders", path="/orders"))

    # Login page (no navbar link but needed in pages)
    pages.append(PageSpec(
        name="Login",
        path="/login",
        layout="centered",
        components=[
            ComponentSpec(type="Card", name="LoginFormCard")
        ],
        forms=[
            FormSpec(
                name="LoginForm",
                fields=[
                    FormFieldSpec(name="email", label="Email", type="email"),
                    FormFieldSpec(name="password", label="Password", type="password")
                ]
            )
        ]
    ))

    return UiSchema(pages=pages, navigation=navigation)
