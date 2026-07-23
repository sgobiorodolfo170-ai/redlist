from typing import List, Literal, Optional, TypedDict, Union

Role = Literal["user", "assistant", "system"]


class TextContent(TypedDict):
    type: Literal["text"]
    text: str


class ImageUrlContent(TypedDict):
    type: Literal["image_url"]
    image_url: dict


ContentPart = Union[TextContent, ImageUrlContent]


class MessageDict(TypedDict, total=False):
    role: Role
    content: Union[str, List[ContentPart]]
    name: str


class ModelConfigDict(TypedDict, total=False):
    name: str
    api_url: str
    api_key: str
    model_name: str
    temperature: float
    max_tokens: int
    top_p: float


class Delta(TypedDict, total=False):
    content: str
    role: str


class Choice(TypedDict, total=False):
    delta: Delta
    index: int
    finish_reason: Optional[str]


class StreamResponse(TypedDict, total=False):
    choices: List[Choice]
    model: str
    object: str
    created: int
    id: str
