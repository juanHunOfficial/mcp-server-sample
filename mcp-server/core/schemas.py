from pydantic import BaseModel, Field, HttpUrl
from typing import Optional, List
from datetime import datetime


class StockPriceResponse(BaseModel):
    """Stock price response details."""
    ticker: str = Field(description="Stock ticker symbol")
    name: str = Field(description="Name of the company")
    price: float = Field(description="Current stock price in USD")
    exchange: str = Field(description="The market hosting the stock")
    currency: str = Field(description="The currency used to trade this stock")


class ErrorResponse(BaseModel):
    """Structured error response for failed API calls."""
    status: str = Field(description="Status of the request", default="error")
    error_code: str = Field(description="Machine-readable error code")
    message: str = Field(description="Human-readable error description")
    suggested_resolutions: list[str] = Field(description="List of suggested actions to resolve the error")


class KnowledgeBaseResponse(BaseModel):
    """Response model for knowledge base ticket details."""
    ticket_id: str = Field(description="This is a placeholder for the database connection")
    short_description: str = Field(description="This is a placeholder for the database connection")
    description: str = Field(description="This is a placeholder for the database connection")
    priority: str = Field(description="This is a placeholder for the database connection")
    close_notes: Optional[str] = Field(description="This is a placeholder for the database connection", default=None) 
    known_solution: Optional[str] = Field(description="This is a placeholder for the database connection", default=None)
    root_cause: Optional[str] = Field(description="This is a placeholder for the database connection", default=None)
    sys_created_on: Optional[datetime] = Field(description="This is a placeholder for the database connection", default=None)


# Terraform tool
class EnvRequest(BaseModel):
    path: str = Field(description="Path to the Terraform file to analyze")


class EnvResponse(BaseModel):
    variables: List[str] = Field(description="List of variable names defined in the Terraform file")
    providers: List[str] = Field(description="List of provider names used in the Terraform file")
    resources: List[str] = Field(description="List of resources in the format type.name found in the Terraform file")
    outputs: List[str] = Field(description="List of output names defined in the Terraform file")


# Code reviewer tool
class Reviewer(BaseModel):
    name: str
    email: str
    role: str


class ReviewerList(BaseModel):
    reviewers: List[Reviewer]


# Coding standards resource
class CodingStandard(BaseModel):
    section: str
    description: str
    link: HttpUrl


class CodingStandardsResponse(BaseModel):
    standards: List[CodingStandard]


# Changelog tool
class ChangelogEntry(BaseModel):
    title: str
    summary: str
    breaking_changes: Optional[str]
    links: list[str]
    markdown: str