from typing import Literal
from pydantic import BaseModel, Field, EmailStr, ConfigDict


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class Login(Strict):
    email: EmailStr
    password: str = Field(min_length=12, max_length=128)


class AcceptInvite(Login):
    token: str = Field(min_length=20, max_length=100)


class ContactInput(Strict):
    customer: str = Field(min_length=1, max_length=200)
    name: str = Field(min_length=1, max_length=200)
    email: EmailStr
    authorized: bool = False
    acceptance_authority: bool = False


class WorkInput(Strict):
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(min_length=1, max_length=2000)
    contact_id: str
    currency: Literal["USD", "EUR", "GBP", "CAD", "AUD"]


class Source(Strict):
    document_id: str
    version: int
    page: int = Field(ge=1)
    excerpt: str = Field(min_length=1, max_length=1500)
    value: str = Field(max_length=300)


class Proposal(Strict):
    category: Literal[
        "purchase_order",
        "acceptance",
        "deliverable",
        "amount",
        "billing_recipient",
        "custom",
    ]
    title: str = Field(min_length=1, max_length=200)
    status: Literal["missing", "received", "needs_review"]
    source: Source


class Analysis(Strict):
    requirements: list[Proposal] = Field(max_length=30)


class RequirementInput(Strict):
    title: str = Field(min_length=1, max_length=200)
    category: str = Field(min_length=1, max_length=40)
    status: Literal["missing", "received", "needs_review", "satisfied", "waived"]
    reason: str = Field(min_length=1, max_length=1000)
    evidence_ids: list[str] = Field(default_factory=list, max_length=20)


class RequestInput(Strict):
    requirement_ids: list[str] = Field(min_length=1, max_length=30)
    contact_id: str
    follow_up_permission: bool
    body: str | None = Field(default=None, min_length=1, max_length=3000)


class RequestDraft(Strict):
    body: str = Field(min_length=1, max_length=3000)


class ReplyAssociation(Strict):
    requirement_id: str
    excerpt: str = Field(min_length=1, max_length=1500)


class ReplyInterpretation(Strict):
    classification: Literal["relevant", "unrelated", "ambiguous"]
    associations: list[ReplyAssociation] = Field(max_length=30)
    explanation: str = Field(min_length=1, max_length=1000)


class DecisionInput(Strict):
    action: Literal["approve", "reject", "correct", "waive"]
    explanation: str = Field(min_length=5, max_length=2000)
    requirement_id: str | None = None


class LineItem(Strict):
    description: str = Field(min_length=1, max_length=300)
    quantity: str = Field(pattern=r"^\d{1,6}(\.\d{1,3})?$")
    unit_price: str = Field(pattern=r"^\d{1,9}(\.\d{1,2})?$")
    evidence_id: str


class PackageInput(Strict):
    mode: Literal["generated", "existing"]
    contact_ids: list[str] = Field(min_length=1, max_length=5)
    document_ids: list[str] = Field(default_factory=list, max_length=20)
    invoice_document_id: str | None = None
    line_items: list[LineItem] = Field(default_factory=list, max_length=30)
    confirmed_total: str = Field(pattern=r"^\d{1,11}(\.\d{1,2})?$")
    tax: str = Field(default="0", pattern=r"^\d{1,9}(\.\d{1,2})?$")
    discount: str = Field(default="0", pattern=r"^\d{1,9}(\.\d{1,2})?$")
    issue_date: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")
    due_date: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")
    summary: str = Field(min_length=1, max_length=2000)
    details_confirmed: bool


class ApprovalInput(Strict):
    digest: str
    authorize: bool


class SettingsInput(Strict):
    business_name: str = Field(min_length=1, max_length=200)
    billing_details: str = Field(min_length=1, max_length=1500)
    timezone: str
    reminder_limit: int = Field(ge=0, le=2)
    reminder_business_days: int = Field(ge=2, le=30)
    automation_paused: bool


class LocalReply(Strict):
    request_id: str
    event_id: str = Field(min_length=5, max_length=100)
    sender: EmailStr
    text: str = Field(min_length=1, max_length=20000)
    out_of_office: bool = False
    forwarded: bool = False


class AccessRequest(Strict):
    name: str = Field(min_length=1, max_length=100)
    email: EmailStr
    business: str = Field(min_length=1, max_length=200)
    problem: str = Field(min_length=10, max_length=2000)
    consent: bool
    website: str = ""
