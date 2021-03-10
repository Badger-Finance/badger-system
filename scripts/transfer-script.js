// We require the Hardhat Runtime Environment explicitly here. This is optional
// but useful for running the script in a standalone fashion through `node <script>`.
//
// When running the script with `hardhat run <script>` you'll find the Hardhat
// Runtime Environment's members available in the global scope.
const hre = require("hardhat");

// Load TEST_ACCOUNT into env vars.
require('dotenv').config()

const erc20abi = [
    // Read-Only Functions
    "function balanceOf(address owner) view returns (uint256)",
    "function decimals() view returns (uint8)",
    "function symbol() view returns (string)",

    // Authenticated Functions
    "function transfer(address to, uint amount) returns (boolean)",

    // Events
    "event Transfer(address indexed from, address indexed to, uint amount)"
];

const bBADGER = "0x19D97D8fA813EE2f51aD4B4e04EA08bAf4DFfC28";
const bSushiWbtcEth = "0x758A43EE2BFf8230eeb784879CdcFF4828F2544D";

async function main() {
  // Hardhat always runs the compile task when running scripts with its command
  // line interface.
  //
  // If this script is run directly using `node` you may want to call compile
  // manually to make sure everything is compiled
  // ait hre.run('compile');

  const account = process.env.TEST_ACCOUNT;
  const whales = [
    ["0x9e67D018488aD636B538e4158E9e7577F2ECac12", bBADGER],
    ["0x6ff0be40314fdf5e07bcba38c69be4955d5e6197", bSushiWbtcEth],
  ];
  const forkAccount = (await ethers.provider.listAccounts())[0];
  const signer = await ethers.provider.getSigner(forkAccount);
  await signer.sendTransaction({
    to: account,
    value: ethers.utils.parseEther("10.0"),
  })
  for (const [whale, tokenAddress] of whales) {
    await hre.network.provider.request({
      method: "hardhat_impersonateAccount",
      params: [whale]},
    )
    console.log("impersonated", whale);
    const signer = await ethers.provider.getSigner(whale);

    const token = new ethers.Contract(tokenAddress, erc20abi, signer);
    let balance;
    try {
      balance = await token.balanceOf(whale);
    } catch (e) {
      balance = ethers.BigNumber.from("1000000000000000000")
    }
    const transferBalance = balance.div(2);
    await token.transfer(account, transferBalance)
    console.log(`transferred ${transferBalance} to ${account} of token ${tokenAddress}`);
  }
}

// We recommend this pattern to be able to use async/await everywhere
// and properly handle errors.
main()
  .then(() => process.exit(0))
  .catch(error => {
    console.error(error);
    process.exit(1);
  });
