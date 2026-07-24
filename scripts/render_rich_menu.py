from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "assets" / "rich-menu.png"
WIDTH = 2500
HEIGHT = 1686

ITEMS = (
    ("คำนวณค่างวด", "สินเชื่อรายเดือน", (24, 112, 190), "฿"),
    ("ประเมินภาระหนี้", "DSR และเงินคงเหลือ", (21, 138, 127), "%"),
    ("คำนวณเงินปันผล", "จากทุนเรือนหุ้น", (91, 73, 175), "+"),
    ("ดอกเบี้ยเงินฝาก", "คำนวณตามจำนวนวัน", (13, 126, 145), "i"),
    ("สรุปรายการ", "รวมและค่าเฉลี่ย", (180, 83, 9), "#"),
    ("วิธีใช้งาน", "คำแนะนำและข้อควรทราบ", (71, 85, 105), "?"),
)


def font(size: int, *, bold: bool = False) -> ImageFont.FreeTypeFont:
    candidates = (
        Path("C:/Windows/Fonts/leelawdb.ttf" if bold else "C:/Windows/Fonts/LeelawUI.ttf"),
        Path(
            "/usr/share/fonts/truetype/noto/NotoSansThai-Bold.ttf"
            if bold
            else "/usr/share/fonts/truetype/noto/NotoSansThai-Regular.ttf"
        ),
        Path(
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
            if bold
            else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
        ),
    )
    for candidate in candidates:
        if candidate.exists():
            return ImageFont.truetype(str(candidate), size)
    raise RuntimeError("No supported Thai font found")


def main() -> None:
    image = Image.new("RGB", (WIDTH, HEIGHT), (240, 247, 250))
    draw = ImageDraw.Draw(image)
    title_font = font(78, bold=True)
    subtitle_font = font(44)
    icon_font = font(100, bold=True)

    for index, (title, subtitle, color, icon) in enumerate(ITEMS):
        row, column = divmod(index, 3)
        left = column * 833
        right = (column + 1) * 833 if column < 2 else WIDTH
        top = row * 843
        bottom = (row + 1) * 843

        margin = 32
        card = (left + margin, top + margin, right - margin, bottom - margin)
        draw.rounded_rectangle(
            card,
            radius=42,
            fill=(255, 255, 255),
            outline=(213, 225, 232),
            width=5,
        )
        draw.rectangle((card[0], card[1], card[0] + 18, card[3]), fill=color)

        center_x = (left + right) // 2
        icon_center_y = top + 260
        draw.ellipse(
            (center_x - 105, icon_center_y - 105, center_x + 105, icon_center_y + 105),
            fill=color,
        )
        icon_box = draw.textbbox((0, 0), icon, font=icon_font)
        draw.text(
            (center_x - (icon_box[2] - icon_box[0]) / 2, icon_center_y - 70),
            icon,
            font=icon_font,
            fill=(255, 255, 255),
        )

        title_box = draw.textbbox((0, 0), title, font=title_font)
        draw.text(
            (center_x - (title_box[2] - title_box[0]) / 2, top + 430),
            title,
            font=title_font,
            fill=(23, 41, 54),
        )
        subtitle_box = draw.textbbox((0, 0), subtitle, font=subtitle_font)
        draw.text(
            (center_x - (subtitle_box[2] - subtitle_box[0]) / 2, top + 555),
            subtitle,
            font=subtitle_font,
            fill=(91, 111, 124),
        )

        pill = (center_x - 145, top + 675, center_x + 145, top + 755)
        draw.rounded_rectangle(pill, radius=40, fill=color)
        action = "แตะเพื่อใช้งาน"
        action_font = font(37, bold=True)
        action_box = draw.textbbox((0, 0), action, font=action_font)
        draw.text(
            (center_x - (action_box[2] - action_box[0]) / 2, top + 688),
            action,
            font=action_font,
            fill=(255, 255, 255),
        )

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    image.save(OUTPUT, "PNG", optimize=True)
    print(f"Rendered {OUTPUT} ({OUTPUT.stat().st_size:,} bytes)")


if __name__ == "__main__":
    main()
