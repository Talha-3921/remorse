import os
from openai import OpenAI

client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

try:
    client.images.generate(
        model="gpt-image-1", prompt="a red circle", size="1024x1024"
    )
    print("IMAGE_MODEL=gpt-image-1")
except Exception as exc:
    print(f"IMAGE_MODEL=dall-e-2")
    print(type(exc).__name__)
