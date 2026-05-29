from fastapi import FastAPI, WebSocket
from pydantic import BaseModel
from datetime import datetime

app = FastAPI(title='Bonds-eye')
clients = []
readings = []

class Reading(BaseModel):
    node_id:str
    rssi:int
    variance:float=0
    confidence:float=0

@app.get('/health')
def health():
    return {'status':'ok','ts':datetime.utcnow().isoformat()}

@app.post('/telemetry')
async def telemetry(r:Reading):
    payload=r.model_dump()
    readings.append(payload)
    for ws in list(clients):
        try:
            await ws.send_json(payload)
        except:
            pass
    return {'accepted':True}

@app.get('/readings/recent')
def recent():
    return readings[-100:]

@app.websocket('/ws/live')
async def live(ws:WebSocket):
    await ws.accept()
    clients.append(ws)
    try:
        while True:
            await ws.receive_text()
    except:
        pass
