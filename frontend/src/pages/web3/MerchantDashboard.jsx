import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { merchantAPI } from '@/api/web3Client';
import toast from 'react-hot-toast';
import { QrCode, TrendingUp, DollarSign, Activity } from 'lucide-react';

export default function MerchantDashboard() {
  const [profile, setProfile] = useState(null);
  const [analytics, setAnalytics] = useState(null);
  const [qrCodes, setQrCodes] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      const [profileRes, analyticsRes, qrRes] = await Promise.all([
        merchantAPI.getProfile().catch(() => ({ data: { data: null } })),
        merchantAPI.getAnalytics().catch(() => ({ data: { data: null } })),
        merchantAPI.getQRCodes().catch(() => ({ data: { data: [] } }))
      ]);

      setProfile(profileRes.data.data);
      setAnalytics(analyticsRes.data.data);
      setQrCodes(qrRes.data.data || []);
    } catch (err) {
      toast.error("Failed to load merchant data");
    } finally {
      setLoading(false);
    }
  };

  const registerMerchant = async (e) => {
    e.preventDefault();
    const formData = new FormData(e.target);
    const data = {
      name: formData.get('name'),
      wallet_address: formData.get('wallet_address'),
      business_type: formData.get('business_type'),
    };

    try {
      await merchantAPI.register(data);
      toast.success("Merchant registered successfully!");
      fetchData();
    } catch (err) {
      toast.error(err.response?.data?.message || "Registration failed");
    }
  };

  if (loading) {
    return <div className="flex justify-center p-12"><div className="w-8 h-8 border-4 border-orange-500 border-t-transparent rounded-full animate-spin"></div></div>;
  }

  if (!profile) {
    return (
      <div className="max-w-2xl mx-auto space-y-8">
        <div>
          <h1 className="text-3xl font-bold text-white mb-2">Merchant Onboarding</h1>
          <p className="text-gray-400">Register your business to start accepting Web3 payments instantly.</p>
        </div>

        <form onSubmit={registerMerchant} className="bg-gray-800/50 p-6 rounded-xl border border-gray-700/50 space-y-6">
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-1">Business Name</label>
            <input name="name" required className="w-full bg-gray-900 border border-gray-700 rounded-lg px-4 py-2.5 text-white" placeholder="e.g. Acme Corp" />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-1">Settlement Wallet Address (EVM)</label>
            <input name="wallet_address" required pattern="^0x[a-fA-F0-9]{40}$" className="w-full bg-gray-900 border border-gray-700 rounded-lg px-4 py-2.5 text-white font-mono" placeholder="0x..." />
            <p className="text-xs text-gray-500 mt-1">This is where you will receive USDC settlements.</p>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-1">Business Type</label>
            <select name="business_type" className="w-full bg-gray-900 border border-gray-700 rounded-lg px-4 py-2.5 text-white">
              <option value="Retail">Retail</option>
              <option value="Digital Goods">Digital Goods</option>
              <option value="Services">Services</option>
            </select>
          </div>
          <button type="submit" className="w-full py-3 bg-gradient-to-r from-orange-500 to-orange-600 text-white font-medium rounded-lg hover:from-orange-600 hover:to-orange-700 transition-all shadow-lg shadow-orange-500/20">
            Register Business
          </button>
        </form>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-white mb-2">{profile.name} Dashboard</h1>
          <p className="text-gray-400 font-mono text-sm">Settlement Wallet: {profile.wallet_address}</p>
        </div>
        <Link to="/merchant/qr-generate" className="flex items-center space-x-2 px-6 py-3 bg-gradient-to-r from-orange-500 to-orange-600 text-white font-medium rounded-lg hover:from-orange-600 hover:to-orange-700 transition-all shadow-lg shadow-orange-500/20">
          <QrCode className="w-5 h-5" />
          <span>Generate Payment QR</span>
        </Link>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="bg-gray-800/50 p-6 rounded-xl border border-gray-700/50 flex items-center space-x-4">
          <div className="w-12 h-12 bg-green-500/20 text-green-400 rounded-full flex items-center justify-center">
            <DollarSign className="w-6 h-6" />
          </div>
          <div>
            <p className="text-gray-400 text-sm">Total Settled (USDC)</p>
            <p className="text-2xl font-bold text-white">{analytics?.total_settled_usdc || '0.00'}</p>
          </div>
        </div>
        <div className="bg-gray-800/50 p-6 rounded-xl border border-gray-700/50 flex items-center space-x-4">
          <div className="w-12 h-12 bg-blue-500/20 text-blue-400 rounded-full flex items-center justify-center">
            <Activity className="w-6 h-6" />
          </div>
          <div>
            <p className="text-gray-400 text-sm">Payments Count</p>
            <p className="text-2xl font-bold text-white">{analytics?.settlement_count || 0}</p>
          </div>
        </div>
        <div className="bg-gray-800/50 p-6 rounded-xl border border-gray-700/50 flex items-center space-x-4">
          <div className="w-12 h-12 bg-orange-500/20 text-orange-400 rounded-full flex items-center justify-center">
            <TrendingUp className="w-6 h-6" />
          </div>
          <div>
            <p className="text-gray-400 text-sm">Fees Paid (USDC)</p>
            <p className="text-2xl font-bold text-white">{analytics?.total_fees_usdc || '0.00'}</p>
          </div>
        </div>
      </div>

      <div>
        <h2 className="text-xl font-bold text-white mb-4">Recent Payment QRs</h2>
        <div className="bg-gray-800/50 rounded-xl border border-gray-700/50 overflow-hidden">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="bg-gray-900/50 border-b border-gray-700/50">
                <th className="py-4 px-6 text-sm font-medium text-gray-400">Amount (USDC)</th>
                <th className="py-4 px-6 text-sm font-medium text-gray-400">Nonce</th>
                <th className="py-4 px-6 text-sm font-medium text-gray-400">Status</th>
                <th className="py-4 px-6 text-sm font-medium text-gray-400">Created At</th>
              </tr>
            </thead>
            <tbody>
              {qrCodes.slice(0, 10).map((qr) => (
                <tr key={qr.id} className="border-b border-gray-700/50 hover:bg-gray-700/20 transition-colors">
                  <td className="py-4 px-6 text-white font-medium">{qr.amount_usdc}</td>
                  <td className="py-4 px-6 text-gray-400 font-mono text-sm">{qr.nonce.substring(0,8)}...</td>
                  <td className="py-4 px-6">
                    <span className={`px-2.5 py-1 rounded-full text-xs font-medium ${
                      qr.status === 'COMPLETED' ? 'bg-green-500/20 text-green-400' :
                      qr.status === 'ACTIVE' ? 'bg-blue-500/20 text-blue-400' :
                      qr.status === 'EXPIRED' ? 'bg-red-500/20 text-red-400' :
                      'bg-orange-500/20 text-orange-400'
                    }`}>
                      {qr.status}
                    </span>
                  </td>
                  <td className="py-4 px-6 text-gray-400 text-sm">{new Date(qr.created_at).toLocaleString()}</td>
                </tr>
              ))}
              {qrCodes.length === 0 && (
                <tr>
                  <td colSpan="4" className="py-8 text-center text-gray-500">No payment QRs generated yet.</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
