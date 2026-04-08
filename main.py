from fastapi import FastAPI, Request
from fastapi.responses import Response

app = FastAPI()

@app.get("/")
def root():
    return {"status": "running"}

@app.post("/webhook")
async def whatsapp_webhook(request: Request):
    data = await request.form()
    user_msg = data.get("Body", "").lower()

    if "hi" in user_msg or "menu" in user_msg:
        reply = "Welcome to HotStuffCafe! Type 'menu' to see options."
    else:
        reply = "Got your message! More features coming soon."

    twiml = f"""
    <Response>
        <Message>{reply}</Message>
    </Response>
    """

    return Response(content=twiml, media_type="application/xml")
