import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { blockchainAPI } from '@/api/web3Client';
import { Activity, ArrowRightLeft, ExternalLink, ShieldCheck } from 'lucide-react';
import { useWebSocket } from '@/hooks/useWebSocket';

export default function BlockchainExplorer() {
  const [transactions, setTransactions] = useState([]);
  const [loading, setLoading] = useState(true);

  // Re-fetch when we get a real-time event
  useWebSocket(null, (event) => {
    if (event.type === 'blockchain_transaction_updated') {
      fetchTransactions();
    }
  });

  useEffect(() => {
    fetchTransactions();
  }, []);

  const fetchTransactions = async () => {
    try {
      const response = await blockchainAPI.getTransactions();
      setTransactions(response.data.data || []);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-3xl font-bold text-white mb-2 flex items-center space-x-3">
          <Activity className="w-8 h-8 text-orange-500" />
          <span>Blockchain Explorer</span>
        </h1>
        <p className="text-gray-400">Live view of NexusPay's non-custodial settlement layer.</p>
      </div>

      <div className="bg-gray-800/50 rounded-2xl border border-gray-700/50 overflow-hidden shadow-xl">
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="bg-gray-900/80 border-b border-gray-700/50">
                <th className="py-5 px-6 text-xs font-semibold text-gray-400 uppercase tracking-wider">Tx Hash</th>
                <th className="py-5 px-6 text-xs font-semibold text-gray-400 uppercase tracking-wider">From → To</th>
                <th className="py-5 px-6 text-xs font-semibold text-gray-400 uppercase tracking-wider">Amount</th>
                <th className="py-5 px-6 text-xs font-semibold text-gray-400 uppercase tracking-wider">Status</th>
                <th className="py-5 px-6 text-xs font-semibold text-gray-400 uppercase tracking-wider">Confirmations</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-700/50">
              {transactions.map((tx) => (
                <tr key={tx.id} className="hover:bg-gray-700/20 transition-colors group">
                  <td className="py-4 px-6">
                    <Link to={`/explorer/tx/${tx.tx_hash}`} className="flex items-center space-x-2 text-orange-400 hover:text-orange-300 transition-colors font-mono text-sm">
                      <span>{tx.tx_hash.substring(0, 10)}...{tx.tx_hash.slice(-8)}</span>
                      <ExternalLink className="w-4 h-4 opacity-0 group-hover:opacity-100 transition-opacity" />
                    </Link>
                    <div className="text-xs text-gray-500 mt-1">{new Date(tx.submitted_at).toLocaleString()}</div>
                  </td>
                  <td className="py-4 px-6">
                    <div className="flex items-center space-x-2">
                      <span className="font-mono text-xs text-gray-400" title={tx.from_address}>{tx.from_address.substring(0,6)}...</span>
                      <ArrowRightLeft className="w-3 h-3 text-gray-600" />
                      <span className="font-mono text-xs text-gray-400" title={tx.to_address}>{tx.to_address.substring(0,6)}...</span>
                    </div>
                  </td>
                  <td className="py-4 px-6">
                    <div className="flex items-center space-x-1">
                      <span className="text-white font-medium">{tx.amount}</span>
                      <span className="text-gray-500 text-xs">{tx.currency}</span>
                    </div>
                  </td>
                  <td className="py-4 px-6">
                    <span className={`inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium border ${
                      tx.status === 'CONFIRMED' ? 'bg-green-500/10 text-green-400 border-green-500/20' :
                      tx.status === 'FAILED' ? 'bg-red-500/10 text-red-400 border-red-500/20' :
                      'bg-orange-500/10 text-orange-400 border-orange-500/20'
                    }`}>
                      {tx.status === 'CONFIRMED' && <ShieldCheck className="w-3 h-3 mr-1" />}
                      {tx.status}
                    </span>
                  </td>
                  <td className="py-4 px-6">
                    <div className="flex items-center space-x-2">
                      <div className="flex-1 h-1.5 bg-gray-700 rounded-full overflow-hidden">
                        <div 
                          className={`h-full rounded-full transition-all duration-500 ${
                            tx.status === 'CONFIRMED' ? 'bg-green-500' : 'bg-orange-500'
                          }`}
                          style={{ width: `${Math.min(100, (tx.confirmations / 3) * 100)}%` }}
                        />
                      </div>
                      <span className="text-xs text-gray-400 font-mono w-8">{tx.confirmations}/3</span>
                    </div>
                  </td>
                </tr>
              ))}
              
              {loading && (
                <tr>
                  <td colSpan="5" className="py-12 text-center">
                    <div className="w-6 h-6 border-2 border-orange-500 border-t-transparent rounded-full animate-spin mx-auto"></div>
                  </td>
                </tr>
              )}
              
              {!loading && transactions.length === 0 && (
                <tr>
                  <td colSpan="5" className="py-12 text-center text-gray-500">
                    No blockchain transactions found.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
