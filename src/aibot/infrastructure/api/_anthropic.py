import anthropic

from src.aibot.core.entities.chat import ChatHistory, ChatMessage

from ._params import ClaudeParams

_client = anthropic.Anthropic()


async def generate_anthropic_response(
    messages: list[ChatMessage],
    system: str,
    model_params: ClaudeParams,
) -> ChatMessage:
    convo = ChatHistory(chat_msgs=[*messages, ChatMessage(role="assistant")]).render_messages()
    response = _client.messages.create(
        model=model_params.model,
        messages=convo,
        max_tokens=model_params.max_tokens,
        system=system,
        temperature=model_params.temperature,
        top_p=model_params.top_p,
    )

    return ChatMessage(role="assistant", content=response.content[0].text)
