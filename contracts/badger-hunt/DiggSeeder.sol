//SPDX-License-Identifier: MIT
pragma solidity ^0.6.11;

import "deps/@openzeppelin/contracts-upgradeable/access/OwnableUpgradeable.sol";
import "interfaces/badger/IBadgerGeyser.sol";
import "interfaces/badger/IAccessControl.sol";
import "interfaces/uniswap/IStakingRewards.sol";
import "interfaces/uniswap/IUniswapRouterV2.sol";
import "interfaces/badger/IPausable.sol";
import "interfaces/badger/IOwnable.sol";
import "interfaces/digg/IDiggDistributor.sol";
import "interfaces/digg/IDigg.sol";
import "interfaces/digg/IDiggRewardsFaucet.sol";

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
    address public airdrop;

    address constant uniRouter = 0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D;
    address constant sushiRouter = 0xd9e1cE17f2641f24aE83637ab66a2cca9C378B9F;
    address constant digg = 0x798D1bE841a82a273720CE31c822C61a67a601C3;
    address constant wbtc = 0x2260FAC5E5542a773Aa44fBCfeDf7C193bc2C599;
    address constant badger = 0x3472A5A71965499acd81997a54BBA8D852C6E53d;
    address constant badgerTree = 0x660802Fc641b154aBA66a62137e71f331B6d787A;

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

    address constant native_sushiWbtcEth_digg_faucet = 0xec48D3eD49432FFE64f39b6EB559d0fa7AC9cc90;
    address constant native_uniDiggWbtc_digg_faucet = 0xB45e51485ff078E85D9fF29c3AC0CbD9351cEBb1;
    address constant native_sushiDiggWbtc_digg_faucet = 0xF2E434772FC12705E823B2683703ee6cd8d19744;

    // ===== Initial DIGG Emissions =====
    uint256 constant native_uniBadgerWbtc_fragments = 13960000000;
    uint256 constant native_sushiBadgerWbtc_fragments = 13960000000;
    uint256 constant native_badger_fragments = 6980000000;
    uint256 constant native_renCrv_fragments = 10920000000;
    uint256 constant native_sbtcCrv_fragments = 10920000000;
    uint256 constant native_tbtcCrv_fragments = 10920000000;
    uint256 constant harvest_renCrv_fragments = 10920000000;
    uint256 constant native_sushiWbtcEth_fragments = 10920000000;

    uint256 constant native_uniDiggWbtc_fragments = 32600000000;
    uint256 constant native_sushiDiggWbtc_fragments = 32600000000;

    // Note: Native DIGG emissions are only released via DiggFaucet
    uint256 constant native_digg_fragments = 16300000000;

    // ===== Initial Badger Emissions =====
    uint256 constant native_uniBadgerWbtc_badger_emissions = 28775 ether;
    uint256 constant native_sushiBadgerWbtc_badger_emissions = 28775 ether;
    uint256 constant native_badger_badger_emissions = 14387 ether;
    uint256 constant native_renCrv_badger_emissions = 22503 ether;
    uint256 constant native_sbtcCrv_badger_emissions = 22503 ether;
    uint256 constant native_tbtcCrv_badger_emissions = 22503 ether;
    uint256 constant harvest_renCrv_badger_emissions = 22503 ether;
    uint256 constant native_sushiWbtcEth_badger_emissions = 22503 ether;

    uint256 constant initial_liquidity_wbtc = 100000000;
    uint256 constant initial_liquidity_digg = 1000000000;

    uint256 constant initial_tree_digg_supply = 23282857143; // 2 days worth of emissions to start, 81.49 a week, rounded up

    uint256 constant DIGG_TOTAL_SUPPLY = 4000000000000;
    uint256 constant LIQUIDITY_MINING_SUPPLY = (DIGG_TOTAL_SUPPLY * 40) / 100;
    uint256 constant DAO_TREASURY_SUPPLY = (DIGG_TOTAL_SUPPLY * 40) / 100;
    uint256 constant TEAM_VESTING_SUPPLY = (DIGG_TOTAL_SUPPLY * 5) / 100;
    uint256 constant AIRDROP_SUPPLY = (DIGG_TOTAL_SUPPLY * 15) / 100;

    uint256 constant badger_next_schedule_start = 1611424800;

    uint256 constant duration = 6 days;

    bytes32 public constant DEFAULT_ADMIN_ROLE = 0x00;
    bytes32 public constant TOKEN_LOCKER_ROLE = keccak256("TOKEN_LOCKER_ROLE");

    bool public seeded;

    function initialize(address airdrop_) public initializer {
        __Ownable_init();
        airdrop = airdrop_;
    }

    function preSeed() external onlyOwner {
        // airdrop_pct = 15% - initial test accounts
        require(IDigg(digg).transfer(airdrop, AIRDROP_SUPPLY - 4000000000), "transfer airdrop");
        require(IDigg(digg).balanceOf(airdrop) > AIRDROP_SUPPLY - 4000000000, "AIRDROP_SUPPLY");
        require(IDiggDistributor(airdrop).isOpen() == false, "airdrop open");
    }

    function seed() external onlyOwner {
        require(seeded == false, "Already Seeded");
        // ===== Configure Emissions Schedules =====
        /*
            All DIGG Schedules are denominated in Shares
        */

        address[10] memory geysers = [
            native_uniBadgerWbtc_geyser,
            native_sushiBadgerWbtc_geyser,
            native_badger_geyser,
            native_renCrv_geyser,
            native_sbtcCrv_geyser,
            native_tbtcCrv_geyser,
            harvest_renCrv_geyser,
            native_sushiWbtcEth_geyser,
            native_uniDiggWbtc_geyser,
            native_sushiDiggWbtc_geyser
        ];

        uint256[10] memory digg_emissions = [
            native_uniBadgerWbtc_fragments,
            native_sushiBadgerWbtc_fragments,
            native_badger_fragments,
            native_renCrv_fragments,
            native_sbtcCrv_fragments,
            native_tbtcCrv_fragments,
            harvest_renCrv_fragments,
            native_sushiWbtcEth_fragments,
            native_uniDiggWbtc_fragments,
            native_sushiDiggWbtc_fragments
        ];

        uint256[10] memory badger_emissions = [
            native_uniBadgerWbtc_badger_emissions,
            native_sushiBadgerWbtc_badger_emissions,
            native_badger_badger_emissions,
            native_renCrv_badger_emissions,
            native_sbtcCrv_badger_emissions,
            native_tbtcCrv_badger_emissions,
            harvest_renCrv_badger_emissions,
            native_sushiWbtcEth_badger_emissions,
            0,
            0
        ];

        for (uint256 i = 0; i < geysers.length; i++) {
            IBadgerGeyser geyser = IBadgerGeyser(geysers[i]);

            // ===== DIGG Geyser Emissions =====
            // Note: native_uniDiggWbtc & native_sushiDiggWbtc distribute half of DIGG emissions through DiggFaucet
            if (i == 8 || i == 9) {
                geyser.signalTokenLock(digg, IDigg(digg).fragmentsToShares(digg_emissions[i] / 2), duration, now);
            } else {
                geyser.signalTokenLock(digg, IDigg(digg).fragmentsToShares(digg_emissions[i]), duration, now);
            }

            // ===== BADGER Geyser Emissions =====
            // native_uniBadgerWbtc & native_sushiBadgerWbtc & native_badger distribute half of BADGER emissions through StakingRewards
            if (i == 0 || i == 1 || i == 2) {
                geyser.signalTokenLock(badger, badger_emissions[i] / 2, duration, badger_next_schedule_start);
            } else if (i == 8 || i == 9) {
                // Note: native_uniDiggWbtc & native_sushiDiggWbtc have no badger schedule
            } else {
                geyser.signalTokenLock(badger, badger_emissions[i], duration, badger_next_schedule_start);
            }

            IAccessControl(address(geyser)).renounceRole(TOKEN_LOCKER_ROLE, address(this));
        }

        address[3] memory faucets = [native_sushiWbtcEth_digg_faucet, native_uniDiggWbtc_digg_faucet, native_sushiDiggWbtc_digg_faucet];
        uint256[3] memory digg_emissions_faucet = [native_digg_fragments, native_uniDiggWbtc_fragments, native_sushiDiggWbtc_fragments];

        /*
            Transfer appropriate DIGG fragments to the faucet
            This value is HALF the stated emissions (half goes to geyser, except in the case of native DIGG)
            Renounce the ability to set rewards for safety
        */
        for (uint256 i = 0; i < faucets.length; i++) {
            IDiggRewardsFaucet rewards = IDiggRewardsFaucet(faucets[i]);

            // Native DIGG has 100% emissions through Faucet, LP has 50% emissions
            uint256 fragments = digg_emissions_faucet[i];
            if (i != 0) {
                fragments = digg_emissions_faucet[i] / 2;
            }
            require(IDigg(digg).transfer(address(rewards), fragments), "faucet transfer");
            rewards.notifyRewardAmount(now, duration, fragments);
            IAccessControl(address(rewards)).renounceRole(DEFAULT_ADMIN_ROLE, address(this));
        }

        // ===== Tree Initial DIGG Supply - 2 days of emissions =====
        require(IDigg(digg).transfer(badgerTree, initial_tree_digg_supply), "badgerTree");

        // ===== Lock Initial Liquidity =====
        IDigg(digg).approve(uniRouter, initial_liquidity_digg);
        IDigg(wbtc).approve(uniRouter, initial_liquidity_wbtc);

        IUniswapRouterV2(uniRouter).addLiquidity(
            digg,
            wbtc,
            initial_liquidity_digg,
            initial_liquidity_wbtc,
            initial_liquidity_digg,
            initial_liquidity_wbtc,
            rewardsEscrow,
            now
        );

        IDigg(digg).approve(sushiRouter, initial_liquidity_digg);
        IDigg(wbtc).approve(sushiRouter, initial_liquidity_wbtc);

        IUniswapRouterV2(sushiRouter).addLiquidity(
            digg,
            wbtc,
            initial_liquidity_digg,
            initial_liquidity_wbtc,
            initial_liquidity_digg,
            initial_liquidity_wbtc,
            rewardsEscrow,
            now
        );

        // ===== Initial DIGG Distribution =====

        // dao_treasury_pct = 40%
        require(IDigg(digg).transfer(daoDiggTimelock, DAO_TREASURY_SUPPLY), "transfer DAO_TREASURY_SUPPLY");

        // team_vesting_pct = 5%
        require(IDigg(digg).transfer(teamVesting, TEAM_VESTING_SUPPLY), "transfer TEAM_VESTING_SUPPLY");

        uint256 remainingBalance = IDigg(digg).balanceOf(address(this));

        // liquidity_mining_pct = 40% - already distributed
        require(LIQUIDITY_MINING_SUPPLY > remainingBalance, "Excess DIGG remaining");
        require(IDigg(digg).transfer(rewardsEscrow, remainingBalance), "transfer LIQUIDITY_MINING_SUPPLY");

        require(IDigg(digg).balanceOf(rewardsEscrow) == remainingBalance, "LIQUIDITY_MINING_SUPPLY");
        require(IDigg(digg).balanceOf(daoDiggTimelock) == DAO_TREASURY_SUPPLY, "DAO_TREASURY_SUPPLY");
        require(IDigg(digg).balanceOf(teamVesting) == TEAM_VESTING_SUPPLY, "TEAM_VESTING_SUPPLY");

        // ===== Open Airdrop & Transfer to Multisig =====
        IDiggDistributor(airdrop).openAirdrop();
        IOwnable(airdrop).transferOwnership(devMultisig);

        require(IDiggDistributor(airdrop).isOpen() == true, "airdrop open");

        seeded = true;
    }
}
