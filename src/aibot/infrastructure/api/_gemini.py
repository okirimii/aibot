from google import genai
from google.genai import types

from src.aibot.core.entities.chat import ChatHistory, ChatMessage

from ._params import GeminiParams

_client = genai.Client()


async def generate_gemini_response(
    messages: list[ChatMessage],
    system: str,
    model_params: GeminiParams,
) -> ChatMessage:
    convo = ChatHistory(chat_msgs=[*messages, ChatMessage(role="assistant")]).render_messages()
    contents = "\n".join([msg["content"] for msg in convo if msg["content"]])
    response = _client.models.generate_content(
        model=model_params.model,
        config=types.GenerateContentConfig(
            system_instruction=system,
            temperature=model_params.temperature,
            top_p=model_params.top_p,
            thinking_config=types.ThinkingConfig(thinking_budget=0),
        ),
        contents=contents,
    )

    return ChatMessage(role="assistant", content=response.text)
