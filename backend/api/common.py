
from pydantic import BaseModel
from fastapi import APIRouter
from openai import AsyncOpenAI, APIStatusError

import logging


logger = logging.getLogger(__name__)


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
    if not (req.api_key and req.baseurl and req.model_name):
        return {
            "success": False,
            "status_code": 400,
            "error": "必要信息缺失",
        }
    logger.info("Testing LLM connection: base_url=%s, model=%s", req.baseurl, req.model_name)
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
        logger.warning("LLM connection test failed: status=%s, error=%s", e.status_code, e.message)
        return {
            "success": False,
            "status_code": e.status_code,
            "error": e.message,
        }
    except Exception as e:
        logger.exception("LLM connection test failed")
        return {
            "success": False,
            "status_code": 500,
            "error": str(e),
        }
