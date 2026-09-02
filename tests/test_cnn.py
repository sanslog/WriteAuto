from openai import OpenAI

client = OpenAI(
    # 若没有配置环境变量，请用百炼API Key将下行替换为：api_key="sk-xxx"
    api_key="sk-ws-H.RYPIEPR.eShW.MEQCICe5K3y_IRsR3Lypzi3_ZPJmSxwevth5enTJITadw1-dAiA47KFY2GTiLICjbBgmcubmEnWeleizV0kZuuBcJ2b88A",
    base_url=f"https://ws-5v6xssegbg6k1zof.cn-beijing.maas.aliyuncs.com/compatible-mode/v1",
)

completion = client.chat.completions.create(
    # 模型列表：https://help.aliyun.com/zh/model-studio/getting-started/models
    model="qwen-plus",
    messages=[
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "say'Hi'"},
    ]
)
print(completion.model_dump_json())