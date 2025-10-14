import aiohttp
import fastapi
from typing import Optional

app = fastapi.FastAPI()

@app.get('/')
async def root():
    return {'message': 'Hello World'}

@app.get('/items/{item_id}')
async def read_item(item_id: int, q: Optional[str] = None):
    return {'item_id': item_id, 'q': q}