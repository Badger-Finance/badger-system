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
//const logger = console

const {
  KOVAN_WBTC_TOKEN_ADDR,
  KOVAN_RENBTC_TOKEN_ADDR,
  // Curve exchange renBTC/wBTC trading pair addr.
  KOVAN_CURVE_TRADING_PAIR_ADDR,
  KOVAN_ADAPTER_ADDR,
} = require('./deploy.json');
const WBTCFaucetABI = require('./WBTCFaucet.json');
const renBTCABI = require('./renBTC.json');

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
  logLevel: LogLevel.Debug
});
let web3 = null;
let account = null;
before(async function() {
  this.timeout(5000);
  // Create and set default eth test account for all tests (we want to mint/burn from same eth addr).
  const provider = new HDWalletProvider(MNEMONIC, INFURA_URL, 0, 10);
  web3 = new Web3(provider);
  const accounts = await web3.eth.getAccounts();
  web3.eth.defaultAccount = accounts[0];  // use first derived path
  // Setup btc account.
  account = new CryptoAccount(PRIVATE_KEY, { network: 'testnet' });

  // Ensure that we're on kovan.
  const networkID = await web3.eth.net.getId();
  if (networkID !== KOVAN_NETWORK_ID) {
    throw `Invalid network id ${networkID}, must use kovan network`;
  }

  // Approve eth account for spending of wbtc/renbtc.
  const wbtc = new web3.eth.Contract(WBTCFaucetABI, KOVAN_WBTC_TOKEN_ADDR);
  await approveSpend(wbtc);
  const renBTC = new web3.eth.Contract(renBTCABI, KOVAN_RENBTC_TOKEN_ADDR);
  await approveSpend(renBTC);
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


  it('should burn renBTC', async () => {
    const recipient = await account.address('btc');
    const amount = 0.00101;
    const params = {
      // Send BTC from Ethereum back to the Bitcoin blockchain.
      asset: 'BTC',
      to: Bitcoin().Address(recipient),
      from: Ethereum(web3.currentProvider).Contract((btcAddress) => ({
        sendTo: KOVAN_ADAPTER_ADDR,
        contractFn: 'burnRenBTC',
        contractParams: [
            {
                type: 'bytes',
                name: '_to',
                value: Buffer.from(btcAddress),
            },
            {
                type: 'uint256',
                name: '_amount',
                value: RenJS.utils.toSmallestUnit(amount, 8),
            },
        ],
        // NB: Need to include gas for burn tx as the gas cost of the burn method
        // is not estimatable.
        txConfig: { gas: 1000000 },
      })),
    };

    const burn = await renJS.burnAndRelease(params);
    logger.info('processing renBTC burn...');
    await processBurn(burn);
  });

  it('should burn wBTC', async () => {
    const recipient = await account.address('btc');
    const amount = .0015;
    const maxSlippage = .1;
    const minAmount = amount * (1 - maxSlippage);
    const params = {
      // Send BTC from Ethereum back to the Bitcoin blockchain.
      asset: 'BTC',
      to: Bitcoin().Address(recipient),
      from: Ethereum(web3.currentProvider).Contract((btcAddress) => ({
        sendTo: KOVAN_ADAPTER_ADDR,
        contractFn: 'burnWBTC',
        contractParams: [
          {
            type: 'bytes',
            name: '_to',
            value: Buffer.from(btcAddress),
          },
          {
            type: 'uint256',
            name: '_amount',
            value: RenJS.utils.toSmallestUnit(amount, 8),
          },
          {
            type: 'uint256',
            name: '_minAmount',
            value: RenJS.utils.toSmallestUnit(minAmount.toFixed(8), 8),
          },
        ],
        // NB: Need to include gas for burn tx as the gas cost of the burn method
        // is not estimatable.
        txConfig: { gas: 1000000 },
      })),
    };

    const burn = await renJS.burnAndRelease(params);
    logger.info('processing renBTC burn...');
    await processBurn(burn);
    logger.info(`Withdrew ${amount} BTC to ${recipient}.`);
  });
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
  await minting;
};

const processBurn = async function (burn) {
  let confirmations = 0;
  await burn
    .burn()
    // Ethereum transaction confirmations.
    .on('confirmation', (confs) => {
        logger.info(`received burn confirmation #: ${confs}`);
        confirmations = confs;
    })
    // Print Ethereum transaction hash.
    .on('transactionHash', (txHash) =>
        logger.info(`txHash: ${String(txHash)}`),
    );

  await burn
    .release()
    // Print RenVM status - 'pending', 'confirming' or 'done'.
    .on('status', (status) => {
      if (status === 'confirming') {
        logger.info(`${status} (${confirmations}/15)`);
      } else {
        logger.info(status);
      }
    })
    // Print RenVM transaction hash
    .on('txHash', logger.info);
};

const approveSpend = async (erc20) => {
  const requestedAllowance = 9999999;
  let allowance = await erc20.methods.allowance(web3.eth.defaultAccount, KOVAN_ADAPTER_ADDR).call({
    from: web3.eth.defaultAccount,
  });
  logger.info(`current allowance ${web3.eth.defaultAccount} -> ${allowance}`);
  if (allowance < requestedAllowance) {
    logger.info(`approving spend on behalf of ${web3.eth.defaultAccount}`);
    await erc20.methods.approve(KOVAN_ADAPTER_ADDR, requestedAllowance).send({
      from: web3.eth.defaultAccount,
    });
    allowance = await erc20.methods.allowance(web3.eth.defaultAccount, KOVAN_ADAPTER_ADDR).call({
      from: web3.eth.defaultAccount,
    });
    logger.info(`new allowance ${web3.eth.defaultAccount} -> ${allowance}`);
    if (allowance != requestedAllowance) {
      throw `Allowance approval failed, requested (${requestedAllowance}) - actual allowance (${allowance})`;
    }
  }
};
