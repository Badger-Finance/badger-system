from helpers.sett.resolvers.StrategyCoreResolver import StrategyCoreResolver


class StrategyCurveGaugeResolver(StrategyCoreResolver):
    def confirm_harvest(self, before, after):
        super().confirm_harvest(before, after)

        # KeepCRV amount should go to X

    def get_strategy_destinations(self):
        strategy = self.manager.strategy
        return {
            "gauge": strategy.gauge(),
            "mintr": strategy.mintr(),
        }
