import React, { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { blockchainAPI } from '@/api/web3Client';
import { useWebSocket } from '@/hooks/useWebSocket';
import { ArrowLeft, CheckCircle2, CircleDashed, CheckCircle, Clock } from 'lucide-react';

export default function TransactionDetail() {
  const { hash } = useParams();
  const [tx, setTx] = useState(null);
  const [loading, setLoading] = useState(true);
  const REQUIRED_CONFIRMATIONS = 3;

  useWebSocket(null, (event) => {
    if (event.type === 'blockchain_transaction_updated' && event.payload.tx_hash === hash) {
      fetchTx();
    }
  });

  useEffect(() => {
    fetchTx();
    // Poll just in case websocket misses something during the critical window
    const interval = setInterval(fetchTx, 10000);
    return () => clearInterval(interval);
  }, [hash]);

  const fetchTx = async () => {
    try {
      const response = await blockchainAPI.getTransactionDetail(hash);
      setTx(response.data.data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return <div className="flex justify-center p-12"><div className="w-8 h-8 border-4 border-orange-500 border-t-transparent rounded-full animate-spin"></div></div>;
  }

  if (!tx) {
    return (
      <div className="text-center py-12">
        <h2 className="text-xl text-white">Transaction not found</h2>
        <p className="text-gray-400 mt-2">It may take a few moments to appear on the network.</p>
        <Link to="/explorer" className="text-orange-500 mt-4 inline-block hover:underline">Return to Explorer</Link>
      </div>
    );
  }

  const progress = Math.min(100, (tx.confirmations / REQUIRED_CONFIRMATIONS) * 100);
  const isComplete = tx.status === 'CONFIRMED';
  const isFailed = tx.status === 'FAILED';

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      <Link to="/explorer" className="inline-flex items-center space-x-2 text-gray-400 hover:text-white transition-colors">
        <ArrowLeft className="w-4 h-4" />
        <span>Back to Explorer</span>
      </Link>

      <div className="bg-gray-800/50 p-8 rounded-2xl border border-gray-700/50 shadow-2xl relative overflow-hidden">
        {/* Status Header */}
        <div className="flex flex-col items-center justify-center text-center space-y-4 mb-10 relative z-10">
          <div className={`w-20 h-20 rounded-full flex items-center justify-center ${
            isComplete ? 'bg-green-500/20 text-green-500' :
            isFailed ? 'bg-red-500/20 text-red-500' :
            'bg-orange-500/20 text-orange-500'
          }`}>
            {isComplete ? <CheckCircle className="w-10 h-10" /> :
             isFailed ? <CircleDashed className="w-10 h-10 text-red-500" /> :
             <Clock className="w-10 h-10 animate-pulse" />}
          </div>
          
          <div>
            <h1 className="text-3xl font-bold text-white mb-2">
              {isComplete ? 'Settlement Complete' :
               isFailed ? 'Transaction Failed' :
               'Awaiting Confirmations'}
            </h1>
            <p className="text-gray-400">
              {isComplete ? 'The transaction has been successfully verified on-chain.' :
               isFailed ? 'The transaction failed or was reverted.' :
               'Waiting for network validators to confirm the block.'}
            </p>
          </div>
        </div>

        {/* Progress Bar */}
        {!isFailed && (
          <div className="mb-10 relative z-10">
            <div className="flex justify-between text-sm mb-2">
              <span className="text-gray-400 font-medium">Network Consensus</span>
              <span className="text-white font-mono">{tx.confirmations} / {REQUIRED_CONFIRMATIONS} Blocks</span>
            </div>
            <div className="h-3 w-full bg-gray-900 rounded-full overflow-hidden">
              <div 
                className={`h-full rounded-full transition-all duration-1000 ease-out ${
                  isComplete ? 'bg-green-500 shadow-[0_0_10px_rgba(34,197,94,0.5)]' : 'bg-gradient-to-r from-orange-600 to-orange-400 shadow-[0_0_10px_rgba(249,115,22,0.5)]'
                }`}
                style={{ width: `${progress}%` }}
              />
            </div>
          </div>
        )}

        {/* Details Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 relative z-10">
          <div className="bg-gray-900/50 p-4 rounded-xl border border-gray-700/50">
            <p className="text-xs text-gray-500 uppercase tracking-wider mb-1">Transaction Hash</p>
            <a 
              href={`https://amoy.polygonscan.com/tx/${tx.tx_hash}`} 
              target="_blank" 
              rel="noopener noreferrer"
              className="text-orange-400 font-mono text-sm break-all hover:underline"
            >
              {tx.tx_hash}
            </a>
          </div>
          
          <div className="bg-gray-900/50 p-4 rounded-xl border border-gray-700/50">
            <p className="text-xs text-gray-500 uppercase tracking-wider mb-1">Status</p>
            <p className="text-white font-medium">{tx.status}</p>
          </div>

          <div className="bg-gray-900/50 p-4 rounded-xl border border-gray-700/50">
            <p className="text-xs text-gray-500 uppercase tracking-wider mb-1">From</p>
            <p className="text-white font-mono text-sm break-all">{tx.from_address}</p>
          </div>

          <div className="bg-gray-900/50 p-4 rounded-xl border border-gray-700/50">
            <p className="text-xs text-gray-500 uppercase tracking-wider mb-1">To</p>
            <p className="text-white font-mono text-sm break-all">{tx.to_address}</p>
          </div>

          <div className="bg-gray-900/50 p-4 rounded-xl border border-gray-700/50">
            <p className="text-xs text-gray-500 uppercase tracking-wider mb-1">Amount</p>
            <p className="text-2xl font-bold text-white">{tx.amount} <span className="text-sm text-gray-400 font-normal">{tx.currency}</span></p>
          </div>

          <div className="bg-gray-900/50 p-4 rounded-xl border border-gray-700/50">
            <p className="text-xs text-gray-500 uppercase tracking-wider mb-1">Network Block</p>
            <p className="text-white font-mono">{tx.block_number || 'Pending'}</p>
          </div>
        </div>

        {/* Decor */}
        {isComplete && (
          <div className="absolute top-0 right-0 -mr-20 -mt-20 w-64 h-64 bg-green-500/10 rounded-full blur-3xl pointer-events-none"></div>
        )}
      </div>
    </div>
  );
}
