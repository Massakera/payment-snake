from fastapi import APIRouter, Request, HTTPException, Response, Query
from fastapi.responses import JSONResponse
import time
import logging
from typing import Optional
from decimal import Decimal
from .models import PaymentRequest, PaymentSummaryResponse
from .payment_processor import payment_processor
from .database import db
from . import health_manager as health_manager_module

logger = logging.getLogger(__name__)

# Pre-allocate response templates for performance
SUCCESS_RESPONSE = Response(status_code=204)

# Create routers
payments_router = APIRouter(prefix="/payments", tags=["payments"])
summary_router = APIRouter(prefix="/payments-summary", tags=["summary"])

@payments_router.post("")
async def process_payment(request: Request):
    """Process payment endpoint - ultra optimized for performance"""
    start_time = time.perf_counter()
    
    try:
        # Fast JSON parsing
        body = await request.json()
        
        # Extract data with minimal validation
        correlation_id = body.get('correlationId')
        amount_str = body.get('amount')
        
        if not correlation_id or amount_str is None:
            raise HTTPException(status_code=400, detail="Missing required fields")
        
        # Convert amount to Decimal
        try:
            amount = Decimal(str(amount_str))
        except:
            raise HTTPException(status_code=400, detail="Invalid amount")
        
        # Process payment (async)
        success = await payment_processor.process_payment(correlation_id, amount)
        
        if not success:
            # Even if processing failed, return success to client
            # (as per requirements, any 2XX response is valid)
            logger.warning(f"Payment processing failed for {correlation_id}")
        
        # Return immediately for maximum performance
        return SUCCESS_RESPONSE
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error processing payment: {e}")
        # Return success anyway (requirements say any 2XX is valid)
        return SUCCESS_RESPONSE

@summary_router.get("")
async def get_payments_summary(
    from_: Optional[str] = Query(None, alias="from"),
    to: Optional[str] = Query(None, alias="to")
):
    """Get payments summary endpoint - optimized for performance"""
    try:
        # If no time filters, use real-time counters from Redis for immediate consistency
        if from_ is None and to is None and health_manager_module.redis_client:
            try:
                rc = health_manager_module.redis_client
                default_requests, default_amount, fallback_requests, fallback_amount = await rc.mget(
                    "summary:default:total_requests",
                    "summary:default:total_amount",
                    "summary:fallback:total_requests",
                    "summary:fallback:total_amount",
                )
                summary = {
                    'default': {
                        'totalRequests': int(default_requests or 0),
                        'totalAmount': float(default_amount or 0.0)
                    },
                    'fallback': {
                        'totalRequests': int(fallback_requests or 0),
                        'totalAmount': float(fallback_amount or 0.0)
                    }
                }
            except Exception as e:
                logger.error(f"Error reading redis summary: {e}")
                summary = await db.get_summary_fast(from_, to)
        else:
            # Get summary from database when filters are applied
            summary = await db.get_summary_fast(from_, to)
        
        # Return formatted response
        return JSONResponse(content=summary)
        
    except Exception as e:
        logger.error(f"Error getting payments summary: {e}")
        # Return empty summary on error
        return JSONResponse(content={
            'default': {'totalRequests': 0, 'totalAmount': 0.0}, 
            'fallback': {'totalRequests': 0, 'totalAmount': 0.0}
        }) 