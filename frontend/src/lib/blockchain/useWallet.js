import { useState, useEffect, useCallback } from 'react';
import { getProvider } from './provider';
import { usdcService } from './token';

export function useWallet() {
  const [address, setAddress] = useState(null);
  const [isConnecting, setIsConnecting] = useState(false);
  const [error, setError] = useState(null);
  const [usdcBalance, setUsdcBalance] = useState('0.00');

  const provider = getProvider();

  const fetchBalance = useCallback(async (walletAddress) => {
    if (!walletAddress) return;
    try {
      const balance = await usdcService.getBalance(walletAddress);
      setUsdcBalance(balance);
    } catch (err) {
      console.error("Failed to fetch USDC balance:", err);
    }
  }, []);

  const connect = useCallback(async () => {
    setIsConnecting(true);
    setError(null);
    try {
      const { address: connectedAddress } = await provider.connectWallet();
      setAddress(connectedAddress);
      await fetchBalance(connectedAddress);
    } catch (err) {
      setError(err.message || "Failed to connect wallet");
    } finally {
      setIsConnecting(false);
    }
  }, [provider, fetchBalance]);

  const disconnect = useCallback(() => {
    provider.disconnect();
    setAddress(null);
    setUsdcBalance('0.00');
  }, [provider]);

  // Handle MetaMask account changes
  useEffect(() => {
    if (window.ethereum) {
      const handleAccountsChanged = (accounts) => {
        if (accounts.length > 0) {
          setAddress(accounts[0]);
          fetchBalance(accounts[0]);
        } else {
          disconnect();
        }
      };

      const handleChainChanged = () => {
        window.location.reload();
      };

      window.ethereum.on('accountsChanged', handleAccountsChanged);
      window.ethereum.on('chainChanged', handleChainChanged);

      return () => {
        window.ethereum.removeListener('accountsChanged', handleAccountsChanged);
        window.ethereum.removeListener('chainChanged', handleChainChanged);
      };
    }
  }, [disconnect, fetchBalance]);

  return {
    address,
    isConnecting,
    error,
    usdcBalance,
    connect,
    disconnect,
    refreshBalance: () => fetchBalance(address)
  };
}
