import inngest
from src.inngest.client import get_inngest_client

client = get_inngest_client()


@client.create_function(
    fn_id="demo-hello",
    trigger=inngest.TriggerEvent(event="demo/hello"),
)
def demo_hello(ctx: inngest.ContextSync) -> str:
    """No-provider smoke function for Inngest Dev Server verification."""
    _ = ctx
    return "ok"
