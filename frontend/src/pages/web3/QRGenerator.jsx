import React, { useState } from 'react';
import { QRCodeSVG } from 'qrcode.react';
import { merchantAPI } from '@/api/web3Client';
import toast from 'react-hot-toast';
import { ChevronLeft } from 'lucide-react';
import { Link } from 'react-router-dom';

export default function QRGenerator() {
  const [amount, setAmount] = useState('');
  const [qrData, setQrData] = useState(null);
  const [loading, setLoading] = useState(false);

  const handleGenerate = async (e) => {
    e.preventDefault();
    if (!amount || isNaN(amount) || Number(amount) <= 0) {
      toast.error('Please enter a valid amount');
      return;
    }

    setLoading(true);
    try {
      const response = await merchantAPI.generateQR({ amount_usdc: amount });
      setQrData(response.data.data);
      toast.success('QR Code generated');
    } catch (err) {
      toast.error('Failed to generate QR Code');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-xl mx-auto space-y-6">
      <div className="flex items-center space-x-4 mb-8">
        <Link to="/merchant" className="p-2 bg-gray-800 hover:bg-gray-700 rounded-lg transition-colors">
          <ChevronLeft className="w-5 h-5 text-gray-400" />
        </Link>
        <h1 className="text-2xl font-bold text-white">Generate Payment QR</h1>
      </div>

      <div className="bg-gray-800/50 p-6 rounded-xl border border-gray-700/50 shadow-xl">
        <form onSubmit={handleGenerate} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-1">Amount (USDC)</label>
            <input 
              type="number" 
              step="0.01"
              value={amount}
              onChange={(e) => setAmount(e.target.value)}
              className="w-full bg-gray-900 border border-gray-700 rounded-lg px-4 py-3 text-white text-lg focus:outline-none focus:border-orange-500" 
              placeholder="0.00" 
              required
            />
          </div>
          <button 
            type="submit" 
            disabled={loading}
            className="w-full py-3 bg-gradient-to-r from-orange-500 to-orange-600 text-white font-medium rounded-lg hover:from-orange-600 hover:to-orange-700 transition-all disabled:opacity-50"
          >
            {loading ? 'Generating...' : 'Generate QR'}
          </button>
        </form>
      </div>

      {qrData && (
        <div className="bg-white p-8 rounded-xl flex flex-col items-center justify-center space-y-4 animate-in fade-in slide-in-from-bottom-4">
          <h2 className="text-xl font-bold text-gray-900">Scan to Pay</h2>
          <p className="text-gray-500 text-sm">Please pay <span className="font-bold text-gray-900">{qrData.amount_usdc} USDC</span></p>
          
          <div className="p-4 border-2 border-gray-100 rounded-xl">
            <QRCodeSVG 
              value={JSON.stringify({
                nonce: qrData.nonce,
                signature: qrData.signature,
                amount: qrData.amount_usdc,
                merchant: qrData.merchant_name
              })}
              size={256}
              level="H"
              includeMargin={true}
            />
          </div>
          
          <div className="text-center">
            <p className="text-xs text-gray-400 font-mono">Nonce: {qrData.nonce}</p>
            <p className="text-xs text-gray-400">Expires at: {new Date(qrData.expires_at).toLocaleTimeString()}</p>
          </div>
        </div>
      )}
    </div>
  );
}
