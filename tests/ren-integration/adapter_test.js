const assert = require('assert');
const Web3 = require('web3');
const RenJS = require('@renproject/ren');
const {
  EthereumConfigMap,
  Bitcoin,
  Ethereum,
  renTestnet,
} = require('@renproject/chains');
const HDWalletProvider = require('truffle-hdwallet-provider');
const {
  LogLevel,
  RenNetwork,
} = require('@renproject/interfaces');
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

const NETWORK = RenNetwork.Testnet;
const ETHEREUM_NETWORK = EthereumConfigMap[NETWORK];

const INFURA_PROJECT_ID = process.env.WEB3_INFURA_PROJECT_ID;
const INFURA_URL = `${ETHEREUM_NETWORK.infura}/v3/${INFURA_PROJECT_ID}`;

// Generate wallet from mnemonic.
const MNEMONIC = process.env.TEST_MNEMONIC;
const PRIVATE_KEY = process.env.TESTNET_PRIVATE_KEY;

  // Ren test env (gateways) are deployed on the kovan testnet.
const KOVAN_NETWORK_ID = 42;
const MINUTES = 60 * SECONDS;

// initialize before running all tests
const renJS = new RenJS(NETWORK, {
  //logLevel: LogLevel.Debug
});
let web3 = null;
let account = null;
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
  account = new CryptoAccount(PRIVATE_KEY, { network: 'testnet' });
});

describe('BadgerRenAdapter', function() {
  this.timeout(60 * MINUTES); // 60 minute t/o for integration tests

  it('should mint renBTC', async () => {
    const params = {
      asset: 'BTC',
      from: Bitcoin(),
      to: Ethereum(web3.currentProvider, ETHEREUM_NETWORK).Contract({
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
    }),
  };

    const mint = await renJS.lockAndMint(params);

    logger.info('processing renBTC mint...');
    const amount = 0.00101;
    await processMint(mint, amount);
  });

  it('should mint wBTC', async () => {
    const maxSlippage = 0.10;
    const params = {
      asset: 'BTC',
      from: Bitcoin(),
      to: Ethereum(web3.currentProvider, ETHEREUM_NETWORK).Contract({
        sendTo: KOVAN_ADAPTER_ADDR,
        contractFn: 'mintWBTC',
        // Arguments expected for calling `mint`
        contractParams: [
          {
            name: '_slippage',
            type: 'uint256',
            value: Number(maxSlippage * 10000).toFixed(0),
          },
          {
            name: '_to',
            type: 'address',
            value: web3.eth.defaultAccount,
          },
        ],
      }),
    };

    const mint = await renJS.lockAndMint(params);

    logger.info('processing wBTC mint...');
    const amount = 0.00101;
    await processMint(mint, amount);
  });


  /*
   *  The burn contract method fails on gas estimation.
   *  Specifically, on infura the rpc `eth_estimateGas` rpc call reverts on local node.
   *  `web3.eth.estimateGas()` fails in similar fashion and is likely what infura
   *  is using under the hood to estimate the gas cost of the method
   *  (they have a gas cap on tx). W/ more control, we can manually set a gas limit
   *  and submit the tx w/o needing to call estimate gas (which fails on local node).
   *  Burns were tested manually in a brownie console.
   */
  //it('should burn renBTC', async () => {
  //  const recipient = await account.address('btc');
  //  const amount = 0.00101;
  //  const params = {
  //    // Send BTC from Ethereum back to the Bitcoin blockchain.
  //    asset: 'BTC',
  //    to: Bitcoin().Address(recipient),
  //    from: Ethereum(web3.currentProvider).Contract((btcAddress) => ({
  //        sendTo: KOVAN_ADAPTER_ADDR,
  //        contractFn: 'burnRenBTC',
  //        contractParams: [
  //            {
  //                type: 'bytes',
  //                name: '_to',
  //                value: Buffer.from(btcAddress),
  //            },
  //            {
  //                type: 'uint256',
  //                name: '_amount',
  //                value: RenJS.utils.toSmallestUnit(amount, 8),
  //            },
  //        ],
  //    })),
  //  };

  //  const burn = await renJS.burnAndRelease(params);
  //  logger.info('processing renBTC burn...');
  //  await processBurn(burn, amount);
  //});
  //
  //it('should burn wBTC', async () => {
  //  const recipient = await account.address('btc');
  //  const amount = .101;
  //  const maxSlippage = .1;
  //  const minAmount = amount * (1 - maxSlippage);
  //  const params = {
  //    // Send BTC from Ethereum back to the Bitcoin blockchain.
  //    asset: 'BTC',
  //    to: Bitcoin().Address(recipient),
  //    from: Ethereum(web3.currentProvider).Contract((btcAddress) => ({
  //        sendTo: KOVAN_ADAPTER_ADDR,
  //        contractFn: 'burnWBTC',
  //        contractParams: [
  //            {
  //                type: 'bytes',
  //                name: '_to',
  //                value: Buffer.from(btcAddress),
  //            },
  //            {
  //                type: 'uint256',
  //                name: '_amount',
  //                value: RenJS.utils.toSmallestUnit(amount, 8),
  //            },
  //            {
  //                type: 'uint256',
  //                name: '_minAmount',
  //                value: RenJS.utils.toSmallestUnit(minAmount.toFixed(8), 8),
  //            },
  //        ],
  //    })),
  //  };

  //  const burn = await renJS.burnAndRelease(params);
  //  logger.info('processing renBTC burn...');
  //  await processBurn(burn, amount);
  //});
});

const processMint = async(mint, _amount) => {
    logger.info(
      `BTC balance: ${await account.balanceOf(
          'btc'
      )} ${'btc'} (${await account.address('btc')})`
    );
    logger.info(`Sending BTC: ${_amount}`);
    await account.send(mint.gatewayAddress, _amount, 'btc', {});

    // Submit mint
    // NB: On testnet this actually mints testBTC.
	await submitMint(mint);
};

const submitMint = async (mint) => {
  const minting = new Promise((resolve, reject) => {
    mint.on('deposit', async (deposit) => {
      // Details of the deposit are available from `deposit.depositDetails`.

      const hash = deposit.txHash();
      const depositLog = (msg) => logger.info(`[${hash.slice(0, 8)}][${deposit.status}] ${msg}`);

      await deposit.confirmed()
        .on('target', (confs, target) => logger.info(`${confs}/${target} confirmations`))
        .on('confirmation', (confs, target) => logger.info(`${confs}/${target} confirmations`));

      await deposit.signed()
        // Print RenVM status - 'pending', 'confirming' or 'done'.
        .on('status', (status) => logger.info(`Status: ${status}`));

      await deposit.mint()
        // Print Ethereum transaction hash.
        .on('transactionHash', (txHash) => logger.info(`Mint tx: ${txHash}`));

      resolve();
    });
  })
  await minting
};

const processBurn = async (burn, amount) => {
  let confirmations = 0;
  await burn
    .burn()
    // Ethereum transaction confirmations.
    .on('confirmation', (confs) => {
        confirmations = confs;
    })
    // Print Ethereum transaction hash.
    .on('transactionHash', (txHash) =>
        this.log(`txHash: ${String(txHash)}`),
    );

  await burnAndRelease
    .release()
    // Print RenVM status - 'pending', 'confirming' or 'done'.
    .on('status', (status) =>
      status === 'confirming'
        ? logger.info(`${status} (${confirmations}/15)`)
        : logger.info(status),
    )
    // Print RenVM transaction hash
    .on('txHash', logger.info);

  logger.info(`Withdrew ${amount} BTC to ${recipient}.`);
};
