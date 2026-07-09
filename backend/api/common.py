
from pydantic import BaseModel
from fastapi import APIRouter
from openai import AsyncOpenAI, APIStatusError


router = APIRouter(prefix="/api", tags=["common"])

# models:
class PingRequest(BaseModel):
    api_key: str
    baseurl: str
    model_name: str


# routers:
@router.post("/pingOpenAI")
async def ping_OpenAI(req: PingRequest):
    """
    测试 LLM API 连接（通过 OpenAI SDK）
    """
    if not req.api_key or req.baseurl or req.model_name:
        return {
            "success": False,
            "status_code": 400,
            "error": "必要信息缺失",
        }
    try:
        client = AsyncOpenAI(
            api_key=req.api_key,
            base_url=req.baseurl.rstrip('/'),
            max_retries=0,
            timeout=10.0,
        )
        resp = await client.chat.completions.create(
            model=req.model_name,
            messages=[{"role": "user", "content": "Say'Hi'"}],
            max_tokens=1000,
        )
        return {
            "success": True,
            "status_code": 200,
            "data": resp.model_dump(),
        }
    except APIStatusError as e:
        return {
            "success": False,
            "status_code": e.status_code,
            "error": e.message,
        }
    except Exception as e:
        return {
            "success": False,
            "status_code": 500,
            "error": str(e),
        }