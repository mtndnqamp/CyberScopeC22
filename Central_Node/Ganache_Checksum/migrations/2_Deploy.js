const HashReg = artifacts.require("HashReg");

module.exports = function(deployer) {
    deployer.deploy(HashReg)
    .then (() => {
        console.log("Deployment successful");
    })
}