import { useEffect, useState } from "react";
import { fetchHealth, type HealthResponse } from "./services/api";

function App() {
  const [backendHealth, setBackendHealth] = useState<HealthResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);

  useEffect(() => {
    fetchHealth().then((data) => {
      setBackendHealth(data);
      setLoading(false);
    });
  }, []);

  return (
    <div
      style={{
        minHeight: "100vh",
        display: "flex",
        flexDirection: "column",
        justifyContent: "center",
        alignItems: "center",
        fontFamily: "system-ui, -apple-system, sans-serif",
        backgroundColor: "#0f172a",
        color: "#f8fafc",
        padding: "2rem",
        boxSizing: "border-box",
      }}
    >
      <div
        style={{
          maxWidth: "600px",
          width: "100%",
          backgroundColor: "#1e293b",
          borderRadius: "12px",
          padding: "2.5rem",
          boxShadow: "0 10px 25px -5px rgba(0, 0, 0, 0.5)",
          textAlign: "center",
          border: "1px solid #334155",
        }}
      >
        <h1
          style={{
            fontSize: "2.5rem",
            fontWeight: 800,
            margin: "0 0 0.5rem 0",
            letterSpacing: "-0.025em",
            color: "#38bdf8",
          }}
        >
          FINCTRL AI
        </h1>
        <h2
          style={{
            fontSize: "1.25rem",
            fontWeight: 500,
            margin: "0 0 2rem 0",
            color: "#94a3b8",
          }}
        >
          AI Finance Controller
        </h2>

        <div
          style={{
            padding: "1rem 1.5rem",
            borderRadius: "8px",
            backgroundColor: "#090d16",
            border: "1px solid #334155",
            marginBottom: "1.5rem",
          }}
        >
          <p
            style={{
              margin: 0,
              fontSize: "1rem",
              fontWeight: 600,
              color: "#4ade80",
            }}
          >
            Frontend is running.
          </p>
        </div>

        <div
          style={{
            fontSize: "0.875rem",
            color: "#64748b",
            borderTop: "1px solid #334155",
            paddingTop: "1rem",
          }}
        >
          Backend Status:{" "}
          {loading ? (
            <span>Checking...</span>
          ) : backendHealth ? (
            <span style={{ color: "#4ade80", fontWeight: 600 }}>
              Online ({backendHealth.service})
            </span>
          ) : (
            <span style={{ color: "#f87171" }}>Offline (Optional API check)</span>
          )}
        </div>
      </div>
    </div>
  );
}

export default App;
