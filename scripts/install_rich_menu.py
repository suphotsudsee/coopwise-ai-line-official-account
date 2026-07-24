import json
import os
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
MENU_PATH = ROOT / "config" / "rich-menu.json"
IMAGE_PATH = ROOT / "assets" / "rich-menu.png"


def main() -> None:
    token = os.environ.get("LINE_CHANNEL_ACCESS_TOKEN")
    if not token:
        raise SystemExit("LINE_CHANNEL_ACCESS_TOKEN is required")
    if not IMAGE_PATH.exists():
        raise SystemExit(f"Rich menu image not found: {IMAGE_PATH}")
    if IMAGE_PATH.stat().st_size > 1_000_000:
        raise SystemExit("Rich menu image must be 1 MB or smaller")

    menu = json.loads(MENU_PATH.read_text(encoding="utf-8"))
    headers = {"Authorization": f"Bearer {token}"}

    with httpx.Client(timeout=30) as client:
        validation = client.post(
            "https://api.line.me/v2/bot/richmenu/validate",
            headers={**headers, "Content-Type": "application/json"},
            json=menu,
        )
        validation.raise_for_status()

        creation = client.post(
            "https://api.line.me/v2/bot/richmenu",
            headers={**headers, "Content-Type": "application/json"},
            json=menu,
        )
        creation.raise_for_status()
        rich_menu_id = creation.json()["richMenuId"]

        try:
            upload = client.post(
                f"https://api-data.line.me/v2/bot/richmenu/{rich_menu_id}/content",
                headers={**headers, "Content-Type": "image/png"},
                content=IMAGE_PATH.read_bytes(),
            )
            upload.raise_for_status()

            default = client.post(
                f"https://api.line.me/v2/bot/user/all/richmenu/{rich_menu_id}",
                headers=headers,
            )
            default.raise_for_status()
        except Exception:
            client.delete(
                f"https://api.line.me/v2/bot/richmenu/{rich_menu_id}",
                headers=headers,
            )
            raise

    print(json.dumps({"status": "installed", "richMenuId": rich_menu_id}))


if __name__ == "__main__":
    main()
