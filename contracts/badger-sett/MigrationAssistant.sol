// SPDX-License-Identifier: MIT

pragma solidity ^0.6.11;
pragma experimental ABIEncoderV2;

import "interfaces/badger/ISett.sol";
import "interfaces/badger/IStrategy.sol";
import "interfaces/badger/IController.sol";
import "interfaces/convex/IBaseRewardsPool.sol";

contract MigrationAssistant {
    event Debug(uint256 value);
    event DebugAddress(address value);

    struct MigrationParams {
        address want;
        address beforeStrategy;
        address afterStrategy;
    }

    function migrate(IController controller, MigrationParams[] memory migrations) public {
        for (uint256 i = 0; i < migrations.length; i++) {
            MigrationParams memory params = migrations[i];

            ISett sett = ISett(controller.vaults(params.want));
            IStrategy beforeStrategy = IStrategy(params.beforeStrategy);
            IStrategy afterStrategy = IStrategy(params.afterStrategy);

            // ===== Pre Verification =====
            // Strategies must have same want
            require(beforeStrategy.want() == afterStrategy.want(), "strategy-want-mismatch");
            require(afterStrategy.want() == sett.token(), "strategy-sett-want-mismatch");
            require(params.want == sett.token(), "want-param-mismatch");
            require(beforeStrategy.controller() == afterStrategy.controller(), "strategy-controller-mismatch");
            // require(beforeStrategy.governance() == afterStrategy.governance(), "strategy-governance-mismatch");

            require(beforeStrategy.controller() == address(controller), "before-strategy-controller-mismatch");
            require(afterStrategy.controller() == address(controller), "after-strategy-controller-mismatch");

            uint256 beforeBalance = sett.balance();
            uint256 beforePpfs = sett.getPricePerFullShare();

            // ===== Run Migration =====
            controller.setStrategy(params.want, params.afterStrategy);

            uint256 afterBalance = sett.balance();
            uint256 afterPpfs = sett.getPricePerFullShare();

            // ===== Post Verification =====
            // Strategy must report same total balance
            require(afterBalance == beforeBalance, "sett-balance-mismatch");

            // PPFS must not change
            require(beforePpfs == afterPpfs, "ppfs-mismatch");
        }
    }
}
