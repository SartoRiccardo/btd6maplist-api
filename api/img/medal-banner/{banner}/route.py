import asyncio
import os.path
from aiohttp import web
import http
import io
from PIL import Image, ImageFont, ImageDraw
import src.http

BANNER_SIZE = (1536, 192)
MEDAL_SIZE = 128
MEDAL_SLOTS = 8
TEXT_POS_REL = (-10, -10)
LUCKIEST_GUY = ImageFont.truetype(os.path.join("bin", "LuckiestGuy-Regular.ttf"), 60)


async def get(request: web.Request) -> web.Response:
    banner = request.match_info["banner"]
    keys = ["wins", "black_border", "no_geraldo", "lccs"]
    medals = {}
    for k in keys:
        if k not in request.query or \
                not request.query[k].isnumeric():
            return web.Response(status=http.HTTPStatus.BAD_REQUEST)
        medals[k] = int(request.query[k])

    async with src.http.http.get(f"https://static-api.nkstatic.com/appdocs/4/assets/opendata/{banner}") as resp:
        if not resp.ok:
            return web.Response(status=http.HTTPStatus.BAD_REQUEST)
        image = await resp.read()

    image = await asyncio.to_thread(generate_image, io.BytesIO(image), medals)

    return web.Response(
        body=image.getvalue(),
        content_type="image/png",
    )


def generate_image(banner: io.BytesIO, medals: dict) -> io.BytesIO:
    unused_space = BANNER_SIZE[0] - MEDAL_SIZE * MEDAL_SLOTS
    padding = unused_space // (MEDAL_SLOTS+1)

    base_img = Image.open(banner).convert("RGB")
    width, eight = base_img.size
    if width != BANNER_SIZE[0]:
        base_img = base_img.resize(BANNER_SIZE)
    canvas = ImageDraw.Draw(base_img)

    medal_x = padding
    medal_y = (BANNER_SIZE[1]-MEDAL_SIZE) // 2
    for key in medals:
        if medals[key] <= 0:
            continue
        medal_img = Image.open(os.path.join("bin", "img", f"medal_{key}.png")).convert("RGBA")
        Image.Image.paste(base_img, medal_img, (medal_x, medal_y), mask=medal_img)
        canvas.text(
            (medal_x + MEDAL_SIZE + TEXT_POS_REL[0], medal_y + MEDAL_SIZE + TEXT_POS_REL[1]),
            str(medals[key]),
            font=LUCKIEST_GUY,
            fill=(255, 255, 255),
            stroke_fill=(0, 0, 0),
            stroke_width=6,
            anchor="mm",
        )

        medal_x += padding + MEDAL_SIZE

    stream = io.BytesIO()
    base_img.save(stream, format="PNG")
    return stream
