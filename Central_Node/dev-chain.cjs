// Development only: fresh Ganache accounts, loopback binding, no hardcoded keys.
const fs = require('fs');
const path = require('path');
const ganache = require('ganache');
const solc = require('solc');
const {Web3} = require('web3');
(async () => {
 const root=path.resolve(__dirname,'..');
 const envPath=path.join(root,'.env.demo');

 const source=fs.readFileSync(path.join(__dirname,'Ganache_Checksum/contracts/HashReg.sol'),'utf8');
 const result=JSON.parse(solc.compile(JSON.stringify({language:'Solidity',sources:{'HashReg.sol':{content:source}},settings:{evmVersion:'london',outputSelection:{'*':{'*':['abi','evm.bytecode.object']}}}})));
 const errors=(result.errors||[]).filter(x=>x.severity==='error');
 if(errors.length) throw Error(errors.map(x=>x.formattedMessage).join('\n'));
 const contract=result.contracts['HashReg.sol'].HashReg;
 const server=ganache.server({logging:{quiet:true},wallet:{totalAccounts:2},chain:{hardfork:'london'}});
 await server.listen(8545,'127.0.0.1');
 try {
 const web3=new Web3('http://127.0.0.1:8545');
 const accounts=server.provider.getInitialAccounts();
 const owner=Object.keys(accounts)[0];
 const deployment=new web3.eth.Contract(contract.abi).deploy({data:'0x'+contract.evm.bytecode.object});
 const gas=await deployment.estimateGas({from:owner});
 const deployed=await deployment.send({from:owner,gas});
 fs.writeFileSync(envPath,`RPC_URL=http://127.0.0.1:8545\nCONTRACT_ADDR=${deployed.options.address}\nACC_PRIVATE_KEY=${accounts[owner].secretKey}\n`,{flag:'w'});
 console.log('Development blockchain ready at http://127.0.0.1:8545.');
 console.log('Fresh development configuration saved to ignored .env.demo; keep this terminal open.');
 console.log('Each restart creates a fresh chain; register the baseline again.');
 console.log('Contract: '+deployed.options.address);
 const stop=async()=>{await server.close();process.exit(0);};
 process.on('SIGINT',stop);process.on('SIGTERM',stop);
 } catch(error) {await server.close();throw error;}
})().catch(error=>{console.error(error.message);process.exitCode=1;});
