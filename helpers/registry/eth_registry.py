import json

from helpers.registry.ChainRegistry import ChainRegistry
from helpers.registry.YearnRegistry import YearnRegistry
from brownie.network import web3
from dotmap import DotMap
from helpers.registry.WhaleRegistryAction import WhaleRegistryAction

aragon_registry = DotMap(
    addresses=DotMap(
        agentImpl="0x3a93c17fc82cc33420d1809dda9fb715cc89dd37",
        companyTemplate="0xd737632caC4d039C9B0EEcc94C12267407a271b5",
    )
)

gnosis_safe_registry = DotMap(
    addresses=DotMap(
        proxyFactory="0x76E2cFc1F5Fa8F6a5b3fC4c8F4788F0116861F9B",
        masterCopy="0x34CfAC646f301356fAa8B21e94227e3583Fe3F5F",
    )
)

onesplit_registry = (DotMap(contract="0x50FDA034C0Ce7a8f7EFDAebDA7Aa7cA21CC1267e"),)

uniswap_registry = DotMap(
    routerV2="0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D",
    factoryV2="0x5C69bEe701ef814a2B6a3EDD4B1652CB9cc5aA6f",
    uniToken="0x1f9840a85d5aF5bf1D1762F925BDADdC4201F984",
    uniStakingRewards=DotMap(eth_wbtc="0xa1484C3aa22a66C62b77E0AE78E15258bd0cB711"),
)

multicall = "0xeefba1e63905ef1d7acba5a8513c70307c1ce441"
multisend = "0x8D29bE29923b68abfDD21e541b9374737B49cdAD"

compound_registry = DotMap(
    comptroller=web3.toChecksumAddress("0x3d9819210a31b4961b30ef54be2aed79b9c9cd3b"),
    cTokens=DotMap(usdc="0x39AA39c021dfbaE8faC545936693aC917d5E7563"),
)

multichain_registry = DotMap(eth_address="0xC564EE9f21Ed8A2d8E7e76c085740d5e4c5FaFbE")

harvest_registry = DotMap(
    badgerTree="0x06466a741094f51b45FB150c6D1e857B3E879967",
    farmToken="0xa0246c9032bC3A600820415aE600c6388619A14D",
    depositHelper="0xf8ce90c2710713552fb564869694b2505bfc0846",
    vaults=DotMap(renCrv="0x9aa8f427a17d6b0d91b6262989edc7d45d6aedf8"),
    farms=DotMap(
        fWBtc="0x917d6480ec60cbddd6cbd0c8ea317bcc709ea77b",
        fRenCrv="0xa3cf8d1cee996253fad1f8e3d68bdcba7b3a3db5",
        fRenCrv2="0x5365A2C47b90EE8C9317faC20edC3ce7037384FB",
        farm="0xae024F29C26D6f71Ec71658B1980189956B0546D",
    ),
)

pickle_registry = DotMap(
    pickleToken="0x429881672B9AE42b8EbA0E26cD9C73711b891Ca5",
    pickleChef="0xbD17B1ce622d73bD438b9E658acA5996dc394b0d",
    jars=DotMap(renCrv="0x2E35392F4c36EBa7eCAFE4de34199b2373Af22ec"),
    pids=DotMap(uniPickleEth=0, pRenCrv=13),
    farms=DotMap(wethStaking="0xa17a8883dA1aBd57c690DF9Ebf58fC194eDAb66F"),
)

sushi_registry = DotMap(
    sushiToken="0x6b3595068778dd592e39a122f4f5a5cf09c90fe2",
    xsushiToken="0x8798249c2E607446EfB7Ad49eC89dD1865Ff4272",
    sushiChef="0xc2EdaD668740f1aA35E4D8f227fB8E17dcA888Cd",
    router="0xd9e1cE17f2641f24aE83637ab66a2cca9C378B9F",
    factory="0xC0AEe478e3658e2610c5F7A4A2E1777cE9e4f2Ac",
    lpTokens=DotMap(
        sushiBadgerWBtc="0x110492b31c59716AC47337E616804E3E3AdC0b4a",
        sushiWbtcWeth="0xCEfF51756c56CeFFCA006cD410B03FFC46dd3a58",
    ),
    pids=DotMap(sushiBadgerWBtc=73, sushiEthWBtc=21),
)

yearn_registry = YearnRegistry(
    registry="0x50c1a2ea0a861a967d9d0ffe2ae4012c2e053804",
    experimental_vaults={"wbtc": "0xA696a63cc78DfFa1a63E9E50587C197387FF6C7E"},
)

aave_registry = DotMap(lendingPoolV2="0x7d2768de32b0b80b7a3454c06bdac94a69ddc7a9")

yearn_registry = (
    DotMap(
        yvWBTC="0xcB550A6D4C8e3517A939BC79d0c7093eb7cF56B5",
    ),
)

curve_registry = DotMap(
    minter="0xd061D61a4d941c39E5453435B6345Dc261C2fcE0",
    crvToken="0xD533a949740bb3306d119CC777fa900bA034cd52",
    pools=DotMap(
        sbtcCrv=DotMap(
            swap="0x7fC77b5c7614E1533320Ea6DDc2Eb61fa00A9714",
            token="0x075b1bb99792c9E1041bA13afEf80C91a1e70fB3",
            gauge="0x705350c4BcD35c9441419DdD5d2f097d7a55410F",
        ),
        renCrv=DotMap(
            swap="0x93054188d876f558f4a66B2EF1d97d16eDf0895B",
            token="0x49849C98ae39Fff122806C06791Fa73784FB3675",
            gauge="0xB1F2cdeC61db658F091671F5f199635aEF202CAC",
        ),
        tbtcCrv=DotMap(
            swap="0xaa82ca713d94bba7a89ceab55314f9effeddc78c",
            # swap="0xC25099792E9349C7DD09759744ea681C7de2cb66",
            token="0x64eda51d3Ad40D56b9dFc5554E06F94e1Dd786Fd",
            gauge="0x6828bcF74279eE32f2723eC536c22c51Eed383C6",
        ),
    ),
)

badger_registry = DotMap(token="0x3472a5a71965499acd81997a54bba8d852c6e53d")

defidollar_registry = DotMap(
    addresses=DotMap(
        badgerSettPeak="0x41671BA1abcbA387b9b2B752c205e22e916BE6e3",
        core="0x2A8facc9D49fBc3ecFf569847833C380A13418a8",
    ),
    pools=[
        DotMap(
            id=0,
            sett="0x6dEf55d2e18486B9dDfaA075bc4e4EE0B28c1545",
        ),
        DotMap(
            id=1,
            sett="0xd04c48A53c111300aD41190D63681ed3dAd998eC",
        ),
        DotMap(
            id=2,
            sett="0xb9D076fDe463dbc9f915E5392F807315Bf940334",
        ),
    ],
)

eth_registry = ChainRegistry(
    curve=curve_registry,
    uniswap=uniswap_registry,
    aragon=aragon_registry,
    sushiswap=sushi_registry,
    sushi=sushi_registry,
    gnosis_safe=gnosis_safe_registry,
    pickle=pickle_registry,
    harvest=harvest_registry,
    multicall=multicall,
    multisend=multisend,
    badger=badger_registry,
    yearn=yearn_registry,
    aave=aave_registry,
    compound=compound_registry,
    defidollar=defidollar_registry,
)

eth_registry.tokens = DotMap(
    weth="0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
    wbtc="0x2260FAC5E5542a773Aa44fBCfeDf7C193bc2C599",
    crv="0xD533a949740bb3306d119CC777fa900bA034cd52",
    tbtc=web3.toChecksumAddress("0x8daebade922df735c38c80c7ebd708af50815faa"),
    usdt=web3.toChecksumAddress("0xdac17f958d2ee523a2206206994597c13d831ec7"),
    badger=eth_registry.badger.token,
    digg="0x798D1bE841a82a273720CE31c822C61a67a601C3",
    farm=eth_registry.harvest.farmToken,
    sushi=eth_registry.sushi.sushiToken,
    xSushi=eth_registry.sushi.xsushiToken,
    usdc=web3.toChecksumAddress("0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48"),
    renbtc=web3.toChecksumAddress("0xeb4c2781e4eba804ce9a9803c67d0893436bb27d"),
    ibbtc=web3.toChecksumAddress("0xc4E15973E6fF2A35cC804c2CF9D2a1b817a8b40F"),
    dfd=web3.toChecksumAddress("0x20c36f062a31865bed8a5b1e512d9a1a20aa333a"),
    ausdc="0xBcca60bB61934080951369a648Fb03DF4F96263C",
)

eth_registry.whales = DotMap(
    badger=DotMap(
        whale="0x19d099670a21bC0a8211a89B84cEdF59AbB4377F",
        token="0x3472A5A71965499acd81997a54BBA8D852C6E53d",
        action=WhaleRegistryAction.DISTRIBUTE_FROM_CONTRACT,
    ),
    bBadger=DotMap(
        whale="0xa9429271a28F8543eFFfa136994c0839E7d7bF77",
        token="0x19D97D8fA813EE2f51aD4B4e04EA08bAf4DFfC28",
        action=WhaleRegistryAction.DISTRIBUTE_FROM_CONTRACT,
    ),
    harvestSuperSett=DotMap(
        whale="0xeD0B7f5d9F6286d00763b0FFCbA886D8f9d56d5e",
        token="0xAf5A1DECfa95BAF63E0084a35c62592B774A2A87",
        action=WhaleRegistryAction.DISTRIBUTE_FROM_CONTRACT,
    ),
    uniBadgerWbtc=DotMap(
        whale="0x235c9e24D3FB2FAFd58a2E49D454Fdcd2DBf7FF1",
        token="0xcD7989894bc033581532D2cd88Da5db0A4b12859",
        action=WhaleRegistryAction.DISTRIBUTE_FROM_CONTRACT,
    ),
    uniDiggWbtc=DotMap(
        whale="0xc17078fdd324cc473f8175dc5290fae5f2e84714",
        token="0xe86204c4eddd2f70ee00ead6805f917671f56c52",
        action=WhaleRegistryAction.DISTRIBUTE_FROM_CONTRACT,
    ),
    sbtcCrv=DotMap(
        whale="0xc25099792e9349c7dd09759744ea681c7de2cb66",
        token=eth_registry.curve.pools.sbtcCrv.token,
        action=WhaleRegistryAction.DISTRIBUTE_FROM_CONTRACT,
    ),
    bSbtcCrv=DotMap(
        whale="0x10fc82867013fce1bd624fafc719bb92df3172fc",
        token="0xd04c48A53c111300aD41190D63681ed3dAd998eC",
        action=WhaleRegistryAction.DISTRIBUTE_FROM_CONTRACT,
    ),
    renCrv=DotMap(
        whale="0xb1f2cdec61db658f091671f5f199635aef202cac",
        token=eth_registry.curve.pools.renCrv.token,
        action=WhaleRegistryAction.DISTRIBUTE_FROM_CONTRACT,
    ),
    bRenCrv=DotMap(
        whale="0x2296f174374508278dc12b806a7f27c87d53ca15",
        token="0x6dEf55d2e18486B9dDfaA075bc4e4EE0B28c1545",
        action=WhaleRegistryAction.DISTRIBUTE_FROM_CONTRACT,
    ),
    tbtcCrv=DotMap(
        whale="0xaf379f0228ad0d46bb7b4f38f9dc9bcc1ad0360c",
        token=eth_registry.curve.pools.tbtcCrv.token,
        action=WhaleRegistryAction.DISTRIBUTE_FROM_CONTRACT,
    ),
    bTbtcCrv=DotMap(
        whale="0x085a9340ff7692ab6703f17ab5ffc917b580a6fd",
        token="0xb9D076fDe463dbc9f915E5392F807315Bf940334",
        action=WhaleRegistryAction.DISTRIBUTE_FROM_CONTRACT,
    ),
    wbtc=DotMap(
        whale="0xc11b1268c1a384e55c48c2391d8d480264a3a7f4",
        token="0x2260FAC5E5542a773Aa44fBCfeDf7C193bc2C599",
        action=WhaleRegistryAction.DISTRIBUTE_FROM_CONTRACT,
    ),
    sushiBadgerWbtc=DotMap(
        whale="0xc2EdaD668740f1aA35E4D8f227fB8E17dcA888Cd",
        token="0x110492b31c59716AC47337E616804E3E3AdC0b4a",
        action=WhaleRegistryAction.DISTRIBUTE_FROM_CONTRACT,
    ),
    sushiDiggWbtc=DotMap(
        whale="0xd16fda96cb572da89e4e39b04b99d99a8e3071fb",
        token="0x110492b31c59716AC47337E616804E3E3AdC0b4a",
        action=WhaleRegistryAction.DISTRIBUTE_FROM_CONTRACT,
    ),
    sushiWbtcEth=DotMap(
        whale="0xc2EdaD668740f1aA35E4D8f227fB8E17dcA888Cd",
        token="0xCEfF51756c56CeFFCA006cD410B03FFC46dd3a58",
        action=WhaleRegistryAction.DISTRIBUTE_FROM_CONTRACT,
    ),
    bSushiWbtcEth=DotMap(
        whale="0x032c701886ad0317f0e58c8f4a570c6f9c0bbf4a",
        token="0x758A43EE2BFf8230eeb784879CdcFF4828F2544D",
        action=WhaleRegistryAction.DISTRIBUTE_FROM_CONTRACT,
    ),
    usdc=DotMap(
        whale="0xbe0eb53f46cd790cd13851d5eff43d12404d33e8",  # binance
        token="0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48",
        action=WhaleRegistryAction.DISTRIBUTE_FROM_CONTRACT,
    ),
    digg=DotMap(
        whale="0x4a8651F2edD68850B944AD93f2c67af817F39F62",
        token="0x798D1bE841a82a273720CE31c822C61a67a601C3",
        action=WhaleRegistryAction.DISTRIBUTE_FROM_CONTRACT,
    ),
    renbtc=DotMap(
        whale="0x35ffd6e268610e764ff6944d07760d0efe5e40e5",
        token="0xeb4c2781e4eba804ce9a9803c67d0893436bb27d",
        action=WhaleRegistryAction.DISTRIBUTE_FROM_CONTRACT,
    ),
)
