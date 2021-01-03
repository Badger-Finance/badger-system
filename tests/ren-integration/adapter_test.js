const assert = require('assert');
const Web3 = require('web3');
const RenJS = require('@renproject/ren');
const CryptoAccount = require('send-crypto');
const logger = require('pino')();

require('dotenv').config();

const INFURA_PROJECT_ID = process.env.WEB3_INFURA_PROJECT_ID;
const PRIVATE_KEY = process.env.TESTNET_PRIVATE_KEY;
const KOVAN_NETWORK_ID = 42;
const KOVAN_BADGER_REN_ADAPTER_ADDR = '0x9C3Ef5ecE74D7D33D0f68dFb550D2474Dc8e9732';

// initialize before running all tests
const renJS = new RenJS('testnet');
let web3 = null;
before(async () => {
  // Need an infura account for testing.
  // Ren test env (gateways) are deployed on the kovan testnet.
  web3 = new Web3(`https://kovan.infura.io/v3/${INFURA_PROJECT_ID}`);
  const networkID = await web3.eth.net.getId();
  if (networkID !== KOVAN_NETWORK_ID) {
    throw `Invalid network id ${networkID}, must use kovan network`;
  }
});

describe('BadgerRenAdapter', () => {
  it('should mint renBTC', async () => {
    const testAccount = web3.eth.accounts.create();

	const mint = await renJS.lockAndMint({
		// Send BTC from the Bitcoin blockchain to the Ethereum blockchain.
		sendToken: RenJS.Tokens.BTC.Btc2Eth,
		// The contract we want to interact with
  		sendTo: KOVAN_BADGER_REN_ADAPTER_ADDR,
  		contractFn: "mint",
		// Arguments expected for calling `mint`
  		contractParams: [
		  {
			  name: "_to",
			  type: "address",
			  value: testAccount.address,
		  },
		],
  		web3Provider: web3.currentProvider,
	});

    const gatewayAddress = await mint.gatewayAddress();
    const account = new CryptoAccount(PRIVATE_KEY, { network: "testnet" });
    logger.info(
        `BTC balance: ${await account.balanceOf(
            "btc"
        )} ${"btc"} (${await account.address("btc")})`
    );
	const amount = RenJS.utils
		.value(0.0008, "btc")
		._smallest();
    logger.info(`Sending BTC: ${amount}`);
    await account.sendSats(gatewayAddress, amount, "btc");

    // Submit mint
	await submitMint(mint);
  });
});

// A debug `sleep`. It prints a count-down to the console.
// tslint:disable-next-line: no-string-based-set-timeout
const sleepWithCountdown = async (seconds) => {
    while (seconds) {
        process.stdout.write(`\u001b[0K\r${seconds}\r`);
        await sleep(1 * SECONDS);
        seconds -= 1;
    }
    process.stdout.write("\u001b[0K\r");
};

const submitMint = async (mint) => {
    // Wait for deposit to be received and submit to Lightnode + Ethereum.
    const confirmations = 0;
    logger.info(`Waiting for ${confirmations} confirmations...`);

    const deposit = await mint
        .wait(confirmations)
        .on("deposit", (depositObject) => {
            logger.info(
                `Received a new deposit: ${JSON.stringify(depositObject)}`
            );
        });

    await sleepWithCountdown(5);

    logger.info(`Submitting deposit to RenVM...`);
    const signature = await deposit
        .submit()
        .on("txHash", (txHash) => {
            logger.debug(`Received txHash: ${txHash}`);
            deposit.txHash().should.equal(txHash);
        })
        .on("status", (status) => {
            logger.debug(`Received status: ${chalk.green(status)}`, {
                overwrite: true,
            });
        });

    logger.info(`Submitting signature to Ethereum...`);
    try {
        await signature
            .submitToEthereum(provider, { gas: 1000000 })
            .on("eth_transactionHash", (txHash) => {
                logger.debug(`Received txHash: ${txHash}`);
            });
        logger.info("Done waiting for Ethereum TX.");
    } catch (error) {
        logger.error(error);
        throw error;
    }
};
