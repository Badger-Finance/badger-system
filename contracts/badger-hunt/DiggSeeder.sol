// SP-License-upgradeable-Identifier: UNLICENSED
pragma solidity ^0.6.11;

import "deps/@openzeppelin/contracts-upgradeable/access/OwnableUpgradeable.sol";
import "interfaces/badger/IBadgerGeyser.sol";
import "interfaces/badger/IAccessControl.sol";
import "interfaces/uniswap/IStakingRewards.sol";
import "interfaces/uniswap/IUniswapRouterV2.sol";
import "interfaces/badger/IPausable.sol";
import "interfaces/badger/IOwnable.sol";
import "interfaces/digg/IDigg.sol";
import "interfaces/digg/IDiggRewardsFaucet.sol";

import "./MerkleDistributor.sol";

/* ===== DiggSeeder =====
Atomically initialize DIGG
    * Set all predefined unlock schedules, starting at current time
    * Seed Uni and Sushi liquidity pools
    * Unpause airdrop
*/
contract DiggSeeder is OwnableUpgradeable {
    address constant devMultisig = 0xB65cef03b9B89f99517643226d76e286ee999e77;
    address constant rewardsEscrow = 0x19d099670a21bC0a8211a89B84cEdF59AbB4377F;
    address constant daoDiggTimelock = 0x5A54Ca44e8F5A1A695f8621f15Bfa159a140bB61;
    address constant teamVesting = 0x124FD4A9bd4914b32c77C9AE51819b1181dbb3D4;
    address constant airdrop = 0xED743eD6c78429981Ad3aaf9d2306D1E3C336010;

    address constant uniRouter = 0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D;
    address constant sushiRouter = 0xd9e1cE17f2641f24aE83637ab66a2cca9C378B9F;
    address constant digg = 0x798D1bE841a82a273720CE31c822C61a67a601C3;
    address constant wbtc = 0x2260FAC5E5542a773Aa44fBCfeDf7C193bc2C599;
    address constant badger = 0x3472A5A71965499acd81997a54BBA8D852C6E53d;

    address constant native_uniBadgerWbtc_geyser = 0xA207D69Ea6Fb967E54baA8639c408c31767Ba62D;
    address constant native_sushiBadgerWbtc_geyser = 0xB5b654efBA23596Ed49FAdE44F7e67E23D6712e7;
    address constant native_badger_geyser = 0xa9429271a28F8543eFFfa136994c0839E7d7bF77;
    address constant native_renCrv_geyser = 0x2296f174374508278DC12b806A7f27c87D53Ca15;
    address constant native_sbtcCrv_geyser = 0x10fC82867013fCe1bD624FafC719Bb92Df3172FC;
    address constant native_tbtcCrv_geyser = 0x085A9340ff7692Ab6703F17aB5FfC917B580a6FD;
    address constant harvest_renCrv_geyser = 0xeD0B7f5d9F6286d00763b0FFCbA886D8f9d56d5e;
    address constant native_sushiWbtcEth_geyser = 0x612f681BCd12A0b284518D42D2DBcC73B146eb65;
    address constant native_uniDiggWbtc_geyser = 0x0194B5fe9aB7e0C43a08aCbb771516fc057402e7;
    address constant native_sushiDiggWbtc_geyser = 0x7F6FE274e172AC7d096A7b214c78584D99ca988B;

    uint256 constant DIGG_TOTAL_SUPPLY = 4000000000000;
    uint256 constant LIQUIDITY_MINING_SUPPLY = (DIGG_TOTAL_SUPPLY * 40) / 100;
    uint256 constant DAO_TREASURY_SUPPLY = (DIGG_TOTAL_SUPPLY * 40) / 100;
    uint256 constant TEAM_VESTING_SUPPLY = (DIGG_TOTAL_SUPPLY * 5) / 100;
    uint256 constant AIRDROP_SUPPLY = (DIGG_TOTAL_SUPPLY * 15) / 100;

    bytes32 public constant DEFAULT_ADMIN_ROLE = 0x00;
    bytes32 public constant TOKEN_LOCKER_ROLE = keccak256("TOKEN_LOCKER_ROLE");

    bool public seeded;

    function initialize() public initializer {
        __Ownable_init();
    }

    function seed() external onlyOwner {
        require(seeded == false, "Already Seeded");
        // ===== Configure Emissions Schedules =====
        /*
            All DIGG Schedules are denominated in Shares
        */

        // address badger = 0x3472a5a71965499acd81997a54bba8d852c6e53d;

        // == native.uniBadgerWbtc ==
        IBadgerGeyser geyser = IBadgerGeyser(native_uniBadgerWbtc_geyser);
        geyser.signalTokenLock(digg, IDigg(digg).fragmentsToShares(9310000000), 7 days, now);
        IAccessControl(address(geyser)).renounceRole(TOKEN_LOCKER_ROLE, address(this));

        // geyser.getUnlockSchedulesFor(digg)[0]

        // == native.sushiBadgerWbtc ==
        geyser = IBadgerGeyser(native_sushiBadgerWbtc_geyser);
        geyser.signalTokenLock(digg, IDigg(digg).fragmentsToShares(7540000000), 7 days, now);
        IAccessControl(address(geyser)).renounceRole(TOKEN_LOCKER_ROLE, address(this));

        // == native.badger ==
        geyser = IBadgerGeyser(native_badger_geyser);
        geyser.signalTokenLock(digg, IDigg(digg).fragmentsToShares(4170000000), 7 days, now);
        IAccessControl(address(geyser)).renounceRole(TOKEN_LOCKER_ROLE, address(this));

        // == native.renCrv ==
        geyser = IBadgerGeyser(native_renCrv_geyser);
        geyser.signalTokenLock(digg, IDigg(digg).fragmentsToShares(6470000000), 7 days, now);
        IAccessControl(address(geyser)).renounceRole(TOKEN_LOCKER_ROLE, address(this));

        // == native.sbtcCrv ==
        geyser = IBadgerGeyser(native_sbtcCrv_geyser);
        geyser.signalTokenLock(digg, IDigg(digg).fragmentsToShares(6470000000), 7 days, now);
        IAccessControl(address(geyser)).renounceRole(TOKEN_LOCKER_ROLE, address(this));

        // == native.tbtcCrv ==
        geyser = IBadgerGeyser(native_tbtcCrv_geyser);
        geyser.signalTokenLock(digg, IDigg(digg).fragmentsToShares(6470000000), 7 days, now);
        IAccessControl(address(geyser)).renounceRole(TOKEN_LOCKER_ROLE, address(this));

        // == harvest.renCrv ==
        geyser = IBadgerGeyser(harvest_renCrv_geyser);
        geyser.signalTokenLock(digg, IDigg(digg).fragmentsToShares(6470000000), 7 days, now);
        IAccessControl(address(geyser)).renounceRole(TOKEN_LOCKER_ROLE, address(this));

        // == native.sushiWbtcEth ==
        geyser = IBadgerGeyser(native_sushiWbtcEth_geyser);
        geyser.signalTokenLock(digg, IDigg(digg).fragmentsToShares(6470000000), 7 days, now);
        IAccessControl(address(geyser)).renounceRole(TOKEN_LOCKER_ROLE, address(this));

        // == native.uniDiggWbtc ==
        geyser = IBadgerGeyser(native_uniDiggWbtc_geyser);
        // Note: Half Auto-compounded
        geyser.signalTokenLock(digg, IDigg(digg).fragmentsToShares(21270000000 / 2), 7 days, now);
        geyser.signalTokenLock(badger, 22707 ether, 7 days, now);
        IAccessControl(address(geyser)).renounceRole(TOKEN_LOCKER_ROLE, address(this));

        // == native.sushiDiggWbtc ==
        geyser = IBadgerGeyser(native_sushiDiggWbtc_geyser);
        // Note: Half Auto-compounded
        geyser.signalTokenLock(digg, IDigg(digg).fragmentsToShares(21270000000 / 2), 7 days, now);
        geyser.signalTokenLock(badger, 22707 ether, 7 days, now);
        IAccessControl(address(geyser)).renounceRole(TOKEN_LOCKER_ROLE, address(this));

        // Add initial unlock schedules for each geyser and read back

        // ===== Populate DIGG rewards pools =====
        // Note: Requires that these are populated with tokens previously

        // == "native.digg" ==
        IDiggRewardsFaucet rewards = IDiggRewardsFaucet(0xec48D3eD49432FFE64f39b6EB559d0fa7AC9cc90);
        uint256 amountInFragments = 10630000000;
        uint256 amountInShares = IDigg(digg).fragmentsToShares(10630000000);

        IDigg(digg).transfer(address(rewards), amountInFragments);
        rewards.notifyRewardAmount(now, 7 days, amountInShares);
        IAccessControl(address(rewards)).renounceRole(DEFAULT_ADMIN_ROLE, address(this));

        // == "native.uniDiggWbtc" ==
        rewards = IDiggRewardsFaucet(0xB45e51485ff078E85D9fF29c3AC0CbD9351cEBb1);
        amountInFragments = 21270000000 / 2;
        amountInShares = IDigg(digg).fragmentsToShares(21270000000 / 2);

        // Note: Half Auto-compounded here
        IDigg(digg).transfer(address(rewards), amountInFragments);
        rewards.notifyRewardAmount(now, 7 days, amountInShares);
        IAccessControl(address(rewards)).renounceRole(DEFAULT_ADMIN_ROLE, address(this));

        // == "native.sushiDiggWbtc" ==
        rewards = IDiggRewardsFaucet(0xF2E434772FC12705E823B2683703ee6cd8d19744);
        amountInFragments = 21270000000 / 2;
        amountInShares = IDigg(digg).fragmentsToShares(21270000000 / 2);

        // Note: Half Auto-compounded here
        IDigg(digg).transfer(address(rewards), amountInFragments);
        rewards.notifyRewardAmount(now, 7 days, amountInShares);
        IAccessControl(address(rewards)).renounceRole(DEFAULT_ADMIN_ROLE, address(this));

        // ===== Lock Initial Liquidity =====
        IDigg(digg).approve(uniRouter, 1000000000);
        IDigg(wbtc).approve(uniRouter, 100000000);

        IUniswapRouterV2(uniRouter).addLiquidity(digg, wbtc, 1000000000, 100000000, 1000000000, 100000000, rewardsEscrow, now);

        IDigg(digg).approve(sushiRouter, 1000000000);
        IDigg(wbtc).approve(sushiRouter, 100000000);

        IUniswapRouterV2(sushiRouter).addLiquidity(digg, wbtc, 1000000000, 100000000, 1000000000, 100000000, rewardsEscrow, now);

        // ===== Initial DIGG Distribution =====

        // dao_treasury_pct = 40%
        IDigg(digg).transfer(daoDiggTimelock, DAO_TREASURY_SUPPLY);

        // team_vesting_pct = 5%
        IDigg(digg).transfer(teamVesting, TEAM_VESTING_SUPPLY);

        // airdrop_pct = 15%
        IDigg(digg).transfer(airdrop, AIRDROP_SUPPLY);

        uint256 remainingBalance = IDigg(digg).balanceOf(address(this));
        // liquidity_mining_pct = 40% - already distributed
        require(LIQUIDITY_MINING_SUPPLY > remainingBalance, "Excess DIGG remaining");
        IDigg(digg).transfer(rewardsEscrow, remainingBalance);

        require(IDigg(digg).balanceOf(rewardsEscrow) == remainingBalance, "LIQUIDITY_MINING_SUPPLY");
        require(IDigg(digg).balanceOf(daoDiggTimelock) == DAO_TREASURY_SUPPLY, "DAO_TREASURY_SUPPLY");
        require(IDigg(digg).balanceOf(teamVesting) == TEAM_VESTING_SUPPLY, "TEAM_VESTING_SUPPLY");
        require(IDigg(digg).balanceOf(airdrop) == AIRDROP_SUPPLY, "AIRDROP_SUPPLY");

        // ===== Unpause Airdrop =====
        // IPausable(airdrop).unpause();
        IOwnable(airdrop).transferOwnership(devMultisig);

        seeded = true;
    }
}
