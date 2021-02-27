# Layout Upgradeable

In order to maintain layout backwards compatibilty w/ different versions of contracts (e.g. Sett).

Changelog:

V1.1
* Strategist no longer has special function calling permissions
* Version function added to contract
* All write functions, with the exception of transfer, are pausable
* Keeper or governance can pause
* Only governance can unpause

V1.2
* Transfer functions are now pausable along with all other non-permissioned write functions
* All permissioned write functions, with the exception of pause() & unpause(), are pausable as well

V1.3
* Withdrawals are processed from idle want in sett.


"SettV1": "0xE4Ae305b08434bF3D74e0086592627F913a258A9",
"SettV1.1": "0x175586ac3f8A7463499D1019A30120aa6fC67C5f",

Old:
           "native.badger": "0x19D97D8fA813EE2f51aD4B4e04EA08bAf4DFfC28",
            "native.renCrv": "0x6dEf55d2e18486B9dDfaA075bc4e4EE0B28c1545",
            "native.sbtcCrv": "0xd04c48A53c111300aD41190D63681ed3dAd998eC",
            "native.tbtcCrv": "0xb9D076fDe463dbc9f915E5392F807315Bf940334",
            "native.uniBadgerWbtc": "0x235c9e24D3FB2FAFd58a2E49D454Fdcd2DBf7FF1",
            "harvest.renCrv": "0xAf5A1DECfa95BAF63E0084a35c62592B774A2A87",
New:
            "native.sushiWbtcEth": "0x758A43EE2BFf8230eeb784879CdcFF4828F2544D",
            "native.sushiBadgerWbtc": "0x1862A18181346EBd9EdAf800804f89190DeF24a5",
            "native.digg": "0x7e7E112A68d8D2E221E11047a72fFC1065c38e1a",
            "native.uniDiggWbtc": "0xC17078FDd324CC473F8175Dc5290fae5f2E84714",
            "native.sushiDiggWbtc": "0x88128580ACdD9c04Ce47AFcE196875747bF2A9f6"
