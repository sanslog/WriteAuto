
from pydantic import BaseModel
import httpx
from fastapi import APIRouter


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
    测试 LLM API 连接
    """
    try:
        # 清理 URL
        baseurl = req.baseurl.rstrip('/')
        
        # 构建请求
        url = f"{baseurl}/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {req.api_key}"
        }
        body = {
            "model": req.model_name or "deepseek-chat",
            "messages": [{"role": "user", "content": "Say'Hi'"}],
            "max_tokens": 2
        }

        # 发送请求
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.post(url, json=body, headers=headers)
            
            # 直接返回结果
            return {
                "success": response.status_code == 200,
                "status_code": response.status_code,
                "data": response.json() if response.status_code == 200 else response.text
            }

    except Exception as e:
        return {
            "success": False,
            "status_code": response.status_code,
            "error": str(e)
        }