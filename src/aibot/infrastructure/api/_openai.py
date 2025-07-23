from openai import OpenAI

from aibot.core.entities.chat import ChatHistory, ChatMessage

from ._params import GPTParams

_client = OpenAI()


async def generate_openai_response(
    messages: list[ChatMessage],
    system: str,
    model_params: GPTParams,
) -> ChatMessage:
    convo = ChatHistory(chat_msgs=[*messages, ChatMessage(role="assistant")]).render_messages()
    full_prompt = [{"role": "developer", "content": system}, *convo]
    response = _client.chat.completions.create(
        model=model_params.model,
        messages=full_prompt,
        max_tokens=model_params.max_tokens,
        temperature=model_params.temperature,
        top_p=model_params.top_p,
    )

    return ChatMessage(role="assistant", content=response.choices[0].message.content)
