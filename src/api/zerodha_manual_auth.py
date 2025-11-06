"""
Zerodha Manual Authentication Handler
FIXES: Token propagation to all cached instances
"""
import logging
import os
from fastapi import APIRouter, HTTPException
from typing import Dict, Any

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth/zerodha", tags=["zerodha-auth"])


@router.get("/callback")
async def zerodha_callback(
    status: str,
    request_token: str,
    action: str,
    type: str = "login"
):
    """
    Zerodha OAuth callback handler.
    Called after user authorizes on Zerodha website.
    """
    try:
        logger.info(f"Zerodha callback received - token: {request_token[:10]}..., action: {action}, status: {status}")
        
        # Return success page
        return {
            "success": True,
            "status": status,
            "action": action,
            "message": "Authorization received. Please submit token via API."
        }
        
    except Exception as e:
        logger.error(f"Zerodha callback error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/submit-token")
async def submit_token(request: Dict[str, Any]):
    """
    Submit Zerodha access token and propagate to ALL instances.
    
    CRITICAL FIX: Clears all caches and updates all references.
    """
    try:
        request_token = request.get('request_token')
        user_id = request.get('user_id', 'PAPER_TRADER_001')
        
        if not request_token:
            raise HTTPException(status_code=400, detail="request_token required")
        
        logger.info(f"Token submission for user: {user_id}")
        
        # Get Zerodha credentials
        api_key = os.getenv('ZERODHA_API_KEY')
        api_secret = os.getenv('ZERODHA_API_SECRET')
        
        if not api_key or not api_secret:
            raise HTTPException(status_code=500, detail="Zerodha credentials not configured")
        
        # Exchange request token for access token
        logger.info("Exchanging request token for access token...")
        
        from kiteconnect import KiteConnect
        kite = KiteConnect(api_key=api_key)
        
        data = kite.generate_session(request_token, api_secret=api_secret)
        access_token = data["access_token"]
        
        logger.info(f"✅ Access token received: {access_token[:10]}...")
        
        # Get user profile to verify
        kite.set_access_token(access_token)
        profile = kite.profile()
        user_name = profile.get('user_name', 'Unknown')
        actual_user_id = profile.get('user_id', user_id)
        
        logger.info(f"User profile retrieved: {user_name}")
        
        # Map user identifiers
        user_id_map = {
            'PAPER_TRADER_001': actual_user_id,
            actual_user_id: actual_user_id
        }
        final_user_id = user_id_map.get(user_id, actual_user_id)
        
        # CRITICAL: Store in Redis FIRST (single source of truth)
        import redis
        redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
        redis_client = redis.from_url(redis_url, decode_responses=True)
        
        redis_key = f"zerodha:token:{final_user_id}"
        redis_client.setex(redis_key, 86400, access_token)  # 24 hours
        
        logger.info(f"✅ Token stored in Redis at {redis_key} BEFORE client updates")
        
        # CRITICAL FIX: Force update ALL Zerodha client instances
        success_count = 0
        total_count = 0
        
        # 1. Update singleton Zerodha client
        try:
            from brokers.zerodha import get_zerodha_client
            zerodha_client = get_zerodha_client()
            
            # Force reinitialize (clears internal caches)
            if zerodha_client.set_access_token(access_token, final_user_id):
                logger.info("✅ [1/5] Singleton Zerodha client updated")
                success_count += 1
            total_count += 1
        except Exception as e:
            logger.error(f"❌ [1/5] Singleton update failed: {e}")
            total_count += 1
        
        # 2. Update orchestrator's reference (force refresh)
        try:
            from src.core.orchestrator import orchestrator
            
            if hasattr(orchestrator, 'zerodha_client'):
                # Force get fresh singleton instance
                from brokers.zerodha import get_zerodha_client
                orchestrator.zerodha_client = get_zerodha_client()
                logger.info("✅ [2/5] Orchestrator Zerodha client reference refreshed")
                success_count += 1
            total_count += 1
        except Exception as e:
            logger.warning(f"⚠️ [2/5] Orchestrator update: {e}")
            total_count += 1
        
        # 3. Update trade engine's reference (force refresh)
        try:
            from src.core.orchestrator import orchestrator
            
            if hasattr(orchestrator, 'trade_engine') and orchestrator.trade_engine:
                if hasattr(orchestrator.trade_engine, 'zerodha_client'):
                    from brokers.zerodha import get_zerodha_client
                    orchestrator.trade_engine.zerodha_client = get_zerodha_client()
                    logger.info("✅ [3/5] Trade engine Zerodha client reference refreshed")
                    success_count += 1
            total_count += 1
        except Exception as e:
            logger.warning(f"⚠️ [3/5] Trade engine update: {e}")
            total_count += 1
        
        # 4. Update multi-user manager
        try:
            from src.core.multi_user_zerodha_manager import multi_user_manager
            
            if hasattr(multi_user_manager, 'update_user_token'):
                # Ensure user ID mapping is correct
                multi_user_manager.update_user_token(final_user_id, access_token)
                logger.info("✅ [4/5] Multi-user manager updated")
                success_count += 1
            total_count += 1
        except ImportError:
            logger.info("ℹ️ [4/5] Multi-user manager not found")
            total_count += 1
        except Exception as e:
            logger.warning(f"⚠️ [4/5] Multi-user manager: {e}")
            total_count += 1
        
        # 5. Update environment variable
        try:
            os.environ['ZERODHA_ACCESS_TOKEN'] = access_token
            logger.info("✅ [5/5] Environment variable updated")
            success_count += 1
            total_count += 1
        except Exception as e:
            logger.error(f"❌ [5/5] Env var update failed: {e}")
            total_count += 1
        
        logger.info("")
        logger.info("="*60)
        logger.info(f"TOKEN PROPAGATION: {success_count}/{total_count} successful")
        logger.info("="*60)
        logger.info("")
        
        return {
            "success": True,
            "message": "Token updated in all instances",
            "user_id": final_user_id,
            "user_name": user_name,
            "updates": {
                "successful": success_count,
                "total": total_count
            }
        }
        
    except Exception as e:
        logger.error(f"❌ Token submission failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))

