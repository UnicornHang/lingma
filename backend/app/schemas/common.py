"""通用 Schema"""
from pydantic import BaseModel, Field


class ErrorResponse(BaseModel):
    """统一错误响应"""

    code: str = Field(..., description="错误代码")
    message: str = Field(..., description="错误消息")
    details: dict | None = Field(None, description="详细信息")


class HealthResponse(BaseModel):
    """健康检查响应"""

    status: str = Field(..., description="整体状态")
    version: str = Field(..., description="版本")
    environment: str = Field(..., description="环境")
    database: str = Field(..., description="数据库状态")
    vector_store: str = Field(..., description="向量库状态")