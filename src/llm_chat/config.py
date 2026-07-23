from typing import Optional
from urllib.parse import urlparse

from pydantic import BaseModel, Field, field_validator


class ModelConfig(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, description="配置显示名称")
    api_url: str = Field(..., min_length=5, description="API 接口地址，兼容 OpenAI 格式")
    api_key: str = Field(..., min_length=8, description="API 密钥")
    model_name: str = Field(..., min_length=1, description="模型名称")
    temperature: Optional[float] = Field(default=None, ge=0, le=2)
    max_tokens: Optional[int] = Field(default=None, ge=1, le=32768)
    top_p: Optional[float] = Field(default=None, ge=0, le=1)

    @field_validator("api_url")
    @classmethod
    def validate_api_url(cls, v: str) -> str:
        v = v.rstrip("/")
        parsed = urlparse(v)
        if parsed.scheme not in ("http", "https"):
            raise ValueError(f"接口地址必须以 http:// 或 https:// 开头: {v}")
        if not parsed.netloc:
            raise ValueError(f"接口地址格式错误，缺少域名: {v}")
        return v

    @field_validator("api_key")
    @classmethod
    def validate_api_key(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 8:
            raise ValueError("API Key 长度不足，请检查")
        return v

    def to_dict(self) -> dict:
        return self.model_dump(exclude_none=True)
