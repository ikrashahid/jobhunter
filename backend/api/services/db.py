import os
from supabase import create_client, Client
from dotenv import load_dotenv
from pathlib import Path

# Walk up until we find .env
_here = Path(__file__).resolve()
for _parent in _here.parents:
    _env = _parent / ".env"
    if _env.exists():
        load_dotenv(_env, override=True)
        break

for _parent in [Path(__file__).parent, Path(__file__).parent.parent,
                Path(__file__).parent.parent.parent]:
    _env = _parent / ".env"
    if _env.exists():
        load_dotenv(_env, override=True)
        break

_client: Client | None = None


def get_client() -> Client:
    global _client
    if _client is None:
        _client = create_client(
            os.getenv("SUPABASE_URL"),
            os.getenv("SUPABASE_KEY"),
        )
    return _client