from dotmap import DotMap

bsc = DotMap(
    gnosis_safe_registry=DotMap(
        addresses=DotMap(
            proxyFactory="0x76E2cFc1F5Fa8F6a5b3fC4c8F4788F0116861F9B",
            masterCopy="0x34CfAC646f301356fAa8B21e94227e3583Fe3F5F",
        ),
    ),
    pancake=DotMap(
        cake="0x0e09fabb73bd3ade0a17ecc321fd13a19e81ce82",
        masterChef="0x73feaa1eE314F8c655E354234017bE2193C9E24E",
        factoryV2="0xBCfCcbde45cE874adCB698cC183deBcF17952812",
        routerV2="0x05fF2B0DB69458A0750badebc4f9e13aDd608C7F",
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
)

bsc.tokens = (
    DotMap(
        btcb="0x7130d2a12b9bcbfae4f2634d864a1ee1ce3ead9c",
        usdc="0x8ac76a51cc950d9822d68b83fe1ad97b32cd580d",
    ),
)

bsc.whale_registry = DotMap()

