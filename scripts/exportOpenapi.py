from __future__ import annotations

import json
from pathlib import Path

from helmet_workbench.api.app import createApp
from helmet_workbench.config import Settings


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    output = root / "docs" / "api" / "openapi.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    app = createApp(Settings(testing=True))
    output.write_text(
        json.dumps(app.openapi(), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(output)


if __name__ == "__main__":
    main()
