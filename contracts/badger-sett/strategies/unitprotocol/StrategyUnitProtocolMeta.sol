pragma solidity 0.6.12;
pragma experimental ABIEncoderV2;

import "../BaseStrategy.sol";

import "deps/@openzeppelin/contracts-upgradeable/math/SafeMathUpgradeable.sol";
import "deps/@openzeppelin/contracts-upgradeable/utils/AddressUpgradeable.sol";
import "deps/@openzeppelin/contracts-upgradeable/token/ERC20/SafeERC20Upgradeable.sol";

import "../../../../interfaces/unitprotocol/IUnitProtocol.sol";
import "../../../../interfaces/chainlink/IChainlink.sol";

abstract contract StrategyUnitProtocolMeta is BaseStrategy {
    using SafeERC20Upgradeable for IERC20Upgradeable;
    using AddressUpgradeable for address;
    using SafeMathUpgradeable for uint256;

    // Unit Protocol module: https://github.com/unitprotocol/core/blob/master/CONTRACTS.md
    address public constant cdpMgr01 = 0x0e13ab042eC5AB9Fc6F43979406088B9028F66fA;
    address public constant unitVault = 0xb1cFF81b9305166ff1EFc49A129ad2AfCd7BCf19;
    address public constant unitVaultParameters = 0xB46F8CF42e504Efe8BEf895f848741daA55e9f1D;
    address public constant debtToken = 0x1456688345527bE1f37E9e627DA0837D6f08C925;
    address public constant eth_usd = 0x5f4eC3Df9cbd43714FE2740f5E3616155c5b8419;

    // sub-strategy related constants
    address public collateral;
    uint256 public collateralDecimal = 1e18;
    address public unitOracle;
    uint256 public collateralPriceDecimal = 1;
    bool public collateralPriceEth = false;

    // configurable minimum collateralization percent this strategy would hold for CDP
    uint256 public minRatio = 200;
    // collateralization percent buffer in CDP debt actions
    uint256 public ratioBuff = 200;
    uint256 public constant ratioBuffMax = 10000;

    // **** Modifiers **** //

    function _onlyCDPInUse() internal view {
        uint256 collateralAmt = getCollateralBalance();
        require(collateralAmt > 0, "!zeroCollateral");

        uint256 debtAmt = getDebtBalance();
        require(debtAmt > 0, "!zeroDebt");
    }

    // **** Getters ****

    function getCollateralBalance() public view returns (uint256) {
        return IUnitVault(unitVault).collaterals(collateral, address(this));
    }

    function getDebtBalance() public view returns (uint256) {
        return IUnitVault(unitVault).getTotalDebt(collateral, address(this));
    }

    function getDebtWithoutFee() public view returns (uint256) {
        return IUnitVault(unitVault).debts(collateral, address(this));
    }

    function debtLimit() public view returns (uint256) {
        return IUnitVaultParameters(unitVaultParameters).tokenDebtLimit(collateral);
    }

    function debtUsed() public view returns (uint256) {
        return IUnitVault(unitVault).tokenDebts(collateral);
    }

    /// @dev Balance of want currently held in strategy positions
    function balanceOfPool() public override view returns (uint256) {
        return getCollateralBalance();
    }

    function collateralValue(uint256 collateralAmt) public view returns (uint256) {
        uint256 collateralPrice = getLatestCollateralPrice();
        return collateralAmt.mul(collateralPrice).mul(1e18).div(collateralDecimal).div(collateralPriceDecimal); // debtToken in 1e18 decimal
    }

    function currentRatio() public view returns (uint256) {
        _onlyCDPInUse();
        uint256 collateralAmt = collateralValue(getCollateralBalance()).mul(100);
        uint256 debtAmt = getDebtBalance();
        return collateralAmt.div(debtAmt);
    }

    // if borrow is true (for addCollateralAndBorrow): return (maxDebt - currentDebt) if positive value, otherwise return 0
    // if borrow is false (for repayAndRedeemCollateral): return (currentDebt - maxDebt) if positive value, otherwise return 0
    function calculateDebtFor(uint256 collateralAmt, bool borrow) public view returns (uint256) {
        uint256 maxDebt = collateralValue(collateralAmt).mul(ratioBuffMax).div(_getBufferedMinRatio(ratioBuffMax));

        uint256 debtAmt = getDebtBalance();

        uint256 debt = 0;

        if (borrow && maxDebt >= debtAmt) {
            debt = maxDebt.sub(debtAmt);
        } else if (!borrow && debtAmt >= maxDebt) {
            debt = debtAmt.sub(maxDebt);
        }

        return (debt > 0) ? debt : 0;
    }

    function _getBufferedMinRatio(uint256 _multiplier) internal view returns (uint256) {
        require(ratioBuffMax > 0, "!ratioBufferMax");
        require(minRatio > 0, "!minRatio");
        return minRatio.mul(_multiplier).mul(ratioBuffMax.add(ratioBuff)).div(ratioBuffMax).div(100);
    }

    function borrowableDebt() public view returns (uint256) {
        uint256 collateralAmt = getCollateralBalance();
        return calculateDebtFor(collateralAmt, true);
    }

    function requiredPaidDebt(uint256 _redeemCollateralAmt) public view returns (uint256) {
        uint256 collateralAmt = getCollateralBalance().sub(_redeemCollateralAmt);
        return calculateDebtFor(collateralAmt, false);
    }

    // **** sub-strategy implementation ****
    function _depositUSDP(uint256 _usdpAmt) internal virtual;

    function _withdrawUSDP(uint256 _usdpAmt) internal virtual;

    // **** Oracle (using chainlink) ****

    function getLatestCollateralPrice() public view returns (uint256) {
        require(unitOracle != address(0), "!_collateralOracle");

        (, int256 price, , , ) = IChainlinkAggregator(unitOracle).latestRoundData();

        if (price > 0) {
            int256 ethPrice = 1;
            if (collateralPriceEth) {
                (, ethPrice, , , ) = IChainlinkAggregator(eth_usd).latestRoundData(); // eth price from chainlink in 1e8 decimal
            }
            return uint256(price).mul(collateralPriceDecimal).mul(uint256(ethPrice)).div(1e8).div(collateralPriceEth ? 1e18 : 1);
        } else {
            return 0;
        }
    }

    // **** Setters ****

    function setMinRatio(uint256 _minRatio) external {
        _onlyGovernance();
        minRatio = _minRatio;
    }

    function setRatioBuff(uint256 _ratioBuff) external {
        _onlyGovernance();
        ratioBuff = _ratioBuff;
    }

    // **** Unit Protocol CDP actions ****

    function addCollateralAndBorrow(uint256 _collateralAmt, uint256 _usdpAmt) internal {
        require(_usdpAmt.add(debtUsed()) < debtLimit(), "!exceedLimit");
        _safeApproveHelper(collateral, unitVault, _collateralAmt);
        IUnitCDPManager(cdpMgr01).join(collateral, _collateralAmt, _usdpAmt);
    }

    function repayAndRedeemCollateral(uint256 _collateralAmt, uint256 _usdpAmt) internal {
        _safeApproveHelper(debtToken, unitVault, _usdpAmt);
        IUnitCDPManager(cdpMgr01).exit(collateral, _collateralAmt, _usdpAmt);
    }

    // **** State Mutation functions ****

    function keepMinRatio() external {
        _onlyCDPInUse();
        _onlyAuthorizedActorsOrController();

        uint256 requiredPaidback = requiredPaidDebt(0);
        if (requiredPaidback > 0) {
            _withdrawUSDP(requiredPaidback);

            uint256 _actualPaidDebt = IERC20Upgradeable(debtToken).balanceOf(address(this));
            uint256 _fee = getDebtBalance().sub(getDebtWithoutFee());

            require(_actualPaidDebt > _fee, "!notEnoughForFee");
            _actualPaidDebt = _actualPaidDebt.sub(_fee); // unit protocol will charge fee first
            _actualPaidDebt = _capMaxDebtPaid(_actualPaidDebt);

            require(IERC20Upgradeable(debtToken).balanceOf(address(this)) >= _actualPaidDebt.add(_fee), "!notEnoughRepayment");
            repayAndRedeemCollateral(0, _actualPaidDebt);
        }
    }

    /// @dev Internal deposit logic to be implemented by Stratgies
    function _deposit(uint256 _want) internal override {
        if (_want > 0) {
            uint256 _newDebt = calculateDebtFor(_want.add(getCollateralBalance()), true);
            if (_newDebt > 0) {
                addCollateralAndBorrow(_want, _newDebt);
                uint256 wad = IERC20Upgradeable(debtToken).balanceOf(address(this));
                _depositUSDP(_newDebt > wad ? wad : _newDebt);
            }
        }
    }

    // to avoid repay all debt resulting to close the CDP unexpectedly
    function _capMaxDebtPaid(uint256 _actualPaidDebt) internal view returns (uint256) {
        uint256 _maxDebtToRepay = getDebtWithoutFee().sub(ratioBuffMax);
        return _actualPaidDebt >= _maxDebtToRepay ? _maxDebtToRepay : _actualPaidDebt;
    }

    /// @dev Internal logic for partial withdrawals. Should exit positions as efficiently as possible.
    /// @dev The withdraw() function shell automatically uses idle want in the strategy before attempting to withdraw more using this
    function _withdrawSome(uint256 _amount) internal override returns (uint256) {
        if (_amount == 0) {
            return _amount;
        }

        uint256 requiredPaidback = requiredPaidDebt(_amount);
        if (requiredPaidback > 0) {
            _withdrawUSDP(requiredPaidback);
        }

        bool _fullWithdraw = _amount == balanceOfPool();
        uint256 _wantBefore = IERC20Upgradeable(want).balanceOf(address(this));
        if (!_fullWithdraw) {
            uint256 _actualPaidDebt = IERC20Upgradeable(debtToken).balanceOf(address(this));
            uint256 _fee = getDebtBalance().sub(getDebtWithoutFee());

            require(_actualPaidDebt > _fee, "!notEnoughForFee");
            _actualPaidDebt = _actualPaidDebt.sub(_fee); // unit protocol will charge fee first
            _actualPaidDebt = _capMaxDebtPaid(_actualPaidDebt);

            require(IERC20Upgradeable(debtToken).balanceOf(address(this)) >= _actualPaidDebt.add(_fee), "!notEnoughRepayment");
            repayAndRedeemCollateral(_amount, _actualPaidDebt);
        } else {
            require(IERC20Upgradeable(debtToken).balanceOf(address(this)) >= getDebtBalance(), "!notEnoughFullRepayment");
            repayAndRedeemCollateral(_amount, getDebtBalance());
            require(getDebtBalance() == 0, "!leftDebt");
            require(getCollateralBalance() == 0, "!leftCollateral");
        }

        uint256 _wantAfter = IERC20Upgradeable(want).balanceOf(address(this));
        return _wantAfter.sub(_wantBefore);
    }

    /// @dev Internal logic for strategy migration. Should exit positions as efficiently as possible
    function _withdrawAll() internal override {
        _withdrawSome(balanceOfPool());
    }
}
