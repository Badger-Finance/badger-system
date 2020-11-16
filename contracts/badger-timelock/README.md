![Badger Logo](../../images/badger-logo.png)

# Smart Timelock & Vesting
The SmartTimelock and SmartVesting are expansions of the OpenZeppelin [OpenZeppelin Timelock](https://github.com/OpenZeppelin/openzeppelin-contracts/blob/master/contracts/token/ERC20/TokenTimelock.sol)  and [OpenZeppelin Vesting](https://github.com/OpenZeppelin/openzeppelin-contracts/blob/release-v3.0.0/contracts/drafts/TokenVesting.sol) contracts that are capable of executing arbitrary calls as long as the balance of the locked token does not decrease.

They incorporate a limited version of the [Gnosis Safe Executor](https://github.com/gnosis/safe-contracts/blob/development/contracts/base/Executor.sol) to allow flexible external calls. The ability to use delegateCall is removed for security reasons.

These external contract calls are gated with the following requirements:
* Only the beneficiary may call these functions.
* The Timelock's balance of the locked token MUST NOT decrease from before to after the call. This ensures that the tokens cannot be spent before the timelock period is complete.

There are safety functions for the beneficiary to withdraw the balance of tokens (other than the locked token) and ether sent to the contract, accidentially or otherwise.

Once the timelock period is complete, the locked tokens can be withdrawn via the standard method. For vesting, the appropriate number of vested tokens can always be withdrawn.

## Governor
Optionally, SmartLocks may assign a governor contract which can allow the timelock to send it's locked tokens to approved addresses, bypassing the balance rules. This is intended to allow staking of the locked assets in approved contracts, without truly transferring them. However, many types of functionality could be implemented using this feature along with special contracts.

## Usage
- Test

    ```brownie test tests/badger-timelock```
