import { useState } from 'react';
import { BrowserProvider } from 'ethers';
import { walletAPI } from '@/api/client';
import toast from 'react-hot-toast';

const Web3ConnectButton = ({ currentAddress, onConnect }) => {
  const [loading, setLoading] = useState(false);

  const connectWallet = async () => {
    if (!window.ethereum) {
      toast.error("MetaMask or a Web3 provider is not installed.");
      return;
    }

    setLoading(true);
    try {
      // 1. Connect to MetaMask
      const provider = new BrowserProvider(window.ethereum);
      const accounts = await provider.send("eth_requestAccounts", []);
      
      if (!accounts || accounts.length === 0) {
        throw new Error("No accounts found.");
      }
      const address = accounts[0];

      // 2. Generate a signable message with a timestamp to prevent replay attacks
      const timestamp = new Date().getTime();
      const message = `Verify wallet ownership for NexusPay: ${timestamp}`;

      // 3. Request signature from the user
      const signer = await provider.getSigner();
      const signature = await signer.signMessage(message);

      // 4. Send to backend for verification and linking
      await walletAPI.linkWeb3Wallet({
        address,
        message,
        signature
      });

      toast.success("Web3 Wallet linked successfully!");
      if (onConnect) onConnect(address);

    } catch (err) {
      console.error("Web3 Connection Error:", err);
      toast.error(err.response?.data?.message || err.message || "Failed to connect wallet.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="bg-gray-800/50 p-6 rounded-xl border border-gray-700/50 mb-6">
      <h3 className="text-lg font-semibold text-white mb-2">Web3 Connectivity</h3>
      <p className="text-gray-400 text-sm mb-4">
        Link your external EVM-compatible wallet (like MetaMask) to enable future on-chain deposits and withdrawals.
      </p>

      {currentAddress ? (
        <div className="flex items-center space-x-3 bg-gray-900/50 p-3 rounded-lg border border-gray-700/50">
          <div className="w-10 h-10 rounded-full bg-gradient-to-tr from-purple-600 to-blue-500 flex items-center justify-center shadow-lg shadow-purple-500/20">
            <svg className="w-5 h-5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1" />
            </svg>
          </div>
          <div>
            <p className="text-sm font-medium text-gray-300">Linked Address</p>
            <p className="text-sm text-white font-mono break-all">{currentAddress}</p>
          </div>
        </div>
      ) : (
        <button
          onClick={connectWallet}
          disabled={loading}
          className="w-full sm:w-auto px-6 py-2.5 bg-gradient-to-r from-[#F6851B] to-[#E2761B] hover:from-[#E2761B] hover:to-[#F6851B] text-white rounded-lg font-medium transition-all shadow-lg shadow-orange-500/20 disabled:opacity-50 flex items-center justify-center space-x-2"
        >
          {loading ? (
            <div className="w-5 h-5 border-2 border-white/20 border-t-white rounded-full animate-spin" />
          ) : (
            <svg className="w-5 h-5" viewBox="0 0 33 32" fill="none" xmlns="http://www.w3.org/2000/svg">
              <path d="M30.672 10.973L21.432 0L17.512 8.784L15.336 6.811L14.792 11.081L23.336 21.324H12.984L17.784 15.649L10.904 14.865L6.376 21.054L0 12.378L13.12 31.054H33L30.672 10.973Z" fill="white"/>
            </svg>
          )}
          <span>{loading ? 'Connecting...' : 'Connect MetaMask'}</span>
        </button>
      )}
    </div>
  );
};

export default Web3ConnectButton;
