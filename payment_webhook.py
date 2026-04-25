from fastapi import APIRouter, Request

router = APIRouter()


@router.post("/payment/callback_uat1.1")
async def razorpay_callback(request: Request):

    data = await request.json()

    status = data.get("payload", {}).get("payment", {}).get("entity", {}).get("status")
    order_id = data.get("payload", {}).get("payment_link", {}).get("entity", {}).get("reference_id")

    # You must store session/order mapping separately (future improvement)

    if status == "captured":
        # TODO: fetch order from DB/session
        print("Payment Success:", order_id)

    else:
        print("Payment Failed:", order_id)

    return {"status": "ok"}
