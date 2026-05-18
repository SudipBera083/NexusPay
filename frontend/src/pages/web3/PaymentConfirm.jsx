import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { merchantAPI } from '@/api/web3Client';
import { useWallet } from '@/lib/blockchain/useWallet';
import { usdcService } from '@/lib/blockchain/token';
import toast from 'react-hot-toast';

export default function PaymentConfirm() {
  const { nonce } = useParams();
  const navigate = useNavigate();
  const { address, connect, isConnecting } = useWallet();
  
  const [qrStatus, setQrStatus] = useState(null);
  const [loading, setLoading] = useState(true);
  const [processing, setProcessing] = useState(false);

  useEffect(() => {
    fetchQRStatus();
  }, [nonce]);

  const fetchQRStatus = async () => {
    try {
      const response = await merchantAPI.getQRStatus(nonce);
      setQrStatus(response.data.data);
    } catch (err) {
      toast.error('Invalid or expired QR code');
      navigate('/pay/scan');
    } finally {
      setLoading(false);
    }
  };

  const handlePay = async () => {
    if (!address) {
      toast.error("Please connect wallet first");
      return;
    }

    setProcessing(true);
    try {
      // 1. Signed Wallet Challenge
      try {
        const { getProvider } = await import('@/lib/blockchain/provider');
        const provider = getProvider();
        if (provider.signer) {
           await provider.signer.signMessage(`NexusPay Login Challenge: ${nonce}`);
        }
      } catch (signError) {
        throw new Error("Wallet challenge rejected. Cannot proceed.");
      }

      // 2. Tell backend we are scanning/initiating (locks the QR)
      const scanRes = await merchantAPI.scanQR(nonce);
      const treasuryAddress = scanRes.data.data.merchant_wallet_address;
      
      // 3. Broadcast transaction via MetaMask
      const tx = await usdcService.sendPayment(treasuryAddress, qrStatus.amount_usdc);
      toast.loading("Transaction submitted, waiting for confirmation...", { id: 'tx' });

      // 4. Submit tx hash to backend
      await merchantAPI.submitTx({
        nonce: nonce,
        tx_hash: tx.txHash,
        wallet_address: address
      });
      
      toast.success("Payment submitted! Awaiting blockchain confirmations.", { id: 'tx' });
      navigate(`/explorer/tx/${tx.txHash}`);
      
    } catch (err) {
      console.error(err);
      toast.error(err.message || "Payment failed", { id: 'tx' });
    } finally {
      setProcessing(false);
    }
  };

  if (loading) {
    return <div className="flex justify-center p-12"><div className="w-8 h-8 border-4 border-orange-500 border-t-transparent rounded-full animate-spin"></div></div>;
  }

  if (!qrStatus) return null;

  return (
    <div className="max-w-md mx-auto mt-12 space-y-6">
      <div className="bg-gray-800/50 p-8 rounded-2xl border border-gray-700/50 shadow-2xl text-center relative overflow-hidden">
        {/* Glow effect */}
        <div className="absolute -top-24 -right-24 w-48 h-48 bg-orange-500/20 rounded-full blur-3xl"></div>
        <div className="absolute -bottom-24 -left-24 w-48 h-48 bg-purple-500/20 rounded-full blur-3xl"></div>

        <div className="relative z-10 space-y-6">
          <div>
            <h2 className="text-gray-400 text-sm font-medium uppercase tracking-wider mb-1">Paying To</h2>
            <h1 className="text-2xl font-bold text-white">{qrStatus.merchant_name}</h1>
          </div>

          <div className="py-6 border-y border-gray-700/50">
            <h2 className="text-gray-400 text-sm font-medium mb-2">Amount</h2>
            <div className="text-5xl font-black text-transparent bg-clip-text bg-gradient-to-br from-orange-400 to-orange-600">
              {qrStatus.amount_usdc}
              <span className="text-2xl ml-2 text-orange-500/80">USDC</span>
            </div>
          </div>

          <div className="space-y-4 pt-2">
            {!address ? (
              <button
                onClick={connect}
                disabled={isConnecting}
                className="w-full py-4 bg-gray-700 text-white font-medium rounded-xl hover:bg-gray-600 transition-colors"
              >
                {isConnecting ? 'Connecting MetaMask...' : 'Connect MetaMask to Pay'}
              </button>
            ) : (
              <div className="space-y-4">
                <div className="text-sm text-gray-400 bg-gray-900/50 p-3 rounded-lg border border-gray-700/50 break-all font-mono">
                  From: {address}
                </div>
                <button
                  onClick={handlePay}
                  disabled={processing}
                  className="w-full py-4 bg-gradient-to-r from-orange-500 to-orange-600 text-white font-bold text-lg rounded-xl shadow-lg shadow-orange-500/20 hover:shadow-orange-500/40 hover:-translate-y-0.5 transition-all disabled:opacity-50 disabled:transform-none"
                >
                  {processing ? 'Processing...' : 'Confirm Payment'}
                </button>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
