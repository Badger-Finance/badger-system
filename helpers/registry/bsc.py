from dotmap import DotMap
from helpers.registry.WhaleRegistryAction import WhaleRegistryAction

bsc_registry = DotMap(
    gnosis_safe_registry=DotMap(
        addresses=DotMap(
            proxyFactory="0x76E2cFc1F5Fa8F6a5b3fC4c8F4788F0116861F9B",
            masterCopy="0x34CfAC646f301356fAa8B21e94227e3583Fe3F5F",
        ),
    ),
    pancake=DotMap(
        cake="0x0e09fabb73bd3ade0a17ecc321fd13a19e81ce82",
        syrup="0x009cF7bC57584b7998236eff51b98A168DceA9B0",
        masterChef="0x73feaa1eE314F8c655E354234017bE2193C9E24E",
        factoryV2="0xBCfCcbde45cE874adCB698cC183deBcF17952812",
        routerV2="0x05fF2B0DB69458A0750badebc4f9e13aDd608C7F",
        smartChefs="0xe4dD0C50fb314A8B2e84D211546F5B57eDd7c2b9",
        chefPairs=DotMap(
            bnbBtcb="0x7561EEe90e24F3b348E1087A005F78B4c8453524",
            bBadgerBtcb="0x10f461ceac7a17f59e249954db0784d42eff5db5",
            bDiggBtcb="0xE1E33459505bB3763843a426F7Fd9933418184ae",
        ),
        chefPids=DotMap(
            bnbBtcb=15,
            bBadgerBtcb=0,
            bDiggBtcb=104,
        ),
    ),
    multicall=DotMap(multicall="0xE1dDc30f691CA671518090931e3bFC1184BFa4Aa",),
    sushi=DotMap(
        sushiToken="",
        xsushiToken="",
        sushiChef="",
        router="",
        factory="",
        lpTokens=DotMap(sushiBadgerWBtc="", sushiWbtcWeth="",),
        pids=DotMap(sushiBadgerWBtc=0, sushiEthWBtc=0),
    ),
    token_registry=DotMap(
        bnb="0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c",
        btcb="0x7130d2A12B9BCbFAe4f2634d864A1Ee1Ce3Ead9c",
        usdc="0x8ac76a51cc950d9822d68b83fe1ad97b32cd580d",
        bBadger="0x1F7216fdB338247512Ec99715587bb97BBf96eae",
        bDigg="0x5986D5c77c65e5801a5cAa4fAE80089f870A71dA",
    ),
)

# bsc_registry.tokens = DotMap(
#     bnb="0x7561EEe90e24F3b348E1087A005F78B4c8453524",
#     btcb="0x7130d2a12b9bcbfae4f2634d864a1ee1ce3ead9c",
#     usdc="0x8ac76a51cc950d9822d68b83fe1ad97b32cd580d",
# )

bsc_registry.whale_registry = DotMap(
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
    # bnb=DotMap(
    #     whale="0x1B82850E491e6176170b32eC3f29AF48Eb2Fe372",
    #     token=bsc_registry.token_registry.bnb,
    #     action=WhaleRegistryAction.DISTRIBUTE_FROM_CONTRACT,
    # ),
    # btcb=DotMap(
    #     whale="0x631Fc1EA2270e98fbD9D92658eCe0F5a269Aa161",
    #     token=bsc_registry.token_registry.btcb,
    #     action=WhaleRegistryAction.DISTRIBUTE_FROM_CONTRACT,
    # ),
)

