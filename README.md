![Badger Logo](./images/badger-logo.png)

# Badger Finance

Badger Finance is a community DAO, focused on bringing Bitcoin to DeFi. The DAO's debut products are Sett, a yield aggregator, and Digg, a BTC-pegged elastic supply currency.

Visit our [GitBook](https://app.gitbook.com/@badger-finance/s/badger-finance/) for more detailed documentation.

## Build

The Badger contracts & tests are built around the [Eth-Brownie](https://eth-brownie.readthedocs.io/en/stable/install.html) Python framework.

If you're not familiar with brownie, see the [quickstart guide](https://eth-brownie.readthedocs.io/en/stable/quickstart.html).

### Dependencies

-   Python 3.9
-   Node.js 10.x development environment (for Ganache).
-   [Eth-Brownie](https://eth-brownie.readthedocs.io/en/stable/install.html)
-   Ganache (v6.12.1)

### Install

For Ubuntu, you can install the prerequisite packages with the following command:

```
sudo apt-get install -y python3 python3-virtualenv python3-pip
```

For other systems, install Python 3.9, Pip, and use pip to install virtualenv with

```
pip install virtualenv
```

To install NodeJS and yarn on UNIX based systems, it is recommended to use the following commands:

```
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.38.0/install.sh | bash
nvm install v14.16.1
npm install -g yarn
```

With prerequisites installed, install the project with:

```bash
git clone https://github.com/Badger-Finance/badger-system
cd badger-system
yarn install --lock-file
virtualenv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Compile

```bash
source venv/bin/activate
brownie compile
```

### Test

```bash
source venv/bin/activate
brownie test
```

### Add coverage and gas profiling

```bash
source venv/bin/activate
brownie test --coverage --gas
```

### Local Instance

Run a local ganache instance connected to badger contracts, with all Sett-related assets distributed to a test account specified in the TEST_ACCOUNT env variable. Assumes the default network is mainnet-fork in the brownie config and uses Alchemy as a web3 provider through the ALCHEMYAPI_TOKEN env variable. Ganache will continue to run until the process is closed.

```bash
source venv/bin/activate
export TEST_ACCOUNT=<enter your account here>
export ALCHEMYAPI_TOKEN=<enter infura key here>
brownie run scripts/local_instance.py
```

### Running Scripts on non-Ethereum chains
The included brownie-config.yaml has configurations for running forked environments on non-ethereum chains where Badger contracts are deployed. To run scripts against another chain, append the appropriate `--network` parameter to any `brownie run` or `brownie test` command.

The appropriate live Badger deploy for that chain will automatically be read.

As an example, `bsc-fork` is the networkID for a Binance Smart Chain forked environment.

```bash
brownie run scripts/local_instance.py --network bsc-fork
```

### Badger Deploy Files
These files maintain a registry of all live Badger contracts on a given chain.
* Ethereum Mainnet: [deploy-final.json](https://github.com/Badger-Finance/badger-system/blob/develop/deploy-final.json)
* Binance Smart Chain: [badger-deploy-bsc.json](https://github.com/Badger-Finance/badger-system/blob/develop/badger-deploy-bsc.json)

### Documentation

You can read more about Badger at our [GitBook](https://app.gitbook.com/@badger-finance/s/badger-finance/).

### Discussion

To join the community, head over to the [Discord server](https://discord.gg/CMzUcANy).
