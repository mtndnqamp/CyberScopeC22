# THE EDGE DEVICE NEEDS THE CONTRACT ABI (find on deployment/central device under build/contracts; should be called HashReg.json) AND CONTRACT ADDRESS WHICH WILL BE GENERATED ON CHAIN DEPLOYMENT

import json
import requests
import os
from dotenv import load_dotenv
from web3 import Web3

# Startup stuff
load_dotenv()

rpc_url = os.getenv("RPC_URL")
contact_addr = os.getenv("CONTACT_ADDR")
prv_key = os.getenv("ACC_PRIVATE_KEY")

w3 = Web3(Web3.HTTPProvider(rpc_url))
node_acc = w3.eth.account.from_key(prv_key)

with open("HashReg.json", "r"):
    abi = json.load(f)["abi"]

contract = w3.eth.contract(address=Web3.to_checksum_address(contact_addr), abi=abi)

# call via contract object i.e. contract.functions.<functionName>
# for the storage function, need to sign the transaction (append contract function with .build_transaction({})), and for read append with .call() function 

# 