import argparse
import asyncio
import json
from pathlib import Path
from typing import Any

from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, VectorParams
from qdrant_client.models import PointStruct

from src.clients.llm import get_embedding
from src.settings import Settings


def parse_message(msg: dict[str, Any]) -> dict[str, Any]:
    text_parts: list[str] = []
    for part in msg.get("text", []):
        if isinstance(part, str):
            text_parts.append(part)
        elif isinstance(part, dict):
            text_parts.append(part.get("text", ""))
    text = "".join(text_parts)

    reactions: dict[str, int] = {}
    for reaction in msg.get("reactions", []):
        reaction_type = reaction["type"]
        if reaction_type == "emoji":
            name = reaction["emoji"]
        elif reaction_type == "custom_emoji":
            name = reaction["document_id"]
        elif reaction_type == "paid":
            name = "paid"
        else:
            name = reaction_type
        reactions[name] = reaction["count"]
    return {
        "from": msg.get("from"),
        "date": msg.get("date"),
        "text": text,
        "reactions": reactions,
    }


def load_messages(export_path: Path) -> list[dict[str, Any]]:
    with export_path.open("r", encoding="utf-8") as file:
        data = json.load(file)
    return data.get("messages", [])


async def main(export_path: Path) -> None:
    messages = load_messages(export_path)
    settings = Settings()

    all_messages = []
    for message in messages:
        cur_message = parse_message(message)
        if len("text") == 0:
            continue
        all_messages.append(cur_message)
    texts = [item["text"] for item in all_messages][:-1_000]

    embeddings = await get_embedding(
        text=texts,
        settings=settings,
    )

    client = QdrantClient(
        location=str(settings.qdrant_host),
    )

    points = [
        PointStruct(id=idx, vector=vector, payload=payload)
        for idx, (vector, payload) in enumerate(zip(embeddings, all_messages))
    ]

    if not client.collection_exists(settings.qdrant_collection):
        client.create_collection(
            settings.qdrant_collection,
            vectors_config=VectorParams(
                size=len(embeddings[0]), distance=Distance.COSINE
            ),
        )

    client.upsert(
        collection_name=settings.qdrant_collection,
        points=points,
    )
    print("Messages indexed into Qdrant.")


def get_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Index Telegram export into Qdrant.")
    parser.add_argument(
        "--export-path",
        type=Path,
        help="Path to the Telegram JSON export file.",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = get_args()
    asyncio.run(main(args.export_path))
