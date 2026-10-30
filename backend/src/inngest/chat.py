from sqlmodel import Session

import inngest
from src.config import get_settings
from src.db.session import engine
from src.inngest.client import get_inngest_client
from src.providers.runtime import get_embedding_provider, get_vector_store
from src.services import chat_pipeline

client = get_inngest_client()


def _session() -> Session:
    return Session(engine)


@client.create_function(
    fn_id="chat-message-requested",
    trigger=inngest.TriggerEvent(event="chat/message.requested.v1"),
    concurrency=[
        inngest.Concurrency(limit=2, key="event.data.owner_id"),
    ],
)
def chat_message_requested(ctx: inngest.ContextSync) -> dict:
    """Embed + search only. Generation streams live on the FastAPI SSE request."""
    data = ctx.event.data
    owner_id = str(data["owner_id"])
    assistant_message_id = str(data["assistant_message_id"])
    question = str(data["question"])

    settings = get_settings()
    embeddings = get_embedding_provider()
    vectors = get_vector_store()

    def embed_and_search() -> dict:
        with _session() as session:
            return chat_pipeline.step_embed_and_search(
                session,
                settings=settings,
                embeddings=embeddings,
                vectors=vectors,
                owner_id=owner_id,
                assistant_message_id=assistant_message_id,
                question=question,
            )

    search_result = ctx.step.run("embed-and-search", embed_and_search)
    return {
        "assistant_message_id": assistant_message_id,
        "search": search_result,
    }
