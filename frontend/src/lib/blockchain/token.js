import { ethers } from 'ethers';
import { getProvider } from './provider';

// Standard ERC20 ABI (subset needed for payments)
const ERC20_ABI = [
  "function transfer(address to, uint256 amount) returns (bool)",
  "function balanceOf(address account) view returns (uint256)",
  "function decimals() view returns (uint8)",
  "function symbol() view returns (string)",
  "event Transfer(address indexed from, address indexed to, uint256 value)"
];

const USDC_CONTRACT_ADDRESS = "0x41E94Eb019C0762f9Bfcf9Fb1E58725BfB0e7582";
const USDC_DECIMALS = 6;

export class TokenService {
  constructor(contractAddress = USDC_CONTRACT_ADDRESS) {
    this.contractAddress = contractAddress;
    this.provider = getProvider();
  }

  async getBalance(address) {
    const contract = new ethers.Contract(
      this.contractAddress,
      ERC20_ABI,
      this.provider.readOnlyProvider
    );
    
    const balanceRaw = await contract.balanceOf(address);
    return ethers.formatUnits(balanceRaw, USDC_DECIMALS);
  }

  async sendPayment(toAddress, amountHuman) {
    if (!this.provider.signer) {
      throw new Error("Wallet not connected");
    }

    const contract = new ethers.Contract(
      this.contractAddress,
      ERC20_ABI,
      this.provider.signer
    );

    const amountRaw = ethers.parseUnits(amountHuman.toString(), USDC_DECIMALS);
    
    // Broadcast transaction via MetaMask
    const tx = await contract.transfer(toAddress, amountRaw);
    
    return {
      txHash: tx.hash,
      wait: () => tx.wait()
    };
  }
}

export const usdcService = new TokenService();
