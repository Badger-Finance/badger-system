pragma solidity 0.6.12;

interface IUnitVaultParameters {
    function tokenDebtLimit(address asset) external view returns (uint256);
}

interface IUnitVault {
    function calculateFee(
        address asset,
        address user,
        uint256 amount
    ) external view returns (uint256);

    function getTotalDebt(address asset, address user) external view returns (uint256);

    function debts(address asset, address user) external view returns (uint256);

    function collaterals(address asset, address user) external view returns (uint256);

    function tokenDebts(address asset) external view returns (uint256);
}

interface IUnitCDPManager {
    function exit(
        address asset,
        uint256 assetAmount,
        uint256 usdpAmount
    ) external returns (uint256);

    function join(
        address asset,
        uint256 assetAmount,
        uint256 usdpAmount
    ) external;
	
    function oracleRegistry() external view returns (address);
}

interface IUnitUsdOracle {
    // returns Q112-encoded value
    // returned value 10**18 * 2**112 is $1
    function assetToUsd(address asset, uint amount) external view returns (uint);
}

interface IUnitOracleRegistry {
    function oracleByAsset(address asset) external view returns (address);
}
