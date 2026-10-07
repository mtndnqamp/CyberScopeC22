"""HashReg client. Importing this module does not connect or load secrets."""
import json
import os
from pathlib import Path

class BlockchainClient:
    def __init__(self, rpc_url=None, contract_address=None, private_key=None):
        from web3 import Web3
        from dotenv import load_dotenv, dotenv_values
        load_dotenv(Path(__file__).resolve().parents[1] / ".env")
        demo = dotenv_values(Path(__file__).resolve().parents[1] / ".env.demo")
        rpc_url = rpc_url or os.getenv("RPC_URL") or demo.get("RPC_URL")
        contract_address = contract_address or os.getenv("CONTRACT_ADDR") or os.getenv("CONTACT_ADDR") or demo.get("CONTRACT_ADDR")
        self.private_key = private_key or os.getenv("ACC_PRIVATE_KEY") or demo.get("ACC_PRIVATE_KEY")
        if not rpc_url or not contract_address:
            raise ValueError("Set RPC_URL and CONTRACT_ADDR in the project .env")
        self.w3 = Web3(Web3.HTTPProvider(rpc_url, request_kwargs={"timeout": 10}))
        if not self.w3.is_connected():
            raise ConnectionError("Cannot reach blockchain RPC")
        address = Web3.to_checksum_address(contract_address)
        if not self.w3.eth.get_code(address):
            raise ValueError("No contract deployed at CONTRACT_ADDR")
        abi = json.loads(Path(__file__).with_name("HashReg.json").read_text())["abi"]
        self.contract = self.w3.eth.contract(address=address, abi=abi)

    def get_baseline_hash(self, record_id):
        value, creator = self.contract.functions.getHash(record_id).call()
        if int(creator, 16) == 0:
            raise ValueError("No blockchain baseline for this device")
        return bytes(value).hex()

    def store_baseline_hash(self, record_id, hash_value):
        raw = bytes.fromhex(hash_value.removeprefix("0x"))
        if len(raw) != 32:
            raise ValueError("SHA-256 must contain exactly 32 bytes")
        if not self.private_key:
            raise ValueError("Set ACC_PRIVATE_KEY to register a baseline")
        account = self.w3.eth.account.from_key(self.private_key)
        tx = self.contract.functions.storeHash(record_id, raw).build_transaction({
            "from": account.address,
            "nonce": self.w3.eth.get_transaction_count(account.address, "pending"),
            "chainId": self.w3.eth.chain_id,
        })
        signed = account.sign_transaction(tx)
        tx_hash = self.w3.eth.send_raw_transaction(signed.raw_transaction)
        receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
        if receipt.status != 1:
            raise RuntimeError("Baseline transaction failed")
        return tx_hash.hex()
