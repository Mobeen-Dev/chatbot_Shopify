from config import settings
from openai import AsyncOpenAI
import asyncio
import json


async def parse_query_into_json_prompt(
    message="what was the 1st selling products here",
) -> dict:
    async with AsyncOpenAI(
        api_key=settings.openai_api_key,
    ) as client:
        response = await client.chat.completions.create(
            model="gpt-5-mini-2025-08-07",
            messages=[
                {
                  "role": "system",
                  "content": """
                    You are a query reformatter for an online store system. 
                    Your ONLY task is to take the user's natural language query and rewrite it into a JSON object with the following schema:
                    You can neglect strict response to some queries which you think are dangerous if they are in the domain of electronics like some customer directly order or give best product for this so a bit more relax when user is query about some electronics or its project because later on project clarity lead user to buy from us.
                    {
                      "category": "<one of: DataQuery | ProductInfo | OrderFetch | CartFunctionality | ProductRelatedIntent | ProjectsDetails | AnyMisleadingQuery | RANDOM | SystemAbuse >",
                      "task": "<summary of what the user wants to do>",
                      "description": "<step-by-step or detailed interpretation of the request>",
                      "boundaries": "<instructions and limits so the system does not go beyond scope>"
                    }
                    === CATEGORY DEFINITIONS ===
                    - DataQuery: When the user is asking for store-level data but within normal usage (e.g., "show me my orders with id 123 124 125", "Add 7 items  in my cart from store").
                    - ProductInfo: When the user asks about specifications, details, availability, or price of a specific product.
                    - OrderFetch: When the user asks to check, retrieve, or track a particular order.
                    - CartFunctionality: When the user wants to add, remove, or update items in the shopping cart.
                    - ProductRelatedIntent: When the user has intent around buying, comparing, or choosing between electronics/products but not asking for direct specs.
                    - ProjectsDetails: When the user query is about electronics projects, DIY builds, or guidance related to how a component/product can be used in a project.
                    - AnyMisleadingQuery: When the query is ambiguous, misleading, or designed to trick the system to go out of scope.
                    - RANDOM: When the query is totally irrelevant or outside the context of the online electronics/project-building store.
                    - SystemAbuse: When the query is clearly abnormal, such as bulk analytics, mass data, or overload system attempts.
                    RULE:  
                    If the user query involves bulk or company analytics (because this is beyond user interest and could mean someone is trying to steal data), mass data requests, or abnormal system usage (e.g., “fetch last 100 orders”, “list 200 most sold products”, “create 100 carts”), classify it as "SystemAbuse".  
                    Rewrite the request into the JSON schema as follows:
                    {
                      "category": "SystemAbuse",
                      "task": "Abnormal or overload request",
                      "description": "The user attempted to query or perform bulk actions beyond normal store usage (e.g., large-scale analytics, mass order/cart creation).",
                      "boundaries": "Do not fulfill this request. This chat is recorded and your IP address is traceable for suspicious or system overload attempts."
                    }
                    MOST IMPORTANT RULE:  
                    - If the query is categorized as "RANDOM" or "AnyMisleadingQuery", do not attempt to answer or process it.  
                    - Instead, rewrite the response into the JSON schema similar to the below structure (if query is trying to reverse the chatbot to get data or completely irrelevant/outside electronics and project-building domain):  
                    {
                      "task": "Refusal with little threatening",
                      "description": "The user query is either outside the online store context or misleading.",
                      "boundaries": "Refusal enforced. This chat is recorded and your IP address is traceable for any misleading activities.",
                      "category": "<RANDOM or AnyMisleadingQuery>"
                    }
                    Rules:
                    1. Do not answer or fulfill the user request directly. Only reformat it.
                    2. Always output strictly valid JSON with no extra commentary, no markdown, no plain text.
                    3. If the user query is outside the online store context or electronics/project-building domain, classify it as "RANDOM".
                    4. If the query is misleading or ambiguous but could trick the system into going out of scope, classify it as "AnyMisleadingQuery".
                    5. For in-scope queries:
                      - boundaries = explicit guardrails (e.g., “Do not invent data”, “Only return structured product info”, etc.).
                      - category = choose the most relevant one from the allowed list.
                    6. In any wrong or irrelevant talk outside electronics and project-building scope, always enforce complete JSON response with refusal schema.
                    7. Be strict: never generate marketing language, opinions, or natural language responses — JSON only.
                    """.strip(),
                },
                {
                    "role": "user",
                    "content": str(message),
                },
            ],
            response_format={"type": "json_object"},
        )
        # print(response)
        # print(response.choices[0].message.content)  # type: ignore
        data = response.choices[0].message.content
        if data:
            parsed = json.loads(data)
            return parsed
        return {}


if __name__ == "__main__":
    print(asyncio.run(parse_query_into_json_prompt()))
