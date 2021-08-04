from time import sleep, time
from threading import Thread
from brownie.network.account import Account
import requests
import os


class TxTimer:
    """
    Starts a timer in a new thread that will send a message to the specified webhook
    if the timer is not turned off before `time_threshold`.

    Usage:
    - call the start_timer method before sending a transaction
    - call the end_timer method on the next line after sending the transaction

    Example:
    tx_timer.start_timer(overrides['from'], 'Harvest')
    tx = self.strategy.harvest(overrides)
    tx_timer.end_timer()
    """

    def __init__(self, time_threshold=1200, timer_tick=1) -> None:
        """
        :param time_threshold: time in seconds to wait for sending alert
        :param timer_tick: how long to sleep thread before resuming loop to see if alert should be sent

        Attributes:
        waiting: whether or not there is a tx currently waiting
        sender: account that tx was sent from, used in alert message
        webhook: webhook url from .env
        tx_type: Harvest, Tend, etc. included in alert message
        """

        self.time_threshold = time_threshold
        self.timer_tick = timer_tick
        self.waiting = False
        self.sender = None
        self.webhook = os.environ.get("TX_TIMER_WEBHOOK")
        self.tx_type = ""

    def alert(self, msg: str) -> None:
        if self.webhook:
            requests.post(self.webhook, {"content": msg})
        else:
            print("No webhook supplied")

    def track_tx(self) -> None:
        """
        Run a loop until the timer is ended or `time_threshold` is hit. If the threshold is hit
        then send an alert to the webhook
        """

        start = time()
        self.waiting = True

        while self.waiting:
            sleep(self.timer_tick)
            if time() - start >= self.time_threshold:
                if self.tx_type:
                    msg = (
                        "🕔 *"
                        + self.tx_type
                        + "* - "
                        + "tx sent from "
                        + str(self.sender.address)
                        + " has exceeded threshold of "
                        + str(self.time_threshold)
                        + " seconds"
                    )
                else:
                    msg = (
                        "🕔 tx sent from "
                        + str(self.sender.address)
                        + " has exceeded threshold of "
                        + str(self.time_threshold)
                        + " seconds"
                    )
                self.alert(msg)
                self.waiting = False
                self.sender = None
                self.tx_type = ""

    def start_timer(self, sender: Account, tx_type: str) -> None:
        self.sender = sender
        self.tx_type = tx_type
        self.thr = Thread(target=self.track_tx)
        self.thr.start()

    def end_timer(self) -> None:
        self.waiting = False
        self.sender = None
        self.tx_type = ""


tx_timer = TxTimer()
