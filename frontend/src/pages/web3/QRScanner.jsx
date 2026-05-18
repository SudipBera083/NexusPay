import React, { useState, useEffect, useRef } from 'react';
import { Html5QrcodeScanner } from 'html5-qrcode';
import { useNavigate } from 'react-router-dom';
import toast from 'react-hot-toast';

export default function QRScanner() {
  const navigate = useNavigate();
  const scannerRef = useRef(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    // Initialize Scanner
    const scanner = new Html5QrcodeScanner(
      "reader",
      { fps: 10, qrbox: { width: 250, height: 250 } },
      /* verbose= */ false
    );

    scanner.render(
      (decodedText) => {
        try {
          // Expecting JSON: { nonce: "...", signature: "...", amount: "..." }
          const data = JSON.parse(decodedText);
          if (data.nonce) {
            scanner.clear();
            navigate(`/pay/confirm/${data.nonce}`);
          } else {
            setError("Invalid QR Code format. Missing nonce.");
          }
        } catch (e) {
          setError("Invalid QR Code format. Not JSON.");
        }
      },
      (errorMessage) => {
        // Handle scan errors quietly (usually just means no QR found yet)
      }
    );

    scannerRef.current = scanner;

    return () => {
      if (scannerRef.current) {
        scannerRef.current.clear().catch(e => console.error(e));
      }
    };
  }, [navigate]);

  return (
    <div className="max-w-md mx-auto mt-12 space-y-6">
      <div className="text-center">
        <h1 className="text-3xl font-bold text-white mb-2">Scan to Pay</h1>
        <p className="text-gray-400">Scan a NexusPay Merchant QR Code to proceed</p>
      </div>

      <div className="bg-white p-4 rounded-2xl overflow-hidden shadow-2xl">
        <div id="reader" className="w-full rounded-xl overflow-hidden"></div>
      </div>

      {error && (
        <div className="bg-red-500/10 border border-red-500/50 p-4 rounded-xl text-center">
          <p className="text-red-400">{error}</p>
        </div>
      )}
    </div>
  );
}
