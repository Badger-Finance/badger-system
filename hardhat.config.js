require("@nomiclabs/hardhat-waffle");
require("@nomiclabs/hardhat-ethers");

// This is a sample Hardhat task. To learn how to create your own go to
// https://hardhat.org/guides/create-task.html
task("accounts", "Prints the list of accounts", async () => {
  const accounts = await ethers.getSigners();

  for (const account of accounts) {
    console.log(account.address);
  }
});

/**
 * @type import('hardhat/config').HardhatUserConfig
 */
module.exports = {
  networks: {
    hardhat: {
      blockGasLimit: 9999999999,
      gas: 99999,
    }
  },
  paths: {
    sources: "/none"
  },
  solidity: ">0.4.0",
};
