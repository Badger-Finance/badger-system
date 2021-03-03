# CLAW Testing

Install geth, npx, brownie etc.

Run geth in light client mode (mainnet).
`geth --http.port 8546 --http --syncmode "light"`

Run hardhat node fork (mainnet).
`npx hardhat node --fork http://127.0.0.1:8546`

Run claw deployment script.
`brownie run scripts/local_instance_claw.py`

Transfer sett LP assets to test user.
`TEST_ACCOUNT=XXX npx hardhat run --network localhost scripts/transfer-script.js`
