import asyncio
import logging
import os
from pathlib import Path
from .run_ai_on_images import run_ai_on_image
from .upload_result import uploadResult
from web3 import AsyncWeb3, WebSocketProvider, HTTPProvider
from web3.utils.subscriptions import LogsSubscription, LogsSubscriptionContext
from web3._utils.events import get_event_data
from .send_notification_to_server import sendNotification
from dotenv import load_dotenv
from web3 import Web3

# Get absolute path of .env file inside worker/
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
dotenv_path = os.path.join(BASE_DIR, ".env")

# Load the .env file
load_dotenv(dotenv_path)


# Your contract address
CONTRACT_ADDRESS = os.getenv('CONTRACT_ADDRESS')
abi = os.getenv('ABI')

# Provider configurations
PROVIDERS = {
    "wss_provider_1": os.getenv('WSS_PROVIDER_1'),
    "wss_provider_2":os.getenv('WSS_PROVIDER_2'),
}

async def test_provider(provider_url, is_websocket=True):
    """Test if a provider is working"""
    try:
        if is_websocket:
            w3 = await AsyncWeb3(WebSocketProvider(provider_url))
        else:
            w3 = AsyncWeb3(HTTPProvider(provider_url))
        
        # Test basic connectivity
        block_number = await w3.eth.block_number
        print(f"Provider {provider_url} is working. Latest block: {block_number}")
        return True
    except Exception as e:
        print(f"Provider {provider_url} failed: {e}")
        return False

async def log_handler(handler_context: LogsSubscriptionContext) -> None:
    try:
        log = handler_context.result
        event_abi = {
        "anonymous":False,"inputs":[{"indexed":False,"internalType":"address","name":"_user","type":"address"},{"indexed":False,"internalType":"string","name":"imageUrl","type":"string"}],"name":"ImageSubmitted","type":"event"
        }
        w3 = handler_context.async_w3
        decoded = get_event_data(w3.codec, event_abi, log)
        urls = decoded["args"]["imageUrl"].split("$$$")
        print("New ImageSubmitted Event:")
        print(f"User: {decoded['args']['_user']}")
        print(f"URL: {decoded['args']['imageUrl']}")
        print(f"Transaction Hash: {log['transactionHash'].hex() if hasattr(log['transactionHash'], 'hex') else log['transactionHash']}")
        user = decoded["args"]["_user"]
        for url in urls:
            print(f"Running AI on image: {url}")
            result = run_ai_on_image(url)
            print(f"AI Result: {result}")
            uploadResult(url,result)
            web3 = Web3(Web3.HTTPProvider(os.getenv('HTTP_PROVIDER_1')))
            if not web3.is_connected():
                print("Failed to connect to Ethereum network")
                return False
            
            print("Connected to Ethereum network")
        
            # Get contract instance
            contract = web3.eth.contract(address=CONTRACT_ADDRESS, abi=abi)
            print(f"Contract loaded at address: {CONTRACT_ADDRESS}")
        
            # Get farmer info from blockchain
            print("Fetching farmer information from blockchain...")
            farmer_info = contract.functions.farmer_map(user).call()
            aadharId = farmer_info[1]
            print(f"Farmer Aadhar ID: {aadharId}")

            await sendNotification(aadharId)
    except Exception as e:
        print(f"Error in log_handler: {e}", exc_info=True)


async def sub_manager():
    max_retries = 5
    retry_delay = 10  # seconds
    
    # Try different providers
    working_provider = None
    
    # Test WebSocket providers first
    for provider_name, provider_url in PROVIDERS.items():
        if "ws" in provider_name:
            print(f"Testing {provider_name}: {provider_url}")
            if await test_provider(provider_url, is_websocket=True):
                working_provider = provider_url
                break
    
    if not working_provider:
        print("No WebSocket providers working. Trying HTTP providers...")
        for provider_name, provider_url in PROVIDERS.items():
            if "http" in provider_name and "ws" not in provider_name:
                print(f"Testing {provider_name}: {provider_url}")
                if await test_provider(provider_url, is_websocket=False):
                    working_provider = provider_url
                    break
    
    if not working_provider:
        print("No working providers found. Please check your API keys and network connection.")
        raise Exception("No working providers found. Please check your API keys and network connection.")
    
    print(f"Using provider: {working_provider}")
    
    for attempt in range(max_retries):
        try:
            print(f"Attempting to connect (attempt {attempt + 1}/{max_retries})")
            
            # Connect to provider
            if "ws" in working_provider:
                w3 = await AsyncWeb3(WebSocketProvider(working_provider))
            else:
                w3 = await AsyncWeb3(HTTPProvider(working_provider))
            
            print("Successfully connected")
            
            # Only subscribe to WebSocket events if using WebSocket provider
            if "ws" in working_provider:
                await w3.subscription_manager.subscribe([
                    LogsSubscription(
                        label="ImageSubmitted (address _user, string imageUrl)",
                        address=w3.to_checksum_address(CONTRACT_ADDRESS),
                        topics=[["0x2176ff554abc6afb8a3baf0448d7ff22c25829c4aee3806c623ed36edb2b2bba"]],
                        handler=log_handler,
                    )
                ])

                print("Subscribed to blockchain events. Waiting for ImageSubmitted events...")
                await w3.subscription_manager.handle_subscriptions()
            else:
                print("Using HTTP provider - real-time events not available")
                print("Consider setting up WebSocket provider for real-time event listening")
                # You could implement polling here instead
                await asyncio.sleep(60)  # Sleep for 1 minute
                
        except Exception as e:
            print(f"Connection attempt {attempt + 1} failed: {e}")
            if attempt < max_retries - 1:
                print(f"Retrying in {retry_delay} seconds...")
                await asyncio.sleep(retry_delay)
                retry_delay *= 2  # Exponential backoff
            else:
                print("Max retries exceeded. Please check your network connection and API key.")
                raise


def start():
    try:
        print("Starting blockchain event listener...")
        asyncio.run(sub_manager())
    except KeyboardInterrupt:
        print("Background worker stopped by user")
    except Exception as e:
        print(f"Background worker failed: {e}", exc_info=True)
    
    
