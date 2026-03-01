import React, { useEffect, useState, useRef } from "react";
import "./index.css";

const API_BASE = (typeof window !== "undefined" && window.location.port === "8888")
    ? (import.meta.env.VITE_API_BASE_URL || "http://localhost:8002")
    : "";

// --- Hero Icon Components ---
const ChatIcon = () => <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path></svg>;
const DashboardIcon = () => <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><rect x="3" y="3" width="7" height="7"></rect><rect x="14" y="3" width="7" height="7"></rect><rect x="14" y="14" width="7" height="7"></rect><rect x="3" y="14" width="7" height="7"></rect></svg>;
const TraceIcon = () => <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"></polyline></svg>;
const MicIcon = () => <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"></path><path d="M19 10v2a7 7 0 0 1-14 0v-2"></path><line x1="12" y1="19" x2="12" y2="23"></line><line x1="8" y1="23" x2="16" y2="23"></line></svg>;
const PaperclipIcon = () => <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M21.44 11.05l-9.19 9.19a6 6 0 0 1-8.49-8.49l9.19-9.19a4 4 0 0 1 5.66 5.66l-9.2 9.19a2 2 0 0 1-2.83-2.83l8.49-8.48"></path></svg>;
const DatabaseAltIcon = () => <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><ellipse cx="12" cy="5" rx="9" ry="3"></ellipse><path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3"></path><path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5"></path></svg>;

function App() {
    const [user, setUser] = useState(null);
    const [authMode, setAuthMode] = useState("login"); // login or register
    const [authForm, setAuthForm] = useState({ username: "", password: "", email: "" });
    const [activeTab, setActiveTab] = useState("consultation");
    const [orders, setOrders] = useState([]);
    const [traces, setTraces] = useState([]);
    const [lowStock, setLowStock] = useState([]);
    const [refillAlerts, setRefillAlerts] = useState([]);
    const [messages, setMessages] = useState([
        { role: "assistant", content: "👋 Welcome to RxGenie AI. I'm your premium digital pharmacist. How can I assist you with your health today?" }
    ]);
    const [inputText, setInputText] = useState("");
    const [isListening, setIsListening] = useState(false);
    const [isTyping, setIsTyping] = useState(false);
    const [expandedTrace, setExpandedTrace] = useState(null);
    const [uploadedPrescription, setUploadedPrescription] = useState(null);
    const [showPrescriptionArea, setShowPrescriptionArea] = useState(false);
    const [deferredPrompt, setDeferredPrompt] = useState(null);
    const [databaseSnapshot, setDatabaseSnapshot] = useState({ orders: [], inventory: [] });
    const [isEmailServiceLive, setIsEmailServiceLive] = useState(false);
    const [apiStatus, setApiStatus] = useState("checking"); // checking, connected, failed

    const recognitionRef = useRef(null);
    const scrollRef = useRef(null);

    useEffect(() => {
        const savedUser = localStorage.getItem("rxgenie_user");
        if (savedUser) {
            setUser(JSON.parse(savedUser));
        }

        // PWA Install Prompt Logic
        const handleBeforeInstallPrompt = (e) => {
            e.preventDefault();
            setDeferredPrompt(e);
        };
        window.addEventListener('beforeinstallprompt', handleBeforeInstallPrompt);

        if ("webkitSpeechRecognition" in window || "SpeechRecognition" in window) {
            const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
            recognitionRef.current = new SpeechRecognition();
            recognitionRef.current.lang = "en-IN";
            recognitionRef.current.continuous = false;
            recognitionRef.current.interimResults = false;

            recognitionRef.current.onresult = (event) => {
                const transcript = event.results[0][0].transcript;
                setInputText(transcript);
                handleSend(transcript);
                setIsListening(false);
            };

            recognitionRef.current.onerror = (event) => {
                console.error("Speech recognition error", event.error);
                setIsListening(false);
            };
            recognitionRef.current.onend = () => setIsListening(false);
        }

        return () => {
            window.removeEventListener('beforeinstallprompt', handleBeforeInstallPrompt);
        };
    }, []);

    useEffect(() => {
        if (user) {
            fetchDashboardData();
            checkEmailServiceStatus();
            checkApiHealth();
            if (activeTab === "database") {
                fetchDatabaseSnapshot();
            }
        } else {
            checkApiHealth();
        }
    }, [user, activeTab]);

    const checkApiHealth = async () => {
        try {
            const res = await fetch(`${API_BASE}/health/email`);
            if (res.ok) setApiStatus("connected");
            else setApiStatus("failed");
        } catch (err) {
            setApiStatus("failed");
        }
    };

    const checkEmailServiceStatus = async () => {
        try {
            const res = await fetch(`${API_BASE}/health/email`);
            const data = await res.json();
            setIsEmailServiceLive(data.live);
        } catch (err) {
            setIsEmailServiceLive(false);
        }
    };

    const fetchDatabaseSnapshot = async () => {
        try {
            const res = await fetch(`${API_BASE}/admin/database-snapshot`);
            const data = await res.json();
            setDatabaseSnapshot(data);
        } catch (err) {
            console.error("DB Snapshot fetch error", err);
        }
    };

    const handleAuth = async (e) => {
        e.preventDefault();
        const endpoint = authMode === "login" ? "/auth/login" : "/auth/register";
        try {
            const res = await fetch(`${API_BASE}${endpoint}`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(authForm)
            });
            const data = await res.json();
            if (res.ok) {
                setUser(data.user);
                localStorage.setItem("rxgenie_user", JSON.stringify(data.user));
            } else {
                alert(data.detail || "Auth failed");
            }
        } catch (err) {
            console.error(err);
            alert("Connection error");
        }
    };

    const handleLogout = () => {
        setUser(null);
        localStorage.removeItem("rxgenie_user");
        setMessages([{ role: "assistant", content: "👋 Welcome to RxGenie AI. I'm your premium digital pharmacist. How can I assist you with your health today?" }]);
    };

    const speakContent = (text) => {
        if ("speechSynthesis" in window) {
            // Cancel any ongoing speech
            window.speechSynthesis.cancel();

            // Clean markdown bold/bullets for cleaner speech
            const cleanText = text.replace(/\*\*|\*|-|#/g, "");
            const utterance = new SpeechSynthesisUtterance(cleanText);
            utterance.rate = 1.0;
            utterance.pitch = 1.1; // Slightly higher for "Genie" vibe
            window.speechSynthesis.speak(utterance);
        }
    };

    useEffect(() => {
        if (scrollRef.current) {
            scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
        }
    }, [messages, isTyping]);

    const fetchDashboardData = async () => {
        if (!user) return;
        try {
            const [ordersRes, tracesRes, stockRes, refillsRes] = await Promise.all([
                fetch(`${API_BASE}/orders?patient_id=${user.patient_id}`).catch(() => ({ json: () => [] })),
                fetch(`${API_BASE}/admin/traces?patient_id=${user.patient_id}`).catch(() => ({ json: () => [] })),
                fetch(`${API_BASE}/admin/low-stock`).catch(() => ({ json: () => [] })),
                fetch(`${API_BASE}/admin/refills?patient_id=${user.patient_id}`).catch(() => ({ json: () => [] }))
            ]);

            const ordersData = typeof ordersRes.json === 'function' ? await ordersRes.json() : [];
            const tracesData = typeof tracesRes.json === 'function' ? await tracesRes.json() : [];
            const stockData = typeof stockRes.json === 'function' ? await stockRes.json() : [];
            const refillsData = typeof refillsRes.json === 'function' ? await refillsRes.json() : [];

            setOrders(Array.isArray(ordersData) ? ordersData : []);
            setTraces(Array.isArray(tracesData) ? tracesData : []);
            setLowStock(Array.isArray(stockData) ? stockData : []);
            setRefillAlerts(Array.isArray(refillsData) ? refillsData : []);
        } catch (err) {
            console.error("Fetch error", err);
        }
    };

    const startListening = () => {
        if (recognitionRef.current) {
            setIsListening(true);
            recognitionRef.current.start();
        } else {
            alert("Speech recognition not supported.");
        }
    };

    const handleSend = async (textOverride = null) => {
        const textToSubmit = textOverride || inputText;
        if (!textToSubmit.trim() || !user) return;

        const newUserMsg = { role: "user", content: textToSubmit };
        setMessages((prev) => [...prev, newUserMsg]);
        setInputText("");
        setShowPrescriptionArea(false);
        setIsTyping(true);

        try {
            const payload = {
                patient_id: user.patient_id,
                text: textToSubmit
            };
            if (uploadedPrescription) {
                payload.prescription_data = uploadedPrescription;
            }

            const res = await fetch(`${API_BASE}/chat-order`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(payload)
            });
            const data = await res.json();

            // Clear prescription after sending
            setUploadedPrescription(null);
            let aiContent = data.message || data.response || data.reason || "I've processed your request.";

            // If order was successful, append extra info
            if (data.success && data.action?.status === "Order Processed") {
                aiContent += `\n\n✅ Order confirmed and saved to your records!`;
                if (data.refill_alerts?.length > 0) {
                    aiContent += `\n🔔 Refill reminder: ${data.refill_alerts[0].reason || "Check your stock soon."}`;
                }
            }

            setMessages(prev => [...prev, { role: "assistant", content: aiContent, traces: data.traces || [] }]);
            speakContent(aiContent);
            fetchDashboardData();

        } catch (err) {
            const errorMsg = "I'm having trouble connecting to the medical nexus. Please try again.";
            setMessages(prev => [...prev, { role: "assistant", content: errorMsg }]);
            speakContent(errorMsg);
        } finally {
            setIsTyping(false);
        }
    };

    const TraceAccordion = ({ traces, index }) => {
        if (!traces || traces.length === 0) return null;
        const isExpanded = expandedTrace === index;

        return (
            <div style={{ marginTop: '12px', borderTop: '1px solid var(--border-light)', paddingTop: '10px' }}>
                <button
                    onClick={() => setExpandedTrace(isExpanded ? null : index)}
                    style={{
                        background: 'none',
                        border: 'none',
                        color: 'var(--primary)',
                        fontSize: '0.8rem',
                        cursor: 'pointer',
                        display: 'flex',
                        alignItems: 'center',
                        gap: '5px',
                        padding: 0
                    }}
                >
                    <TraceIcon /> {isExpanded ? 'Hide Reasoning' : 'Show Agent Reasoning Traces'}
                </button>
                {isExpanded && (
                    <div style={{ marginTop: '10px', display: 'flex', flexDirection: 'column', gap: '8px' }}>
                        {traces.map((t, ti) => (
                            <div key={ti} style={{ background: 'rgba(0,0,0,0.03)', padding: '10px', borderRadius: '8px', fontSize: '0.8rem' }}>
                                <div style={{ fontWeight: 600, color: 'var(--secondary)', marginBottom: '4px' }}>{t.agent_name}</div>
                                <div style={{ color: 'var(--text-muted)', fontStyle: 'italic', marginBottom: '4px' }}>{t.reasoning}</div>
                                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                                    <span style={{ fontSize: '0.7rem', opacity: 0.7 }}>Outcome: {t.decision}</span>
                                    <span className="badge" style={{ fontSize: '0.6rem', padding: '2px 6px' }}>{new Date(t.timestamp).toLocaleTimeString()}</span>
                                </div>
                            </div>
                        ))}
                    </div>
                )}
            </div>
        );
    };

    return (
        <div style={{ display: 'flex', minHeight: '100vh', background: 'var(--bg-vibrant)', padding: '20px', gap: '20px', fontFamily: 'Inter, sans-serif' }}>
            {!user && (
                <div style={{
                    position: 'fixed', top: 0, left: 0, width: '100vw', height: '100vh',
                    background: 'rgba(255,255,255,0.95)', zIndex: 1000,
                    display: 'flex', alignItems: 'center', justifyContent: 'center'
                }}>
                    <div className="card" style={{ width: '400px', padding: '40px', textAlign: 'center' }}>
                        <h2 style={{ marginBottom: '10px', color: 'var(--primary)' }}>RxGenie Premium 🧞‍♂️</h2>
                        <p style={{ color: 'var(--text-muted)', marginBottom: '30px' }}>
                            {authMode === "login" ? "Welcome back! Please login." : "Create your account to get started."}
                        </p>
                        <form onSubmit={handleAuth} style={{ display: 'flex', flexDirection: 'column', gap: '15px' }}>
                            <input
                                type="text"
                                placeholder="Username"
                                className="chat-input"
                                value={authForm.username}
                                onChange={e => setAuthForm({ ...authForm, username: e.target.value })}
                                required
                            />
                            <input
                                type="password"
                                placeholder="Password"
                                className="chat-input"
                                value={authForm.password}
                                onChange={e => setAuthForm({ ...authForm, password: e.target.value })}
                                required
                            />
                            {authMode === "register" && (
                                <input
                                    type="email"
                                    placeholder="Email Address"
                                    className="chat-input"
                                    value={authForm.email}
                                    onChange={e => setAuthForm({ ...authForm, email: e.target.value })}
                                    required
                                />
                            )}
                            <button type="submit" className="btn" style={{ width: '100%', fontSize: '1rem', background: 'var(--secondary)' }}>
                                {authMode === "login" ? "Login" : "Register"}
                            </button>
                        </form>
                        <p style={{ marginTop: '20px', fontSize: '0.9rem' }}>
                            {authMode === "login" ? "New here? " : "Already have an account? "}
                            <span
                                style={{ color: 'var(--primary)', cursor: 'pointer', fontWeight: '600' }}
                                onClick={() => setAuthMode(authMode === "login" ? "register" : "login")}
                            >
                                {authMode === "login" ? "Create account" : "Login here"}
                            </span>
                        </p>
                    </div>
                </div>
            )}

            {/* Sidebar */}
            <aside style={{ width: '280px', display: 'flex', flexDirection: 'column', gap: '15px' }}>
                <div style={{ padding: '10px 10px 20px 10px', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                    <div>
                        <h1 style={{ fontSize: '1.5rem', margin: 0, color: 'var(--primary)', fontWeight: '800' }}>RxGenie</h1>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '5px', marginTop: '2px' }}>
                            <div style={{ width: '6px', height: '6px', borderRadius: '50%', background: apiStatus === "connected" ? "#10b981" : (apiStatus === "failed" ? "#ef4444" : "#f59e0b") }}></div>
                            <span style={{ fontSize: '0.6rem', color: 'var(--text-muted)', fontWeight: '600', textTransform: 'uppercase' }}>
                                API {apiStatus}
                            </span>
                        </div>
                    </div>
                    {user && (
                        <button
                            type="button"
                            onClick={(e) => { e.preventDefault(); handleLogout(); }}
                            style={{ fontSize: '0.7rem', color: 'var(--secondary)', border: 'none', background: 'none', cursor: 'pointer', padding: '5px' }}
                        >
                            Logout
                        </button>
                    )}
                </div>

                <div className="card" style={{ padding: '15px' }}>
                    <div
                        className={`nav-item ${activeTab === 'consultation' ? 'active' : ''}`}
                        onClick={(e) => { e.preventDefault(); setActiveTab('consultation'); }}
                    >
                        <ChatIcon /> Consultation
                    </div>
                    <div
                        className={`nav-item ${activeTab === 'dashboard' ? 'active' : ''}`}
                        onClick={(e) => { e.preventDefault(); setActiveTab('dashboard'); }}
                    >
                        <DashboardIcon /> Admin Panel
                    </div>
                    <div
                        className={`nav-item ${activeTab === 'traces' ? 'active' : ''}`}
                        onClick={(e) => { e.preventDefault(); setActiveTab('traces'); }}
                    >
                        <TraceIcon /> Agent Traces
                    </div>
                    <div
                        className={`nav-item ${activeTab === 'database' ? 'active' : ''}`}
                        onClick={(e) => { e.preventDefault(); setActiveTab('database'); }}
                    >
                        <DatabaseAltIcon /> Live Database
                    </div>
                </div>

                {/* Mobile App Download */}
                <div className="card" style={{
                    marginTop: '20px',
                    textAlign: 'center',
                    background: 'rgba(255, 255, 255, 0.8)',
                    border: '1px solid rgba(16, 185, 129, 0.2)',
                    padding: '20px 15px'
                }}>
                    <h4 style={{ margin: '0 0 5px 0', color: 'var(--primary)', fontWeight: '700' }}>RxGenie Everywhere 📱</h4>
                    <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '15px' }}>Install the expert app on any device</p>

                    <div style={{
                        background: 'white',
                        padding: '12px',
                        borderRadius: '16px',
                        display: 'inline-block',
                        marginBottom: '15px',
                        boxShadow: '0 4px 12px rgba(0,0,0,0.08)',
                        border: '1px solid #f1f5f9'
                    }}>
                        <img src="/qr_code.png" alt="Scan QR" style={{ width: '120px', height: '120px', display: 'block' }} />
                        <div style={{ fontSize: '0.65rem', fontWeight: '600', color: 'var(--primary)', marginTop: '8px' }}>SCAN TO INSTALL</div>
                    </div>

                    <div style={{ borderTop: '1px solid #f1f5f9', paddingTop: '15px', marginTop: '5px' }}>
                        {deferredPrompt ? (
                            <button
                                className="btn"
                                style={{ width: '100%', fontSize: '0.85rem', background: 'var(--primary)', boxShadow: '0 4px 10px rgba(16, 185, 129, 0.2)' }}
                                onClick={async () => {
                                    deferredPrompt.prompt();
                                    const { outcome } = await deferredPrompt.userChoice;
                                    if (outcome === 'accepted') {
                                        setDeferredPrompt(null);
                                    }
                                }}
                            >
                                ✨ Install as Desktop App
                            </button>
                        ) : (
                            <div style={{ padding: '10px', background: '#f8fafc', borderRadius: '10px', border: '1px solid #e2e8f0' }}>
                                <div style={{ fontSize: '0.7rem', color: 'var(--primary)', fontWeight: '700', marginBottom: '4px' }}>ALREADY INSTALLED?</div>
                                <p style={{ fontSize: '0.65rem', color: 'var(--text-muted)', margin: 0, lineHeight: '1.4' }}>
                                    If on Mobile, tap <b>'Add to Home Screen'</b> in your browser menu for the full experience.
                                </p>
                            </div>
                        )}
                    </div>
                </div>

                <div className="card" style={{ marginTop: '20px', background: 'linear-gradient(135deg, var(--secondary), #4f46e5)', color: 'white' }}>
                    <h4 style={{ margin: '0 0 10px 0' }}>Proactive Alerts</h4>
                    <p style={{ fontSize: '0.85rem', opacity: 0.9 }}>{lowStock.length} items require restock in your inventory.</p>
                    <button className="btn" style={{ background: 'rgba(255,255,255,0.2)', width: '100%', color: 'white', marginTop: '10px' }}>View Alerts</button>
                </div>
            </aside>

            {/* Main Content Area */}
            <main style={{ minWidth: 0, flex: 1 }}>
                {activeTab === 'consultation' && (
                    <div className="card" style={{ height: '750px', display: 'flex', flexDirection: 'column', gap: '0', padding: '0', overflow: 'hidden' }}>
                        <div style={{ padding: '25px 30px', borderBottom: '1px solid var(--border-light)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                            <div>
                                <h3 style={{ margin: 0 }}>AI Health Consultant</h3>
                                <p style={{ margin: '5px 0 0 0', fontSize: '0.85rem', color: 'var(--text-muted)' }}>Powered by Groq & Llama 3.3</p>
                            </div>
                            <div style={{ display: 'flex', gap: '8px' }}>
                                <span className="badge badge-success">System Online</span>
                                <span className="badge badge-warning">Voice Ready</span>
                            </div>
                        </div>

                        <div ref={scrollRef} style={{ flex: 1, overflowY: 'auto', padding: '30px', display: 'flex', flexDirection: 'column' }}>
                            {messages.map((m, i) => (
                                <div key={i} className={`chat-bubble ${m.role === 'user' ? 'chat-user' : 'chat-ai'}`} style={{ whiteSpace: 'pre-wrap' }}>
                                    {m.content}
                                    {m.role === 'assistant' && (
                                        <TraceAccordion traces={m.traces} index={i} />
                                    )}
                                </div>
                            ))}
                            {isTyping && (
                                <div className="chat-bubble chat-ai" style={{ display: 'flex', gap: '4px', padding: '12px 20px' }}>
                                    <div style={{ width: '6px', height: '6px', background: '#cbd5e1', borderRadius: '50%', animation: 'bounce 0.6s infinite alternate' }}></div>
                                    <div style={{ width: '6px', height: '6px', background: '#cbd5e1', borderRadius: '50%', animation: 'bounce 0.6s infinite alternate 0.2s' }}></div>
                                    <div style={{ width: '6px', height: '6px', background: '#cbd5e1', borderRadius: '50%', animation: 'bounce 0.6s infinite alternate 0.4s' }}></div>
                                </div>
                            )}
                        </div>

                        <div style={{ padding: '25px 30px', background: '#f8fafc', borderTop: '1px solid var(--border-light)' }}>
                            {showPrescriptionArea && (
                                <div style={{ marginBottom: '15px', animation: 'slideUp 0.3s ease' }}>
                                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                                        <label style={{ fontSize: '0.8rem', fontWeight: 600, color: 'var(--primary)' }}>📄 Doctor's Note / Prescription</label>
                                        <button
                                            onClick={() => { setUploadedPrescription(null); setShowPrescriptionArea(false); }}
                                            style={{ background: 'none', border: 'none', color: '#ef4444', fontSize: '0.7rem', cursor: 'pointer' }}
                                        >
                                            Clear & Close
                                        </button>
                                    </div>
                                    <textarea
                                        style={{ width: '100%', borderRadius: '12px', border: '1px solid #e2e8f0', padding: '10px', fontSize: '0.85rem', minHeight: '80px', background: 'white', resize: 'none' }}
                                        placeholder="Type or paste the prescription details here (e.g., Patient is prescribed Aqualibra...)"
                                        value={uploadedPrescription || ""}
                                        onChange={(e) => setUploadedPrescription(e.target.value)}
                                    />
                                </div>
                            )}
                            <div style={{ display: 'flex', gap: '15px', alignItems: 'center' }}>
                                <div style={{ position: 'relative', flex: 1, display: 'flex', alignItems: 'center' }}>
                                    <input
                                        autoFocus
                                        style={{ width: '100%', boxSizing: 'border-box', border: '2px solid ' + (uploadedPrescription ? 'var(--primary)' : '#e2e8f0'), borderRadius: '18px', padding: '16px 80px 16px 20px', transition: 'all 0.3s' }}
                                        placeholder={uploadedPrescription ? "Prescription attached. Send order..." : "Tell me what medication you need..."}
                                        value={inputText}
                                        onChange={(e) => setInputText(e.target.value)}
                                        onKeyDown={(e) => e.key === "Enter" && handleSend()}
                                    />
                                    <div style={{ position: 'absolute', right: '15px', display: 'flex', gap: '10px', alignItems: 'center' }}>
                                        <button
                                            onClick={() => setShowPrescriptionArea(!showPrescriptionArea)}
                                            style={{ background: 'none', border: 'none', cursor: 'pointer', color: uploadedPrescription ? '#10b981' : '#94a3b8', display: 'flex', alignItems: 'center' }}
                                            title="Attach Prescription"
                                        >
                                            <PaperclipIcon />
                                        </button>
                                        <button
                                            onClick={() => startListening()}
                                            style={{ background: 'none', border: 'none', cursor: 'pointer', color: isListening ? 'var(--secondary)' : '#94a3b8', display: 'flex', alignItems: 'center' }}
                                            title="Use Voice"
                                        >
                                            <MicIcon />
                                        </button>
                                    </div>
                                </div>
                                <button className="btn" onClick={() => handleSend()}>Send Prompt</button>
                            </div>
                        </div>
                    </div>
                )}

                {activeTab === 'dashboard' && (
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
                        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px' }}>
                            <div className="card">
                                <h3>📧 Email Notification Settings</h3>
                                <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginBottom: '15px' }}>Receive proactive refill alerts at your real email address.</p>
                                <div style={{ display: 'flex', gap: '10px' }}>
                                    <input
                                        type="email"
                                        style={{ flex: 1, padding: '10px', borderRadius: '8px', border: '1px solid #e2e8f0' }}
                                        placeholder="e.g., mandlavaishnavi602@gmail.com"
                                        value={user?.email || ""}
                                        onChange={(e) => setUser({ ...user, email: e.target.value })}
                                    />
                                    <button
                                        className="btn"
                                        style={{ background: 'var(--primary)', padding: '10px 15px' }}
                                        onClick={async () => {
                                            try {
                                                const res = await fetch(`${API_BASE}/auth/update-email`, {
                                                    method: "POST",
                                                    headers: { "Content-Type": "application/json" },
                                                    body: JSON.stringify({ username: user.username, email: user.email })
                                                });
                                                if (res.ok) alert("✅ Email saved! You will now receive refill alerts here.");
                                                else alert("Failed to save email.");
                                            } catch (err) { console.error(err); }
                                        }}
                                    >
                                        Save
                                    </button>
                                </div>
                                <div style={{ marginTop: '8px', display: 'flex', alignItems: 'center', gap: '5px' }}>
                                    <div style={{ width: '8px', height: '8px', borderRadius: '50%', background: isEmailServiceLive ? '#10b981' : '#f59e0b' }}></div>
                                    <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>
                                        {isEmailServiceLive ? "LIVE: Real Email active" : "DEMO: Printing to terminal logs (SMTP not configured)"}
                                    </span>
                                </div>
                                <div style={{ marginTop: '20px' }}>
                                    <h4 style={{ fontSize: '0.9rem', marginBottom: '10px' }}>📉 Low Stock Inventory</h4>
                                    {lowStock.length > 0 ? lowStock.map((item, idx) => (
                                        <div key={idx} style={{ display: 'flex', justifyContent: 'space-between', padding: '10px 0', borderBottom: '1px solid #f1f5f9', fontSize: '0.9rem' }}>
                                            <span>{item['product name']}</span>
                                            <span style={{ fontWeight: 600, color: 'var(--secondary)' }}>{item.stock} left</span>
                                        </div>
                                    )) : <p style={{ color: 'var(--text-muted)', fontSize: '0.9rem' }}>No low stock alerts.</p>}
                                </div>
                            </div>
                            <div className="card">
                                <h3>🔔 Proactive Refill Alerts</h3>
                                <div style={{ marginTop: '20px', display: 'flex', flexDirection: 'column', gap: '12px' }}>
                                    {refillAlerts.length > 0 ? refillAlerts.map((alert, idx) => (
                                        <div key={idx} style={{ padding: '15px', background: '#fffbeb', border: '1px solid #fef3c7', borderRadius: '12px', color: '#92400e' }}>
                                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                                                <strong>Refill Soon: {alert.medicine}</strong>
                                                <span className="badge badge-warning" style={{ fontSize: '0.6rem' }}>{alert.days} days left</span>
                                            </div>
                                            <p style={{ margin: '5px 0', fontSize: '0.85rem' }}>{alert.reason}</p>
                                            <button
                                                className="btn"
                                                style={{ background: '#059669', marginTop: '10px', width: '100%', fontSize: '0.8rem' }}
                                                onClick={() => {
                                                    setInputText(`I need a refill for ${alert.medicine}`);
                                                    setActiveTab('consultation');
                                                }}
                                            >
                                                Auto-Refill Now
                                            </button>
                                        </div>
                                    )) : (
                                        <div style={{ textAlign: 'center', padding: '20px', color: 'var(--text-muted)', fontSize: '0.9rem' }}>
                                            No urgent refill alerts.
                                        </div>
                                    )}
                                </div>
                            </div>
                        </div>

                        <div className="card" style={{ marginTop: '20px' }}>
                            <h3>📦 Recent Fulfillment Log</h3>
                            <table style={{ width: '100%', marginTop: '20px', borderCollapse: 'collapse' }}>
                                <thead>
                                    <tr style={{ textAlign: 'left', color: 'var(--text-muted)', fontSize: '0.85rem' }}>
                                        <th style={{ padding: '12px' }}>ORDER ITEM</th>
                                        <th style={{ padding: '12px' }}>PATIENT ID</th>
                                        <th style={{ padding: '12px' }}>DOSAGE</th>
                                        <th style={{ padding: '12px' }}>REVENUE</th>
                                        <th style={{ padding: '12px' }}>STATUS</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {orders.map((o, idx) => (
                                        <tr key={idx} style={{ borderTop: '1px solid #f1f5f9' }}>
                                            <td style={{ padding: '12px', fontWeight: 500 }}>{o.product?.name}</td>
                                            <td style={{ padding: '12px', color: 'var(--text-muted)' }}>{o.patient?.id}</td>
                                            <td style={{ padding: '12px' }}>{o.dosage_frequency || 'As directed'}</td>
                                            <td style={{ padding: '12px', fontWeight: 600 }}>€{o.total_price?.toFixed(2)}</td>
                                            <td style={{ padding: '12px' }}><span className="badge badge-success">FULFILLED</span></td>
                                        </tr>
                                    ))}
                                    {orders.length === 0 && (
                                        <tr><td colSpan="5" style={{ textAlign: 'center', padding: '20px', color: 'var(--text-muted)' }}>No orders found yet.</td></tr>
                                    )}
                                </tbody>
                            </table>
                        </div>
                    </div>
                )}

                {activeTab === 'traces' && (
                    <div className="card">
                        <h3>🔍 Expert Agent Trace Logs</h3>
                        <div style={{ marginTop: '20px', display: 'flex', flexDirection: 'column', gap: '15px' }}>
                            {traces.map((t, idx) => (
                                <div key={idx} style={{ padding: '20px', border: '1px solid #e2e8f0', borderRadius: '12px' }}>
                                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '10px' }}>
                                        <span style={{ fontWeight: 700, color: 'var(--primary)' }}>Trace ID: {t._id.slice(-6).toUpperCase()}</span>
                                        <span className="badge">{new Date(t.timestamp).toLocaleString()}</span>
                                    </div>
                                    <p style={{ margin: '5px 0', fontSize: '0.95rem' }}><strong>Agent:</strong> {t.agent_name}</p>
                                    <p style={{ margin: '5px 0', fontSize: '0.95rem' }}><strong>Expert Logic:</strong> {t.reasoning}</p>
                                    <div style={{ marginTop: '10px', padding: '10px', background: '#f8fafc', borderRadius: '8px', fontSize: '0.85rem', fontFamily: 'monospace' }}>
                                        {JSON.stringify(t.result, null, 2)}
                                    </div>
                                </div>
                            ))}
                            {traces.length === 0 && <p style={{ textAlign: 'center', color: 'var(--text-muted)' }}>No logs available.</p>}
                        </div>
                    </div>
                )}

                {activeTab === 'database' && (
                    <div className="card">
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
                            <h3>🗄️ Real-time MongoDB Snapshot</h3>
                            <button className="btn" style={{ fontSize: '0.8rem' }} onClick={fetchDatabaseSnapshot}>Refresh DB</button>
                        </div>

                        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px' }}>
                            <div>
                                <h4 style={{ color: 'var(--secondary)', marginBottom: '10px' }}>Orders Collection</h4>
                                <div style={{ height: '550px', overflowY: 'auto', background: '#1e293b', color: '#38bdf8', padding: '15px', borderRadius: '12px', fontSize: '0.75rem', fontFamily: 'monospace' }}>
                                    <pre>{JSON.stringify(databaseSnapshot.orders, null, 2)}</pre>
                                </div>
                            </div>
                            <div>
                                <h4 style={{ color: 'var(--primary)', marginBottom: '10px' }}>Inventory (dataset2)</h4>
                                <div style={{ height: '550px', overflowY: 'auto', background: '#1e293b', color: '#34d399', padding: '15px', borderRadius: '12px', fontSize: '0.75rem', fontFamily: 'monospace' }}>
                                    <pre>{JSON.stringify(databaseSnapshot.inventory, null, 2)}</pre>
                                </div>
                            </div>
                        </div>
                    </div>
                )}
            </main>

            <style>{`
                @keyframes bounce { to { transform: translateY(0); } from { transform: translateY(-5px); } }
                @keyframes slideUp { from { transform: translateY(10px); opacity: 0; } to { transform: translateY(0); opacity: 1; } }
                ::-webkit-scrollbar { width: 8px; }
                ::-webkit-scrollbar-track { background: transparent; }
                ::-webkit-scrollbar-thumb { background: #e2e8f0; border-radius: 10px; }
                ::-webkit-scrollbar-thumb:hover { background: #cbd5e1; }
                .chat-bubble { max-width: 80%; padding: 12px 20px; border-radius: 18px; line-height: 1.5; margin-bottom: 20px; }
                .chat-ai { align-self: flex-start; background: #f1f5f9; color: #1e293b; border-bottom-left-radius: 2px; }
                .chat-user { align-self: flex-end; background: var(--secondary); color: white; border-bottom-right-radius: 2px; }
                .nav-item { padding: 12px 15px; border-radius: 10px; cursor: pointer; display: flex; align-items: center; gap: 10px; transition: all 0.2s; color: var(--text-muted); }
                .nav-item:hover { background: #f1f5f9; color: var(--primary); }
                .nav-item.active { background: #eff6ff; color: var(--primary); font-weight: 600; }
                .container { display: flex; min-height: 100vh; background: var(--bg-vibrant); padding: 20px; gap: 20px; font-family: Inter, sans-serif; }
            `}</style>
        </div>
    );
}

export default App;