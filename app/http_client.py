import aiohttp
import asyncio
import json
import logging
from typing import Optional, Dict, Any
from decimal import Decimal

logger = logging.getLogger(__name__)

class UltraFastHTTPClient:
    def __init__(self):
        # Connection pooling otimizado
        connector = aiohttp.TCPConnector(
            limit=100,  # Max connections
            limit_per_host=50,  # Max per host
            ttl_dns_cache=300,  # DNS cache
            use_dns_cache=True,
            keepalive_timeout=30,
            enable_cleanup_closed=True,
            force_close=False
        )
        
        # Mais agressivo: 400ms totais (100ms connect + 300ms read)
        self.timeout = aiohttp.ClientTimeout(
            total=0.4,  # 400ms total
            connect=0.1,  # 100ms para conectar
            sock_read=0.3  # 300ms para ler
        )
        
        self.session = aiohttp.ClientSession(
            connector=connector,
            # DO NOT set a global timeout on the session, it causes issues with background tasks
            skip_auto_headers=['User-Agent'],  # Reduz overhead
            raise_for_status=False,  # Handle manually
            json_serialize=json.dumps  # Use standard json
        )
        
        # Pre-allocate common headers
        self.headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
    
    async def post_fast(self, url: str, data: dict) -> Optional[dict]:
        """Ultra-fast POST request with optimized JSON handling"""
        try:
            # JSON serialization otimizada
            json_data = json.dumps(data, separators=(',', ':'))
            
            async with self.session.post(
                url,
                data=json_data,
                headers=self.headers,
                compress=False,  # Desabilita compressão para reduzir CPU
                timeout=self.timeout
            ) as resp:
                if resp.status == 200:
                    return await resp.json()
                else:
                    logger.warning(f"HTTP {resp.status} from {url}")
                    return None
                    
        except asyncio.TimeoutError:
            logger.warning(f"Timeout calling {url}")
            return None
        except Exception as e:
            logger.error(f"Error calling {url}: {e}")
            return None
    
    async def get_fast(self, url: str) -> Optional[dict]:
        """Ultra-fast GET request"""
        try:
            async with self.session.get(
                url,
                headers=self.headers,
                compress=False,
                timeout=self.timeout
            ) as resp:
                if resp.status == 200:
                    return await resp.json()
                else:
                    logger.warning(f"HTTP {resp.status} from {url}")
                    return None
                    
        except asyncio.TimeoutError:
            logger.warning(f"Timeout calling {url}")
            return None
        except Exception as e:
            logger.error(f"Error calling {url}: {e}")
            return None
    
    async def close(self):
        """Close the session"""
        if self.session:
            await self.session.close()

# Global HTTP client instance - will be initialized on app startup
http_client: Optional[UltraFastHTTPClient] = None 