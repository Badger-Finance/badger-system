// SPDX-License-Identifier: MIT
pragma solidity >=0.5.0 <0.8.0;

interface ICurveRegistry {
    function find_pool_for_coins(
        address _from,
        address _to,
        uint256 _index
    ) external returns (address);

    function get_coin_indices(
        address _pool,
        address _from,
        address _to
    )
        external
        returns (
            int128,
            int128,
            bool
        );
}
