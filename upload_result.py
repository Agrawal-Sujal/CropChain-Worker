import logging
import os
from pathlib import Path
from web3 import Web3
from dotenv import load_dotenv

# Get absolute path of .env file inside worker/
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
dotenv_path = os.path.join(BASE_DIR, ".env")

# Load the .env file
load_dotenv(dotenv_path)



abi = os.getenv('ABI')
pk = os.getenv('PRIVATE_KEY')
address = os.getenv('ADDRESS')
contractAddress = os.getenv('CONTRACT_ADDRESS')

def uploadResult(url, result):
    """Upload AI result to blockchain with proper logging"""
    try:
        print(f"Starting blockchain upload for URL: {url}")
        print(f"AI Result: {result}")
        
        # Initialize Web3 connection
        w3 = Web3(Web3.HTTPProvider(os.getenv('HTTP_PROVIDER_1')))
        
        # Check connection
        if not w3.is_connected():
            print("Failed to connect to Ethereum network")
            return False
            
        print("Connected to Ethereum network")
        
        # Reference the deployed contract
        billboard = w3.eth.contract(address=contractAddress, abi=abi)
        print(f"Contract loaded at address: {contractAddress}")

        # Get current nonce
        nonce = w3.eth.get_transaction_count(address)
        print(f"Current nonce: {nonce}")

        # Manually build and sign a transaction
        print("Building transaction...")
        unsent_billboard_tx = billboard.functions.AI_solution(url, result).build_transaction({
            "from": address,
            "nonce": nonce,
        })
        
        print("Signing transaction...")
        signed_tx = w3.eth.account.sign_transaction(unsent_billboard_tx, private_key=pk)
        print("Transaction signed successfully")

        # Send the raw transaction
        print("Sending transaction to blockchain...")
        tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
        tx_hash_hex = '0x' + tx_hash.hex()
        print(f"Transaction hash: {tx_hash_hex}")
        
        # Wait for transaction receipt
        print("Waiting for transaction confirmation...")
        tx_receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
        
        if tx_receipt.status == 1:
            print("Transaction confirmed successfully!")
            print(f"Gas used: {tx_receipt.gasUsed}")
            print(f"Block number: {tx_receipt.blockNumber}")
            return True
        else:
            print("Transaction failed")
            return False
            
    except Exception as e:
        print(f"Error uploading result to blockchain: {e}", exc_info=True)
        return False
