pragma solidity ^0.8.20;

contract HashReg {
    struct HashRecord {
        bytes32 hashVal;
        address creator;
    }

    mapping(string => HashRecord) private hashes;

    event HashStored(string indexed recordId, address indexed account, uint256 timestamp);
    // event HashFetched(string indexed recordId, address indexed account, uint256 timestamp);

    function storeHash(string memory recordId, bytes32 hashVal) external {
        HashRecord storage rec = hashes[recordId];
        
        if (rec.creator == address(0)) {
            // First time storage
            rec.creator = msg.sender;
        } else {
            // Record exists
            require(rec.creator == msg.sender, "Only original creator of this record can update record.");
        }

        rec.hashVal = hashVal;
        emit HashStored(recordId, msg.sender, block.timestamp);
    }
    // function kept as view because emitting events change blockchain state
    function getHash(string memory recordId) public view returns (bytes32, address) {
        // emit HashFetched(recordId, msg.sender, block.timestamp);
        HashRecord memory rec = hashes[recordId];
        return (rec.hashVal, rec.creator);
    }
}