from helpers.sett.resolvers.StrategyCoreResolver import StrategyCoreResolver


class StrategyCurveGaugeResolver(StrategyCoreResolver):
    def confirm_harvest(self, before, after):
        assert False

    def get_strategy_destinations(self):
        strategy = self.manager.strategy
        return {}
