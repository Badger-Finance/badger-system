class StrategyConfig:
    def __init__(self, strategyName, want, params, controller=None):
        assert want == params.want
        self.strategyName = strategyName
        self.want = want
        self.params = params
        self.controller = controller
