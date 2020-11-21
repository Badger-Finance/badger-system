# from tests.sett.helpers.snapshots import (
#     confirm_deposit,
#     confirm_earn,
#     confirm_harvest,
#     confirm_tend,
#     confirm_withdraw,
#     sett_snapshot,
# )
# from tests.conftest import (
#     distribute_from_whales,
#     distribute_rewards_escrow,
#     get_sett_by_id,
# )
# from helpers.time_utils import daysToSeconds
# import brownie
# from helpers.proxy_utils import deploy_proxy
# import pytest
# from operator import itemgetter
# from brownie.test import given, strategy
# from brownie import *
# from helpers.constants import *
# from helpers.gnosis_safe import convert_to_test_mode, exec_direct
# from dotmap import DotMap
# from scripts.deploy.deploy_badger import main
# from helpers.registry import whale_registry


# @pytest.mark.parametrize(
#     "settId",
#     [
#         "native.renCrv",
#         "native.badger",
#         "native.sbtcCrv",
#         "native.tbtcCrv",
#         "pickle.renCrv",
#         "harvest.renCrv",
#     ],
# )
# def test_action_flow(badger):
#     # # TODO: Get token randomly from selection
#     badger = shared_setup
#     settConfig = get_sett_by_id(shared_setup, settId)

#     controller = settConfig.controller
#     sett = settConfig.sett
#     strategy = settConfig.strategy
#     want = settConfig.want
#     deployer = badger.deployer
#     randomUser = accounts[6]

#     assert sett.token() == strategy.want()

#     users = [badger.deployer, accounts[2], accounts[3], accounts[4]]

#     # rounds = 100

#     # user = get_random_user(users)

#     # # Initial deposit
#     # user = get_random_user(users)
#     # amount = get_random_amount(want, user)
#     # sett.deposit(amount, {'from': user})

#     # for round in range(rounds):
#     #     # Take user action
#     #     take_keeper_action(badger, sett, strategy, user)

#     #     user = get_random_user(users)
#     #     take_user_action(badger, sett, strategy, user)

#     #     take_keeper_action(badger, sett, strategy, user)
