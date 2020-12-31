const assert = require('assert');
const Web3 = require('web3');
const RenJS = require('@renproject/ren');

require('dotenv').config();

const KOVAN_NETWORK_ID = 42;
const KOVAN_BADGER_REN_ADAPTER_ADDR = '0x9C3Ef5ecE74D7D33D0f68dFb550D2474Dc8e9732';

// initialize before running all tests
const renJS = new RenJS('testnet');
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

	const amount = .001;
	const mint = await renJS.lockAndMint({
		// Send BTC from the Bitcoin blockchain to the Ethereum blockchain.
		asset: "BTC",
		from: Bitcoin(),
		to: Ethereum(web3.currentProvider).Contract({
			// The contract we want to interact with
			sendTo: KOVAN_BADGER_REN_ADAPTER_ADDR,

			// The name of the function we want to call
			contractFn: "mint",

			// Arguments expected for calling `mint`
			contractParams: [
				{
					name: "_to",
					type: "address",
					value: testAccount.address,
				},
				{
					name: "_amount",
					type: "uint256",
					value: RenJS.utils.value(amount, "btc").sats(),
				},
			],
		}),
	});

    const gatewayAddress = lockAndMint.addr();
    console.log(`Deposit ${amount} BTC to ${gatewayAddress} for testing`);

    // TODO: Connect to bitcoin testnet and make deposit
    // Would need to run a local bitcoin testnet node and interact w/ it, prob better
	// to do this step manually for now.

    // Wait for deposit to clear
    await lockAndMint.waitAndSubmit(web3.currentProvider, 0 /* confirmations */)

    // TODO: Check renBTC balance
  });
});
