/**
 * @type import('hardhat/config').HardhatUserConfig
 */
module.exports = {
  solidity: {
    compilers: [
      {
        version: "0.6.12",
      },
      {
        version: "0.6.8",
      },
      {
        version: "0.5.10",
      },
      {
        version: "0.4.24",
      },
    ],
  },
  networks: {
    arbitrum: {
      url: 'https://rinkeby.arbitrum.io/rpc',
      gasPrice: 0,
    },
  },
};
