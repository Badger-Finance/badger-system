![Badger Logo](./images/badger-logo.png)
# Badger Finance 
Badger Finance is a community DAO, focused on bringing Bitcoin to DeFi. The DAO's debut products are Sett, a yield aggregator, and Digg, a BTC-pegged elastic supply currency.

Visit our [GitBook](https://app.gitbook.com/@badger-finance/s/badger-finance/) for more detailed documentation.

## Build
The Badger contracts & tests are built around the [Eth-Brownie](https://eth-brownie.readthedocs.io/en/stable/install.html) Python framework.

If you're not familiar with brownie, see the [quickstart guide](https://eth-brownie.readthedocs.io/en/stable/quickstart.html).


### Dependencies
- Python 3.9 
- Node.js 10.x development environment (for Ganache).
- [Eth-Brownie](https://eth-brownie.readthedocs.io/en/stable/install.html) 
- Ganache (v6.12.1)

### Install
```bash
git clone https://github.com/Badger-Finance/badger-system
cd badger-system
yarn install --lock-file
python3 -m venv venv
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
Run a local ganache instance connected to badger contracts, with all Sett-related assets distributed to a test account specified in the TEST_ACCOUNT env variable. Assumes the default network is mainnet-fork in the brownie config. Ganache will continue to run until the process is closed.

```bash
source venv/bin/activate
brownie run scripts/local_instance.py
```

### Documentation

You can read more about Badger at our [GitBook](https://app.gitbook.com/@badger-finance/s/badger-finance/).

### Discussion

To join the community, head over to the [Discord server](https://discord.gg/CMzUcANy).
