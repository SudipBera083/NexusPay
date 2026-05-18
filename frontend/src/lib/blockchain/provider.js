import { ethers } from 'ethers';

// Fallback providers configuration
const RPC_URLS = [
  'https://rpc-amoy.polygon.technology',
  'https://polygon-amoy.public.blastapi.io',
  'https://rpc.ankr.com/polygon_amoy'
];

export class BlockchainProvider {
  static instance = null;

  constructor() {
    this.provider = null;
    this.signer = null;
    this.address = null;
    this.chainId = 80002; // Polygon Amoy
    
    // Initialize read-only provider immediately
    this.initReadOnlyProvider();
  }

  static getInstance() {
    if (!BlockchainProvider.instance) {
      BlockchainProvider.instance = new BlockchainProvider();
    }
    return BlockchainProvider.instance;
  }

  initReadOnlyProvider() {
    // Use FallbackProvider for reliability
    const providers = RPC_URLS.map((url, idx) => ({
      provider: new ethers.JsonRpcProvider(url),
      priority: idx + 1,
      stallTimeout: 1000
    }));
    this.readOnlyProvider = new ethers.FallbackProvider(providers);
  }

  async connectWallet() {
    if (!window.ethereum) {
      throw new Error("MetaMask or compatible Web3 wallet not found");
    }

    try {
      this.provider = new ethers.BrowserProvider(window.ethereum);
      
      // Request accounts
      const accounts = await this.provider.send("eth_requestAccounts", []);
      this.address = accounts[0];
      this.signer = await this.provider.getSigner();
      
      // Verify network
      const network = await this.provider.getNetwork();
      if (Number(network.chainId) !== this.chainId) {
        await this.switchNetwork();
      }
      
      return { address: this.address, signer: this.signer };
    } catch (error) {
      console.error("Wallet connection failed:", error);
      throw error;
    }
  }

  async switchNetwork() {
    try {
      await window.ethereum.request({
        method: 'wallet_switchEthereumChain',
        params: [{ chainId: ethers.toQuantity(this.chainId) }],
      });
    } catch (switchError) {
      // If network doesn't exist, add it
      if (switchError.code === 4902) {
        await window.ethereum.request({
          method: 'wallet_addEthereumChain',
          params: [
            {
              chainId: ethers.toQuantity(this.chainId),
              chainName: 'Polygon Amoy Testnet',
              nativeCurrency: {
                name: 'MATIC',
                symbol: 'MATIC',
                decimals: 18
              },
              rpcUrls: [RPC_URLS[0]],
              blockExplorerUrls: ['https://amoy.polygonscan.com/']
            }
          ]
        });
      } else {
        throw switchError;
      }
    }
  }

  disconnect() {
    this.provider = null;
    this.signer = null;
    this.address = null;
  }
}

export const getProvider = () => BlockchainProvider.getInstance();
