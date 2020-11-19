# def test_confirm_contract_admins(badger):
#     owner = badger.deployer

#     assert badger.devProxyAdmin.owner() == owner

#     # By checking the implementations, we're implictly testing the ProxyAdmins' ownership as only the ProxyAdmin can use this function on a contract
#     assert (
#         badger.devProxyAdmin.getProxyImplementation(badger.badgerTree)
#         == badger.logic.BadgerTree
#     )
#     assert (
#         badger.devProxyAdmin.getProxyImplementation(badger.badgerHunt)
#         == badger.logic.BadgerHunt
#     )
#     assert (
#         badger.devProxyAdmin.getProxyImplementation(badger.rewardsEscrow)
#         == badger.logic.RewardsEscrow
#     )

#     # TODO: Finish checks
