from helpers.sett.resolvers.StrategyCoreResolver import StrategyCoreResolver


class StrategyCurveGaugeResolver(StrategyCoreResolver):
    def get_strategy_destinations(self):
        strategy = self.manager.strategy
        return {
            "gauge": strategy.gauge(),
            "mintr": strategy.mintr(),
        }
