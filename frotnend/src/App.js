import React, { useState, useEffect, useCallback } from 'react';

// You can install lucide-react for icons: npm install lucide-react
// For this example, we'll use simple text/SVG for status indicators.
// import { CheckCircle, XCircle, AlertTriangle, LogIn } from 'lucide-react';

const API_BASE_URL = "http://localhost:8000"; // Your FastAPI backend URL

// Simple SVG Icons (as lucide-react might not be available by default)
const CheckCircleIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-green-400 h-6 w-6 mr-2">
    <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path>
    <polyline points="22 4 12 14.01 9 11.01"></polyline>
  </svg>
);

const XCircleIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-red-400 h-6 w-6 mr-2">
    <circle cx="12" cy="12" r="10"></circle>
    <line x1="15" y1="9" x2="9" y2="15"></line>
    <line x1="9" y1="9" x2="15" y2="15"></line>
  </svg>
);

const AlertTriangleIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-yellow-400 h-6 w-6 mr-2">
    <path d="m21.73 18-8-14a2 2 0 0 0-3.46 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3Z"></path>
    <line x1="12" x2="12" y1="9" y2="13"></line>
    <line x1="12" x2="12.01" y1="17" y2="17"></line>
  </svg>
);

const LogInIcon = () => (
    <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="h-5 w-5 mr-2">
        <path d="M15 3h4a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2h-4"></path>
        <polyline points="10 17 15 12 10 7"></polyline>
        <line x1="15" y1="12" x2="3" y2="12"></line>
    </svg>
);


// Toast Notification Component
const Toast = ({ message, type, show }) => {
    if (!show) return null;

    let bgColor = 'bg-sky-500'; // Default info
    if (type === 'success') bgColor = 'bg-emerald-500';
    if (type === 'error') bgColor = 'bg-red-500';

    return (
        <div className={`fixed bottom-5 left-1/2 transform -translate-x-1/2 px-6 py-3 rounded-lg shadow-lg text-white ${bgColor} transition-opacity duration-300 ${show ? 'opacity-100' : 'opacity-0'}`}>
            {message}
        </div>
    );
};

// Main App Component
function App() {
    const [linkedinStatus, setLinkedinStatus] = useState({
        isConnected: false,
        userUrn: null,
        checking: true,
        error: null,
    });
    const [toast, setToast] = useState({ message: '', type: 'info', show: false });
    const [isLoading, setIsLoading] = useState(false); // For button loading state

    const showToast = useCallback((message, type = 'info', duration = 3000) => {
        setToast({ message, type, show: true });
        setTimeout(() => {
            setToast(prev => ({ ...prev, show: false }));
        }, duration);
    }, []);

    const fetchLinkedInStatus = useCallback(async () => {
        setLinkedinStatus(prev => ({ ...prev, checking: true, error: null }));
        try {
            const response = await fetch(`${API_BASE_URL}/auth/linkedin/status`);
            if (!response.ok) {
                const errorData = await response.json().catch(() => ({ detail: "Failed to fetch status" }));
                throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
            }
            const data = await response.json();
            setLinkedinStatus({
                isConnected: data.is_connected,
                userUrn: data.user_urn,
                checking: false,
                error: null,
            });
        } catch (error) {
            console.error('Error checking LinkedIn status:', error);
            setLinkedinStatus({
                isConnected: false,
                userUrn: null,
                checking: false,
                error: error.message,
            });
            showToast(`Error checking LinkedIn status: ${error.message}`, 'error');
        }
    }, [showToast]);

    useEffect(() => {
        fetchLinkedInStatus();

        const urlParams = new URLSearchParams(window.location.search);
        if (urlParams.get('auth_success') === 'true') {
            showToast('LinkedIn authentication successful!', 'success');
            fetchLinkedInStatus(); // Re-fetch status after successful auth
            window.history.replaceState({}, document.title, window.location.pathname);
        } else if (urlParams.get('auth_error')) {
            showToast(`LinkedIn authentication failed: ${urlParams.get('auth_error')}`, 'error');
            window.history.replaceState({}, document.title, window.location.pathname);
        }
    }, [fetchLinkedInStatus, showToast]);

    const handleLinkedInConnect = () => {
        setIsLoading(true);
        // The backend will handle the redirect to LinkedIn's authorization page
        window.location.href = `${API_BASE_URL}/auth/linkedin/login`;
        // No need to setIsLoading(false) here as the page will redirect
    };

    // Function to render status display
    const renderStatusDisplay = () => {
        if (linkedinStatus.checking) {
            return (
                <>
                    <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-sky-400 mr-2"></div>
                    <p className="text-slate-200">Status: <span className="font-semibold">Checking...</span></p>
                </>
            );
        }
        if (linkedinStatus.error) {
            return (
                <>
                    <AlertTriangleIcon />
                    <p className="text-slate-200">Status: <span className="font-semibold text-yellow-400">Error</span></p>
                </>
            );
        }
        if (linkedinStatus.isConnected) {
            return (
                <>
                    <CheckCircleIcon />
                    <p className="text-slate-200">Status: <span className="font-semibold text-green-400">Connected</span></p>
                </>
            );
        }
        return (
            <>
                <XCircleIcon />
                <p className="text-slate-200">Status: <span className="font-semibold text-red-400">Disconnected</span></p>
            </>
        );
    };


    return (
        <div className="bg-slate-900 text-slate-100 min-h-screen flex flex-col items-center justify-center p-4 font-['Inter',_sans-serif]">
            <div className="bg-slate-800 p-8 rounded-xl shadow-2xl w-full max-w-lg transform transition-all duration-500 hover:scale-105">
                <header className="text-center mb-10">
                    <h1 className="text-4xl font-bold text-sky-400 tracking-tight">
                        LinkedIn Automation Agent
                    </h1>
                    <p className="text-slate-400 mt-2">Manage your LinkedIn presence effortlessly.</p>
                </header>

                <section className="mb-8 p-6 bg-slate-700 rounded-lg shadow-md">
                    <h2 className="text-2xl font-semibold mb-6 text-sky-300 text-center">LinkedIn Connection</h2>
                    <div className="flex items-center justify-center mb-6 p-4 bg-slate-600/50 rounded-md min-h-[60px]">
                        {renderStatusDisplay()}
                    </div>
                    {linkedinStatus.isConnected && linkedinStatus.userUrn && (
                        <p className="text-sm text-slate-400 text-center mb-6">
                            Connected as: <span className="font-medium text-sky-400">{linkedinStatus.userUrn}</span>
                        </p>
                    )}
                     {linkedinStatus.error && (
                        <p className="text-sm text-red-400 text-center mb-6">
                            Details: {linkedinStatus.error}
                        </p>
                    )}
                    <button
                        onClick={handleLinkedInConnect}
                        disabled={isLoading || linkedinStatus.checking}
                        className={`w-full flex items-center justify-center font-semibold py-3 px-6 rounded-lg transition duration-200 ease-in-out focus:outline-none focus:ring-4 focus:ring-opacity-50
                                    ${isLoading || linkedinStatus.checking ? 'bg-slate-500 cursor-not-allowed' : 
                                      linkedinStatus.isConnected ? 'bg-orange-500 hover:bg-orange-600 focus:ring-orange-400 text-white' : 
                                                                  'bg-sky-500 hover:bg-sky-600 focus:ring-sky-400 text-white'}`}
                    >
                        {isLoading ? (
                            <>
                                <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-white mr-3"></div>
                                Processing...
                            </>
                        ) : (
                            <>
                                <LogInIcon />
                                {linkedinStatus.isConnected ? 'Reconnect to LinkedIn' : 'Connect to LinkedIn'}
                            </>
                        )}
                    </button>
                </section>

                {/* Agent Status/Log Section (Future Enhancement) */}
                <section className="p-6 bg-slate-700 rounded-lg shadow-md">
                    <h2 className="text-2xl font-semibold mb-4 text-sky-300 text-center">Agent Activity</h2>
                    <div className="text-center text-slate-400 p-4 bg-slate-600/50 rounded-md">
                        <p>Content generation and posting are managed automatically by the agent.</p>
                        <p className="mt-2">Approvals will be sent via WhatsApp.</p>
                        {/* In the future, you could display logs or last activity here */}
                    </div>
                </section>
            </div>

            <Toast message={toast.message} type={toast.type} show={toast.show} />
            
            <footer className="text-center text-slate-500 mt-10 text-sm">
                <p>&copy; {new Date().getFullYear()} LinkedIn Automation Agent. For personal use.</p>
            </footer>
        </div>
    );
}

export default App;
