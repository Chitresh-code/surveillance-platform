"""Bootstrap an operator account (docs/GAPS.md item 1): `uv run python -m api.create_operator <username> <password>`.

No self-service signup exists (operator management is docs/GAPS.md item 2, not built yet),
so this is the only way to create the first login.
"""

import sys

from common.db import session_scope
from common.ids import new_id
from common.models import Operator

from api.auth import hash_password


def main() -> None:
    if len(sys.argv) != 3:
        print("usage: uv run python -m api.create_operator <username> <password>")
        raise SystemExit(1)

    username, password = sys.argv[1], sys.argv[2]
    with session_scope() as session:
        session.add(Operator(id=new_id("op"), username=username, password_hash=hash_password(password)))
    print(f"created operator {username!r}")


if __name__ == "__main__":
    main()
