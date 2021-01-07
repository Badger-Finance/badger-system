const assert = require('assert');
const Web3 = require('web3');
const RenJS = require('@renproject/ren');
const HDWalletProvider = require('truffle-hdwallet-provider');
const { LogLevel } = require('@renproject/interfaces');
const {
  SECONDS,
  sleep,
} = require('@renproject/utils');
const CryptoAccount = require('send-crypto');
const logger = require('pino')({
    prettyPrint: { colorize: true }
});

const {
  // Curve exchange renBTC/wBTC trading pair addr.
  KOVAN_CURVE_TRADING_PAIR_ADDR,
  KOVAN_ADAPTER_ADDR,
} = require('./deploy.json');
const curveABI = require('./curveABI.json');

require('dotenv').config();

const INFURA_PROJECT_ID = process.env.WEB3_INFURA_PROJECT_ID;
const INFURA_URL = `https://kovan.infura.io/v3/${INFURA_PROJECT_ID}`;
// Generate wallet from mnemonic.
const MNEMONIC = process.env.TEST_MNEMONIC;
const PRIVATE_KEY = process.env.TESTNET_PRIVATE_KEY;
  // Ren test env (gateways) are deployed on the kovan testnet.
const KOVAN_NETWORK_ID = 42;
const MINUTES = 60 * SECONDS;

// initialize before running all tests
const renJS = new RenJS('testnet', {
  logLevel: LogLevel.Debug
});
let web3 = null;
before(async () => {
  // Create and set default test account for all tests (we want to mint/burn from same eth addr).
  const provider = new HDWalletProvider(MNEMONIC, INFURA_URL, 0, 10);
  web3 = new Web3(provider);
  const accounts = await web3.eth.getAccounts();
  web3.eth.defaultAccount = accounts[0];  // use first derived path
  const networkID = await web3.eth.net.getId();
  if (networkID !== KOVAN_NETWORK_ID) {
    throw `Invalid network id ${networkID}, must use kovan network`;
  }
});

describe('BadgerRenAdapter', function() {
  this.timeout(60 * MINUTES); // 60 minute t/o for integration tests

  it('should mint renBTC', async () => {

    const amount = 0.00101;
    const mint = await renJS.lockAndMint({
      // Send BTC from the Bitcoin blockchain to the Ethereum blockchain.
      sendToken: RenJS.Tokens.BTC.Btc2Eth,
      // The contract we want to interact with
      sendTo: KOVAN_ADAPTER_ADDR,
      contractFn: 'mintRenBTC',
      // Arguments expected for calling `mint`
      contractParams: [
        {
      	  name: '_to',
      	  type: 'address',
      	  value: web3.eth.defaultAccount,
        },
      ],
      web3Provider: web3.currentProvider,
    });

    logger.info('processing renBTC mint...');
    await processMint(mint, amount);
  });

  it('should burn renBTC', async () => {
  });

  it('should mint wBTC', async () => {

    const amount = 0.00101;
    // Use high max slippage, we just want the tx to go thru for test purposes.
    const maxSlippage = 0.05;
    const mint = await renJS.lockAndMint({
      // Send BTC from the Bitcoin blockchain to the Ethereum blockchain.
      sendToken: RenJS.Tokens.BTC.Btc2Eth,
      // The contract we want to interact with
      sendTo: KOVAN_ADAPTER_ADDR,
      contractFn: 'mintWBTC',
      // Arguments expected for calling `mint`
      contractParams: [
        {
          name: "_slippage",
          type: "uint256",
          value: Number(maxSlippage * 10000).toFixed(0),
        },
        {
          name: "_wbtcDestination",
          type: "address",
          value: web3.eth.defaultAccount,
        },
      ],
      web3Provider: web3.currentProvider,
    });

    logger.info('processing wBTC mint...');
    await processMint(mint, amount);
  });

  it('should burn wBTC', async () => {
  });


});

// A debug `sleep`. It prints a count-down to the console.
const sleepWithCountdown = async (seconds) => {
  while (seconds) {
    process.stdout.write(`\u001b[0K\r${seconds}\r`);
    await sleep(1 * SECONDS);
    seconds -= 1;
  }
  process.stdout.write('\u001b[0K\r');
};

const processMint = async(mint, _amount) => {
    const gatewayAddress = await mint.gatewayAddress();
    const account = new CryptoAccount(PRIVATE_KEY, { network: 'testnet' });
    logger.info(
      `BTC balance: ${await account.balanceOf(
          'btc'
      )} ${'btc'} (${await account.address('btc')})`
    );
	const amount = RenJS.utils
	  .value(_amount, 'btc')
	  ._smallest();
    logger.info(`Sending BTC: ${amount}`);
    await account.sendSats(gatewayAddress, amount, 'btc');

    // Submit mint
    // NB: On testnet this actually mints testBTC.
	await submitMint(mint);
};

const submitMint = async (mint) => {
  const confirmations = 0;
  logger.info(`Waiting for ${confirmations} confirmations...`);

  let deposit;
  try {
    deposit = await mint
      .wait(confirmations)
      .on('deposit', (depositObject) => {
        logger.info(
          `Received a new deposit: ${JSON.stringify(depositObject)}`
        );
      });
  } catch (e) {
    console.error(`error waiting for deposit: ${e}`);
    throw e;
  }

  await sleepWithCountdown(5);

  logger.info(`Submitting deposit to RenVM...`);
  const signature = await deposit
    .submit()
    .on('txHash', (txHashB64) => {
        const buf = Buffer.from(txHashB64, 'base64');
        const txHashHex = buf.toString('hex');
      logger.info(`Received txHash(testnet.renVM): 0x${txHashHex}`);
    })
    .on('status', (status) => {
      logger.info(`Received status: ${status}`, {
        overwrite: true,
      });
    });

  logger.info(`Submitting signature to Ethereum...`);
  try {
    await signature
      .submitToEthereum(web3.currentProvider, { gas: 1000000 })
      .on('eth_transactionHash', (txHash) => {
        logger.info(`Received txHash: ${txHash}`);
      });
    logger.info('Done waiting for Ethereum TX.');
  } catch (error) {
    logger.error(error);
    throw error;
  }
};

const getMinExchangeRate = async (amount) => {
  const curve = new web3.eth.Contract(curveABI, KOVAN_CURVE_TRADING_PAIR_ADDR);
  // NB: In production, we actually want to calculate this based on the expected badger/renVM fees.
  // For testing purposes we'll just make the minimum mint amount 95% of the mint amount.
  const amountAfterMint = amount * 0.95;
  const amountAfterMintInSats = Math.round(
    RenJS.utils.value(amountAfterMint, "btc").sats().toNumber()
  );

  const swapResult =
    (await curve.methods.get_dy(0, 1, amountAfterMintInSats).call()) /
    10 ** 8; // satoshi denominated, convert back to BTC
  return Number(swapResult / amountAfterMint);
}
