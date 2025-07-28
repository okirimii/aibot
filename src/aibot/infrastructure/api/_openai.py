from openai import OpenAI

from src.aibot.core.entities.chat import ChatHistory, ChatMessage

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


async def get_openai_moderation_result(content: str) -> dict:
    """Get detailed moderation results from OpenAI.

    Parameters
    ----------
    content : str
        Content to moderate

    Returns
    -------
    dict
        Detailed moderation result including categories and scores
    """
    moderation_response = _client.moderations.create(
        model="omni-moderation-latest",
        input=content,
    )

    # Convert to dictionary for storage and analysis
    return {
        "id": moderation_response.id,
        "model": moderation_response.model,
        "results": [
            {
                "flagged": result.flagged,
                "categories": {
                    "sexual": result.categories.sexual,
                    "sexual/minors": result.categories.sexual_minors,
                    "harassment": result.categories.harassment,
                    "harassment/threatening": result.categories.harassment_threatening,
                    "hate": result.categories.hate,
                    "hate/threatening": result.categories.hate_threatening,
                    "illicit": result.categories.illicit,
                    "illicit/violent": result.categories.illicit_violent,
                    "self-harm": result.categories.self_harm,
                    "self-harm/intent": result.categories.self_harm_intent,
                    "self-harm/instructions": result.categories.self_harm_instructions,
                    "violence": result.categories.violence,
                    "violence/graphic": result.categories.violence_graphic,
                },
                "category_scores": {
                    "sexual": result.category_scores.sexual,
                    "sexual/minors": result.category_scores.sexual_minors,
                    "harassment": result.category_scores.harassment,
                    "harassment/threatening": result.category_scores.harassment_threatening,
                    "hate": result.category_scores.hate,
                    "hate/threatening": result.category_scores.hate_threatening,
                    "illicit": result.category_scores.illicit,
                    "illicit/violent": result.category_scores.illicit_violent,
                    "self-harm": result.category_scores.self_harm,
                    "self-harm/intent": result.category_scores.self_harm_intent,
                    "self-harm/instructions": result.category_scores.self_harm_instructions,
                    "violence": result.category_scores.violence,
                    "violence/graphic": result.category_scores.violence_graphic,
                },
                "category_applied_input_types": getattr(
                    result,
                    "category_applied_input_types",
                    {},
                ),
            }
            for result in moderation_response.results
        ],
    }
