// SPDX-License-Identifier: GPL-3.0
pragma solidity >=0.6.0 <0.7.0;
pragma experimental ABIEncoderV2;

import "deps/@openzeppelin/contracts-upgradeable/utils/EnumerableSetUpgradeable.sol";
import "deps/@openzeppelin/contracts-upgradeable/proxy/Initializable.sol";

// Data from Vault
struct StrategyParams {
    uint256 performanceFee;
    uint256 activation;
    uint256 debtRatio;
    uint256 minDebtPerHarvest;
    uint256 maxDebtPerHarvest;
    uint256 lastReport;
    uint256 totalDebt;
    uint256 totalGain;
    uint256 totalLoss;
}

interface VaultView {
    function name() external view returns (string memory);

    function symbol() external view returns (string memory);

    function token() external view returns (address);

    function strategies(address _strategy) external view returns (StrategyParams memory);

    function pendingGovernance() external view returns (address);

    function governance() external view returns (address);

    function management() external view returns (address);

    function guardian() external view returns (address);

    function rewards() external view returns (address);

    function withdrawalQueue(uint256 index) external view returns (address);
}

interface StratView {
    function name() external view returns (string memory);

    function strategist() external view returns (address);

    function rewards() external view returns (address);

    function keeper() external view returns (address);
}

contract BadgerRegistryV2 is Initializable {
    using EnumerableSetUpgradeable for EnumerableSetUpgradeable.AddressSet;

    //@dev Multisig. Vaults from here are considered Production ready
    address public governance;

    //@dev Given an Author Address, and Token, Return the Vault
    mapping(address => EnumerableSetUpgradeable.AddressSet) private vaults;

    event NewVault(address author, address vault);
    event RemoveVault(address author, address vault);
    event PromoteVault(address author, address vault);

    //@dev View Data for each strat we will return
    struct StratInfo {
        address at;
        string name;
        address strategist;
        address rewards;
        address keeper;
        uint256 performanceFee;
        uint256 activation;
        uint256 debtRatio;
        uint256 minDebtPerHarvest;
        uint256 maxDebtPerHarvest;
        uint256 lastReport;
        uint256 totalDebt;
        uint256 totalGain;
        uint256 totalLoss;
    }

    /// Vault data we will return for each Vault
    struct VaultInfo {
        address at;
        string name;
        string symbol;
        address token;
        address pendingGovernance; // If this is non zero, this is an attack from the deployer
        address governance;
        address rewards;
        address guardian;
        address management;
        StratInfo[] strategies;
    }

    function initialize(address _governance) public initializer {
        governance = _governance;
    }

    function setGovernance(address _newGov) public {
        require(msg.sender == governance, "!gov");
        governance = _newGov;
    }

    /// Anyone can add a vault to here, it will be indexed by their address
    function add(address vault) public {
        bool added = vaults[msg.sender].add(vault);
        if (added) {
            emit NewVault(msg.sender, vault);
        }
    }

    /// Remove the vault from your index
    function remove(address vault) public {
        bool removed = vaults[msg.sender].remove(vault);
        if (removed) {
            emit RemoveVault(msg.sender, vault);
        }
    }

    //@dev Retrieve a list of all Vault Addresses from the given author
    function fromAuthor(address author) public view returns (address[] memory) {
        uint256 length = vaults[author].length();
        address[] memory list = new address[](length);
        for (uint256 i = 0; i < length; i++) {
            list[i] = vaults[author].at(i);
        }
        return list;
    }

    //@dev Retrieve a list of all Vaults and the basic Vault info
    function fromAuthorVaults(address author) public view returns (VaultInfo[] memory) {
        uint256 length = vaults[author].length();

        VaultInfo[] memory vaultData = new VaultInfo[](length);
        for (uint256 x = 0; x < length; x++) {
            VaultView vault = VaultView(vaults[author].at(x));
            StratInfo[] memory allStrats = new StratInfo[](0);

            VaultInfo memory data = VaultInfo({
                at: vaults[author].at(x),
                name: vault.name(),
                symbol: vault.symbol(),
                token: vault.token(),
                pendingGovernance: vault.pendingGovernance(),
                governance: vault.governance(),
                rewards: vault.rewards(),
                guardian: vault.guardian(),
                management: vault.management(),
                strategies: allStrats
            });

            vaultData[x] = data;
        }
        return vaultData;
    }

    //@dev Given the Vault, retrieve all the data as well as all data related to the strategies
    function fromAuthorWithDetails(address author) public view returns (VaultInfo[] memory) {
        uint256 length = vaults[author].length();
        VaultInfo[] memory vaultData = new VaultInfo[](length);

        for (uint256 x = 0; x < length; x++) {
            VaultView vault = VaultView(vaults[author].at(x));

            // TODO: Strat Info with real data
            uint256 stratCount = 0;
            for (uint256 y = 0; y < 20; y++) {
                if (vault.withdrawalQueue(y) != address(0)) {
                    stratCount++;
                }
            }
            StratInfo[] memory allStrats = new StratInfo[](stratCount);

            for (uint256 z = 0; z < stratCount; z++) {
                StratView strat = StratView(vault.withdrawalQueue(z));
                StrategyParams memory params = vault.strategies(vault.withdrawalQueue(z));
                StratInfo memory stratData = StratInfo({
                    at: vault.withdrawalQueue(z),
                    name: strat.name(),
                    strategist: strat.strategist(),
                    rewards: strat.rewards(),
                    keeper: strat.keeper(),
                    performanceFee: params.performanceFee,
                    activation: params.activation,
                    debtRatio: params.debtRatio,
                    minDebtPerHarvest: params.minDebtPerHarvest,
                    maxDebtPerHarvest: params.maxDebtPerHarvest,
                    lastReport: params.lastReport,
                    totalDebt: params.totalDebt,
                    totalGain: params.totalGain,
                    totalLoss: params.totalLoss
                });
                allStrats[z] = stratData;
            }

            VaultInfo memory data = VaultInfo({
                at: vaults[author].at(x),
                name: vault.name(),
                symbol: vault.symbol(),
                token: vault.token(),
                pendingGovernance: vault.pendingGovernance(),
                governance: vault.governance(),
                rewards: vault.rewards(),
                guardian: vault.guardian(),
                management: vault.management(),
                strategies: allStrats
            });

            vaultData[x] = data;
        }

        return vaultData;
    }

    //@dev Promote a vault to Production
    //@dev Promote just means indexed by the Governance Address
    function promote(address vault) public {
        require(msg.sender == governance, "!gov");
        bool promoted = vaults[msg.sender].add(vault);

        if (promoted) {
            emit PromoteVault(msg.sender, vault);
        }
    }
}
