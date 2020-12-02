import json
from dotmap import DotMap

with open("dependency-artifacts/aragon/Agent.json") as f:
    Agent = json.load(f)

with open("dependency-artifacts/aragon/Vault.json") as f:
    Vault = json.load(f)

with open("dependency-artifacts/aragon/Voting.json") as f:
    Voting = json.load(f)

with open("dependency-artifacts/aragon/Finance.json") as f:
    Finance = json.load(f)

with open("dependency-artifacts/aragon/TokenManager.json") as f:
    TokenManager = json.load(f)

with open("dependency-artifacts/aragon/CompanyTemplate.json") as f:
    CompanyTemplate = json.load(f)

with open("dependency-artifacts/aragon/MiniMeToken.json") as f:
    MiniMeToken = json.load(f)

with open("dependency-artifacts/gnosis-safe/MasterCopy.json") as f:
    MasterCopy = json.load(f)

with open("dependency-artifacts/gnosis-safe/ProxyFactory.json") as f:
    ProxyFactory = json.load(f)

with open("dependency-artifacts/gnosis-safe/GnosisSafe.json") as f:
    GnosisSafe = json.load(f)

with open("dependency-artifacts/open-zeppelin/TokenTimelock.json") as f:
    TokenTimelock = json.load(f)

with open("dependency-artifacts/open-zeppelin-upgrades/ProxyAdmin.json") as f:
    ProxyAdmin = json.load(f)

with open(
    "dependency-artifacts/open-zeppelin-upgrades/AdminUpgradeabilityProxy.json"
) as f:
    AdminUpgradeabilityProxy = json.load(f)

with open("dependency-artifacts/uniswap/UniswapV2Pair.json") as f:
    UniswapV2Pair = json.load(f)

with open("dependency-artifacts/uniswap/UniswapV2Factory.json") as f:
    UniswapV2Factory = json.load(f)

with open("dependency-artifacts/uniswap/UniswapV2Router02.json") as f:
    UniswapV2Router = json.load(f)

aragon_registry = DotMap(
    addresses=DotMap(
        agentImpl="0x3a93c17fc82cc33420d1809dda9fb715cc89dd37",
        companyTemplate="0xd737632caC4d039C9B0EEcc94C12267407a271b5",
    ),
    artifacts=DotMap(
        Agent=Agent,
        CompanyTemplate=CompanyTemplate,
        Vault=Vault,
        Voting=Voting,
        Finance=Finance,
        TokenManager=TokenManager,
        MiniMeToken=MiniMeToken,
    ),
)

gnosis_safe_registry = DotMap(
    addresses=DotMap(
        proxyFactory="0x76E2cFc1F5Fa8F6a5b3fC4c8F4788F0116861F9B",
        masterCopy="0x34CfAC646f301356fAa8B21e94227e3583Fe3F5F",
    ),
    artifacts=DotMap(
        MasterCopy=MasterCopy, ProxyFactory=ProxyFactory, GnosisSafe=GnosisSafe
    ),
)

open_zeppelin_registry = DotMap(
    artifacts=DotMap(
        ProxyAdmin=ProxyAdmin,
        AdminUpgradeabilityProxy=AdminUpgradeabilityProxy,
        TokenTimelock=TokenTimelock,
    )
)

token_registry = DotMap(
    weth="0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
    wbtc="0x2260FAC5E5542a773Aa44fBCfeDf7C193bc2C599",
    crv="0xD533a949740bb3306d119CC777fa900bA034cd52",
    tbtc="0x8daebade922df735c38c80c7ebd708af50815faa",
)

onesplit_registry = DotMap(contract="0x50FDA034C0Ce7a8f7EFDAebDA7Aa7cA21CC1267e")

uniswap_registry = DotMap(
    routerV2="0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D",
    factoryV2="0x5C69bEe701ef814a2B6a3EDD4B1652CB9cc5aA6f",
    uniToken="0x1f9840a85d5aF5bf1D1762F925BDADdC4201F984",
    uniStakingRewards=DotMap(eth_wbtc="0xa1484C3aa22a66C62b77E0AE78E15258bd0cB711"),
    artifacts=DotMap(
        UniswapV2Factory=UniswapV2Factory,
        UniswapV2Router=UniswapV2Router,
        UniswapV2Pair=UniswapV2Pair,
    ),
)

harvest_registry = DotMap(
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
    artifacts=DotMap(),
)


whale_registry = DotMap(
    sbtcCrv=DotMap(
        whale="0xc25099792e9349c7dd09759744ea681c7de2cb66",
        token=curve_registry.pools.sbtcCrv.token,
    ),
    renCrv=DotMap(
        whale="0xb1f2cdec61db658f091671f5f199635aef202cac",
        token=curve_registry.pools.renCrv.token,
    ),
    tbtcCrv=DotMap(
        whale="0xaf379f0228ad0d46bb7b4f38f9dc9bcc1ad0360c",
        token=curve_registry.pools.tbtcCrv.token,
        whaleType="CurveRewards",
    ),
    wbtc=DotMap(
        whale="0x2bf792ffe8803585f74e06907900c2dc2c29adcb", token=token_registry.wbtc,
    ),
)


registry = DotMap(
    curve=curve_registry,
    uniswap=uniswap_registry,
    open_zeppelin=open_zeppelin_registry,
    aragon=aragon_registry,
    gnosis_safe=gnosis_safe_registry,
    onesplit=gnosis_safe_registry,
    pickle=pickle_registry,
    harvest=harvest_registry,
    tokens=token_registry,
    whales=whale_registry,
)
