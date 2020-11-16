"""
E2E isolated tests for StrategyHarvestMetaFarm

This strategy stakes the assets into the appropraite Harvest Vault and stakes the resulting tokens for FARM.
Additional FARM rewards are 'recycled'.
Harvest FARM rewards are realized via the Rewards system rather than via withdrawal.

(After withdrawal, rewards will appear at next rewards cycle)
"""