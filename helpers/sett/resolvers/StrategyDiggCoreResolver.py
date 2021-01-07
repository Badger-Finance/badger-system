from .StrategyCoreResolver import StrategyCoreResolver


class StrategyDiggCoreResolver(StrategyCoreResolver):
    def confirm_deposit(self, before, after, params):
        super().confirm_deposit(before, after, params)
