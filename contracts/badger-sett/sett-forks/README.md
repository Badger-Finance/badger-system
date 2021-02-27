# Layout Upgradeable

In order to maintain layout backwards compatibilty w/ different versions of contracts (e.g. Sett).

Changelog:

V1.1
* Strategist no longer has special function calling permissions
* Version function added to contract
* All write functions, with the exception of transfer, are pausable
* Keeper or governance can pause
* Only governance can unpause

V1.2
* Transfer functions are now pausable along with all other non-permissioned write functions
* All permissioned write functions, with the exception of pause() & unpause(), are pausable as well
