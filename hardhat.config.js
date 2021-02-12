/**
 * @type import('hardhat/config').HardhatUserConfig
 */

require('hardhat-deploy');
require('hardhat-deploy-ethers');

require('@nomiclabs/hardhat-etherscan');

module.exports = {
  solidity: "0.6.12",
  networks: {
    hardhat: {}
  }
};
