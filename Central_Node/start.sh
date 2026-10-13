#!/bin/bash
chain=$(ganache --chain.networkId=5566 --wallet.accounts="0x3ff4e56809eff51fea0a4d096b852ec3367ec9c2dde9a3dfa5c8a140a99bb768","0x16345785d8a0000 " --wallet.accounts="0xcf4a54bc13ee1781d993b77aad15433c11544558f56815752bb7c2b97dc7c516","0x16345785d8a0000 " --server.host="127.0.0.1" --server.port="8545" --detach)
cd Ganache_Checksum
truffle migrate
echo "Instance: $chain"
echo "Press ENTER to stop"
read
ganache instances stop $chain