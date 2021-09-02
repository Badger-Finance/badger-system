from tests.sett.fixtures.SettMiniDeployBase import SettMiniDeployBase
from config.badger_config import badger_config, sett_config
from helpers.token_utils import distribute_from_whales
from brownie import interface, accounts


class HarvestMetaFarmMiniDeploy(SettMiniDeployBase):
    def fetch_params(self):
        params = sett_config.harvest.renCrv.params
        want = sett_config.harvest.renCrv.params.want

        return (params, want)

    def post_deploy_setup(self, deploy=True):
        # TODO(bodu): Check if there's any post deploy setup we need to do.
        distribute_from_whales(self.deployer, 1, "renCrv")
        self.strategy.setWithdrawalMaxDeviationThreshold(50, {"from": self.governance})

        # Strategy must be whitelisted on Harvest's controller
        harvestController = interface.IHarvestController(
            "0x3cc47874dc50d98425ec79e647d83495637c55e3"
        )
        gov = accounts.at(harvestController.governance(), force=True)

        harvestController.addToWhitelist(self.strategy.address, {"from": gov})
        # assert harvestController.greyList(self.strategy.address, {"from": gov}) == False
