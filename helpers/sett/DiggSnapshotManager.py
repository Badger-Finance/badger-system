from brownie import chain
from rich.console import Console

from config.badger_config import digg_config_test
from .SnapshotManager import SnapshotManager

console = Console()

# Rebase constants pulled directly from `UFragmentsPolicy.sol`.
# 15 minute rebase window at 8pm UTC everyday.
REBASE_WINDOW_OFFSET_SEC = digg_config_test.rebaseWindowOffsetSec
REBASE_WINDOW_LENGTH_SEC = digg_config_test.rebaseWindowLengthSec
MIN_REBASE_TIME_INTERVAL_SEC = digg_config_test.minRebaseTimeIntervalSec
# Pad shifts into rebase winudow by 1 minute.
REBASE_SHIFT_PADDING_SECONDS = 60
DAY = 24 * 60 * 60


class DiggSnapshotManager(SnapshotManager):
    def rebase(self, value, overrides, confirm=True):
        console.print(f"rebasing at value: {value}")
        user = overrides["from"].address
        trackedUsers = {"user": user}
        before = self.snap(trackedUsers)

        # Shift into rebase window (if not already). Need to mine a block as well
        # as the rebase logic checks if block ts w/in rebase window.
        # Update market value and rebase.
        tx = self.badger.digg_system.dynamicOracle.setValueAndPush(value)
        assert tx.return_value == value
        # NB: Guarantee the configured report delay has passed. Otherwise,
        # the median oracle will attempt to use the last report.
        chain.sleep(digg_config_test.marketOracleParams.reportDelaySec)

        self._shift_into_next_rebase_window()

        tx = self.badger.digg_system.orchestrator.rebase()

        after = self.snap(trackedUsers)
        if confirm:
            self.resolver.confirm_rebase(before, after, value)

    def _shift_into_next_rebase_window(self):
        # seconds offset into the day
        utcnow_unix_offset_secs = (chain.time() % MIN_REBASE_TIME_INTERVAL_SEC)
        # Shift forward into rebase window into tomorrow.
        secs_remaining_in_day = DAY - utcnow_unix_offset_secs
        chain.sleep(
            secs_remaining_in_day
            + REBASE_WINDOW_OFFSET_SEC
            + REBASE_SHIFT_PADDING_SECONDS)
        chain.mine()
