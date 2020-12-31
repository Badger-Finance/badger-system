const assert = require('assert');
const Web3 = require('web3');
const renJS = new RenJS("testnet");

require('dotenv').config();

const KOVAN_NETWORK_ID = 42;

// initialize before running all tests
let web3 = null;
before(async () => {
  // Need an infura account for testing.
  // Ren test env (gateways) are deployed on the kovan testnet.
  web3 = new Web3(`https://kovan.infura.io/v3/${process.env.WEB3_INFURA_PROJECT_ID}`);
  const networkID = await web3.eth.net.getId();
  if (networkID !== KOVAN_NETWORK_ID) {
    throw `Invalid network id ${networkID}, must use kovan network`;
  }
});

describe('BadgerRenAdapter', () => {
  it('should mint renBTC', async () => {
    const testAccount = web3.eth.accounts.create();
    const lockAndMint = renJS.lockAndMint({
        sendToken: "BTC", // Bridge BTC to Ethereum
        sendAmount: renJS.utils.value(amount, "btc").sats(), // Amount of BTC
        sendTo: testAccount.address, // Recipient Ethereum address
    });

    const gatewayAddress = lockAndMint.addr();
    console.log(`Deposit ${amount} BTC to ${gatewayAddress} for testing`);
    // TODO: Connect to bitcoin testnet and make deposit
    // (probably use a pre-configured addr w/ some manually loaded BTC from faucet)

    // Wait for deposit to clear
    await lockAndMint.waitAndSubmit(web3.currentProvider, 0 /* confirmations */)

    // TODO: Check renBTC balance
  });
});
