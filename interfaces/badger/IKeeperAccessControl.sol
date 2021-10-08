// SPDX-License-Identifier: MIT
pragma solidity >=0.5.0 <0.8.0;

interface IKeeperAccessControl {
    // ===== Permissioned Functions: Earner (Move money into strategy positions) =====
    function deposit(address strategy) external;

    function earn(address sett) external;

    // ===== Permissioned Functions: Tender =====
    function tend(address strategy) external;

    // ===== Permissioned Functions: Harvester =====
    function harvest(address strategy) external returns (uint256);

    function harvestNoReturn(address strategy) external;
}
