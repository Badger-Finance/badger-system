const hre = require("hardhat");
const ethers = hre.ethers;

async function main() {
    // We get the contract to deploy
    const name = "Greeter"
    const ContractFactory = await ethers.getContractFactory(name);
    const contract = await ContractFactory.deploy("Hello, Hardhat!");
  
    console.log("Contract " + name + " deployed to:", contract.address);
  }
  
  main()
    .then(() => process.exit(0))
    .catch((error) => {
      console.error(error);
      process.exit(1);
    });