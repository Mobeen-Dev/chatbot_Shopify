import asyncio
from openai import DefaultAioHttpClient
from openai import AsyncOpenAI
from config import settings

async def main() -> None:
    async with AsyncOpenAI(
        api_key=settings.openai_api_key,
        http_client=DefaultAioHttpClient(),
    ) as client:
        chat_completion = await client.chat.completions.create(
            messages=[
                {
                    "role": "user",
                    "content": "Say this is a test",
                }
            ],
            model="gpt-4o",
        )
        print(chat_completion)
        print("\n\n")
        print(chat_completion.choices[0].message.content)


asyncio.run(main())