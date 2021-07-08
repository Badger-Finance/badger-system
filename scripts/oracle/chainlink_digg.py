from scripts.systems.badger_system import connect_badger
from helpers.gnosis_safe import GnosisSafe, MultisigTxMetadata


def main():
    badger = connect_badger()
    digg = badger.digg
    raw = 0.9566301
    scaled = raw * 10 ** 18

    centralizedOracle = GnosisSafe(digg.centralizedOracle)

    print("Raw Link")
    print(raw)
    print("Formatted for Median Oracle")
    print(f"{scaled:.0f}")

    tx = centralizedOracle.execute(
        MultisigTxMetadata(description="Set Market Data"),
        {
            "to": digg.marketMedianOracle.address,
            "data": digg.marketMedianOracle.pushReport.encode_input(scaled),
        },
    )
