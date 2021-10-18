from helpers.registry.ChainRegistry import ChainRegistry
from dotmap import DotMap
from helpers.registry.WhaleRegistryAction import WhaleRegistryAction


gnosis_safe_registry = DotMap(
    addresses=DotMap(
        proxyFactory="0x76E2cFc1F5Fa8F6a5b3fC4c8F4788F0116861F9B",
        masterCopy="0x34CfAC646f301356fAa8B21e94227e3583Fe3F5F",
    ),
)
pancake_registry = DotMap(
    cake="0x0e09fabb73bd3ade0a17ecc321fd13a19e81ce82",
    syrup="0x009cF7bC57584b7998236eff51b98A168DceA9B0",
    masterChef="0x73feaa1eE314F8c655E354234017bE2193C9E24E",
    factoryV1="0xBCfCcbde45cE874adCB698cC183deBcF17952812",
    routerV1="0x05fF2B0DB69458A0750badebc4f9e13aDd608C7F",
    factoryV2="0xca143ce32fe78f1f7019d7d551a6402fc5350c73",
    routerV2="0x10ED43C718714eb63d5aA57B78B54704E256024E",
    smartChefs="0xe4dD0C50fb314A8B2e84D211546F5B57eDd7c2b9",
    chefPairs=DotMap(
        bnbBtcb="0x7561EEe90e24F3b348E1087A005F78B4c8453524",
        bBadgerBtcb="0x10f461ceac7a17f59e249954db0784d42eff5db5",
        bDiggBtcb="0xE1E33459505bB3763843a426F7Fd9933418184ae",
    ),
    pairsV2=DotMap(
        bnbBtcb="0x61EB789d75A95CAa3fF50ed7E47b96c132fEc082",
        bBadgerBtcb="0x5A58609dA96469E9dEf3fE344bC39B00d18eb9A5",
        bDiggBtcb="0x81d776C90c89B8d51E9497D58338933127e2fA80",
    ),
    chefPids=DotMap(
        bnbBtcb=15,
        bBadgerBtcb=0,
        bDiggBtcb=104,
    ),
    pidsV2=DotMap(
        bnbBtcb=262,
        bBadgerBtcb=332,
        bDiggBtcb=331,
    ),
)
multicall_registry = DotMap(
    multicall="0xE1dDc30f691CA671518090931e3bFC1184BFa4Aa",
)
sushi_registry = DotMap(
    sushiToken="",
    xsushiToken="",
    sushiChef="",
    router="",
    factory="",
    lpTokens=DotMap(
        sushiBadgerWBtc="",
        sushiWbtcWeth="",
    ),
    pids=DotMap(sushiBadgerWBtc=0, sushiEthWBtc=0),
)
token_registry = DotMap(
    bnb="0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c",
    btcb="0x7130d2A12B9BCbFAe4f2634d864A1Ee1Ce3Ead9c",
    usdc="0x8ac76a51cc950d9822d68b83fe1ad97b32cd580d",
    bBadger="0x1F7216fdB338247512Ec99715587bb97BBf96eae",
    bDigg="0x5986D5c77c65e5801a5cAa4fAE80089f870A71dA",
)

bsc_registry = ChainRegistry(
    sushiswap=sushi_registry,
    sushi=sushi_registry,
    multicall=multicall_registry,
    pancake=pancake_registry,
    tokens=token_registry,
)

bsc_registry.whales = DotMap(
    bnbBtcb=DotMap(
        whale=bsc_registry.pancake.masterChef,
        token=bsc_registry.pancake.chefPairs.bnbBtcb,
        action=WhaleRegistryAction.DISTRIBUTE_FROM_CONTRACT,
    ),
    bDiggBtcb=DotMap(
        whale=bsc_registry.pancake.masterChef,
        token=bsc_registry.pancake.chefPairs.bDiggBtcb,
        action=WhaleRegistryAction.DISTRIBUTE_FROM_CONTRACT,
    ),
    bBadgerBtcb=DotMap(
        whale=bsc_registry.pancake.masterChef,
        token=bsc_registry.pancake.chefPairs.bBadgerBtcb,
        action=WhaleRegistryAction.DISTRIBUTE_FROM_CONTRACT,
    ),
    # Need these for `test_simulation.py` on bsc
    bnb=DotMap(
        whale="0xd7D069493685A581d27824Fc46EdA46B7EfC0063",
        token=bsc_registry.tokens.bnb,
        action=WhaleRegistryAction.DISTRIBUTE_FROM_CONTRACT,
    ),
    btcb=DotMap(
        whale="0x631Fc1EA2270e98fbD9D92658eCe0F5a269Aa161",
        token=bsc_registry.tokens.btcb,
        action=WhaleRegistryAction.DISTRIBUTE_FROM_CONTRACT,
    ),
    bBadger=DotMap(
        whale="0x5a58609da96469e9def3fe344bc39b00d18eb9a5",
        token=bsc_registry.tokens.bBadger,
        action=WhaleRegistryAction.DISTRIBUTE_FROM_CONTRACT,
    ),
    bDigg=DotMap(
        whale="0x81d776c90c89b8d51e9497d58338933127e2fa80",
        token=bsc_registry.tokens.bDigg,
        action=WhaleRegistryAction.DISTRIBUTE_FROM_CONTRACT,
    ),
    pancakebBadgerbtcb=DotMap(
        whale="0x2A842e01724F10d093aE8a46A01e66DbCf3C7373",
        token=bsc_registry.tokens.bDigg,
        action=WhaleRegistryAction.DISTRIBUTE_FROM_CONTRACT,
    ),
)
