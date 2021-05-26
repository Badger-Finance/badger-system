//  SPDX-License-Identifier: MIT

pragma solidity >=0.6.0;

// Meta token calls are proxied through bridge token contracts so that we can support
// a many (bridges) to one (meta token) relationship.
interface IMetaToken {
    // Deposited tokens from root chain -> child chain.
    function deposit(address _to, uint256 _amount) external;

    // Withdrawn tokens from child chain -> root chain.
    function withdraw(address _from, uint256 _amount) external;
}
